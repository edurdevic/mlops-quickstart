---
name: adapt-model-deployment
description: >-
  Adapt the MLOps Quickstart MLflow 3 deployment pipeline (evaluate → approve →
  deploy) to a custom model. Use when the user wants to change evaluation
  metrics or thresholds, customize the human-in-the-loop approval gate, adjust
  the serving endpoint configuration, or wire a freshly registered model
  version to the deployment job.
---

# Adapt the Model Deployment Pipeline

Target folder: `notebooks/2_model_training_and_deployment/model_deployment/`
Target job: `resources/2_2_model_deployment_job.yml`

This pipeline follows the
[MLflow 3 Deployment Jobs](https://docs.databricks.com/gcp/en/mlflow/deployment-job)
pattern: **evaluate → approve → deploy**.

## When to use

Use this skill whenever the user wants to:

- Change the evaluation metric or threshold gate.
- Customize the approval tag name or who can apply it.
- Adjust the serving endpoint (workload size, scale-to-zero, naming).
- Connect a newly registered model version to the deployment job.
- Skip serving entirely (batch-only deployments).

## Step-by-step

### 1. `1_model_evaluation.ipynb`

Update for the new problem type:

- Point `eval_data` at the holdout / golden dataset for the new model.
- Set `target` to the new label column (drop entirely for clustering).
- Set `model_type` correctly for `mlflow.evaluate`:
  - `"classifier"` for classification.
  - `"regressor"` for regression.
  - Omit / use custom metrics for clustering and forecasting.
- Add custom evaluation logic (fairness, slice metrics, business KPIs) as
  additional cells if needed. Log everything to MLflow.

### 2. `2_model_approval.ipynb`

This is a human-in-the-loop gate that checks for an `approval` tag on the
model version. **Important gotcha**: the widget default declared in code
is `approval_tag_name="approval"` (the *tag name* is `approval`), and the
expected *value* is `approved`. So the tag on the model version must be
`approval=approved`. The widget metadata at the bottom of the notebook
JSON (which you may see while reading the file) reflects cached UI state
from past runs and can mislead you — trust the `dbutils.widgets.text(...)`
call in the cell body.

Customize when needed:

- **Rename the tag** (e.g. `prod_approval`) if your org uses a different
  convention. Update the `dbutils.widgets.text` default in the notebook
  AND the workflow your approvers use to apply tags.
- **Restrict who can apply the tag** by combining UC permissions on
  *Apply Tag* with a
  [governed tag policy](https://docs.databricks.com/aws/en/admin/governed-tags/)
  that limits valid values.
- **Email approvers**: configure the job's `email_notifications.on_failure`
  so approvers get notified when the approval task fails (i.e. no tag
  applied yet).
- **Apply the tag programmatically** (e.g. from a CI script) with the UC
  MLflow REST endpoint:

  ```bash
  databricks api post /api/2.0/mlflow/unity-catalog/model-versions/set-tag \
    --json '{"name":"<catalog>.<schema>.<model>","version":"<n>","key":"approval","value":"approved"}'
  ```

### 3. `3_model_deployment.ipynb`

Creates or updates the serving endpoint:

- Adjust `workload_size`, `scale_to_zero_enabled`, and any traffic-split
  configuration to match expected load and cost.
- Keep the endpoint naming convention
  `{catalog_name}-{schema_name}-{model}-endpoint` (dots replaced with
  dashes). See `mlops-quickstart-overview`.
- Promote the model version to the `@champion` alias as the final step.
  Inference notebooks always load `@champion`.
- **Batch-only deployments**: if no realtime endpoint is needed, remove
  this notebook from the job (delete the `deployment` task in the YAML) or
  replace it with a notebook that only sets the `@champion` alias.

### 4. Job wiring (`resources/2_2_model_deployment_job.yml`)

- Update `parameters.model_name` so the default points at the renamed
  registered model: `${var.catalog_name}.${var.schema_name}.<model_name>`.
- `model_version` is intentionally parameterized so each run targets a
  specific version. Don't hardcode it.
- Update `email_notifications.on_failure` with the team's address.

### 5. Connect the model to the deployment job

After registering the **first** version of the renamed model, follow
[Connect the deployment job to a model](https://docs.databricks.com/gcp/en/mlflow/deployment-job#connect-the-deployment-job-to-a-model)
in the Databricks UI so new model versions trigger this job automatically.

## Parameterization contract

The deployment notebooks share two parameters via widgets: `model_name`
(fully qualified UC reference) and `model_version`. Preserve both names and
the three-level UC reference convention from `mlops-quickstart-overview`.

## Edge cases

- **No approval gate**: for low-risk auto-deploys, replace
  `2_model_approval.ipynb` with a notebook that auto-applies the approval
  tag when the evaluation task succeeds. Document the reduced safety.
- **Cross-environment promotion**: if dev/prod use different catalogs but
  share a single source-of-truth model, either retrain per environment or
  follow
  [Promote a model across environments](https://docs.databricks.com/aws/en/machine-learning/manage-model-lifecycle#promote-a-model-across-environments).
- **Non-existent endpoint on first run**: the deployment notebook must
  handle "create if missing, update if exists." Keep the existing
  conditional logic when refactoring.
- **`UseBudgetPolicy` permission on serverless workspaces**: workspaces
  that enforce serverless budget policies will fail endpoint creation
  with `PERMISSION_DENIED: missing UseBudgetPolicyPermission on policy …`.
  The principal running the deployment notebook (user or service
  principal) needs `Use` permission on whichever budget policy the
  workspace assigns to model-serving endpoints. Surface this requirement
  in the rollout checklist.
- **Best-historical-run trap in training**: the training notebook
  registers the highest-`test_accuracy` historical run, not the latest
  run. If you bump a DBR-shipped library version (scikit-learn, etc.) in
  `requirements.txt`, the eval task can fail loading an older artifact
  pickled with a different version. See `manage-dependencies` for the
  pinning policy.
