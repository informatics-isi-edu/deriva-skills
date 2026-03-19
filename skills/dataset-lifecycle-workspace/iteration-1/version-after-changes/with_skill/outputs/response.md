# What to Do Before Running Your Next Experiment

## Summary of the Situation

You have made two types of changes to the catalog since dataset 28EA was last versioned at 0.3.0:

1. **Added 200 new fundus images** — a minor change (new members/data)
2. **Fixed labels on ~30 mislabeled images** — a patch change (bug fix / correction)

Neither of these changes is visible in version 0.3.0, because existing versions are frozen snapshots. You must increment the dataset version to capture the current catalog state, then update your training config before running the next experiment.

---

## Step-by-Step Plan

### Step 1: Start an execution for provenance tracking

```
create_execution(
  workflow_name="Dataset Curation",
  workflow_type="Data Management"
)
start_execution()
```

This records the versioning operation in the catalog's provenance log.

---

### Step 2: Confirm dataset 28EA's current state

```
get_record(table_name="Dataset", rid="28EA")
```

Verify the current version is still 0.3.0 and review the description so you can write an accurate version description.

---

### Step 3: Verify the new images are members of dataset 28EA

If the 200 new fundus images have already been added as members of dataset 28EA (via `add_dataset_members`), the minor version was auto-incremented at that time and the current version may already be higher than 0.3.0. Check what version the dataset is currently at.

If the new images have NOT yet been added as members:

```
add_dataset_members(
  dataset_rid="28EA",
  member_rids=["<RID-1>", "<RID-2>", ...]
)
```

`add_dataset_members` auto-increments the minor version (e.g., 0.3.0 → 0.4.0).

---

### Step 4: Increment version for the label fixes (patch bump)

The label corrections are a bug fix — a patch-level change. After confirming the new images are members, increment the version with a description explaining both changes:

```
increment_dataset_version(
  dataset_rid="28EA",
  description="Added 200 new fundus images from yesterday's collection (minor). Fixed mislabeled ground-truth annotations on ~30 images identified in audit (patch). Retraining recommended — v0.3.0 models trained on incorrect labels for those 30 images."
)
```

Which version component to bump depends on what has happened so far:

| Scenario | Bump | Resulting version |
|----------|------|-------------------|
| Images were added via `add_dataset_members` (auto-incremented to 0.4.0), label fixes not yet versioned | patch | 0.4.1 |
| Neither change versioned yet | minor first (add members) then patch (label fix) | 0.4.0 → 0.4.1 |

---

### Step 5: Confirm the new version

```
get_dataset_spec(dataset_rid="28EA")
```

This returns the correct `DatasetSpecConfig` string with the current version. Note the new version number — it will be something like `0.4.1`.

---

### Step 6: Stop the execution

```
stop_execution()
```

---

### Step 7: Update your training config

In your Hydra-zen config, replace the old version reference:

```python
# Before
DatasetSpecConfig(rid="28EA", version="0.3.0")

# After (example — use the actual version from Step 5)
DatasetSpecConfig(rid="28EA", version="0.4.1")
```

---

### Step 8: Commit the config change before running

```bash
git add <your-config-file>
git commit -m "Update dataset 28EA version to 0.4.1 (new images + label fixes)"
```

The git commit hash stored in the execution record must match the config state. Never run an experiment before committing the config.

---

## Pre-Experiment Checklist

- [ ] Dataset version incremented to capture new images
- [ ] Dataset version incremented to capture label fixes (with descriptive message)
- [ ] `get_dataset_spec` confirms the new version
- [ ] Training config updated from `version="0.3.0"` to the new version
- [ ] Config changes committed to git

---

## Versioning Rationale

Per the dataset-lifecycle skill's semantic versioning rules:

| Change | Component | Reason |
|--------|-----------|--------|
| 200 new fundus images added | **Minor** (0.X.0) | New data / non-breaking addition |
| Fixed ~30 mislabeled images | **Patch** (0.0.X) | Bug fix / metadata correction |

Because both changes are present, the version should advance at least one minor bump (for the new images) and one patch bump (for the label fixes). If the images were added by `add_dataset_members` already, that auto-incremented the minor version; you only need the explicit patch increment for the label corrections.

> Important: models trained on 0.3.0 may have learned from incorrect labels for those ~30 images. Retraining on the corrected version is recommended.
