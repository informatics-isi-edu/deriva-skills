# Denormalize Info: Schema Shape + Size Estimation

**Date:** 2026-04-03
**Status:** Approved
**Repos:** deriva-ml, deriva-mcp

## Problem

`preview_denormalized_dataset` requires a dataset RID, but users often want to explore what a denormalized join *would look like* before they have a dataset — or before they commit to fetching rows. The column structure and join path are purely schema-level information. Size estimates help users decide whether to proceed.

## Design

### SDK: `denormalize_info()` (deriva-ml)

Add a method that returns schema shape and size estimates for a denormalized table, aligned with the `bag_info()` / `estimate_bag_size()` patterns.

**Two entry points:**

1. **DerivaML-level** (no dataset required): `ml.denormalize_info(include_tables)` — returns columns, join path, and global per-table row counts.
2. **Dataset-level** (dataset-scoped): `dataset.denormalize_info(include_tables, version)` — returns columns, join path, and dataset-scoped row counts.

**Return structure** (aligned with `estimate_bag_size` field naming):

```python
{
    "columns": [("Subject.Subject_ID", "text"), ("Report_HVF.Filename", "text"), ...],
    "join_path": ["Report_HVF", "Observation", "Subject"],
    "tables": {
        "Subject": {"row_count": 1500, "is_asset": False},
        "Report_HVF": {"row_count": 3200, "is_asset": True, "asset_bytes": 45000000},
        "Observation": {"row_count": 2800, "is_asset": False}
    },
    "total_rows": 3200,
    "total_asset_bytes": 45000000,
    "total_asset_size": "45.0 MB"
}
```

**Field alignment with `estimate_bag_size()`:**
- `tables` dict keyed by table name, each with `row_count`, `is_asset`, `asset_bytes`
- `total_rows`, `total_asset_bytes`, `total_asset_size` at top level
- Uses `_human_readable_size()` for formatting

**Implementation details:**
- Reuses `_prepare_wide_table()` for column specs and join tree resolution
- Reuses `denormalize_columns()` internally (it already calls `_prepare_wide_table`)
- For row counts: query ermrest aggregate endpoints per table (global or dataset-scoped)
- For asset bytes: query sum of Length column for asset tables
- `join_path` extracted from the join tree returned by `_prepare_wide_table()`
- The `tables` dict includes intermediate tables (used for joins) even if not in `include_tables`, so the user can see the full join chain

**DerivaML-level method** (no dataset):
- Lives on `DerivaML` class or as a mixin method
- Calls `DerivaModel._prepare_wide_table()` with a synthetic/null dataset context for schema-only resolution
- Queries global row counts (no dataset filtering)

**Dataset-level method:**
- Lives on `Dataset` class
- Calls `_prepare_wide_table()` scoped to dataset members
- Queries dataset-scoped row counts (filtered by membership)

### MCP Tool: Unified `preview_denormalized_dataset` (deriva-mcp)

Modify the existing tool to make `dataset_rid` optional.

**Signature:**
```python
@mcp.tool()
async def preview_denormalized_dataset(
    include_tables: list[str],
    dataset_rid: str | None = None,
    version: str | None = None,
    limit: int = 0,
) -> str:
```

**Behavior matrix:**

| dataset_rid | limit | Result |
|-------------|-------|--------|
| None | ignored | Schema shape + global size estimates |
| provided | 0 | Schema shape + dataset-scoped size estimates |
| provided | >0 | Shape + estimates + actual row preview |

**Response always includes:**
- `columns` — list of (name, type) pairs
- `join_path` — ordered table list showing connections
- `tables` — per-table breakdown (row_count, is_asset, asset_bytes)
- `total_rows`, `total_asset_bytes`, `total_asset_size`

**When `limit > 0` and `dataset_rid` provided, also includes:**
- `rows` — array of row dicts
- `count` — number of rows returned

**The tool supports iterative exploration:** users start with just `include_tables` to see the shape, then add more tables, then optionally provide a dataset RID and limit to preview actual data.

## Non-Goals

- No cache status tracking (unlike `bag_info`)
- No CSV size estimation (unlike `estimate_bag_size`)
- No changes to `denormalize_as_dict` or `denormalize_as_dataframe`
- No changes to the bag export pipeline

## Changes by Repo

### deriva-ml
- Add `denormalize_info(include_tables, version=None)` to `Dataset` class
- Add DerivaML-level `denormalize_info(include_tables)` (no dataset required)
- Add mixin wrapper in `core/mixins/dataset.py`
- Extract join path from `_prepare_wide_table()` join tree

### deriva-mcp
- Modify `preview_denormalized_dataset` in `tools/dataset.py`:
  - Make `dataset_rid` optional
  - Add `limit` default to 0
  - Call `denormalize_info()` for shape/size (always)
  - Call `denormalize_as_dict()` only when `limit > 0` and `dataset_rid` provided
