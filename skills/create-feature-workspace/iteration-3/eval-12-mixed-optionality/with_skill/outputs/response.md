# Adding Values with Mixed Required/Optional Columns

(Reconstructed from agent summary — agent couldn't write due to permissions)

## Approach

Uses `add_feature_value_record` (not `add_feature_value`) for multi-column features. Optional metadata columns like `confidence` can be included or omitted per entry.

## Sequence

1. Read `deriva://feature/Image/Diagnosis` to confirm column requirements
2. Read `deriva://vocabulary/{vocab_table}` to check valid terms
3. `create_execution` + `start_execution`
4. `add_feature_value_record` with mixed entries:

```
add_feature_value_record(table_name="Image", feature_name="Diagnosis", entries=[
    {"target_rid": "2-IMG1", "Diagnosis_Type": "Normal", "confidence": 0.95},
    {"target_rid": "2-IMG2", "Diagnosis_Type": "Abnormal"},
    {"target_rid": "2-IMG3", "Diagnosis_Type": "Normal", "confidence": 0.88},
    {"target_rid": "2-IMG4", "Diagnosis_Type": "Normal"},
])
```

5. `stop_execution()`

## Key Points

- Required columns (Diagnosis_Type) must be in every entry
- Optional columns (confidence) can be included or omitted per entry
- Uses `add_feature_value_record` because multiple columns are involved
