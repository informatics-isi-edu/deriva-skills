# Image Quality Tracking: Column vs. Feature

## Recommendation

**Create a feature, not a column.**

The requirement that different technicians rate quality differently — and that you need to know who scored what — is precisely the scenario DerivaML features were designed for. A column on the Image table stores one value per image with no provenance. A feature stores multiple scored observations per image, each linked to the execution (and therefore the workflow and the user/technician) that produced it.

---

## Why a Column Falls Short

Adding a `quality` column to the Image table would mean:

- One quality value per image — the last write wins, overwriting any previous score.
- No record of who scored it or when.
- No support for multiple reviewers rating the same image.
- No way to compare scores across technicians or identify disagreements.

This does not meet your stated requirements.

---

## How a Feature Solves This

A DerivaML feature creates a dedicated table (e.g., `Image_quality`) in the `deriva-ml` schema that stores (Image RID, execution RID, quality value) tuples. Because each score is tied to an Execution record, you automatically get:

- **Who scored it** — the Execution links to the workflow and the user who ran it.
- **When it was scored** — Execution has start/stop timestamps.
- **Multiple scores per image** — each technician's execution produces its own row; no overwriting.
- **Controlled vocabulary** — the quality values are stored in a vocabulary table, so you can enforce valid values (e.g., `Good`, `Adequate`, `Poor`) and add descriptions.
- **Audit trail** — the full lineage from image → score → execution → workflow → technician is queryable.

---

## Exact Steps and Tool Calls

### Step 1: Connect to the catalog

```
mcp__deriva__connect_catalog(
  hostname="your-deriva-host.org",
  catalog_id="1"           # replace with your catalog number
)
```

### Step 2: Confirm the Image table exists and note its schema

```
mcp__deriva__get_table(
  schema_name="isa",        # replace with the schema that contains Image
  table_name="Image"
)
```

Look at the result to confirm the table exists and note the primary key column name (typically `RID`).

### Step 3: Create the quality vocabulary

```
mcp__deriva__create_vocabulary(
  schema_name="deriva-ml",
  vocab_name="Image_Quality_Score",
  comment="Controlled vocabulary for fundus image quality ratings"
)
```

### Step 4: Add terms to the vocabulary

```
mcp__deriva__add_term(
  schema_name="deriva-ml",
  vocab_name="Image_Quality_Score",
  name="Good",
  description="Image is sharp, well-exposed, and fully captures the fundus"
)

mcp__deriva__add_term(
  schema_name="deriva-ml",
  vocab_name="Image_Quality_Score",
  name="Adequate",
  description="Image is usable but has minor artifacts or partial coverage"
)

mcp__deriva__add_term(
  schema_name="deriva-ml",
  vocab_name="Image_Quality_Score",
  name="Poor",
  description="Image is blurry, over/under-exposed, or substantially incomplete"
)
```

Add or remove terms to match your grading rubric.

### Step 5: Create the feature

```
mcp__deriva__create_feature(
  schema_name="isa",            # schema containing the Image table
  table_name="Image",
  feature_name="quality",
  feature_columns=[
    {
      "name": "Quality_Score",
      "type": "text",
      "vocab": "Image_Quality_Score",   # links to the vocabulary created above
      "nullok": false,
      "comment": "Technician quality rating for this image"
    },
    {
      "name": "Notes",
      "type": "text",
      "nullok": true,
      "comment": "Optional free-text notes from the reviewer"
    }
  ],
  comment="Quality scores assigned to fundus images by technicians during review executions"
)
```

This creates the `Image_quality` table in the `deriva-ml` schema with foreign keys to `Image` and `Execution`.

### Step 6: Verify the feature table was created

```
mcp__deriva__get_table(
  schema_name="deriva-ml",
  table_name="Image_quality"
)
```

Confirm the table has columns: `RID`, `Image`, `Execution`, `Quality_Score`, `Notes`, plus standard system columns.

---

## How Technicians Record Scores

Each technician runs a review workflow. The sequence is:

1. **Create or look up a Workflow** for the quality review process (`mcp__deriva__create_workflow` or `mcp__deriva__lookup_workflow_by_url`).
2. **Start an Execution** under that workflow — one execution per technician per review session (`mcp__deriva__start_execution`). The execution is linked to the user's identity.
3. **Add feature values** for each image reviewed:
   ```
   mcp__deriva__add_feature_value(
     schema_name="isa",
     table_name="Image",
     feature_name="quality",
     row_rid="<Image RID>",
     execution_rid="<Execution RID>",
     values={
       "Quality_Score": "Good",
       "Notes": "Slight lens flare in upper-left quadrant but fundus fully visible"
     }
   )
   ```
4. **Stop the Execution** when done (`mcp__deriva__stop_execution`).

Because each score row carries the Execution RID, you can always query:
- All scores by a given technician: filter `Image_quality` by executions belonging to that user's workflows.
- All scores for a given image: filter `Image_quality` by Image RID — you get every technician's score as a separate row.
- Inter-rater agreement: join two technicians' score rows for the same image and compare.

---

## Summary

| Concern | Column | Feature |
|---|---|---|
| Multiple raters per image | No (overwrites) | Yes |
| Who scored it | No | Yes (via Execution) |
| When it was scored | No | Yes (via Execution timestamps) |
| Controlled vocabulary | Possible but manual | Built-in |
| Audit trail / lineage | No | Yes |

Use a feature.
