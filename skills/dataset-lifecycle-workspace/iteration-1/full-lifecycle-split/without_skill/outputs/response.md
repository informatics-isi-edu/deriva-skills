# Chest X-Ray Training Pipeline: Dataset Creation and Stratified Splitting

## Overview

This document describes the exact sequence of DerivaML MCP tool calls needed to:
1. Create a complete dataset containing all ~12,000 labeled chest X-ray images
2. Split it 70/15/15 into train/validation/test sets with stratified sampling on the `Diagnosis_Image` column from the `Image_Diagnosis` feature table
3. Mark ground truth labels on each split

---

## Step 1: Connect to the Catalog

```
mcp__deriva__connect_catalog(
  hostname = "<your-deriva-host>",
  catalog_id = "<your-catalog-id>"
)
```

Set it as the active catalog:

```
mcp__deriva__set_active_catalog(
  hostname = "<your-deriva-host>",
  catalog_id = "<your-catalog-id>"
)
```

---

## Step 2: Verify the Feature Table and Label Column

Confirm the `Image_Diagnosis` feature table exists and inspect the `Diagnosis_Image` column before building any datasets.

```
mcp__deriva__get_table(
  schema_name = "deriva-ml",
  table_name = "Image_Diagnosis"
)
```

Take a sample to understand the label distribution:

```
mcp__deriva__get_table_sample_data(
  schema_name = "deriva-ml",
  table_name = "Image_Diagnosis",
  sample_size = 100
)
```

Count total labeled records:

```
mcp__deriva__count_table(
  schema_name = "deriva-ml",
  table_name = "Image_Diagnosis"
)
```

---

## Step 3: Create the Full Dataset

Create a dataset that will hold all ~12,000 images. This becomes the source dataset for the splits.

```
mcp__deriva__create_dataset(
  dataset_name = "chest-xray-full",
  description = "Complete set of ~12,000 labeled chest X-ray images for training pipeline"
)
```

Note the returned `Dataset_RID` — call it `FULL_DATASET_RID` for subsequent steps.

---

## Step 4: Add All Images to the Full Dataset

Populate the full dataset by adding the Image records that have `Image_Diagnosis` labels. The members are identified by their RIDs.

First, query all Image RIDs that have a label in `Image_Diagnosis`:

```
mcp__deriva__query_table(
  schema_name = "deriva-ml",
  table_name = "Image_Diagnosis",
  filters = []
)
```

This returns a list of `Image_RID` values (and their associated `Diagnosis_Image` label). Collect all `Image_RID` values.

Then add them as dataset members:

```
mcp__deriva__add_dataset_members(
  dataset_rid = "<FULL_DATASET_RID>",
  table_name = "Image",
  member_rids = ["<rid_1>", "<rid_2>", ..., "<rid_12000>"]
)
```

> Note: If the dataset member API supports batch inserts in chunks, submit in batches of 500–1000 RIDs to avoid timeouts.

---

## Step 5: Increment the Dataset Version

Before splitting, lock in a stable version of the full dataset.

```
mcp__deriva__increment_dataset_version(
  dataset_rid = "<FULL_DATASET_RID>"
)
```

---

## Step 6: Create the Three Split Datasets

Create empty destination datasets for each split:

```
mcp__deriva__create_dataset(
  dataset_name = "chest-xray-train",
  description = "Training split (70%) — stratified on Diagnosis_Image"
)
```
→ `TRAIN_DATASET_RID`

```
mcp__deriva__create_dataset(
  dataset_name = "chest-xray-val",
  description = "Validation split (15%) — stratified on Diagnosis_Image"
)
```
→ `VAL_DATASET_RID`

```
mcp__deriva__create_dataset(
  dataset_name = "chest-xray-test",
  description = "Test split (15%) — stratified on Diagnosis_Image"
)
```
→ `TEST_DATASET_RID`

---

## Step 7: Perform Stratified Splitting

DerivaML's `split_dataset` tool supports stratified splitting. Call it on the full dataset with the desired ratios and the feature/column to stratify on:

```
mcp__deriva__split_dataset(
  dataset_rid = "<FULL_DATASET_RID>",
  split_ratios = [0.70, 0.15, 0.15],
  split_names = ["train", "val", "test"],
  stratify_feature = "Image_Diagnosis",
  stratify_column = "Diagnosis_Image",
  output_dataset_rids = [
    "<TRAIN_DATASET_RID>",
    "<VAL_DATASET_RID>",
    "<TEST_DATASET_RID>"
  ],
  random_seed = 42
)
```

This call:
- Reads `Diagnosis_Image` from the `Image_Diagnosis` feature table for each image in the full dataset
- Groups images by diagnosis label
- Samples 70/15/15 from each label group proportionally (stratified)
- Populates the three destination datasets with the resulting member RIDs

---

## Step 8: Mark Ground Truth Labels on Each Split

After splitting, denormalize/attach the `Image_Diagnosis` feature labels into each split dataset so each split carries ground truth. Use `add_feature_value_record` for each split, or `denormalize_dataset` to embed the feature values directly.

### Option A — Denormalize features into each split dataset

```
mcp__deriva__denormalize_dataset(
  dataset_rid = "<TRAIN_DATASET_RID>",
  feature_table = "Image_Diagnosis",
  label_column = "Diagnosis_Image"
)
```

```
mcp__deriva__denormalize_dataset(
  dataset_rid = "<VAL_DATASET_RID>",
  feature_table = "Image_Diagnosis",
  label_column = "Diagnosis_Image"
)
```

```
mcp__deriva__denormalize_dataset(
  dataset_rid = "<TEST_DATASET_RID>",
  feature_table = "Image_Diagnosis",
  label_column = "Diagnosis_Image"
)
```

### Option B — Add a dataset-level feature value marking it as ground truth

```
mcp__deriva__add_feature_value_record(
  table_name = "Dataset",
  record_rid = "<TRAIN_DATASET_RID>",
  feature_name = "Dataset_Split",
  feature_values = {"Split_Type": "train", "Is_Ground_Truth": true}
)
```

```
mcp__deriva__add_feature_value_record(
  table_name = "Dataset",
  record_rid = "<VAL_DATASET_RID>",
  feature_name = "Dataset_Split",
  feature_values = {"Split_Type": "val", "Is_Ground_Truth": true}
)
```

```
mcp__deriva__add_feature_value_record(
  table_name = "Dataset",
  record_rid = "<TEST_DATASET_RID>",
  feature_name = "Dataset_Split",
  feature_values = {"Split_Type": "test", "Is_Ground_Truth": true}
)
```

---

## Step 9: Nest the Splits Under the Full Dataset

Establish parent-child relationships so the catalog records that the three splits were derived from the full dataset:

```
mcp__deriva__add_dataset_child(
  parent_dataset_rid = "<FULL_DATASET_RID>",
  child_dataset_rid = "<TRAIN_DATASET_RID>"
)
```

```
mcp__deriva__add_dataset_child(
  parent_dataset_rid = "<FULL_DATASET_RID>",
  child_dataset_rid = "<VAL_DATASET_RID>"
)
```

```
mcp__deriva__add_dataset_child(
  parent_dataset_rid = "<FULL_DATASET_RID>",
  child_dataset_rid = "<TEST_DATASET_RID>"
)
```

---

## Step 10: Version the Split Datasets

Lock each split with a stable version number before handing them to training runs:

```
mcp__deriva__increment_dataset_version(dataset_rid = "<TRAIN_DATASET_RID>")
mcp__deriva__increment_dataset_version(dataset_rid = "<VAL_DATASET_RID>")
mcp__deriva__increment_dataset_version(dataset_rid = "<TEST_DATASET_RID>")
```

---

## Step 11: Verify Split Sizes and Label Distribution

Check that the splits have the expected member counts:

```
mcp__deriva__list_dataset_members(dataset_rid = "<TRAIN_DATASET_RID>")
mcp__deriva__list_dataset_members(dataset_rid = "<VAL_DATASET_RID>")
mcp__deriva__list_dataset_members(dataset_rid = "<TEST_DATASET_RID>")
```

Expected approximate sizes (from 12,000 total):
- Train: ~8,400 images
- Val: ~1,800 images
- Test: ~1,800 images

Spot-check label distribution in the train split:

```
mcp__deriva__query_table(
  schema_name = "deriva-ml",
  table_name = "Image_Diagnosis",
  filters = [
    {"column": "Dataset_RID", "operator": "=", "value": "<TRAIN_DATASET_RID>"}
  ]
)
```

---

## Step 12: Validate the Datasets

Run the dataset bag validator on each split to confirm integrity:

```
mcp__deriva__validate_dataset_bag(dataset_rid = "<TRAIN_DATASET_RID>")
mcp__deriva__validate_dataset_bag(dataset_rid = "<VAL_DATASET_RID>")
mcp__deriva__validate_dataset_bag(dataset_rid = "<TEST_DATASET_RID>")
```

---

## Summary of Produced Artifacts

| Dataset | RID variable | Members | Purpose |
|---|---|---|---|
| `chest-xray-full` | `FULL_DATASET_RID` | ~12,000 | Source of truth, all labeled images |
| `chest-xray-train` | `TRAIN_DATASET_RID` | ~8,400 (70%) | Model training, ground truth labeled |
| `chest-xray-val` | `VAL_DATASET_RID` | ~1,800 (15%) | Hyperparameter tuning, ground truth labeled |
| `chest-xray-test` | `TEST_DATASET_RID` | ~1,800 (15%) | Final evaluation, ground truth labeled |

All three split datasets:
- Are nested as children of the full dataset (provenance chain preserved)
- Carry the `Diagnosis_Image` ground truth labels from the `Image_Diagnosis` feature table
- Are stratified — each diagnosis class is represented proportionally across splits
- Have stable version numbers ready for use in execution records
