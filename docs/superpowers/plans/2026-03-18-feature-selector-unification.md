# Feature Selector Unification Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Unify `FeatureRecord` and `FeatureValueRecord` into a single type with a complete set of selectors, exposed consistently across deriva-ml, MCP tools, MCP resources, and skills.

**Architecture:** Add `select_first`, `select_latest`, `select_majority_vote` to `FeatureRecord`. Eliminate `FeatureValueRecord` from `restructure_assets` internals. Expand MCP tools and resources to expose all selectors. Update skills documentation.

**Tech Stack:** Python 3.12+, Pydantic, pytest, deriva-ml, FastMCP

**Repos:**
- `~/GitHub/deriva-ml` — library (FeatureRecord, DatasetBag, restructure_assets)
- `~/GitHub/deriva-mcp` — MCP server (tools, resources)
- `~/GitHub/deriva-skills` — skills documentation

**Spec:** `~/GitHub/deriva-skills/docs/superpowers/specs/2026-03-18-feature-selector-unification-design.md`

---

## Chunk 1: Add selectors to FeatureRecord (deriva-ml)

### Task 1: Add `select_first` to FeatureRecord

**Files:**
- Modify: `~/GitHub/deriva-ml/src/deriva_ml/feature.py` (FeatureRecord class)
- Test: `~/GitHub/deriva-ml/tests/feature/test_fetch_table_features.py`

- [ ] **Step 1: Write failing tests for select_first**

Add to `tests/feature/test_fetch_table_features.py` after the `TestSelectNewest` class:

```python
class TestSelectFirst:
    """Tests for FeatureRecord.select_first — picks earliest RCT."""

    def test_select_first_picks_earliest_rct(self):
        class TestFeature(FeatureRecord):
            Feature_Name: str = "Test"
            Image: str

        records = [
            TestFeature(Image="A", RCT="2026-01-03T00:00:00", Feature_Name="Test"),
            TestFeature(Image="A", RCT="2026-01-01T00:00:00", Feature_Name="Test"),
            TestFeature(Image="A", RCT="2026-01-02T00:00:00", Feature_Name="Test"),
        ]
        result = FeatureRecord.select_first(records)
        assert result.RCT == "2026-01-01T00:00:00"

    def test_select_first_handles_none_rct(self):
        class TestFeature(FeatureRecord):
            Feature_Name: str = "Test"
            Image: str

        records = [
            TestFeature(Image="A", RCT=None, Feature_Name="Test"),
            TestFeature(Image="A", RCT="2026-01-01T00:00:00", Feature_Name="Test"),
        ]
        # None RCT sorts as empty string — earliest
        result = FeatureRecord.select_first(records)
        assert result.RCT is None

    def test_select_first_single_record(self):
        class TestFeature(FeatureRecord):
            Feature_Name: str = "Test"
            Image: str

        records = [
            TestFeature(Image="A", RCT="2026-01-01T00:00:00", Feature_Name="Test"),
        ]
        result = FeatureRecord.select_first(records)
        assert result.RCT == "2026-01-01T00:00:00"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ~/GitHub/deriva-ml && uv run pytest tests/feature/test_fetch_table_features.py::TestSelectFirst -v`
Expected: FAIL with "AttributeError: type object 'FeatureRecord' has no attribute 'select_first'"

- [ ] **Step 3: Implement select_first**

Add to `src/deriva_ml/feature.py` after the `select_newest` static method:

```python
@staticmethod
def select_first(records: list["FeatureRecord"]) -> "FeatureRecord":
    """Select the feature record with the earliest creation time.

    Uses the RCT (Row Creation Time) field. Records with ``None`` RCT
    are treated as older than any timestamped record.

    Useful when you want to preserve the original annotation and ignore
    later revisions.

    Args:
        records: List of FeatureRecord instances for the same target
            object. Must be non-empty.

    Returns:
        The FeatureRecord with the earliest RCT value.
    """
    return min(records, key=lambda r: r.RCT or "")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd ~/GitHub/deriva-ml && uv run pytest tests/feature/test_fetch_table_features.py::TestSelectFirst -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
cd ~/GitHub/deriva-ml
git add src/deriva_ml/feature.py tests/feature/test_fetch_table_features.py
git commit -m "feat: add select_first selector to FeatureRecord"
```

### Task 2: Add `select_latest` alias to FeatureRecord

**Files:**
- Modify: `~/GitHub/deriva-ml/src/deriva_ml/feature.py`
- Test: `~/GitHub/deriva-ml/tests/feature/test_fetch_table_features.py`

- [ ] **Step 1: Write failing test**

```python
class TestSelectLatest:
    """Tests for FeatureRecord.select_latest — alias for select_newest."""

    def test_select_latest_is_equivalent_to_newest(self):
        class TestFeature(FeatureRecord):
            Feature_Name: str = "Test"
            Image: str

        records = [
            TestFeature(Image="A", RCT="2026-01-01T00:00:00", Feature_Name="Test"),
            TestFeature(Image="A", RCT="2026-01-03T00:00:00", Feature_Name="Test"),
            TestFeature(Image="A", RCT="2026-01-02T00:00:00", Feature_Name="Test"),
        ]
        result = FeatureRecord.select_latest(records)
        assert result.RCT == "2026-01-03T00:00:00"
        assert result == FeatureRecord.select_newest(records)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/GitHub/deriva-ml && uv run pytest tests/feature/test_fetch_table_features.py::TestSelectLatest -v`
Expected: FAIL

- [ ] **Step 3: Implement select_latest**

Add to `src/deriva_ml/feature.py` after `select_first`:

```python
@staticmethod
def select_latest(records: list["FeatureRecord"]) -> "FeatureRecord":
    """Select the most recently created feature record.

    Alias for ``select_newest``. Included for API symmetry with
    ``select_first``.
    """
    return FeatureRecord.select_newest(records)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd ~/GitHub/deriva-ml && uv run pytest tests/feature/test_fetch_table_features.py::TestSelectLatest -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd ~/GitHub/deriva-ml
git add src/deriva_ml/feature.py tests/feature/test_fetch_table_features.py
git commit -m "feat: add select_latest alias to FeatureRecord"
```

### Task 3: Add `select_majority_vote` factory to FeatureRecord

**Files:**
- Modify: `~/GitHub/deriva-ml/src/deriva_ml/feature.py`
- Test: `~/GitHub/deriva-ml/tests/feature/test_fetch_table_features.py`

- [ ] **Step 1: Write failing tests**

```python
class TestSelectMajorityVote:
    """Tests for FeatureRecord.select_majority_vote — picks most common value."""

    def test_majority_vote_picks_most_common(self):
        class TestFeature(FeatureRecord):
            Feature_Name: str = "Test"
            Image: str
            Diagnosis_Type: str

        records = [
            TestFeature(Image="A", Diagnosis_Type="Normal", RCT="2026-01-01T00:00:00", Feature_Name="Test"),
            TestFeature(Image="A", Diagnosis_Type="Abnormal", RCT="2026-01-02T00:00:00", Feature_Name="Test"),
            TestFeature(Image="A", Diagnosis_Type="Normal", RCT="2026-01-03T00:00:00", Feature_Name="Test"),
        ]
        selector = FeatureRecord.select_majority_vote("Diagnosis_Type")
        result = selector(records)
        assert result.Diagnosis_Type == "Normal"

    def test_majority_vote_tie_breaks_by_newest(self):
        class TestFeature(FeatureRecord):
            Feature_Name: str = "Test"
            Image: str
            Diagnosis_Type: str

        records = [
            TestFeature(Image="A", Diagnosis_Type="Normal", RCT="2026-01-01T00:00:00", Feature_Name="Test"),
            TestFeature(Image="A", Diagnosis_Type="Abnormal", RCT="2026-01-03T00:00:00", Feature_Name="Test"),
        ]
        selector = FeatureRecord.select_majority_vote("Diagnosis_Type")
        result = selector(records)
        # Tie (1 each) — break by newest RCT
        assert result.RCT == "2026-01-03T00:00:00"

    def test_majority_vote_auto_detect_single_term_column(self):
        """Auto-detect column when feature metadata is available."""
        from unittest.mock import MagicMock

        # Create a mock Feature with one term column
        mock_feature = MagicMock()
        mock_col = MagicMock()
        mock_col.name = "Diagnosis_Type"
        mock_feature.term_columns = [mock_col]

        class TestFeature(FeatureRecord):
            Feature_Name: str = "Test"
            Image: str
            Diagnosis_Type: str
            feature = mock_feature

        records = [
            TestFeature(Image="A", Diagnosis_Type="Normal", RCT="2026-01-01T00:00:00", Feature_Name="Test"),
            TestFeature(Image="A", Diagnosis_Type="Normal", RCT="2026-01-02T00:00:00", Feature_Name="Test"),
            TestFeature(Image="A", Diagnosis_Type="Abnormal", RCT="2026-01-03T00:00:00", Feature_Name="Test"),
        ]
        # No column specified — should auto-detect from feature metadata
        selector = TestFeature.select_majority_vote()
        result = selector(records)
        assert result.Diagnosis_Type == "Normal"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ~/GitHub/deriva-ml && uv run pytest tests/feature/test_fetch_table_features.py::TestSelectMajorityVote -v`
Expected: FAIL

- [ ] **Step 3: Implement select_majority_vote**

Add to `src/deriva_ml/feature.py` after `select_latest`:

```python
@classmethod
def select_majority_vote(cls, column: str | None = None):
    """Return a selector that picks the most common value for a column.

    Creates a selector function that counts the values of the specified
    column across all records, picks the most frequent one, and breaks
    ties by most recent RCT.

    For single-term features, the column can be auto-detected from the
    feature's metadata. For multi-term features, the column must be
    specified explicitly.

    Args:
        column: Name of the column to count values for. If None,
            auto-detects the first term column from feature metadata.

    Returns:
        A selector function ``(list[FeatureRecord]) -> FeatureRecord``.

    Raises:
        DerivaMLException: If column is None and the feature has no
            term columns or multiple term columns.
    """
    def _selector(records: list["FeatureRecord"]) -> "FeatureRecord":
        col = column
        if col is None:
            # Auto-detect from feature metadata on the record class
            record_cls = type(records[0])
            if hasattr(record_cls, 'feature') and record_cls.feature and record_cls.feature.term_columns:
                if len(record_cls.feature.term_columns) == 1:
                    col = record_cls.feature.term_columns[0].name
                else:
                    from deriva_ml.core.deriva_ml_exception import DerivaMLException
                    raise DerivaMLException(
                        "select_majority_vote requires a column name for "
                        "features with multiple term columns. "
                        f"Available: {[c.name for c in record_cls.feature.term_columns]}"
                    )
            else:
                from deriva_ml.core.deriva_ml_exception import DerivaMLException
                raise DerivaMLException(
                    "select_majority_vote requires a column name — "
                    "could not auto-detect from feature metadata."
                )

        from collections import Counter
        counts = Counter(getattr(r, col, None) for r in records)
        max_count = max(counts.values())
        majority_values = {v for v, c in counts.items() if c == max_count}
        candidates = [r for r in records if getattr(r, col, None) in majority_values]
        return max(candidates, key=lambda r: r.RCT or "")

    return _selector
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd ~/GitHub/deriva-ml && uv run pytest tests/feature/test_fetch_table_features.py::TestSelectMajorityVote -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Run ALL existing selector tests to verify no regressions**

Run: `cd ~/GitHub/deriva-ml && uv run pytest tests/feature/test_fetch_table_features.py -v`
Expected: All existing tests PASS

- [ ] **Step 6: Commit**

```bash
cd ~/GitHub/deriva-ml
git add src/deriva_ml/feature.py tests/feature/test_fetch_table_features.py
git commit -m "feat: add select_majority_vote factory to FeatureRecord"
```

### Task 4: Integration test — new selectors with fetch_table_features

**Files:**
- Test: `~/GitHub/deriva-ml/tests/feature/test_fetch_table_features.py`

- [ ] **Step 1: Write integration test for select_first with fetch_table_features**

Add to the `TestFetchTableFeatures` class or create a new class:

```python
class TestFetchWithNewSelectors:
    """Integration tests: new selectors with fetch_table_features on live catalog."""

    def test_fetch_with_selector_first(self, dataset_test, tmp_path):
        """select_first should return the earliest value per record."""
        ml = dataset_test
        features = ml.fetch_table_features(
            "Image",
            feature_name="Image_Classification",
            selector=FeatureRecord.select_first,
        )
        records = features.get("Image_Classification", [])
        # All records should be present (one per image)
        assert len(records) > 0
        # Each record should have RCT set
        for r in records:
            assert hasattr(r, 'RCT')

    def test_fetch_with_selector_latest(self, dataset_test, tmp_path):
        """select_latest should return same results as select_newest."""
        ml = dataset_test
        newest = ml.fetch_table_features(
            "Image",
            feature_name="Image_Classification",
            selector=FeatureRecord.select_newest,
        )
        latest = ml.fetch_table_features(
            "Image",
            feature_name="Image_Classification",
            selector=FeatureRecord.select_latest,
        )
        newest_rids = {getattr(r, 'Image', None) for r in newest.get("Image_Classification", [])}
        latest_rids = {getattr(r, 'Image', None) for r in latest.get("Image_Classification", [])}
        assert newest_rids == latest_rids
```

- [ ] **Step 2: Run integration tests**

Run: `cd ~/GitHub/deriva-ml && uv run pytest tests/feature/test_fetch_table_features.py::TestFetchWithNewSelectors -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
cd ~/GitHub/deriva-ml
git add tests/feature/test_fetch_table_features.py
git commit -m "test: add integration tests for new FeatureRecord selectors"
```

---

## Chunk 2: Eliminate FeatureValueRecord from restructure_assets (deriva-ml)

### Task 5: Update restructure_assets to use FeatureRecord

**Files:**
- Modify: `~/GitHub/deriva-ml/src/deriva_ml/dataset/dataset_bag.py`
- Modify: `~/GitHub/deriva-ml/src/deriva_ml/dataset/__init__.py`
- Modify: `~/GitHub/deriva-ml/src/deriva_ml/__init__.py`
- Test: `~/GitHub/deriva-ml/tests/dataset/test_restructure.py`

- [ ] **Step 1: Update _load_features_cache to keep FeatureRecord**

In `dataset_bag.py`, find `_load_features_cache` (around line 1335). Change the cache type and remove the FeatureValueRecord conversion:

```python
# Before: records_cache: dict[str, dict[RID, list[FeatureValueRecord]]] = {}
# After:
records_cache: dict[str, dict[RID, list[FeatureRecord]]] = {}
```

Replace the FeatureValueRecord construction loop (lines 1387-1410) with:

```python
for fv in feature_values:
    target_rid = getattr(fv, table_name, None)
    if target_rid is None:
        continue
    # Check the value column is populated
    value = getattr(fv, use_column, None) if use_column else None
    if value is None:
        continue
    records_cache[group_key][target_rid].append(fv)
```

- [ ] **Step 2: Update value_selector parameter type**

In both `_build_dataset_type_path_map` and `restructure_assets` methods, change:

```python
# Before
value_selector: Callable[[list[FeatureValueRecord]], FeatureValueRecord] | None = None

# After
value_selector: Callable[[list[FeatureRecord]], FeatureRecord] | None = None
```

Update the import at the top of the file to import `FeatureRecord`:
```python
from deriva_ml.feature import FeatureRecord
```

- [ ] **Step 3: Update directory naming to use FeatureRecord attributes**

Where the code reads `record.value` for directory naming, change to `getattr(record, use_column)`. The `use_column` variable is already tracked in the cache-loading code.

Store the column name alongside the records in the cache so it's available at naming time:

```python
# Store as: records_cache[group_key] = (column_name, {target_rid: [FeatureRecord, ...]})
```

Or refactor to pass the column name through the resolution chain.

- [ ] **Step 4: Delete FeatureValueRecord and module-level selectors**

Remove from `dataset_bag.py`:
- `class FeatureValueRecord` (lines 69-135)
- `def select_majority_vote` (lines 141-160)
- `def select_latest` (lines 163-175)
- `def select_first` (lines 178-190)

- [ ] **Step 5: Update exports**

In `src/deriva_ml/dataset/__init__.py`, remove:
```python
FeatureValueRecord, select_first, select_majority_vote
```

In `src/deriva_ml/__init__.py`, remove the lazy import for `FeatureValueRecord`.

Optionally re-export the FeatureRecord selectors for convenience:
```python
from deriva_ml.feature import FeatureRecord
# Users can now do: from deriva_ml import FeatureRecord
# Then: FeatureRecord.select_majority_vote("col")
```

- [ ] **Step 6: Update test_restructure.py**

In `tests/dataset/test_restructure.py`, find the `test_value_selector_applied_to_child_dataset_assets` test (line 839). Change:

```python
# Before
from deriva_ml.dataset.dataset_bag import FeatureValueRecord
def tracking_selector(records: list[FeatureValueRecord]) -> FeatureValueRecord:

# After
from deriva_ml.feature import FeatureRecord
def tracking_selector(records: list[FeatureRecord]) -> FeatureRecord:
```

Update the selector logic to use FeatureRecord attributes instead of `.value` and `.raw_record`.

- [ ] **Step 7: Run ALL restructure tests**

Run: `cd ~/GitHub/deriva-ml && uv run pytest tests/dataset/test_restructure.py -v`
Expected: All tests PASS

- [ ] **Step 8: Run the full test suite**

Run: `cd ~/GitHub/deriva-ml && uv run pytest -x`
Expected: All tests PASS. Fix any failures before proceeding.

- [ ] **Step 9: Commit**

```bash
cd ~/GitHub/deriva-ml
git add src/deriva_ml/feature.py src/deriva_ml/dataset/dataset_bag.py \
        src/deriva_ml/dataset/__init__.py src/deriva_ml/__init__.py \
        tests/dataset/test_restructure.py
git commit -m "refactor: eliminate FeatureValueRecord, use FeatureRecord everywhere"
```

---

## Chunk 3: Update MCP tools (deriva-mcp)

### Task 6: Expand fetch_table_features selectors

**Files:**
- Modify: `~/GitHub/deriva-mcp/src/deriva_mcp/tools/feature.py`
- Test: `~/GitHub/deriva-mcp/tests/test_feature.py`

- [ ] **Step 1: Write tests for new selector names**

Add to `tests/test_feature.py`:

```python
class TestFetchTableFeaturesSelectors:
    """Tests for expanded selector support in fetch_table_features MCP tool."""

    @pytest.fixture
    def feature_tools(self):
        # Use existing fixture pattern from test_feature.py
        ...

    async def test_selector_first(self, feature_tools, mock_ml):
        """selector='first' should use FeatureRecord.select_first."""
        mock_ml.fetch_table_features.return_value = {"Diagnosis": []}
        result = await feature_tools["fetch_table_features"](
            table_name="Image", selector="first"
        )
        data = json.loads(result)
        assert "Diagnosis" in data or data == {}
        # Verify select_first was passed as selector
        call_kwargs = mock_ml.fetch_table_features.call_args.kwargs
        assert call_kwargs.get("selector") is not None

    async def test_selector_latest(self, feature_tools, mock_ml):
        """selector='latest' should use FeatureRecord.select_latest."""
        mock_ml.fetch_table_features.return_value = {"Diagnosis": []}
        result = await feature_tools["fetch_table_features"](
            table_name="Image", selector="latest"
        )
        data = json.loads(result)
        assert "status" not in data or data.get("status") != "error"

    async def test_selector_majority_vote_requires_feature_name(self, feature_tools, mock_ml):
        """majority_vote without feature_name should error."""
        result = await feature_tools["fetch_table_features"](
            table_name="Image", selector="majority_vote"
        )
        data = json.loads(result)
        assert data["status"] == "error"
        assert "feature_name" in data["message"].lower() or "majority_vote" in data["message"].lower()

    async def test_selector_unknown_errors(self, feature_tools, mock_ml):
        """Unknown selector name should error."""
        result = await feature_tools["fetch_table_features"](
            table_name="Image", selector="nonexistent"
        )
        data = json.loads(result)
        assert data["status"] == "error"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ~/GitHub/deriva-mcp && uv run pytest tests/test_feature.py::TestFetchTableFeaturesSelectors -v`
Expected: FAIL

- [ ] **Step 3: Update fetch_table_features tool**

In `src/deriva_mcp/tools/feature.py`, expand the selector resolution block:

```python
from deriva_ml.feature import FeatureRecord

selector_fn = None
if selector == "newest":
    selector_fn = FeatureRecord.select_newest
elif selector == "first":
    selector_fn = FeatureRecord.select_first
elif selector == "latest":
    selector_fn = FeatureRecord.select_latest
elif selector == "majority_vote":
    if not feature_name:
        return json.dumps({
            "status": "error",
            "message": "selector='majority_vote' requires feature_name to be specified.",
        })
    feat = ml.lookup_feature(table_name, feature_name)
    RecordClass = feat.feature_record_class()
    selector_fn = RecordClass.select_majority_vote()
elif selector is not None:
    return json.dumps({
        "status": "error",
        "message": f"Unknown selector '{selector}'. Supported: 'newest', 'first', 'latest', 'majority_vote'.",
    })
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd ~/GitHub/deriva-mcp && uv run pytest tests/test_feature.py::TestFetchTableFeaturesSelectors -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd ~/GitHub/deriva-mcp
git add src/deriva_mcp/tools/feature.py tests/test_feature.py
git commit -m "feat: add first, latest, majority_vote selectors to fetch_table_features"
```

### Task 7: Add value_selector, workflow, execution to restructure_assets

**Files:**
- Modify: `~/GitHub/deriva-mcp/src/deriva_mcp/tools/dataset.py`
- Test: `~/GitHub/deriva-mcp/tests/test_dataset.py`

- [ ] **Step 1: Write tests**

Add to `tests/test_dataset.py` in the restructure_assets test class:

```python
async def test_restructure_with_value_selector(self, dataset_tools, mock_ml):
    """value_selector parameter should be passed through to bag."""
    mock_bag = MagicMock()
    mock_bag.restructure_assets.return_value = {}
    mock_ml.download_dataset_bag.return_value = mock_bag
    mock_ml.lookup_dataset.return_value = MagicMock(current_version="1.0.0")

    result = await dataset_tools["restructure_assets"](
        dataset_rid="2-XXXX",
        asset_table="Image",
        output_dir="./data",
        value_selector="newest",
    )
    call_kwargs = mock_bag.restructure_assets.call_args.kwargs
    assert call_kwargs.get("value_selector") is not None

async def test_restructure_mutual_exclusivity(self, dataset_tools, mock_ml):
    """value_selector + workflow should error."""
    result = await dataset_tools["restructure_assets"](
        dataset_rid="2-XXXX",
        asset_table="Image",
        output_dir="./data",
        value_selector="newest",
        workflow="Training",
    )
    data = json.loads(result)
    assert data["status"] == "error"
```

- [ ] **Step 2: Add parameters to restructure_assets tool**

In `src/deriva_mcp/tools/dataset.py`, add `value_selector`, `workflow`, `execution` parameters. Add mutual exclusivity check. Resolve string names to FeatureRecord selectors before passing to `bag.restructure_assets()`.

- [ ] **Step 3: Run tests**

Run: `cd ~/GitHub/deriva-mcp && uv run pytest tests/test_dataset.py -k restructure -v`
Expected: All PASS

- [ ] **Step 4: Commit**

```bash
cd ~/GitHub/deriva-mcp
git add src/deriva_mcp/tools/dataset.py tests/test_dataset.py
git commit -m "feat: add value_selector, workflow, execution to restructure_assets tool"
```

### Task 8: Add feature-values/first and feature-values/majority_vote resources

**Files:**
- Modify: `~/GitHub/deriva-mcp/src/deriva_mcp/resources.py`
- Test: `~/GitHub/deriva-mcp/tests/test_resources.py`

- [ ] **Step 1: Add resource handlers**

In `resources.py`, after `get_table_feature_values_newest`, add:

```python
@mcp.resource(
    "deriva://table/{table_name}/feature-values/first",
    name="Table Feature Values (First)",
    description="Feature values for a table, deduplicated to earliest (first) annotation per target object",
    mime_type="application/json",
)
def get_table_feature_values_first(table_name: str) -> str:
    """Return feature values deduplicated to the earliest per target object."""
    ml = conn_manager.get_active_or_raise()
    try:
        from deriva_ml.feature import FeatureRecord
        features = ml.fetch_table_features(table_name, selector=FeatureRecord.select_first)
        result = {fname: [r.model_dump(mode="json") for r in records] for fname, records in features.items()}
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})

@mcp.resource(
    "deriva://table/{table_name}/feature-values/majority_vote",
    name="Table Feature Values (Majority Vote)",
    description="Feature values for a table, deduplicated to consensus (majority vote) label per target object",
    mime_type="application/json",
)
def get_table_feature_values_majority_vote(table_name: str) -> str:
    """Return feature values deduplicated by majority vote per target object."""
    ml = conn_manager.get_active_or_raise()
    try:
        from deriva_ml.feature import FeatureRecord
        # For each feature, use auto-detected column
        features = ml.fetch_table_features(table_name)
        result = {}
        for fname, records in features.items():
            if not records:
                result[fname] = []
                continue
            RecordClass = type(records[0])
            selector = RecordClass.select_majority_vote()
            # Group by target and apply selector
            from collections import defaultdict
            feat = ml.lookup_feature(table_name, fname)
            target_col = feat.target_table.name
            grouped = defaultdict(list)
            for r in records:
                grouped[getattr(r, target_col, None)].append(r)
            selected = []
            for group in grouped.values():
                if len(group) == 1:
                    selected.append(group[0])
                else:
                    try:
                        selected.append(selector(group))
                    except Exception:
                        selected.append(FeatureRecord.select_newest(group))
            result[fname] = [r.model_dump(mode="json") for r in selected]
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})
```

- [ ] **Step 2: Run resource tests**

Run: `cd ~/GitHub/deriva-mcp && uv run pytest tests/test_resources.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
cd ~/GitHub/deriva-mcp
git add src/deriva_mcp/resources.py tests/test_resources.py
git commit -m "feat: add feature-values/first and majority_vote resources"
```

### Task 9: Update MCP server instructions

**Files:**
- Modify: `~/GitHub/deriva-mcp/src/deriva_mcp/server.py`

- [ ] **Step 1: Update the server prompt to document new selectors and resources**

Add the new selector names to the `fetch_table_features` documentation in the server prompt. Add the new resources to the resource list.

- [ ] **Step 2: Commit**

```bash
cd ~/GitHub/deriva-mcp
git add src/deriva_mcp/server.py
git commit -m "docs: update MCP server instructions for new selectors and resources"
```

### Task 10: Add resource metadata to RAG index

**Files:**
- Modify: `~/GitHub/deriva-mcp/src/deriva_mcp/rag/` (schema indexing)

- [ ] **Step 1: Update schema indexer to include MCP resource metadata**

When `rag_index_schema` runs, also index the registered MCP resource URIs, names, and descriptions as searchable chunks. This makes resources discoverable via `rag_search`.

- [ ] **Step 2: Run RAG tests**

Run: `cd ~/GitHub/deriva-mcp && uv run pytest tests/test_rag*.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
cd ~/GitHub/deriva-mcp
git add src/deriva_mcp/rag/
git commit -m "feat: index MCP resource metadata in per-user RAG"
```

---

## Chunk 4: Update skills (deriva-skills)

### Task 11: Update create-feature skill

**Files:**
- Modify: `~/GitHub/deriva-skills/skills/create-feature/references/concepts.md`
- Modify: `~/GitHub/deriva-skills/skills/create-feature/SKILL.md`

- [ ] **Step 1: Consolidate selector docs in concepts.md**

Remove:
- The "two record types" distinction
- The separate "Catalog API selectors" and "Bag API selectors" tables
- The "Mixing FeatureRecord and FeatureValueRecord selectors" pitfall

Replace with a single "Predefined selectors" table showing all selectors on `FeatureRecord`:

| Selector | Type | What it does |
|----------|------|-------------|
| `select_newest` | Static | Most recent by RCT |
| `select_first` | Static | Earliest by RCT |
| `select_latest` | Static | Alias for select_newest |
| `select_by_execution(rid)` | Factory | Filter by execution, then newest |
| `select_majority_vote(col)` | Factory | Most common value, ties by newest. Auto-detects column for single-term features |

Update the "Which selection method" table to remove the bag column:

| I want to... | MCP tool | Python API |
|---|---|---|
| Latest value | `selector="newest"` | `selector=FeatureRecord.select_newest` |
| Earliest value | `selector="first"` | `selector=FeatureRecord.select_first` |
| Majority vote | `selector="majority_vote"` | `selector=RecordClass.select_majority_vote()` |
| By workflow | `workflow="Training"` | `ml.select_by_workflow(records, "Training")` |
| By execution | `execution="3-XYZ"` | `selector=FeatureRecord.select_by_execution("3-XYZ")` |
| Custom logic | Write Python script | `selector=my_function` |

- [ ] **Step 2: Update SKILL.md selector table**

Add `"first"`, `"latest"`, `"majority_vote"` to the MCP selector table.

- [ ] **Step 3: Commit**

```bash
cd ~/GitHub/deriva-skills
git add skills/create-feature/
git commit -m "docs: update feature skill for unified selectors"
```

### Task 12: Update prepare-training-data skill

**Files:**
- Modify: `~/GitHub/deriva-skills/skills/prepare-training-data/references/restructure-guide.md`

- [ ] **Step 1: Update value_selector examples**

Change all `FeatureValueRecord` references to `FeatureRecord`. Update import paths. Update the built-in selector list.

- [ ] **Step 2: Add MCP value_selector parameter documentation**

Show the new `value_selector` string parameter on the MCP `restructure_assets` tool.

- [ ] **Step 3: Commit**

```bash
cd ~/GitHub/deriva-skills
git add skills/prepare-training-data/
git commit -m "docs: update prepare-training-data for unified selectors"
```

### Task 13: Run full test suites across all repos

- [ ] **Step 1: deriva-ml full test suite**

Run: `cd ~/GitHub/deriva-ml && uv run pytest -x -v`
Expected: All PASS

- [ ] **Step 2: deriva-mcp full test suite**

Run: `cd ~/GitHub/deriva-mcp && uv run pytest -x -v`
Expected: All PASS

- [ ] **Step 3: Review all changes**

```bash
cd ~/GitHub/deriva-ml && git log --oneline -10
cd ~/GitHub/deriva-mcp && git log --oneline -10
cd ~/GitHub/deriva-skills && git log --oneline -10
```

Verify each commit is clean and the change set is complete.
