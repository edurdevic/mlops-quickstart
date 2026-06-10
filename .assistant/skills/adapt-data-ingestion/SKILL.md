---
name: adapt-data-ingestion
description: >-
  Adapt the MLOps Quickstart data ingestion notebook from the Iris placeholder
  to a custom data source (cloud storage, JDBC, API, Delta table, etc.). Use
  when the user wants to ingest their own dataset, swap the source data, rename
  the feature table, add bronze/silver/gold preprocessing stages, or extend
  `1_data_preprocessing/`.
---

# Adapt Data Ingestion

Target file: `notebooks/1_data_preprocessing/data_ingestion.ipynb`
Target job: `resources/1_data_preprocessing_job.yml`

## When to use

Use this skill whenever the user wants to:

- Replace the Iris dataset with their own source data.
- Add preprocessing stages (bronze → silver → gold).
- Rename the feature table or change its schema/primary key.

## Step-by-step

1. **Replace the data source.** Remove the `sklearn.datasets.load_iris()`
   block. Replace with the customer's data source — for example:
   - Cloud storage: `spark.read.format("parquet").load("s3://...")`,
     `dbutils.fs.ls` + Auto Loader, etc.
   - JDBC: `spark.read.format("jdbc").options(...).load()`.
   - REST API: pull with `requests` then `spark.createDataFrame(...)`.
   - Existing Delta table: `spark.read.table("...")`.

2. **Rename the feature table.** Replace `iris_data` with a meaningful name
   (e.g. `customer_churn_features`). Keep the three-level reference
   `{catalog_name}.{schema_name}.<table_name>` — never hardcode catalog or
   schema.

3. **Adjust the schema.** Update column casts, primary key constraints, and
   any column-level transformations to match the new dataset.

4. **Preserve idempotency.** Keep the "table exists?" guard so the notebook
   can safely re-run. Decide deliberately between `overwrite` and `append`
   for the new use case.

5. **Add multi-stage preprocessing (optional).** For bronze → silver → gold
   pipelines:
   - Add notebooks under `notebooks/1_data_preprocessing/` (e.g.
     `1_bronze_ingestion.ipynb`, `2_silver_cleaning.ipynb`,
     `3_gold_features.ipynb`).
   - Add corresponding `tasks` in `resources/1_data_preprocessing_job.yml`,
     wiring `depends_on` to enforce execution order.
   - Pass `catalog_name` / `schema_name` to each new task via
     `base_parameters`.

6. **Update the job notification email.** Replace
   `your.name@address.com` in `resources/1_data_preprocessing_job.yml` with
   the team's address.

## Parameterization contract

Every new notebook must define widgets for `catalog_name` and `schema_name`
and reference all tables as `{catalog_name}.{schema_name}.<object>`. See the
`mlops-quickstart-overview` skill for the full contract.

## Edge cases

- **Streaming sources** (Kafka, Kinesis, Auto Loader): keep ingestion in a
  separate notebook and configure the job task as a continuous trigger if
  needed.
- **Large datasets**: prefer Auto Loader over `spark.read` for incremental
  cloud-storage ingestion.
- **Sensitive columns**: apply column masks or row filters via Unity Catalog
  rather than dropping them in the notebook, so governance is centralized.
- **Schema drift**: if the source schema may evolve, enable
  `mergeSchema` (`.option("mergeSchema", "true")`) and document the
  decision in the notebook.
