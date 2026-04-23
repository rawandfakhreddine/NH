from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, Response
from flask_login import login_required, current_user
from app import db
from app.models import Beneficiary, Claim
import os
import pickle
import csv
import warnings
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

main = Blueprint("main", __name__)

# =========================
# LOAD ML MODEL
# =========================
model = None

model_path = "fraud_model.pkl"

if os.path.exists(model_path):
    try:
        with open(model_path, "rb") as f:
            model = pickle.load(f)
        print("Model loaded successfully")
    except Exception as e:
        print("Error loading model:", e)
else:
    print("fraud_model.pkl not found")


# =========================
# AI PREDICTION FUNCTION
# =========================
def predict_claim_risk(claim):
    score = 0
    reasons = []

    if float(claim.total_gross or 0) > 10000:
        score += 40
        reasons.append("Large claim amount")

    if str(claim.status).lower() == "denied":
        score += 35
        reasons.append("Denied status")

    if float(claim.patient_share or 0) > 500:
        score += 25
        reasons.append("High patient share")

    # ML model still used if available
    if model is not None:
        try:
            features = pd.DataFrame([{
                "total_gross": float(claim.total_gross or 0),
                "patient_share": float(claim.patient_share or 0),
                "net_amount": float(claim.net_amount or 0)
            }])

            pred = model.predict(features)[0]
            pred_text = str(pred).lower()

            if pred_text in ["high", "1"]:
                risk = "High"
                score = max(score, 85)
            elif pred_text in ["medium", "2"]:
                risk = "Medium"
                score = max(score, 60)
            else:
                risk = "Low"
                score = max(score, 25)

        except Exception as e:
            print("Prediction error:", e)
            if score >= 70:
                risk = "High"
            elif score >= 40:
                risk = "Medium"
            else:
                risk = "Low"
    else:
        if score >= 70:
            risk = "High"
        elif score >= 40:
            risk = "Medium"
        else:
            risk = "Low"

    if not reasons:
        reasons.append("Normal financial pattern")

    if risk == "High":
        recommendation = "Manual review required"
    elif risk == "Medium":
        recommendation = "Monitor before approval"
    else:
        recommendation = "Looks safe"

    return {
        "risk": risk,
        "score": min(score, 99),
        "explanation": ", ".join(reasons),
        "recommendation": recommendation
    }

# =========================
# HOME
# =========================
@main.route("/")
def home():
    return render_template("home.html")


# =========================
# DASHBOARD
# =========================
@main.route("/dashboard")
@login_required
def dashboard():
    total_beneficiaries = Beneficiary.query.count()
    total_claims = Claim.query.count()
    recent_claims = Claim.query.order_by(Claim.id.desc()).limit(5).all()

    return render_template(
        "dashboard.html",
        user=current_user,
        total_beneficiaries=total_beneficiaries,
        total_claims=total_claims,
        recent_claims=recent_claims
    )


# =========================
# BENEFICIARIES
# =========================
@main.route("/beneficiaries")
@login_required
def beneficiaries():
    q = request.args.get("q", "").strip()
    gender = request.args.get("gender", "").strip()
    sort = request.args.get("sort", "newest").strip()

    query = Beneficiary.query

    if q:
        query = query.filter(
            (Beneficiary.first_name.ilike(f"%{q}%")) |
            (Beneficiary.last_name.ilike(f"%{q}%")) |
            (Beneficiary.national_id.ilike(f"%{q}%")) |
            (Beneficiary.nationality.ilike(f"%{q}%")) |
            (Beneficiary.email_address.ilike(f"%{q}%"))
        )

    if gender:
        query = query.filter_by(gender=gender)

    if sort == "oldest":
        query = query.order_by(Beneficiary.id.asc())
    elif sort == "first_name":
        query = query.order_by(Beneficiary.first_name.asc())
    elif sort == "last_name":
        query = query.order_by(Beneficiary.last_name.asc())
    else:
        query = query.order_by(Beneficiary.id.desc())

    beneficiaries = query.all()

    return render_template(
        "beneficiaries.html",
        beneficiaries=beneficiaries,
        q=q,
        gender=gender,
        sort=sort
    )


# =========================
# ADD BENEFICIARY
# =========================
@main.route("/add_beneficiary", methods=["GET", "POST"])
@login_required
def add_beneficiary():
    if request.method == "POST":
        b = Beneficiary(
            national_id=request.form["national_id"],
            first_name=request.form["first_name"],
            last_name=request.form["last_name"],
            date_of_birth=request.form["date_of_birth"],
            gender=request.form["gender"],
            nationality=request.form["nationality"],
            mobile_number=request.form.get("mobile_number"),
            email_address=request.form.get("email_address")
        )

        db.session.add(b)
        db.session.commit()

        flash("Beneficiary added!", "success")
        return redirect(url_for("main.beneficiaries"))

    return render_template("add_beneficiary.html")


# =========================
# CLAIMS
# =========================
@main.route("/claims")
@login_required
def claims():
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()
    sort = request.args.get("sort", "newest").strip()
    page = request.args.get("page", 1, type=int)

    query = Claim.query

    if q:
        query = query.filter(
            (Claim.claim_number.ilike(f"%{q}%")) |
            (Claim.beneficiary_national_id.ilike(f"%{q}%")) |
            (Claim.diagnosis_code.ilike(f"%{q}%"))
        )

    if status:
        query = query.filter_by(status=status)

    if sort == "oldest":
        query = query.order_by(Claim.id.asc())
    elif sort == "gross_high":
        query = query.order_by(Claim.total_gross.desc())
    elif sort == "gross_low":
        query = query.order_by(Claim.total_gross.asc())
    else:
        query = query.order_by(Claim.id.desc())

    pagination = query.paginate(page=page, per_page=25, error_out=False)
    claim_objects = pagination.items

    claims = []
    for c in claim_objects:
        ai = predict_claim_risk(c)

        claims.append({
            "claim_number": c.claim_number,
            "beneficiary_national_id": c.beneficiary_national_id,
            "encounter_date": c.encounter_date,
            "diagnosis_code": c.diagnosis_code,
            "total_gross": c.total_gross,
            "patient_share": c.patient_share,
            "net_amount": c.net_amount,
            "status": c.status,
            "risk": ai["risk"],
            "score": ai["score"],
            "explanation": ai["explanation"],
            "recommendation": ai["recommendation"]
        })

    return render_template(
        "claims.html",
        claims=claims,
        q=q,
        status=status,
        sort=sort,
        pagination=pagination
    )


# =========================
# ADD CLAIM
# =========================
@main.route("/add_claim", methods=["GET", "POST"])
@login_required
def add_claim():
    if request.method == "POST":
        claim = Claim(
            claim_number=request.form["claim_number"],
            beneficiary_national_id=request.form["beneficiary_national_id"],
            encounter_date=request.form["encounter_date"],
            diagnosis_code=request.form["diagnosis_code"],
            total_gross=float(request.form["total_gross"]),
            patient_share=float(request.form["patient_share"]),
            net_amount=float(request.form["net_amount"]),
            status=request.form["status"]
        )

        db.session.add(claim)
        db.session.commit()

        flash("Claim added!", "success")
        return redirect(url_for("main.claims"))

    return render_template("add_claim.html")


# =========================
# AI DASHBOARD
# =========================
@main.route("/ai_dashboard")
@login_required
def ai_dashboard():
    latest_claims = Claim.query.order_by(Claim.id.desc()).limit(500).all()

    total = len(latest_claims)
    high = 0
    medium = 0
    low = 0
    recent_risks = []

    if total == 0:
        return render_template(
            "ai_dashboard.html",
            total=0,
            high=0,
            medium=0,
            low=0,
            high_percent=0,
            medium_percent=0,
            low_percent=0,
            recent_risks=[]
        )

    for c in latest_claims:
        ai = predict_claim_risk(c)
        risk = ai["risk"]

        if risk == "High":
            high += 1
        elif risk == "Medium":
            medium += 1
        else:
            low += 1

        recent_risks.append({
            "claim_number": c.claim_number,
            "beneficiary_national_id": c.beneficiary_national_id,
            "diagnosis_code": c.diagnosis_code,
            "total_gross": c.total_gross,
            "status": c.status,
            "risk": ai["risk"],
            "score": ai["score"],
            "explanation": ai["explanation"],
            "recommendation": ai["recommendation"]
        })

    high_percent = round((high / total) * 100, 1)
    medium_percent = round((medium / total) * 100, 1)
    low_percent = round((low / total) * 100, 1)

    return render_template(
        "ai_dashboard.html",
        total=total,
        high=high,
        medium=medium,
        low=low,
        high_percent=high_percent,
        medium_percent=medium_percent,
        low_percent=low_percent,
        recent_risks=recent_risks[:5]
    )

# =========================
# PORTAL
# =========================
@main.route("/portal")
@login_required
def portal():
    return render_template("home.html")


# =========================
# FULL AI CHAT PAGE
# =========================
@main.route("/ai_chat")
@login_required
def ai_chat():
    return render_template("ai_chat.html")


# =========================
# CHATBOT
# =========================
@main.route("/chat", methods=["POST"])
def chat():
    data = request.get_json() or {}
    msg = data.get("message", "").lower()

    total_claims = Claim.query.count()
    total_beneficiaries = Beneficiary.query.count()

    if "claims" in msg:
        reply = f"There are {total_claims} claims."
    elif "beneficiaries" in msg:
        reply = f"There are {total_beneficiaries} beneficiaries."
    else:
        reply = "Ask about claims or beneficiaries."

    return jsonify({"response": reply})


# =========================
# EXPORT CLAIMS
# =========================
@main.route("/export_claims")
@login_required
def export_claims():
    claims = Claim.query.limit(1000).all()

    def generate():
        yield "Claim Number,Beneficiary ID,Diagnosis,Total Gross,Status\n"
        for c in claims:
            yield f"{c.claim_number},{c.beneficiary_national_id},{c.diagnosis_code},{c.total_gross},{c.status}\n"

    return Response(
        generate(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=claims.csv"}
    )

