# Databricks notebook source

# COMMAND ----------

# MAGIC %md
# MAGIC # Model Approval Notebook
# MAGIC
# MAGIC Part 2 of the MLflow 3 Deployment Pipeline.
# MAGIC
# MAGIC This notebook applies business logic to decide whether the `@challenger` model should be promoted to production. It can be:
# MAGIC - Automated (if metrics meet criteria)
# MAGIC - Manual (require a human to set an approval tag)
# MAGIC - Hybrid (metrics check + manual review)
# MAGIC
# MAGIC **TODO:** Adapt approval criteria to your business requirements.

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
# MAGIC ## Step 1: Load challenger model and evaluation metrics

# COMMAND ----------

import mlflow
import pandas as pd

# TODO: Change "iris_model" to your model name
model_name = f"{catalog_name}.{schema_name}.iris_model"

client = mlflow.tracking.MlflowClient()

# Get challenger version
challenger_version = client.get_model_version_by_alias(model_name, "challenger")
print(f"Challenger version: {challenger_version.version}")
print(f"Status: {challenger_version.status}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: Define approval criteria
# MAGIC
# MAGIC **TODO:** Adapt these thresholds to your business requirements.
# MAGIC
# MAGIC Examples:
# MAGIC - Minimum accuracy threshold (e.g., >= 0.95)
# MAGIC - Improvement over champion (e.g., +5%)
# MAGIC - Business metric requirements
# MAGIC - Fairness/bias checks
# MAGIC - Resource constraints

# COMMAND ----------

# TODO: Set approval thresholds appropriate for your use case
APPROVAL_CRITERIA = {
    'min_accuracy': 0.90,              # Minimum accuracy required
    'min_f1_score': 0.85,              # Minimum F1 score
    'improvement_over_champion': -0.05  # Allow slight decrease (e.g., -5%)
}

print("Approval Criteria:")
for criterion, value in APPROVAL_CRITERIA.items():
    print(f"  {criterion}: {value}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3: Retrieve evaluation metrics

# COMMAND ----------

# Get latest runs with evaluation metrics
runs = client.search_runs(
    experiment_names=[f"/{pd.io.sql.get_user()}/iris_model_{catalog_name}" if False else "*"],
    filter_string="tags.mlflow.loggedModel = 'true'",
    max_results=100
)

if not runs:
    print("No evaluation runs found. Running evaluation notebook...")
    raise Exception("Please run evaluation notebook first")

# Get the most recent run with evaluation metrics
latest_run = runs[0]
metrics = latest_run.data.metrics

print(f"\nEvaluation Metrics (from run {latest_run.info.run_id[:8]}):")
challenger_accuracy = metrics.get('challenger_accuracy', 'N/A')
challenger_f1 = metrics.get('challenger_f1_score', 'N/A')
print(f"  Challenger Accuracy: {challenger_accuracy}")
print(f"  Challenger F1 Score: {challenger_f1}")

if 'champion_accuracy' in metrics:
    champion_accuracy = metrics.get('champion_accuracy')
    improvement = champion_accuracy - challenger_accuracy if isinstance(challenger_accuracy, float) else None
    print(f"  Champion Accuracy: {champion_accuracy}")
    print(f"  Improvement: {improvement}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4: Apply approval logic

# COMMAND ----------

# Automated approval based on criteria
approval_decision = True
rejection_reasons = []

# Check minimum accuracy
if isinstance(challenger_accuracy, (int, float)):
    if challenger_accuracy < APPROVAL_CRITERIA['min_accuracy']:
        approval_decision = False
        rejection_reasons.append(
            f"Accuracy {challenger_accuracy:.4f} < required {APPROVAL_CRITERIA['min_accuracy']:.4f}"
        )

# Check minimum F1 score
if isinstance(challenger_f1, (int, float)):
    if challenger_f1 < APPROVAL_CRITERIA['min_f1_score']:
        approval_decision = False
        rejection_reasons.append(
            f"F1 Score {challenger_f1:.4f} < required {APPROVAL_CRITERIA['min_f1_score']:.4f}"
        )

# Check improvement over champion
if 'champion_accuracy' in metrics and improvement is not None:
    if improvement < APPROVAL_CRITERIA['improvement_over_champion']:
        approval_decision = False
        rejection_reasons.append(
            f"Improvement {improvement:+.4f} < required {APPROVAL_CRITERIA['improvement_over_champion']:+.4f}"
        )

# Print decision
print("="*60)
if approval_decision:
    print("✓ APPROVED FOR DEPLOYMENT")
else:
    print("❌ REJECTED - DOES NOT MEET CRITERIA")
    print("\nRejection Reasons:")
    for reason in rejection_reasons:
        print(f"  - {reason}")
print("="*60)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5: Set approval tag on model version
# MAGIC
# MAGIC Record the approval decision as a tag on the model version.

# COMMAND ----------

# Set approval status tag
approval_status = "approved" if approval_decision else "rejected"

client.set_model_version_tag(
    model_name,
    challenger_version.version,
    "approval_status",
    approval_status
)

# Set additional tags for traceability
client.set_model_version_tag(
    model_name,
    challenger_version.version,
    "evaluated_at",
    pd.Timestamp.now().isoformat()
)

print(f"✓ Set approval_status={approval_status} on model version {challenger_version.version}")

# Fail if rejected
if not approval_decision:
    print("\n⚠️  Model rejected. Stopping deployment.")
    raise Exception(f"Model approval failed. Reasons: {'; '.join(rejection_reasons)}")
else:
    print("\n✓ Proceeding to deployment step (3_model_deployment.py)")
