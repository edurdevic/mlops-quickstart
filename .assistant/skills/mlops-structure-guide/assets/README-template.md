# Your MLOps Project

> **Description:** [TODO: Brief description of your ML project and business problem]

This repository contains an end-to-end MLOps pipeline on Databricks for [TODO: your use case]. The pipeline automates:

- **Data Ingestion:** Load and transform raw data into feature tables
- **Model Training:** Train models and register them to Unity Catalog
- **Model Deployment:** Evaluate, approve, and promote models to production
- **Batch Inference:** Score new data with the production model

The pipeline is deployed using Databricks Asset Bundles (DAB) with support for multiple environments (dev/prod) and CI/CD automation.

## Table of Contents

- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Setup](#setup)
- [Deployment](#deployment)
- [Running Jobs](#running-jobs)
- [Customization Guide](#customization-guide)
- [Troubleshooting](#troubleshooting)

---

## Quick Start

This quick start assumes you have a Databricks workspace and the Databricks CLI configured.

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd <your-repo-name>
```

### 2. Set up your workspace connection

Open `databricks.yml` and update these sections:

**For dev environment:**
```yaml
targets:
  dev:
    workspace:
      host: https://your-workspace.cloud.databricks.com  # TODO: Set this
    variables:
      catalog_name: your_dev_catalog      # TODO: Change to your dev catalog
      schema_name: your_schema            # TODO: Change to your schema
```

**For prod environment (if needed):**
```yaml
  prod:
    workspace:
      host: https://prod-workspace.cloud.databricks.com  # TODO: Set if different
    variables:
      catalog_name: your_prod_catalog     # TODO: Change to your prod catalog
      schema_name: your_schema
```

### 3. Authenticate with Databricks

```bash
databricks auth login --host https://your-workspace.cloud.databricks.com
```

Choose one of the authentication methods:
- OAuth (recommended)
- Service Principal
- PAT (Personal Access Token)

### 4. Deploy to dev

```bash
# Validate the bundle configuration
databricks bundle validate --target dev

# Do a dry run (won't create resources)
databricks bundle deploy --target dev --no-lock

# Actually deploy
databricks bundle deploy --target dev
```

### 5. Verify jobs were created

```bash
# List all jobs created by this bundle
databricks jobs list --output json | \
  jq '.jobs[] | select(.tags.Project == "your_project_name")'
```

You should see 4 jobs:
- `1 - Data Ingestion Job`
- `2.1 - Model Training Job`
- `2.2 - Model Deployment Job`
- `3 - Batch Inference Job`

### 6. Run the pipeline

**First run:** Execute jobs in sequence to train and deploy the model

```bash
# Get job IDs
INGESTION_JOB=$(databricks jobs list --output json | jq -r '.jobs[] | select(.name | contains("Data Ingestion")) | .job_id')
TRAINING_JOB=$(databricks jobs list --output json | jq -r '.jobs[] | select(.name | contains("Model Training")) | .job_id')
DEPLOYMENT_JOB=$(databricks jobs list --output json | jq -r '.jobs[] | select(.name | contains("Deployment")) | .job_id')
INFERENCE_JOB=$(databricks jobs list --output json | jq -r '.jobs[] | select(.name | contains("Batch Inference")) | .job_id')

# Run data ingestion
databricks jobs run-now --job-id $INGESTION_JOB
# Wait for it to complete...

# Run model training
databricks jobs run-now --job-id $TRAINING_JOB
# Wait for it to complete...

# Run deployment (evaluate → approve → deploy)
databricks jobs run-now --job-id $DEPLOYMENT_JOB
# Wait for it to complete...

# Run batch inference
databricks jobs run-now --job-id $INFERENCE_JOB
```

**Subsequent runs:** Typically just re-train and re-deploy

```bash
# Re-train the model
databricks jobs run-now --job-id $TRAINING_JOB

# Re-run deployment if training succeeded
databricks jobs run-now --job-id $DEPLOYMENT_JOB

# Re-run inference
databricks jobs run-now --job-id $INFERENCE_JOB
```

---

## Project Structure

```
.
├── notebooks/
│   ├── 1_data_preprocessing/
│   │   └── data_ingestion.ipynb           # Load, transform, write feature table
│   ├── 2_model_training_and_deployment/
│   │   ├── model_training.ipynb           # Train & register @challenger
│   │   └── model_deployment/
│   │       ├── 1_model_evaluation.ipynb   # Evaluate metrics
│   │       ├── 2_model_approval.ipynb     # Apply business logic
│   │       └── 3_model_deployment.ipynb   # Promote to @champion
│   └── 3_inference/
│       └── batch_inference.ipynb          # Score new data
│
├── resources/
│   ├── 1_data_preprocessing_job.yml       # Data ingestion job config
│   ├── 2_1_model_training_job.yml         # Training job config
│   ├── 2_2_model_deployment_job.yml       # Deployment job config
│   └── 3_batch_inference_job.yml          # Inference job config
│
├── databricks.yml                         # Asset Bundle configuration
├── requirements.txt                       # Python dependencies
└── README.md                              # This file
```

### Data Flow

```
Raw Data
   ↓
[Data Ingestion] → Feature Table
   ↓
[Model Training] → @challenger (new model)
   ↓
[Model Evaluation] → Compare metrics
   ↓
[Model Approval] → Apply business criteria
   ↓
[Model Deployment] → @champion (production model)
   ↓
[Batch Inference] → Predictions Table
```

---

## Prerequisites

### Databricks workspace
- Unity Catalog enabled
- You have permission to create catalogs/schemas (or they already exist)
- You can create jobs and run notebooks

### Local machine
- Databricks CLI v1.0+: [Install here](https://docs.databricks.com/dev-tools/cli/install)
- Python 3.8+
- Git

### Verify prerequisites

```bash
# Check Databricks CLI version
databricks version

# Test workspace connection
databricks workspace list

# Check Python version
python --version
```

---

## Setup

### 1. Install Python dependencies

```bash
pip install -r requirements.txt
```

All notebooks install from this file automatically with:
```python
%pip install -r ../../requirements.txt
dbutils.library.restartPython()
```

### 2. Create Unity Catalog and schema (if needed)

If your catalog and schema don't exist yet:

```bash
# Create catalog
databricks sql --file - <<EOF
CREATE CATALOG IF NOT EXISTS your_dev_catalog;
GRANT CREATE ON CATALOG your_dev_catalog TO \`your_team\`;
EOF

# Create schema
databricks sql --file - <<EOF
CREATE SCHEMA IF NOT EXISTS your_dev_catalog.your_schema;
GRANT MODIFY ON SCHEMA your_dev_catalog.your_schema TO \`your_team\`;
EOF
```

### 3. Configure variables in databricks.yml

Update these TODO items in `databricks.yml`:
- [ ] `bundle.name` → Your project name
- [ ] `targets.dev.workspace.host` → Your dev workspace URL
- [ ] `targets.dev.variables.catalog_name` → Your dev catalog
- [ ] `targets.dev.variables.schema_name` → Your schema
- [ ] `targets.prod.workspace.host` → Your prod workspace (if different)
- [ ] `targets.prod.variables.catalog_name` → Your prod catalog

### 4. Customize notebooks

Edit each notebook to match your data and model:

**`1_data_preprocessing/data_ingestion.ipynb`:**
- Replace data loading logic to read from your source
- Adjust transformations to match your data schema
- Update table names and column names

**`2_model_training_and_deployment/model_training.ipynb`:**
- Replace the algorithm (currently DecisionTree)
- Update feature and target columns
- Adjust evaluation metrics for your problem type
- Change model name

**`2_model_training_and_deployment/model_deployment/2_model_approval.ipynb`:**
- Update approval criteria thresholds
- Adjust business rules (e.g., min accuracy)

**`3_inference/batch_inference.ipynb`:**
- Update inference data source
- Adjust feature selection
- Change output table names

---

## Deployment

### Deploy to development

```bash
# Validate
databricks bundle validate --target dev

# Deploy
databricks bundle deploy --target dev
```

### Deploy to production

Before deploying to production:

1. Test the pipeline in dev
2. Verify all TODOs in `databricks.yml` are completed
3. Ensure prod workspace/catalog/schema are set up
4. Review permissions in `databricks.yml` (optional)

Then deploy:

```bash
# Validate
databricks bundle validate --target prod

# Deploy
databricks bundle deploy --target prod
```

### Verify deployment

```bash
# List jobs in dev
databricks jobs list --target dev | jq '.jobs[] | select(.tags.Environment == "dev")'

# List jobs in prod
databricks jobs list --target prod | jq '.jobs[] | select(.tags.Environment == "prod")'
```

---

## Running Jobs

### Run a job manually

```bash
# Find the job ID
JOB_ID=$(databricks jobs list --output json | \
  jq -r '.jobs[] | select(.name | contains("Data Ingestion")) | .job_id')

# Run the job
RUN_ID=$(databricks jobs run-now --job-id $JOB_ID | jq .run_id)

# Monitor the run
databricks runs get --run-id $RUN_ID
```

### Check job status

```bash
# List runs for a job
databricks runs list --job-id $JOB_ID

# Get detailed run info
databricks runs get --run-id $RUN_ID

# View run output and logs
databricks runs get-output --run-id $RUN_ID
```

### Stop a running job

```bash
# Cancel a run
databricks runs cancel --run-id $RUN_ID
```

---

## Customization Guide

### Change the algorithm

Edit `notebooks/2_model_training_and_deployment/model_training.ipynb`:

**Current (DecisionTree):**
```python
from sklearn.tree import DecisionTreeClassifier
model = DecisionTreeClassifier(random_state=42, max_depth=5)
```

**For Random Forest:**
```python
from sklearn.ensemble import RandomForestClassifier
model = RandomForestClassifier(n_estimators=100, random_state=42)
```

**For XGBoost:**
```python
from xgboost import XGBClassifier
model = XGBClassifier(random_state=42)
```

### Change evaluation metrics

Edit `notebooks/2_model_training_and_deployment/model_training.ipynb`:

**For Regression:**
```python
from sklearn.metrics import mean_squared_error, r2_score
rmse = np.sqrt(mean_squared_error(y_test, y_pred))
r2 = r2_score(y_test, y_pred)
mlflow.log_metric("rmse", rmse)
mlflow.log_metric("r2", r2)
```

**For Classification:**
```python
from sklearn.metrics import roc_auc_score, precision_recall_curve
roc_auc = roc_auc_score(y_test, y_pred_proba)
mlflow.log_metric("roc_auc", roc_auc)
```

### Change approval criteria

Edit `notebooks/2_model_training_and_deployment/model_deployment/2_model_approval.ipynb`:

```python
APPROVAL_CRITERIA = {
    'min_accuracy': 0.95,              # Require 95% accuracy
    'improvement_over_champion': 0.01  # Require 1% improvement
}
```

### Schedule batch inference to run daily

Edit `resources/3_batch_inference_job.yml`:

```yaml
schedule:
  quartz_cron_expression: "0 2 * * ?"  # Daily at 2 AM UTC
  timezone_id: "UTC"
  pause_status: "UNPAUSED"
```

Then redeploy:
```bash
databricks bundle deploy --target dev
```

### Add email notifications

Edit each job YAML file in `resources/`:

```yaml
email_notifications:
  on_failure:
    - "your.team@company.com"
  no_alert_for_skipped_runs: false
```

---

## Troubleshooting

### "Workspace host not configured"

**Error:** `INVALID_PARAMETER_VALUE: Workspace host is not configured`

**Solution:** Set the workspace host in `databricks.yml`:
```yaml
targets:
  dev:
    workspace:
      host: https://your-workspace.cloud.databricks.com
```

### "Catalog/schema not found"

**Error:** `RESOURCE_NOT_FOUND: Catalog 'your_catalog' not found`

**Solution:**
1. Create the catalog: `CREATE CATALOG your_catalog`
2. Create the schema: `CREATE SCHEMA your_catalog.your_schema`
3. Verify in databricks.yml that `catalog_name` and `schema_name` match

### "Notebook not found"

**Error:** `RESOURCE_NOT_FOUND: Notebook not found`

**Solution:** Check the notebook path in the job YAML matches your repository structure:
```yaml
notebook_task:
  notebook_path: "../notebooks/1_data_preprocessing/data_ingestion.ipynb"
```

### "Model alias does not exist"

**Error:** `RESOURCE_NOT_FOUND: Model alias 'champion' not found`

**Solution:** The `@champion` alias doesn't exist yet. Run the full pipeline:
1. Run data ingestion
2. Run model training (creates `@challenger`)
3. Run model deployment (creates `@champion`)

### "Permission denied"

**Error:** `PERMISSION_DENIED: You do not have permission to access catalog`

**Solution:**
1. Verify you have permission to use the catalog: `SHOW GRANT ON CATALOG your_catalog`
2. Ask your workspace admin to grant you permissions
3. Use a different catalog you have access to

### Deployment jobs not created

**Error:** `bundle deploy` completes but no jobs appear in workspace

**Solution:**
1. Check that all job YAMLs are in the `resources/` folder
2. Verify `databricks.yml` has `include: - resources/*.yml`
3. Run validation: `databricks bundle validate`
4. Check that variables are correctly set

---

## Next Steps

1. **Customize data loading:** Update `1_data_preprocessing/data_ingestion.ipynb` with your data source
2. **Adapt model:** Change algorithm, features, and metrics in `2_1_model_training_job.yml`
3. **Test locally:** Run notebooks individually to verify they work
4. **Deploy to dev:** Run `databricks bundle deploy --target dev`
5. **Run the pipeline:** Execute jobs in order and monitor runs
6. **Set up CI/CD:** (Optional) Add GitHub Actions or Azure DevOps automation
7. **Deploy to prod:** Run `databricks bundle deploy --target prod`

---

## Additional Resources

- [Databricks Asset Bundles Documentation](https://docs.databricks.com/dev-tools/bundles/)
- [Unity Catalog Documentation](https://docs.databricks.com/data-governance/unity-catalog/)
- [MLflow Model Registry](https://mlflow.org/docs/latest/model-registry.html)
- [Databricks CLI Reference](https://docs.databricks.com/dev-tools/cli/)

---

## Support

For issues or questions:

1. Check the [Troubleshooting](#troubleshooting) section above
2. Search Databricks documentation
3. Check job logs in Databricks UI
4. Open a GitHub issue in this repository

---

## License

[TODO: Add your license here]
