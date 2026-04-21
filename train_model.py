import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import joblib

# Simple demo dataset for fraud risk prediction
data = {
    "total_gross": [100, 200, 500, 1200, 3000, 4500, 800, 150, 2500, 6000],
    "patient_share": [10, 20, 50, 100, 200, 300, 80, 15, 150, 400],
    "net_amount": [90, 180, 450, 1100, 2800, 4200, 720, 135, 2350, 5600],
    "status_code": [0, 0, 0, 1, 1, 2, 0, 0, 1, 2],  # Submitted=0, Pending=1, Denied=2
    "risk": ["Low", "Low", "Low", "Medium", "Medium", "High", "Low", "Low", "Medium", "High"]
}

df = pd.DataFrame(data)

X = df[["total_gross", "patient_share", "net_amount", "status_code"]]
y = df["risk"]

model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X, y)

joblib.dump(model, "fraud_model.pkl")
print("Model saved as fraud_model.pkl")