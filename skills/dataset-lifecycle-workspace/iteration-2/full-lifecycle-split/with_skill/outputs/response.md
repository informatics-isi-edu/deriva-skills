# Chest X-Ray Dataset: Full Lifecycle Plan

This document describes the exact sequence of MCP tool calls to create a complete chest X-ray dataset, then perform a stratified 70/15/15 train/val/test split with ground truth labels marked.

---

## Assumptions

- Feature table for diagnosis labels: `Image_Diagnosis`
- Label column within that table: `Diagnosis_Image`
- Denormalized stratify column: `Image_Diagnosis_Diagnosis_Image`
- The images are stored in a table named `Image`
- Catalog is already accessible; hostname and catalog_id are known

---

## Phase 0: Connect

**Step 0.1 — Connect to the catalog**

```
connect_catalog(
  hostname="<your-hostname>",
  catalog_id="<your-catalog-id>"
)
```

---

## Phase 1: Assess

**Step 1.1 — Check existing datasets**

```
query_table(table_name="Dataset")
```

Review results. If a complete chest X-ray dataset already exists, reuse it and skip to Phase 3 (Split).

**Step 1.2 — Verify data volume**

```
count_table(table_name="Image")
```

Confirm approximately 12,000 records are present.

**Step 1.3 — Check registered element types**

Read resource: `deriva://catalog/dataset-element-types`

Confirm that `Image` is registered. If it is not, it will be registered in Phase 3.

**Step 1.4 — Check available dataset types**

Read resource: `deriva://catalog/dataset-types`

Confirm `Complete`, `Labeled`, `Training`, `Validation`, `Testing`, and `Split` are present. These are all built-in types and should exist by default.

**Step 1.5 — Discover all image RIDs**

```
query_table(
  table_name="Image",
  output_columns=["RID"]
)
```

Collect all ~12,000 RIDs. This query may need to be paginated if the catalog imposes a row limit; repeat with `offset` until all RIDs are collected.

---

## Phase 2: Plan

**Dataset structure:**

1. **Complete dataset** — contains all ~12,000 images; types: `Complete`, `Labeled`
2. **Split** — created from the complete dataset; three-way 70/15/15 split stratified on `Image_Diagnosis_Diagnosis_Image`; each partition typed: `Labeled`
   - Training child: `Training`, `Labeled` (~8,400 images)
   - Validation child: `Validation`, `Labeled` (~1,800 images)
   - Testing child: `Testing`, `Labeled` (~1,800 images)

**Stratify column derivation:**

The feature table is `Image_Diagnosis` and the label column is `Diagnosis_Image`. Per the skill's convention, the denormalized column name is constructed as `{FeatureTableName}_{ColumnName}`:

```
stratify_by_column = "Image_Diagnosis_Diagnosis_Image"
include_tables     = ["Image", "Image_Diagnosis"]
```

**Missing value policy:** Use `stratify_missing="drop"` — if any images have no diagnosis label, they are excluded from the split rather than causing an error or polluting a class.

---

## Phase 3: Create

**Step 3.1 — Create an execution for provenance**

```
create_execution(
  workflow_name="Dataset Curation",
  workflow_type="Data Management",
  description="Create complete chest X-ray dataset and perform 70/15/15 stratified split on Diagnosis_Image"
)
```

```
start_execution()
```

Note the execution RID returned.

**Step 3.2 — Register element type (idempotent)**

```
add_dataset_element_type(table_name="Image")
```

**Step 3.3 — Create the complete dataset**

```
create_dataset(
  description="All ~12,000 labeled chest X-ray images available in the catalog as of the curation date. Images have ground truth diagnosis labels in Image_Diagnosis. Intended as the source for train/val/test splits for supervised classification models.",
  dataset_types=["Complete", "Labeled"]
)
```

Note the returned dataset RID (referred to below as `<COMPLETE_RID>`).

**Step 3.4 — Add all images to the dataset**

```
add_dataset_members(
  dataset_rid="<COMPLETE_RID>",
  member_rids=["<RID_1>", "<RID_2>", ..., "<RID_12000>"],
  description="Initial population: all labeled chest X-ray images from the Image table"
)
```

> Note: If the member list is too large for a single call, batch into multiple `add_dataset_members` calls (e.g., 1,000 RIDs per call). Each call auto-increments the minor version. The final call's description should summarize the full batch.

---

## Phase 4: Split (dry run first, then execute)

**Step 4.1 — Preview the split (dry run)**

```
split_dataset(
  source_dataset_rid="<COMPLETE_RID>",
  test_size=0.15,
  val_size=0.15,
  seed=42,
  stratify_by_column="Image_Diagnosis_Diagnosis_Image",
  stratify_missing="drop",
  include_tables=["Image", "Image_Diagnosis"],
  dry_run=true
)
```

Review the output:
- Confirm expected counts: ~8,400 train / ~1,800 val / ~1,800 test
- Verify class distribution is preserved across partitions
- Check how many images are dropped due to missing diagnosis labels (if any)

If the dry run output looks correct, proceed.

**Step 4.2 — Execute the split**

```
split_dataset(
  source_dataset_rid="<COMPLETE_RID>",
  test_size=0.15,
  val_size=0.15,
  seed=42,
  stratify_by_column="Image_Diagnosis_Diagnosis_Image",
  stratify_missing="drop",
  include_tables=["Image", "Image_Diagnosis"],
  training_types=["Labeled"],
  testing_types=["Labeled"],
  validation_types=["Labeled"],
  split_description="70/15/15 stratified split on Diagnosis_Image label. Seed 42. Images missing diagnosis labels excluded. All partitions carry ground truth Labeled type."
)
```

This creates:
- A parent `Split` dataset containing three child datasets
- Training child: types `Training` + `Labeled`
- Validation child: types `Validation` + `Labeled`
- Testing child: types `Testing` + `Labeled`

Note the RIDs for the training, validation, and testing child datasets from the output.

---

## Phase 5: Finalize Execution

**Step 5.1 — Stop the execution**

```
stop_execution()
```

---

## Phase 6: Version and Verify

**Step 6.1 — Check children of the complete dataset**

```
list_dataset_children(dataset_rid="<COMPLETE_RID>")
```

Confirm three children are present (Training, Validation, Testing) plus the parent Split container.

**Step 6.2 — Spot-check partition sizes**

```
list_dataset_members(dataset_rid="<TRAINING_RID>")
list_dataset_members(dataset_rid="<VALIDATION_RID>")
list_dataset_members(dataset_rid="<TESTING_RID>")
```

Confirm approximate counts of 8,400 / 1,800 / 1,800.

**Step 6.3 — Denormalize a sample to verify labels are present**

```
denormalize_dataset(
  dataset_rid="<TRAINING_RID>",
  include_tables=["Image", "Image_Diagnosis"],
  limit=10
)
```

Confirm `Image_Diagnosis_Diagnosis_Image` values are populated in the returned rows.

**Step 6.4 — Record final versions for experiment configs**

After `split_dataset` runs, all affected datasets auto-increment their versions. Use `get_dataset_spec` to generate the correct `DatasetSpecConfig` strings:

```
get_dataset_spec(dataset_rid="<TRAINING_RID>")
get_dataset_spec(dataset_rid="<VALIDATION_RID>")
get_dataset_spec(dataset_rid="<TESTING_RID>")
```

Use the returned version strings in experiment configs (never omit the version for real experiments):

```python
DatasetSpecConfig(rid="<TRAINING_RID>",   version="<VERSION>")
DatasetSpecConfig(rid="<VALIDATION_RID>",  version="<VERSION>")
DatasetSpecConfig(rid="<TESTING_RID>",     version="<VERSION>")
```

---

## Summary of Tool Calls (in order)

| # | Tool | Key Parameters |
|---|------|----------------|
| 1 | `connect_catalog` | hostname, catalog_id |
| 2 | `query_table` | table_name="Dataset" — check for existing datasets |
| 3 | `count_table` | table_name="Image" — verify ~12,000 rows |
| 4 | Read resource | `deriva://catalog/dataset-element-types` |
| 5 | Read resource | `deriva://catalog/dataset-types` |
| 6 | `query_table` | table_name="Image", output_columns=["RID"] — collect all RIDs |
| 7 | `create_execution` | workflow_name="Dataset Curation", workflow_type="Data Management" |
| 8 | `start_execution` | — |
| 9 | `add_dataset_element_type` | table_name="Image" |
| 10 | `create_dataset` | description="All ~12,000 labeled chest X-ray images...", dataset_types=["Complete", "Labeled"] |
| 11 | `add_dataset_members` | dataset_rid=\<COMPLETE_RID\>, member_rids=[all ~12,000 RIDs] |
| 12 | `split_dataset` | source_dataset_rid=\<COMPLETE_RID\>, test_size=0.15, val_size=0.15, seed=42, stratify_by_column="Image_Diagnosis_Diagnosis_Image", include_tables=["Image","Image_Diagnosis"], stratify_missing="drop", **dry_run=true** |
| 13 | `split_dataset` | same as above, dry_run=false, add training_types=["Labeled"], testing_types=["Labeled"], validation_types=["Labeled"], split_description="..." |
| 14 | `stop_execution` | — |
| 15 | `list_dataset_children` | dataset_rid=\<COMPLETE_RID\> — verify split structure |
| 16 | `list_dataset_members` | dataset_rid=\<TRAINING_RID\> |
| 17 | `list_dataset_members` | dataset_rid=\<VALIDATION_RID\> |
| 18 | `list_dataset_members` | dataset_rid=\<TESTING_RID\> |
| 19 | `denormalize_dataset` | dataset_rid=\<TRAINING_RID\>, include_tables=["Image","Image_Diagnosis"], limit=10 |
| 20 | `get_dataset_spec` | dataset_rid=\<TRAINING_RID\> |
| 21 | `get_dataset_spec` | dataset_rid=\<VALIDATION_RID\> |
| 22 | `get_dataset_spec` | dataset_rid=\<TESTING_RID\> |

---

## Key Decisions Explained

- **`stratify_by_column="Image_Diagnosis_Diagnosis_Image"`** — Derived from the feature table name `Image_Diagnosis` and label column `Diagnosis_Image` using the `{FeatureTableName}_{ColumnName}` convention.
- **`include_tables=["Image", "Image_Diagnosis"]`** — Required whenever `stratify_by_column` is used; tells the splitter how to denormalize the data to access the label column.
- **`stratify_missing="drop"`** — Any image that lacks a `Diagnosis_Image` value is excluded from the split. This is safer than `"include"` (which would treat nulls as their own class) or `"error"` (which would abort if any nulls exist).
- **`training_types`, `testing_types`, `validation_types` all set to `["Labeled"]`** — This marks all three partitions with the `Labeled` type, indicating they contain ground truth labels. This is required for evaluation tools, ROC curve generation, and any downstream code that filters for labeled datasets.
- **`seed=42`** — Fixed seed for reproducibility. All future runs with this seed will produce the same partition.
- **Dry run first** — Always preview with `dry_run=true` before committing. This costs nothing and allows you to verify counts and class balance before writing to the catalog.
