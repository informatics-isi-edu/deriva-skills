---
name: create-feature
description: "ALWAYS use this skill when creating features, adding labels or annotations to records, setting up classification categories, querying or exploring feature values, or working with feature values in DerivaML. Covers: deciding whether a feature is needed vs a column, discovering existing features, designing single vs multi-column features, creating vocabularies and features, adding feature values with provenance, querying and browsing feature values (preview via MCP for shape, full retrieval via Python API for analysis), selecting among multiple annotations (newest, by workflow, custom selectors), caching feature values for reuse, and understanding how features integrate with datasets. Triggers on: 'create feature', 'add labels', 'annotate images', 'classification', 'ground truth', 'confidence score', 'feature values', 'what features exist', 'explore annotations', 'show feature values', 'query features', 'what are the labels', 'list annotations', 'browse features', 'feature preview'."
disable-model-invocation: false
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

**Start with `rag_search`** to discover features by concept, not just name:
```
rag_search("diagnosis label classification", doc_type="catalog-schema")
rag_search("quality score confidence", doc_type="catalog-schema")
```

Then use resources for full structured details of a specific feature:
```
Read resource: deriva://catalog/features               # All features (structured JSON)
Read resource: deriva://feature/{table_name}/{feature_name}  # Specific feature details
Read resource: deriva://table/{table_name}/feature-values/newest  # Existing values
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

### Step 3: Choose the right approach — script or MCP tools

Feature values modify catalog data, so the approach depends on scale and reproducibility needs:

| Situation | Approach |
|-----------|----------|
| Verifying a new feature works (1-5 test values) | MCP tools directly — quick and disposable |
| Production annotations, batch labels, model predictions | Committed script — provides code provenance in the execution record |

**For production data, always write a script first.** The execution record captures the git hash of the committed code. Without a committed script, the execution has provenance (who, when, what) but no code link (how). Use the `catalog-operations-workflow` skill or `dataset-lifecycle` skill's script templates to generate the script, commit it, then run via `deriva-ml-run`.

**For quick testing** (verifying the feature works, adding a few sample values), MCP tools are fine:

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
- **Boolean values**: Pass as strings (`"true"`, `"false"`) — the MCP tools expect string values even for boolean columns

### Common mistakes

| Mistake | What happens | Fix |
|---------|-------------|-----|
| Adding values without an execution | Error — provenance required | `create_execution` + `start_execution` first |
| Using MCP tools for production batch annotations | Works but no code provenance | Write and commit a script, run via `deriva-ml-run` |
| Using wrong term name | Error — must match vocabulary exactly | Read `deriva://vocabulary/{vocab}` to check valid terms |
| Missing required column | Error — required fields must be present | Read `deriva://feature/{table}/{feature}` for required fields |
| One execution per label | Works but clutters provenance | Batch labels from same source into one execution |
| Passing boolean as true/false literal | Pydantic validation error | Pass as string: `"true"` / `"false"` |
| Forgetting `stop_execution()` | Execution stays "running" | Always stop after adding values |

For the complete MCP tool parameters and Python API examples, see `references/workflow.md`.

## Phase 5: Query and Explore Feature Values

Feature queries fall into two categories. **Always choose the right one — never use preview tools to retrieve feature values.**

### Rule: "get values" = Python API, "explore shape" = preview

- **User asks to get, retrieve, list, or show feature values** → ALWAYS use the Python API via a script. Even for small numbers of values. Results stay out of context and are cached for reuse.
- **User asks exploratory questions** ("what features exist?", "what does this feature look like?", "what columns does it have?") → Preview tools are fine for a small sample.

**NEVER use `preview_table` with large limits to retrieve feature values.** This dumps raw records into the conversation context, which is wasteful and doesn't support selectors or caching.

### Exploratory preview (MCP tools — understanding shape, not retrieving data)

Use MCP tools only for speculative, exploratory questions — understanding what a feature looks like, checking column types, spot-checking a handful of values:

```
# Spot-check: what do a few values look like? (keep limit small)
preview_table(table_name="Execution_Image_Scouts_Pick", limit=5)

# What features are joined with this data?
preview_denormalized_dataset(dataset_rid="...", include_tables=["Image", "Image_Classification"], limit=5)
```

**To discover the feature table name**, use RAG search — don't guess from naming conventions:
```
rag_search("Scouts_Pick feature", doc_type="catalog-schema")
```

MCP resources also provide structured feature metadata:
```
Read resource: deriva://catalog/features               # All features overview
Read resource: deriva://feature/{table}/{feature}      # Specific feature structure
```

### Full retrieval (DerivaML Python API — always for actual values)

When the user asks for feature values, use the Python API in a script. This applies regardless of how many values exist — the pattern is the same for 10 values or 10 million. Run a script, print a summary, cache the results.

**Step 1: Before retrieving, check provenance and ask the user which values they want.**

Multiple executions may have contributed values (different annotators, model runs, corrections). The user needs to choose a selection strategy before retrieval:

```python
# Quick check: how many executions contributed?
all_values = list(ml.list_feature_values("Image", "Scouts_Pick"))
executions = set(r.Execution for r in all_values)
print(f"Total values: {len(all_values)}, from {len(executions)} execution(s): {executions}")
```

If there is more than one execution, **ask the user** which values they want:

| Option | When to use |
|--------|-------------|
| All values (no dedup) | User wants the complete picture, including duplicates |
| Newest per record | Default for most analysis — latest annotation wins |
| From a specific execution | User knows which run they trust |
| From a specific workflow type | e.g., only "Annotation" not "Prediction" |

Only proceed to full retrieval after the user confirms their selection strategy.

**Step 2: Retrieve with the chosen selector and cache the results.**

```python
from deriva_ml.feature import FeatureRecord

# Get all values for a feature — returns typed Pydantic models
features = ml.fetch_table_features("Image", feature_name="Diagnosis")
diagnosis_records = features["Diagnosis"]

# Deduplicate to newest value per record
features = ml.fetch_table_features(
    "Image", feature_name="Diagnosis",
    selector=FeatureRecord.select_newest,
)

# Convert to DataFrame for analysis
import pandas as pd
df = pd.DataFrame([r.model_dump() for r in diagnosis_records])
```

**When to use full retrieval:**
- Feature table has more than ~50 values
- You need to filter, aggregate, or join values
- Results feed into dataset creation or model training
- You need selector logic (newest, by workflow, custom)

**Caching:** When feature values will be reused (e.g., for dataset subsetting, repeated analysis), cache the DataFrame in the script rather than re-querying the catalog each time.

### Resolve multiple values with selectors

When a record has values from multiple annotators or model runs, use selectors to pick one:

| I want... | Selector |
|-----------|----------|
| Latest value regardless of source | `FeatureRecord.select_newest` |
| Values from a specific workflow type | `ml.select_by_workflow(records, "Training")` |
| Values from a specific workflow by RID | `ml.select_by_workflow(records, "2-ABC1")` |
| Custom logic (highest confidence, etc.) | Write a custom selector function |

```python
from deriva_ml.feature import FeatureRecord

# Built-in: newest per record
features = ml.fetch_table_features("Image", feature_name="Diagnosis",
                                    selector=FeatureRecord.select_newest)

# By workflow type
from collections import defaultdict
all_values = list(ml.list_feature_values("Image", "Diagnosis"))
by_image = defaultdict(list)
for v in all_values:
    by_image[v.Image].append(v)
selected = {rid: ml.select_by_workflow(recs, "Annotation") for rid, recs in by_image.items()}
```

### Custom selection logic

When built-in selectors don't fit, write a custom function:

```python
from deriva_ml.feature import FeatureRecord

def select_highest_confidence(records: list[FeatureRecord]) -> FeatureRecord:
    return max(records, key=lambda r: getattr(r, "Confidence", 0))

features = ml.fetch_table_features("Image", feature_name="Diagnosis",
                                    selector=select_highest_confidence)

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
