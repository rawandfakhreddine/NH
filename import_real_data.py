import os
import glob
from datetime import datetime
import pandas as pd

from app import create_app, db
from app.models import Beneficiary, Claim

SHEET_NAME = "data"


def clean_text(value):
    if pd.isna(value):
        return ""
    return str(value).strip()


def clean_float(value):
    if pd.isna(value) or value == "":
        return 0.0
    try:
        return float(value)
    except Exception:
        return 0.0


def clean_date(value):
    if pd.isna(value) or value == "":
        return None

    if isinstance(value, datetime):
        return value.date()

    try:
        parsed = pd.to_datetime(value, errors="coerce")
        if pd.isna(parsed):
            return None
        return parsed.date()
    except Exception:
        return None


def make_safe_name(member_id):
    member_id = clean_text(member_id)
    if not member_id:
        return "Imported", "Member"
    return "Imported", member_id[-6:]


def find_excel_file():
    root = os.getcwd()

    patterns = [
        os.path.join(root, "*.xlsx"),
        os.path.join(root, "app", "*.xlsx"),
    ]

    matches = []
    for pattern in patterns:
        matches.extend(glob.glob(pattern))

    preferred = [m for m in matches if "HHD_PATIENTS" in os.path.basename(m).upper()]
    if preferred:
        return preferred[0]

    if matches:
        return matches[0]

    return None


def main():
    app = create_app()

    with app.app_context():
        file_path = find_excel_file()

        if not file_path:
            print("ERROR: No .xlsx file found in project root or app folder.")
            return

        print(f"Using Excel file: {file_path}")
        print("Reading Excel file...")

        try:
            df = pd.read_excel(file_path, sheet_name=SHEET_NAME)
        except Exception as e:
            print(f"ERROR reading Excel file: {e}")
            return

        required_columns = ["MEMBERID_2", "CLAIMID"]
        for col in required_columns:
            if col not in df.columns:
                print(f"ERROR: Required column missing: {col}")
                print("Available columns are:")
                print(list(df.columns))
                return

        df = df.dropna(subset=["MEMBERID_2", "CLAIMID"])

        inserted_beneficiaries = 0
        inserted_claims = 0
        skipped_beneficiaries = 0
        skipped_claims = 0

        print("Importing data...")

        for _, row in df.iterrows():
            member_id = clean_text(row.get("MEMBERID_2"))
            birth_date = clean_date(row.get("MEMBER_BIRTHDATE"))
            encounter_start = clean_date(row.get("ENCOUNTERSTART"))
            claim_id = clean_text(row.get("CLAIMID"))
            diagnosis_code = clean_text(row.get("DIAGNOSISCODE"))

            total_gross = clean_float(row.get("ENCOUNTERNET"))
            net_amount = clean_float(row.get("ACTIVITYNET"))
            patient_share = clean_float(row.get("ACTIVITYWRITEOFFAMOUNT"))

            if not member_id:
                skipped_beneficiaries += 1
                continue

            if not claim_id:
                skipped_claims += 1
                continue

            # IMPORTANT: skip claims with missing encounter date
            if not encounter_start:
                skipped_claims += 1
                continue

            # BENEFICIARY
            existing_beneficiary = Beneficiary.query.filter_by(national_id=member_id).first()

            if not existing_beneficiary:
                first_name, last_name = make_safe_name(member_id)

                new_beneficiary = Beneficiary(
                    national_id=member_id,
                    first_name=first_name,
                    last_name=last_name,
                    date_of_birth=birth_date,
                    gender="Unknown",
                    nationality="Unknown",
                    mobile_number="",
                    email_address=""
                )

                db.session.add(new_beneficiary)
                db.session.flush()
                inserted_beneficiaries += 1
            else:
                skipped_beneficiaries += 1

            # CLAIM
            existing_claim = Claim.query.filter_by(claim_number=claim_id).first()

            if not existing_claim:
                new_claim = Claim(
                    claim_number=claim_id,
                    beneficiary_national_id=member_id,
                    encounter_date=encounter_start,
                    diagnosis_code=diagnosis_code if diagnosis_code else "N/A",
                    total_gross=total_gross,
                    patient_share=patient_share,
                    net_amount=net_amount,
                    status="Submitted"
                )

                db.session.add(new_claim)
                db.session.flush()
                inserted_claims += 1
            else:
                skipped_claims += 1

        db.session.commit()

        print("\n===== IMPORT FINISHED =====")
        print(f"Inserted beneficiaries: {inserted_beneficiaries}")
        print(f"Skipped beneficiaries:  {skipped_beneficiaries}")
        print(f"Inserted claims:        {inserted_claims}")
        print(f"Skipped claims:         {skipped_claims}")
        print("===========================")


if __name__ == "__main__":
    main()