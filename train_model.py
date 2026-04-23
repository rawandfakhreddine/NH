import pandas as pd
import pickle
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

# =========================================
# SAMPLE TRAINING DATA
# =========================================
data = {
    "total_gross": [500, 1200, 2500, 3000, 4500, 6000, 8500, 10000, 15000, 20000,
                    700, 1600, 2800, 5200, 7300, 9400, 11000, 13000, 17000, 22000],
    "patient_share": [50, 100, 250, 300, 600, 1200, 1600, 2000, 3000, 5000,
                      70, 150, 280, 600, 1000, 1800, 2200, 2600, 3300, 5200],
    "net_amount": [450, 1100, 2250, 2700, 3900, 4800, 6900, 8000, 12000, 15000,
                   630, 1450, 2520, 4600, 6300, 7600, 8800, 10400, 13700, 16800],
    "risk": [
        "Low", "Low", "Low", "Low", "Medium",
        "Medium", "Medium", "High", "High", "High",
        "Low", "Low", "Low", "Medium", "Medium",
        "Medium", "High", "High", "High", "High"
    ]
}

df = pd.DataFrame(data)

X = df[["total_gross", "patient_share", "net_amount"]]
y = df["risk"]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

model = RandomForestClassifier(
    n_estimators=200,
    max_depth=6,
    random_state=42
)
model.fit(X_train, y_train)

y_pred = model.predict(X_test)
print("Model trained successfully")
print(classification_report(y_test, y_pred))

with open("fraud_model.pkl", "wb") as f:
    pickle.dump(model, f)

print("Saved fraud_model.pkl")