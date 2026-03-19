# Browsing Dataset Contents: Dataset RID 3-XYZ9

This document describes the exact sequence of steps and tool calls to explore what's in the dataset with RID `3-XYZ9` — including image types, diagnosis distribution, and unlabeled records.

---

## Step 1: Ensure catalog connection

Before anything else, confirm there is an active catalog connection.

**Check active connections:**
```
Read resource: deriva://catalog/connections
```

If no connection is active, connect to the appropriate catalog:
```
connect_catalog(hostname="<hostname>", catalog_id="<catalog_id>")
```

---

## Step 2: Get the dataset overview

Read the dataset resource to see its types, current version, description, and member counts.

**Tool call:**
```
Read resource: deriva://dataset/3-XYZ9
```

**What to look for:**
- The current version (e.g., `1.2.0`) — needed for versioned operations
- Dataset types (e.g., `Complete`, `Labeled`, `Unlabeled`)
- Description — does it explain what kinds of images are in here?
- Member counts by element type

---

## Step 3: List dataset members by element type

Get the members of the dataset to confirm which tables have data (e.g., `Image`, `Subject`, etc.).

**Tool call:**
```
list_dataset_members(dataset_rid="3-XYZ9")
```

**What to look for:**
- Which element types are present (likely `Image`)
- Total member count — expect ~5,000

---

## Step 4: Check what features/labels exist on Image records

Before browsing the data, find out what annotation features are registered on the `Image` table. This reveals what label columns are available (e.g., `Diagnosis`, `Grade`, `Label`).

**Tool call:**
```
fetch_table_features(table_name="Image")
```

**What to look for:**
- Feature names and the columns they correspond to
- Whether a `Diagnosis` or classification feature exists

---

## Step 5: Denormalize to see image data with labels

Browse actual image records joined with their classification labels. Use a small limit first to understand the schema, then broaden.

**Tool call — Image data with classification labels:**
```
denormalize_dataset(
    dataset_rid="3-XYZ9",
    include_tables=["Image", "Image_Classification"],
    limit=20
)
```

If `Image_Classification` is not the right table name (check the feature names from Step 4), substitute the correct joined table. For example:

```
denormalize_dataset(
    dataset_rid="3-XYZ9",
    include_tables=["Image", "Subject"],
    limit=20
)
```

**What to look for:**
- Column names — especially any `Diagnosis`, `Label`, or classification column
- Whether those columns contain nulls (unlabeled records)
- The range of values in the diagnosis/label column

---

## Step 6: Check diagnosis distribution — labeled records

To see how diagnoses are distributed, denormalize with a filter for records that have a diagnosis value. Because `denormalize_dataset` returns rows, examining the values across the result set (or using a query) reveals the distribution.

For a broader view without a limit:
```
denormalize_dataset(
    dataset_rid="3-XYZ9",
    include_tables=["Image", "Image_Classification"],
    limit=5000
)
```

Alternatively, query the table directly to count by diagnosis:
```
query_table(
    table_name="Image_Classification",
    filters={"dataset_rid": "3-XYZ9"},
    columns=["Diagnosis"]
)
```

**What to look for:**
- Count of each unique diagnosis value
- Whether any diagnosis values are `null` or empty (these are unlabeled)

---

## Step 7: Find unlabeled images

To specifically find images without a diagnosis, denormalize and look for null values in the label column.

**Tool call:**
```
denormalize_dataset(
    dataset_rid="3-XYZ9",
    include_tables=["Image", "Image_Classification"],
    limit=5000
)
```

In the results, filter client-side (or by inspection) for rows where `Diagnosis` is null or empty.

Alternatively, if the dataset has a known `Unlabeled` type tag (from Step 2), that already indicates a portion of records have no labels.

---

## Step 8: Check for child datasets (splits) and parents

Determine whether this dataset has been split into train/test/validation subsets, or whether it is itself a child of a larger collection.

**Tool calls:**
```
list_dataset_children(dataset_rid="3-XYZ9")
list_dataset_parents(dataset_rid="3-XYZ9")
```

**What to look for:**
- If children exist: what split was applied? What are the child RIDs and their types?
- If parents exist: is this dataset a curated subset of a larger collection?

---

## Step 9: Check provenance

See which executions have used this dataset — useful for understanding its history.

**Tool call:**
```
list_dataset_executions(dataset_rid="3-XYZ9")
```

---

## Step 10: (Optional) Generate a shareable Chaise URL

If visual browsing in the web UI is preferred:

**Tool call:**
```
cite(rid="3-XYZ9", current=true)
```

This produces a live URL to the dataset page in Chaise where you can sort, filter, and facet interactively.

---

## Summary of Tool Call Sequence

| # | Tool / Resource | Purpose |
|---|-----------------|---------|
| 1 | `Read: deriva://catalog/connections` | Confirm active connection |
| 2 | `Read: deriva://dataset/3-XYZ9` | Overview: types, version, description, member counts |
| 3 | `list_dataset_members(dataset_rid="3-XYZ9")` | Confirm element types and total count (~5,000) |
| 4 | `fetch_table_features(table_name="Image")` | Discover available label/annotation features |
| 5 | `denormalize_dataset(dataset_rid="3-XYZ9", include_tables=["Image", "Image_Classification"], limit=20)` | Sample records to understand schema and label columns |
| 6 | `denormalize_dataset(..., limit=5000)` | Full scan to review diagnosis distribution |
| 7 | Inspect null values in diagnosis column | Identify unlabeled images |
| 8 | `list_dataset_children(dataset_rid="3-XYZ9")` | Check for train/test/val splits |
| 8b | `list_dataset_parents(dataset_rid="3-XYZ9")` | Check if this is a subset of a larger dataset |
| 9 | `list_dataset_executions(dataset_rid="3-XYZ9")` | Review provenance history |
| 10 | `cite(rid="3-XYZ9", current=true)` | (Optional) Generate Chaise URL for visual browsing |

---

## Key Findings to Report

After running the above steps, the questions are answered as follows:

- **What kinds of images are in the dataset?** — answered by Step 5 (image metadata columns, modality, source)
- **How are diagnoses distributed?** — answered by Step 6 (counts per unique diagnosis value)
- **Are there unlabeled images?** — answered by Step 7 (rows with null in the diagnosis column); also indicated by `Unlabeled` type tag in Step 2
- **Has the dataset been split?** — answered by Step 8 (`list_dataset_children`)
