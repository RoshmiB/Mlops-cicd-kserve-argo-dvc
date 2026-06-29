import os
import argparse
import warnings

import numpy as np
import pandas as pd
import joblib
from evidently import Report
from evidently.presets import DataDriftPreset, DataSummaryPreset, TargetDriftPreset

warnings.filterwarnings('ignore')


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate an Evidently drift report from reference and current datasets."
    )
    parser.add_argument("--reference-csv", required=True, help="Path to reference CSV")
    parser.add_argument("--current-csv", required=True, help="Path to current CSV")
    parser.add_argument("--target", default="loan_status", help="Target column name")
    parser.add_argument("--model-path", default=None, help="Optional saved model to generate predictions for target drift")
    parser.add_argument("--prediction-column", default="prediction", help="Prediction column name to use or create")
    parser.add_argument("--report-path", default="evidently_drift_only_report.html", help="Output path for the HTML report")
    parser.add_argument("--skip-target-drift", action="store_true", help="Skip target drift even when target and prediction are available")
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
    if 'loan_status' in df.columns:
        df['loan_status'] = df['loan_status'].map({'Fully Paid': 0, 'Charged Off': 1})
    df['loan_to_income_ratio'] = df['loan_amnt'] / df['annual_inc'] + 1e-6
    df['revol_bal_to_income'] = df['revol_bal'] / df['annual_inc'] + 1e-6
    df['inq_to_acc_ratio'] = df['inq_last_6mths'] / (df['open_acc'] + 1)
    df.drop(['sub_grade'], axis=1, inplace=True, errors='ignore')

    return df


def load_csv(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        raise FileNotFoundError(f"CSV not found: {path}")
    df = pd.read_csv(path)
    return preprocess(df)


def load_model(path: str):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Model file not found: {path}")
    return joblib.load(path)


def main():
    args = parse_args()

    reference_df = load_csv(args.reference_csv)
    current_df = load_csv(args.current_csv)

    if args.target not in reference_df.columns:
        raise ValueError(f"Target column '{args.target}' not found in reference CSV")

    if args.target not in current_df.columns:
        print(f"Warning: target column '{args.target}' not found in current CSV; target drift will be skipped.")

    model = None
    if args.model_path:
        print(f"Loading model from: {args.model_path}")
        model = load_model(args.model_path)
        if args.prediction_column not in current_df.columns:
            features = current_df.drop([args.target], axis=1) if args.target in current_df.columns else current_df
            current_df[args.prediction_column] = model.predict(features)
            print(f"Generated predictions into column '{args.prediction_column}'")

    metrics = [DataDriftPreset(), DataSummaryPreset()]
    if not args.skip_target_drift and args.target in current_df.columns and args.prediction_column in current_df.columns:
        metrics.insert(1, TargetDriftPreset())

    print(f"Building Evidently report with metrics: {[m.__class__.__name__ for m in metrics]}")
    report = Report(metrics=metrics)
    report_snapshot = report.run(reference_data=reference_df, current_data=current_df)
    report_snapshot.save_html(args.report_path)

    print(f"Saved Evidently drift report to: {args.report_path}")

    report_dict = report_snapshot.dict()
    for metric in report_dict.get('metrics', []):
        name = metric.get('metric')
        result = metric.get('result', {})
        print(f"Metric: {name}")
        for key, value in result.items():
            if key in ('dataset_drift', 'share_of_drifted_columns', 'drift_column_names'):
                print(f"  {key}: {value}")


if __name__ == '__main__':
    main()
