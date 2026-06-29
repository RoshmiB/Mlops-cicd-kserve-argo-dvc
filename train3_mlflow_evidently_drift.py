import os
import argparse
import warnings

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split, RandomizedSearchCV, StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.metrics import roc_auc_score, precision_score, recall_score, f1_score, confusion_matrix, roc_curve

import mlflow
import mlflow.xgboost
from evidently import Report
from evidently.presets import DataDriftPreset, TargetDriftPreset, DataSummaryPreset

warnings.filterwarnings('ignore')


def parse_args():
    parser = argparse.ArgumentParser(
        description="Train an XGBoost model, log artifacts to MLflow, and generate Evidently drift reports."
    )
    parser.add_argument("--csv", default="data/loans.csv", help="Path to reference CSV file")
    parser.add_argument(
        "--current-csv",
        default=None,
        help="Optional path to current/production CSV file for drift monitoring. If omitted, the test split is used."
    )
    parser.add_argument("--target", default="loan_status", help="Target column name")
    parser.add_argument("--experiment", default="loan-defaulter-prediction", help="MLflow experiment name")
    parser.add_argument("--run", default="run-1", help="MLflow run name")
    parser.add_argument("--test-size", type=float, default=0.2, help="Test split fraction")
    parser.add_argument("--random-state", type=int, default=42, help="Random seed")
    parser.add_argument("--threshold", type=float, default=0.48, help="Custom classification threshold")
    parser.add_argument(
        "--report-path",
        default="evidently_drift_report.html",
        help="Output path for the generated Evidently HTML report"
    )
    return parser.parse_args()


def preprocess(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.drop(['id', 'member_id', 'delinq_2yrs', 'pub_rec', 'grade', 'last_pymnt_amnt', 'installment'], axis=1, inplace=True, errors='ignore')
    df.dropna(subset=['revol_util'], inplace=True)

    df['emp_length'] = df['emp_length'].replace({'< 1 year': '0', '10+ years': '10'})
    df['emp_length'] = df['emp_length'].astype(str).str.replace(' years', '', regex=False)
    df['emp_length'] = pd.to_numeric(df['emp_length'], errors='coerce')

    median_emp_length = df['emp_length'].median()
    df['emp_length'] = df['emp_length'].fillna(median_emp_length).astype(int)

    df['term'] = df['term'].astype(str).str.replace(' months', '', regex=False).astype(float).astype(int)
    df['revol_util'] = df['revol_util'].astype(str).str.rstrip('%').astype(float) / 100.0
    df['int_rate'] = df['int_rate'].astype(str).str.rstrip('%').astype(float) / 100.0

    df = pd.get_dummies(df, columns=['purpose', 'home_ownership', 'verification_status'], drop_first=True)
    df['loan_status'] = df['loan_status'].map({'Fully Paid': 0, 'Charged Off': 1})
    df['loan_to_income_ratio'] = df['loan_amnt'] / df['annual_inc'] + 1e-6
    df['revol_bal_to_income'] = df['revol_bal'] / df['annual_inc'] + 1e-6
    df['inq_to_acc_ratio'] = df['inq_last_6mths'] / (df['open_acc'] + 1)
    df.drop(['sub_grade'], axis=1, inplace=True, errors='ignore')

    return df


def load_current_data(path: str, target: str) -> pd.DataFrame:
    if path is None:
        return None
    if not os.path.exists(path):
        raise FileNotFoundError(f"Current data CSV not found: {path}")
    df = pd.read_csv(path)
    df = preprocess(df)
    if target not in df.columns:
        raise ValueError(f"Target column '{target}' not found in current CSV: {path}")
    return df


def save_chart(filename: str, title: str):
    plt.tight_layout()
    plt.savefig(filename)
    plt.close()


def main():
    args = parse_args()
    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:7006")
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment(args.experiment)
    mlflow.xgboost.autolog()

    if not os.path.exists(args.csv):
        raise SystemExit(f"Reference CSV not found: {args.csv}")

    df = pd.read_csv(args.csv)
    df = preprocess(df)

    if args.target not in df.columns:
        raise SystemExit(f"Target column '{args.target}' not found in reference data")

    X = df.drop([args.target], axis=1)
    y = df[args.target]

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        random_state=args.random_state,
        stratify=y,
        test_size=args.test_size,
    )

    pipeline = Pipeline([
        ('xgb', XGBClassifier(
            random_state=args.random_state,
            eval_metric='logloss',
            tree_method='hist',
            use_label_encoder=False,
        ))
    ])

    param_grid = {
        'xgb__max_depth': [3, 4, 5, 6],
        'xgb__gamma': [0, 0.1, 0.3],
        'xgb__learning_rate': [0.01, 0.05, 0.1],
        'xgb__n_estimators': [100, 200, 300],
        'xgb__subsample': [0.8, 1.0],
        'xgb__colsample_bytree': [0.8, 1.0],
    }

    current_df = load_current_data(args.current_csv, args.target)

    with mlflow.start_run(run_name=args.run):
        print("Starting hyperparameter tuning...")
        random_search = RandomizedSearchCV(
            estimator=pipeline,
            param_distributions=param_grid,
            cv=StratifiedKFold(n_splits=3, shuffle=True, random_state=args.random_state),
            scoring='f1',
            n_iter=30,
            n_jobs=-1,
            verbose=1,
            random_state=args.random_state,
        )

        random_search.fit(X_train, y_train)
        best_pipeline = random_search.best_estimator_

        print(f"Best hyperparameters: {random_search.best_params_}")
        mlflow.log_params(random_search.best_params_)

        y_prob = best_pipeline.predict_proba(X_test)[:, 1]
        y_pred = np.where(y_prob > args.threshold, 1, 0)

        mlflow.log_param("custom_threshold", args.threshold)
        mlflow.log_metric("roc_auc", roc_auc_score(y_test, y_prob))
        mlflow.log_metric("precision", precision_score(y_test, y_pred))
        mlflow.log_metric("recall", recall_score(y_test, y_pred))
        mlflow.log_metric("f1", f1_score(y_test, y_pred))

        cm = confusion_matrix(y_test, y_pred)
        plt.figure(figsize=(6, 4))
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues')
        plt.title('Confusion Matrix')
        save_chart('confusion_matrix.png', 'Confusion Matrix')
        mlflow.log_artifact('confusion_matrix.png')

        fpr, tpr, _ = roc_curve(y_test, y_prob)
        plt.figure(figsize=(8, 6))
        plt.plot(fpr, tpr, label=f'ROC AUC = {roc_auc_score(y_test, y_prob):.3f}')
        plt.plot([0, 1], [0, 1], '--', color='gray')
        plt.xlabel('False Positive Rate')
        plt.ylabel('True Positive Rate')
        plt.title('ROC Curve')
        plt.legend()
        save_chart('roc_curve.png', 'ROC Curve')
        mlflow.log_artifact('roc_curve.png')

        reference_df = X_train.copy()
        reference_df[args.target] = y_train

        if current_df is None:
            current_df = X_test.copy()
            current_df[args.target] = y_test
            current_source = 'test_split'
        else:
            current_source = args.current_csv

        if 'prediction' not in current_df.columns:
            current_df['prediction'] = best_pipeline.predict(current_df.drop([args.target], axis=1))

        report_metrics = [DataDriftPreset(), DataSummaryPreset()]
        if args.target in current_df.columns:
            report_metrics.insert(1, TargetDriftPreset())

        print(f"Generating Evidently report using current data source: {current_source}")
        drift_report = Report(metrics=report_metrics)
        report_snapshot = drift_report.run(reference_data=reference_df, current_data=current_df)

        report_snapshot.save_html(args.report_path)
        mlflow.log_artifact(args.report_path)

        report_dict = report_snapshot.dict()
        metrics = report_dict.get('metrics', [])

        dataset_drift = False
        drift_share = 0.0
        target_drift = False
        target_drift_share = 0.0

        for metric in metrics:
            if metric.get('metric') == 'DatasetDriftMetric':
                result = metric.get('result', {})
                drift_share = float(result.get('share_of_drifted_columns', 0.0))
                dataset_drift = bool(result.get('dataset_drift', False))
            if metric.get('metric') == 'TargetDriftMetric':
                result = metric.get('result', {})
                target_drift_share = float(result.get('share_of_drifted_columns', 0.0))
                target_drift = bool(result.get('dataset_drift', False))

        mlflow.log_metric('evidently_drift_share', drift_share)
        mlflow.log_metric('evidently_dataset_drift_detected', 1.0 if dataset_drift else 0.0)
        mlflow.log_metric('evidently_target_drift_share', target_drift_share)
        mlflow.log_metric('evidently_target_drift_detected', 1.0 if target_drift else 0.0)
        mlflow.log_param('current_data_source', current_source)

        print(
            f"Evidently summary: dataset drift={dataset_drift}, "
            f"drift share={drift_share:.3f}, target drift={target_drift}, "
            f"target drift share={target_drift_share:.3f}"
        )

        mlflow.xgboost.log_model(
            best_pipeline.named_steps['xgb'],
            artifact_path='model',
            registered_model_name='LoanDefaultPredictor'
        )


if __name__ == '__main__':
    main()
