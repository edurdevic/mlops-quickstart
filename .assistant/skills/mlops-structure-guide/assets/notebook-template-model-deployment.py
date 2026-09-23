# Databricks notebook source

# COMMAND ----------

# MAGIC %md
# MAGIC # Model Deployment Notebook
# MAGIC
# MAGIC Part 3 of the MLflow 3 Deployment Pipeline.
# MAGIC
# MAGIC This notebook promotes the approved `@challenger` model to `@champion` and optionally creates/updates a serving endpoint.
# MAGIC
# MAGIC **TODO:** Adapt serving endpoint configuration to your needs (optional if not using realtime inference).

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
# MAGIC ## Step 1: Verify approval

# COMMAND ----------

import mlflow
import pandas as pd
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.serving import ServedModelInput, EndpointConfigInput

# TODO: Change "iris_model" to your model name
model_name = f"{catalog_name}.{schema_name}.iris_model"

client = mlflow.tracking.MlflowClient()

# Get challenger version
challenger_version = client.get_model_version_by_alias(model_name, "challenger")
print(f"Challenger version: {challenger_version.version}")

# Verify it was approved
approval_status = challenger_version.tags.get("approval_status")
if approval_status != "approved":
    raise Exception(
        f"Model version {challenger_version.version} has approval_status='{approval_status}'. "
        "Please approve it in the approval notebook first."
    )

print(f"✓ Model approved (approval_status={approval_status})")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: Promote to @champion

# COMMAND ----------

# Promote challenger to champion
client.set_registered_model_alias(
    model_name,
    "champion",
    challenger_version.version
)

print(f"✓ Promoted version {challenger_version.version} to @champion")

# Verify promotion
champion_version = client.get_model_version_by_alias(model_name, "champion")
assert champion_version.version == challenger_version.version, "Promotion verification failed"
print(f"✓ Verification passed: @champion is v{champion_version.version}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3: Create or update serving endpoint (optional)
# MAGIC
# MAGIC If you want to serve the model for real-time inference, create a serving endpoint.
# MAGIC
# MAGIC **Note:** This step is optional. If you only need batch inference, you can skip this.

# COMMAND ----------

# TODO: Set CREATE_ENDPOINT to True if you want to create a serving endpoint
CREATE_ENDPOINT = False

if CREATE_ENDPOINT:
    # Initialize Databricks SDK
    ws = WorkspaceClient()

    # Generate endpoint name (must be lowercase, no dots/underscores)
    # TODO: Customize endpoint naming if needed
    endpoint_name = f"{catalog_name}-{schema_name}-iris-model-endpoint".lower().replace("_", "-")

    print(f"Creating serving endpoint: {endpoint_name}")

    # Check if endpoint already exists
    try:
        existing_endpoint = ws.serving_endpoints.get(endpoint_name)
        print(f"Endpoint {endpoint_name} already exists. Updating...")

        # Update existing endpoint to point to new champion
        config = EndpointConfigInput(
            served_models=[
                ServedModelInput(
                    model_name=model_name,
                    model_version=str(champion_version.version),
                    workload_size="Small",
                    workload_type="CPU"
                )
            ]
        )
        ws.serving_endpoints.update_config_and_wait(endpoint_name, config)
        print(f"✓ Updated endpoint {endpoint_name} to serve v{champion_version.version}")

    except Exception as e:
        if "not found" in str(e).lower():
            # Create new endpoint
            print(f"Creating new endpoint {endpoint_name}...")
            config = EndpointConfigInput(
                served_models=[
                    ServedModelInput(
                        model_name=model_name,
                        model_version=str(champion_version.version),
                        workload_size="Small",
                        workload_type="CPU"
                    )
                ]
            )
            ws.serving_endpoints.create_and_wait(
                name=endpoint_name,
                config=config
            )
            print(f"✓ Created endpoint {endpoint_name}")
        else:
            raise
else:
    print("ℹ Skipping serving endpoint creation (CREATE_ENDPOINT=False)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4: Log deployment record

# COMMAND ----------

# Log deployment metadata
with mlflow.start_run():
    mlflow.log_param("deployed_model_version", champion_version.version)
    mlflow.log_param("deployment_timestamp", pd.Timestamp.now().isoformat())
    mlflow.log_param("environment", "dev")  # TODO: Make this dynamic based on environment

    # If endpoint created, log that too
    if CREATE_ENDPOINT:
        mlflow.log_param("serving_endpoint_name", endpoint_name)

    print(f"✓ Logged deployment record to MLflow")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary
# MAGIC
# MAGIC Deployment complete!

# COMMAND ----------

print("="*60)
print("✓ DEPLOYMENT COMPLETE")
print("="*60)
print(f"\nModel: {model_name}")
print(f"Champion Version: v{champion_version.version}")
if CREATE_ENDPOINT:
    print(f"Serving Endpoint: {endpoint_name}")
print(f"\nThe @champion model is now ready for:")
print("  - Batch inference (via 3_batch_inference_job.yml)")
if CREATE_ENDPOINT:
    print(f"  - Real-time inference (via {endpoint_name} endpoint)")
print("="*60)
