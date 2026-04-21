from app import db, login_manager
from flask_login import UserMixin


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fullname = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False, default="User")


class Beneficiary(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    national_id = db.Column(db.String(50), unique=True, nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    date_of_birth = db.Column(db.String(20), nullable=False)
    gender = db.Column(db.String(20), nullable=False)
    nationality = db.Column(db.String(50), nullable=False)
    mobile_number = db.Column(db.String(30), nullable=True)
    email_address = db.Column(db.String(150), nullable=True)


class Claim(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    claim_number = db.Column(db.String(50), unique=True, nullable=False)
    beneficiary_national_id = db.Column(db.String(50), nullable=False)
    encounter_date = db.Column(db.String(20), nullable=False)
    diagnosis_code = db.Column(db.String(20), nullable=False)
    total_gross = db.Column(db.Float, nullable=False)
    patient_share = db.Column(db.Float, nullable=False)
    net_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(30), nullable=False, default="Submitted")


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))