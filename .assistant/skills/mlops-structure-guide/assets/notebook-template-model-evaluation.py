# Databricks notebook source

# COMMAND ----------

# MAGIC %md
# MAGIC # Model Evaluation Notebook
# MAGIC
# MAGIC Part 1 of the MLflow 3 Deployment Pipeline.
# MAGIC
# MAGIC This notebook evaluates the `@challenger` model by comparing its metrics against the `@champion` model (if it exists) and other evaluation criteria.
# MAGIC
# MAGIC **TODO:** Adapt evaluation logic to your problem type and success criteria.

# COMMAND ----------

# Install dependencies
%pip install -r ../../../requirements.txt
dbutils.library.restartPython()

# COMMAND ----------

# Define widgets for parameterization
dbutils.widgets.text("catalog_name", "mlops_quickstart_dev")
dbutils.widgets.text("schema_name", "iris")

catalog_name = dbutils.widgets.get("catalog_name")
schema_name = dbutils.widgets.get("schema_name")

print(f"Catalog: {catalog_name}")
print(f"Schema: {schema_name}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1: Load challenger model

# COMMAND ----------

import mlflow
import mlflow.sklearn

# TODO: Change "iris_model" to your model name
model_name = f"{catalog_name}.{schema_name}.iris_model"

# Load challenger model
try:
    challenger_uri = f"models:/{model_name}@challenger"
    challenger_model = mlflow.pyfunc.load_model(challenger_uri)

    client = mlflow.tracking.MlflowClient()
    challenger_version = client.get_model_version_by_alias(model_name, "challenger")
    print(f"✓ Loaded @challenger: version {challenger_version.version}")
    print(f"  Status: {challenger_version.status}")
except Exception as e:
    print(f"❌ Could not find @challenger model: {e}")
    raise

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: Load test data
# MAGIC
# MAGIC Reload test data used during training for consistent evaluation.

# COMMAND ----------

import pandas as pd
from sklearn.model_selection import train_test_split

# Load feature table
# TODO: Change "iris_data" to your feature table name
table_name = f"{catalog_name}.{schema_name}.iris_data"
df = spark.read.table(table_name).toPandas()

# Prepare same train/test split as training notebook
# TODO: Change feature and target column names
feature_cols = ['sepal_length', 'sepal_width', 'petal_length', 'petal_width']
target_col = 'target'

X = df[feature_cols]
y = df[target_col]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

print(f"Test set: {len(X_test)} rows")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3: Evaluate challenger model

# COMMAND ----------

from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

# Make predictions
y_pred_challenger = challenger_model.predict(X_test)

# Compute metrics
# TODO: Adapt metrics to your problem type
challenger_metrics = {
    'accuracy': accuracy_score(y_test, y_pred_challenger),
    'f1_score': f1_score(y_test, y_pred_challenger, average='weighted'),
    'precision': precision_score(y_test, y_pred_challenger, average='weighted'),
    'recall': recall_score(y_test, y_pred_challenger, average='weighted')
}

print("Challenger Model Metrics:")
for metric, value in challenger_metrics.items():
    print(f"  {metric}: {value:.4f}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4: Compare with champion (if exists)

# COMMAND ----------

# Try to load champion model
champion_exists = False
try:
    champion_uri = f"models:/{model_name}@champion"
    champion_model = mlflow.pyfunc.load_model(champion_uri)

    champion_version = client.get_model_version_by_alias(model_name, "champion")
    print(f"✓ Loaded @champion: version {champion_version.version}")

    # Evaluate champion
    y_pred_champion = champion_model.predict(X_test)

    champion_metrics = {
        'accuracy': accuracy_score(y_test, y_pred_champion),
        'f1_score': f1_score(y_test, y_pred_champion, average='weighted'),
        'precision': precision_score(y_test, y_pred_champion, average='weighted'),
        'recall': recall_score(y_test, y_pred_champion, average='weighted')
    }

    print("\nChampion Model Metrics:")
    for metric, value in champion_metrics.items():
        print(f"  {metric}: {value:.4f}")

    champion_exists = True

except Exception as e:
    print(f"ℹ No @champion model exists yet (this is the first deployment)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5: Log evaluation results to MLflow
# MAGIC
# MAGIC Log evaluation metrics so they're tracked in the model registry.

# COMMAND ----------

# Start MLflow run to log evaluation results
with mlflow.start_run() as run:
    # Log challenger metrics
    for metric, value in challenger_metrics.items():
        mlflow.log_metric(f"challenger_{metric}", value)

    # Log champion metrics if exists
    if champion_exists:
        for metric, value in champion_metrics.items():
            mlflow.log_metric(f"champion_{metric}", value)

        # Log improvement
        accuracy_improvement = challenger_metrics['accuracy'] - champion_metrics['accuracy']
        mlflow.log_metric("accuracy_improvement", accuracy_improvement)

    print(f"✓ Logged evaluation results to MLflow run: {run.info.run_id}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 6: Generate evaluation summary
# MAGIC
# MAGIC Create a summary to help with the approval decision.

# COMMAND ----------

print("="*60)
print("EVALUATION SUMMARY")
print("="*60)
print(f"\nChallenger Model: v{challenger_version.version}")
print(f"  Accuracy: {challenger_metrics['accuracy']:.4f}")
print(f"  F1 Score: {challenger_metrics['f1_score']:.4f}")

if champion_exists:
    print(f"\nChampion Model: v{champion_version.version}")
    print(f"  Accuracy: {champion_metrics['accuracy']:.4f}")
    print(f"  F1 Score: {champion_metrics['f1_score']:.4f}")
    print(f"\nImprovement:")
    print(f"  Accuracy: {accuracy_improvement:+.4f}")
else:
    print(f"\n⚠️  No champion model exists. This will be the first deployment.")

print(f"\nNext step: Review metrics and approve for deployment in 2_model_approval.py")
print("="*60)
