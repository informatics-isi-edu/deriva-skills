"""Shared test fixtures for dataset-lifecycle skill tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

# Add the skill scripts directory to sys.path so we can import subset_filters
# without needing a package install.
SKILL_SCRIPTS_DIR = Path(__file__).parent.parent / "skills" / "dataset-lifecycle" / "scripts"
sys.path.insert(0, str(SKILL_SCRIPTS_DIR))


@pytest.fixture
def sample_df() -> pd.DataFrame:
    """A simple DataFrame simulating denormalized dataset output.

    Columns use the {Table}.{Column} naming convention from DerivaML's
    denormalize_as_dataframe().
    """
    return pd.DataFrame({
        "Image.RID": ["1-AA", "1-BB", "1-CC", "1-DD", "1-EE"],
        "Image.Filename": ["a.png", "b.png", "c.png", "d.png", "e.png"],
        "Image_Classification.Label": ["Cat", "Dog", None, "Cat", "Bird"],
        "Image_Classification.Confidence": [0.95, 0.80, None, 0.70, 0.99],
    })


@pytest.fixture
def sample_dataframes(sample_df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Wrap sample_df as a single-source dataframes dict (keyed by RID)."""
    return {"DS-001": sample_df}


@pytest.fixture
def multi_source_dataframes() -> dict[str, pd.DataFrame]:
    """Two source DataFrames with overlapping RIDs to test deduplication."""
    df1 = pd.DataFrame({
        "Subject.RID": ["2-XX", "2-YY", "2-ZZ"],
        "Subject.Name": ["Alice", "Bob", "Carol"],
        "Subject.Score": [85.0, 92.0, 78.0],
    })
    df2 = pd.DataFrame({
        "Subject.RID": ["2-YY", "2-WW"],
        "Subject.Name": ["Bob", "Dave"],
        "Subject.Score": [92.0, 65.0],
    })
    return {"DS-A": df1, "DS-B": df2}


@pytest.fixture
def empty_dataframes() -> dict[str, pd.DataFrame]:
    """An empty dict — no source DataFrames."""
    return {}


@pytest.fixture
def empty_rows_dataframes() -> dict[str, pd.DataFrame]:
    """A DataFrame with columns but zero rows."""
    df = pd.DataFrame({
        "Image.RID": pd.Series([], dtype="str"),
        "Image.Filename": pd.Series([], dtype="str"),
    })
    return {"DS-EMPTY": df}
