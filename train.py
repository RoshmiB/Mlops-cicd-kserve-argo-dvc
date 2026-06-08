import pandas as pd
import numpy as np
from sklearn.model_selection import RandomizedSearchCV, train_test_split
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OneHotEncoder
from sklearn.preprocessing import StandardScaler
from imblearn.over_sampling import SMOTE
from xgboost import XGBClassifier
from sklearn.metrics import classification_report, precision_score, recall_score, f1_score, accuracy_score, roc_auc_score
import pickle


#ignore warnings
import warnings
warnings.filterwarnings('ignore')


# Load the dataset
df = pd.read_excel('data/Telco_customer_churn.xlsx')
# print(df.head())
print(df.shape)
# pd.set_option('display.max_columns', None)
# print(df.columns)


# step 1: drop irrelevant columns and check for missing values and duplicates
# print("Check for missing values:")
# print(df.isnull().sum())
# print(df.isna().sum())
# print(df.info())
# print("Check for duplicates:")
# print(df.nunique())

# dropping CustomerID because it is a unique identifier and does not contribute to the predictive modeling.
# dropping Count because it is a sequential number that does not provide meaningful information for the model.
# dropping Country, State, City, Zip Code, Lat Long, Latitude, Longitude because they are location-based features that may not be relevant for predicting customer churn and could introduce noise into the model.
# dropping Churn Label, Churn Reason, Churn Score because they are target variables that can lead to data leakage if included in the training data, as they contain information about the outcome we are trying to predict (customer churn).

columns_to_drop = ['CustomerID', 'Count', 'Country', 'State', 'City', 'Zip Code', 'Lat Long',
                   'Latitude','Longitude','Churn Label', 'Churn Reason', 'Churn Score']
df_cleaned = df.drop(columns=columns_to_drop)
df_cleaned = df_cleaned.drop_duplicates()
# print("Shape of the cleaned dataset:", df_cleaned.shape)
# print("Description of the cleaned dataset:")
# print(df_cleaned.describe().T) # summerizing only the numerical features, do include="all" to include categorical features as well.

# step 2: Train-Test Split (80:20)
# Extracting features (X) and target (y)

X = df_cleaned.drop('Churn Value', axis=1) # axis=1 indicates that we are dropping a column, not a row
y = df_cleaned['Churn Value']
print(X.shape, y.shape)

# Before splitting the data, save the column names of X for future reference;
# as train_test_split converts the corresponding data into numpy arrays
X_colnames = X.columns
# print(X_colnames)


# Perform the train-test split 80:20
# stratify=y ensures that the class distribution in the target variable is preserved in both the training and testing sets.
# Used for small, imbalanced and classification datasets
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

# step-3 Handling Missing Values
# 'Total Charges' column has some missing or invalid values. Convert it to numeric and handle missing values.
print("Before handling missing values:")
print(X_train['Total Charges'].isnull().sum())
print(df_cleaned['Total Charges'].head())

# Convert 'Total Charges' to numeric, coercing invalid values to NaN
X_train['Total Charges'] = pd.to_numeric(X_train['Total Charges'], errors='coerce')
X_test['Total Charges'] = pd.to_numeric(X_test['Total Charges'], errors='coerce')
print("After converting 'Total Charges' to numeric:")
#show NAN values in 'Total Charges' column
print(X_train['Total Charges'].isnull().sum(),X_test['Total Charges'].isnull().sum())
print(X_train['Total Charges'].dtype, X_test['Total Charges'].dtype)
# Initialize the SimpleImputer with a strategy to fill missing values with the median
imputer = SimpleImputer(strategy='median')
# Fit the imputer on the training data and transform both training and test data
X_train['Total Charges'] = imputer.fit_transform(X_train[['Total Charges']]) # median of the train to fill the Nan Values
X_test['Total Charges'] = imputer.transform(X_test[['Total Charges']]) # median of the train to fill the Nan values [to aovid data leakage!]
print(X_train['Total Charges'].isnull().sum(), X_test['Total Charges'].isnull().sum())

# step-4 Removing Duplicates, move this part in cleaning above
# Removing any duplicate rows in both training and test sets
# X_train.drop_duplicates(inplace=True)
# X_test.drop_duplicates(inplace=True)

#step 5: Encode categorical variables
# use pd.get_dummies when you have a small number of categorical variables and OneHotEncoder when you have a large number 
# of categorical variables or when you want to avoid the dummy variable trap by dropping one category.
print(X_train.select_dtypes(include='object').T)
# Identify categorical columns
categorical_cols = X_train.select_dtypes(include='object').columns.tolist()
print("Categorical columns:", categorical_cols)
# Initialize the OneHotEncoder
# sparse_output=False gives a numpy array instead of a sparse matrix
# handle_unknown='ignore' prevents errors if test data has unseen categories
# drop='first' avoids the dummy variable trap by dropping the first category of each feature, which helps to reduce multicollinearity in the model.
encoder = OneHotEncoder(sparse_output=False, handle_unknown='ignore', drop='first')
# Fit the encoder on the training data and transform both training and test data
X_train_encoded = encoder.fit_transform(X_train[categorical_cols])
X_test_encoded = encoder.transform(X_test[categorical_cols])
#Get the new column names after encoding
encoded_colnames = encoder.get_feature_names_out(categorical_cols)
print("Encoded column names:", encoded_colnames)

# encoded_df = pd.DataFrame(X_train_encoded, columns=encoded_colnames)
#show the first few rows of the encoded dataframe

X_train_encoded_df = pd.DataFrame(
    X_train_encoded, 
    columns=encoded_colnames, 
    index=X_train.index
)

X_test_encoded_df = pd.DataFrame(
    X_test_encoded, 
    columns=encoded_colnames, 
    index=X_test.index
)

print(X_train_encoded_df.head().T)
print(X_train_encoded.shape, X_test_encoded.shape)


#step 6: Standardization - Feature scaling
# We are using StandardScaler to standardize the data. The StandardScaler transforms the features by scaling them to have 
# a mean of 0 and a standard deviation of 1. This ensures that all features contribute equally to the model, 
# regardless of their original scales. Standard deviation is simply the square root of the variance.

scaler = StandardScaler()
numerical_cols = X_train.select_dtypes(exclude='object').columns.tolist() 
# X_train_scaled = pd.DataFrame(scaler.fit_transform(X_train[numerical_cols]), columns=numerical_cols)
# X_test_scaled = pd.DataFrame(scaler.transform(X_test[numerical_cols]), columns=numerical_cols)

# Scale only the continuous numerical features
X_train_scaled_num = pd.DataFrame(
    scaler.fit_transform(X_train[numerical_cols]), 
    columns=numerical_cols, 
    index=X_train.index
)

X_test_scaled_num = pd.DataFrame(
    scaler.transform(X_test[numerical_cols]), 
    columns=numerical_cols, 
    index=X_test.index
)

# ==========================================
# STEP 7: CONCATENATE TO CREATE FINAL DATASETS
# ==========================================
X_train_final = pd.concat([X_train_scaled_num, X_train_encoded_df], axis=1)
X_test_final = pd.concat([X_test_scaled_num, X_test_encoded_df], axis=1)

print("Final Training Data Shape:", X_train_final.shape)
print(X_train_final.head().T)

print("\nFirst Few Rows of Training Target:")
print(y_train.head())

#step 8: Analyze the Dataset to Show Class Imbalance

# Analyzing the distribution of churners (1) vs. non-churners (0) in the training set
churn_distribution = y_train.value_counts()

# Display the class distribution
print("\nClass Distribution in the Training Set:")
print(churn_distribution)

# Calculating the percentage of each class
churn_percentage = (churn_distribution / len(y_train)) * 100
print("\nPercentage Distribution of Churn vs. Non-Churn:")
print(churn_percentage)

# From the output, we can see that only 27% of his customers churn, while 73% remain loyal. 
# This imbalance could cause a model that predicts everyone as non-churners to have a seemingly high accuracy, 
# even though it's not truly useful for identifying churners.
#This imbalance could potentially skew the results, particularly if accuracy is used as the primary performance metric. 
# A high accuracy score might appear favorable, but it could be misleading if the model predominantly predicts customers as non-churners.

# step 9: Apply SMOTE to the training data to handle class imbalance
# print('Before:', y_train.value_counts())
# smote = SMOTE(random_state=42)
# X_train_smote, y_train_smote = smote.fit_resample(X_train_final, y_train)
# print('After:', np.unique(y_train_smote, return_counts = True))

# step 9: Calculate scale_pos_weight for XGBoost to handle class imbalance
neg_count = (y_train == 0).sum()
pos_count = (y_train == 1).sum()
scale_pos_weight = neg_count / pos_count
print(f"Negative samples: {neg_count}, Positive samples: {pos_count}")
print(f"Calculated scale_pos_weight: {scale_pos_weight:.2f}")

# step 10: Define the hyperparameter grid for XGBoost
param_dist = {
    'n_estimators': [50, 100, 200, 300],                 # Number of trees
    'learning_rate': [0.01, 0.05, 0.1, 0.2],              # Learning rate
    'max_depth': [3, 4, 5, 6],                          # Maximum depth of each tree
    'min_child_weight': [1, 3, 5, 7],                       # Minimum sum of instance weight (hessian) needed in a child
    'subsample': [0.7, 0.8, 0.9, 1.0],                        # Subsample ratio of the training instance
    'colsample_bytree': [0.6, 0.7, 0.8, 1.0],            # Subsample ratio of columns when constructing each tree
    'gamma': [0, 0.1, 0.2, 0.4],                          # Minimum loss reduction required to make a further partition on a leaf node
    'scale_pos_weight': [scale_pos_weight, scale_pos_weight * 0.8, scale_pos_weight * 1.2]              # Handle class imbalance
}

# step 11: Initialize the XGBoost model
xgb_model = XGBClassifier(random_state=42, use_label_encoder=False, eval_metric='logloss')

# step 12: Set up RandomizedSearchCV
random_search = RandomizedSearchCV(estimator=xgb_model, param_distributions=param_dist,
                                   n_iter=20, scoring='recall', cv=5, verbose=1, n_jobs=-1, random_state=42)

# step 13: Fit RandomizedSearchCV on the SMOTEd training data
#Fit and extract best estimator using clean training data without SMOTE, as XGBoost can handle class imbalance using the scale_pos_weight parameter.
random_search.fit(X_train_final, y_train)

# step 14: Get the best parameters and best estimator
best_params = random_search.best_params_
best_xgb_model = random_search.best_estimator_

print("\n--- Tuning Complete ---")
print(f"Best Hyperparameters: {best_params}")
print(f"Best Recall Score (from training set): {random_search.best_score_:.4f}")

# step 15: Make predictions on the test set using the best model
y_pred_xgb_best = best_xgb_model.predict_proba(X_test_final)[:, 1]
# Adjust threshold manually to find the sweet spot
custom_threshold = 0.5 # You can experiment with different thresholds (e.g., 0.5, 0.6, 0.7) to see how it affects precision and recall  
y_pred_custom = (y_pred_xgb_best >= custom_threshold).astype(int)

# step 16: Calculate Precision, Recall, and F1 Score for the best model
precision_xgb_best = precision_score(y_test, y_pred_custom)
recall_xgb_best = recall_score(y_test, y_pred_custom)
f1_xgb_best = f1_score(y_test, y_pred_custom)

# step 17: Print the evaluation metrics
print(f"Best Model Precision after Randomized Search cross-validation: {precision_xgb_best:.4f}")
print(f"Best Model Recall after Randomized Search cross-validation: {recall_xgb_best:.4f}")
print(f"Best Model F1 Score after Randomized Search cross-validation: {f1_xgb_best:.4f}")

print("\nDetailed Classification Report:")
print(classification_report(y_test, y_pred_custom, target_names=['Non-Churner (0))]', 'Churner (1)']))

accuracy = accuracy_score(y_test, y_pred_custom)
auc = roc_auc_score(y_test, y_pred_custom)

print(f"Accuracy: {accuracy:.4f}")
print(f"AUC-ROC: {auc:.4f}")

# Save model and preprocessing artifacts
artifacts = {
    'model': best_xgb_model,
    'encoder': encoder,
    'scaler': scaler,
    'numerical_cols': numerical_cols,
    'categorical_cols': categorical_cols,
}

with open('models/churn_model.pkl', 'wb') as f:
    pickle.dump(artifacts, f)

print("Model artifacts saved to models/churn_model.pkl")
