---
name: adapt-model-training
description: >-
  Adapt the MLOps Quickstart model training notebook from the Iris classifier
  placeholder to a custom algorithm and problem type (regression, clustering,
  classification, forecasting). Use when the user wants to change the model,
  features, target, metrics, or registered model name, or when they ask how to
  fit a different ML problem into this template.
---

# Adapt Model Training

Target file: `notebooks/2_model_training_and_deployment/model_training.ipynb`
Target job: `resources/2_1_model_training_job.yml`

## When to use

Use this skill whenever the user wants to:

- Swap `DecisionTreeClassifier` for a different algorithm.
- Change the problem type (regression, clustering, forecasting, …).
- Change features, target column, or evaluation metric.
- Rename the registered model in Unity Catalog.

## Step-by-step

1. **Pick the algorithm for the problem type.**
   - **Regression**: `LinearRegression`, `XGBRegressor`, `LGBMRegressor`,
     `RandomForestRegressor`, etc.
   - **Classification**: `RandomForestClassifier`, `LogisticRegression`,
     `XGBClassifier`, etc.
   - **Clustering**: `KMeans`, `DBSCAN`, etc. — note: no target column.
   - **Forecasting**: Prophet, ARIMA, or DL approaches.

2. **Update `features` and `target`.** Match the columns produced by the
   adapted data ingestion notebook. For clustering, drop the `target`
   variable and any train/test split that depends on it.

3. **Update logged metrics.** Choose metrics appropriate to the problem
   type:
   - Regression → `rmse`, `mae`, `r2`.
   - Classification → `accuracy`, `f1`, `precision`, `recall`, `roc_auc`.
   - Clustering → `silhouette_score`, `davies_bouldin_score`.

4. **Update best-run selection.** Change `selected_metric` to the metric you
   actually optimize, and flip the direction (`maximize` vs `minimize`)
   accordingly.

5. **Rename the registered model.** Update `model_name` (currently
   `iris_model`) and keep the three-level reference
   `{catalog_name}.{schema_name}.<model_name>`.

6. **Keep the Challenger alias.** Register every new training run with the
   `@challenger` alias. The deployment pipeline will promote it to
   `@champion` later. Do not write `@champion` from the training notebook.

7. **Let the signature stay inferred.** `mlflow.models.infer_signature` is
   driven by the `X_train` / `y_train` you pass in — just make sure they are
   representative.

8. **Sync the training job YAML.** Update
   `resources/2_1_model_training_job.yml`:
   - Task `notebook_path` if you rename the notebook.
   - `base_parameters` if you add new widgets.
   - `email_notifications.on_failure` to the team's address.

## Parameterization contract

Keep widgets for `catalog_name` and `schema_name`. The MLflow experiment
should remain user-scoped — `/{user}/{model}_{catalog}` — to avoid
collisions when multiple developers train in parallel. See
`mlops-quickstart-overview` for the full contract.

## Edge cases

- **Clustering**: remove evaluation steps that depend on a target column
  (e.g. accuracy). Use unsupervised metrics like silhouette score.
- **Imbalanced classification**: log `f1_weighted` or `roc_auc` instead of
  raw accuracy; consider class weights or resampling.
- **Forecasting with seasonality**: log the model artifact plus a holdout
  forecast plot. Track both point metrics (RMSE) and percentile errors
  (MAPE, sMAPE).
- **Hyperparameter search**: wrap runs inside a parent MLflow run and rely
  on the existing best-run selection logic to pick the registered version.
- **Deep learning**: log the model with `mlflow.pyfunc` or framework-native
  flavor (`mlflow.pytorch`, `mlflow.tensorflow`) — the rest of the pipeline
  is flavor-agnostic.
