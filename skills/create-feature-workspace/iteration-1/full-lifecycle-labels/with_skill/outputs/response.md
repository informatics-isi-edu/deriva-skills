# Setting Up Diagnostic Labels for Chest X-Ray Images

## Design Analysis

### Is this a feature or a column?

This is clearly a feature, not a column:

- **Provenance required**: Multiple radiologists are labeling the same images independently — we need to track who labeled what (which execution, which annotator).
- **Multivalued by design**: Multiple radiologists label the same image, producing multiple values per record. Features accumulate these values and support inter-annotator agreement analysis.
- **Controlled vocabulary**: The 5 diagnosis categories must be consistent across all annotators.
- **ML training labels**: These labels will serve as ground truth for training image classifiers.
- **Model confidence score**: A separate float value from a model run also needs provenance.

### Feature design

The task involves two distinct annotation acts from different sources:

1. **Radiologist diagnostic labels** — assigned by human annotators in separate annotation executions. Each radiologist runs their own execution.
2. **Model confidence scores** — assigned by a model in a separate execution.

These come from different processes (human annotators vs. a model), so they should be **separate features**:

- Feature 1: `Diagnosis` — term-based, references `Diagnosis_Type` vocabulary, includes a `Reviewer` metadata FK to track which radiologist assigned each label.
- Feature 2: `Model_Confidence` — term-based with a float metadata column, or alternatively a metadata-only feature. Since confidence is typically associated with a predicted class, a single feature combining both makes sense: `Model_Prediction` with `Diagnosis_Type` (predicted class) and a `confidence` float4 metadata column.

If the model only produces a confidence score without a class label, `Model_Confidence` would be a metadata-only feature — but that's unusual. The design below assumes the model produces both a predicted class and a confidence score.

**Summary:**
- `Diagnosis` feature: `terms=["Diagnosis_Type"]`, `metadata=["Radiologist"]` — for human radiologist labels
- `Model_Prediction` feature: `terms=["Diagnosis_Type"]`, `metadata=[{"name": "confidence", "type": {"typename": "float4"}}]` — for model predictions with confidence

---

## Step-by-Step Tool Calls

### Step 0: Connect to the catalog

```
connect_catalog(
    hostname="your-deriva-server.example.org",
    catalog_id="1"
)
```

### Step 1: Assess — check for existing features

Before creating anything, check whether a `Diagnosis` feature or similar already exists on the `Image` table.

```
Read resource: deriva://catalog/features
```

Also check for existing features specifically on the Image table:

```
Read resource: deriva://table/Image/feature-values/newest
```

Assuming no existing `Diagnosis` or `Model_Prediction` features are found, proceed.

---

### Step 2: Create the `Diagnosis_Type` vocabulary and its terms

```
create_vocabulary(
    vocabulary_name="Diagnosis_Type",
    comment="Diagnostic classification categories for chest X-ray images"
)
```

```
add_term(
    vocabulary_name="Diagnosis_Type",
    term_name="Normal",
    description="No pathological findings detected"
)
```

```
add_term(
    vocabulary_name="Diagnosis_Type",
    term_name="Pneumonia",
    description="Bacterial or viral pneumonia present"
)
```

```
add_term(
    vocabulary_name="Diagnosis_Type",
    term_name="COVID-19",
    description="COVID-19 pneumonia findings present"
)
```

```
add_term(
    vocabulary_name="Diagnosis_Type",
    term_name="Tuberculosis",
    description="Tuberculosis findings present"
)
```

```
add_term(
    vocabulary_name="Diagnosis_Type",
    term_name="Lung_Cancer",
    description="Lung cancer findings present"
)
```

---

### Step 3: Create the `Diagnosis` feature (for radiologist labels)

The `metadata=["Radiologist"]` parameter adds a foreign key column to the `Radiologist` table, enabling per-value tracking of which radiologist assigned each label. (This assumes a `Radiologist` table exists in the catalog. If the catalog only has a general `User` or `Annotator` table, substitute that name.)

```
create_feature(
    table_name="Image",
    feature_name="Diagnosis",
    terms=["Diagnosis_Type"],
    metadata=["Radiologist"],
    comment="Radiologist-assigned diagnostic classification for chest X-ray images. Values from Diagnosis_Type vocabulary (Normal, Pneumonia, COVID-19, Tuberculosis, Lung_Cancer). Supports multiple independent annotations per image for inter-annotator agreement analysis. Primary ground truth label for training classification models."
)
```

This creates the `Diagnosis_Feature_Value` table with columns:
- `Image` (FK to Image table — the target record)
- `Diagnosis_Type` (FK to Diagnosis_Type vocabulary)
- `Radiologist` (FK to Radiologist table — provenance: which radiologist)
- `Execution` (FK to Execution table — provenance: which annotation run)
- `Feature_Name` (FK to Feature_Name vocabulary)

---

### Step 4: Create the `Model_Prediction` feature (for model confidence scores)

```
create_feature(
    table_name="Image",
    feature_name="Model_Prediction",
    terms=["Diagnosis_Type"],
    metadata=[{"name": "confidence", "type": {"typename": "float4"}, "nullok": true, "comment": "Model confidence score for the predicted class, range 0.0-1.0"}],
    comment="Automated model prediction for chest X-ray diagnosis. Includes predicted class from Diagnosis_Type vocabulary and a confidence score (float, 0.0-1.0). Provenance tracked through Execution enables comparison across model versions and runs."
)
```

This creates the `Model_Prediction_Feature_Value` table with columns:
- `Image` (FK to Image table)
- `Diagnosis_Type` (FK to Diagnosis_Type vocabulary — predicted class)
- `confidence` (float4 — model confidence score)
- `Execution` (FK to Execution table)
- `Feature_Name` (FK to Feature_Name vocabulary)

---

### Step 5: Create a workflow for radiologist annotation sessions

```
create_workflow(
    workflow_name="Radiologist Annotation",
    workflow_type="Annotation",
    description="Manual diagnostic labeling of chest X-ray images by board-certified radiologists. Each radiologist runs a separate execution so labels are independently tracked."
)
```

---

### Step 6: Add radiologist labels (one execution per radiologist)

Each radiologist gets their own execution so annotations are independently attributed. Here is the pattern for Radiologist A (repeat for each radiologist):

**Start the execution:**

```
create_execution(
    workflow_name="Radiologist Annotation",
    description="Diagnostic labeling session — Radiologist A (Dr. Smith)",
    execution_rid=null
)
```

```
start_execution()
```

**Add feature values for the images this radiologist labeled:**

For a single-value add (if each image gets one label per call):

```
add_feature_value_record(
    table_name="Image",
    feature_name="Diagnosis",
    entries=[
        {"target_rid": "2-XRAY0001", "Diagnosis_Type": "Normal",    "Radiologist": "3-RAD1"},
        {"target_rid": "2-XRAY0002", "Diagnosis_Type": "Pneumonia",  "Radiologist": "3-RAD1"},
        {"target_rid": "2-XRAY0003", "Diagnosis_Type": "COVID-19",   "Radiologist": "3-RAD1"},
        {"target_rid": "2-XRAY0004", "Diagnosis_Type": "Tuberculosis","Radiologist": "3-RAD1"},
        {"target_rid": "2-XRAY0005", "Diagnosis_Type": "Lung_Cancer","Radiologist": "3-RAD1"}
        ...
    ]
)
```

*(Repeat for all ~10,000 images assigned to this radiologist. The entries list can be batched.)*

**Stop the execution:**

```
stop_execution()
```

**Repeat Steps 6 for each additional radiologist**, each in their own separate `create_execution` / `start_execution` / `stop_execution` block. Each execution is independently attributed in the `Execution` column of every feature value record.

---

### Step 7: Create a workflow for model inference

```
create_workflow(
    workflow_name="Chest X-Ray Classifier Inference",
    workflow_type="Inference",
    description="Automated diagnostic classification of chest X-ray images. Produces predicted class and confidence score per image."
)
```

---

### Step 8: Add model confidence scores

**Start the execution:**

```
create_execution(
    workflow_name="Chest X-Ray Classifier Inference",
    description="Model v1.0 inference run on full chest X-ray dataset"
)
```

```
start_execution()
```

**Add model predictions with confidence scores:**

```
add_feature_value_record(
    table_name="Image",
    feature_name="Model_Prediction",
    entries=[
        {"target_rid": "2-XRAY0001", "Diagnosis_Type": "Normal",    "confidence": 0.97},
        {"target_rid": "2-XRAY0002", "Diagnosis_Type": "Pneumonia",  "confidence": 0.83},
        {"target_rid": "2-XRAY0003", "Diagnosis_Type": "COVID-19",   "confidence": 0.91},
        {"target_rid": "2-XRAY0004", "Diagnosis_Type": "Tuberculosis","confidence": 0.76},
        {"target_rid": "2-XRAY0005", "Diagnosis_Type": "Lung_Cancer","confidence": 0.88}
        ...
    ]
)
```

**Stop the execution:**

```
stop_execution()
```

---

### Step 9: Verify the feature values are recorded

Browse all feature values on the Image table, deduplicated to newest per record:

```
Read resource: deriva://table/Image/feature-values/newest
```

Or inspect values for a specific feature with full provenance (showing all radiologist labels per image):

```
Read resource: deriva://feature/Image/Diagnosis/values
```

Fetch with filtering — e.g., only values from a specific radiologist's execution (`3-EXEC5`):

```
fetch_table_features(
    table_name="Image",
    feature_name="Diagnosis",
    execution="3-EXEC5"
)
```

Or get the newest label per image (for downstream use as a single ground truth):

```
fetch_table_features(
    table_name="Image",
    feature_name="Diagnosis",
    selector="newest"
)
```

---

## Summary of What Gets Created

| Artifact | Name | Type |
|----------|------|------|
| Vocabulary | `Diagnosis_Type` | Controlled vocabulary with 5 terms |
| Feature 1 | `Diagnosis` on `Image` | Term-based + Radiologist FK metadata |
| Feature table 1 | `Diagnosis_Feature_Value` | Association table |
| Feature 2 | `Model_Prediction` on `Image` | Term-based + float4 confidence metadata |
| Feature table 2 | `Model_Prediction_Feature_Value` | Association table |
| Workflow | `Radiologist Annotation` | Annotation workflow type |
| Executions (N) | One per radiologist | Each radiologist's labeling session |
| Workflow | `Chest X-Ray Classifier Inference` | Inference workflow type |
| Execution (1+) | One per model run | Model inference provenance |

## Key Design Decisions

1. **Two separate features** (`Diagnosis` and `Model_Prediction`) rather than one, because human annotation and model inference are independent processes with different workflows and provenance requirements.

2. **One execution per radiologist** — this is how "who labeled what" is tracked. Each radiologist's execution creates a separate provenance chain. All feature value records from that execution point to it via the `Execution` FK.

3. **`Radiologist` FK in `Diagnosis` metadata** — provides an additional direct link to the specific radiologist within each feature value record, complementing the execution-level provenance. This enables queries like "show me all labels by Dr. Smith" without having to join through executions.

4. **Reusing `Diagnosis_Type` vocabulary** across both features ensures consistent category names for both human labels and model predictions, making it straightforward to compute agreement metrics.

5. **`nullok: true` on `confidence`** — not every model run may produce a confidence score; making the column nullable avoids breaking inserts for models that only provide a class label.
