---
name: execution-lifecycle
description: "ALWAYS use this skill when running ML experiments, creating executions, managing workflow provenance, pre-flight validation, or configuring experiment runs in DerivaML. Covers the full execution lifecycle: pre-flight checks (validate RIDs, check cache, prefetch data), creating and running executions via MCP tools or Python API, managing inputs/outputs with provenance, uploading results, nested executions, dry runs, and the deriva-ml-run CLI. Triggers on: 'run experiment', 'create execution', 'execution lifecycle', 'upload outputs', 'pre-flight', 'dry run', 'validate before running', 'cache dataset', 'workflow provenance', 'deriva-ml-run', 'multirun', 'sweep', 'check git before running', 'nested execution', 'restore execution', 'track my work'."
disable-model-invocation: true
---

# Execution Lifecycle in DerivaML

An execution is the fundamental unit of provenance in DerivaML. It records what work was done, with what inputs (datasets, assets), what outputs were produced, and what code and configuration were used.

For background on the execution hierarchy, statuses, workflows, nested executions, dry run mode, and the working directory layout, see `references/concepts.md`.

## Prerequisite: Connect to a Catalog

All execution operations require an active catalog connection:

```
connect_catalog(hostname="...", catalog_id="...")
```

If already connected (check `deriva://catalog/connections`), skip this step.

## Phase 1: Pre-Flight Validation

Before running an experiment, validate that everything is in place. **Stop and fix any issues.**

### Step 1: Resolve the configuration

Before validating anything, you need to know what the configuration specifies. Identify all dataset RIDs, asset RIDs, and versions that will be used:

**For CLI runs** — inspect the resolved config:
```bash
uv run deriva-ml-run +experiment=baseline --info
```
Extract the dataset RIDs and versions from the resolved `datasets` group, and asset RIDs from the `assets` group.

**For MCP tool runs** — the user provides the RIDs directly in the `create_execution` call. Collect them before proceeding.

**For Python API runs** — read the `ExecutionConfiguration` or the hydra-zen config module to extract dataset and asset references.

### Step 2: Validate all RIDs and versions

```
validate_rids(
    dataset_rids=["28CT", "28D0"],
    asset_rids=["3WSE"],
    dataset_versions={"28CT": "0.9.0"}
)
```

This checks that all RIDs exist in the catalog, versions are valid, and warns about missing descriptions. Catches typos, deleted datasets, and wrong version numbers before runtime.

**Stop if any errors.** Fix the configuration before proceeding.

### Step 3: Check data readiness and decide whether to stage

For each dataset in the config, check cache status and size:

```
bag_info(dataset_rid="28CT", version="0.9.0")
```

Returns size info AND cache status:
- `not_cached` → will need to download (check `total_asset_size` to estimate time)
- `cached_metadata_only` → table data present, assets need materialization
- `cached_materialized` → ready to go, no download needed
- `cached_incomplete` → needs re-materialization

**Decision: should you stage data before running?**

| Situation | Action |
|-----------|--------|
| Small dataset (<100 MB), not cached | Let execution download it — fast enough |
| Large dataset (>1 GB), not cached | **Stage first** with `cache_dataset` |
| Any dataset, `cached_materialized` | No action needed — will use cache |
| Asset (model weights), not cached | **Stage first** with `cache_dataset(asset_rid=...)` |

### Step 4: Stage data if needed

For datasets:
```
cache_dataset(dataset_rid="28CT", version="0.9.0")
```

For individual assets (model weights, etc.):
```
cache_dataset(asset_rid="3WSE")
```

These download into the local cache without creating execution records. Subsequent `download_execution_dataset` / `download_asset` calls will use the cached copy.

### Step 5: Code and environment checks (CLI runs)

For `deriva-ml-run` CLI experiments:

1. **Git clean** — `git status` must show no uncommitted changes
2. **Version current** — bump with `uv run bump-version patch|minor` if needed
3. **Lock file valid** — `uv lock --check` must pass

### Step 6: User confirmation

Present a summary before production runs:
- Commit hash, version, branch
- Experiment name and key parameters
- Dataset versions and cache status (all should be `cached_materialized` after staging)
- Get explicit approval

## Phase 2: Create and Run

There are three ways to run an execution, depending on context:

### Path A: MCP Tools (interactive, Claude-driven)

```
create_execution(workflow_name="Training", workflow_type="Training",
                 description="Train CNN on labeled images",
                 dataset_rids=["28CT"], asset_rids=["3WSE"])
start_execution()

# Download inputs
download_execution_dataset(dataset_rid="28CT", version="0.9.0")
download_asset(asset_rid="3WSE")

# ... do work ...

# Register outputs
asset_file_path(asset_name="Execution_Asset", file_name="model.pt")

# Add feature values if applicable
add_feature_value(table_name="Image", feature_name="Prediction",
                  entries=[...])

stop_execution()
upload_execution_outputs()
```

Steps 2-7 operate on the **active execution** — no `execution_rid` parameter needed.

### Path B: Python API (in scripts)

```python
config = ExecutionConfiguration(
    workflow=workflow,
    datasets=["28CT"],
    assets=["3WSE"],
    description="Train CNN on labeled images"
)
with ml.create_execution(config) as exe:
    for dataset in exe.datasets:
        dataset.restructure_assets(...)
    # ... do work ...
    path = exe.asset_file_path("Execution_Asset", "model.pt")
    # ... write to path ...

# Upload AFTER the with block
exe.upload_execution_outputs()
```

### Path C: CLI (deriva-ml-run)

```bash
# Dry run first
uv run deriva-ml-run +experiment=baseline dry_run=True

# Production run
uv run deriva-ml-run +experiment=baseline

# With overrides
uv run deriva-ml-run +experiment=baseline model_config.learning_rate=0.001

# Named multirun (parameter sweep)
uv run deriva-ml-run +multirun=lr_sweep
```

The CLI runner handles the full lifecycle automatically: creates execution, downloads data, runs the model function, uploads outputs, sets status.

## Phase 3: Verify Results

After a run, verify the execution was recorded correctly:

```
# Check execution details
Read resource: deriva://execution/{execution_rid}

# Rich view with config and parameters
Read resource: deriva://experiment/{execution_rid}

# Get Chaise web UI link
cite(rid="{execution_rid}", current=True)
```

Verify:
- Status is "Completed" (not "Running" or "Failed")
- Correct input datasets and assets are linked
- Output assets are attached
- Git commit hash matches your code

## Critical Rules

1. **Every execution needs a workflow** — find with `lookup_workflow_by_url` or let `create_execution` create one
2. **Upload AFTER the with block** — `exe.upload_execution_outputs()` goes after `with`, not inside
3. **Use `asset_file_path` for all outputs** — never manually place files in the working directory
4. **Commit code before running** — git hash is recorded for provenance
5. **Dry run first** — test with `dry_run=True` before production runs
6. **Validate before running** — `validate_rids` + `bag_info` catches config errors early

## Key Tools

| Tool | Purpose |
|------|---------|
| `validate_rids` | Pre-flight: verify RIDs and versions exist |
| `bag_info` | Pre-flight: check dataset size and cache status |
| `cache_dataset` | Pre-flight: download data into cache without execution |
| `create_execution` | Create execution (finds/creates workflow automatically) |
| `start_execution` / `stop_execution` | Manage lifecycle timing |
| `download_execution_dataset` | Download dataset as BDBag within execution |
| `download_asset` | Download individual asset within execution |
| `asset_file_path` | Register output file for upload |
| `upload_execution_outputs` | Upload all registered files to catalog |
| `get_execution_info` | Active execution details |
| `update_execution_status` | Progress tracking |
| `restore_execution` | Re-download previous execution's inputs |
| `add_nested_execution` | Link parent-child executions |

## Reference Resources

- `references/concepts.md` — Execution hierarchy, statuses, workflows, nested executions, dry run, working directory, data flow
- `references/workflow.md` — Step-by-step MCP and Python API workflows with complete examples
- `references/cli-reference.md` — deriva-ml-run CLI commands, Hydra overrides, multirun syntax
- `deriva://execution/{execution_rid}` — Execution details and status
- `deriva://experiment/{execution_rid}` — Rich view with Hydra config and parameters
- `deriva://execution/{execution_rid}/inputs` — Input datasets and assets
- `deriva://catalog/workflows` — Available workflows
- `deriva://catalog/workflow-types` — Workflow type vocabulary terms

## Related Skills

- **`configure-experiment`** — Setting up Hydra-zen config groups and experiment presets
- **`write-hydra-config`** — Python API patterns for each config type
- **`run-notebook`** — Notebook-specific creation and development cycle
- **`dataset-lifecycle`** — Creating and versioning the datasets that executions consume
- **`create-feature`** — Creating features whose values are produced by executions
- **`prepare-training-data`** — Restructuring downloaded data for ML frameworks
