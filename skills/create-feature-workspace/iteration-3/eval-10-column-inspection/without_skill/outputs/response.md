# How to Inspect a Feature's Structure Before Adding Labels

To figure out what values you can use and what columns are required for your Diagnosis feature on the Image table, follow this sequence of MCP tool calls:

## Step 1: Look Up the Feature Definition

Use `lookup_feature` (via the `deriva://catalog/features` resource) or `fetch_table_features` to understand the feature's structure. The most direct approach is:

```
Tool: fetch_table_features
Parameters:
  table_name: "Image"
  feature_name: "Diagnosis"
```

This returns the feature's column structure, including which columns are term columns (controlled vocabulary values), asset columns (file references), and value columns (direct values like numbers or text). Each feature value record will show you the actual column names used.

## Step 2: Inspect the Feature's Vocabulary Terms

The response from `fetch_table_features` will show you the term column names (e.g., `Diagnosis_Type`). To see all valid values for each term column, query the corresponding vocabulary table:

```
Tool: query_table
Parameters:
  table_name: "Diagnosis_Type"
  columns: ["Name", "Description", "Synonyms"]
```

This lists every allowed term you can use as a value. The `Name` column contains the exact strings you should pass when adding feature values. The vocabulary table name corresponds to the term column name in the feature definition.

If you are unsure which vocabulary table backs a term column, you can also check the catalog schema resource for foreign key relationships on the feature's association table.

## Step 3: Verify Required vs. Optional Columns

To get a complete picture of the feature table's columns and which are required:

```
Tool: rag_search
Parameters:
  query: "Diagnosis feature Image table columns"
  include_schema: true
  include_data: false
```

This searches the indexed catalog schema and will return information about the feature's association table, including all columns, their types, and whether they allow nulls.

## Step 4: Add Feature Values

Once you know the valid values and required columns, you have two options depending on complexity:

### For simple features (single term column):

```
Tool: add_feature_value
Parameters:
  table_name: "Image"
  feature_name: "Diagnosis"
  entries: [
    {"target_rid": "1-ABC", "value": "Normal"},
    {"target_rid": "1-DEF", "value": "Abnormal"},
    ... (up to 500 entries)
  ]
```

The `value` field takes a term name from the vocabulary. The `target_rid` is the RID of each Image record.

### For complex features (multiple columns per record):

```
Tool: add_feature_value_record
Parameters:
  table_name: "Image"
  feature_name: "Diagnosis"
  entries: [
    {"target_rid": "1-ABC", "Diagnosis_Type": "Normal", "confidence": 0.95},
    {"target_rid": "1-DEF", "Diagnosis_Type": "Abnormal", "confidence": 0.87},
    ...
  ]
```

Each entry includes the `target_rid` plus all the feature columns by name. Term columns accept vocabulary term names (strings), asset columns accept asset RIDs, and value columns accept their native types (numbers, strings, booleans).

## Summary of Tool Call Sequence

| Step | Tool | Purpose |
|------|------|---------|
| 1 | `fetch_table_features("Image", feature_name="Diagnosis")` | See the feature structure, column names, and any existing values |
| 2 | `query_table("Diagnosis_Type")` | List all valid vocabulary terms for the term column |
| 3 | `add_feature_value` or `add_feature_value_record` | Add labels for your 500 images in batch |

The key insight is that `fetch_table_features` reveals the column names and types, and then `query_table` on the vocabulary table shows you the allowed values. With both pieces of information, you can construct your batch entries for `add_feature_value` or `add_feature_value_record`.
