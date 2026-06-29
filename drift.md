## Yes — train3_mlflow_evidently_drift.py covers both drift types

### What it checks

1. **Data drift**
   - `reference_df` = training data (`X_train` + `y_train`)
   - `current_df` = default test split (`X_test` + `y_test`), or `--current-csv` if provided
   - The script runs:
     - `DataDriftPreset()`
     - `DataSummaryPreset()`
   - This compares feature distributions between reference and current datasets.

2. **Target drift**
   - It inserts `TargetDriftPreset()` when the current data contains both:
     - the true target column (`loan_status`)
     - plus a `prediction` column
   - If a model is available, it generates `prediction` for the current dataset
   - Then Evidently compares target/prediction distributions between reference and current

### Easy explanation

- Think of `reference_df` as “what the model was trained on”
- And `current_df` as “what the model is seeing now”
- If `current_df` is the test split, this is a validation-style drift check
- If `current_df` comes from real production input, this becomes a production drift check

### How the script decides what to report

- Always runs:
  - `DataDriftPreset()` → detects changes in feature distributions
  - `DataSummaryPreset()` → summary of dataset stats
- Also runs:
  - `TargetDriftPreset()` → only when the current data has predictions and true labels

### Why it is useful

- `DataDriftPreset()` answers:
  - “Have the input features shifted?”
- `TargetDriftPreset()` answers:
  - “Has the target/prediction behavior shifted?”

### What to remember

- If you use the default test split, you are checking drift between training and test data
- If you provide a real `--current-csv`, you are checking drift against actual new data
- The script logs both HTML report and numeric drift metrics into MLflow

If you want, I can also summarize exactly which lines of code correspond to each drift check.


Reviewing the script sections that perform data and target drift so the explanation is precise.

Read [](file:///Users/rajaguru/Documents/interview_prep/Mlops-cicd-kserve-argo-dvc/train3_mlflow_evidently_drift.py#60-60), lines 60 to 170

Read [](file:///Users/rajaguru/Documents/interview_prep/Mlops-cicd-kserve-argo-dvc/train3_mlflow_evidently_drift.py#170-170), lines 170 to 246

## Yes — this file checks both kinds of drift

### 1. Data drift
This is always checked.

- `reference_df = X_train.copy(); reference_df[args.target] = y_train`
  - training data becomes the reference dataset
- `current_df = X_test.copy(); current_df[args.target] = y_test`
  - by default, the test split is the “current” dataset
- If you pass `--current-csv`, then `current_df` is loaded from that file instead

Then the script creates:
- `DataDriftPreset()`
- `DataSummaryPreset()`

And runs:
- `drift_report = Report(metrics=report_metrics)`
- `report_snapshot = drift_report.run(reference_data=reference_df, current_data=current_df)`

That is the core data drift check: Evedently compares the reference feature distributions with the current feature distributions.

---

### 2. Target drift
This is checked only when the current data has a prediction column.

The code does:
- `if 'prediction' not in current_df.columns: current_df['prediction'] = best_pipeline.predict(...)`

Then it builds the metric list:
- `report_metrics = [DataDriftPreset(), DataSummaryPreset()]`
- `if args.target in current_df.columns: report_metrics.insert(1, TargetDriftPreset())`

So if the current dataset includes the true target (`loan_status`) and predictions, Evidently also runs:
- `TargetDriftPreset()`

That compares the target/prediction relationship between reference and current data.

---

### Easy summary

- `DataDriftPreset()` = “Did input features shift?”
- `TargetDriftPreset()` = “Did the model’s target/prediction behavior shift?”
- `DataSummaryPreset()` = “What are the dataset statistics?”

---

### What this means practically

- With no `--current-csv`, you are checking drift between training data and test split.
- With `--current-csv`, you are checking drift against new real data.
- A `prediction` column is generated automatically if needed, so target drift can be computed without extra input.

---

### Key lines in the file
- `current_df = load_current_data(args.current_csv, args.target)` → optional current dataset
- `current_df['prediction'] = best_pipeline.predict(...)` → create predictions
- `report_metrics.insert(1, TargetDriftPreset())` → enable target drift
- `drift_report.run(reference_data=reference_df, current_data=current_df)` → run the drift check
- metric extraction loop logs:
  - `DatasetDriftMetric`
  - `TargetDriftMetric`

If you want, I can also show a diagram of `reference_df` vs `current_df` and exactly how the report output maps to those drift checks.






please explain line by line here once what we are doing , how we are checking the drift what is reference and current prediction? :- 
target = 'cnt'
prediction = 'prediction'
numerical_features = ['temp', 'atemp', 'hum', 'windspeed', 'hr', 'weekday']
categorical_features = ['season', 'holiday', 'workingday'] 
reference = raw_data.loc['2011-01-01 00:00:00':'2011-01-28 23:00:00']
current = raw_data.loc['2011-01-29 00:00:00':'2011-02-28 23:00:00'] regressor = ensemble.RandomForestRegressor(random_state = 0, n_estimators = 50) 
regressor.fit(reference[numerical_features + categorical_features], reference[target]) 
ref_prediction = regressor.predict(reference[numerical_features + categorical_features])
current_prediction = regressor.predict(current[numerical_features + categorical_features]) reference['prediction'] = ref_prediction
current['prediction'] = current_prediction column_mapping = ColumnMapping()

column_mapping.target = target
column_mapping.prediction = prediction
column_mapping.numerical_features = numerical_features
column_mapping.categorical_features = categorical_features regression_perfomance = Report(metrics=[RegressionPreset()])
regression_perfomance.run(current_data=reference, reference_data=None, column_mapping=column_mapping) regression_perfomance.show()

Optimized tool selection

Here is what each line does, and how “reference” / “current” are used.

target = 'cnt'
prediction = 'prediction'
numerical_features = ['temp', 'atemp', 'hum', 'windspeed', 'hr', 'weekday']
categorical_features = ['season', 'holiday', 'workingday']

target is the name of the true value we want to predict. In this dataset, cnt is the real count.
prediction is the column name we will use to store model predictions.
numerical_features are the numeric input columns used by the model.
categorical_features are the categorical input columns used by the model.

reference = raw_data.loc['2011-01-01 00:00:00':'2011-01-28 23:00:00']
current = raw_data.loc['2011-01-29 00:00:00':'2011-02-28 23:00:00']

reference is the older historical period. It is the data used to train the model and to establish the “baseline.”
current is the more recent period. It is the data we want to compare against the baseline to see if performance or data distribution has changed.
So:

reference = baseline / training period
current = new period / evaluation period

regressor = ensemble.RandomForestRegressor(random_state=0, n_estimators=50)
regressor.fit(reference[numerical_features + categorical_features], reference[target])

 This creates a random forest regression model.
It fits the model on reference data using the selected numerical + categorical features.
The model learns to predict cnt from those features.

ref_prediction = regressor.predict(reference[numerical_features + categorical_features])
current_prediction = regressor.predict(current[numerical_features + categorical_features])

ref_prediction is the model’s prediction on the reference dataset.
current_prediction is the same model’s prediction on the current dataset.
So:

reference prediction = how well the model predicts its own training/baseline data
current prediction = how well the model predicts the later/new data

reference['prediction'] = ref_prediction
current['prediction'] = current_prediction

These lines add a prediction column to each dataset.
reference now contains both actual cnt and predicted values for the reference period.
current now contains actual cnt and predicted values for the current period.

column_mapping = ColumnMapping()
column_mapping.target = target
column_mapping.prediction = prediction
column_mapping.numerical_features = numerical_features
column_mapping.categorical_features = categorical_features

column_mapping tells Evidently which columns are the target, prediction, numeric features, and categorical features.
This is required for its report to know how to interpret the dataset.

regression_perfomance = Report(metrics=[RegressionPreset()])
regression_perfomance.run(current_data=reference, reference_data=None, column_mapping=column_mapping)
regression_perfomance.show()

RegressionPreset() is a built-in Evidently report metric set for regression tasks.
Report(...) builds a report object configured to compute regression metrics and drift checks.
run(...) executes the report.
Here the code uses:

current_data=reference
reference_data=None
That means the report is using the reference dataset as current data, and no explicit reference dataset is provided.

Important note
If your goal is to check drift between two periods, the usual pattern is:

regression_perfomance.run(current_data=current, reference_data=reference, column_mapping=column_mapping)

That way:

reference_data = old/baseline period
current_data = new/recent period
Then Evidently can compare distributions, prediction performance, and drift between the two periods.

So what is “reference” vs “current prediction”?
reference prediction: model outputs on the baseline training period
current prediction: model outputs on the newer evaluation period
reference dataset = old baseline data used to train the model
current dataset = newer data used to detect drift or performance degradation

What drift is being checked?
With RegressionPreset(), Evidently typically checks:

prediction drift
feature drift
target drift
regression performance change
But only if both reference_data and current_data are provided correctly.

Summary
You train a model on reference.
You predict on both reference and current.
You tell Evidently which columns are what.
Then you run the report to compare baseline vs recent behavior.
If you want, I can also rewrite the snippet correctly for drift checking with Evidently.





Yes — this is a good pattern for checking data drift with Evidently in train3_mlflow_evidently.py.

What your code is doing
reference_df = X_train.copy(); reference_df[args.target] = y_train
This makes the training data the “reference” dataset.
current_df = X_test.copy(); current_df[args.target] = y_test
This makes the test data the “current” dataset.
drift_report = Report(metrics=[DataDriftPreset(), DataSummaryPreset()])
DataDriftPreset() checks for feature distribution drift between reference and current.
DataSummaryPreset() summarizes data characteristics for both datasets.
report_snapshot = drift_report.run(reference_data=reference_df, current_data=current_df)
This compares the two datasets and computes drift metrics.
report_snapshot.save_html(...) and mlflow.log_artifact(...)
Saves the interactive report and logs it to MLflow.
So yes, you can do this

Your implementation is valid for checking drift between the training split and the test split.

Important caveat
X_test / y_test is not real production data.
It only shows whether the test split distribution differs from the training split.
That is useful for validation, but not the same as production drift.
If you want true data drift monitoring
Use:

reference_data = old/training data
current_data = newly arrived production data
For example:

reference_df = historical data from last month
current_df = new data from today/this week
Then DataDriftPreset() will tell you whether the feature distributions have shifted.

If you want model performance drift too
Your current setup only does data drift. If you want prediction/performance drift, use:

RegressionPreset() for regression
ClassificationPreset() or TargetDriftPreset() for classification
And supply a prediction column if needed
Recommendation
Your code is fine for a drift check pattern. If you want, I can help you modify it to:

use actual production/current data,
add prediction columns,
switch to DataDriftPreset() + TargetDriftPreset() or RegressionPreset() for a more complete drift/performance report.


✅ Created new file: train3_mlflow_evidently_drift.py

What it includes
MLflow training and evaluation for XGBoost
Evidently DataDriftPreset, TargetDriftPreset, and DataSummaryPreset
support for:
--csv as reference data
optional --current-csv for actual current/production data
fallback to test split when current data is not provided
HTML drift report saved and logged to MLflow
extracted drift metrics logged as MLflow metrics
Usage
Run locally like:

python train3_mlflow_evidently_drift.py --csv data/loans.csv

Or with a current dataset:

python train3_mlflow_evidently_drift.py --csv data/loans.csv --current-csv data/current_loans.csv


If you want, I can also add a second file that only generates drift reports without retraining.

yes please

Creating a second standalone drift-only script now.

✅ Created a second script: evidently_drift_only.py

What it does
loads --reference-csv and --current-csv
preprocesses both datasets
optionally loads a saved model to generate prediction
generates an Evidently report with:
DataDriftPreset
DataSummaryPreset
optional TargetDriftPreset
saves HTML report to --report-path
prints extracted drift summary values
Example usage

python evidently_drift_only.py --reference-csv data/loans.csv --current-csv data/current_loans.csv
If you want next
I can also add:

a README usage section
a version using mlflow.models.load_model(...)
a validation step to align current data columns with reference data before report generation









