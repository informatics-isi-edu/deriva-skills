# Bag Info & Execution Readiness Design Note

## Goal

Three connected improvements:

1. **`bag_info`** — Combine `estimate_bag_size` with cache status into a unified method
2. **`prefetch`** — Download bags/assets into local cache without creating an execution
3. **Execution readiness** — Pre-flight validation and prefetch steps before running experiments

---

## Part 1: `bag_info` Method

### Current State

- `Dataset.estimate_bag_size(version, exclude_tables)` — queries snapshot catalog for row counts and asset sizes
- `Dataset._bag_is_fully_materialized(bag_path)` — checks if all fetch.txt entries exist locally (private method)
- `Dataset._materialize_dataset_bag(minid, use_minid)` — downloads and materializes (checks `validated_check.txt`)
- Cache structure: `~/.deriva-ml/{hostname}/{catalog_id}/datasets/{dataset_rid}/{version}/`

### Proposed: `bag_info` Method

Rename `estimate_bag_size` → `bag_info` and add cache status:

```python
def bag_info(
    self,
    version: DatasetVersion | str,
    exclude_tables: set[str] | None = None,
) -> dict[str, Any]:
    """Get comprehensive info about a dataset bag: size, contents, and cache status.

    Returns:
        dict with keys:
            - tables: dict mapping table name to {row_count, is_asset, asset_bytes}
            - total_rows: total row count across all tables
            - total_asset_bytes: total size of asset files in bytes
            - total_asset_size: human-readable size string
            - cache_status: one of "not_cached", "cached_metadata_only",
              "cached_materialized", "cached_incomplete"
            - cache_path: local path to cached bag (if cached), else None
            - has_minid: whether a MINID has been registered for this version
    """
```

### Cache status values

| Status | Meaning | Detection |
|--------|---------|-----------|
| `not_cached` | No local copy exists | Bag directory doesn't exist |
| `cached_metadata_only` | Table data downloaded, assets not fetched | Bag exists, fetch.txt has unresolved entries, no `validated_check.txt` |
| `cached_materialized` | Fully downloaded and validated | `validated_check.txt` exists AND `_bag_is_fully_materialized` returns True |
| `cached_incomplete` | Was cached but some assets are missing | `validated_check.txt` exists but `_bag_is_fully_materialized` returns False |

### Changes: deriva-ml

1. **Dataset class** (`dataset.py`):
   - Rename `estimate_bag_size` → `bag_info` (keep old name as deprecated alias)
   - Add cache status detection logic using existing `_bag_is_fully_materialized`
   - Add `has_minid` check via `_get_minid()`
   - Make `_bag_is_fully_materialized` public or add a public `cache_status()` method

2. **DerivaML mixin** (`core/mixins/dataset.py`):
   - Update `estimate_bag_size` → `bag_info` (keep old name as deprecated alias)
   - Forward new parameters

### Changes: MCP tools

3. **MCP tool** (`tools/dataset.py`):
   - Rename `estimate_bag_size` tool → `bag_info` (keep old name as deprecated alias)
   - Include `cache_status`, `cache_path`, `has_minid` in the returned JSON
   - Add tool description noting that this checks local cache without downloading

### Changes: MCP resources

4. **MCP resource**: Add `deriva://dataset/{rid}/bag-info` or expand existing dataset resource
   - Include cache status alongside existing dataset metadata
   - This enables the model to check "is this dataset already downloaded?" without a tool call

### Changes: RAG

5. **RAG schema indexer**: No change needed — bag_info is runtime state, not schema

### Changes: Skills

6. **`dataset-lifecycle` skill**: Add bag_info to the "Use" phase — check cache status before downloading
7. **`prepare-training-data` skill**: Reference bag_info for size estimation pre-download
8. **`debug-bags` skill**: Reference bag_info for troubleshooting cache issues

### Backward compatibility

- Keep `estimate_bag_size` as a deprecated alias that calls `bag_info`
- MCP tool can keep both names during transition

---

## Part 2: Prefetch Tool

### Problem

Currently, downloading a dataset or asset requires either:
- Creating an execution (`create_execution` → `download_execution_dataset`) — which pollutes provenance with "prefetch" executions
- Using `download_dataset` — which is a tool but still downloads synchronously during a conversation

Users want to warm the cache ahead of time without creating execution records.

### Proposed: `prefetch` Tool

```python
@mcp.tool()
async def prefetch(
    dataset_rid: str | None = None,
    asset_rid: str | None = None,
    version: str | None = None,
    materialize: bool = True,
) -> str:
    """Download a dataset bag or asset into the local cache without creating an execution.

    Use this to warm the cache before running experiments. No execution or
    provenance records are created — this is purely a local operation.

    Args:
        dataset_rid: RID of a dataset to prefetch (mutually exclusive with asset_rid).
        asset_rid: RID of an asset to prefetch (mutually exclusive with dataset_rid).
        version: Dataset version to prefetch (required for datasets).
        materialize: If True (default), download all asset files. If False,
            download only metadata (table data without binary assets).

    Returns:
        JSON with cache_status, cache_path, and size info.
    """
```

### Changes: deriva-ml

1. **Dataset class** (`dataset.py`):
   - Add `prefetch(version, materialize=True)` method
   - Calls `_download_dataset_minid` + optionally `_materialize_dataset_bag`
   - Returns the `bag_info` result after prefetch
   - No execution wrapping, no provenance records

2. **DerivaML class** or mixin:
   - Add `prefetch_dataset(dataset_spec)` convenience method
   - Add `prefetch_asset(asset_rid, dest_dir)` for individual assets

### Changes: MCP tools

3. **MCP tool** (`tools/dataset.py`):
   - Add `prefetch` tool as described above
   - Returns bag_info after prefetch so the user sees what was downloaded

### Changes: Skills

4. **`dataset-lifecycle` skill**: Add prefetch to the "Use" phase
5. **`route-run-workflows` / execution skill**: Add prefetch step to pre-flight checklist

---

## Part 3: Execution Readiness Workflow

### Problem

Experiments fail at runtime when:
- Dataset RIDs in the config don't exist or point to wrong versions
- Asset RIDs (model weights, etc.) are invalid
- Bags are too large to download during execution
- Network issues during materialization

These can all be caught before `start_execution()`.

### Proposed: Pre-flight validation steps

Add to the execution workflow (both the skill and the MCP tool documentation):

```
## Pre-Flight Checklist

Before running an experiment:

1. **Validate configuration**
   - `validate_rids(dataset_rids=[...], asset_rids=[...], dataset_versions={...})`
   - Checks all RIDs exist, versions are valid, descriptions are present

2. **Check bag readiness**
   - For each dataset in the config:
     `bag_info(dataset_rid, version)` → check cache_status
   - If not cached: shows download size so user can decide whether to prefetch

3. **Prefetch if needed**
   - `prefetch(dataset_rid=..., version=...)` for large datasets
   - `prefetch(asset_rid=...)` for model weights or other assets
   - Avoids download time during the execution itself

4. **Create and run**
   - `create_execution(...)` with validated inputs
   - `start_execution()`
```

### Changes: MCP tools

1. **`validate_rids` tool**: Already exists — no changes needed
2. **`bag_info` tool**: New (from Part 1) — used in step 2
3. **`prefetch` tool**: New (from Part 2) — used in step 3
4. **`create_execution` docstring**: Add reference to pre-flight checklist

### Changes: Skills

5. **`route-run-workflows` skill**: Add pre-flight validation phase
6. **Execution skill** (when created): Include the full readiness checklist
7. **`dataset-lifecycle` skill**: Cross-reference from "Use" phase

### Changes: MCP server instructions

8. **`server.py`**: Add pre-flight workflow to the "Running workflows" section:
   ```
   **Before running an experiment:**
   1. `validate_rids` - Verify all dataset and asset RIDs exist
   2. `bag_info` - Check dataset sizes and cache status
   3. `prefetch` - Download large datasets/assets ahead of time
   ```

---

## Implementation Order

| Priority | Task | Repo | Effort |
|:---:|------|------|:---:|
| 1 | `bag_info` method on Dataset | deriva-ml | Small |
| 2 | `bag_info` MCP tool (rename estimate_bag_size) | deriva-mcp | Small |
| 3 | `bag_info` MCP resource | deriva-mcp | Small |
| 4 | `prefetch` method on Dataset/DerivaML | deriva-ml | Medium |
| 5 | `prefetch` MCP tool | deriva-mcp | Small |
| 6 | Update server instructions | deriva-mcp | Small |
| 7 | Update execution skill with readiness checklist | deriva-skills | Medium |
| 8 | Update dataset-lifecycle skill | deriva-skills | Small |
| 9 | Update prepare-training-data skill | deriva-skills | Small |

### Backward compatibility

- `estimate_bag_size` remains as deprecated alias everywhere
- `download_dataset` / `download_execution_dataset` unchanged
- No breaking changes to existing execution workflow — pre-flight is additive
