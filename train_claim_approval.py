import pandas as pd
import pickle
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report

# =========================
# SAMPLE TRAINING DATA
# =========================
data = {
    "total_gross": [1200, 8000, 3000, 15000, 2500, 700, 9500, 4000, 6000, 1800],
    "patient_share": [100, 1200, 300, 5000, 200, 50, 2000, 500, 1500, 100],
    "net_amount": [1100, 6800, 2700, 10000, 2300, 650, 7500, 3500, 4500, 1700],
    "diagnosis_code": ["A10", "Z99", "B20", "Z12", "C30", "A15", "Z88", "B44", "Z77", "A22"],
    "status": ["Approved", "Denied", "Approved", "Denied", "Approved", "Approved", "Denied", "Approved", "Needs Review", "Approved"]
}

df = pd.DataFrame(data)

# =========================
# ENCODE DIAGNOSIS CODE
# =========================
diagnosis_encoder = LabelEncoder()
df["diagnosis_code_encoded"] = diagnosis_encoder.fit_transform(df["diagnosis_code"])

# =========================
# FEATURES / TARGET
# =========================
X = df[["total_gross", "patient_share", "net_amount", "diagnosis_code_encoded"]]
y = df["status"]

# =========================
# TRAIN / TEST SPLIT
# =========================
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# =========================
# MODEL
# =========================
model = RandomForestClassifier(random_state=42)
model.fit(X_train, y_train)

# =========================
# EVALUATION
# =========================
y_pred = model.predict(X_test)
print("Model trained successfully.")
print(classification_report(y_test, y_pred))

# =========================
# SAVE MODEL
# =========================
with open("claim_approval_model.pkl", "wb") as f:
    pickle.dump(model, f)

# SAVE ENCODER TOO
with open("claim_diagnosis_encoder.pkl", "wb") as f:
    pickle.dump(diagnosis_encoder, f)

print("Saved claim_approval_model.pkl")
print("Saved claim_diagnosis_encoder.pkl")