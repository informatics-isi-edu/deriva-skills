# Feature Selector Unification

**Date:** 2026-03-18
**Status:** Draft
**Scope:** deriva-ml, deriva-mcp, deriva-skills

## Problem

Feature value selection is fragmented across three layers with two incompatible record types:

1. **`FeatureRecord`** (Pydantic model) — used by catalog API (`fetch_table_features`, `list_feature_values`) and bag API. Has `select_newest` and `select_by_execution` selectors.
2. **`FeatureValueRecord`** (dataclass) — used only inside `restructure_assets`. Has `select_majority_vote`, `select_latest`, `select_first` selectors.

The MCP tool `fetch_table_features` only exposes `selector="newest"`, `workflow`, and `execution`. It cannot express majority vote, first, or custom selectors.

Users who need non-trivial selection must drop down to Python scripts. The two record types have different attributes and selectors can't be used interchangeably.

## Design Principle

**Bags should behave as much like catalog connections as possible.** One record type, one set of selectors, consistent behavior across live catalog and downloaded bags.

## Design

### Layer 1: deriva-ml

#### Eliminate `FeatureValueRecord`

Remove `FeatureValueRecord` entirely. It's an internal implementation detail of `restructure_assets` that wraps a `FeatureRecord` with a pre-resolved `.value` field. The same information is available from `FeatureRecord` directly via typed attributes.

**Files:**
- `src/deriva_ml/dataset/dataset_bag.py` — delete class definition (lines 69-135), delete module-level selectors (lines 141-190)
- `src/deriva_ml/dataset/__init__.py` — remove `FeatureValueRecord`, `select_first`, `select_majority_vote` exports
- `src/deriva_ml/__init__.py` — remove lazy `FeatureValueRecord` import

#### Add selectors to `FeatureRecord`

Add three new static/class methods to `FeatureRecord` in `src/deriva_ml/feature.py`:

```python
@staticmethod
def select_first(records: list["FeatureRecord"]) -> "FeatureRecord":
    """Select the earliest feature record by creation time (lowest RCT)."""
    return min(records, key=lambda r: r.RCT or "")

@staticmethod
def select_latest(records: list["FeatureRecord"]) -> "FeatureRecord":
    """Alias for select_newest. Included for API symmetry."""
    return FeatureRecord.select_newest(records)

@classmethod
def select_majority_vote(cls, column: str | None = None):
    """Return a selector that picks the most common value for a column.

    If column is None, auto-detects the first term column from the
    feature's metadata (works for single-term features, the common case).
    For multi-term features, column must be specified.

    Ties are broken by most recent RCT.
    """
    def _selector(records: list["FeatureRecord"]) -> "FeatureRecord":
        # Determine the column to count
        col = column
        if col is None:
            # Auto-detect from feature metadata
            if cls.feature and cls.feature.term_columns:
                col = cls.feature.term_columns[0].name
            else:
                # Fallback: use Feature_Name as column hint
                raise DerivaMLException(
                    "select_majority_vote requires a column name for "
                    "features with multiple term columns"
                )

        from collections import Counter
        counts = Counter(getattr(r, col, None) for r in records)
        max_count = max(counts.values())
        majority_values = {v for v, c in counts.items() if c == max_count}
        candidates = [r for r in records if getattr(r, col, None) in majority_values]
        return max(candidates, key=lambda r: r.RCT or "")

    return _selector
```

**Design decision:** `select_majority_vote` is a factory (like `select_by_execution`) because it needs to know which column to count. For single-term features, it auto-detects from the feature's `term_columns`. For multi-term features, the caller must specify the column.

#### Update `restructure_assets`

Change the `value_selector` parameter type:

```python
# Before
value_selector: Callable[[list[FeatureValueRecord]], FeatureValueRecord] | None

# After
value_selector: Callable[[list[FeatureRecord]], FeatureRecord] | None
```

Update the internal `_load_features_cache` method to keep `FeatureRecord` objects instead of converting to `FeatureValueRecord`. The directory-naming code that currently reads `record.value` will instead read `getattr(record, column_name)` where `column_name` is the resolved column from `group_by`.

**Key change in the restructure flow:**

```python
# Before (lines 1385-1410): converts FeatureRecord → FeatureValueRecord
for fv in feature_values:
    fv_dict = fv.model_dump()
    record = FeatureValueRecord(target_rid=..., value=fv_dict[use_column], ...)
    records_cache[group_key][target_rid].append(record)

# After: keeps FeatureRecord directly, resolves value at directory-naming time
for fv in feature_values:
    target_rid = getattr(fv, table_name, None)
    records_cache[group_key][target_rid].append(fv)

# At directory-naming time:
value = getattr(selected_record, use_column, None) or "Unknown"
```

### Layer 2: MCP Tools

#### `fetch_table_features` — add selector names

Expand the `selector` string parameter to support all built-in selectors:

```python
async def fetch_table_features(
    table_name: str,
    feature_name: str | None = None,
    selector: str | None = None,      # "newest", "first", "latest", "majority_vote"
    workflow: str | None = None,
    execution: str | None = None,
) -> str:
```

Selector resolution:

```python
if selector == "newest":
    selector_fn = FeatureRecord.select_newest
elif selector == "first":
    selector_fn = FeatureRecord.select_first
elif selector == "latest":
    selector_fn = FeatureRecord.select_latest
elif selector == "majority_vote":
    # Auto-detect column from feature metadata
    if feature_name:
        feat = ml.lookup_feature(table_name, feature_name)
        RecordClass = feat.feature_record_class()
        selector_fn = RecordClass.select_majority_vote()
    else:
        return error("majority_vote requires feature_name")
```

Note: `majority_vote` requires `feature_name` because it needs to resolve the term column. The tool returns an error if `feature_name` is not specified with `majority_vote`.

#### `restructure_assets` — add selection parameters

Add selector parameters consistent with `fetch_table_features`:

```python
async def restructure_assets(
    dataset_rid: str,
    asset_table: str,
    output_dir: str,
    group_by: list[str] | None = None,
    value_selector: str | None = None,   # NEW: "newest", "first", "majority_vote"
    workflow: str | None = None,         # NEW: Workflow RID or type name
    execution: str | None = None,        # NEW: Execution RID
    use_symlinks: bool = True,
    enforce_vocabulary: bool = True,
    version: str | None = None,
    materialize: bool = True,
) -> str:
```

`value_selector`, `workflow`, and `execution` are mutually exclusive — same rule as `fetch_table_features`. Resolution maps the string to the `FeatureRecord` selector and passes it to `bag.restructure_assets(value_selector=...)`.

### Layer 3: MCP Resources

Existing resources already use `FeatureRecord`:
- `deriva://table/{table}/feature-values` → `ml.fetch_table_features()` → returns `FeatureRecord`
- `deriva://table/{table}/feature-values/newest` → `ml.fetch_table_features(selector=FeatureRecord.select_newest)` → returns `FeatureRecord`
- `deriva://feature/{table}/{name}/values` → `ml.list_feature_values()` → returns `FeatureRecord`

**Add new resources** for selector parity:
- `deriva://table/{table}/feature-values/first` → `ml.fetch_table_features(selector=FeatureRecord.select_first)` — earliest annotation per record
- `deriva://table/{table}/feature-values/majority_vote` → `ml.fetch_table_features(selector=RecordClass.select_majority_vote())` — consensus label per record (requires auto-detection of term column)

**Files:**
- `src/deriva_mcp/resources.py` — add two new resource handlers following the pattern of `get_table_feature_values_newest`

### Layer 3b: RAG Indexing

Resource names and descriptions should be included in the per-user RAG index so they're discoverable via `rag_search`. When `rag_index_schema` runs, it should also index the available MCP resources with their URIs, names, and descriptions. This makes resources discoverable when a user asks "how do I get the majority vote labels?" — the RAG should surface the `feature-values/majority_vote` resource.

**Files:**
- `src/deriva_mcp/rag/` — update schema indexing to include resource metadata

### Layer 4: Skills

#### `create-feature` skill

Update `references/concepts.md`:
- Remove the two-type distinction (FeatureRecord vs FeatureValueRecord)
- Consolidate selector tables into one
- Remove the "mixing types" pitfall
- Update "Writing custom selectors" to show one signature
- Update `select_majority_vote` example to show factory pattern

Update `SKILL.md`:
- Add `"first"` and `"majority_vote"` to the MCP selector table
- Update the custom selector escalation path

#### `prepare-training-data` skill

Update `references/restructure-guide.md`:
- Change `value_selector` examples from `FeatureValueRecord` to `FeatureRecord`
- Update built-in selector imports
- Add `value_selector` string parameter for MCP tool usage

#### `dataset-lifecycle` skill

Update `references/concepts.md`:
- Brief mention of `restructure_assets` value_selector now supporting named selectors

## Summary of Changes

### deriva-ml (library)

| File | Change |
|------|--------|
| `feature.py` | Add `select_first`, `select_latest`, `select_majority_vote` to `FeatureRecord` |
| `dataset/dataset_bag.py` | Delete `FeatureValueRecord` class + 3 module selectors. Update `restructure_assets` to use `FeatureRecord` directly |
| `dataset/__init__.py` | Remove `FeatureValueRecord` export. Re-export selectors from `FeatureRecord` if needed |
| `__init__.py` | Remove lazy `FeatureValueRecord` import |

### deriva-mcp (MCP server)

| File | Change |
|------|--------|
| `tools/feature.py` | Add `"first"`, `"latest"`, `"majority_vote"` to `fetch_table_features` selector mapping |
| `tools/dataset.py` | Add `value_selector`, `workflow`, `execution` parameters to `restructure_assets` tool |
| `resources.py` | Add `feature-values/first` and `feature-values/majority_vote` resources |
| `rag/` | Index MCP resource names and descriptions in per-user RAG content |
| `server.py` | Update MCP server instructions to document new selectors and resources |

### deriva-skills (skills)

| File | Change |
|------|--------|
| `create-feature/references/concepts.md` | Consolidate selector docs to one type, update examples |
| `create-feature/SKILL.md` | Add new MCP selectors to table, update custom selector section |
| `prepare-training-data/references/restructure-guide.md` | Update value_selector examples to `FeatureRecord` |

### Tests

| File | Change |
|------|--------|
| `tests/dataset/test_restructure.py` | Update `FeatureValueRecord` references to `FeatureRecord` |
| New test | Test `select_first`, `select_majority_vote` on `FeatureRecord` |

### Documentation

| File | Change |
|------|--------|
| `docs/concepts/features.md` | Update selector examples, remove `FeatureValueRecord` |
| `docs/concepts/datasets.md` | Update restructure examples |

## User-Facing API After Change

### MCP tool: `fetch_table_features`

```
# Built-in selectors (all mutually exclusive with workflow/execution)
fetch_table_features("Image", feature_name="Diagnosis", selector="newest")
fetch_table_features("Image", feature_name="Diagnosis", selector="first")
fetch_table_features("Image", feature_name="Diagnosis", selector="majority_vote")

# Workflow/execution filtering (unchanged)
fetch_table_features("Image", feature_name="Diagnosis", workflow="Training")
fetch_table_features("Image", feature_name="Diagnosis", execution="3-XYZ")
```

### MCP tool: `restructure_assets`

```
# With named selector (new parameter)
restructure_assets(dataset_rid="...", asset_table="Image",
                   output_dir="./ml_data", group_by=["Diagnosis"],
                   value_selector="majority_vote")
```

### Python API

```python
from deriva_ml.feature import FeatureRecord

# All selectors on one type
features = ml.fetch_table_features("Image", selector=FeatureRecord.select_newest)
features = ml.fetch_table_features("Image", selector=FeatureRecord.select_first)
features = ml.fetch_table_features("Image", selector=RecordClass.select_majority_vote())

# Same selectors work on bags
features = bag.fetch_table_features("Image", selector=FeatureRecord.select_newest)

# Same selectors work in restructure_assets
bag.restructure_assets(
    output_dir="./data", group_by=["Diagnosis"],
    value_selector=RecordClass.select_majority_vote(),
)

# Custom selectors — one signature everywhere
def select_best(records: list[FeatureRecord]) -> FeatureRecord:
    return max(records, key=lambda r: getattr(r, "Confidence", 0))

features = ml.fetch_table_features("Image", selector=select_best)
bag.restructure_assets(output_dir="./data", value_selector=select_best)
```

## Migration

Since breaking changes are acceptable:
1. Ship in the next deriva-ml minor version
2. Update MCP server and skills in the same release cycle
3. Update user guide documentation
4. No deprecation period needed

## Decisions

1. **`select_majority_vote` auto-detects for single-term features.** Yes — the 90% case is single-term, and requiring the column name adds friction. Multi-term features must specify the column explicitly.

2. **`restructure_assets` gets `workflow` and `execution` parameters** for parity with `fetch_table_features`. Both MCP tool and Python API.

3. **Add `feature-values/first` and `feature-values/majority_vote` resources.** Provides parity with the tool selectors and makes all selection modes discoverable via resources. Resource names and descriptions should also be indexed in the per-user RAG content so they're discoverable via `rag_search`.
