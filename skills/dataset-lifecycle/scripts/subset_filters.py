"""Filter Registry for Dataset Subset Generation.

Provides common filter implementations for selecting records from
denormalized DataFrames. Each filter takes a dict of DataFrames
(keyed by source dataset RID) and returns selected RIDs with a
description of the selection.

Custom filters can be registered with @register_filter("name") and
referenced by name in hydra configs via filter_name parameter.

Built-in filters:
  - has_feature: Records that have a non-null value for a feature column
  - feature_equals: Records where a feature column matches a specific value
  - feature_in: Records where a feature column is in a list of values
  - numeric_range: Records where a numeric column is within bounds
"""

from __future__ import annotations

from typing import Protocol

import pandas as pd


class FilterFunction(Protocol):
    """Protocol for filter functions.

    Args:
        dataframes: Dict mapping source dataset RID to its denormalized DataFrame.
            For single-source subsets, this has one entry.
        element_table: Table whose RIDs are collected for the new dataset.
        **kwargs: Filter-specific parameters from filter_params config.

    Returns:
        Tuple of (list of selected RIDs, human-readable description of selection).
    """

    def __call__(
        self,
        dataframes: dict[str, pd.DataFrame],
        *,
        element_table: str,
        **kwargs,
    ) -> tuple[list[str], str]: ...


FILTER_REGISTRY: dict[str, FilterFunction] = {}


def register_filter(name: str):
    """Decorator to register a filter function by name."""
    def decorator(fn):
        FILTER_REGISTRY[name] = fn
        return fn
    return decorator


# =============================================================================
# Built-in filters
# =============================================================================


@register_filter("has_feature")
def has_feature(
    dataframes: dict[str, pd.DataFrame],
    *,
    element_table: str,
    column: str,
    **kwargs,
) -> tuple[list[str], str]:
    """Select records that have a non-null value for a feature column.

    Use this to build datasets of labeled records from a larger set that
    may contain unlabeled data. For example, selecting all images that
    have an Image_Class label.
    """
    df = pd.concat(dataframes.values(), ignore_index=True)
    selected = df[df[column].notna()]
    rids = selected[f"{element_table}.RID"].unique().tolist()

    total = df[f"{element_table}.RID"].nunique()
    desc = f"Selected {len(rids)} of {total} records that have a value for {column}"
    return rids, desc


@register_filter("feature_equals")
def feature_equals(
    dataframes: dict[str, pd.DataFrame],
    *,
    element_table: str,
    column: str,
    value: str,
    **kwargs,
) -> tuple[list[str], str]:
    """Select records where a feature column matches a specific value."""
    df = pd.concat(dataframes.values(), ignore_index=True)
    selected = df[df[column] == value]
    rids = selected[f"{element_table}.RID"].unique().tolist()

    desc = f"Selected {len(rids)} records where {column} = '{value}'"
    return rids, desc


@register_filter("feature_in")
def feature_in(
    dataframes: dict[str, pd.DataFrame],
    *,
    element_table: str,
    column: str,
    values: list[str],
    **kwargs,
) -> tuple[list[str], str]:
    """Select records where a feature column is in a list of values."""
    df = pd.concat(dataframes.values(), ignore_index=True)
    selected = df[df[column].isin(values)]
    rids = selected[f"{element_table}.RID"].unique().tolist()

    desc = f"Selected {len(rids)} records where {column} in: {', '.join(values)}"
    return rids, desc


@register_filter("numeric_range")
def numeric_range(
    dataframes: dict[str, pd.DataFrame],
    *,
    element_table: str,
    column: str,
    min_val: float | None = None,
    max_val: float | None = None,
    **kwargs,
) -> tuple[list[str], str]:
    """Select records where a numeric column is within bounds."""
    df = pd.concat(dataframes.values(), ignore_index=True)
    mask = df[column].notna()
    if min_val is not None:
        mask = mask & (df[column] >= min_val)
    if max_val is not None:
        mask = mask & (df[column] <= max_val)
    selected = df[mask]
    rids = selected[f"{element_table}.RID"].unique().tolist()

    bounds = []
    if min_val is not None:
        bounds.append(f">= {min_val}")
    if max_val is not None:
        bounds.append(f"<= {max_val}")
    desc = f"Selected {len(rids)} records where {column} {' and '.join(bounds)}"
    return rids, desc
