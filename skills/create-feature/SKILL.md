---
name: create-feature
description: "ALWAYS use this skill when creating features, adding labels or annotations to records, setting up classification categories, or working with feature values in DerivaML. Covers: deciding whether a feature is needed vs a column, discovering existing features, designing single vs multi-column features, creating vocabularies and features, adding feature values with provenance, querying and selecting among multiple annotations, and understanding how features integrate with datasets. Triggers on: 'create feature', 'add labels', 'annotate images', 'classification', 'ground truth', 'confidence score', 'feature values', 'what features exist', 'explore annotations'."
disable-model-invocation: true
---

# Creating and Populating Features in DerivaML

Features link domain objects (e.g., Image, Subject) to structured values — controlled vocabulary terms, computed values, or assets — with full provenance tracking through executions.

## Prerequisite: Connect to a Catalog

All feature operations require an active catalog connection:

```
connect_catalog(hostname="...", catalog_id="...")
```

If already connected (check `deriva://catalog/connections`), skip this step.

## Phase 1: Assess

Before creating a feature, determine whether one is needed and whether it already exists.

### Is this a feature or a column?

Features have overhead (separate table, execution requirement, provenance). Use a feature when you need provenance, multivalued support, or controlled vocabulary terms. Use a column when the value is intrinsic to the record and immutable. See `references/concepts.md` under "When to Use a Feature vs a Column" for the full decision guide.

### Search existing features

```
# Browse all features — target tables, types, column schemas
Read resource: deriva://catalog/features

# Details for a specific feature
Read resource: deriva://feature/{table_name}/{feature_name}

# What feature values already exist on a table
Read resource: deriva://table/{table_name}/feature-values/newest
```

```python
features = ml.find_features("Image")
feature = ml.lookup_feature("Image", "Diagnosis")
```

**Before creating, ask:**
- Does a feature with this purpose already exist? The `semantic-awareness` skill checks automatically, and `create_feature` warns about near-duplicates.
- Can the existing feature be extended with new vocabulary terms?
- Is this really a feature, or should it be a column on the table?

## Phase 2: Design

### Choose the feature type

| Type | Parameter | Use case |
|------|-----------|----------|
| Term-based | `terms=["Vocab_Name"]` | Classification labels, categories |
| Asset-based | `assets=["Asset_Table"]` | Segmentation masks, annotation overlays |
| Mixed | both `terms` and `assets` | Labels with associated files |
| With metadata | `metadata=[...]` | Confidence scores, reviewer references |

### Single vs multi-column

- **One feature, multiple term columns** — when values are always assigned together in the same annotation act (e.g., diagnosis + severity in one clinical assessment)
- **Separate features** — when values are assigned independently by different processes (e.g., quality scored by QC, diagnosis by pathologist)

The test: if you always set them at the same time in the same execution, they belong together.

### Naming

- Use PascalCase with underscores: `Tumor_Classification`, `Image_Quality`
- Name the annotation act, not the vocabulary: `Diagnosis` (not `Diagnosis_Type`)
- Be specific: `Cell_Classification` (not just `Classification`)

For the full design guide, see `references/concepts.md` under "Designing a Feature."

## Phase 3: Create the Feature Definition

### Standard workflow

1. **Create vocabulary + terms** (if term-based; see `manage-vocabulary` skill):
   ```
   create_vocabulary(vocabulary_name="Diagnosis_Type", comment="...")
   add_term(vocabulary_name="Diagnosis_Type", term_name="Normal", description="...")
   ```

2. **Create the feature**:
   ```
   create_feature(table_name="Image", feature_name="Diagnosis",
                   terms=["Diagnosis_Type"], comment="Clinical diagnosis for this image")
   ```

### Description guidance

Every feature needs a description explaining what it measures, what values it takes, and its role:

**Good:** "Diagnostic classification of chest X-ray images. Values from the Diagnosis vocabulary (normal, pneumonia, COVID-19). Primary ground truth label for training classification models"

**Bad:** "Classification" or "Labels" or empty

Since features are multivalued, note whether it's intended for ground truth, model predictions, or computed metrics.

## Phase 4: Add Feature Values

Adding values requires knowing what columns a feature has, which are required, and what values are valid.

### Step 1: Inspect the feature structure

Before adding values, check what the feature expects:

```
# Read the feature definition — shows columns, types, required/optional, vocabularies
Read resource: deriva://feature/{table_name}/{feature_name}
```

The resource returns:
- **term_columns** — vocabulary-controlled fields with the vocabulary table name and whether required
- **asset_columns** — file reference fields with the asset table name
- **value_columns** — free-form fields with data type (float4, text, etc.)
- **required_fields** — list of all fields that must be provided

### Step 2: Determine valid values

For **term columns**, valid values are the terms in the referenced vocabulary:
```
# See what values are valid for a term column
Read resource: deriva://vocabulary/{vocabulary_table_name}
```

For **value columns**, check the type:
- `float4`/`float8` — numeric values
- `text` — any string
- `boolean` — true/false
- `int4`/`int8` — integer values

### Step 3: Add values within an execution

Feature values require provenance — every value is linked to the execution that created it:

```
create_execution(workflow_name="Expert Annotation", workflow_type="Annotation")
start_execution()
```

**Simple features** (single term or asset column) — use `add_feature_value`:
```
add_feature_value(table_name="Image", feature_name="Diagnosis",
                  entries=[{"target_rid": "2-IMG1", "value": "Normal"},
                           {"target_rid": "2-IMG2", "value": "Abnormal"}])
```

**Multi-column features** — use `add_feature_value_record` with explicit column names:
```
add_feature_value_record(table_name="Image", feature_name="Diagnosis",
                          entries=[{"target_rid": "2-IMG1",
                                    "Diagnosis_Type": "Normal",
                                    "confidence": 0.95},
                                   {"target_rid": "2-IMG2",
                                    "Diagnosis_Type": "Abnormal",
                                    "confidence": 0.87}])
```

```
stop_execution()
```

### Batch adding guidance

- **Batch size**: Both tools accept lists of entries — batch them rather than calling one at a time
- **One execution per logical task**: All labels from one annotator's session go in one execution. Don't create a new execution per label
- **Multiple annotators**: Each annotator gets their own execution (creates provenance trail)
- **Model predictions**: Each model run gets its own execution
- **Optional columns can be omitted**: Only required fields must be present in every entry. Optional fields can vary per entry

### Common mistakes

| Mistake | What happens | Fix |
|---------|-------------|-----|
| Adding values without an execution | Error — provenance required | `create_execution` + `start_execution` first |
| Using wrong term name | Error — must match vocabulary exactly | Read `deriva://vocabulary/{vocab}` to check valid terms |
| Missing required column | Error — required fields must be present | Read `deriva://feature/{table}/{feature}` for required fields |
| One execution per label | Works but clutters provenance | Batch labels from same source into one execution |
| Forgetting `stop_execution()` | Execution stays "running" | Always stop after adding values |

For the complete MCP tool parameters and Python API examples, see `references/workflow.md`.

## Phase 5: Query and Select

### Browse feature values

```
# All values with provenance
Read resource: deriva://feature/{table}/{feature}/values

# Deduplicated to newest per record
Read resource: deriva://table/{table}/feature-values/newest

# With selection/filtering
resource deriva://table/{name}/features (table_name="Image", feature_name="Diagnosis", selector="newest")
```

### Resolve multiple values

When a record has values from multiple annotators or model runs, use one of the built-in selectors:

| I want... | MCP parameter |
|-----------|---------------|
| Latest value regardless of source | `selector="newest"` |
| Earliest (original) annotation | `selector="first"` |
| Consensus label (majority vote) | `selector="majority_vote"` (requires `feature_name`) |
| Values from a specific workflow type | `workflow="Training"` |
| Values from a specific workflow by RID | `workflow="2-ABC1"` |
| Values from one specific execution | `execution="3-XYZ"` |

These are mutually exclusive — pick one.

Feature values are also available as pre-deduplicated MCP resources:

| Resource | Deduplication |
|----------|--------------|
| `deriva://table/{table}/feature-values/newest` | Most recent per record |
| `deriva://table/{table}/feature-values/first` | Earliest per record |
| `deriva://table/{table}/feature-values/majority_vote` | Consensus per record |

### Custom selection logic

When built-in selectors don't fit (highest confidence, specific annotator, etc.), write a Python script. All selectors now use a single type — `FeatureRecord` — everywhere (catalog queries, bag queries, and Python API `bag.restructure_assets()`).

```python
from deriva_ml.feature import FeatureRecord

# Custom selector: pick the value with highest confidence
def select_highest_confidence(records: list[FeatureRecord]) -> FeatureRecord:
    return max(records, key=lambda r: getattr(r, "Confidence", 0))

# Works with catalog queries
features = ml.resource deriva://table/{name}/features ("Image", selector=select_highest_confidence)

# Same selector works with bag restructuring
bag.restructure_assets(output_dir="./data", group_by=["Diagnosis"],
                       value_selector=select_highest_confidence)
```

See `references/concepts.md` under "Feature Selection" for the full Python API and common pitfalls.

## Integration with Datasets

Features are tightly coupled with datasets:

- **In dataset bags** — feature values for dataset members are automatically included in BDBag exports
- **In preview_denormalized_dataset** — include feature tables to see labels alongside data. Column names: `{FeatureTableName}_{ColumnName}`
- **Dataset versioning** — adding feature values does NOT update existing versions. Call `increment_dataset_version` after adding features to make them visible in new versions
- **In split_dataset** — the `stratify_by_column` parameter references feature columns in denormalized format

## Reference Resources

- `references/concepts.md` — Feature types, design guidance, naming, multivalued features, selection, Python API, integration
- `references/workflow.md` — Step-by-step MCP and Python API examples
- `references/feature-selectors.md` — Complete guide to writing and using feature selectors
- `deriva://docs/features` — Full user guide to features in DerivaML
- `deriva://catalog/features` — Browse all existing features (target tables, types, columns)
- `deriva://feature/{table_name}/{feature_name}` — Feature details and column schema
- `deriva://feature/{table_name}/{feature_name}/values` — Feature values with provenance
- `deriva://table/{table_name}/feature-values` — All feature values (raw, no dedup)
- `deriva://table/{table_name}/feature-values/newest` — Deduplicated to newest per record
- `deriva://table/{table_name}/feature-values/first` — Deduplicated to earliest per record
- `deriva://table/{table_name}/feature-values/majority_vote` — Deduplicated to consensus per record

## Related Skills

- **`manage-vocabulary`** — Create and manage the controlled vocabularies that features reference.
- **`dataset-lifecycle`** — Features annotate records in datasets. Feature values are included in bag exports and affect dataset versioning.
- **`ml-data-engineering`** — Consuming feature values for ML training — restructuring, DataFrames, value selectors.
