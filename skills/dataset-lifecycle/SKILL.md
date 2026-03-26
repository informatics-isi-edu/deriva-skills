---
name: dataset-lifecycle
description: "Use this skill for ALL DerivaML dataset operations — creating, populating, splitting, versioning, browsing, and downloading datasets. Covers: creating datasets and adding members, train/test/validation splits (stratified, labeled, dry run), dataset version management after catalog changes, choosing and designing dataset types (orthogonal tagging), exploring and browsing dataset contents by element type using preview_denormalized_dataset, navigating parent/child hierarchies, downloading BDBags (timeouts, exclude_tables, bag_info), restructuring assets for ML frameworks, and referencing datasets in experiment configs via DatasetSpecConfig. Also covers preparing datasets specifically for model training — stratified splits by label distribution, setting up training/validation/testing partitions, and creating explicit split datasets in the catalog rather than computing on the fly. Triggers on: 'create a dataset', 'split dataset', 'stratify', 'train test split', 'prepare data for model', 'dataset version', 'what is in this dataset', 'browse dataset', 'wide table', 'flat table', 'denormalize', 'dataset types', 'element types', 'BDBag download', 'DatasetSpecConfig', 'add members', 'list members', 'dataset children', 'training data setup', 'curated subset', 'filter dataset', 'subset by class', 'select by value', 'create labeled dataset', 'filter by feature', 'subset with labels', 'has feature', 'images with labels', 'records that have', 'build dataset from'. Do NOT use for: creating features/labels (use create-feature), creating tables (use create-table), running experiments (use execution-lifecycle), uploading assets (use work-with-assets), or managing vocabularies (use manage-vocabulary)."
---

# Dataset Lifecycle

This skill covers the full lifecycle of a DerivaML dataset: assessing whether one is needed, planning its structure and types, creating and populating it, versioning for reproducibility, and consuming it in experiments.

## Prerequisite: Connect to a Catalog

All dataset operations require an active catalog connection. Before anything else, ensure you are connected:

```
connect_catalog(hostname="...", catalog_id="...")
```

If you don't know the catalog ID, read `deriva://registry/{hostname}` to see available catalogs and aliases. If you're already connected (check `deriva://catalog/connections`), skip this step.

## Phase 1: Assess

Before creating a dataset, determine whether an existing one can be reused, extended, or split.

1. **Search existing datasets.** Use `rag_search("your purpose", doc_type="catalog-data")` to find datasets by description, type, or purpose. Fall back to `deriva://catalog/datasets` for the full structured list. Use `preview_table(table_name="Image")` to understand how much data is available.
2. **Check available element types.** Read `deriva://catalog/dataset-element-types` to see which tables can contribute members. Read `deriva://catalog/element-type-paths` to understand FK traversal paths for bag exports. If the table you need isn't registered, call `add_dataset_element_type`.
3. **Decide: reuse, extend, or create.**

| Situation | Action |
|-----------|--------|
| Existing dataset covers your need | Reuse it — reference its RID + version in config |
| Existing dataset needs more members | `add_dataset_members` to extend it |
| Need a different split of existing data | `split_dataset` from the existing dataset |
| Need a focused subset for an experiment | Create a new dataset with selected member RIDs |
| Building from scratch | Create a new dataset |

## Phase 2: Plan

### Choose the dataset structure

| Pattern | When to use | How |
|---------|-------------|-----|
| Standalone | Building a new collection from scratch | `create_dataset` |
| Split children | Need train/test/val partitions | `split_dataset` from a parent |
| Curated subset | Focused set filtered by data values | Preview shape → generate script from template → run |
| Manual nesting | Grouping related datasets together | `create_dataset` + `add_dataset_child` |

### Choose dataset types

Types describe independent dimensions of a dataset — they are orthogonal tags, not a hierarchy. A dataset gets one or more tags from each relevant dimension.

**Built-in dimensions:**

| Dimension | Types | Mutually exclusive? |
|-----------|-------|:-------------------:|
| Partition role | `Training`, `Testing`, `Validation`, `Complete`, `Split` | Mostly yes |
| Annotation status | `Labeled`, `Unlabeled` | Yes |

**Guidelines:**
- Apply at least one type — untyped datasets are hard to discover
- Apply types from each relevant dimension — if the data has ground truth labels, add `Labeled`
- Types compose freely across dimensions — `Training` + `Labeled` + `Fundus` is three independent tags
- Don't compound dimensions — use `Training` + `Labeled`, never `TrainingLabeled`
- Check existing types first — use `rag_search("dataset types", doc_type="catalog-schema")` or read `deriva://catalog/dataset-types` for the full list

For detailed naming conventions, facet design, anti-patterns, and the substitution test, see `references/type-naming-strategy.md`.

For creating custom types, see `references/workflow.md` under "Managing Types."

## Phase 3: Create

**Default: use the script-based workflow** for any dataset creation that adds more than a handful of members. This ensures code provenance — every execution record links to a committed git hash. The MCP tool path is only for trivial cases (creating an empty dataset, adding 2-3 members manually).

### Choosing the right script path

There are two script-based approaches. Choose based on whether a source dataset already exists:

| Situation | Path | Template |
|-----------|------|----------|
| **No source dataset** — creating the first dataset from raw table data (bootstrap) | **Phase 3a: Bootstrap** | `catalog-operations-workflow` script patterns |
| **Source dataset exists** — filtering, subsetting, or selecting from an existing dataset | **Phase 3b: Curated Subsets** | `generate_subset_template.py` with filter registry |

The subset template (Phase 3b) requires downloading a bag from a source dataset. If no dataset exists yet (bootstrap case), use the standalone script pattern from Phase 3a instead.

### Phase 3a: Bootstrap dataset (no source dataset)

Use this when creating the **first dataset** from records already in the catalog — e.g., "create a dataset with all file records" or "create a dataset from all Image records." There is no existing dataset to filter from.

**Use the script patterns from the `catalog-operations-workflow` skill** (`references/script-patterns.md`), specifically the **Base Script Template** + **Dataset Creation** pattern.

1. **Register element types** (via MCP — idempotent, one-time setup):
   ```
   add_dataset_element_type(table_name="Image")
   ```

2. **Generate a standalone script** in `src/scripts/` following the Base Script Template:
   - Accept `--hostname`, `--catalog-id`, and `--dry-run` as CLI arguments
   - Connect via `DerivaML(hostname=..., catalog_id=...)`
   - Query all RIDs from the target table using `ml.pathBuilder.schemas[schema].tables[table].entities()`
   - Create a workflow and execution for provenance
   - Create the dataset with `execution.create_dataset()`
   - Add all RIDs with `dataset.add_dataset_members()`
   - **Do NOT add a CLI entry point** in `pyproject.toml`. These are one-time catalog operations, not reusable tools. Run with `uv run python src/scripts/<script>.py`.

3. **Test with `--dry-run`**, commit, then run for real.

4. **Split** (optional — use `dry_run=true` to preview first):
   ```
   split_dataset(source_dataset_rid="...", test_size=0.2, seed=42, dry_run=true)
   ```

### MCP tool path (trivial cases only)

For creating an empty dataset or adding a small number of known RIDs:

1. **Start an execution** for provenance tracking:
   ```
   create_execution(workflow_name="Dataset Curation", workflow_type="Data Management")
   start_execution()
   ```

2. **Create the dataset** with types and a good description:
   ```
   create_dataset(description="...", dataset_types=["Complete", "Labeled"])
   ```

3. **Add members and finalize:**
   ```
   add_dataset_members(dataset_rid="...", member_rids=["2-IMG1", "2-IMG2"])
   stop_execution()
   ```

For complete MCP tool parameters and Python API examples, see `references/workflow.md`.

### Description guidance

Every dataset needs a description that explains its composition, purpose, and key characteristics.

**Good:** "500 CIFAR-10 images (50 per class), balanced across all 10 categories, for rapid iteration during development"

**Bad:** "Training data" or "My dataset" or empty

For split datasets, note the split strategy and rationale.

### Why render splits explicitly in the catalog

**Always create explicit split datasets** (Training, Validation, Testing) and store them as children of the source dataset in the catalog. Don't compute splits on the fly each time you run an experiment.

| Approach | Problem |
|----------|---------|
| Split on the fly each run | Different random seeds → different splits → non-reproducible results. No record of which images were in which split |
| Explicit split datasets in catalog | Fixed, versioned, shareable. Every experiment references the same split by RID + version. Results are reproducible across team members |

The recommended pattern:
1. Create the source dataset with all data
2. `split_dataset` to create explicit Training/Validation/Testing children
3. Reference the split datasets by RID + version in experiment configs (`DatasetSpecConfig`)
4. All team members use the same splits — results are comparable

This is especially important for stratified splits — recomputing a stratified split each time may produce different partitions if the underlying data changes.

## Phase 3b: Curated Subsets (source dataset exists)

When the user wants a dataset filtered by data values from an **existing dataset** (e.g., "only labeled images", "just cats and dogs", "images with confidence > 0.8"), follow this workflow. This requires a source dataset to download a bag from — if no dataset exists yet, use **Phase 3a: Bootstrap** instead.

Curated subsets run through `deriva-ml-run` using the `script_config` hydra group, giving them the same provenance tracking as model training.

### Scaffolding check

Before generating anything, verify the project has the required infrastructure. If any piece is missing, create it — this handles both first-time setup and subsequent subset scripts.

1. **Filter registry** — Check if `src/models/subset_filters.py` exists. If not, copy it from this skill's `scripts/subset_filters.py`. This provides built-in filters: `has_feature`, `feature_equals`, `feature_in`, `numeric_range`.

2. **Config file** — Check if `src/configs/dataset_generation.py` exists. If not, create it with `script_store = store(group="script_config")` and an import for the generation function being created.

3. **Workflow config** — Check if `DatasetGenerationWorkflow` exists in `src/configs/workflow.py`. If not, add it with `workflow_type="Dataset_Generation"` and register as `name="dataset_generation"`.

4. **Base config** — Check if `script_config` appears in the hydra_defaults list in `src/configs/base.py`. If not, add `{"optional script_config": "none"}` to the defaults.

5. **Workflow types** — Check if `Dataset_Generation` and `Skill_Generated` exist in the catalog's Workflow_Type vocabulary. If not, create them via `add_workflow_type` MCP tool.

### Subset workflow

**Step 1: Preview the data shape.** Use `preview_denormalized_dataset` with `limit=10` to understand the columns, table joins, and value distributions. This is a small sample only — results are not cached or downloaded. Use it to understand what you're working with, not to extract the full data.

**Step 2: Discuss criteria with the user.** Based on the preview, confirm what filter they want. Common patterns:
- "Give me all labeled images" → `has_feature` on the label column
- "Only cat images" → `feature_equals` with column + value
- "Cats and dogs" → `feature_in` with column + value list
- "High confidence predictions" → `numeric_range` on confidence column
- Something complex → generate a custom filter function and register it

**Step 3: Generate the model function.** Read `scripts/generate_subset_template.py` and fill in the placeholders (`{{FUNCTION_NAME}}`, `{{EXPERIMENT_NAME}}`). Write to `src/models/generate_<name>.py`. If the user needs a custom filter not in the built-in registry, write the filter function in the same file and register it with `@register_filter("custom_name")`.

**Step 4: Generate config + experiment.** Add a named config to `src/configs/dataset_generation.py` using `builds(generate_function, ...)` with the filter name, params, source dataset RIDs, include_tables, and output metadata. Add an experiment entry to `src/configs/experiments.py` wiring together the connection, script_config, workflow, and datasets.

**Step 5: Dry run.** Run `uv run deriva-ml-run +experiment=<name> dry_run=true`. Show the user the output (selected count, filter description) and wait for approval.

**Step 6: Commit.** The script creates a new data element in the catalog, so it must be committed before running for real. The execution record captures the git hash — uncommitted code means no code provenance link.

**Step 7: Run for real.** After approval: `uv run deriva-ml-run +experiment=<name>`

**Step 8: Log the decision.** Use the `maintain-experiment-notes` skill to record what was created, the filter criteria, why those criteria were chosen, and the resulting dataset RID.

### How this relates to split_dataset

Splitting and curated subsets are both "given a source dataset, produce child datasets" — but they differ:
- **split_dataset** partitions ALL members into non-overlapping train/test/val sets
- **Curated subsets** SELECT members by data values — some members may be excluded entirely

Both produce datasets with full provenance tracking. Bags downloaded with `materialize=False` are cached by checksum, so multiple subset scripts from the same source don't re-download data.

### Caching feature values with `cache_features()`

When filtering by a single feature (e.g., "images with label X"), downloading a full bag just to read labels is overkill. The subset template supports a **catalog-query path** that uses `cache_features()` to fetch feature values directly from the catalog into SQLite-backed working data:

```python
from deriva_ml.feature import FeatureRecord

feature_df = ml.cache_features(
    "Image",                           # element table
    "Image_Classification",            # feature name
    selector=FeatureRecord.select_newest,
)
```

**When to use each path:**

| Situation | Path | Set `feature_name` in config? |
|-----------|------|:-----------------------------:|
| Filtering by a single feature column | Catalog-query | Yes |
| Need columns from multiple joined tables | Bag | No |
| Iterating on filter criteria interactively | Catalog-query | Yes |

**Caching behavior:**
- The first call to `cache_features()` fetches from the catalog and stores locally. Subsequent calls within the same script return the cached data instantly.
- The cache persists across multiple filter iterations, making it efficient to experiment with different filter thresholds or value lists without re-querying.
- Use `force=True` if feature values may have changed since the last cache (e.g., new labels were added between runs).
- **Cache key limitation:** The cache key is `features_{table}_{feature}` and does NOT include the selector. Always use the same selector for a given table/feature pair within a session. Use `force=True` if you need to switch selectors.

## Phase 4: Version

Versioning is essential for reproducible experiments. Every version is a frozen snapshot of the catalog state at the time it was created.

### Rules

1. **Always use explicit versions for real experiments.** `DatasetSpecConfig(rid="28EA", version="0.4.0")` — never omit the version or use "current" except for debugging.
2. **Increment after catalog changes.** Adding features, fixing labels, adding assets — none of these are visible in existing versions until you call `increment_dataset_version`.
3. **Always provide a version description.** Explain what changed, why, and the impact.
4. **Update configs immediately, commit before running.** The git hash in the execution record must match the config state.

### Semantic versioning

| Component | When | Examples |
|-----------|------|----------|
| **Major** | Breaking/schema changes | Columns added/removed, restructured tables |
| **Minor** | New data or features | Members added, new annotations, split created |
| **Patch** | Bug fixes, corrections | Fixed mislabeled records, metadata typos |

### Pre-experiment checklist

- [ ] Version explicitly specified (not "current")
- [ ] Config updated with correct version
- [ ] Config committed to git

For the full versioning rules, common mistakes, and version history API, see `references/concepts.md` under "Dataset Versioning."

## Phase 5: Use

Once a dataset is created and versioned, there are several ways to consume it.

### Browse in Chaise

Every dataset has a page in the Chaise web UI. Generate a shareable URL:
```
cite(rid="1-ABC4")              # permanent snapshot URL
cite(rid="1-ABC4", current=true) # live URL
```

### Reference in experiment configs

The standard way to use a dataset in an ML experiment is through `DatasetSpecConfig` in a Hydra-zen config:

```python
DatasetSpecConfig(rid="28EA", version="0.4.0")
```

Use the `get_dataset_spec` MCP tool to generate the correct string. See the `configure-experiment` and `write-hydra-config` skills for how dataset configs integrate into experiment configurations.

### Explore and browse contents

Understand what's in a dataset using MCP tools (no browser needed):

**Step 1: Get the overview** — types, version, description, member counts:
```
Read resource: deriva://dataset/{rid}
```

**Step 2: See what's inside** — members are returned grouped by element type (table). This tells you which tables have data in this dataset:
```
resource deriva://dataset/{rid}/members (dataset_rid="...", version="1.0.0")
```

**Step 3: Preview columns** — before fetching data, use `limit=1` to see what columns the wide table would have. This is fast (no data fetched) and helps verify the FK paths are correct:
```
preview_denormalized_dataset(dataset_rid="...", include_tables=["Image", "Subject"], limit=1)
```
Returns column names and types without any data. Use this to debug FK path errors or find the right column name for stratification.

**Step 4: Browse actual data** — denormalize to see real values. Include related tables to see joined data (e.g., an Image's Subject metadata, or feature annotations):
```
# See Image data joined with Subject metadata
preview_denormalized_dataset(dataset_rid="...", include_tables=["Image", "Subject"], limit=10)

# See Images with their classification labels
preview_denormalized_dataset(dataset_rid="...", include_tables=["Image", "Image_Classification"], limit=10)
```

**Important:** `preview_denormalized_dataset` is a preview only — results are not cached or stored. It returns a small sample (max 100 rows) to help you understand the data shape, column names, and relationships. Do NOT attempt to use `list_cached_results` or `query_cached_result` on preview results — they are not cached.

Once you understand the shape and decide on your filter criteria, use the DerivaML Python API to access the full dataset for building subsets or ML pipelines.

**Step 4: Check features and labels** — see what annotations exist on member records:
```
resource deriva://table/{name}/features (table_name="Image")
```

**Step 5: Navigate the hierarchy** — check for children (splits) and parents:
```
# Resource: deriva://dataset/{rid} (dataset_rid="...")
list_dataset_parents(dataset_rid="...")
resource deriva://dataset/{rid}/members (dataset_rid="...", recurse=true)  # members across full tree
```

**Step 6: Check provenance and validate:**
```
# Resource: deriva://dataset/{rid} (dataset_rid="...")                 # which executions used this
# Python API: bag inspection (dataset_rid="...", version="1.0.0")  # verify bag integrity
```

For individual records, use `get_record(table_name="Image", rid="2-IMG1")`.

Alternatively, browse in the Chaise web UI — use `cite(rid="...")` to generate a URL.

### Download as BDBag

For production pipelines and reproducible experiments:

```
estimate_bag_size(dataset_rid="...", version="1.0.0")  # preview first
# Python API: dataset.download_dataset_bag(dataset_rid="...", version="1.0.0")
```

For slow downloads, increase the timeout or exclude tables:
```
# Python API: dataset.download_dataset_bag(dataset_rid="...", version="1.0.0", timeout=[10, 1800])
# Python API: dataset.download_dataset_bag(dataset_rid="...", version="1.0.0", exclude_tables=["Study"])
```

### Restructure for ML frameworks

After downloading, organize files for PyTorch ImageFolder or similar:
```
restructure_assets(dataset_rid="...", asset_table="Image",
                   output_dir="./ml_data", group_by=["Diagnosis"])
```

## Reference Resources

- `scripts/subset_filters.py` — Filter registry with built-in filters (has_feature, feature_equals, feature_in, numeric_range). Copy to user's `src/models/` on first use.
- `scripts/generate_subset_template.py` — Template for generation model functions. Fill in placeholders per use case.
- `references/concepts.md` — Full background: what datasets are, types, element types, versioning, navigation, consumption, bag downloads
- `references/workflow.md` — Step-by-step MCP and Python API examples for every operation
- `references/bags.md` — BDBag contents, FK traversal, materialization, caching, timeouts
- `references/type-naming-strategy.md` — Orthogonal tagging principles, naming conventions, anti-patterns
- `rag_search("...", doc_type="catalog-data")` — Discover datasets by description, type, or purpose
- `deriva://catalog/datasets` — Full structured list of all datasets (fallback)
- `rag_search("...", doc_type="catalog-schema")` — Find dataset types by meaning
- `deriva://catalog/dataset-types` — Full list of dataset type vocabulary terms (fallback)
- `deriva://dataset/{rid}` — Dataset details including current version
- `deriva://catalog/dataset-element-types` — Registered element types
- `deriva://catalog/element-type-paths` — FK traversal paths for bag exports
- `deriva://catalog/connections` — Check active catalog connection
- `deriva://docs/datasets` — Full user guide to datasets in DerivaML

## Related Skills

- **`ml-data-engineering`** — Restructuring assets for PyTorch/TensorFlow, building training DataFrames, DatasetBag API, value selectors
- **`debug-bag-contents`** — Diagnosing missing data, FK traversal issues, and export problems in dataset bags
- **`create-feature`** — Creating features and adding labels/annotations to records in datasets
- **`configure-experiment`** — Setting up Hydra-zen configs that reference datasets
- **`execution-lifecycle`** — Running experiments that consume datasets with provenance tracking
- **`catalog-operations-workflow`** — Writing Python scripts for batch dataset operations with code provenance
