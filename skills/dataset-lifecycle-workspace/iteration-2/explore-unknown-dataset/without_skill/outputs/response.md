# Exploring Unknown Dataset RID 2-B4C8

Below is the exact sequence of steps and MCP tool calls I would make to explore dataset RID 2-B4C8 before using it in an experiment.

---

## Step 1: Ensure a Catalog Connection Exists

Before anything else, I need a connected catalog. If one is not already active, I would connect to the appropriate Deriva server.

```
mcp__deriva__connect_catalog(host="<server>", catalog_id="<id>")
```

Or, if a catalog is already active:

```
mcp__deriva__set_active_catalog(host="<server>", catalog_id="<id>")
```

---

## Step 2: Retrieve the Dataset Record

Fetch the top-level metadata for the dataset.

```
mcp__deriva__get_dataset_spec(dataset_rid="2-B4C8")
```

**What I'm looking for:**
- `Name` / `Description` — human-readable label and purpose
- `Version` — which version this RID corresponds to
- `Status` — e.g., Draft, Released, Deprecated
- `Created` / `Updated` timestamps
- Any linked `Dataset_Type` terms that describe the domain or experiment type

---

## Step 3: List the Dataset's Members

Enumerate what data records are inside the dataset.

```
mcp__deriva__list_dataset_members(dataset_rid="2-B4C8")
```

**What I'm looking for:**
- Which tables/entity types are represented (e.g., Subject, File, Image, Execution)
- How many members of each type exist
- Whether the dataset is heterogeneous (multiple types) or focused on one entity type

---

## Step 4: List the Dataset's Children (Nested Datasets)

Check whether this dataset contains sub-datasets.

```
mcp__deriva__list_dataset_children(dataset_rid="2-B4C8")
```

**What I'm looking for:**
- Any child dataset RIDs and their names/descriptions
- Whether this is a collection/composite dataset that groups smaller datasets
- If children exist, I would repeat Steps 2–4 recursively for each child of interest

---

## Step 5: List the Dataset's Parents

Understand the provenance context — where did this dataset come from?

```
mcp__deriva__list_dataset_parents(dataset_rid="2-B4C8")
```

**What I'm looking for:**
- Whether this dataset was derived from a larger parent dataset (e.g., a split or filtered subset)
- Parent dataset names/descriptions to understand lineage

---

## Step 6: List Executions Associated with the Dataset

Understand what workflows produced or consumed this dataset.

```
mcp__deriva__list_dataset_executions(dataset_rid="2-B4C8")
```

**What I'm looking for:**
- `Execution` records that created this dataset (output executions)
- `Execution` records that used this dataset as input
- Associated `Workflow` names and versions — what processing was applied?
- Execution status (Succeeded, Failed, Running) to assess data quality/completeness

---

## Step 7: Inspect a Specific Execution (if relevant ones were found)

For any execution that created this dataset, retrieve its full details.

```
mcp__deriva__get_execution_info(execution_rid="<RID from Step 6>")
```

**What I'm looking for:**
- Workflow description and version
- Input parameters used
- Start/end times and duration
- Any linked assets or outputs

---

## Step 8: Examine Sample Data from Member Tables

For each major entity type found in Step 3, look at a sample of actual records.

```
mcp__deriva__get_table_sample_data(table_name="<TableName>", schema_name="<SchemaName>", limit=10)
```

Or use a targeted query filtered to members of this dataset:

```
mcp__deriva__query_table(
    schema_name="deriva-ml",
    table_name="Dataset_Member",
    filters={"Dataset": "2-B4C8"},
    limit=20
)
```

**What I'm looking for:**
- Column names and data types present in the records
- Representative values — species, modality, time points, conditions, etc.
- Presence of file/asset columns (URL, Filename, Byte_Count, MD5)
- Any null/empty fields that might indicate incomplete records

---

## Step 9: Check for Asset Files

If the dataset contains file assets, verify they are accessible.

```
mcp__deriva__asset_file_path(dataset_rid="2-B4C8")
```

Or estimate the total download size before committing to a download:

```
mcp__deriva__estimate_bag_size(dataset_rid="2-B4C8")
```

**What I'm looking for:**
- Total file count and size — is it feasible to download for local use?
- File types present (CSV, HDF5, TIFF, etc.) — do I have tools to read them?

---

## Step 10: Validate the Dataset

Check that the dataset is internally consistent and all referenced RIDs resolve.

```
mcp__deriva__validate_dataset_bag(dataset_rid="2-B4C8")
```

And validate that all RIDs referenced within the dataset actually exist in the catalog:

```
mcp__deriva__validate_rids(dataset_rid="2-B4C8")
```

**What I'm looking for:**
- Any broken references or missing records
- Validation errors that would indicate the dataset is incomplete or corrupted
- Confidence that I can safely use this dataset in a new execution

---

## Step 11: Denormalize the Dataset (Optional — for a flat view)

If I want a single flat table combining all member metadata for easier inspection:

```
mcp__deriva__denormalize_dataset(dataset_rid="2-B4C8")
```

**What I'm looking for:**
- A denormalized tabular representation that joins all member attributes
- Useful for getting a holistic picture of what columns/fields are available across all members

---

## Summary of Information Gathered

After completing the steps above, I would have:

| Question | Answered By |
|---|---|
| What is this dataset about? | Steps 2, 7 |
| What data records does it contain? | Step 3 |
| Is it a subset of a larger collection? | Steps 4, 5 |
| How was it created / what processing was applied? | Steps 6, 7 |
| What do the actual records look like? | Step 8 |
| How large are the associated files? | Step 9 |
| Is the dataset valid and complete? | Step 10 |
| What columns/fields are available? | Steps 8, 11 |

Only after satisfying all of the above would I proceed to use 2-B4C8 as an input to my experiment execution.
