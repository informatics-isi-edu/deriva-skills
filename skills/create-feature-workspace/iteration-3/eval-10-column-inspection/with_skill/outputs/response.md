# How to Inspect the Diagnosis Feature and Determine Valid Values

You need two things before you can add labels for 500 images: (1) know what columns the Diagnosis feature expects and which are required, and (2) know what term values are valid. Here is the exact sequence of steps.

## Step 1: Inspect the Feature Structure

Read the feature definition resource to see all columns, their types, and whether they are required or optional:

```
Read resource: deriva://feature/Image/Diagnosis
```

This returns:

- **term_columns** -- the vocabulary-controlled fields. Each entry shows the vocabulary table name (e.g., `Diagnosis_Type`) and whether the column is required (`required: true/false`).
- **asset_columns** -- any file reference fields (may be empty for a term-only feature).
- **value_columns** -- free-form fields like confidence scores, with their data types (e.g., `float4`, `text`).
- **required_fields** -- a flat list of all column names that must be present in every entry you submit.

For example, a Diagnosis feature created with `terms=["Diagnosis_Type"]` and `metadata=[{"name": "confidence", "type": {"typename": "float4"}}]` would show:

- `term_columns`: `Diagnosis_Type` (required)
- `value_columns`: `confidence` (optional, float4)
- `required_fields`: `["Diagnosis_Type"]`

This tells you that every entry must include a `Diagnosis_Type` value, but `confidence` can be omitted.

## Step 2: Determine Valid Values for Term Columns

For each term column listed in the feature definition, read the referenced vocabulary to see the exact term names you can use:

```
Read resource: deriva://vocabulary/Diagnosis_Type
```

This returns all terms in the vocabulary -- for example: `Normal`, `Abnormal`, `Suspected Glaucoma`, etc. Term names are **case-sensitive** -- `"Normal"` is valid but `"normal"` will produce an error.

If the terms you need do not exist yet, add them before labeling:

```
add_term(vocabulary_name="Diagnosis_Type", term_name="New_Category", description="Description of this category")
```

## Step 3: Add Labels Within an Execution

Once you know the required columns and valid values, create an execution and batch-add the labels. All 500 labels from one annotator session should go in a single execution.

```
create_execution(workflow_name="Expert Diagnosis Annotation", workflow_type="Annotation",
                 description="Diagnosis labeling for batch of 500 images")
start_execution()
```

**If the feature has a single term column** (simple feature), use `add_feature_value`:

```
add_feature_value(table_name="Image", feature_name="Diagnosis",
                  entries=[
                      {"target_rid": "2-IMG1", "value": "Normal"},
                      {"target_rid": "2-IMG2", "value": "Abnormal"},
                      ... # all 500 entries in one batch call
                  ])
```

**If the feature has multiple columns** (e.g., term + confidence), use `add_feature_value_record` with explicit column names:

```
add_feature_value_record(table_name="Image", feature_name="Diagnosis",
                          entries=[
                              {"target_rid": "2-IMG1", "Diagnosis_Type": "Normal", "confidence": 0.95},
                              {"target_rid": "2-IMG2", "Diagnosis_Type": "Abnormal"},
                              ... # confidence is optional, so some entries can omit it
                          ])
```

```
stop_execution()
```

## Summary of MCP Calls

Here is the complete sequence of MCP tool calls / resource reads, with parameters:

| Step | Action | Parameters |
|------|--------|------------|
| 1 | `Read resource: deriva://feature/Image/Diagnosis` | -- |
| 2 | `Read resource: deriva://vocabulary/{vocab_table}` | Use the vocabulary table name from step 1 (e.g., `deriva://vocabulary/Diagnosis_Type`) |
| 3 | `create_execution(...)` | `workflow_name="Expert Diagnosis Annotation"`, `workflow_type="Annotation"`, `description="Diagnosis labeling - 500 images"` |
| 4 | `start_execution()` | -- |
| 5 | `add_feature_value(...)` or `add_feature_value_record(...)` | `table_name="Image"`, `feature_name="Diagnosis"`, `entries=[...]` (batch all 500) |
| 6 | `stop_execution()` | -- |

Steps 1 and 2 are the inspection steps that answer your question. Steps 3-6 are the actual labeling workflow you would follow once you know the column structure and valid values.

## Key Points

- **Always inspect before adding values.** The `deriva://feature/Image/Diagnosis` resource tells you exactly what columns exist, which are required, and what vocabulary each term column draws from.
- **Check the vocabulary for valid term names.** The `deriva://vocabulary/{vocab_table}` resource lists all valid values. Using an invalid term name will produce an error.
- **Batch your entries.** Both `add_feature_value` and `add_feature_value_record` accept lists -- submit all 500 entries in one call rather than one at a time.
- **One execution per logical task.** All 500 labels from one annotation session belong in one execution. Do not create a new execution per label.
