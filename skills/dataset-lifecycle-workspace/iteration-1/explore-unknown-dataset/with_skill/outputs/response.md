# Exploring Dataset RID 2-B4C8

Sure! Before using a dataset in your experiment, it's good practice to understand its composition, types, version, and member structure. Here's the exact sequence of steps and tool calls I would make to explore dataset `2-B4C8`.

---

## Step 1: Get a high-level overview

Read the dataset resource to see metadata including description, types, current version, and member counts.

**Tool call:**
```
get_record(rid="2-B4C8")
```

This returns the dataset record with fields like:
- `Description` — what the dataset contains
- `RID`, `Version`, `Status`
- Any other top-level metadata

Alternatively, read the resource URI for a richer summary:
```
Read resource: deriva://dataset/2-B4C8
```

---

## Step 2: Check dataset types

Look up the dataset's assigned types (e.g., `Training`, `Labeled`, `Complete`) to understand its intended role.

**Tool call:**
```
query_table(
  table_name="Dataset_Dataset_Type",
  filters={"Dataset": "2-B4C8"}
)
```

This shows which orthogonal type tags are applied to this dataset.

---

## Step 3: List direct members (grouped by table)

See what records are in this dataset and which tables they come from.

**Tool call:**
```
list_dataset_members(
  dataset_rid="2-B4C8"
)
```

This returns members grouped by element type (e.g., `Image`, `Subject`, `Study`), giving you a sense of what kind of data is present and how many records exist per type.

---

## Step 4: Check for child datasets (hierarchy)

If this dataset was created by splitting a parent, it may have child datasets (e.g., Train/Test/Validation splits). Conversely, it may itself be a child of a larger parent.

**Tool call — check children:**
```
list_dataset_children(dataset_rid="2-B4C8")
```

**Tool call — check parents:**
```
list_dataset_parents(dataset_rid="2-B4C8")
```

If children exist (e.g., `Training`, `Testing`, `Validation` splits), you would want to explore those individually for your experiment.

---

## Step 5: Recurse into full member hierarchy

If the dataset has nested children, retrieve all members across the full hierarchy at once.

**Tool call:**
```
list_dataset_members(
  dataset_rid="2-B4C8",
  recurse=true
)
```

This is useful when the dataset is a `Split` parent that groups multiple partition children.

---

## Step 6: Get a denormalized view of the data

For a richer picture of the actual records — joining member tables with related metadata — denormalize the dataset.

**Tool call:**
```
denormalize_dataset(
  dataset_rid="2-B4C8"
)
```

To focus on specific tables (e.g., only Image and Subject records):
```
denormalize_dataset(
  dataset_rid="2-B4C8",
  include_tables=["Image", "Subject"]
)
```

This gives a flattened view similar to a SQL join, showing the full context of each member record.

---

## Step 7: Sample the underlying tables

If you want to understand what the raw data looks like (column names, value distributions), sample one of the member tables.

**Tool call:**
```
get_table_sample_data(table_name="Image")
```

Repeat for other relevant tables identified in Step 3.

---

## Step 8: Check the dataset's version

Before referencing this dataset in an experiment config, note its current version so you can pin it for reproducibility.

**Tool call:**
```
get_current_version(dataset_rid="2-B4C8")
```

This returns the semantic version string (e.g., `1.2.0`). You would then reference it in your experiment config as:
```python
DatasetSpecConfig(rid="2-B4C8", version="1.2.0")
```

---

## Step 9: Get a shareable citation URL

To link to this dataset in documentation or share it with collaborators:

**Tool call:**
```
cite(rid="2-B4C8", current=true)
```

For a permanent snapshot URL (tied to the current version):
```
cite(rid="2-B4C8")
```

---

## Step 10: Estimate download size (optional)

If you're planning to download the dataset as a BDBag for local use, preview the size first:

**Tool call:**
```
estimate_bag_size(
  dataset_rid="2-B4C8",
  version="1.2.0"
)
```

This prevents surprises before committing to a large download.

---

## Summary of Tool Call Sequence

| Step | Tool Call | Purpose |
|------|-----------|---------|
| 1 | `get_record(rid="2-B4C8")` | Top-level metadata and description |
| 2 | `query_table(table_name="Dataset_Dataset_Type", filters={"Dataset": "2-B4C8"})` | Assigned type tags |
| 3 | `list_dataset_members(dataset_rid="2-B4C8")` | Direct members by element type |
| 4a | `list_dataset_children(dataset_rid="2-B4C8")` | Child datasets (splits) |
| 4b | `list_dataset_parents(dataset_rid="2-B4C8")` | Parent dataset context |
| 5 | `list_dataset_members(dataset_rid="2-B4C8", recurse=true)` | All members across full hierarchy |
| 6 | `denormalize_dataset(dataset_rid="2-B4C8")` | Joined/denormalized member records |
| 7 | `get_table_sample_data(table_name="Image")` | Sample raw table data |
| 8 | `get_current_version(dataset_rid="2-B4C8")` | Version to pin in experiment config |
| 9 | `cite(rid="2-B4C8", current=true)` | Shareable URL |
| 10 | `estimate_bag_size(dataset_rid="2-B4C8", version="1.2.0")` | Download size preview |

Once you've completed these steps, you'll know:
- What data types are in the dataset (images, subjects, studies, etc.)
- How many members are present and in what tables
- Whether it's labeled/unlabeled and what partition role it plays
- Whether it has train/test/val children you should use instead of the parent
- The exact version to pin in your `DatasetSpecConfig`
