---
name: mlops-structure-guide
description: >-
  Complete guide to structuring a draft ML notebook into a production-ready
  MLops pipeline on Databricks. Covers splitting notebooks into separate
  stages, creating jobs, configuring Asset Bundles, and setting up CI/CD.
  Self-contained with all template files. Use when transforming a single
  notebook into a full MLops project with data ingestion, training, deployment,
  and inference stages.
---

# MLops Structure Guide — Transform Notebook to Pipeline

This skill guides you through transforming a single ML notebook into a
production-grade MLops pipeline on Databricks. It covers:

- Splitting your notebook into specialized stages (ingest → train → deploy → infer)
- Creating separate notebooks for each stage
- Organizing them into Databricks jobs
- Configuring the Asset Bundle for multi-environment deployment
- Writing a project README with quick-start instructions

## When to use this skill

Use this skill when you have:

- ✅ A working ML notebook with data loading, training, and inference logic
- ✅ A Databricks workspace with Unity Catalog enabled
- ✅ Want to productionize the notebook into a repeatable pipeline
- ✅ Need to deploy to dev/prod environments with CI/CD

## High-level architecture

A complete MLops pipeline has these stages, each in its own notebook and job:

```
┌─────────────────────────────────────────────────────────────┐
│                    MLops Pipeline                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. DATA INGESTION        2. TRAINING       3. DEPLOYMENT   │
│     └─ Load data       └─ Train model   ┌─ Evaluate       │
│     └─ Transform       └─ Log metrics   ├─ Approve        │
│     └─ Create table    └─ Register      └─ Promote        │
│                           model                             │
│                                                              │
│  4. BATCH INFERENCE                                          │
│     └─ Load champion model                                  │
│     └─ Score new data                                       │
│     └─ Write predictions                                    │
│                                                              │
└─────────────────────────────────────────────────────────────┘

Directory structure:
├── notebooks/
│   ├── 1_data_preprocessing/
│   │   └── data_ingestion.ipynb
│   ├── 2_model_training_and_deployment/
│   │   ├── model_training.ipynb
│   │   └── model_deployment/
│   │       ├── 1_model_evaluation.ipynb
│   │       ├── 2_model_approval.ipynb
│   │       └── 3_model_deployment.ipynb
│   └── 3_inference/
│       ├── batch_inference.ipynb
│       └── realtime_inference.ipynb
├── resources/
│   ├── 1_data_preprocessing_job.yml
│   ├── 2_1_model_training_job.yml
│   ├── 2_2_model_deployment_job.yml
│   └── 3_batch_inference_job.yml
├── databricks.yml
├── requirements.txt
└── README.md
```

## Step 1: Analyze your current notebook

Before splitting, identify the logical stages in your notebook:

| Stage | Purpose | Input | Output |
|-------|---------|-------|--------|
| **Data Ingestion** | Load, clean, transform data | Raw data (files, API, DB) | Feature table in UC |
| **Model Training** | Train & register model | Feature table | Registered model (with @challenger alias) |
| **Model Deployment** | Evaluate, approve, promote | Challenger model | Champion model + serving endpoint |
| **Batch Inference** | Score new data | Champion model + new data | Predictions table / Inference table |

**Questions to ask:**
- Where does your notebook load data? (cells 1-5?)
- Where does training start? (cells 6-20?)
- Are evaluation metrics computed? If so, where?
- Does it score on new data? If so, where?

Create a map of your notebook's cells to these stages.

## Step 2: Split your notebook into stages

### Stage 1: Data Ingestion

**Source:** Cells that load, clean, and transform raw data.

**Output:** A feature table in Unity Catalog (e.g. `{catalog}.{schema}.iris_data`).

**Key principles:**
- Remove any model training code.
- Keep all data transformation logic.
- Make it **idempotent**: check if table exists before deciding to create vs. append/overwrite.
- Accept `catalog_name` and `schema_name` as widgets so it's reusable across environments.

**Template reference:** See `assets/notebook-template-data-ingestion.ipynb`

**Example transformation:**

```python
# Original notebook (single cell):
from sklearn.datasets import load_iris
iris = load_iris()
df = pd.DataFrame(iris.data, columns=iris.feature_names)
df['target'] = iris.target

# Split into data_ingestion.ipynb:
dbutils.widgets.text("catalog_name", "mlops_quickstart_dev")
dbutils.widgets.text("schema_name", "iris")

from sklearn.datasets import load_iris
iris = load_iris()
df = pd.DataFrame(iris.data, columns=iris.feature_names)
df['target'] = iris.target

table_name = f"{catalog_name}.{schema_name}.iris_data"
spark_df = spark.createDataFrame(df)

# Idempotent write: create if not exists, overwrite if exists
spark_df.write.mode("overwrite").format("delta").saveAsTable(table_name)
print(f"✓ Ingested {spark_df.count()} rows to {table_name}")
```

---

### Stage 2: Model Training

**Source:** Cells that prepare features, train the model, log metrics, and register.

**Output:** A registered model in Unity Catalog with the `@challenger` alias.

**Key principles:**
- Accept `catalog_name`, `schema_name`, and `model_version` as widgets.
- Read from the feature table created by Stage 1.
- Log all metrics to MLflow (accuracy, F1, ROC-AUC, etc.).
- Register **every** training run with the `@challenger` alias — **never** use `@champion` from training.
- Keep the model signature inferred (let `infer_signature` drive it).
- Use a user-scoped MLflow experiment to avoid collisions: `/{user}/{model}_{catalog}`.

**Template reference:** See `assets/notebook-template-model-training.ipynb`

**Example transformation:**

```python
# Original notebook (multiple cells):
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import train_test_split

X = df[features]
y = df['target']
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

model = DecisionTreeClassifier(random_state=42)
model.fit(X_train, y_train)

accuracy = model.score(X_test, y_test)
print(f"Accuracy: {accuracy}")

# Split into model_training.ipynb:
dbutils.widgets.text("catalog_name", "mlops_quickstart_dev")
dbutils.widgets.text("schema_name", "iris")
dbutils.widgets.text("model_version", "1")

import mlflow
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import train_test_split

table_name = f"{catalog_name}.{schema_name}.iris_data"
df = spark.read.table(table_name).toPandas()

X = df[['sepal_length', 'sepal_width', 'petal_length', 'petal_width']]
y = df['target']
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

model = DecisionTreeClassifier(random_state=42)
model.fit(X_train, y_train)

accuracy = model.score(X_test, y_test)

# Log to MLflow
with mlflow.start_run():
    mlflow.log_metric("accuracy", accuracy)
    mlflow.sklearn.log_model(model, artifact_path="model", 
                             signature=mlflow.models.infer_signature(X_train, y_train))
    
    # Register with @challenger alias
    model_uri = "runs:/{}/model".format(mlflow.active_run().info.run_id)
    model_name = f"{catalog_name}.{schema_name}.iris_model"
    registered_model = mlflow.register_model(model_uri, model_name)
    client = mlflow.tracking.MlflowClient()
    client.set_registered_model_alias(model_name, "challenger", registered_model.version)
    print(f"✓ Registered model {model_name} version {registered_model.version} as @challenger")
```

---

### Stage 3: Model Deployment (Evaluation → Approval → Promotion)

**Source:** Cells that evaluate the challenger model, apply business logic, and promote to champion.

**Output:** Promoted model with `@champion` alias + serving endpoint (optional).

**Key principles:**
- This stage **cannot exist in isolation** — it must be triggered after a new `@challenger` is registered.
- Break it into 3 sub-notebooks: `1_model_evaluation.ipynb`, `2_model_approval.ipynb`, `3_model_deployment.ipynb`.
- Use MLflow 3 **Deployment Jobs** to orchestrate them.
- The first run manually connects the deployment job to your registered model (done in evaluation notebook).
- Never hardcode the model version — read it from the run context or from parameters.

**Template reference:** See assets for all three notebooks.

**Notebook breakdown:**

**1_model_evaluation.ipynb:**
- Fetch the `@challenger` model
- Compare metrics vs. `@champion` (if it exists)
- Compute evaluation metrics (e.g., ROC curve, confusion matrix)
- Log results to MLflow
- **On first run:** Connect the deployment job to the registered model
  ```python
  client = mlflow.tracking.MlflowClient()
  client.create_model_version_tag(model_name, "deployment_job_run_id", str(mlflow.active_run().info.run_id), version)
  ```

**2_model_approval.ipynb:**
- Read evaluation metrics from stage 1
- Check against approval criteria (e.g., accuracy > 95%)
- If criteria met: set an approval tag
- If not: fail with a clear message

**3_model_deployment.ipynb:**
- Check that approval tag exists
- Promote `@challenger` to `@champion`
- Create/update serving endpoint (optional)
- Log deployment timestamp

**Example:**

```python
# 1_model_evaluation.ipynb
dbutils.widgets.text("catalog_name", "mlops_quickstart_dev")
dbutils.widgets.text("schema_name", "iris")

model_name = f"{catalog_name}.{schema_name}.iris_model"
client = mlflow.tracking.MlflowClient()

challenger_version = client.get_model_version_by_alias(model_name, "challenger")
challenger_uri = f"models:/{model_name}@challenger"
challenger_model = mlflow.pyfunc.load_model(challenger_uri)

# Run evaluation...
accuracy = evaluate_model(challenger_model, test_data)
mlflow.log_metric("challenger_accuracy", accuracy)

# 2_model_approval.ipynb
challenger_version = client.get_model_version_by_alias(model_name, "challenger")
runs = client.search_runs(experiment_ids=[...], filter_string=f"tags.version = {challenger_version.version}")
metrics = runs[0].data.metrics

if metrics['challenger_accuracy'] > 0.95:
    client.set_model_version_tag(model_name, challenger_version.version, "approval_status", "approved")
    print("✓ Model approved for deployment")
else:
    raise Exception("Model did not meet approval criteria")

# 3_model_deployment.ipynb
challenger_version = client.get_model_version_by_alias(model_name, "challenger")
approval_tag = client.get_model_version_by_alias(model_name, "challenger")

if approval_tag.tags.get("approval_status") == "approved":
    client.set_registered_model_alias(model_name, "champion", challenger_version.version)
    print(f"✓ Promoted version {challenger_version.version} to @champion")
else:
    raise Exception("Cannot deploy: model not approved")
```

---

### Stage 4: Batch Inference

**Source:** Cells that load the champion model and score new data.

**Output:** Predictions written to an inference table.

**Key principles:**
- Always load the `@champion` alias (never hardcode a version).
- Accept `catalog_name`, `schema_name`, and optionally `model_version` as widgets.
- Make it idempotent: append/overwrite predictions based on your use case.
- Log inference metadata (timestamp, row count, model version used).

**Template reference:** See `assets/notebook-template-batch-inference.ipynb`

**Example transformation:**

```python
# Original notebook (inference cell):
champion_model = mlflow.sklearn.load_model("models:/iris_model@champion")
predictions = champion_model.predict(X_new)
results_df['prediction'] = predictions

# Split into batch_inference.ipynb:
dbutils.widgets.text("catalog_name", "mlops_quickstart_dev")
dbutils.widgets.text("schema_name", "iris")

champion_model = mlflow.pyfunc.load_model(f"models:/{catalog_name}.{schema_name}.iris_model@champion")

# Load new data
new_data_table = f"{catalog_name}.{schema_name}.new_iris_samples"
df_new = spark.read.table(new_data_table).toPandas()

X_new = df_new[['sepal_length', 'sepal_width', 'petal_length', 'petal_width']]
predictions = champion_model.predict(X_new)

df_new['prediction'] = predictions
df_new['prediction_timestamp'] = pd.Timestamp.now()

# Write results (idempotent)
output_table = f"{catalog_name}.{schema_name}.iris_predictions"
spark.createDataFrame(df_new).write.mode("overwrite").format("delta").saveAsTable(output_table)

print(f"✓ Scored {len(df_new)} rows and wrote to {output_table}")
```

---

## Step 3: Create the notebook files

Using the templates from `assets/`, create these notebooks in your repository:

```
notebooks/
├── 1_data_preprocessing/
│   └── data_ingestion.ipynb           (based on notebook-template-data-ingestion.ipynb)
├── 2_model_training_and_deployment/
│   ├── model_training.ipynb           (based on notebook-template-model-training.ipynb)
│   └── model_deployment/
│       ├── 1_model_evaluation.ipynb   (based on notebook-template-model-evaluation.ipynb)
│       ├── 2_model_approval.ipynb     (based on notebook-template-model-approval.ipynb)
│       └── 3_model_deployment.ipynb   (based on notebook-template-model-deployment.ipynb)
└── 3_inference/
    └── batch_inference.ipynb          (based on notebook-template-batch-inference.ipynb)
```

**Adaptation steps:**

1. Copy the template notebook.
2. Replace placeholder variable names with your actual names (e.g., `iris_data` → `your_table_name`).
3. Swap the data loading code (keep the ingestion stage code structure, adapt the source).
4. Swap the feature/target columns to match your dataset.
5. Swap the model algorithm (if different from DecisionTree).
6. Test each notebook individually in your workspace.

---

## Step 4: Set up the Asset Bundle

The Asset Bundle (DAB) allows you to define jobs declaratively and deploy them across dev/prod environments.

### 4a. Create `databricks.yml`

This file defines your bundle configuration, targets (dev/prod), and variables.

**Reference:** `assets/databricks-yml-template.yaml`

**Key sections:**

```yaml
bundle:
  name: your_project_name           # Change to your project name

include:
  - resources/*.yml                 # Automatically includes all job YAMLs in resources/

targets:
  dev:                              # Development environment
    mode: development
    workspace:
      host: https://your-workspace.cloud.databricks.com  # TODO: Set your workspace
      root_path: /Workspace/Users/${workspace.current_user.userName}/.bundle/${bundle.name}/${bundle.target}
    default: true                   # dev is the default target
    variables:
      catalog_name: your_dev_catalog
      schema_name: your_schema
      environment: dev

  prod:                             # Production environment
    mode: production
    workspace:
      host: https://your-workspace.cloud.databricks.com  # TODO: Set your workspace
      root_path: /Workspace/Shared/.bundle/${bundle.name}/${bundle.target}
    variables:
      catalog_name: your_prod_catalog
      schema_name: your_schema
      environment: prod
```

**Adaptation checklist:**

- [ ] Set `bundle.name` to your project name
- [ ] Set workspace `host` for dev target
- [ ] Set `catalog_name` and `schema_name` for dev
- [ ] Set workspace `host` for prod target (may be different workspace)
- [ ] Set `catalog_name` and `schema_name` for prod

---

### 4b. Create job YAML files in `resources/`

Each stage gets its own job YAML file. Copy the templates and adapt:

#### Job 1: Data Ingestion

**File:** `resources/1_data_preprocessing_job.yml`

**Reference:** `assets/job-template-data-ingestion.yml`

**Customize:**
- Job name and description
- Task notebook path (should be `../notebooks/1_data_preprocessing/data_ingestion.ipynb`)
- Task email notifications (add your team's email)
- Job cluster settings (optional; defaults to serverless)

---

#### Job 2: Model Training

**File:** `resources/2_1_model_training_job.yml`

**Reference:** `assets/job-template-model-training.yml`

**Customize:**
- Job name and description
- Task notebook path
- Email notifications
- Job cluster settings

---

#### Job 3: Model Deployment

**File:** `resources/2_2_model_deployment_job.yml`

**Reference:** `assets/job-template-model-deployment.yml`

**Key points:**
- This job has 3 tasks in sequence: `evaluation` → `approval` → `deployment`
- Each task references the corresponding notebook under `model_deployment/`
- Tasks depend on each other using `depends_on`
- **Important:** After first deployment, you must manually connect this job to your registered model in the Databricks UI (click "Connect to a model" in the job configuration)

---

#### Job 4: Batch Inference

**File:** `resources/3_batch_inference_job.yml`

**Reference:** `assets/job-template-batch-inference.yml`

**Customize:**
- Job name and description
- Task notebook path
- Schedule (optional; e.g., daily at 2 AM)
- Email notifications

---

## Step 5: Configure parameterization

All notebooks must accept `catalog_name` and `schema_name` as widgets, and all table references must use the three-level format: `{catalog_name}.{schema_name}.<table_name>`.

**Parameterization contract:**

| Parameter | Where it's set | Where it's used | Default |
|-----------|----------------|-----------------|---------|
| `catalog_name` | Job YAML `base_parameters` | Notebook widget | Set per target in `databricks.yml` |
| `schema_name` | Job YAML `base_parameters` | Notebook widget | Set per target in `databricks.yml` |
| `model_version` | Job YAML `base_parameters` | Notebook widget (deployment only) | `1` |

**Example:**

In `resources/1_data_preprocessing_job.yml`:

```yaml
parameters:
  - name: "catalog_name"
    default: "${var.catalog_name}"
  - name: "schema_name"
    default: "${var.schema_name}"

tasks:
  - task_key: "ingest_data"
    notebook_task:
      notebook_path: "../notebooks/1_data_preprocessing/data_ingestion.ipynb"
      base_parameters:
        catalog_name: "{{job.parameters.catalog_name}}"
        schema_name: "{{job.parameters.schema_name}}"
```

In the notebook's first cell:

```python
dbutils.widgets.text("catalog_name", "mlops_quickstart_dev")
dbutils.widgets.text("schema_name", "iris")
catalog_name = dbutils.widgets.get("catalog_name")
schema_name = dbutils.widgets.get("schema_name")
```

---

## Step 6: Create a project README

Use the template in `assets/README-template.md` to create a project README that includes:

- Overview of your ML problem
- Quick start instructions
- Project structure explanation
- How to deploy and run jobs
- Troubleshooting tips

**Key sections to customize:**

1. **Project name and description** — what problem does it solve?
2. **Prerequisites** — workspace access, catalog, authentication
3. **Quick start** — clone, configure TODOs, deploy
4. **Running jobs** — how to trigger, monitor, view results
5. **Customization** — pointers to which files to change for your data/model

---

## Step 7: Set up CI/CD (optional)

If using GitHub or Azure DevOps, add automation to deploy your bundle when you push code.

### GitHub Actions

Create `.github/workflows/databricks_deployment.yml`:

```yaml
name: Deploy to Databricks

on:
  push:
    branches: [ dev, main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Databricks CLI
        uses: databricks/setup-cli@v0
      
      - name: Deploy to Databricks (dev)
        if: github.ref == 'refs/heads/dev'
        env:
          DATABRICKS_HOST: ${{ secrets.DATABRICKS_HOST }}
          DATABRICKS_TOKEN: ${{ secrets.DATABRICKS_TOKEN }}
        run: databricks bundle deploy --target dev
      
      - name: Deploy to Databricks (prod)
        if: github.ref == 'refs/heads/main'
        env:
          DATABRICKS_HOST: ${{ secrets.DATABRICKS_HOST }}
          DATABRICKS_TOKEN: ${{ secrets.DATABRICKS_TOKEN }}
        run: databricks bundle deploy --target prod
```

---

## Step 8: Deployment and testing

### Local deployment

```bash
# Authenticate with Databricks
databricks auth login --host https://your-workspace.cloud.databricks.com

# Deploy to dev (dry run)
databricks bundle deploy --target dev --no-lock

# Deploy to dev (actual)
databricks bundle deploy --target dev

# Deploy to prod
databricks bundle deploy --target prod
```

### Verify jobs were created

```bash
# List jobs
databricks jobs list --output json | jq '.jobs[] | select(.tags.Project == "your_project")'
```

### Run a job manually

```bash
# Find job ID
JOB_ID=$(databricks jobs list --output json | jq -r '.jobs[] | select(.name | contains("Data Ingestion")) | .job_id' | head -1)

# Run it
databricks jobs run-now --job-id $JOB_ID

# Check run status
databricks runs list --job-id $JOB_ID
```

---

## Parameterization checklist

Before deploying, verify:

- [ ] All table references use `{catalog_name}.{schema_name}.table_name`
- [ ] All notebooks have `catalog_name` and `schema_name` widgets
- [ ] All job YAMLs pass these parameters via `base_parameters`
- [ ] `databricks.yml` sets `catalog_name` and `schema_name` per target
- [ ] No hardcoded catalog or schema names in notebook code
- [ ] No hardcoded model names — use `{catalog_name}.{schema_name}.model_name`

---

## Deployment checklist

Before deploying to production, verify:

- [ ] Each notebook has been tested individually in your workspace
- [ ] Job YAMLs have email notifications configured
- [ ] Dev and prod targets have different catalogs/schemas
- [ ] Permissions are set on resources/ jobs if needed
- [ ] CI/CD workflow (if applicable) has correct secrets configured
- [ ] README has been updated with your project details and TODOs marked

---

## Common patterns

### Deploying a new model version

```bash
# 1. Push changes to model training notebook
# 2. GitHub Actions / Azure DevOps automatically runs bundle deploy
# 3. Manually trigger the training job
databricks jobs run-now --job-id <training_job_id>
# 4. Once training completes, the deployment job can be triggered
# 5. Review evaluation metrics
# 6. If approved, the deployment job promotes to @champion
```

### Debugging a failed job

```bash
# Find the failed run
databricks runs list --job-id <job_id> --limit 5

# Get full run details
databricks runs get --run-id <run_id>

# View logs
databricks runs get-output --run-id <run_id>
```

### Scaling compute for a job

Edit the job YAML and add a `job_clusters` section:

```yaml
job_clusters:
  - job_cluster_key: "compute"
    new_cluster:
      autoscale:
        min_workers: 2
        max_workers: 8
      spark_version: "15.4.x-scala2.12"
      node_type_id: "i3.xlarge"

tasks:
  - task_key: "ingest_data"
    job_cluster_key: "compute"
    # ...
```

Then redeploy:

```bash
databricks bundle deploy --target dev
```

---

## Troubleshooting

**Problem:** "Notebook not found" error when deploying

- **Solution:** Check that notebook paths in job YAMLs are relative to the bundle root. Use `../notebooks/...` format.

**Problem:** Job parameters aren't being passed to notebooks

- **Solution:** Ensure widgets are defined in the notebook's first cell with matching names. Check `base_parameters` in job YAML.

**Problem:** Model alias doesn't exist (`@challenger` or `@champion`)

- **Solution:** Make sure you're registering the model in the training notebook with the alias. See Step 2 for example code.

**Problem:** "Permission denied" when deploying

- **Solution:** Ensure your Databricks token has the necessary permissions. Run `databricks workspace list` to verify connectivity.

**Problem:** Different results between dev and prod

- **Solution:** Verify `catalog_name` and `schema_name` are correctly set per target in `databricks.yml`. Check for any hardcoded values in notebook code.

---

## Next steps

1. ✅ Copy template files from `assets/` and adapt them to your data/model
2. ✅ Test each notebook individually in your workspace
3. ✅ Create job YAML files in `resources/`
4. ✅ Configure `databricks.yml` with your workspace and catalog details
5. ✅ Deploy with `databricks bundle deploy --target dev`
6. ✅ Manually run jobs to verify they work
7. ✅ Set up CI/CD pipeline for automated deployments
8. ✅ Deploy to production

For more information, see the [Databricks Asset Bundles documentation](https://docs.databricks.com/en/dev-tools/bundles/).
