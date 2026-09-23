# Databricks notebook source

# COMMAND ----------

# MAGIC %md
# MAGIC # Batch Inference Notebook
# MAGIC
# MAGIC This notebook loads the `@champion` model and scores new data in batch.
# MAGIC
# MAGIC **TODO:** Adapt this notebook to your inference data source and prediction schema.

# COMMAND ----------

# Install dependencies
%pip install -r ../../requirements.txt
dbutils.library.restartPython()

# COMMAND ----------

# Define widgets for parameterization
dbutils.widgets.text("catalog_name", "mlops_quickstart_dev")
dbutils.widgets.text("schema_name", "iris")
dbutils.widgets.text("model_version", "1")  # Optional: can specify model version explicitly

catalog_name = dbutils.widgets.get("catalog_name")
schema_name = dbutils.widgets.get("schema_name")
model_version = dbutils.widgets.get("model_version")

print(f"Catalog: {catalog_name}")
print(f"Schema: {schema_name}")
print(f"Model version: {model_version}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1: Load champion model
# MAGIC
# MAGIC Always load the `@champion` alias (never hardcode a version).

# COMMAND ----------

import mlflow
import pandas as pd
from datetime import datetime

# TODO: Change "iris_model" to your model name
model_name = f"{catalog_name}.{schema_name}.iris_model"

# Load @champion model
champion_uri = f"models:/{model_name}@champion"

try:
    champion_model = mlflow.pyfunc.load_model(champion_uri)
    print(f"✓ Loaded @champion model: {champion_uri}")
except Exception as e:
    print(f"❌ Failed to load @champion model: {e}")
    raise Exception(
        f"Cannot find @champion alias for {model_name}. "
        "Please run the deployment pipeline first."
    )

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: Load inference data
# MAGIC
# MAGIC **TODO:** Replace this with your inference data source.
# MAGIC Examples:
# MAGIC - Existing Delta table: `spark.read.table(...)`
# MAGIC - Cloud storage: `spark.read.format("parquet").load(...)`
# MAGIC - SQL query: `spark.sql(...)`

# COMMAND ----------

# Example: Load new iris samples from a table
# TODO: Change "new_iris_samples" to your inference data table
inference_table = f"{catalog_name}.{schema_name}.new_iris_samples"

try:
    df_inference = spark.read.table(inference_table).toPandas()
    print(f"✓ Loaded {len(df_inference)} rows from {inference_table}")
except Exception as e:
    print(f"❌ Could not load inference table: {e}")
    print(f"\nCreating sample data for demonstration...")

    # Create sample data if table doesn't exist
    import numpy as np
    np.random.seed(42)
    sample_data = np.random.randn(10, 4) * 0.5 + 5.5  # Similar to Iris data
    df_inference = pd.DataFrame(
        sample_data,
        columns=['sepal_length', 'sepal_width', 'petal_length', 'petal_width']
    )
    print(f"✓ Created {len(df_inference)} sample rows for demonstration")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3: Prepare features
# MAGIC
# MAGIC Select and order features to match training data.

# COMMAND ----------

# TODO: Change feature column order to match training
feature_cols = ['sepal_length', 'sepal_width', 'petal_length', 'petal_width']

# Verify all features are present
missing_cols = [col for col in feature_cols if col not in df_inference.columns]
if missing_cols:
    raise ValueError(f"Missing required columns: {missing_cols}")

X_inference = df_inference[feature_cols]
print(f"✓ Selected {len(feature_cols)} features")
print(f"  Features: {feature_cols}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4: Score data

# COMMAND ----------

# Make predictions
predictions = champion_model.predict(X_inference)

print(f"✓ Scored {len(predictions)} rows")
print(f"\nPrediction distribution:")
import numpy as np
unique, counts = np.unique(predictions, return_counts=True)
for pred_class, count in zip(unique, counts):
    print(f"  Class {pred_class}: {count} samples")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5: Add predictions to results

# COMMAND ----------

# Add predictions to original data
df_results = df_inference.copy()
df_results['prediction'] = predictions
df_results['prediction_timestamp'] = datetime.now()

# Add metadata
df_results['model_name'] = model_name
df_results['model_alias'] = 'champion'

print(f"\nSample predictions (first 5 rows):")
print(df_results[['sepal_length', 'sepal_width', 'prediction', 'prediction_timestamp']].head())

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 6: Write predictions
# MAGIC
# MAGIC Write results to an inference table for analysis.

# COMMAND ----------

# Convert to Spark DataFrame
df_results_spark = spark.createDataFrame(df_results)

# TODO: Change "iris_predictions" to your predictions table name
predictions_table = f"{catalog_name}.{schema_name}.iris_predictions"

# Write predictions (idempotent: overwrite if exists)
df_results_spark.write.mode("overwrite").format("delta").saveAsTable(predictions_table)

print(f"✓ Wrote {len(df_results)} predictions to {predictions_table}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Verification

# COMMAND ----------

# Verify predictions table
df_verify = spark.read.table(predictions_table)

print(f"✓ Verified: {df_verify.count()} rows in {predictions_table}")
print(f"\nSchema:")
df_verify.printSchema()
print(f"\nSample data:")
df_verify.limit(5).display()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

print("="*60)
print("✓ BATCH INFERENCE COMPLETE")
print("="*60)
print(f"\nModel: {model_name}")
print(f"Model Alias: @champion")
print(f"Rows scored: {len(df_results)}")
print(f"Results table: {predictions_table}")
print("="*60)
