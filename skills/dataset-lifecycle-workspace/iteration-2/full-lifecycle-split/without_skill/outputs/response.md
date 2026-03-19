# Chest X-Ray Training Pipeline: Dataset Setup and Stratified Split

## Overview

This document describes the exact sequence of DerivaML MCP tool calls needed to:
1. Create a complete dataset containing all ~12,000 labeled chest X-ray images
2. Split it 70/15/15 into train/val/test subsets using stratified sampling on the `Diagnosis_Image` column from the `Image_Diagnosis` feature table
3. Mark each split with ground truth labels

---

## Prerequisites

- An active catalog connection (catalog already connected)
- The `Image_Diagnosis` feature table exists and has a `Diagnosis_Image` column with diagnosis labels
- Images are accessible as assets in the catalog

---

## Step 1: Create the Complete Dataset

Create a parent dataset that will contain all chest X-ray images. This becomes the source for the subsequent splits.

```
Tool: mcp__deriva__create_dataset
Parameters:
  name: "Chest X-Ray Full Dataset"
  description: "Complete collection of ~12,000 labeled chest X-ray images for training pipeline"
```

**Expected output:** A dataset RID, e.g. `"2-XXXX"`. Store this as `FULL_DATASET_RID`.

---

## Step 2: Identify the Image Table and Add All Members

Query the Image table to get all RIDs, then add them to the full dataset.

### 2a. Sample the Image table to confirm structure

```
Tool: mcp__deriva__get_table_sample_data
Parameters:
  table: "Image"
  schema: "isa"          # or whichever schema contains Image
  limit: 5
```

This confirms the table name, schema, and primary key column before bulk membership operations.

### 2b. Add all image records as dataset members

```
Tool: mcp__deriva__add_dataset_members
Parameters:
  dataset_rid: "<FULL_DATASET_RID>"
  table: "Image"
  schema: "isa"
  # No filter — include all rows
```

**Expected outcome:** All ~12,000 image records are members of `FULL_DATASET_RID`.

---

## Step 3: Attach Feature Labels to the Full Dataset

The `Image_Diagnosis` feature table holds the `Diagnosis_Image` labels. Before splitting, confirm the feature table is reachable and verify label distribution.

### 3a. Sample the feature table

```
Tool: mcp__deriva__get_table_sample_data
Parameters:
  table: "Image_Diagnosis"
  schema: "isa"
  limit: 10
```

Confirms column names, especially that `Diagnosis_Image` is present and contains the class labels (e.g. "Normal", "Pneumonia", "COVID-19", etc.).

### 3b. Query label distribution for stratification planning

```
Tool: mcp__deriva__query_table
Parameters:
  table: "Image_Diagnosis"
  schema: "isa"
  # Select the label column and count occurrences grouped by label
  # The exact filter/aggregation syntax depends on catalog ERMrest support
```

This gives the per-class counts needed to verify the 70/15/15 split will yield sufficient examples per class.

---

## Step 4: Stratified Split — 70 / 15 / 15

Use the `split_dataset` tool, specifying stratification on `Diagnosis_Image` from the `Image_Diagnosis` feature table.

```
Tool: mcp__deriva__split_dataset
Parameters:
  dataset_rid: "<FULL_DATASET_RID>"
  splits:
    - name: "train"
      ratio: 0.70
    - name: "val"
      ratio: 0.15
    - name: "test"
      ratio: 0.15
  stratify_on:
    feature_table: "Image_Diagnosis"
    label_column: "Diagnosis_Image"
  random_seed: 42
```

**Expected output:** Three child dataset RIDs, e.g.:
- `TRAIN_DATASET_RID` — ~8,400 images
- `VAL_DATASET_RID`   — ~1,800 images
- `TEST_DATASET_RID`  — ~1,800 images

Each child dataset is automatically registered as a child of `FULL_DATASET_RID`.

---

## Step 5: Mark Each Split with a Dataset Type

Assign dataset type terms so downstream tooling knows which split is which.

### 5a. Create (or reuse) dataset type terms for train/val/test

If these vocabulary terms do not already exist:

```
Tool: mcp__deriva__create_dataset_type_term
Parameters:
  name: "training"
  description: "Training split for ML model development"
```

```
Tool: mcp__deriva__create_dataset_type_term
Parameters:
  name: "validation"
  description: "Validation split for hyperparameter tuning"
```

```
Tool: mcp__deriva__create_dataset_type_term
Parameters:
  name: "test"
  description: "Held-out test split for final evaluation"
```

### 5b. Add dataset types to each split

```
Tool: mcp__deriva__add_dataset_type
Parameters:
  dataset_rid: "<TRAIN_DATASET_RID>"
  dataset_type: "training"
```

```
Tool: mcp__deriva__add_dataset_type
Parameters:
  dataset_rid: "<VAL_DATASET_RID>"
  dataset_type: "validation"
```

```
Tool: mcp__deriva__add_dataset_type
Parameters:
  dataset_rid: "<TEST_DATASET_RID>"
  dataset_type: "test"
```

---

## Step 6: Mark Ground Truth Labels on Each Split

For each split dataset, add a feature that designates `Image_Diagnosis.Diagnosis_Image` as the ground truth label column. This is done by adding the `Image_Diagnosis` feature to each split dataset, indicating it represents ground truth.

### 6a. Associate the feature table as ground truth on the train split

```
Tool: mcp__deriva__add_feature_value
Parameters:
  dataset_rid: "<TRAIN_DATASET_RID>"
  feature_table: "Image_Diagnosis"
  feature_column: "Diagnosis_Image"
  role: "ground_truth"
```

### 6b. Associate the feature table as ground truth on the val split

```
Tool: mcp__deriva__add_feature_value
Parameters:
  dataset_rid: "<VAL_DATASET_RID>"
  feature_table: "Image_Diagnosis"
  feature_column: "Diagnosis_Image"
  role: "ground_truth"
```

### 6c. Associate the feature table as ground truth on the test split

```
Tool: mcp__deriva__add_feature_value
Parameters:
  dataset_rid: "<TEST_DATASET_RID>"
  feature_table: "Image_Diagnosis"
  feature_column: "Diagnosis_Image"
  role: "ground_truth"
```

---

## Step 7: Set Descriptions on Each Split Dataset

Provide human-readable context so collaborators understand each dataset's purpose.

```
Tool: mcp__deriva__set_dataset_description
Parameters:
  dataset_rid: "<TRAIN_DATASET_RID>"
  description: "Training split (70%) — ~8,400 chest X-rays, stratified on Diagnosis_Image. Ground truth labels from Image_Diagnosis feature table."
```

```
Tool: mcp__deriva__set_dataset_description
Parameters:
  dataset_rid: "<VAL_DATASET_RID>"
  description: "Validation split (15%) — ~1,800 chest X-rays, stratified on Diagnosis_Image. Ground truth labels from Image_Diagnosis feature table."
```

```
Tool: mcp__deriva__set_dataset_description
Parameters:
  dataset_rid: "<TEST_DATASET_RID>"
  description: "Test split (15%) — ~1,800 chest X-rays, stratified on Diagnosis_Image. Ground truth labels from Image_Diagnosis feature table. Held out for final evaluation only."
```

---

## Step 8: Verify the Split Hierarchy

Confirm the parent/child relationships are correct.

```
Tool: mcp__deriva__list_dataset_children
Parameters:
  dataset_rid: "<FULL_DATASET_RID>"
```

Expected: returns three child datasets — train, val, test — with their RIDs and types.

Also spot-check member counts on each split:

```
Tool: mcp__deriva__count_table
Parameters:
  # Or list_dataset_members with a limit to confirm approximate sizes
  dataset_rid: "<TRAIN_DATASET_RID>"
```

```
Tool: mcp__deriva__count_table
Parameters:
  dataset_rid: "<VAL_DATASET_RID>"
```

```
Tool: mcp__deriva__count_table
Parameters:
  dataset_rid: "<TEST_DATASET_RID>"
```

---

## Step 9: (Optional) Version the Full Dataset

Lock the full dataset at a stable version so downstream experiments can reference a reproducible snapshot.

```
Tool: mcp__deriva__increment_dataset_version
Parameters:
  dataset_rid: "<FULL_DATASET_RID>"
```

Then version each split:

```
Tool: mcp__deriva__increment_dataset_version
Parameters:
  dataset_rid: "<TRAIN_DATASET_RID>"
```

```
Tool: mcp__deriva__increment_dataset_version
Parameters:
  dataset_rid: "<VAL_DATASET_RID>"
```

```
Tool: mcp__deriva__increment_dataset_version
Parameters:
  dataset_rid: "<TEST_DATASET_RID>"
```

---

## Summary of Dataset RIDs

| Dataset       | Split Ratio | Approx. Size | Type       | Ground Truth         |
|---------------|-------------|--------------|------------|----------------------|
| Full Dataset  | 100%        | ~12,000      | —          | Image_Diagnosis      |
| Train Split   | 70%         | ~8,400       | training   | Image_Diagnosis      |
| Val Split     | 15%         | ~1,800       | validation | Image_Diagnosis      |
| Test Split    | 15%         | ~1,800       | test       | Image_Diagnosis      |

Stratification is applied on `Image_Diagnosis.Diagnosis_Image` so each class's prevalence is proportional across all three splits.

---

## Notes on Stratified Sampling

The `split_dataset` tool's `stratify_on` parameter instructs DerivaML to group images by their `Diagnosis_Image` label value before assigning them to splits. Within each label group, images are randomly shuffled (using `random_seed: 42` for reproducibility) and then distributed at 70/15/15. This ensures that a rare diagnosis class with, say, 100 examples ends up with ~70 in train, ~15 in val, and ~15 in test — rather than all landing in one split by chance.

If any label class has fewer than ~7 examples (i.e., too few to yield at least one sample in each of the three splits), `split_dataset` will warn about that class. In that case, consider merging rare classes into an "Other" term before splitting.
