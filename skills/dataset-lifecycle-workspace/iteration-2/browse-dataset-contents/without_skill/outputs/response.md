# Browsing Dataset Contents for RID 3-XYZ9

## Goal

Understand what's in a dataset of ~5,000 images: what kinds of images exist, how diagnoses are distributed, and whether any images are unlabeled.

---

## Step 1: Connect to the catalog and get the dataset spec

First, connect to the catalog that holds dataset 3-XYZ9, then retrieve the dataset's top-level metadata and structure.

```
mcp__deriva__connect_catalog(host="<host>", catalog_id="<catalog_id>")
```

Then fetch the dataset spec to understand what tables and member types are in it:

```
mcp__deriva__get_dataset_spec(dataset_rid="3-XYZ9")
```

**Why:** The spec reveals the dataset's type, version, description, and — critically — what entity types (tables) are referenced as members. This tells us whether images, labels, diagnoses, etc. are organized as separate member types or combined in one table.

---

## Step 2: List the dataset members

List the members of the dataset to understand how many there are and what the records look like:

```
mcp__deriva__list_dataset_members(dataset_rid="3-XYZ9")
```

**Why:** This returns the actual member records. With ~5,000 images, the list may be truncated, but even a sample tells us what columns are present (e.g., image type, diagnosis, label status) and how the data is structured.

---

## Step 3: Sample the underlying image table directly

Using the member table name discovered in Step 1 (e.g., `Image` or `Subject` in some schema), query the table directly to get a sample with all relevant columns:

```
mcp__deriva__get_table_sample_data(
    schema_name="<schema>",
    table_name="<image_table>",
    sample_size=20
)
```

**Why:** `list_dataset_members` may return only RIDs and member type info. Sampling the source table directly shows the full column set — file names, image type, modality, diagnosis, label fields, etc.

---

## Step 4: Get the full table schema

Retrieve the table definition to see every column, its type, and whether it's nullable:

```
mcp__deriva__get_table(
    schema_name="<schema>",
    table_name="<image_table>"
)
```

**Why:** This reveals which columns represent "diagnosis" and "label" fields, what their controlled vocabulary is, and which columns are nullable (unlabeled records will have NULL in label/diagnosis columns).

---

## Step 5: Count total images in the dataset

Get the total row count for the image table to confirm scale:

```
mcp__deriva__count_table(
    schema_name="<schema>",
    table_name="<image_table>"
)
```

**Why:** Confirms the ~5,000 figure and establishes baseline for computing percentages.

---

## Step 6: Query diagnosis distribution

Query the image table grouped by the diagnosis column to see the distribution. This uses `query_table` with a filter or aggregation approach. Since DerivaML uses ERMrest, the query would be:

```
mcp__deriva__query_table(
    schema_name="<schema>",
    table_name="<image_table>",
    filters=[{"column": "Dataset_RID", "operator": "=", "value": "3-XYZ9"}],
    output_columns=["Diagnosis", "Image_Type"]
)
```

Then inspect the results to count occurrences of each diagnosis value.

**Why:** This is the core of the "how are diagnoses distributed" question. The result set (or a summary) shows which diagnoses appear and how often.

---

## Step 7: Find unlabeled images

Query for records where the diagnosis (or label) column is NULL:

```
mcp__deriva__query_table(
    schema_name="<schema>",
    table_name="<image_table>",
    filters=[
        {"column": "Dataset_RID", "operator": "=", "value": "3-XYZ9"},
        {"column": "Diagnosis", "operator": "::null::", "value": null}
    ]
)
```

**Why:** Null values in the diagnosis or label column indicate unlabeled images. Counting these (or reviewing them) answers the "are there any unlabeled ones" question directly.

---

## Step 8: Check for vocabulary tables

If the diagnosis column references a controlled vocabulary, look at the vocabulary table to see all possible label values (including any that have zero images assigned):

```
mcp__deriva__get_table_sample_data(
    schema_name="<vocab_schema>",
    table_name="<Diagnosis_vocabulary_table>",
    sample_size=50
)
```

**Why:** A vocabulary table lists all valid diagnosis terms. Comparing this against the diagnosis distribution from Step 6 reveals which terms exist but have no images assigned — a subtler form of "gap" in the dataset.

---

## Step 9: Check dataset children (if hierarchical)

Check whether the dataset has child datasets (e.g., train/val/test splits):

```
mcp__deriva__list_dataset_children(dataset_rid="3-XYZ9")
```

**Why:** Some datasets are organized hierarchically. If 3-XYZ9 is a parent dataset, the splits may carry different label distributions that are masked by aggregate counts.

---

## Summary of Information Gathered

After these steps you would know:

| Question | Source |
|---|---|
| What kinds of images are in the dataset? | `get_table_sample_data` + `query_table` on Image_Type column |
| How are diagnoses distributed? | `query_table` grouped/filtered by Diagnosis column |
| Are there unlabeled images? | `query_table` with NULL filter on Diagnosis/Label column |
| Total image count | `count_table` |
| Schema/column structure | `get_table` |
| Any sub-splits | `list_dataset_children` |

---

## Notes on Tool Limitations

- `query_table` returns raw rows; aggregation (GROUP BY counts) must be done client-side by inspecting the result set unless ERMrest aggregate syntax is supported in the filter.
- If the dataset is very large, `list_dataset_members` may be paginated. The full diagnosis distribution should be computed by querying the source table directly, not by paging through 5,000 member records one at a time.
- The exact schema name and table name depend on the catalog's model and are discovered via `get_dataset_spec` and `get_table` in Steps 1 and 4.
