"""FastAPI inference server for churn prediction"""
from fastapi import FastAPI
from pydantic import BaseModel
import pickle
import numpy as np
import pandas as pd

app = FastAPI()

# Load model artifacts
# rb = read binary mode, since we are loading a pickle file
with open('models/churn_model.pkl', 'rb') as f:
    artifacts = pickle.load(f)

model = artifacts['model']
encoder = artifacts['encoder']
scaler = artifacts['scaler']
numerical_cols = artifacts['numerical_cols']
categorical_cols = artifacts['categorical_cols']

class CustomerData(BaseModel):
    gender: str
    senior_citizen: str
    partner: str
    dependents: str
    tenure_months: int
    phone_service: str
    multiple_lines: str
    internet_service: str
    online_security: str
    online_backup: str
    device_protection: str
    tech_support: str
    streaming_tv: str
    streaming_movies: str
    contract: str
    paperless_billing: str
    payment_method: str
    monthly_charges: float
    total_charges: float
    cltv: float

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.post("/predict")
def predict(data: CustomerData):
    raw_input = {
        'Gender': data.gender,
        'Senior Citizen': data.senior_citizen,
        'Partner': data.partner,
        'Dependents': data.dependents,
        'Tenure Months': data.tenure_months,
        'Phone Service': data.phone_service,
        'Multiple Lines': data.multiple_lines,
        'Internet Service': data.internet_service,
        'Online Security': data.online_security,
        'Online Backup': data.online_backup,
        'Device Protection': data.device_protection,
        'Tech Support': data.tech_support,
        'Streaming TV': data.streaming_tv,
        'Streaming Movies': data.streaming_movies,
        'Contract': data.contract,
        'Paperless Billing': data.paperless_billing,
        'Payment Method': data.payment_method,
        'Monthly Charges': data.monthly_charges,
        'Total Charges': data.total_charges,
        'CLTV': data.cltv,
    }

    df = pd.DataFrame([raw_input])
    scaled_num = scaler.transform(df[numerical_cols])
    encoded_cat = encoder.transform(df[categorical_cols])
    features = np.concatenate([scaled_num, encoded_cat], axis=1)

    prediction = model.predict(features)[0]
    probability = model.predict_proba(features)[0][1]

    return {
        "churn": int(prediction),
        "churn_probability": float(probability)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)