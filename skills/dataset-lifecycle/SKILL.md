---
name: dataset-lifecycle
description: "Use this skill for ALL DerivaML dataset operations — creating, populating, splitting, versioning, browsing, and downloading datasets. Covers: creating datasets and adding members, train/test/validation splits (stratified, labeled, dry run), dataset version management after catalog changes, choosing and designing dataset types (orthogonal tagging), exploring and browsing dataset contents by element type using preview_denormalized_dataset, navigating parent/child hierarchies, downloading BDBags (timeouts, exclude_tables, bag_info), restructuring assets for ML frameworks, and referencing datasets in experiment configs via DatasetSpecConfig. Also covers preparing datasets specifically for model training — stratified splits by label distribution, setting up training/validation/testing partitions, and creating explicit split datasets in the catalog rather than computing on the fly. Triggers on: 'create a dataset', 'split dataset', 'stratify', 'train test split', 'prepare data for model', 'dataset version', 'what is in this dataset', 'browse dataset', 'wide table', 'flat table', 'denormalize', 'dataset types', 'element types', 'BDBag download', 'DatasetSpecConfig', 'add members', 'list members', 'dataset children', 'training data setup'. Do NOT use for: creating features/labels (use create-feature), creating tables (use create-table), running experiments (use execution-lifecycle), uploading assets (use work-with-assets), or managing vocabularies (use manage-vocabulary)."
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
| Curated subset | Focused set for a specific experiment | `create_dataset` + `add_dataset_members` with selected RIDs |
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
- Check existing types first — read `deriva://catalog/dataset-types`

For detailed naming conventions, facet design, anti-patterns, and the substitution test, see `references/type-naming-strategy.md`.

For creating custom types, see `references/workflow.md` under "Managing Types."

## Phase 3: Create

The standard sequence:

1. **Start an execution** for provenance tracking:
   ```
   create_execution(workflow_name="Dataset Curation", workflow_type="Data Management")
   start_execution()
   ```

2. **Register element types** (catalog-level, idempotent):
   ```
   add_dataset_element_type(table_name="Image")
   ```

3. **Create the dataset** with types and a good description:
   ```
   create_dataset(description="...", dataset_types=["Complete", "Labeled"])
   ```

4. **Validate and add members:**
   ```
   validate_rids(dataset_rids=["2-IMG1", "2-IMG2"])
   add_dataset_members(dataset_rid="...", member_rids=["2-IMG1", "2-IMG2"])
   ```

5. **Split** (optional — use `dry_run=true` to preview first):
   ```
   split_dataset(source_dataset_rid="...", test_size=0.2, seed=42, dry_run=true)
   ```

6. **Finalize:**
   ```
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

- `references/concepts.md` — Full background: what datasets are, types, element types, versioning, navigation, consumption, bag downloads
- `references/workflow.md` — Step-by-step MCP and Python API examples for every operation
- `references/bags.md` — BDBag contents, FK traversal, materialization, caching, timeouts
- `references/type-naming-strategy.md` — Orthogonal tagging principles, naming conventions, anti-patterns
- `deriva://catalog/datasets` — Browse existing datasets
- `deriva://catalog/dataset-types` — Available dataset type vocabulary terms
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
