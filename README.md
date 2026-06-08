# MLOps CI/CD KServe Argo DVC

## Overview

This project is a small ML workflow repository for practicing MLOps concepts such as CI/CD, model training, deployment, and reproducible data pipelines.

## Project Files

| File | Purpose |
| --- | --- |
| `train.py` | Trains the model and generates artifacts |
| `api.py` | Exposes the trained model as an API |
| `requirements.txt` | Python dependencies |
| `data/` | Input dataset and related artifacts |
| `README.md` | Project documentation |

## Quick Start

| Step | Command |
| --- | --- |
| Create a virtual environment | `python3 -m venv .venv` |
| Activate the environment | `source .venv/bin/activate` |
| Install dependencies | `pip install -r requirements.txt` |
| Run training | `python3 train.py` |
1> to deactivate :- conda deactivate or deactivate
2> 


# Notes

- Use `fit_transform()` only on training data.
- Use `transform()` on validation, test, or production data.
- Keep the workflow reproducible by pinning dependencies in `requirements.txt`.

## Training and Inference Flow

1. Prepare the dataset in `data/`
2. Run `python3 train.py`
3. Use `api.py` for serving the model

## `fit_transform()` vs `transform()`

| Method | What it does | Use on | Why |
| --- | --- | --- | --- |
| `fit_transform()` | Learns parameters and transforms the data in one step | Training data | Establishes the rules from training data only |
| `transform()` | Applies previously learned parameters without refitting | Test data or new data | Prevents data leakage and keeps evaluation realistic |

Why Misusing Them Causes Data Leakage
Imagine you are scaling test scores between 0 and 100 using a Min-Max Scaler.
Your Training Set has scores ranging from 50 to 90.
Your Test Set has scores ranging from 60 to 100.
The Correct Approach (Using transform on Test)You run scaler.fit_transform(X_train). 
The scaler learns that the training minimum is 50 and the maximum is 90. It scales the training data based on those boundaries.You run scaler.transform(X_test). The scaler uses the training rules (Min=50, Max=90). A test score of 100 will scale to a value above 1.0. This is correct because, in the real world, your model wouldn't know a score of 100 was possible yet.
The Wrong Approach (Using fit_transform on Test)If you accidentally run scaler.fit_transform(X_test), the scaler wipes its memory of the training data. It recalculates a new minimum (60) and maximum (100) based on the test set.This introduces Data Leakage. Your test data predictions are now biased by information the model should not know, leading to overly optimistic test scores that will fail in production.

## Data Leakage Example

| Scenario | Outcome |
| --- | --- |
| `scaler.fit_transform(X_train)` followed by `scaler.transform(X_test)` | Correct and safe |
| `scaler.fit_transform(X_test)` | Incorrect because it leaks test-set information into preprocessing |

## Recommended Python Example

```python
from sklearn.preprocessing import StandardScaler
scaler = StandardScaler()
# Fit on training data
X_train_scaled = scaler.fit_transform(X_train)
# Apply the learned scaling to test data
X_test_scaled = scaler.transform(X_test)
```

## One hot Encoding
handle_unknown='ignore': 
If your X_test set contains a category that wasn't present in X_train (e.g., a new country or a rare sentiment word), this setting prevents your code from crashing. It will safely assign all zeros to that unknown category.
sparse_output=False: 
By default, OneHotEncoder returns a compressed sparse matrix to save memory. Setting this to False returns a standard NumPy array, making it easy to convert back into a readable Pandas DataFrame.

