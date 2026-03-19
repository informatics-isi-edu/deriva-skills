# Browsing a Multi-Element Dataset Independently by Type

## Task

Dataset RID `4-MULTI` contains two element types — Subject (~200 records) and Image (~8,000 records). The goal is to:

1. Get an overview of the full dataset
2. Drill into Subject records and see demographics
3. Drill into Image records and check modality breakdown

---

## Step 1: Verify catalog connection

Before anything else, confirm an active catalog connection.

**Resource read:** `deriva://catalog/connections`

If not connected:

```
connect_catalog(hostname="<hostname>", catalog_id="<catalog_id>")
```

---

## Step 2: Get the dataset overview

Read the dataset resource to see its description, types, version, and registered element types.

**Resource read:** `deriva://dataset/4-MULTI`

This returns the dataset's metadata: its current version, dataset types (e.g., Complete, Labeled), description, and the tables contributing members.

---

## Step 3: List all members grouped by element type

```
list_dataset_members(dataset_rid="4-MULTI")
```

**What this returns:** Members grouped by table name. You will see two groups:

- `Subject`: ~200 RIDs
- `Image`: ~8,000 RIDs

This confirms both element types are present and shows their exact counts before drilling in.

---

## Step 4: Browse Subject records — demographics

Use `denormalize_dataset` scoped to just the Subject table. This returns Subject records joined with any related tables that carry demographic attributes (e.g., age, sex, diagnosis).

```
denormalize_dataset(
    dataset_rid="4-MULTI",
    include_tables=["Subject"],
    limit=50
)
```

To focus only on demographic columns of interest, inspect what columns are available first:

```
get_table(table_name="Subject")
```

Then re-run `denormalize_dataset` with a specific limit or filter criteria if needed. For example, to see only subjects of a particular sex or age range, pass column criteria once you know the column names.

**What you learn:** The Subject records with their demographic fields (age, sex, diagnosis, or whatever attributes the catalog stores). With ~200 subjects the full set fits in a single denormalized view.

---

## Step 5: Check what features/annotations exist on Subject

```
fetch_table_features(table_name="Subject")
```

This shows any feature tables attached to Subject — for example, clinical labels or cohort annotations — which may contain additional demographic or phenotypic data beyond the Subject table's own columns.

---

## Step 6: Browse Image records — modality breakdown

Scope `denormalize_dataset` to just the Image table, joined with any modality-carrying table. First check what related tables exist:

```
get_table(table_name="Image")
```

Then denormalize:

```
denormalize_dataset(
    dataset_rid="4-MULTI",
    include_tables=["Image"],
    limit=20
)
```

With 8,000 images a small limit is appropriate for an initial look. The result will include every column on Image, including any modality/acquisition type column stored directly on the table.

If modality is stored in a related vocabulary table (e.g., `Modality` or `Image_Modality`), include it:

```
denormalize_dataset(
    dataset_rid="4-MULTI",
    include_tables=["Image", "Modality"],
    limit=20
)
```

---

## Step 7: Check Image features and labels

```
fetch_table_features(table_name="Image")
```

This reveals any annotation tables attached to Image (e.g., `Image_Classification`, `Image_Quality`). If modality is tracked as a feature rather than a direct column, it will appear here.

---

## Step 8: Aggregate modality breakdown (if needed)

`denormalize_dataset` returns rows — to get a count-by-modality summary, scan the returned rows and group by the modality column. Alternatively, use:

```
query_table(
    table_name="Image",
    filters={"Dataset": "4-MULTI"}
)
```

and inspect the modality values across all returned rows. With 8,000 images, use pagination or a targeted filter to enumerate unique modality values.

---

## Summary of Tool Call Sequence

| Step | Tool / Resource | Purpose |
|------|----------------|---------|
| 1 | `deriva://catalog/connections` | Verify active connection |
| 2 | `deriva://dataset/4-MULTI` | Dataset overview: types, version, description |
| 3 | `list_dataset_members(dataset_rid="4-MULTI")` | Member counts grouped by element type |
| 4 | `get_table(table_name="Subject")` | Inspect Subject columns before denormalizing |
| 5 | `denormalize_dataset(dataset_rid="4-MULTI", include_tables=["Subject"], limit=50)` | Browse Subject demographics |
| 6 | `fetch_table_features(table_name="Subject")` | Check demographic feature tables on Subject |
| 7 | `get_table(table_name="Image")` | Inspect Image columns (find modality column) |
| 8 | `denormalize_dataset(dataset_rid="4-MULTI", include_tables=["Image"], limit=20)` | Browse Image records |
| 9 | `fetch_table_features(table_name="Image")` | Check annotation/feature tables on Image |

---

## Key Points

- `list_dataset_members` groups results by element type automatically — this is the primary way to see what types are present and at what scale.
- `denormalize_dataset` with `include_tables` scoped to a single table lets you isolate one element type for focused inspection without mixing in the other. Specifying just `["Subject"]` excludes Image rows entirely and vice versa.
- `fetch_table_features` reveals annotation tables that may hold the demographics or modality data you are looking for, especially if those values are stored as features rather than direct columns.
- For the modality breakdown with 8,000 images, start with a small `limit` to see the column structure, then filter or paginate to enumerate all modality values.
