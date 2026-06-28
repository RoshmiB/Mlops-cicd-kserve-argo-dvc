import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split, RandomizedSearchCV, StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.metrics import roc_auc_score, precision_score, recall_score, f1_score, confusion_matrix, roc_curve
import mlflow
import mlflow.xgboost
import warnings
import argparse

# === ADD EVIDENTLY IMPORTS HERE ===
from evidently import Report
from evidently.presets import DataDriftPreset, DataSummaryPreset
warnings.filterwarnings('ignore')


def parse_args():
    p = argparse.ArgumentParser("Simple MLflow demo (loan defaulter prediction)")
    p.add_argument("--csv", default="data/loans.csv", help="Path to CSV (default: data/loans.csv)")
    p.add_argument("--target", default="loan_status", help="Target column name (default: loan_status)")
    p.add_argument("--experiment", default="loan-defaulter-prediction", help="MLflow experiment name")
    p.add_argument("--run", default="run-1", help="MLflow run name")
    p.add_argument("--test-size", type=float, default=0.2, help="Test split fraction (default: 0.3)")
    p.add_argument("--random-state", type=int, default=42, help="Random seed (default: 42)")
    return p.parse_args()

def preprocess(df):
    # Data loading and pre-processing
    df.drop(['id', 'member_id','delinq_2yrs','pub_rec','grade','last_pymnt_amnt', 'installment'], axis=1, inplace=True)
    df.dropna(subset=['revol_util'], inplace=True)

    df['emp_length'] = df['emp_length'].replace({'< 1 year': '0', '10+ years': '10'})
    df['emp_length'] = df['emp_length'].astype(str).str.replace(' years', '', regex=False)
    df['emp_length'] = pd.to_numeric(df['emp_length'], errors='coerce')

    median_emp_length = df['emp_length'].median()
    df['emp_length'] = df['emp_length'].fillna(median_emp_length).astype(int)

    df['term'] = df['term'].astype(str).str.replace(' months', '', regex=False).astype(int)
    df['revol_util'] = df['revol_util'].astype(str).str.rstrip('%').astype(float) / 100.0
    df['int_rate'] = df['int_rate'].astype(str).str.rstrip('%').astype(float) / 100.0

    # EDA 
    df = pd.get_dummies(df, columns=['purpose', 'home_ownership', 'verification_status'], drop_first=True)

    df['loan_status'] = df['loan_status'].map({
        'Fully Paid':0,
        'Charged Off':1
    })

    df['loan_to_income_ratio'] = df['loan_amnt'] / df['annual_inc'] + 1e-6 
    df['revol_bal_to_income'] = df['revol_bal']/df['annual_inc'] + 1e-6
    df['inq_to_acc_ratio']=df['inq_last_6mths']/(df['open_acc']+1)

    df.drop(['sub_grade'],axis=1,inplace=True,errors='ignore')

    return(df)


def main():
    args = parse_args()

    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:7006")
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment(args.experiment)
    
    mlflow.xgboost.autolog()
    
    if not os.path.exists(args.csv):
        raise SystemExit(f"CSV not found: {args.csv}.")
    
    df = pd.read_csv(args.csv)
    df = preprocess(df)

    # MODEL SELECTION
    X = df.drop([args.target],axis=1)
    y = df[args.target]

    X_train, X_test, y_train, y_test = train_test_split(X,y,random_state=args.random_state,stratify=y,test_size=args.test_size)

    scale_pos_weight = (np.sum(y_train == 0)/np.sum(y_train == 1))

    pipeline = Pipeline([
        ('xgb', XGBClassifier(
            random_state=42,
            eval_metric='logloss',
            scale_pos_weight=scale_pos_weight,
            tree_method='hist'
        ))
    ])

    # HPP TUNING
    param_grid = {
        'xgb__max_depth': [3, 4, 5, 6] ,
        'xgb__gamma': [0, 0.1, 0.3],
        'xgb__learning_rate': [0.01, 0.05, 0.1],
        'xgb__n_estimators': [100,200,300],
        'xgb__subsample': [0.8, 1.0],
        'xgb__colsample_bytree': [0.8, 1.0],
    }
    
    with mlflow.start_run(run_name=args.run):

        print("\nStarting Cost-Sensitive XGBoost Tuning via RandomizedSearchCV...")
        random_search = RandomizedSearchCV(
            estimator=pipeline, 
            param_distributions=param_grid,
            cv=StratifiedKFold(n_splits=3, shuffle=True, random_state=args.random_state), 
            scoring='f1', 
            n_iter=30,
            n_jobs=-1, 
            verbose=1,
            random_state=args.random_state
        )

        random_search.fit(X_train, y_train)
        best_xgb = random_search.best_estimator_

        print(f"Best Parameters Found: {random_search.best_params_}")
        mlflow.log_params(random_search.best_params_)

        # MODEL EVALUATION
        y_prob_default = best_xgb.predict_proba(X_test)[:, 1]

        custom_threshold = 0.48
        mlflow.log_param("custom_threshold", custom_threshold)
        y_pred_adjusted = np.where(y_prob_default > custom_threshold, 1, 0)

        roc_auc = roc_auc_score(y_test,y_prob_default)
        precision = precision_score(y_test,y_pred_adjusted)
        recall = recall_score(y_test,y_pred_adjusted)
        f1 = f1_score(y_test,y_pred_adjusted)

        mlflow.log_metric("roc_auc",roc_auc)
        mlflow.log_metric("precision",precision)
        mlflow.log_metric("recall",recall)
        mlflow.log_metric("f1",f1)

        cm = confusion_matrix(y_test,y_pred_adjusted)
        plt.figure(figsize=(6,4))
        sns.heatmap(cm,annot=True,fmt="d")
        plt.savefig("confusion_matrix.png")
        mlflow.log_artifact("confusion_matrix.png")
        plt.close() # Clean up memory

        fpr,tpr,_ = roc_curve(y_test,y_prob_default)
        plt.figure(figsize=(8,6))
        plt.plot(fpr,tpr)
        plt.plot([0,1],[0,1],'--')
        plt.savefig("roc_curve.png")
        mlflow.log_artifact("roc_curve.png")
        plt.close() # Clean up memory

        # ====================================================================
        # === NEW FULLY COMPATIBLE EVIDENTLY GENERATION & EXTRACTION BLOCK ===
        # ====================================================================
        print("\nGenerating Evidently Reports...")

        reference_df = X_train.copy()
        reference_df[args.target] = y_train

        current_df = X_test.copy()
        current_df[args.target] = y_test

        # 1. Define the report template
        drift_report = Report(metrics=[DataDriftPreset(), DataSummaryPreset()])

        # 2. Compute metrics and capture the Evaluation Snapshot
        report_snapshot = drift_report.run(reference_data=reference_df, current_data=current_df)

        # 3. Save and log the interactive HTML dashboard to MLflow
        report_html_path = "evidently_data_drift_report.html"
        report_snapshot.save_html(report_html_path)
        mlflow.log_artifact(report_html_path)

        # 4. FIX: Use the .dict() method directly on the snapshot result object
        report_dict = report_snapshot.dict()

        # 5. Extract summary metrics using the standardized v0.7 list-based schema
        metrics_list = report_dict.get("metrics", [])
        
        drift_share = 0.0
        dataset_drift = False

        # Loop through the list to safely locate the DatasetDriftMetric calculations
        for metric in metrics_list:
            if metric.get("metric") == "DatasetDriftMetric":
                result = metric.get("result", {})
                drift_share = result.get("share_of_drifted_columns", 0.0)
                dataset_drift = result.get("dataset_drift", False)
                break

        # 6. Log quantitative values to the active MLflow dashboard
        mlflow.log_metric("evidently_drift_share", float(drift_share))
        mlflow.log_metric("evidently_dataset_drift_detected", 1.0 if dataset_drift else 0.0)

        print(f"Evidently Metrics Extracted! Drift Share: {drift_share:.2f}, Dataset Drift: {dataset_drift}")
        print("Evidently reports generated and logged successfully to MLflow!")
        # ====================================================================

        mlflow.xgboost.log_model(
            best_xgb.named_steps["xgb"],
            artifact_path="model",
            registered_model_name="LoanDefaultPredictor"
        )


if __name__ == "__main__":
    # Assuming parse_args() is defined elsewhere in your script file
    main()
