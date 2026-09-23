# Databricks notebook source

# COMMAND ----------

# MAGIC %md
# MAGIC # Model Training Notebook
# MAGIC
# MAGIC This notebook trains a model on the feature table and registers it to Unity Catalog with the `@challenger` alias.
# MAGIC
# MAGIC **TODO:** Adapt this notebook to your algorithm, features, target, and metrics.

# COMMAND ----------

# Install dependencies
%pip install -r ../../requirements.txt
dbutils.library.restartPython()

# COMMAND ----------

# Define widgets for parameterization
dbutils.widgets.text("catalog_name", "mlops_quickstart_dev")
dbutils.widgets.text("schema_name", "iris")
dbutils.widgets.text("model_version", "1")

catalog_name = dbutils.widgets.get("catalog_name")
schema_name = dbutils.widgets.get("schema_name")
model_version = dbutils.widgets.get("model_version")

print(f"Catalog: {catalog_name}")
print(f"Schema: {schema_name}")
print(f"Model version: {model_version}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1: Set up MLflow experiment
# MAGIC
# MAGIC Use a user-scoped experiment to avoid collisions during development.

# COMMAND ----------

import mlflow
import mlflow.sklearn

# Get current user
username = spark.sql("SELECT current_user()").collect()[0][0].split("@")[0]

# Set experiment to user-scoped path to avoid collisions
# TODO: Change "iris_model" to your model name
experiment_path = f"/{username}/iris_model_{catalog_name}"
mlflow.set_experiment(experiment_path)

print(f"MLflow experiment: {experiment_path}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: Load feature table
# MAGIC
# MAGIC Read the feature table created by the data ingestion notebook.

# COMMAND ----------

import pandas as pd

# TODO: Change "iris_data" to your feature table name
table_name = f"{catalog_name}.{schema_name}.iris_data"

# Load data
df = spark.read.table(table_name).toPandas()

print(f"Loaded {len(df)} rows from {table_name}")
print(f"\nColumns: {df.columns.tolist()}")
print(f"\nData types:\n{df.dtypes}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3: Prepare features and target
# MAGIC
# MAGIC **TODO:** Adapt this to your features and target column.

# COMMAND ----------

from sklearn.model_selection import train_test_split

# Define features and target
# TODO: Change feature and target column names to match your dataset
feature_cols = ['sepal_length', 'sepal_width', 'petal_length', 'petal_width']
target_col = 'target'

X = df[feature_cols]
y = df[target_col]

# Split into train/test
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

print(f"Training set: {len(X_train)} rows")
print(f"Test set: {len(X_test)} rows")
print(f"\nFeatures: {feature_cols}")
print(f"Target: {target_col}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4: Train model
# MAGIC
# MAGIC **TODO:** Replace with your chosen algorithm.

# COMMAND ----------

from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

# TODO: Replace DecisionTreeClassifier with your algorithm
# Examples:
# - Classification: RandomForestClassifier, LogisticRegression, XGBClassifier
# - Regression: LinearRegression, XGBRegressor, RandomForestRegressor
# - Clustering: KMeans, DBSCAN (no target column needed)

model = DecisionTreeClassifier(random_state=42, max_depth=5)
model.fit(X_train, y_train)

print("✓ Model trained successfully")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5: Evaluate and log metrics
# MAGIC
# MAGIC **TODO:** Adapt metrics to your problem type.

# COMMAND ----------

# Make predictions
y_pred = model.predict(X_test)

# Compute metrics
# TODO: Change metrics based on your problem type:
# - Classification: accuracy, f1_score, precision_score, recall_score, roc_auc_score
# - Regression: mean_squared_error, mean_absolute_error, r2_score
# - Clustering: silhouette_score, davies_bouldin_score

accuracy = accuracy_score(y_test, y_pred)
f1 = f1_score(y_test, y_pred, average='weighted')
precision = precision_score(y_test, y_pred, average='weighted')
recall = recall_score(y_test, y_pred, average='weighted')

print(f"Accuracy:  {accuracy:.4f}")
print(f"F1 Score:  {f1:.4f}")
print(f"Precision: {precision:.4f}")
print(f"Recall:    {recall:.4f}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 6: Log to MLflow and register model
# MAGIC
# MAGIC Register the model with the `@challenger` alias. The deployment pipeline will promote it to `@champion` after evaluation.

# COMMAND ----------

# Start MLflow run
with mlflow.start_run():
    # Log parameters
    mlflow.log_param("algorithm", "DecisionTreeClassifier")
    mlflow.log_param("max_depth", 5)
    mlflow.log_param("test_size", 0.2)

    # Log metrics
    mlflow.log_metric("accuracy", accuracy)
    mlflow.log_metric("f1_score", f1)
    mlflow.log_metric("precision", precision)
    mlflow.log_metric("recall", recall)

    # Log model with signature
    signature = mlflow.models.infer_signature(X_train, y_train)
    mlflow.sklearn.log_model(
        model,
        artifact_path="model",
        signature=signature
    )

    run_id = mlflow.active_run().info.run_id
    model_uri = f"runs:/{run_id}/model"

    # Register model with @challenger alias
    # TODO: Change "iris_model" to your model name
    model_name = f"{catalog_name}.{schema_name}.iris_model"

    registered_model = mlflow.register_model(model_uri, model_name)

    # Set @challenger alias
    client = mlflow.tracking.MlflowClient()
    client.set_registered_model_alias(
        model_name,
        "challenger",
        registered_model.version
    )

    print(f"✓ Registered model {model_name} version {registered_model.version}")
    print(f"✓ Set @challenger alias")
    print(f"\nModel URI: {model_uri}")
    print(f"Run ID: {run_id}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary
# MAGIC
# MAGIC Model training and registration complete. The model is now available as `@challenger` in the Unity Catalog. The deployment pipeline will evaluate it and promote to `@champion` if it passes approval criteria.
