"""Tests for the subset_filters module (dataset-lifecycle skill).

Covers:
- Filter registry mechanics (registration, lookup, custom filters)
- Shared helpers (_merge_dataframes, _extract_rids, _validate_column)
- All built-in filters (all_records, has_feature, feature_equals, feature_in, numeric_range)
- Edge cases (empty DataFrames, missing columns, non-numeric columns, deduplication)
"""

from __future__ import annotations

import pandas as pd
import pytest

from subset_filters import (
    FILTER_REGISTRY,
    _extract_rids,
    _merge_dataframes,
    _validate_column,
    all_records,
    feature_equals,
    feature_in,
    get_filter,
    has_feature,
    numeric_range,
    register_filter,
)


# =============================================================================
# Registry tests
# =============================================================================


class TestFilterRegistry:
    """Tests for the filter registry mechanics."""

    def test_builtin_filters_registered(self):
        expected = {"all_records", "has_feature", "feature_equals", "feature_in", "numeric_range"}
        assert expected.issubset(FILTER_REGISTRY.keys())

    def test_get_filter_returns_callable(self):
        fn = get_filter("all_records")
        assert callable(fn)

    def test_get_filter_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown filter 'nonexistent'"):
            get_filter("nonexistent")

    def test_get_filter_error_lists_available(self):
        with pytest.raises(ValueError, match="all_records"):
            get_filter("bad_name")

    def test_register_custom_filter(self):
        @register_filter("test_custom")
        def my_filter(dataframes, *, element_table, **kwargs):
            return [], "custom"

        assert "test_custom" in FILTER_REGISTRY
        assert get_filter("test_custom") is my_filter
        # Cleanup
        del FILTER_REGISTRY["test_custom"]

    def test_register_overwrites_existing(self):
        @register_filter("test_overwrite")
        def first(dataframes, *, element_table, **kwargs):
            return [], "first"

        @register_filter("test_overwrite")
        def second(dataframes, *, element_table, **kwargs):
            return [], "second"

        assert get_filter("test_overwrite") is second
        del FILTER_REGISTRY["test_overwrite"]


# =============================================================================
# Helper tests
# =============================================================================


class TestMergeDataframes:
    """Tests for _merge_dataframes helper."""

    def test_merges_single_source(self, sample_dataframes):
        df = _merge_dataframes(sample_dataframes, "Image")
        assert len(df) == 5
        assert "Image.RID" in df.columns

    def test_merges_multiple_sources(self, multi_source_dataframes):
        df = _merge_dataframes(multi_source_dataframes, "Subject")
        # 3 + 2 = 5 rows (duplicates are kept in the merged DF)
        assert len(df) == 5

    def test_empty_dict_raises(self, empty_dataframes):
        with pytest.raises(ValueError, match="No source DataFrames provided"):
            _merge_dataframes(empty_dataframes, "Image")

    def test_missing_rid_column_raises(self, sample_dataframes):
        with pytest.raises(KeyError, match="WrongTable.RID"):
            _merge_dataframes(sample_dataframes, "WrongTable")

    def test_missing_rid_column_lists_available(self, sample_dataframes):
        with pytest.raises(KeyError, match="Image.RID"):
            _merge_dataframes(sample_dataframes, "WrongTable")

    def test_zero_rows_succeeds(self, empty_rows_dataframes):
        df = _merge_dataframes(empty_rows_dataframes, "Image")
        assert len(df) == 0


class TestExtractRids:
    """Tests for _extract_rids helper."""

    def test_extracts_unique_rids(self, sample_df):
        rids = _extract_rids(sample_df, "Image")
        assert len(rids) == 5
        assert set(rids) == {"1-AA", "1-BB", "1-CC", "1-DD", "1-EE"}

    def test_deduplicates(self):
        df = pd.DataFrame({"T.RID": ["A", "A", "B", "B", "B"]})
        rids = _extract_rids(df, "T")
        assert sorted(rids) == ["A", "B"]


class TestValidateColumn:
    """Tests for _validate_column helper."""

    def test_valid_column_passes(self, sample_df):
        _validate_column(sample_df, "Image_Classification.Label")

    def test_invalid_column_raises(self, sample_df):
        with pytest.raises(KeyError, match="Nonexistent"):
            _validate_column(sample_df, "Nonexistent")

    def test_error_lists_available_columns(self, sample_df):
        with pytest.raises(KeyError, match="Image.Filename"):
            _validate_column(sample_df, "Nonexistent")


# =============================================================================
# all_records filter
# =============================================================================


class TestAllRecords:
    """Tests for the all_records filter."""

    def test_returns_all_rids(self, sample_dataframes):
        rids, desc = all_records(sample_dataframes, element_table="Image")
        assert len(rids) == 5
        assert "1-AA" in rids

    def test_description(self, sample_dataframes):
        _, desc = all_records(sample_dataframes, element_table="Image")
        assert "5" in desc
        assert "Image" in desc

    def test_deduplicates_across_sources(self, multi_source_dataframes):
        rids, _ = all_records(multi_source_dataframes, element_table="Subject")
        # 2-YY appears in both sources but should only appear once
        assert len(rids) == 4
        assert sorted(rids) == ["2-WW", "2-XX", "2-YY", "2-ZZ"]

    def test_empty_dict_raises(self, empty_dataframes):
        with pytest.raises(ValueError):
            all_records(empty_dataframes, element_table="Image")

    def test_zero_rows_returns_empty(self, empty_rows_dataframes):
        rids, desc = all_records(empty_rows_dataframes, element_table="Image")
        assert rids == []
        assert "0" in desc


# =============================================================================
# has_feature filter
# =============================================================================


class TestHasFeature:
    """Tests for the has_feature filter."""

    def test_selects_non_null(self, sample_dataframes):
        rids, _ = has_feature(
            sample_dataframes, element_table="Image",
            column="Image_Classification.Label",
        )
        # Cat, Dog, Cat, Bird are non-null; one row has None
        assert len(rids) == 4
        assert "1-CC" not in rids  # the None row

    def test_description_includes_counts(self, sample_dataframes):
        _, desc = has_feature(
            sample_dataframes, element_table="Image",
            column="Image_Classification.Label",
        )
        assert "4 of 5" in desc

    def test_all_null_returns_empty(self):
        df = pd.DataFrame({
            "Image.RID": ["1-A", "1-B"],
            "Feature.Val": [None, None],
        })
        rids, _ = has_feature({"ds": df}, element_table="Image", column="Feature.Val")
        assert rids == []

    def test_missing_column_raises(self, sample_dataframes):
        with pytest.raises(KeyError, match="Bad.Column"):
            has_feature(sample_dataframes, element_table="Image", column="Bad.Column")

    def test_empty_dict_raises(self, empty_dataframes):
        with pytest.raises(ValueError):
            has_feature(empty_dataframes, element_table="Image", column="x")


# =============================================================================
# feature_equals filter
# =============================================================================


class TestFeatureEquals:
    """Tests for the feature_equals filter."""

    def test_exact_match(self, sample_dataframes):
        rids, _ = feature_equals(
            sample_dataframes, element_table="Image",
            column="Image_Classification.Label", value="Cat",
        )
        assert sorted(rids) == ["1-AA", "1-DD"]

    def test_no_match_returns_empty(self, sample_dataframes):
        rids, _ = feature_equals(
            sample_dataframes, element_table="Image",
            column="Image_Classification.Label", value="Fish",
        )
        assert rids == []

    def test_case_sensitive(self, sample_dataframes):
        rids, _ = feature_equals(
            sample_dataframes, element_table="Image",
            column="Image_Classification.Label", value="cat",  # lowercase
        )
        assert rids == []

    def test_description(self, sample_dataframes):
        _, desc = feature_equals(
            sample_dataframes, element_table="Image",
            column="Image_Classification.Label", value="Dog",
        )
        assert "Dog" in desc

    def test_missing_column_raises(self, sample_dataframes):
        with pytest.raises(KeyError):
            feature_equals(
                sample_dataframes, element_table="Image",
                column="Nope", value="x",
            )


# =============================================================================
# feature_in filter
# =============================================================================


class TestFeatureIn:
    """Tests for the feature_in filter."""

    def test_matches_values(self, sample_dataframes):
        rids, _ = feature_in(
            sample_dataframes, element_table="Image",
            column="Image_Classification.Label", values=["Cat", "Dog"],
        )
        assert sorted(rids) == ["1-AA", "1-BB", "1-DD"]

    def test_empty_values_returns_empty(self, sample_dataframes):
        rids, _ = feature_in(
            sample_dataframes, element_table="Image",
            column="Image_Classification.Label", values=[],
        )
        assert rids == []

    def test_single_value(self, sample_dataframes):
        rids, _ = feature_in(
            sample_dataframes, element_table="Image",
            column="Image_Classification.Label", values=["Bird"],
        )
        assert rids == ["1-EE"]

    def test_description_truncates_long_list(self, sample_dataframes):
        long_values = [f"val_{i}" for i in range(20)]
        _, desc = feature_in(
            sample_dataframes, element_table="Image",
            column="Image_Classification.Label", values=long_values,
        )
        assert "..." in desc
        assert "20 total" in desc

    def test_description_short_list(self, sample_dataframes):
        _, desc = feature_in(
            sample_dataframes, element_table="Image",
            column="Image_Classification.Label", values=["Cat", "Dog"],
        )
        assert "..." not in desc

    def test_missing_column_raises(self, sample_dataframes):
        with pytest.raises(KeyError):
            feature_in(
                sample_dataframes, element_table="Image",
                column="Nope", values=["x"],
            )


# =============================================================================
# numeric_range filter
# =============================================================================


class TestNumericRange:
    """Tests for the numeric_range filter."""

    def test_both_bounds(self, sample_dataframes):
        rids, _ = numeric_range(
            sample_dataframes, element_table="Image",
            column="Image_Classification.Confidence",
            min_val=0.75, max_val=0.96,
        )
        # 0.95, 0.80 match; 0.70 too low; 0.99 too high; None excluded
        assert sorted(rids) == ["1-AA", "1-BB"]

    def test_min_only(self, sample_dataframes):
        rids, _ = numeric_range(
            sample_dataframes, element_table="Image",
            column="Image_Classification.Confidence",
            min_val=0.90,
        )
        assert sorted(rids) == ["1-AA", "1-EE"]

    def test_max_only(self, sample_dataframes):
        rids, _ = numeric_range(
            sample_dataframes, element_table="Image",
            column="Image_Classification.Confidence",
            max_val=0.75,
        )
        assert rids == ["1-DD"]

    def test_no_bounds_raises(self, sample_dataframes):
        with pytest.raises(ValueError, match="at least one of min_val or max_val"):
            numeric_range(
                sample_dataframes, element_table="Image",
                column="Image_Classification.Confidence",
            )

    def test_non_numeric_column_raises(self, sample_dataframes):
        with pytest.raises(TypeError, match="expected a numeric type"):
            numeric_range(
                sample_dataframes, element_table="Image",
                column="Image_Classification.Label",
                min_val=0.5,
            )

    def test_excludes_null_values(self, sample_dataframes):
        rids, _ = numeric_range(
            sample_dataframes, element_table="Image",
            column="Image_Classification.Confidence",
            min_val=0.0,
        )
        # 1-CC has None confidence — should be excluded
        assert "1-CC" not in rids
        assert len(rids) == 4

    def test_no_matches_returns_empty(self, sample_dataframes):
        rids, _ = numeric_range(
            sample_dataframes, element_table="Image",
            column="Image_Classification.Confidence",
            min_val=1.0,
        )
        assert rids == []

    def test_description_includes_bounds(self, sample_dataframes):
        _, desc = numeric_range(
            sample_dataframes, element_table="Image",
            column="Image_Classification.Confidence",
            min_val=0.5, max_val=0.9,
        )
        assert ">= 0.5" in desc
        assert "<= 0.9" in desc

    def test_missing_column_raises(self, sample_dataframes):
        with pytest.raises(KeyError):
            numeric_range(
                sample_dataframes, element_table="Image",
                column="Nope", min_val=0.0,
            )

    def test_empty_dict_raises(self, empty_dataframes):
        with pytest.raises(ValueError):
            numeric_range(
                empty_dataframes, element_table="Image",
                column="x", min_val=0.0,
            )
