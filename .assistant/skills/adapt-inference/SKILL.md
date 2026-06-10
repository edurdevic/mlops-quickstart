---
name: adapt-inference
description: >-
  Adapt the MLOps Quickstart inference notebooks (batch and realtime / serving
  endpoint) to a custom model and input schema. Use when the user wants to run
  batch scoring on new data, query the realtime serving endpoint, change the
  inference output table, or enable Lakehouse Monitoring on inference results.
---

# Adapt Inference (Batch + Realtime)

Target files:

- `notebooks/3_inference/batch_inference.ipynb`
- `notebooks/3_inference/realtime_inference.ipynb`

Target job: `resources/3_batch_inference_job.yml`

Both notebooks always load the model via the `@champion` alias — never
hardcode a version.

## When to use

Use this skill whenever the user wants to:

- Replace the sample input with their own new/unseen data.
- Change the inference output table or its schema.
- Enable Lakehouse Monitoring on inference results.
- Call the realtime serving endpoint with a custom payload.

## Batch inference

Steps for `batch_inference.ipynb`:

1. **Replace the input data source.** Swap the sample data for the
   customer's actual new/unseen data. Same options as data ingestion: Delta
   table, cloud storage, JDBC, API.

2. **Match the input schema** to what the model expects. Use
   `mlflow.models.get_model_info(...).signature` to verify, or call
   `loaded_model.metadata.get_input_schema()`. Cast / reorder columns to
   match.

3. **Update prediction post-processing.** Examples:
   - Classification: map class indices back to label strings.
   - Regression: clip predictions to a valid range.
   - Forecasting: attach forecast horizon timestamps.

4. **Rename the inference table.** Replace `iris_inferences` with a
   meaningful name. Keep the three-level reference
   `{catalog_name}.{schema_name}.<table_name>`.

5. **Keep Change Data Feed (CDF) enabled** at the end of the notebook:

   ```python
   spark.sql(f"ALTER TABLE {table_name} SET TBLPROPERTIES (delta.enableChangeDataFeed = true)")
   ```

   This enables
   [Lakehouse Monitoring](https://docs.databricks.com/aws/en/lakehouse-monitoring/)
   on the inference table. Drop it only if you have no monitoring plan.

6. **Preserve idempotency.** Existing logic creates the table on first run
   and appends afterwards. Keep that pattern.

7. **Sync the job YAML.** Update
   `resources/3_batch_inference_job.yml`: notebook path,
   `base_parameters`, and `email_notifications.on_failure`.

## Realtime inference

Steps for `realtime_inference.ipynb`:

1. **Update `sample_input`** to match the model's input schema (same as
   batch).

2. **Derive the endpoint name** from the convention
   `{catalog_name}-{schema_name}-{model}-endpoint` (dots replaced with
   dashes). The deployment notebook creates the endpoint with this exact
   name.

3. **Set authentication** via the SDK or REST. The notebook uses the
   workspace context by default; for external callers, document how to
   obtain a token (service principal preferred).

## Parameterization contract

Both notebooks read `catalog_name` / `schema_name` widgets, and the batch
job passes them through `base_parameters`. Keep the three-level UC reference
convention from `mlops-quickstart-overview` for all tables and models.

## Edge cases

- **Schema mismatch at scoring time**: catch with the MLflow signature
  check up front and emit a clear error before scoring. Don't silently
  reorder columns.
- **Streaming inference**: split the batch notebook into a
  `readStream` + `foreachBatch` writer; the model load and post-processing
  logic stay the same.
- **Cold-start endpoint**: if `scale_to_zero_enabled` is true, the first
  request can take seconds to warm up. Document this in the realtime
  notebook so consumers know what to expect.
- **PII in inferences**: apply column masks via Unity Catalog on the
  inference table rather than masking in the notebook.
- **Model not yet promoted**: if `@champion` does not exist yet (first
  deployment hasn't run), the notebook should fail with a clear message
  pointing the user at the deployment job.
