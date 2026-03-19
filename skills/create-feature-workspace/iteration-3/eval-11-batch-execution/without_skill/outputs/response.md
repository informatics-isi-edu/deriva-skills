# Organizing Multi-Annotator Diagnosis Labeling with DerivaML

## Overview

For three pathologists independently labeling 2000 images, you want **one execution per pathologist** so that every feature value carries provenance back to the specific annotator's workflow run. You can then batch-insert all labels for a given pathologist in a single `add_feature_value` call (up to the full 2000 at once).

## Step-by-Step Approach

### 1. Set Up the Vocabulary and Feature (One-Time)

First, ensure you have a vocabulary for the diagnosis labels and a feature linking it to the Image table.

**Create the vocabulary** (if it doesn't already exist):

```
create_vocabulary(
    vocabulary_name="Diagnosis_Label",
    comment="Pathologist diagnosis labels for image classification"
)
```

**Add terms** for each diagnosis category:

```
add_term("Diagnosis_Label", "Normal", "No pathological findings")
add_term("Diagnosis_Label", "Abnormal", "Pathological findings present")
add_term("Diagnosis_Label", "Indeterminate", "Unable to determine diagnosis")
```

**Create the feature** on the Image table referencing the vocabulary:

```
create_feature(
    table_name="Image",
    feature_name="Diagnosis",
    comment="Pathologist diagnosis label for each image",
    terms=["Diagnosis_Label"]
)
```

### 2. Create One Execution Per Pathologist

Each pathologist gets their own execution so provenance tracks who produced which labels. You can optionally create a parent execution to group all three.

**Create a parent execution** (optional, for organizational grouping):

```
create_execution(
    workflow_name="Multi-Annotator Diagnosis Labeling",
    workflow_type="Annotation",
    description="Three independent pathologists labeling 2000 images for diagnosis"
)
start_execution()
stop_execution()
```

Save the parent execution RID (e.g., from `get_execution_info()`).

**Create Pathologist 1's execution:**

```
create_execution(
    workflow_name="Pathologist 1 - Diagnosis Labeling",
    workflow_type="Annotation",
    description="Dr. Smith labeling 2000 images for diagnosis",
    dataset_rids=["<dataset_rid>"]
)
start_execution()
```

Save the execution RID for Pathologist 1.

```
stop_execution()
```

Repeat for Pathologist 2 and Pathologist 3, each with their own `create_execution` call.

**Nest child executions under the parent** (optional):

```
add_nested_execution(
    parent_execution_rid="<parent_rid>",
    child_execution_rid="<pathologist_1_rid>",
    sequence=0
)
add_nested_execution(
    parent_execution_rid="<parent_rid>",
    child_execution_rid="<pathologist_2_rid>",
    sequence=1
)
add_nested_execution(
    parent_execution_rid="<parent_rid>",
    child_execution_rid="<pathologist_3_rid>",
    sequence=2
)
```

### 3. Batch-Insert Feature Values Per Pathologist

The `add_feature_value` tool accepts a list of entries, so you can submit all 2000 labels in a single call per pathologist. Each call is tied to that pathologist's execution for provenance.

**Pathologist 1's labels (all 2000 in one batch):**

```
add_feature_value(
    table_name="Image",
    feature_name="Diagnosis",
    entries=[
        {"target_rid": "1-AAA1", "value": "Normal"},
        {"target_rid": "1-AAA2", "value": "Abnormal"},
        {"target_rid": "1-AAA3", "value": "Normal"},
        {"target_rid": "1-AAA4", "value": "Indeterminate"},
        ... (all 2000 entries)
    ],
    execution_rid="<pathologist_1_execution_rid>"
)
```

**Pathologist 2's labels:**

```
add_feature_value(
    table_name="Image",
    feature_name="Diagnosis",
    entries=[
        {"target_rid": "1-AAA1", "value": "Normal"},
        {"target_rid": "1-AAA2", "value": "Normal"},
        {"target_rid": "1-AAA3", "value": "Abnormal"},
        {"target_rid": "1-AAA4", "value": "Normal"},
        ... (all 2000 entries)
    ],
    execution_rid="<pathologist_2_execution_rid>"
)
```

**Pathologist 3's labels:**

```
add_feature_value(
    table_name="Image",
    feature_name="Diagnosis",
    entries=[
        {"target_rid": "1-AAA1", "value": "Abnormal"},
        {"target_rid": "1-AAA2", "value": "Normal"},
        {"target_rid": "1-AAA3", "value": "Normal"},
        {"target_rid": "1-AAA4", "value": "Normal"},
        ... (all 2000 entries)
    ],
    execution_rid="<pathologist_3_execution_rid>"
)
```

Each image will end up with three feature value rows (one per pathologist), each linked to its respective execution for full provenance.

### 4. Querying Labels Later

**Get all diagnosis labels across all annotators:**

```
fetch_table_features(
    table_name="Image",
    feature_name="Diagnosis"
)
```

This returns all three values per image (one from each pathologist's execution).

**Get labels from a specific pathologist only:**

```
fetch_table_features(
    table_name="Image",
    feature_name="Diagnosis",
    execution="<pathologist_2_execution_rid>"
)
```

**Get the most recent label per image (e.g., after adjudication):**

```
fetch_table_features(
    table_name="Image",
    feature_name="Diagnosis",
    selector="newest"
)
```

**Get labels produced by all Annotation workflows:**

```
fetch_table_features(
    table_name="Image",
    feature_name="Diagnosis",
    workflow="Annotation"
)
```

## Complete MCP Tool Call Sequence

Here is the exact sequence of MCP tool calls with parameters:

1. `create_vocabulary(vocabulary_name="Diagnosis_Label", comment="Pathologist diagnosis labels")`
2. `add_term("Diagnosis_Label", "Normal", "No pathological findings")`
3. `add_term("Diagnosis_Label", "Abnormal", "Pathological findings present")`
4. `add_term("Diagnosis_Label", "Indeterminate", "Unable to determine")`
5. `create_feature(table_name="Image", feature_name="Diagnosis", comment="Pathologist diagnosis label", terms=["Diagnosis_Label"])`
6. `create_execution(workflow_name="Multi-Annotator Diagnosis Labeling", workflow_type="Annotation", description="Parent execution grouping three pathologist annotations", dataset_rids=["<dataset_rid>"])`
7. `start_execution()` then `stop_execution()` -- parent is just an organizational container
8. `create_execution(workflow_name="Pathologist 1 Labeling", workflow_type="Annotation", description="Dr. Smith independent diagnosis labels")`
9. `start_execution()` then `stop_execution()`
10. `create_execution(workflow_name="Pathologist 2 Labeling", workflow_type="Annotation", description="Dr. Jones independent diagnosis labels")`
11. `start_execution()` then `stop_execution()`
12. `create_execution(workflow_name="Pathologist 3 Labeling", workflow_type="Annotation", description="Dr. Lee independent diagnosis labels")`
13. `start_execution()` then `stop_execution()`
14. `add_nested_execution(parent_execution_rid="<parent>", child_execution_rid="<path1>", sequence=0)`
15. `add_nested_execution(parent_execution_rid="<parent>", child_execution_rid="<path2>", sequence=1)`
16. `add_nested_execution(parent_execution_rid="<parent>", child_execution_rid="<path3>", sequence=2)`
17. `add_feature_value(table_name="Image", feature_name="Diagnosis", entries=[...2000 entries...], execution_rid="<path1_rid>")`
18. `add_feature_value(table_name="Image", feature_name="Diagnosis", entries=[...2000 entries...], execution_rid="<path2_rid>")`
19. `add_feature_value(table_name="Image", feature_name="Diagnosis", entries=[...2000 entries...], execution_rid="<path3_rid>")`

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **One execution per pathologist** | Each label carries provenance to the specific annotator. You can filter/query by execution to get one pathologist's labels. |
| **Single `add_feature_value` call per pathologist** | The `entries` parameter accepts a list, so all 2000 labels go in one batch call rather than 2000 individual calls. This is far more efficient. |
| **Nested executions under a parent** | The parent groups the three annotation runs logically. Use `list_nested_executions` to find all related annotation work. |
| **Same feature name, different executions** | Multiple values per image are distinguished by their execution RID. Use `fetch_table_features` with `execution` parameter to retrieve a specific pathologist's labels. |
| **Vocabulary-backed terms** | Using controlled vocabulary (`Diagnosis_Label`) ensures consistency -- pathologists can only assign valid terms, preventing typos or inconsistent labels. |
