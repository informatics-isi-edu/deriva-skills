# Exploring Dataset RID 2-B4C8

To help you understand what's in dataset 2-B4C8 before using it in your experiment, I would follow the exploration steps from Phase 5 of the dataset lifecycle skill. Here is the exact sequence of tool calls I would make.

---

## Step 0: Ensure catalog connection

Before anything else, verify there is an active connection.

**Tool:** `connect_catalog` (if not already connected)
```
connect_catalog(hostname="<your-deriva-host>", catalog_id="<catalog-id>")
```

If already connected (check `deriva://catalog/connections`), skip this step.

---

## Step 1: Get the overview

Read the dataset resource to see its types, current version, description, and member counts.

**Resource read:** `deriva://dataset/2-B4C8`

This returns:
- Dataset description
- Assigned types (e.g., `Complete`, `Training`, `Labeled`)
- Current version (e.g., `1.2.0`)
- Member count summary by element type

---

## Step 2: List the members

See what records are inside the dataset, grouped by element type (table). This reveals which tables have data.

**Tool:** `list_dataset_members`
```
list_dataset_members(dataset_rid="2-B4C8")
```

If there is a specific version you want to pin to (e.g., for reproducibility), pass it explicitly:
```
list_dataset_members(dataset_rid="2-B4C8", version="<version-from-step-1>")
```

This shows member RIDs grouped by table (e.g., 500 Image records, 20 Study records). It tells you the composition at a glance.

---

## Step 3: Browse actual data with denormalization

Pick the primary element type (likely `Image` or whatever table Step 2 revealed has the most members) and denormalize to see real column values joined with related tables.

**Tool:** `denormalize_dataset` — see image data with subject metadata
```
denormalize_dataset(dataset_rid="2-B4C8", include_tables=["Image", "Subject"], limit=10)
```

**Tool:** `denormalize_dataset` — see images with their labels
```
denormalize_dataset(dataset_rid="2-B4C8", include_tables=["Image", "Image_Classification"], limit=10)
```

Adjust `include_tables` based on what Step 2 showed is actually in the dataset. The `limit=10` cap keeps output manageable for an initial look; raise it once you know what you're looking for.

---

## Step 4: Check features and annotations

Find out what feature annotations exist on the member records (e.g., classification labels, embeddings, quality scores).

**Tool:** `fetch_table_features`
```
fetch_table_features(table_name="Image")
```

Replace `"Image"` with the primary element type found in Step 2.

---

## Step 5: Navigate the hierarchy

Check whether this dataset is a child of a larger collection (e.g., it might be a train split from a parent), or whether it has child splits of its own.

**Tool:** `list_dataset_parents`
```
list_dataset_parents(dataset_rid="2-B4C8")
```

**Tool:** `list_dataset_children`
```
list_dataset_children(dataset_rid="2-B4C8")
```

If there are children (splits), you can see all members across the full tree:
```
list_dataset_members(dataset_rid="2-B4C8", recurse=true)
```

---

## Step 6: Check provenance

Find out which executions (workflows) created or used this dataset — useful for understanding its origin and whether it has been used in previous experiments.

**Tool:** `list_dataset_executions`
```
list_dataset_executions(dataset_rid="2-B4C8")
```

---

## Step 7: Validate bag integrity (optional but recommended)

Before using the dataset in a real experiment, confirm the bag is internally consistent.

**Tool:** `validate_dataset_bag`
```
validate_dataset_bag(dataset_rid="2-B4C8", version="<version-from-step-1>")
```

---

## Step 8: Estimate download size (if you plan to download)

Before committing to a full download, get a size estimate.

**Tool:** `estimate_bag_size`
```
estimate_bag_size(dataset_rid="2-B4C8", version="<version-from-step-1>")
```

---

## Step 9: Generate a shareable URL

If you want to view the dataset in the Chaise web UI or share it with a colleague:

**Tool:** `cite`
```
cite(rid="2-B4C8")               # permanent snapshot URL for the current version
cite(rid="2-B4C8", current=true) # live URL
```

---

## Summary of call order

| # | Tool / Resource | Purpose |
|---|----------------|---------|
| 0 | `connect_catalog(...)` | Ensure active connection |
| 1 | `deriva://dataset/2-B4C8` | Overview: types, version, description |
| 2 | `list_dataset_members(dataset_rid="2-B4C8")` | Composition by element type |
| 3 | `denormalize_dataset(dataset_rid="2-B4C8", include_tables=[...], limit=10)` | Sample real data values |
| 4 | `fetch_table_features(table_name="Image")` | Available feature annotations |
| 5 | `list_dataset_parents(dataset_rid="2-B4C8")` | Is this a split or standalone? |
| 5 | `list_dataset_children(dataset_rid="2-B4C8")` | Does it have sub-splits? |
| 6 | `list_dataset_executions(dataset_rid="2-B4C8")` | Provenance / usage history |
| 7 | `validate_dataset_bag(dataset_rid="2-B4C8", version="...")` | Integrity check |
| 8 | `estimate_bag_size(dataset_rid="2-B4C8", version="...")` | Pre-download size check |
| 9 | `cite(rid="2-B4C8")` | Chaise URL for browser / sharing |

After working through these steps you will know: what tables are in the dataset and how many records, what columns and labels are present, where the dataset came from, whether it is a partition of a larger set, and whether it is safe to download and use in your experiment.
