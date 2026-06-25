import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    classification_report,
    confusion_matrix
)
from sklearn.model_selection import GridSearchCV, RandomizedSearchCV, StratifiedKFold, train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.preprocessing import MinMaxScaler
from imblearn.over_sampling import SMOTE
from xgboost import XGBClassifier
from imblearn.pipeline import Pipeline
from catboost import CatBoostClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    classification_report,
    confusion_matrix
)


warnings.filterwarnings('ignore')

#**********************************************
# Dataset Overview
#**********************************************

df = pd.read_csv('data/loans.csv')
pd.set_option('display.max_columns', None)
print (df.head())

print (df.info()) # emp_length and revol_util have null values
print (df.describe().T) 
print (df.shape) # 38770 rows and 23 columns

print (df['emp_length'].value_counts())
print (df['revol_util'].value_counts())
print (df['pub_rec'].value_counts())
print (df['delinq_2yrs'].value_counts())

#**********************************************
# Data loading and pre-processing
#**********************************************

df['revol_bal_to_income'] = \
df['revol_bal']/df['annual_inc']

df['inq_to_acc_ratio']=\
df['inq_last_6mths']/(df['open_acc']+1)

df.drop(['id', 'member_id','delinq_2yrs','pub_rec','grade','last_pymnt_amnt', 'installment'], axis=1, inplace=True)

# drop the rows with null values in  revol_util columns
df.dropna(subset=['revol_util'], inplace=True)

# for 'emp_length', we will replace '< 1 year' with 0 and '10+ years' with 10, and then convert the column to integer
# 'emp_length' (remove the 'years' string and convert to integer) 

df['emp_length'] = df['emp_length'].replace({'< 1 year': '0', '10+ years': '10'})
df['emp_length'] = df['emp_length'].astype(str).str.replace(' years', '', regex=False)
df['emp_length'] = pd.to_numeric(df['emp_length'], errors='coerce')

# impute the median value of the 'emp_length' column and fill the null values with the median value
median_emp_length = df['emp_length'].median()
print(f'Median value of emp_length: {median_emp_length}')
df['emp_length'] = df['emp_length'].fillna(median_emp_length).astype(int)

# 'term' (remove the 'months' string and convert to integer)
df['term'] = df['term'].astype(str).str.replace(' months', '', regex=False).astype(int)

# remove % from 'revol_util', 'int_rate' and convert to float
df['revol_util'] = df['revol_util'].astype(str).str.rstrip('%').astype(float) / 100.0
df['int_rate'] = df['int_rate'].astype(str).str.rstrip('%').astype(float) / 100.0


# check loan_staus with purpose and home_ownership columns to see if there is any relationship between them using plots
plt.figure(figsize=(12, 10))  
sns.countplot(
    y='purpose',              
    hue='loan_status', 
    data=df,            
    palette='viridis',
    order=df['purpose'].value_counts().index # Sorts from most common to least common
)
plt.title('Loan Status Distribution Across Loan Purposes')
plt.xlabel('Count of Loans')
plt.ylabel('Loan Purpose')
plt.legend(title='Loan Status', loc='lower right')
plt.tight_layout()
plt.show()

plt.figure(figsize=(12, 6))
sns.countplot(x='home_ownership', hue='loan_status', data=df)
plt.title('Loan Status by Home Ownership')
plt.show()

# for purpose,home_ownership,verification_status,'sub_grade' we will do one-hot encoding and drop the original column
df = pd.get_dummies(df, columns=['purpose', 'home_ownership', 'verification_status'], drop_first=True)

# do label encoding for 'sub_grade' and 'loan_status' columns
le = LabelEncoder()
df['sub_grade'] = le.fit_transform(df['sub_grade'].astype(str))
print(le.classes_)

print(df['loan_status'].unique())
df['loan_status'] = df['loan_status'].map({
    'Fully Paid':0,
    'Charged Off':1
})
print(df['loan_status'].value_counts())

#  checking for outliers in the loan_amnt and  annual_inc columns using the IQR method to detect and remove outliers  
#  also visualizing the distribution using boxplots

# with_outliner_cols = ['loan_amnt', 'annual_inc']

# for col in with_outliner_cols:
#     plt.figure(figsize=(8, 6))
#     sns.boxplot(x=df[col])
#     plt.title(f'Boxplot of {col}')
#     plt.show()
    
# Q1 = df[with_outliner_cols].quantile(0.25)
# Q3 = df[with_outliner_cols].quantile(0.75)
# IQR = Q3 - Q1

# df_clean = df[((df[with_outliner_cols] >= (Q1 - 1.5 * IQR)) & (df[with_outliner_cols] <= (Q3 + 1.5 * IQR))).all(axis=1)].copy() # .copy() is used to avoid SettingWithCopyWarning when we will do feature engineering later
# # no of outlines removed
# print(f'Number of outliers removed: {df.shape[0] - df_clean.shape[0]}')

df_clean = df.copy()

skewed_cols = [
    'annual_inc',
    'loan_amnt',
    'revol_bal'
]

for col in skewed_cols:

    df_clean[col] = np.log1p(df_clean[col])

print(df_clean[skewed_cols].describe())

print (df_clean.head())

#**********************************************
# EDA (Exploratory Data Analysis)
#**********************************************

# create a correlation heatmap to visualize the relationships between the features
plt.figure(figsize=(12, 10))
sns.heatmap(df_clean.select_dtypes(include=[np.number]).corr(), annot=True, cmap='coolwarm', fmt='.2f')
plt.title('Correlation Heatmap')
plt.show()

# 'sub_grade' has a strong corrrelation with 'int_rate' so we will drop the 'sub_grade' column to avoid multicollinearity
df_clean.drop(['sub_grade'], axis=1, inplace=True, errors='ignore')

# create a plot to visualize the distribution of the target variable, 
# class imbalance is present in the dataset, so we need to handle it during model training
plt.figure(figsize=(8, 6))
sns.countplot(x='loan_status', data=df_clean, palette='pastel')
plt.title('Distribution of Loan Status')
plt.show()

# create boxplots and kde plots to visualize the distribution of 'dti' by 'loan_status' 
fig, axes = plt.subplots(1, 2, figsize=(14, 5))
sns.boxplot(ax=axes[0], x='loan_status', y='dti', data=df_clean, palette='pastel')
axes[0].set_title('Debt-to-Income (DTI) by Loan Status')

sns.kdeplot(ax=axes[1],data=df_clean, x='dti', hue='loan_status', common_norm=False, shade=True)
axes[1].set_title('Distribution of Debt-to-Income Ratio by Loan Status')
plt.show()

# create a new feature 'loan_to_income_ratio' by dividing 'loan_amnt' by 'annual_inc' to see if it has any relationship with the target variable
df_clean['loan_to_income_ratio'] = df_clean['loan_amnt'] / df_clean ['annual_inc'] + 1e-6 # add a small value to avoid division by zero

fig, axes = plt.subplots(1, 2, figsize=(14, 5))
sns.boxplot(ax=axes[0], x='loan_status', y='loan_to_income_ratio', data=df_clean, palette='pastel')
axes[0].set_title('Loan-to-Income Ratio by Loan Status')

sns.kdeplot(ax=axes[1],data=df_clean, x='loan_to_income_ratio', hue='loan_status', common_norm=False, shade=True)
axes[1].set_title('Distribution of Loan-to-Income Ratio by Loan Status')
plt.show()

print(df_clean.head())

df_clean['revol_per_account']=\
df_clean['revol_bal']/(df_clean['open_acc']+1)

df_clean['interest_burden']=\
df_clean['loan_amnt']*df_clean['int_rate']/(df_clean['annual_inc']+1)

df_clean['dti_interest']=\
df_clean['dti']*df_clean['int_rate']


# #**********************************************
# 4. MODEL SELECTION
#**********************************************

print(df_clean.columns.tolist())



X = df_clean.drop(['loan_status'], axis=1)
y=df_clean['loan_status']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)




# handle class imbalance using SMOTE (Synthetic Minority Over-sampling Technique) to generate synthetic samples for the minority class in the training set
# smote = SMOTE(random_state=42, sampling_strategy=0.4)
# X_train_balanced, y_train_balanced = smote.fit_resample(X_train, y_train)
# print(f"Original training shape: {y_train.value_counts()}")
# print(f"Balanced training shape: {y_train_balanced.value_counts()}")


# # Initialize baseline model evaluation
# xgb_model = XGBClassifier(
#     random_state=42, 
#     scale_pos_weight=1, 
#     eval_metric='logloss',

# )

pipeline = Pipeline([

('smote',

SMOTE(
sampling_strategy=0.5,
random_state=42
)),

('xgb',

XGBClassifier(
random_state=42,
eval_metric='auc',
tree_method='hist'
))

])


# xgb_model.fit(X_train_balanced, y_train_balanced)
# print("\nBaseline Model Selected and Trained.")


#**********************************************
# 5. HPP TUNING (HYPERPARAMETER TUNING)
#**********************************************

param_grid = {
    'xgb__max_depth': [2, 3, 4, 5],
    'xgb__gamma': [0, 0.1, 0.3, 0.5, 1],
    'xgb__learning_rate': [0.01, 0.05, 0.1],
    'xgb__n_estimators': [100, 200, 300],
    'xgb__subsample': [0.6, 0.8, 1.0],
    'xgb__colsample_bytree': [0.6, 0.8, 1.0],
    'xgb__scale_pos_weight': [1, 2, 3, 4, 5]
}

cv_strategy = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

print("\nStarting Cost-Sensitive XGBoost Tuning via RandomizedSearchCV...")
random_search = RandomizedSearchCV(
    estimator=pipeline, 
    param_distributions=param_grid,
    cv=cv_strategy, 
    scoring='roc_auc', 
    n_iter=30,
    n_jobs=-1, 
    verbose=1,
    random_state=42
)

# Fit directly on the original clean training sets
random_search.fit(X_train, y_train)
best_xgb = random_search.best_estimator_

print(f"Best Parameters Found: {random_search.best_params_}")

importance = pd.DataFrame({

'Feature':X_train.columns,

'Importance':

best_xgb.named_steps['xgb']

.feature_importances_

})


print(

importance

.sort_values(

'Importance',

ascending=False

)

.head(20)

)


#**********************************************
# 6. MODEL EVALUATION
#**********************************************

y_prob_default = best_xgb.predict_proba(X_test)[:, 1]

# Apply a conservative operational threshold
# If chance of default > 15%, classify as Default (1)



thresholds=[

0.15,

0.2,

0.25,

0.3,

0.35,

0.4

]


for t in thresholds:

    y_pred=(

        y_prob_default>t

    ).astype(int)


    print(

    f"\nThreshold={t}"

    )


    print(

    confusion_matrix(

    y_test,

    y_pred

    )

    )


    print(

    classification_report(

    y_test,

    y_pred,

    target_names=

    [

    'Safe',

    'Default'

    ]

    )

    )


from sklearn.metrics import roc_curve


fpr,tpr,_=roc_curve(

y_test,

y_prob_default

)


plt.figure(figsize=(8,6))

plt.plot(

fpr,

tpr

)

plt.plot(

[0,1],

[0,1],

'--'

)

plt.xlabel("False Positive Rate")

plt.ylabel("True Positive Rate")

plt.title("ROC Curve")

plt.show()

# custom_threshold = 0.3
# y_pred_adjusted = np.where(y_prob_default > custom_threshold, 1, 0)

# print("\n=== Optimized Confusion Matrix ===")
# # Structure: [[True Safe, False Default], [False Safe, True Default]]
# print(confusion_matrix(y_test, y_pred_adjusted))

# print("\n=== Optimized Classification Report ===")
# print(classification_report(y_test, y_pred_adjusted, target_names=['Safe (0)', 'Default (1)']))

# print("\n=== ROC-AUC Score ===")
# print(f"{roc_auc_score(y_test, y_prob_default):.4f}")


# Model evaluation metrics for different thresholds

# results=[]

# def evaluate_model(name, model, X_train, y_train, X_test, y_test, threshold=0.25):

#     model.fit(X_train,y_train)

#     y_prob=model.predict_proba(X_test)[:,1]

#     y_pred=np.where(y_prob>=threshold,1,0)

#     acc=accuracy_score(y_test,y_pred)

#     precision=precision_score(y_test,y_pred)

#     recall=recall_score(y_test,y_pred)

#     f1=f1_score(y_test,y_pred)

#     auc=roc_auc_score(y_test,y_prob)

#     results.append({

#         'Model':name,

#         'Accuracy':round(acc,3),

#         'Precision(Default)':round(precision,3),

#         'Recall(Default)':round(recall,3),

#         'F1(Default)':round(f1,3),

#         'ROC_AUC':round(auc,3)

#     })

#     print("\n"+"="*50)

#     print(name)

#     print("="*50)

#     print("\nConfusion Matrix")

#     print(confusion_matrix(y_test,y_pred))

#     print("\nClassification Report")

#     print(classification_report(

#         y_test,

#         y_pred,

#         target_names=['Safe','Default']

#     ))



# xgb_model = XGBClassifier(

#     random_state=42,

#     n_estimators=200,

#     max_depth=5,

#     learning_rate=0.05,

#     subsample=0.8,

#     colsample_bytree=0.8,

#     gamma=1,

#     scale_pos_weight=1,

#     eval_metric='logloss'
# )

# evaluate_model(

#     'XGBoost',

#     xgb_model,

#     X_train_balanced,

#     y_train_balanced,

#     X_test,

#     y_test,

#     threshold=0.25
# )

# rf_model=RandomForestClassifier(

#     n_estimators=300,

#     max_depth=10,

#     min_samples_split=10,

#     min_samples_leaf=5,

#     class_weight='balanced',

#     random_state=42,

#     n_jobs=-1

# )

# evaluate_model(

#     'Random Forest',

#     rf_model,

#     X_train_balanced,

#     y_train_balanced,

#     X_test,

#     y_test,

#     threshold=0.25

# )

# cat_model=CatBoostClassifier(

#     iterations=300,

#     depth=5,

#     learning_rate=0.05,

#     loss_function='Logloss',

#     eval_metric='AUC',

#     random_seed=42,

#     verbose=False

# )

# evaluate_model(

#     'CatBoost',

#     cat_model,

#     X_train_balanced,

#     y_train_balanced,

#     X_test,

#     y_test,

#     threshold=0.25

# )

# comparison=pd.DataFrame(results)

# comparison=comparison.sort_values(

#     by='ROC_AUC',

#     ascending=False

# )

# print("\nModel Comparison")

# print(comparison)


# from sklearn.metrics import roc_curve

# plt.figure(figsize=(8,6))

# for name,model in [

#     ('XGBoost',xgb_model),

#     ('Random Forest',rf_model),

#     ('CatBoost',cat_model)

# ]:

#     y_prob=model.predict_proba(X_test)[:,1]

#     fpr,tpr,_=roc_curve(y_test,y_prob)

#     auc=roc_auc_score(y_test,y_prob)

#     plt.plot(

#         fpr,

#         tpr,

#         label=f'{name} AUC={auc:.3f}'

#     )


# plt.plot(

#     [0,1],

#     [0,1],

#     linestyle='--'

# )

# plt.xlabel("False Positive Rate")

# plt.ylabel("True Positive Rate")

# plt.title("ROC Curve Comparison")

# plt.legend()

# plt.show()
