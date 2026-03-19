# Exploring an Unknown Dataset (RID 2-B4C8)

This document outlines the exact sequence of MCP tool calls I would make to understand the contents of dataset RID `2-B4C8` before using it in an experiment.

---

## Step 1: Get the Dataset Spec

The first thing to do is retrieve the high-level metadata for the dataset — its name, description, version, status, and what types of members it contains.

**Tool:** `mcp__deriva__get_dataset_spec`
**Parameters:**
```json
{
  "dataset_rid": "2-B4C8"
}
```

**What I'm looking for:** The dataset name, description, version, any tags or status fields (e.g., "released", "draft"), and what member types are registered.

---

## Step 2: List the Dataset's Members

Once I know the dataset spec, I want to see the actual members — the records that belong to this dataset.

**Tool:** `mcp__deriva__list_dataset_members`
**Parameters:**
```json
{
  "dataset_rid": "2-B4C8"
}
```

**What I'm looking for:** The member types (e.g., subjects, files, executions), RIDs of individual members, and a sense of how many items exist in each category.

---

## Step 3: List the Dataset's Children (if any)

Datasets can be hierarchical. I'll check if this dataset has child datasets nested inside it.

**Tool:** `mcp__deriva__list_dataset_children`
**Parameters:**
```json
{
  "dataset_rid": "2-B4C8"
}
```

**What I'm looking for:** Whether this is a leaf dataset or a collection of sub-datasets, and if so, what the sub-dataset names/RIDs are.

---

## Step 4: List the Dataset's Parents (if any)

It's also useful to know if this dataset is part of a larger collection — understanding the provenance hierarchy helps interpret how it was created.

**Tool:** `mcp__deriva__list_dataset_parents`
**Parameters:**
```json
{
  "dataset_rid": "2-B4C8"
}
```

**What I'm looking for:** Whether this dataset is a child of a larger dataset or collection, which provides context about its origin.

---

## Step 5: List Executions Associated with the Dataset

I want to understand what workflows produced or consumed this dataset. This reveals its provenance.

**Tool:** `mcp__deriva__list_dataset_executions`
**Parameters:**
```json
{
  "dataset_rid": "2-B4C8"
}
```

**What I'm looking for:** Which executions (workflow runs) are associated with this dataset, and whether the dataset was an input or output of those executions.

---

## Step 6: Inspect a Representative Execution (if any were found)

If Step 5 reveals executions, I'd pick the most relevant one to understand the workflow that generated this dataset.

**Tool:** `mcp__deriva__get_execution_info`
**Parameters:**
```json
{
  "execution_rid": "<RID from step 5>"
}
```

**What I'm looking for:** The workflow type, execution status, description, and timestamps — to understand when and how the data was generated.

---

## Step 7: Estimate the Dataset Size

Before downloading or using the dataset in an experiment, I want to understand how large it is.

**Tool:** `mcp__deriva__estimate_bag_size`
**Parameters:**
```json
{
  "dataset_rid": "2-B4C8"
}
```

**What I'm looking for:** Total estimated download size so I can plan storage and compute resources appropriately.

---

## Step 8: Validate the Dataset (optional but recommended)

Before trusting the dataset for use in an experiment, it's good practice to validate it — checking that RIDs resolve and the bag structure is intact.

**Tool:** `mcp__deriva__validate_dataset_bag`
**Parameters:**
```json
{
  "dataset_rid": "2-B4C8"
}
```

**What I'm looking for:** Any broken references, missing files, or integrity issues that would make this dataset unreliable.

---

## Step 9: Get a Sample of the Underlying Table Data

If the dataset references specific tables in the catalog (e.g., a subject or specimen table), I'd look at a sample of that table to understand the data schema and content.

**Tool:** `mcp__deriva__get_table_sample_data`
**Parameters:**
```json
{
  "schema_name": "<schema from dataset spec>",
  "table_name": "<table from dataset spec>"
}
```

**What I'm looking for:** Column names, data types, and example rows that show what the records actually contain.

---

## Summary of Exploration Sequence

| Step | Tool | Purpose |
|------|------|---------|
| 1 | `get_dataset_spec` | High-level metadata: name, description, version, status |
| 2 | `list_dataset_members` | What records belong to the dataset |
| 3 | `list_dataset_children` | Whether it contains nested sub-datasets |
| 4 | `list_dataset_parents` | Where it fits in the dataset hierarchy |
| 5 | `list_dataset_executions` | Provenance: what workflows produced/used it |
| 6 | `get_execution_info` | Details on the workflow run that created it |
| 7 | `estimate_bag_size` | Total data volume for planning |
| 8 | `validate_dataset_bag` | Integrity check before use |
| 9 | `get_table_sample_data` | Inspect actual data rows and schema |

After completing these steps, I would have a thorough understanding of the dataset's contents, provenance, structure, size, and integrity — enough to decide whether it is suitable for use in an experiment.
