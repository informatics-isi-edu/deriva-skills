# Browsing a Multi-Element Dataset Independently by Type

This document describes the exact sequence of DerivaML MCP tool calls needed to browse a dataset (RID `4-MULTI`) that contains multiple element types (Subject records and Image records), first as an overview and then drilling into each type separately.

---

## Step 1: Get an Overview of the Dataset

Use `get_dataset_spec` to fetch the dataset's full specification. This shows the dataset metadata, its element type definitions, and a count of members per element type.

**Tool call:**
```
mcp__deriva__get_dataset_spec
  dataset_rid: "4-MULTI"
```

**What you'll see:** The dataset spec includes a list of element types registered to this dataset (e.g., `Subject` and `Image`), along with their source tables and any associated metadata. This gives you the top-level picture: roughly how many members of each type are included.

---

## Step 2: List All Dataset Members (Full Overview)

Use `list_dataset_members` without filtering by type to see the complete flat list of member records. For a dataset with ~8,200 records, you may want to paginate or limit results.

**Tool call:**
```
mcp__deriva__list_dataset_members
  dataset_rid: "4-MULTI"
```

**What you'll see:** A list of all members, each with their RID, element type, and linking metadata. You can confirm the total count (~200 subjects + ~8,000 images = ~8,200 total) and see the mix of types.

---

## Step 3: Drill Into Just the Subject Records

Use `list_dataset_members` again but this time filter to only the `Subject` element type. This isolates the ~200 subject records.

**Tool call:**
```
mcp__deriva__list_dataset_members
  dataset_rid: "4-MULTI"
  element_type: "Subject"
```

**What you'll see:** Only the Subject members. Each entry has the Subject's RID, which you can then use with `get_record` to fetch demographic details for individual subjects.

### Optional: Fetch a Sample Subject Record for Demographics

To inspect what demographic fields exist on a Subject record:

**Tool call:**
```
mcp__deriva__get_record
  rid: "<Subject RID from above>"
```

**What you'll see:** The full Subject record including any demographic columns (e.g., age, sex, species, diagnosis) as defined in the catalog schema.

### Optional: Get a Sample of the Subject Table Schema

To understand the full set of demographic columns available on the Subject table:

**Tool call:**
```
mcp__deriva__get_table
  table: "Subject"
```

**What you'll see:** The table schema including all column definitions, their types, and any annotations.

---

## Step 4: Drill Into Just the Image Records

Use `list_dataset_members` filtered to only the `Image` element type. This isolates the ~8,000 image records.

**Tool call:**
```
mcp__deriva__list_dataset_members
  dataset_rid: "4-MULTI"
  element_type: "Image"
```

**What you'll see:** Only the Image members. Each entry has the Image's RID.

### Optional: Check Modality Breakdown via Table Sample

To see the distribution of modalities, fetch a sample from the Image table to understand what values the modality column contains:

**Tool call:**
```
mcp__deriva__get_table_sample_data
  table: "Image"
```

**What you'll see:** A sample of Image rows including modality, acquisition parameters, and other imaging metadata columns.

### Optional: Query for a Modality Breakdown Count

To get an aggregate count of images by modality, use `query_table` with a filter or grouping against the Image table. Note: the exact column name for modality depends on the catalog schema — common names are `Modality`, `Imaging_Modality`, or similar.

**Tool call:**
```
mcp__deriva__query_table
  table: "Image"
  filters: []
```

**What you'll see:** All Image records; you can then inspect the `Modality` column values across the result set to understand the breakdown.

---

## Summary of Tool Call Sequence

| Step | Tool | Key Parameters | Purpose |
|------|------|---------------|---------|
| 1 | `get_dataset_spec` | `dataset_rid: "4-MULTI"` | Top-level overview: element types and counts |
| 2 | `list_dataset_members` | `dataset_rid: "4-MULTI"` | Full member list across all element types |
| 3 | `list_dataset_members` | `dataset_rid: "4-MULTI"`, `element_type: "Subject"` | Isolate just Subject records (~200) |
| 3a | `get_record` | `rid: "<subject-rid>"` | Inspect individual Subject demographics |
| 3b | `get_table` | `table: "Subject"` | Understand the full Subject schema |
| 4 | `list_dataset_members` | `dataset_rid: "4-MULTI"`, `element_type: "Image"` | Isolate just Image records (~8,000) |
| 4a | `get_table_sample_data` | `table: "Image"` | Sample Image rows to see modality field values |
| 4b | `query_table` | `table: "Image"` | Query Image records for modality analysis |

---

## Key Concept

The `element_type` parameter on `list_dataset_members` is the core mechanism for browsing a multi-element dataset independently by type. Without it, all members across all types are returned together. With it, you get a focused view of just one category of records, making it straightforward to analyze demographics for Subjects and modality distributions for Images as separate concerns.
