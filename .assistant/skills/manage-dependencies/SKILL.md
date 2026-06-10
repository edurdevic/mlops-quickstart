---
name: manage-dependencies
description: >-
  Manage Python dependencies for the MLOps Quickstart via the root
  `requirements.txt` file. Use when the user wants to add, remove, or upgrade a
  Python package, pin or unpin a library version, fix a dependency conflict, or
  understand how notebooks install their dependencies.
---

# Manage Dependencies

Target file: `requirements.txt` (repo root).

## Convention

- **`requirements.txt` is the single source of truth** for every pinned
  Python library version used by the notebooks.
- Every notebook installs from it with one cell at the top:

  ```python
  %pip install -r ../../requirements.txt        # 2 levels deep
  # or
  %pip install -r ../../../requirements.txt     # 3 levels deep (model_deployment/)
  dbutils.library.restartPython()
  ```

- **Never pin a version inside a notebook.** Always edit `requirements.txt`.
- **Only pin libraries DBR does not already ship at a suitable version.**
  Pinning a library DBR provides (scikit-learn, pandas, requests, numpy,
  …) at a *different* version than what DBR ships risks deserialization
  errors when the eval/inference notebooks load older MLflow model
  artifacts that were saved against the DBR-shipped version. The current
  pins are limited to `mlflow` (needed for the MLflow 3 deployment job
  pattern) and `databricks-sdk` (used by the serving endpoint code).

## When to use

Use this skill whenever the user wants to:

- Add a new Python library the notebooks need.
- Upgrade or downgrade an existing pin (e.g. bump MLflow).
- Resolve a dependency conflict between `requirements.txt` and the
  Databricks Runtime / serverless environment.
- Remove a library the project no longer uses.

## Step-by-step

1. **Edit `requirements.txt` only.** Keep entries pinned (`pkg==X.Y.Z`).
   Pinning ensures reproducible runs across dev, staging, and prod.

2. **Match Databricks Runtime versions when possible.** When the chosen
   pin conflicts with what the serverless environment or DBR ML provides,
   either:
   - Update the pin to match what the runtime ships, or
   - Confirm the pip resolver can install the requested version on top
     (some libraries can be upgraded, others are baked in).

3. **Do not touch the `%pip install -r …` cells in notebooks.** They use
   relative paths (`../../requirements.txt` from notebooks at depth 2,
   `../../../requirements.txt` from notebooks at depth 3). If a new
   notebook is added, mirror the same pattern at the correct depth.

4. **Verify locally where possible.** Before deploying, run the affected
   notebook once interactively (or `databricks bundle run <job>`) so the
   pip install actually executes against the target compute.

## Path depth reference

| Notebook location | Relative path |
|-------------------|---------------|
| `notebooks/1_data_preprocessing/*.ipynb` | `../../requirements.txt` |
| `notebooks/2_model_training_and_deployment/*.ipynb` | `../../requirements.txt` |
| `notebooks/2_model_training_and_deployment/model_deployment/*.ipynb` | `../../../requirements.txt` |
| `notebooks/3_inference/*.ipynb` | `../../requirements.txt` |

## Edge cases

- **Library bundled with DBR/serverless**: pinning the same version it
  already provides is a no-op. Pinning a different version may fail if
  the library is "frozen" by the runtime. Test before merging.
- **Transitive conflict**: when `pkg-a==X` and `pkg-b==Y` disagree on a
  shared transitive dep, prefer pinning the transitive dep directly in
  `requirements.txt` rather than loosening the top-level pins.
- **GPU / accelerated wheels**: install from the correct index URL by
  adding `--extra-index-url <url>` at the top of `requirements.txt` (one
  per line, before any package lines).
- **Private packages**: workspace files or UC volumes can host private
  wheels — reference them with the full `/Volumes/...` or
  `/Workspace/...` path inside `requirements.txt`.
- **Adding a brand-new notebook**: when adding a notebook at a new depth,
  always include the install cell at the top with the correct relative
  path to `requirements.txt`.
