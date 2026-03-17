# Dataset Versioning Semantics

## Table of Contents

- [How Versions Work](#how-versions-work)
- [Snapshot Mechanics](#snapshot-mechanics)
- [Automatic Versioning](#automatic-versioning)
- [Manual Version Increments](#manual-version-increments)
- [Semantic Versioning Decisions](#semantic-versioning-decisions)
- [Version History](#version-history)
- [Working with Versioned Data](#working-with-versioned-data)
- [Versions in Executions](#versions-in-executions)
- [Split Datasets and Versioning](#split-datasets-and-versioning)
- [Common Pitfalls](#common-pitfalls)
- [Pre-Experiment Checklist](#pre-experiment-checklist)

---

## How Versions Work

Every dataset in DerivaML has a version number using semantic versioning (`major.minor.patch`). A version is not just a label — it is bound to a **catalog snapshot**, a frozen view of the catalog at the moment the version was created. This means:

- The same dataset RID + version always produces the same data
- Changes to the catalog after the version was created are invisible to that version
- Downloading the same version repeatedly yields identical results

Versions start at `0.1.0` when a dataset is first created.

## Snapshot Mechanics

When a dataset version is created (either automatically or manually), DerivaML records a **catalog snapshot ID** — a server-side timestamp that pins the version to the exact catalog state at that instant.

### What the snapshot captures

- All records in the catalog at that moment (not just dataset members)
- All feature values, vocabulary terms, and metadata
- All foreign key relationships

### What the snapshot does NOT capture

- Future record additions or deletions
- Future feature value changes or corrections
- Future vocabulary term additions
- Changes to records already in the dataset (e.g., corrected labels)

### The version trap

This is the most common source of confusion: **a version captures the catalog state, not just the dataset membership**. If you:

1. Create a dataset and add 100 images → version `0.1.0`
2. Upload feature values for those images
3. Download version `0.1.0`

The download will **not** include the feature values from step 2, because they were added after the version was created. You must call `increment_dataset_version` after step 2 to create a new version that includes those features.

## Automatic Versioning

DerivaML automatically increments the **minor** version when:
- Members are added to a dataset via `add_dataset_members`
- Members are removed via `delete_dataset_members`
- A split is performed via `split_dataset`

This means you don't need to manually increment after membership changes — the system handles it. However, the automatic increment does **not** happen for:
- Adding or modifying feature values
- Changing vocabulary terms
- Updating record metadata
- Schema changes

For these, you must increment manually.

## Manual Version Increments

### MCP tool

```
increment_dataset_version(
    dataset_rid="2-XXXX",
    description="Added severity grading feature to all 12,450 images"
)
```

The `description` is strongly recommended. It appears in the version history and helps track what changed.

### Python API

```python
from deriva_ml.dataset.aux_classes import VersionPart

# Default: increment minor version
new_version = dataset.increment_dataset_version(
    description="Added severity grading feature"
)

# Explicit component selection
new_version = dataset.increment_dataset_version(
    component=VersionPart.major,
    description="Changed Image schema — added Width/Height columns"
)

new_version = dataset.increment_dataset_version(
    component=VersionPart.patch,
    description="Fixed 47 mislabeled pneumonia images"
)
```

## Semantic Versioning Decisions

| Version Component | When to Increment | Examples |
|-------------------|-------------------|----------|
| **Major** (X.0.0) | Breaking changes that would invalidate models trained on previous versions | Schema changes (new required columns, removed columns), restructured element types, changed feature definitions |
| **Minor** (0.X.0) | New data or features that extend the dataset without breaking compatibility | Added images, new feature annotations, expanded vocabulary, new dataset members |
| **Patch** (0.0.X) | Corrections that fix errors without changing the dataset's scope | Fixed mislabeled images, corrected metadata typos, updated descriptions |

### Decision guidance

Ask yourself:
- **"Would a model trained on the old version need retraining?"** → Major
- **"Is there more data or new annotations?"** → Minor
- **"Did I fix something that was wrong?"** → Patch

## Version History

### MCP tool

Read the `deriva://dataset/{rid}/versions` resource to see the complete version history, including version numbers, descriptions, and timestamps.

### Python API

```python
history = dataset.dataset_history()
for entry in history:
    print(f"v{entry.version}: {entry.description} ({entry.timestamp})")
```

### Current version

```python
current = dataset.current_version
print(f"Current version: {current}")  # e.g., "1.2.3"
```

### Binding to a specific version

```python
# Get a dataset object pinned to a specific version
versioned = dataset.set_version("1.0.0")

# All operations on `versioned` use the snapshot from v1.0.0
members = versioned.list_dataset_members()
bag = versioned.download_dataset_bag()
```

## Working with Versioned Data

### In configurations (Hydra-Zen)

Always pin to explicit versions in production configurations:

```python
from hydra_zen import builds
from deriva_ml.dataset.aux_classes import DatasetSpecConfig

# Good: explicit version
training_v1 = builds(DatasetSpecConfig, rid="1-ABC4", version="1.2.0")

# Bad: implicit "current" — not reproducible
training = builds(DatasetSpecConfig, rid="1-ABC4")
```

### In MCP tools

```
download_dataset(dataset_rid="2-XXXX", version="1.0.0")
estimate_bag_size(dataset_rid="2-XXXX", version="1.0.0")
```

### When "current" is acceptable

Use "current" (or omit version) only for:
- Interactive exploration and debugging
- Dry runs and previews
- Quick data checks

Never use "current" for:
- Production training runs
- Published results or papers
- Shared experiment configurations

## Versions in Executions

When an execution downloads a dataset, the version is recorded as part of the execution's provenance:

```python
config = ExecutionConfiguration(
    workflow=workflow,
    datasets=[
        DatasetSpec(rid="1-ABC", version="1.2.0"),  # pinned version
    ],
    description="Training run with v1.2.0 data"
)

with ml.create_execution(config) as exe:
    bag = exe.download_dataset_bag(DatasetSpec(rid="1-ABC", version="1.2.0"))
    # ...
```

This creates an auditable chain: execution → dataset version → exact catalog snapshot.

## Split Datasets and Versioning

When `split_dataset` creates child datasets (Training, Testing, Validation), it automatically:

1. Creates a parent "Split" dataset
2. Creates child datasets with members from each partition
3. Increments the version on all created datasets

The child datasets inherit the source dataset's version snapshot. If you later add new data to the source and want updated splits, you must:

1. Increment the source dataset version
2. Run `split_dataset` again (this creates new child datasets — it does not modify old ones)

Old splits remain valid and downloadable at their original versions.

## Common Pitfalls

### Pitfall: "My new features aren't in the download"

**Cause:** You added feature values after the last version increment. The current version's snapshot was taken before the features existed.

**Fix:** `increment_dataset_version(description="Added new features")`, then download the new version.

### Pitfall: "I updated labels but the bag hasn't changed"

**Cause:** Label corrections modify existing records, but old version snapshots still point to the pre-correction state.

**Fix:** `increment_dataset_version(component=VersionPart.patch, description="Corrected mislabeled records")`, then download the new version.

### Pitfall: "My config references version 1.0.0 but the dataset is at 2.1.0"

**Cause:** The dataset was modified and versioned multiple times, but the config was never updated.

**Fix:** This is actually fine if you **want** to use v1.0.0 data — that's the point of version pinning. But if you want the latest data, update the config to the current version and commit.

### Pitfall: "Two experiments have different results from the 'same' dataset"

**Cause:** One used "current" version (which changed between runs), the other used an explicit version.

**Fix:** Always use explicit versions. Check the execution records to see which version each experiment actually used.

### Pitfall: "I deleted members but they're still in the download"

**Cause:** You're downloading an old version that was created before the deletion. Deleting members auto-increments the version, so the new version won't have those members.

**Fix:** Download the latest version (the one created after the deletion).

## Pre-Experiment Checklist

Before running any experiment:

- [ ] Dataset version is explicitly specified in configuration (not "current" or omitted)
- [ ] Configuration file is committed to git
- [ ] Version number matches your intent (check version history if unsure)
- [ ] If catalog was modified since last version, `increment_dataset_version` has been called
- [ ] All affected configuration files reference the new version

After any catalog modification:

- [ ] Version has been incremented with a descriptive message
- [ ] All config files updated to new version
- [ ] Config changes committed to git before running experiments

## Reference Resources

| Resource / Tool | Purpose |
|-----------------|---------|
| `deriva://dataset/{rid}` | Current dataset info including version |
| `deriva://dataset/{rid}/versions` | Version history with descriptions and timestamps |
| `increment_dataset_version` | Create new version snapshot after catalog changes |
| `get_dataset_spec` | View dataset specification and current version |
| `download_dataset` | Download specific version (version parameter) |
| `estimate_bag_size` | Preview what a version contains before downloading |
