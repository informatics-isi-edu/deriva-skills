# Chest X-Ray Training Pipeline: Dataset Creation and 70/15/15 Split

## Overview

This document describes the exact sequence of MCP tool calls to:
1. Create a complete dataset of all ~12,000 labeled chest X-ray images
2. Split it 70/15/15 (train/val/test) with stratified sampling on `Image_Diagnosis.Diagnosis_Image`
3. Mark all three partitions as ground-truth labeled

---

## Phase 1: Assess — Check What Already Exists

Before creating anything, verify no suitable dataset already exists.

**Step 1.1 — Browse existing datasets**

```
query_table(
  table_name="Dataset"
)
```

**Step 1.2 — Check available dataset types**

```
query_table(
  table_name="Dataset_Type"
)
```

**Step 1.3 — Check registered element types**

```
Read resource: deriva://catalog/dataset-element-types
```

If the `Image` table is not listed in the element types response, it must be registered (Step 3.2 below). The call is idempotent, so it is safe to call regardless.

---

## Phase 2: Plan

### Dataset structure

Because we're building from scratch and need train/val/test partitions, the structure is:

```
Chest X-Ray Complete Dataset  (types: Complete, Labeled)
└── Chest X-Ray Split  (type: Split — created automatically by split_dataset)
    ├── Training  (types: Training, Labeled — ~8,400 images, 70%)
    ├── Validation  (types: Validation, Labeled — ~1,800 images, 15%)
    └── Testing  (types: Testing, Labeled — ~1,800 images, 15%)
```

### Stratify column derivation

The task specifies:
- Feature table: `Image_Diagnosis`
- Label column: `Diagnosis_Image`

Following the `{FeatureTableName}_{ColumnName}` convention:

```
stratify_by_column = "Image_Diagnosis_Diagnosis_Image"
include_tables     = ["Image", "Image_Diagnosis"]
```

---

## Phase 3: Create

### Step 3.1 — Create and start an execution for provenance

```
create_execution(
  workflow_name="Dataset Curation",
  workflow_type="Data Management",
  description="Create complete chest X-ray dataset and 70/15/15 stratified split for training pipeline"
)
```

```
start_execution()
```

Record the returned execution RID (e.g., `"2-EXC1"`).

---

### Step 3.2 — Register element type (idempotent)

```
add_dataset_element_type(
  table_name="Image"
)
```

---

### Step 3.3 — Query all labeled chest X-ray image RIDs

To get all image RIDs to include in the complete dataset:

```
query_table(
  table_name="Image"
)
```

This returns all Image records. If the catalog has a filtering mechanism (e.g., a modality column indicating "Chest X-Ray"), apply an appropriate filter. For the purposes of this plan we assume all ~12,000 Image records are the target chest X-ray images.

Collect the full list of RIDs returned (e.g., `["2-IMG1", "2-IMG2", ..., "2-IMG12000"]`).

---

### Step 3.4 — Validate the RIDs (optional but recommended)

For large batches it is recommended to validate a sample first. For 12,000 images, validate all:

```
validate_rids(
  dataset_rids=["2-IMG1", "2-IMG2", ..., "2-IMG12000"]
)
```

Resolve any invalid RIDs before proceeding.

---

### Step 3.5 — Create the complete dataset

```
create_dataset(
  description="All 12,000 labeled chest X-ray images with diagnosis annotations. Complete collection as of 2026-03-18, intended as the source for the 70/15/15 stratified training pipeline.",
  dataset_types=["Complete", "Labeled"]
)
```

Record the returned dataset RID (e.g., `"2-DS01"`).

---

### Step 3.6 — Add all images as members

For 12,000 images, use `members_by_table` for efficiency:

```
add_dataset_members(
  dataset_rid="2-DS01",
  members_by_table={
    "Image": ["2-IMG1", "2-IMG2", ..., "2-IMG12000"]
  },
  description="Initial population: all 12,000 labeled chest X-ray images"
)
```

This auto-increments the dataset version to `0.2.0`.

---

### Step 3.7 — Dry-run the stratified split (preview)

Always preview the split plan before modifying the catalog:

```
split_dataset(
  source_dataset_rid="2-DS01",
  test_size=0.15,
  val_size=0.15,
  seed=42,
  stratify_by_column="Image_Diagnosis_Diagnosis_Image",
  stratify_missing="drop",
  include_tables=["Image", "Image_Diagnosis"],
  dry_run=true
)
```

Review the output to confirm:
- Total images stratified (unlabeled images excluded by `stratify_missing="drop"`)
- Approximately 70/15/15 count breakdown per class
- Class distribution is maintained across partitions

If counts or class distribution look wrong (e.g., too many images dropped due to missing labels), investigate the `Image_Diagnosis` table before proceeding.

---

### Step 3.8 — Execute the stratified split

Once the dry run looks correct:

```
split_dataset(
  source_dataset_rid="2-DS01",
  test_size=0.15,
  val_size=0.15,
  seed=42,
  stratify_by_column="Image_Diagnosis_Diagnosis_Image",
  stratify_missing="drop",
  include_tables=["Image", "Image_Diagnosis"],
  training_types=["Labeled"],
  testing_types=["Labeled"],
  validation_types=["Labeled"],
  split_description="70/15/15 stratified split on Diagnosis_Image label. Seed=42 for reproducibility. Unlabeled images excluded."
)
```

This creates:
- A **Split** parent dataset (e.g., `"2-DS02"`)
- A **Training + Labeled** child (~8,400 images, e.g., `"2-DS03"`)
- A **Validation + Labeled** child (~1,800 images, e.g., `"2-DS04"`)
- A **Testing + Labeled** child (~1,800 images, e.g., `"2-DS05"`)

The source dataset version is auto-incremented to `0.3.0`.

---

### Step 3.9 — Stop the execution

```
stop_execution()
```

---

## Phase 4: Version

After the split is created, record the final version for use in experiment configs.

**Step 4.1 — Get the current version of each split dataset**

```
get_dataset_spec(dataset_rid="2-DS03")   # Training
get_dataset_spec(dataset_rid="2-DS04")   # Validation
get_dataset_spec(dataset_rid="2-DS05")   # Testing
```

Each call returns a `DatasetSpecConfig` string with the pinned version. Example output:

```
DatasetSpecConfig(rid="2-DS03", version="0.1.0")  # Training
DatasetSpecConfig(rid="2-DS04", version="0.1.0")  # Validation
DatasetSpecConfig(rid="2-DS05", version="0.1.0")  # Testing
```

---

## Phase 5: Verify

### Step 5.1 — Confirm the hierarchy

```
list_dataset_children(
  dataset_rid="2-DS01",
  recurse=true
)
```

Expected: The Split parent and the three partition children.

### Step 5.2 — Spot-check member counts

```
list_dataset_members(dataset_rid="2-DS03")   # Training — expect ~8,400
list_dataset_members(dataset_rid="2-DS04")   # Validation — expect ~1,800
list_dataset_members(dataset_rid="2-DS05")   # Testing — expect ~1,800
```

### Step 5.3 — Browse in Chaise (optional)

```
cite(rid="2-DS01")   # Permanent URL for the complete dataset
cite(rid="2-DS03")   # Permanent URL for the training split
```

---

## Summary of Tool Calls (in order)

| # | Tool | Key Parameters |
|---|------|---------------|
| 1 | `query_table` | `table_name="Dataset"` |
| 2 | `query_table` | `table_name="Dataset_Type"` |
| 3 | Read resource | `deriva://catalog/dataset-element-types` |
| 4 | `create_execution` | `workflow_name="Dataset Curation"`, `workflow_type="Data Management"` |
| 5 | `start_execution` | — |
| 6 | `add_dataset_element_type` | `table_name="Image"` |
| 7 | `query_table` | `table_name="Image"` (collect RIDs) |
| 8 | `validate_rids` | `dataset_rids=[...all 12,000 RIDs...]` |
| 9 | `create_dataset` | `dataset_types=["Complete", "Labeled"]` |
| 10 | `add_dataset_members` | `dataset_rid="2-DS01"`, `members_by_table={"Image": [...]}` |
| 11 | `split_dataset` | dry_run=true, 70/15/15, stratified on `Image_Diagnosis_Diagnosis_Image` |
| 12 | `split_dataset` | dry_run=false (live), with `*_types=["Labeled"]` |
| 13 | `stop_execution` | — |
| 14 | `get_dataset_spec` | Training, Validation, Testing RIDs (one call each) |
| 15 | `list_dataset_children` | `dataset_rid="2-DS01"`, `recurse=true` |
| 16 | `list_dataset_members` | Training, Validation, Testing (spot-check) |

---

## Pre-Experiment Checklist

Before using these datasets in training:

- [ ] Version explicitly specified in all configs (not "current")
- [ ] Configs updated with correct `DatasetSpecConfig(rid=..., version=...)`
- [ ] Config changes committed to git before any experiment run
- [ ] `estimate_bag_size` run on training split to verify expected row counts and asset sizes
