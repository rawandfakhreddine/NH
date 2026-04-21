from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Beneficiary, Claim
import os
import pickle
import numpy as np

main = Blueprint("main", __name__)

# =========================
# LOAD AI MODEL (.pkl)
# =========================
model = None
model_path = "fraud_model.pkl"

if os.path.exists(model_path):
    try:
        with open(model_path, "rb") as f:
            model = pickle.load(f)
        print("Model loaded successfully from fraud_model.pkl")
    except Exception as e:
        print("Error loading model:", e)
        model = None
else:
    print("fraud_model.pkl not found")


# =========================
# ML PREDICTION FUNCTION
# =========================
def predict_claim_risk(claim):
    """
    Uses the .pkl model first.
    If anything fails, returns None and fallback logic is used.
    """
    if model is None:
        return None

    try:
        features = np.array([[
            float(claim.total_gross or 0),
            float(claim.patient_share or 0),
            float(claim.net_amount or 0)
        ]])

        prediction = model.predict(features)[0]

        # Flexible mapping
        if prediction in [1, "1", "High", "HIGH", "high"]:
            return "High"
        elif prediction in [2, "2", "Medium", "MEDIUM", "medium"]:
            return "Medium"
        else:
            return "Low"

    except Exception as e:
        print("Prediction error:", e)
        return None


# =========================
# FALLBACK / EXPLANATION LOGIC
# =========================
def analyze_claim(claim):
    """
    Main analysis logic:
    1. Try ML model
    2. If ML unavailable/fails, use rule-based fallback
    """
    ml_prediction = predict_claim_risk(claim)

    reasons = []

    if claim.total_gross and float(claim.total_gross) > 5000:
        reasons.append("High claim amount")

    if claim.status == "Denied":
        reasons.append("Claim was denied")

    diagnosis_code = str(claim.diagnosis_code).strip().upper() if claim.diagnosis_code else ""
    if diagnosis_code.startswith("Z"):
        reasons.append("Unusual diagnosis code")

    if ml_prediction is not None:
        explanation = "Predicted by AI model"
        if reasons:
            explanation += " + " + ", ".join(reasons)
        return ml_prediction, explanation

    # fallback rules
    if len(reasons) >= 2:
        risk = "High"
    elif len(reasons) == 1:
        risk = "Medium"
    else:
        risk = "Low"

    explanation = ", ".join(reasons) if reasons else "No major risk factors detected"
    return risk, explanation


def get_risk_counts():
    claims = Claim.query.all()
    high = 0
    medium = 0
    low = 0

    for claim in claims:
        risk, _ = analyze_claim(claim)
        if risk == "High":
            high += 1
        elif risk == "Medium":
            medium += 1
        else:
            low += 1

    return high, medium, low


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
    all_beneficiaries = Beneficiary.query.order_by(Beneficiary.id.desc()).all()
    return render_template("beneficiaries.html", beneficiaries=all_beneficiaries)


@main.route("/beneficiaries/add", methods=["GET", "POST"])
@login_required
def add_beneficiary():
    if request.method == "POST":
        national_id = request.form.get("national_id")

        existing = Beneficiary.query.filter_by(national_id=national_id).first()
        if existing:
            flash("National ID already exists.", "error")
            return redirect(url_for("main.add_beneficiary"))

        new = Beneficiary(
            national_id=request.form.get("national_id"),
            first_name=request.form.get("first_name"),
            last_name=request.form.get("last_name"),
            date_of_birth=request.form.get("date_of_birth"),
            gender=request.form.get("gender"),
            nationality=request.form.get("nationality"),
            mobile_number=request.form.get("mobile_number"),
            email_address=request.form.get("email_address")
        )

        db.session.add(new)
        db.session.commit()

        flash("Beneficiary added successfully.", "success")
        return redirect(url_for("main.beneficiaries"))

    return render_template("add_beneficiary.html")


# =========================
# CLAIMS
# =========================
@main.route("/claims")
@login_required
def claims():
    all_claims = Claim.query.order_by(Claim.id.desc()).all()
    return render_template("claims.html", claims=all_claims)


@main.route("/claims/add", methods=["GET", "POST"])
@login_required
def add_claim():
    if request.method == "POST":
        claim_number = request.form.get("claim_number")

        existing = Claim.query.filter_by(claim_number=claim_number).first()
        if existing:
            flash("Claim already exists.", "error")
            return redirect(url_for("main.add_claim"))

        new = Claim(
            claim_number=request.form.get("claim_number"),
            beneficiary_national_id=request.form.get("beneficiary_national_id"),
            encounter_date=request.form.get("encounter_date"),
            diagnosis_code=request.form.get("diagnosis_code"),
            total_gross=float(request.form.get("total_gross")),
            patient_share=float(request.form.get("patient_share")),
            net_amount=float(request.form.get("net_amount")),
            status=request.form.get("status")
        )

        db.session.add(new)
        db.session.commit()

        flash("Claim added successfully.", "success")
        return redirect(url_for("main.claims"))

    return render_template("add_claim.html")


# =========================
# AI FRAUD PAGE
# =========================
@main.route("/ai-fraud", methods=["GET", "POST"])
@login_required
def ai_fraud():
    prediction = None

    if request.method == "POST":
        try:
            total_gross = float(request.form.get("total_gross"))
            patient_share = float(request.form.get("patient_share"))
            net_amount = float(request.form.get("net_amount"))

            if model is not None:
                features = np.array([[total_gross, patient_share, net_amount]])
                raw_prediction = model.predict(features)[0]

                if raw_prediction in [1, "1", "High", "HIGH", "high"]:
                    prediction = "High Risk"
                elif raw_prediction in [2, "2", "Medium", "MEDIUM", "medium"]:
                    prediction = "Medium Risk"
                else:
                    prediction = "Low Risk"
            else:
                prediction = "AI model not available"

        except Exception as e:
            print("AI fraud prediction error:", e)
            prediction = "Prediction failed"

    return render_template("ai_fraud.html", prediction=prediction)


# =========================
# AI DASHBOARD
# =========================
@main.route("/ai-dashboard")
@login_required
def ai_dashboard():
    claims = Claim.query.order_by(Claim.id.desc()).all()

    high = 0
    medium = 0
    low = 0
    recent_risks = []

    for claim in claims:
        risk, explanation = analyze_claim(claim)

        if risk == "High":
            high += 1
        elif risk == "Medium":
            medium += 1
        else:
            low += 1

        recent_risks.append({
            "claim_number": claim.claim_number,
            "beneficiary_national_id": claim.beneficiary_national_id,
            "diagnosis_code": claim.diagnosis_code,
            "total_gross": claim.total_gross,
            "status": claim.status,
            "risk": risk,
            "explanation": explanation
        })

    total = len(claims)

    high_percent = round((high / total) * 100, 1) if total else 0
    medium_percent = round((medium / total) * 100, 1) if total else 0
    low_percent = round((low / total) * 100, 1) if total else 0

    return render_template(
        "ai_dashboard.html",
        total=total,
        high=high,
        medium=medium,
        low=low,
        high_percent=high_percent,
        medium_percent=medium_percent,
        low_percent=low_percent,
        recent_risks=recent_risks[:10]
    )


# =========================
# PORTAL
# =========================
@main.route("/portal")
@login_required
def portal():
    recent_claims = Claim.query.order_by(Claim.id.desc()).limit(5).all()

    notices = [f"Claim {c.claim_number} - {c.total_gross}" for c in recent_claims]

    standards = [
        "High amount > 5000 -> High Risk",
        "Denied claim -> High Risk",
        "Diagnosis starting with Z -> Medium Risk",
        "ML model integrated using fraud_model.pkl"
    ]

    dictionary = [
        "Beneficiary -> Patient",
        "Claim -> Financial transaction",
        "Diagnosis -> Medical classification",
        "Encounter -> Visit"
    ]

    reporting = [
        f"Total Claims: {Claim.query.count()}",
        f"Total Beneficiaries: {Beneficiary.query.count()}",
        "AI Monitoring Active",
        "ML Model: fraud_model.pkl"
    ]

    return render_template(
        "portal.html",
        notices=notices,
        standards=standards,
        dictionary=dictionary,
        reporting=reporting
    )


# =========================
# CHATBOT
# =========================
@main.route("/chat", methods=["POST"])
def chat():
    data = request.get_json() or {}
    message = data.get("message", "").strip().lower()
    lang = data.get("lang", "en")

    total_claims = Claim.query.count()
    total_beneficiaries = Beneficiary.query.count()
    high, medium, low = get_risk_counts()

    latest_high_risk = []
    for claim in Claim.query.order_by(Claim.id.desc()).limit(20).all():
        risk, explanation = analyze_claim(claim)
        if risk == "High":
            latest_high_risk.append(
                f"{claim.claim_number} ({claim.total_gross}) - {explanation}"
            )

    latest_high_risk = latest_high_risk[:3]

    if lang == "ar":
        if "كم" in message and "مطالب" in message:
            reply = f"يوجد حاليًا {total_claims} مطالبة في النظام."
        elif "كم" in message and "مستفيد" in message:
            reply = f"يوجد حاليًا {total_beneficiaries} مستفيد في النظام."
        elif "عالي" in message and "مخاطر" in message:
            reply = f"يوجد {high} مطالبة عالية المخاطر."
        elif "متوسط" in message and "مخاطر" in message:
            reply = f"يوجد {medium} مطالبة متوسطة المخاطر."
        elif "منخفض" in message and "مخاطر" in message:
            reply = f"يوجد {low} مطالبة منخفضة المخاطر."
        elif ("اعرض" in message or "show" in message) and ("عالية" in message or "high risk" in message):
            if latest_high_risk:
                reply = "أحدث المطالبات عالية المخاطر:\n" + "\n".join(latest_high_risk)
            else:
                reply = "لا توجد مطالبات عالية المخاطر حاليًا."
        elif "ذكاء" in message or "احتيال" in message:
            reply = f"تحليل الذكاء الاصطناعي الحالي: عالية المخاطر {high}، متوسطة {medium}، منخفضة {low}."
        else:
            reply = "يمكنني إخبارك بعدد المطالبات، وعدد المستفيدين، وعدد المطالبات عالية أو متوسطة أو منخفضة المخاطر."
    else:
        if "how many claims" in message or "total claims" in message:
            reply = f"There are currently {total_claims} claims in the system."
        elif "how many beneficiaries" in message or "total beneficiaries" in message:
            reply = f"There are currently {total_beneficiaries} beneficiaries in the system."
        elif "how many high risk" in message or "high risk claims" in message:
            reply = f"There are currently {high} high-risk claims."
        elif "how many medium risk" in message or "medium risk claims" in message:
            reply = f"There are currently {medium} medium-risk claims."
        elif "how many low risk" in message or "low risk claims" in message:
            reply = f"There are currently {low} low-risk claims."
        elif "show high risk" in message or "list high risk" in message:
            if latest_high_risk:
                reply = "Latest high-risk claims:\n" + "\n".join(latest_high_risk)
            else:
                reply = "There are no high-risk claims right now."
        elif "ai summary" in message or "fraud summary" in message:
            reply = f"AI summary: {high} high-risk claims, {medium} medium-risk claims, and {low} low-risk claims."
        else:
            reply = "I can tell you the total claims, total beneficiaries, high-risk claims, medium-risk claims, low-risk claims, or list the latest high-risk claims."

    return jsonify({"response": reply})