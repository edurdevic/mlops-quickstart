# Databricks notebook source

# COMMAND ----------

# MAGIC %md
# MAGIC # Data Ingestion Notebook
# MAGIC
# MAGIC This notebook loads data from a source, transforms it, and writes to a feature table in Unity Catalog.
# MAGIC
# MAGIC **TODO:** Adapt this notebook to your data source and transformations.

# COMMAND ----------

# Install dependencies (if needed)
%pip install -r ../../requirements.txt
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
# MAGIC ## Step 1: Load data
# MAGIC
# MAGIC **TODO:** Replace this cell with your data source.
# MAGIC Examples:
# MAGIC - Cloud storage: `spark.read.format("parquet").load("s3://bucket/path")`
# MAGIC - JDBC: `spark.read.format("jdbc").options(...).load()`
# MAGIC - REST API: use `requests` then `spark.createDataFrame(...)`
# MAGIC - Existing Delta table: `spark.read.table(...)`

# COMMAND ----------

# Example: Load Iris dataset from sklearn
import pandas as pd
from sklearn.datasets import load_iris

iris = load_iris()
df_pandas = pd.DataFrame(iris.data, columns=iris.feature_names)
df_pandas['target'] = iris.target
df_pandas['species'] = df_pandas['target'].map({0: 'setosa', 1: 'versicolor', 2: 'virginica'})

# Convert to Spark DataFrame
df_spark = spark.createDataFrame(df_pandas)

print(f"Loaded {df_spark.count()} rows")
df_spark.display()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: Data transformation
# MAGIC
# MAGIC **TODO:** Add your data cleaning and transformation logic here.
# MAGIC Examples:
# MAGIC - Rename columns
# MAGIC - Cast data types
# MAGIC - Handle missing values
# MAGIC - Filter rows
# MAGIC - Add derived columns

# COMMAND ----------

# Example transformations
from pyspark.sql.functions import col, when

# Rename columns for clarity
df_transformed = df_spark.withColumnRenamed("sepal length (cm)", "sepal_length") \
                          .withColumnRenamed("sepal width (cm)", "sepal_width") \
                          .withColumnRenamed("petal length (cm)", "petal_length") \
                          .withColumnRenamed("petal width (cm)", "petal_width")

# Add a created timestamp
from pyspark.sql.functions import current_timestamp
df_transformed = df_transformed.withColumn("created_at", current_timestamp())

print(f"Transformed {df_transformed.count()} rows")
df_transformed.display()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3: Write to Unity Catalog
# MAGIC
# MAGIC Write the feature table to Unity Catalog. This is idempotent — it will create the table if it doesn't exist, or overwrite it if it does.

# COMMAND ----------

# Define the table name using three-level reference
# TODO: Change "iris_data" to your feature table name
table_name = f"{catalog_name}.{schema_name}.iris_data"

# Write in overwrite mode (idempotent)
df_transformed.write.mode("overwrite").format("delta").saveAsTable(table_name)

print(f"✓ Successfully ingested data to {table_name}")
print(f"  Rows: {df_transformed.count()}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Verification
# MAGIC
# MAGIC Verify the table was created and contains data.

# COMMAND ----------

# Read back and verify
df_verify = spark.read.table(table_name)
print(f"Verified: {df_verify.count()} rows in {table_name}")
print("\nSchema:")
df_verify.printSchema()
print("\nSample data:")
df_verify.limit(5).display()
