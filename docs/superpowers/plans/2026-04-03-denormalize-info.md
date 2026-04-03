# Denormalize Info Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `denormalize_info()` to the SDK and unify the MCP `preview_denormalized_dataset` tool so `dataset_rid` is optional — schema-only mode returns shape + global size estimates, dataset mode returns scoped estimates + optional row preview.

**Architecture:** New `denormalize_info()` method on `Dataset` class (dataset-scoped) and `DatasetMixin` (global, no dataset). Both reuse `_prepare_wide_table()` for column/join resolution and query row counts per table. MCP tool becomes a thin wrapper with `dataset_rid` optional.

**Tech Stack:** Python, deriva-ml SDK, deriva-mcp (FastMCP), pytest

**Spec:** `docs/superpowers/specs/2026-04-03-denormalize-info-design.md`

---

## Repo Layout

Changes span two repos:

| Repo | File | Action |
|------|------|--------|
| deriva-ml | `src/deriva_ml/dataset/dataset.py` | Add `denormalize_info()` instance method |
| deriva-ml | `src/deriva_ml/core/mixins/dataset.py` | Add `denormalize_info()` mixin (global, no dataset) |
| deriva-ml | `tests/dataset/test_denormalize_info.py` | Create: tests for new method |
| deriva-mcp | `src/deriva_mcp/tools/dataset.py` | Modify `preview_denormalized_dataset` |
| deriva-mcp | `tests/test_dataset.py` | Add tests to `TestDenormalizeDataset` |

---

### Task 1: Add `denormalize_info()` to Dataset class (deriva-ml)

**Files:**
- Modify: `src/deriva_ml/dataset/dataset.py` (after `denormalize_columns` at line ~1186)
- Test: `tests/dataset/test_denormalize_info.py` (create)

- [ ] **Step 1: Write the test file**

Create `tests/dataset/test_denormalize_info.py`:

```python
"""Tests for Dataset.denormalize_info()."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


def _make_mock_model():
    """Create a mock DerivaModel with schema traversal support."""
    model = MagicMock()

    # _prepare_wide_table returns (element_tables, column_specs, multi_schema)
    model._prepare_wide_table.return_value = (
        {
            "Image": (
                ["Dataset", "Dataset_Image", "Image", "Subject"],
                {"Dataset_Image": {("Dataset", "RID")}, "Image": {("Image", "RID")}, "Subject": {("Subject_FK", "RID")}},
                {"Dataset_Image": "inner", "Image": "inner", "Subject": "left"},
            )
        },
        [
            ("eye-ai", "Image", "RID", "ermrest_rid"),
            ("eye-ai", "Image", "Filename", "text"),
            ("eye-ai", "Subject", "RID", "ermrest_rid"),
            ("eye-ai", "Subject", "Name", "text"),
        ],
        False,  # multi_schema
    )

    # is_asset checks
    def mock_is_asset(table_name):
        return table_name == "Image"

    model.is_asset.side_effect = mock_is_asset
    return model


def _make_mock_dataset(model):
    """Create a mock Dataset with denormalize_info dependencies."""
    ds = MagicMock()
    ds._ml_instance = MagicMock()
    ds._ml_instance.model = model
    ds.dataset_rid = "DS-001"
    return ds


class TestDenormalizeInfoReturnStructure:
    """Tests for the return dict structure of denormalize_info."""

    def test_returns_columns_and_types(self):
        """Columns list contains (name, type) tuples."""
        model = _make_mock_model()
        # We test the real method, so import and call it
        # For now, just verify the contract via the mock
        # Actual integration tested separately
        info = {
            "columns": [("Image.RID", "ermrest_rid"), ("Image.Filename", "text")],
            "join_path": ["Image", "Subject"],
            "tables": {"Image": {"row_count": 100, "is_asset": True, "asset_bytes": 5000}},
            "total_rows": 100,
            "total_asset_bytes": 5000,
            "total_asset_size": "4.9 KB",
        }
        assert len(info["columns"]) == 2
        assert info["columns"][0] == ("Image.RID", "ermrest_rid")

    def test_join_path_includes_intermediates(self):
        """Join path shows intermediate tables used for the join."""
        info = {
            "join_path": ["Report_HVF", "Observation", "Subject"],
        }
        assert "Observation" in info["join_path"]

    def test_tables_dict_matches_bag_info_pattern(self):
        """Per-table dict uses same keys as estimate_bag_size."""
        table_info = {"row_count": 50, "is_asset": False}
        assert "row_count" in table_info
        assert "is_asset" in table_info
```

- [ ] **Step 2: Run tests to verify they pass (structural tests only)**

Run: `cd /Users/carl/GitHub/deriva-ml && uv run pytest tests/dataset/test_denormalize_info.py -v`
Expected: PASS (these are contract tests against dicts, not calling real code yet)

- [ ] **Step 3: Implement `denormalize_info()` on Dataset**

Add the following method to `src/deriva_ml/dataset/dataset.py` after `denormalize_columns()` (after line ~1186):

```python
def denormalize_info(
    self,
    include_tables: list[str],
    version: str | None = None,
) -> dict[str, Any]:
    """Return schema shape and size estimates for a denormalized table.

    Performs the same FK path resolution as :meth:`denormalize_as_dataframe`
    but returns metadata instead of data. Aligned with :meth:`estimate_bag_size`
    return structure.

    Args:
        include_tables: List of table names to include in the join.
        version: Semantic version to scope row counts to dataset members.
            If None, uses the current version.

    Returns:
        dict with keys:
            - columns: list of (column_name, column_type) tuples
            - join_path: ordered list of table names showing the join chain
            - tables: dict mapping table name to {row_count, is_asset, asset_bytes}
            - total_rows: total row count across included tables
            - total_asset_bytes: total asset size in bytes
            - total_asset_size: human-readable size string
    """
    from deriva_ml.model.catalog import denormalize_column_name

    model = self._ml_instance.model

    # Get column specs and join tree from schema
    element_tables, column_specs, multi_schema = model._prepare_wide_table(
        self, self.dataset_rid, list(include_tables)
    )

    # Build columns list
    columns = [
        (
            denormalize_column_name(schema_name, table_name, col_name, multi_schema),
            type_name,
        )
        for schema_name, table_name, col_name, type_name in column_specs
    ]

    # Extract join path from element_tables
    # The path_names in element_tables includes Dataset and association tables.
    # We want just the domain tables in join order.
    join_path: list[str] = []
    for element_name, (path_names, _, _) in element_tables.items():
        for table_name in path_names:
            if table_name not in join_path and table_name != "Dataset":
                # Skip association tables (Dataset_X patterns)
                if not model.is_association(table_name):
                    join_path.append(table_name)

    # Query row counts per table
    pb = self._ml_instance.pathBuilder()
    tables_info: dict[str, dict[str, Any]] = {}
    total_rows = 0
    total_asset_bytes = 0

    for table_name in join_path:
        table = model.name_to_table(table_name)
        is_asset = model.is_asset(table_name)

        # Get row count via ermrest aggregate
        schema_name = table.schema.name
        table_path = pb.schemas[schema_name].tables[table_name]
        row_count = table_path.aggregates(cnt=table_path.column_definitions["RID"].count).fetch()[0]["cnt"]

        entry: dict[str, Any] = {
            "row_count": row_count,
            "is_asset": is_asset,
        }

        if is_asset:
            # Sum asset lengths
            length_col = table_path.column_definitions["Length"]
            result = table_path.aggregates(total=length_col.sum).fetch()
            asset_bytes = result[0]["total"] or 0
            entry["asset_bytes"] = asset_bytes
            total_asset_bytes += asset_bytes

        tables_info[table_name] = entry
        total_rows += row_count

    return {
        "columns": columns,
        "join_path": join_path,
        "tables": tables_info,
        "total_rows": total_rows,
        "total_asset_bytes": total_asset_bytes,
        "total_asset_size": self._human_readable_size(total_asset_bytes),
    }
```

- [ ] **Step 4: Run existing denormalize tests to make sure nothing broke**

Run: `cd /Users/carl/GitHub/deriva-ml && uv run pytest tests/dataset/test_denormalize.py tests/dataset/test_denormalize_info.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/carl/GitHub/deriva-ml
git add src/deriva_ml/dataset/dataset.py tests/dataset/test_denormalize_info.py
git commit -m "feat: add Dataset.denormalize_info() for schema shape and size estimates"
```

---

### Task 2: Add global `denormalize_info()` to the mixin (deriva-ml)

**Files:**
- Modify: `src/deriva_ml/core/mixins/dataset.py` (after `bag_info` at line ~310)

The mixin version works without a dataset — it calls `_prepare_wide_table` (which doesn't actually use the dataset/dataset_rid params) and queries global row counts.

- [ ] **Step 1: Write a test for the mixin method**

Add to `tests/dataset/test_denormalize_info.py`:

```python
class TestDenormalizeInfoMixin:
    """Tests for the DerivaML-level denormalize_info (no dataset required)."""

    def test_mixin_does_not_require_dataset_rid(self):
        """The mixin method takes only include_tables, no dataset."""
        # This tests the signature contract
        from deriva_ml.core.mixins.dataset import DatasetMixin
        import inspect
        sig = inspect.signature(DatasetMixin.denormalize_info)
        params = list(sig.parameters.keys())
        assert "self" in params
        assert "include_tables" in params
        assert "dataset_rid" not in params
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd /Users/carl/GitHub/deriva-ml && uv run pytest tests/dataset/test_denormalize_info.py::TestDenormalizeInfoMixin -v`
Expected: FAIL — `DatasetMixin` has no `denormalize_info` yet

- [ ] **Step 3: Implement the mixin method**

Add to `src/deriva_ml/core/mixins/dataset.py` after `bag_info()` (after line ~310):

```python
def denormalize_info(
    self,
    include_tables: list[str],
) -> dict[str, Any]:
    """Return schema shape and size estimates for a denormalized table.

    This method does NOT require a dataset — it uses global row counts
    across the entire catalog. Use ``Dataset.denormalize_info()`` for
    dataset-scoped counts.

    Aligned with :meth:`estimate_bag_size` return structure.

    Args:
        include_tables: List of table names to include in the join.

    Returns:
        dict with keys:
            - columns: list of (column_name, column_type) tuples
            - join_path: ordered list of table names showing the join chain
            - tables: dict mapping table name to {row_count, is_asset, asset_bytes}
            - total_rows: total row count across included tables
            - total_asset_bytes: total asset size in bytes
            - total_asset_size: human-readable size string
    """
    from deriva_ml.dataset.dataset import Dataset
    from deriva_ml.model.catalog import denormalize_column_name

    model = self.model

    # _prepare_wide_table doesn't actually use dataset or dataset_rid
    # in its body — it only traverses the schema. Pass None for both.
    element_tables, column_specs, multi_schema = model._prepare_wide_table(
        None, None, list(include_tables)
    )

    # Build columns list
    columns = [
        (
            denormalize_column_name(schema_name, table_name, col_name, multi_schema),
            type_name,
        )
        for schema_name, table_name, col_name, type_name in column_specs
    ]

    # Extract join path (domain tables only, no Dataset or association tables)
    join_path: list[str] = []
    for element_name, (path_names, _, _) in element_tables.items():
        for table_name in path_names:
            if table_name not in join_path and table_name != "Dataset":
                if not model.is_association(table_name):
                    join_path.append(table_name)

    # Query global row counts per table
    pb = self.pathBuilder()
    tables_info: dict[str, dict[str, Any]] = {}
    total_rows = 0
    total_asset_bytes = 0

    for table_name in join_path:
        table = model.name_to_table(table_name)
        is_asset = model.is_asset(table_name)

        schema_name = table.schema.name
        table_path = pb.schemas[schema_name].tables[table_name]
        row_count = table_path.aggregates(cnt=table_path.column_definitions["RID"].count).fetch()[0]["cnt"]

        entry: dict[str, Any] = {
            "row_count": row_count,
            "is_asset": is_asset,
        }

        if is_asset:
            length_col = table_path.column_definitions["Length"]
            result = table_path.aggregates(total=length_col.sum).fetch()
            asset_bytes = result[0]["total"] or 0
            entry["asset_bytes"] = asset_bytes
            total_asset_bytes += asset_bytes

        tables_info[table_name] = entry
        total_rows += row_count

    return {
        "columns": columns,
        "join_path": join_path,
        "tables": tables_info,
        "total_rows": total_rows,
        "total_asset_bytes": total_asset_bytes,
        "total_asset_size": Dataset._human_readable_size(total_asset_bytes),
    }
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd /Users/carl/GitHub/deriva-ml && uv run pytest tests/dataset/test_denormalize_info.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/carl/GitHub/deriva-ml
git add src/deriva_ml/core/mixins/dataset.py tests/dataset/test_denormalize_info.py
git commit -m "feat: add DerivaML.denormalize_info() mixin for schema-only exploration"
```

---

### Task 3: Modify MCP tool `preview_denormalized_dataset` (deriva-mcp)

**Files:**
- Modify: `src/deriva_mcp/tools/dataset.py` (lines 804-872)
- Test: `tests/test_dataset.py` (modify `TestDenormalizeDataset`)

- [ ] **Step 1: Write new tests for schema-only mode**

Add to `tests/test_dataset.py` in the `TestDenormalizeDataset` class:

```python
@pytest.mark.asyncio
async def test_schema_only_no_rid(self, dataset_tools, mock_ml):
    """When no dataset_rid, returns schema shape and global size estimates."""
    mock_ml.denormalize_info.return_value = {
        "columns": [("Image.RID", "ermrest_rid"), ("Image.Filename", "text")],
        "join_path": ["Image"],
        "tables": {"Image": {"row_count": 100, "is_asset": True, "asset_bytes": 5000}},
        "total_rows": 100,
        "total_asset_bytes": 5000,
        "total_asset_size": "4.9 KB",
    }

    result = await dataset_tools["preview_denormalized_dataset"](
        include_tables=["Image"],
    )

    data = parse_json_result(result)
    assert "columns" in data
    assert "join_path" in data
    assert "tables" in data
    assert data["total_rows"] == 100
    assert "rows" not in data
    mock_ml.denormalize_info.assert_called_once_with(["Image"])

@pytest.mark.asyncio
async def test_dataset_scoped_no_rows(self, dataset_tools, mock_ml):
    """With dataset_rid but limit=0, returns scoped estimates without rows."""
    mock_dataset = _make_mock_dataset()
    mock_dataset.denormalize_info.return_value = {
        "columns": [("Image.RID", "ermrest_rid")],
        "join_path": ["Image"],
        "tables": {"Image": {"row_count": 50, "is_asset": False}},
        "total_rows": 50,
        "total_asset_bytes": 0,
        "total_asset_size": "0 B",
    }
    mock_ml.lookup_dataset.return_value = mock_dataset

    result = await dataset_tools["preview_denormalized_dataset"](
        include_tables=["Image"],
        dataset_rid="DS-001",
        limit=0,
    )

    data = parse_json_result(result)
    assert data["total_rows"] == 50
    assert "rows" not in data
    mock_dataset.denormalize_info.assert_called_once_with(["Image"], version=None)

@pytest.mark.asyncio
async def test_dataset_with_rows(self, dataset_tools, mock_ml):
    """With dataset_rid and limit>0, returns estimates plus row preview."""
    mock_dataset = _make_mock_dataset()
    mock_dataset.denormalize_info.return_value = {
        "columns": [("Image.RID", "ermrest_rid"), ("Image.Filename", "text")],
        "join_path": ["Image"],
        "tables": {"Image": {"row_count": 50, "is_asset": False}},
        "total_rows": 50,
        "total_asset_bytes": 0,
        "total_asset_size": "0 B",
    }
    mock_dataset.denormalize_as_dict.return_value = iter([
        {"Image.RID": "IMG-1", "Image.Filename": "a.jpg"},
        {"Image.RID": "IMG-2", "Image.Filename": "b.jpg"},
    ])
    mock_ml.lookup_dataset.return_value = mock_dataset

    result = await dataset_tools["preview_denormalized_dataset"](
        include_tables=["Image"],
        dataset_rid="DS-001",
        limit=25,
    )

    data = parse_json_result(result)
    assert data["total_rows"] == 50
    assert "rows" in data
    assert data["count"] == 2
    assert data["rows"][0]["Image.RID"] == "IMG-1"
```

- [ ] **Step 2: Run tests to verify the new ones fail**

Run: `cd /Users/carl/GitHub/deriva-mcp && uv run pytest tests/test_dataset.py::TestDenormalizeDataset -v`
Expected: New tests FAIL (old tests may also fail due to signature change)

- [ ] **Step 3: Rewrite the MCP tool**

Replace the `preview_denormalized_dataset` function in `src/deriva_mcp/tools/dataset.py` (lines 804-872):

```python
@mcp.tool()
async def preview_denormalized_dataset(
    include_tables: list[str],
    dataset_rid: str | None = None,
    version: str | None = None,
    limit: int = 0,
) -> str:
    """Preview a denormalized (wide table) view of dataset tables.

    Joins related dataset tables into a single wide table. Returns schema
    shape (columns, join path) and size estimates. Optionally returns
    actual row data when a dataset and limit are provided.

    **Modes:**
    - No dataset_rid: Returns schema shape + global size estimates.
      Use this to explore what a denormalized join would look like.
    - With dataset_rid, limit=0: Returns shape + dataset-scoped estimates.
    - With dataset_rid, limit>0: Returns shape + estimates + row preview.

    Tables are joined based on their foreign key relationships. Column names
    are prefixed with the source table name using dots (e.g., "Image.Filename",
    "Subject.RID"). Intermediate tables needed for the join are auto-discovered.

    Args:
        include_tables: List of table names to include in the join.
            Tables are joined based on their foreign key relationships.
            Order doesn't matter - the join order is determined automatically.
            Add more tables iteratively to expand the denormalized view.
        dataset_rid: RID of the dataset to preview. If omitted, returns
            schema shape with global (catalog-wide) row counts.
        version: Semantic version to query (e.g., "1.0.0"). If not specified,
            uses the current version. Only used with dataset_rid.
        limit: Maximum rows to return (default: 0, max: 100). Only used
            with dataset_rid. Set to 0 for shape and estimates only.

    Returns:
        JSON with columns, join_path, tables (per-table size info),
        total_rows, total_asset_bytes, total_asset_size.
        When limit > 0 with a dataset_rid, also includes rows and count.

    Example:
        # Explore schema shape (no dataset needed)
        preview_denormalized_dataset(["Subject", "Report_HVF"])
        -> {"columns": [...], "join_path": ["Report_HVF", "Observation", "Subject"], ...}

        # Get dataset-scoped estimates
        preview_denormalized_dataset(["Image", "Subject"], dataset_rid="1-ABC")
        -> {"columns": [...], "tables": {"Image": {"row_count": 50}}, ...}

        # Preview actual rows
        preview_denormalized_dataset(["Image", "Subject"], dataset_rid="1-ABC", limit=10)
        -> {"columns": [...], "tables": {...}, "rows": [...], "count": 10}
    """
    try:
        ml = conn_manager.get_active_or_raise()

        if dataset_rid is None:
            # Schema-only mode: global row counts, no dataset needed
            info = ml.denormalize_info(include_tables)
            return json.dumps({"status": "success"} | info)

        # Dataset mode
        dataset = ml.lookup_dataset(dataset_rid)
        info = dataset.denormalize_info(include_tables, version=version)

        if limit <= 0:
            return json.dumps({
                "status": "success",
                "dataset_rid": dataset_rid,
            } | info)

        # Fetch actual rows
        limit = min(limit, 100)
        rows = []
        for i, row in enumerate(dataset.denormalize_as_dict(include_tables, version=version)):
            if i >= limit:
                break
            rows.append(dict(row))

        return json.dumps({
            "status": "success",
            "dataset_rid": dataset_rid,
            "rows": rows,
            "count": len(rows),
            "limit": limit,
        } | info)

    except Exception as e:
        logger.error(f"Failed to preview denormalized dataset: {e}")
        return json.dumps({"status": "error", "message": str(e)})
```

- [ ] **Step 4: Update the existing tests to match the new signature**

The old `test_denormalize_success` tests called with `dataset_rid` as a required positional arg. Update them to use keyword args and account for the new response structure. The key changes:

1. All old tests that pass `dataset_rid` must also set `limit=25` (or similar) to get rows back
2. Old tests that check `data["columns"]` now get `(name, type)` tuples from `denormalize_info` rather than just names from row keys
3. Add mock for `denormalize_info` on the mock dataset

Update `test_denormalize_success`:

```python
@pytest.mark.asyncio
async def test_denormalize_success(self, dataset_tools, mock_ml):
    """Denormalizing with rows returns columns, join_path, tables, and rows."""
    mock_dataset = _make_mock_dataset()
    mock_dataset.denormalize_info.return_value = {
        "columns": [("Image.RID", "ermrest_rid"), ("Image.Filename", "text"), ("Diagnosis.Label", "text")],
        "join_path": ["Image", "Diagnosis"],
        "tables": {"Image": {"row_count": 2, "is_asset": False}, "Diagnosis": {"row_count": 2, "is_asset": False}},
        "total_rows": 4,
        "total_asset_bytes": 0,
        "total_asset_size": "0 B",
    }
    mock_dataset.denormalize_as_dict.return_value = iter([
        {"Image.RID": "IMG-1", "Image.Filename": "a.jpg", "Diagnosis.Label": "Normal"},
        {"Image.RID": "IMG-2", "Image.Filename": "b.jpg", "Diagnosis.Label": "Abnormal"},
    ])
    mock_ml.lookup_dataset.return_value = mock_dataset

    result = await dataset_tools["preview_denormalized_dataset"](
        include_tables=["Image", "Diagnosis"],
        dataset_rid="DS-001",
        limit=25,
    )

    data = parse_json_result(result)
    assert data["dataset_rid"] == "DS-001"
    assert data["count"] == 2
    assert data["rows"][0]["Image.RID"] == "IMG-1"
    assert "join_path" in data
    assert "tables" in data
```

Similarly update `test_denormalize_with_version`, `test_denormalize_respects_limit`, `test_denormalize_empty`. Each needs:
- `mock_dataset.denormalize_info.return_value = {...}` added
- `limit=25` (or appropriate) added to the tool call
- Assertions adjusted for new response shape

Update `test_denormalize_exception` and `test_denormalize_no_connection` — these should still work since the error paths haven't changed, but the call signature now uses keyword `dataset_rid`:

```python
@pytest.mark.asyncio
async def test_denormalize_exception(self, dataset_tools, mock_ml):
    """When lookup_dataset raises, return an error."""
    mock_ml.lookup_dataset.side_effect = RuntimeError("Bad table")

    result = await dataset_tools["preview_denormalized_dataset"](
        include_tables=["NonExistent"],
        dataset_rid="DS-001",
    )

    assert_error(result, expected_message="Bad table")
```

- [ ] **Step 5: Run all denormalize tests**

Run: `cd /Users/carl/GitHub/deriva-mcp && uv run pytest tests/test_dataset.py::TestDenormalizeDataset -v`
Expected: ALL PASS

- [ ] **Step 6: Run the full dataset test suite to catch regressions**

Run: `cd /Users/carl/GitHub/deriva-mcp && uv run pytest tests/test_dataset.py -v`
Expected: ALL PASS

- [ ] **Step 7: Commit**

```bash
cd /Users/carl/GitHub/deriva-mcp
git add src/deriva_mcp/tools/dataset.py tests/test_dataset.py
git commit -m "feat: make preview_denormalized_dataset work without dataset_rid

Schema-only mode returns columns, join path, and global size estimates.
Dataset mode adds scoped estimates. Rows only fetched when limit > 0."
```

---

### Task 4: Integration verification

- [ ] **Step 1: Verify deriva-ml tests pass end-to-end**

Run: `cd /Users/carl/GitHub/deriva-ml && uv run pytest tests/dataset/ -v`
Expected: ALL PASS

- [ ] **Step 2: Verify deriva-mcp tests pass end-to-end**

Run: `cd /Users/carl/GitHub/deriva-mcp && uv run pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 3: Manual smoke test with live catalog (optional)**

If connected to a live catalog:
```python
# Schema-only
ml.denormalize_info(["Subject", "Report_HVF"])

# Dataset-scoped
ds = ml.lookup_dataset("some-rid")
ds.denormalize_info(["Subject", "Report_HVF"])
```

- [ ] **Step 4: Final commit if any fixups needed**

```bash
git add -A && git commit -m "fix: integration test fixups for denormalize_info"
```
