# Organizing Multi-Annotator Diagnosis Labels: Executions and Batching Strategy

## Recommended Architecture

For three pathologists independently labeling 2000 images with diagnosis labels, use **one execution per pathologist**. This is the core principle: each annotator's labeling session maps to a single execution, providing clean provenance and enabling inter-annotator agreement analysis downstream.

Do NOT create one execution per label (2000 x 3 = 6000 executions would clutter provenance) or one execution for all three pathologists (you would lose the ability to distinguish who labeled what).

## Exact Sequence of MCP Tool Calls

### Phase 1: Connect and Assess

```
connect_catalog(hostname="your-server.org", catalog_id="1")
```

Check whether a Diagnosis feature already exists:

```
Read resource: deriva://catalog/features
```

If a suitable feature exists, skip to Phase 3. If a feature exists but needs more terms, add terms to the existing vocabulary rather than creating a new feature.

### Phase 2: Create Vocabulary and Feature (if needed)

**Step 2a: Create the vocabulary**

```
create_vocabulary(
    vocabulary_name="Diagnosis_Type",
    comment="Pathologist diagnosis classifications for image review"
)
```

**Step 2b: Add terms**

```
add_term(
    vocabulary_name="Diagnosis_Type",
    term_name="Normal",
    description="No pathological abnormality detected"
)

add_term(
    vocabulary_name="Diagnosis_Type",
    term_name="Abnormal",
    description="Pathological abnormality present"
)
```

(Add all additional diagnosis categories your pathologists will use.)

**Step 2c: Inspect the vocabulary to confirm terms are correct**

```
Read resource: deriva://vocabulary/Diagnosis_Type
```

**Step 2d: Create the feature**

```
create_feature(
    table_name="Image",
    feature_name="Diagnosis",
    terms=["Diagnosis_Type"],
    comment="Pathologist diagnosis label for this image. Multiple pathologists label independently for inter-annotator agreement. Values from the Diagnosis_Type vocabulary."
)
```

**Step 2e: Confirm the feature structure**

```
Read resource: deriva://feature/Image/Diagnosis
```

This tells you the exact column names, which are required, and what values are valid -- essential before batching values.

### Phase 3: Add Feature Values -- One Execution Per Pathologist

#### Pathologist A

**Step 3a: Create and start the execution**

```
create_execution(
    workflow_name="Pathologist A Diagnosis Review",
    workflow_type="Annotation",
    description="Independent diagnosis labeling by Pathologist A -- batch of 2000 images"
)

start_execution()
```

**Step 3b: Batch add all of Pathologist A's labels**

Use `add_feature_value` with the full batch. Both `add_feature_value` and `add_feature_value_record` accept lists of entries, so send all 2000 labels in one call (or a few large batches if needed for practical reasons):

```
add_feature_value(
    table_name="Image",
    feature_name="Diagnosis",
    entries=[
        {"target_rid": "2-IMG0001", "value": "Normal"},
        {"target_rid": "2-IMG0002", "value": "Abnormal"},
        {"target_rid": "2-IMG0003", "value": "Normal"},
        ... (all 2000 entries)
    ]
)
```

If the feature has multiple columns (e.g., diagnosis + confidence), use `add_feature_value_record` instead:

```
add_feature_value_record(
    table_name="Image",
    feature_name="Diagnosis",
    entries=[
        {"target_rid": "2-IMG0001", "Diagnosis_Type": "Normal", "confidence": 0.95},
        {"target_rid": "2-IMG0002", "Diagnosis_Type": "Abnormal", "confidence": 0.80},
        ... (all 2000 entries)
    ]
)
```

**Step 3c: Stop the execution**

```
stop_execution()
```

#### Pathologist B

Repeat the same pattern with a separate execution:

```
create_execution(
    workflow_name="Pathologist B Diagnosis Review",
    workflow_type="Annotation",
    description="Independent diagnosis labeling by Pathologist B -- batch of 2000 images"
)

start_execution()

add_feature_value(
    table_name="Image",
    feature_name="Diagnosis",
    entries=[
        {"target_rid": "2-IMG0001", "value": "Abnormal"},
        {"target_rid": "2-IMG0002", "value": "Abnormal"},
        ... (all 2000 entries for Pathologist B)
    ]
)

stop_execution()
```

#### Pathologist C

Same pattern again:

```
create_execution(
    workflow_name="Pathologist C Diagnosis Review",
    workflow_type="Annotation",
    description="Independent diagnosis labeling by Pathologist C -- batch of 2000 images"
)

start_execution()

add_feature_value(
    table_name="Image",
    feature_name="Diagnosis",
    entries=[
        {"target_rid": "2-IMG0001", "value": "Normal"},
        {"target_rid": "2-IMG0002", "value": "Normal"},
        ... (all 2000 entries for Pathologist C)
    ]
)

stop_execution()
```

### Phase 4: Verify and Query

**Check all values were written:**

```
Read resource: deriva://feature/Image/Diagnosis/values
```

This returns all 6000 values (3 annotators x 2000 images) with full provenance, including which execution produced each value.

**Get the newest label per image (any annotator):**

```
fetch_table_features(
    table_name="Image",
    feature_name="Diagnosis",
    selector="newest"
)
```

**Get labels from a specific pathologist:**

```
fetch_table_features(
    table_name="Image",
    feature_name="Diagnosis",
    execution="<pathologist_A_execution_rid>"
)
```

**Get consensus (majority vote) labels:**

```
fetch_table_features(
    table_name="Image",
    feature_name="Diagnosis",
    selector="majority_vote"
)
```

This returns the most common label per image across all three pathologists. Ties are broken by the most recent value.

## Summary of Key Principles

| Principle | Approach |
|-----------|----------|
| Execution granularity | One execution per pathologist (not per label, not per batch chunk) |
| Batching | Send all 2000 labels per pathologist in one `add_feature_value` call |
| Feature design | Single feature ("Diagnosis") shared by all pathologists -- multivalued by design |
| Provenance | Each label links to its execution, so you can always trace which pathologist assigned which label |
| Resolving duplicates | Use `selector="majority_vote"` for consensus, `execution="<rid>"` for a specific pathologist, or `selector="newest"` for the latest label |
| Workflow type | Use `"Annotation"` for human labeling; later model predictions would use a different workflow type like `"Inference"` |

## Practical Batching Notes

- Both `add_feature_value` and `add_feature_value_record` accept arbitrarily large lists of entries. Send all 2000 at once rather than calling the tool 2000 times.
- If the labels arrive incrementally (e.g., a pathologist labels 500 images per day over 4 days), you have two options:
  - **Preferred**: Keep the execution open (`create_execution` + `start_execution` at the beginning, call `add_feature_value` multiple times as batches arrive, then `stop_execution` when the pathologist finishes all 2000). All labels from one pathologist stay in one execution.
  - **Acceptable alternative**: Create a separate execution per session (e.g., "Pathologist A -- Day 1", "Pathologist A -- Day 2"). This is acceptable if you want finer-grained provenance, but the `workflow` selector lets you group by workflow type ("Annotation") regardless.
- Term names must exactly match vocabulary entries (case-sensitive). Confirm valid terms by reading `deriva://vocabulary/Diagnosis_Type` before batching.
