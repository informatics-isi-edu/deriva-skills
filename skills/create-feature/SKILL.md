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

## Phase 3: Create

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

3. **Add values within an execution** (provenance is required):
   ```
   create_execution(workflow_name="Expert Annotation", workflow_type="Annotation")
   start_execution()

   add_feature_value(table_name="Image", feature_name="Diagnosis",
                     entries=[{"target_rid": "2-IMG1", "value": "Normal"},
                              {"target_rid": "2-IMG2", "value": "Abnormal"}])

   stop_execution()
   ```

For features with multiple columns, use `add_feature_value_record` instead:
```
add_feature_value_record(table_name="Image", feature_name="Diagnosis",
                          entries=[{"target_rid": "2-IMG1",
                                    "Diagnosis_Type": "Normal",
                                    "confidence": 0.95}])
```

For the complete MCP tool parameters and Python API examples, see `references/workflow.md`.

### Description guidance

Every feature needs a description explaining what it measures, what values it takes, and its role:

**Good:** "Diagnostic classification of chest X-ray images. Values from the Diagnosis vocabulary (normal, pneumonia, COVID-19). Primary ground truth label for training classification models"

**Bad:** "Classification" or "Labels" or empty

Since features are multivalued, note whether it's intended for ground truth, model predictions, or computed metrics.

## Phase 4: Query and Select

### Browse feature values

```
# All values with provenance
Read resource: deriva://feature/{table}/{feature}/values

# Deduplicated to newest per record
Read resource: deriva://table/{table}/feature-values/newest

# With selection/filtering
fetch_table_features(table_name="Image", feature_name="Diagnosis", selector="newest")
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

When built-in selectors don't fit (highest confidence, specific annotator, etc.), write a Python script. All selectors now use a single type — `FeatureRecord` — everywhere (catalog queries, bag queries, and `restructure_assets`).

```python
from deriva_ml.feature import FeatureRecord

# Custom selector: pick the value with highest confidence
def select_highest_confidence(records: list[FeatureRecord]) -> FeatureRecord:
    return max(records, key=lambda r: getattr(r, "Confidence", 0))

# Works with catalog queries
features = ml.fetch_table_features("Image", selector=select_highest_confidence)

# Same selector works with bag restructuring
bag.restructure_assets(output_dir="./data", group_by=["Diagnosis"],
                       value_selector=select_highest_confidence)
```

See `references/concepts.md` under "Feature Selection" for the full Python API and common pitfalls.

## Integration with Datasets

Features are tightly coupled with datasets:

- **In dataset bags** — feature values for dataset members are automatically included in BDBag exports
- **In denormalize_dataset** — include feature tables to see labels alongside data. Column names: `{FeatureTableName}_{ColumnName}`
- **Dataset versioning** — adding feature values does NOT update existing versions. Call `increment_dataset_version` after adding features to make them visible in new versions
- **In split_dataset** — the `stratify_by_column` parameter references feature columns in denormalized format

## Reference Resources

- `references/concepts.md` — Feature types, design guidance, naming, multivalued features, selection, Python API, integration
- `references/workflow.md` — Step-by-step MCP and Python API examples
- `deriva://docs/features` — Full user guide to features in DerivaML
- `deriva://catalog/features` — Browse existing features
- `deriva://feature/{table_name}/{feature_name}` — Feature details and column schema
- `deriva://feature/{table_name}/{feature_name}/values` — Feature values with provenance
- `deriva://table/{table_name}/feature-values/newest` — Deduplicated to newest per record

## Related Skills

- **`manage-vocabulary`** — Create and manage the controlled vocabularies that features reference.
- **`dataset-lifecycle`** — Features annotate records in datasets. Feature values are included in bag exports and affect dataset versioning.
- **`prepare-training-data`** — Consuming feature values for ML training — restructuring, DataFrames, value selectors.
