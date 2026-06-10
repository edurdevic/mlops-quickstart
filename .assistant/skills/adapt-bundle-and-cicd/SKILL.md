---
name: adapt-bundle-and-cicd
description: >-
  Adapt the MLOps Quickstart Databricks Asset Bundle (databricks.yml,
  resources/*.yml) and CI/CD pipelines (Azure DevOps, GitHub Actions). Use when
  the user wants to rename the bundle, change catalog/schema per environment,
  add a staging target, configure permissions, switch from serverless to job
  clusters, or wire up secrets and branch triggers for deployment.
---

# Adapt the Bundle and CI/CD

Target files:

- `databricks.yml` — bundle config (targets, variables, permissions).
- `resources/*.yml` — one DAB job definition per file.
- `azure_pipelines.yml` — Azure DevOps CD pipeline.
- `.github/workflows/databricks_deployment.yml` — GitHub Actions CD pipeline.

## When to use

Use this skill whenever the user wants to:

- Rename the bundle or change per-environment catalogs/schemas.
- Add a staging (or other intermediate) target.
- Adjust permissions per environment.
- Switch from serverless to dedicated job clusters.
- Wire up CI/CD with their own service principal and branch mapping.

## Step-by-step: `databricks.yml`

1. **Rename the bundle.** Change `bundle.name` to your project name. It is
   used to namespace deployments (`/Workspace/.../bundle/<bundle.name>/...`).

2. **Set per-target catalogs/schemas.** Update
   `targets.<env>.variables.catalog_name` and `schema_name` to the
   customer's UC namespace. Keep a separate catalog per environment for
   data isolation (e.g. `myproject_dev`, `myproject_prod`).

3. **Update permission groups.** Replace `PowerUsers` / `Developers` with
   the customer's groups. Match dev to broader access and prod to a
   narrower group.

4. **Add new bundle-level variables** under the top-level `variables` block
   if notebooks need extra parameters (e.g. `feature_store_name`,
   `notification_email`).

## Step-by-step: `resources/*.yml`

For each job YAML:

- Rename `name` / `task_key` / `description` to reflect the customer's
  pipeline.
- Update `notebook_path` if notebooks are renamed or moved.
- Add or rename `base_parameters` to match any new widgets.
- Replace `your.name@address.com` in `email_notifications.on_failure`.
- **Switch to dedicated job clusters** (cost optimization vs. serverless)
  by uncommenting the `job_clusters` block and assigning each task a
  `job_cluster_key`. Otherwise tasks default to serverless.

## Adding a staging environment

The template ships with `dev` and `prod`. To add an intermediate `staging`
target:

1. **In `databricks.yml`**, add a target block between `dev` and `prod`:

   ```yaml
   staging:
     mode: production
     workspace:
       root_path: /Workspace/Users/${workspace.current_user.userName}/.bundle/${bundle.name}/${bundle.target}
     variables:
       catalog_name: <your_staging_catalog>
       schema_name: default
       environment: staging
     resources:
       jobs:
         data_ingestion_job:
           permissions:
             - level: "CAN_MANAGE"
               group_name: "PowerUsers"
             - level: "CAN_MANAGE_RUN"
               group_name: "Developers"
         # ... repeat for each job
   ```

   Use a dedicated staging catalog (e.g. `myproject_staging`) to keep data
   isolated.

2. **In CI/CD**, add a branch trigger:
   - **Azure DevOps** (`azure_pipelines.yml`): add `staging` to
     `branches.include` and extend the environment-detection script with a
     condition mapping `refs/heads/staging` → `--target staging`.
   - **GitHub Actions** (`.github/workflows/databricks_deployment.yml`):
     add a condition that runs `databricks bundle deploy --target staging`
     on pushes to the `staging` branch.

3. **Service principal**: if staging lives in a different workspace, add
   separate `DATABRICKS_CLIENT_ID` / `DATABRICKS_CLIENT_SECRET` secrets and
   make the pipeline pick the right pair based on the branch.

4. **Branch strategy**: a typical flow is
   `feature/* → dev → staging → master/main`. Protect `staging` with
   required reviews and status checks before promoting to prod.

## CI/CD configuration

### Azure DevOps (`azure_pipelines.yml`)

- Update `WORKSPACE_HOST_NAME` to your workspace URL.
- Add `DATABRICKS_CLIENT_ID` and `DATABRICKS_CLIENT_SECRET` as pipeline
  secrets.
- Default branch mapping: `dev` → `--target dev`; `master`/`main` →
  `--target prod`.

### GitHub Actions (`.github/workflows/databricks_deployment.yml`)

- Update `WORKSPACE_HOST_NAME` (repo variable or workflow input).
- Add `DATABRICKS_CLIENT_ID` and `DATABRICKS_CLIENT_SECRET` as repo
  secrets.
- Default branch mapping: `dev` → dev target; `main`/`master` → prod
  target.

## Parameterization contract

The bundle is the source of truth for `catalog_name`, `schema_name`, and
`environment`. Notebooks must read these via widgets, jobs must pass them
via `base_parameters`, and the variable defaults live in `databricks.yml`.
See `mlops-quickstart-overview` for the full contract.

## Edge cases

- **Shared workspace, separate catalogs**: when dev/prod share a workspace,
  per-target `catalog_name` is enough to keep data isolated. Use separate
  service principals if you need per-environment audit trails.
- **Cross-workspace deployments**: each target should reference its own
  `workspace.host` (or rely on the CLI profile selected by the pipeline).
- **First-time deploy**: run `databricks bundle validate --target <env>`
  before `deploy`. It catches missing variables, bad permissions, and
  notebook path typos.
- **Permissions drift**: if a job's permissions in the UI no longer match
  the YAML, the next `bundle deploy` will reset them. This is intentional —
  the bundle is the source of truth.
- **`mode: development` vs `mode: production`**: `dev` uses development
  mode (prefixed names, single-user run-as) while `staging`/`prod` use
  production mode. Don't mix.
