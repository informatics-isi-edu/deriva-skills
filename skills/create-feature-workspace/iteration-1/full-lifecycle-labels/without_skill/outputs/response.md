# Setting Up Diagnostic Labels for Chest X-Ray Images in DerivaML

## Overview

This document describes the exact sequence of steps and MCP tool calls to set up a multi-label, multi-annotator diagnostic feature for ~10,000 chest X-ray images. The feature captures:

- A categorical diagnosis label (one of 5 categories)
- Which radiologist assigned the label (per-annotator tracking)
- An optional model confidence score

---

## Prerequisites

- A Deriva catalog already exists and is connected
- The chest X-ray images are stored as assets in the catalog (e.g., in a table called `CXR_Image`)
- You know the catalog ID (e.g., `1`)

---

## Step 1: Connect to the Catalog

```
mcp__deriva__connect_catalog(catalog_id="1")
mcp__deriva__set_active_catalog(catalog_id="1")
```

---

## Step 2: Create a Vocabulary for Diagnosis Categories

The 5 diagnosis categories need to be represented as controlled vocabulary terms so that labels are consistent and queryable.

```
mcp__deriva__create_vocabulary(
    schema_name="vocab",
    table_name="Diagnosis"
)
```

Then add each term:

```
mcp__deriva__add_term(
    schema_name="vocab",
    table_name="Diagnosis",
    name="Normal",
    description="No pathological findings detected"
)

mcp__deriva__add_term(
    schema_name="vocab",
    table_name="Diagnosis",
    name="Pneumonia",
    description="Bacterial or viral pneumonia"
)

mcp__deriva__add_term(
    schema_name="vocab",
    table_name="Diagnosis",
    name="COVID-19",
    description="COVID-19 pneumonia pattern"
)

mcp__deriva__add_term(
    schema_name="vocab",
    table_name="Diagnosis",
    name="Tuberculosis",
    description="Tuberculosis findings"
)

mcp__deriva__add_term(
    schema_name="vocab",
    table_name="Diagnosis",
    name="Lung_Cancer",
    description="Malignant pulmonary findings"
)
```

---

## Step 3: Create the Feature

The feature ties a diagnosis label (and optional confidence score) to each chest X-ray image. Because multiple radiologists label the same image independently, this must be a **per-annotator** feature — meaning the same image can have multiple feature records, one per labeler.

```
mcp__deriva__create_feature(
    table_schema="deriva",
    table_name="CXR_Image",
    feature_name="Diagnosis",
    feature_columns=[
        {
            "name": "Diagnosis",
            "type": "text",
            "nullok": false,
            "vocab_table": {"schema": "vocab", "table": "Diagnosis"}
        },
        {
            "name": "Confidence_Score",
            "type": "float4",
            "nullok": true,
            "description": "Model confidence score (0.0–1.0); null if label is human-only"
        },
        {
            "name": "Annotator",
            "type": "text",
            "nullok": false,
            "description": "Identity of the radiologist or model that assigned this label"
        }
    ]
)
```

**Key design notes:**

- `Diagnosis` is a foreign key into the `vocab.Diagnosis` vocabulary table — this enforces controlled vocabulary and prevents typos.
- `Confidence_Score` is nullable: human radiologist labels leave it null; model-generated labels populate it.
- `Annotator` records which radiologist (or model name) assigned the label, enabling per-annotator analysis and inter-rater agreement computation.
- The feature table is **not** constrained to one record per image — multiple records per image are allowed, one for each annotator.

---

## Step 4: Verify the Feature Was Created

```
mcp__deriva__fetch_table_features(
    table_schema="deriva",
    table_name="CXR_Image"
)
```

Expected: a feature named `Diagnosis` appears in the results, associated with `CXR_Image`.

---

## Step 5: Add Feature Values (Labels)

For each image-annotator pair, insert a feature value record. This is typically done programmatically in bulk (e.g., from a CSV export of radiologist annotations), but the MCP call would look like:

```
mcp__deriva__add_feature_value_record(
    table_schema="deriva",
    table_name="CXR_Image",
    feature_name="Diagnosis",
    row_rid="<RID of the CXR_Image record>",
    values={
        "Diagnosis": "Pneumonia",
        "Confidence_Score": null,
        "Annotator": "dr_smith"
    }
)
```

For a model-generated label with a confidence score:

```
mcp__deriva__add_feature_value_record(
    table_schema="deriva",
    table_name="CXR_Image",
    feature_name="Diagnosis",
    row_rid="<RID of the CXR_Image record>",
    values={
        "Diagnosis": "Pneumonia",
        "Confidence_Score": 0.94,
        "Annotator": "chest-xray-classifier-v2"
    }
)
```

For bulk insertion of ~10,000 images across multiple radiologists, use `insert_records` directly against the generated feature table:

```
mcp__deriva__insert_records(
    schema_name="deriva",
    table_name="CXR_Image_Diagnosis_Feature",
    records=[
        {
            "CXR_Image": "<RID>",
            "Diagnosis": "Normal",
            "Confidence_Score": null,
            "Annotator": "dr_jones"
        },
        {
            "CXR_Image": "<RID>",
            "Diagnosis": "Normal",
            "Confidence_Score": 0.87,
            "Annotator": "chest-xray-classifier-v2"
        },
        ...
    ]
)
```

`insert_records` accepts batches; for 10,000 images × N annotators, split into batches of ~500–1000 records.

---

## Step 6: Add Visible Columns for the Feature Table (Optional UI Polish)

To make the feature table display cleanly in Chaise, configure the visible columns:

```
mcp__deriva__set_visible_columns(
    schema_name="deriva",
    table_name="CXR_Image_Diagnosis_Feature",
    visible_columns=[
        "CXR_Image",
        "Diagnosis",
        "Annotator",
        "Confidence_Score",
        "RCT",
        "RMT"
    ]
)
```

---

## Resulting Data Model

```
CXR_Image (1) ────────< CXR_Image_Diagnosis_Feature (many)
                              │
                              ├── Diagnosis ──> vocab.Diagnosis (FK)
                              ├── Annotator  (free text: radiologist ID or model name)
                              └── Confidence_Score (nullable float)
```

Each row in `CXR_Image_Diagnosis_Feature` represents one label assigned by one annotator to one image. A single image can have many rows — one per radiologist and/or one per model run.

---

## Summary of Tool Calls in Order

| Step | Tool | Purpose |
|------|------|---------|
| 1 | `connect_catalog` | Connect to the catalog |
| 2 | `set_active_catalog` | Set working catalog |
| 3 | `create_vocabulary` | Create `vocab.Diagnosis` vocabulary table |
| 4–8 | `add_term` ×5 | Add the 5 diagnosis terms |
| 9 | `create_feature` | Create `Diagnosis` feature on `CXR_Image` with Diagnosis, Confidence_Score, Annotator columns |
| 10 | `fetch_table_features` | Verify feature creation |
| 11+ | `insert_records` (batched) | Bulk-load ~10,000+ label records |
| 12 | `set_visible_columns` | Configure Chaise UI display |

---

## Inter-Rater Analysis

Once labels are loaded, inter-rater agreement (e.g., Cohen's kappa, Fleiss' kappa) can be computed by querying:

```
mcp__deriva__query_table(
    schema_name="deriva",
    table_name="CXR_Image_Diagnosis_Feature",
    filters=[]
)
```

The result provides all (image, annotator, diagnosis) triples needed for agreement computation. Images labeled by all N radiologists can be identified by grouping on `CXR_Image` and counting distinct `Annotator` values.
