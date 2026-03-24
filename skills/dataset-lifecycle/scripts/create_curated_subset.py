"""Create a curated dataset subset by filtering a denormalized source dataset.

This is a reusable script template for the common workflow:
  1. Denormalize a source dataset (join element tables with features)
  2. Apply filter criteria to select a subset of records
  3. Create a new dataset containing only the selected records

The filter strategy is parameterized — edit the CONFIGURATION section below
to match your use case. Common strategies are provided as examples.

Usage:
    # Preview what would be created (dry run)
    uv run python scripts/create_curated_subset.py --dry-run

    # Create the dataset for real
    uv run python scripts/create_curated_subset.py

Provenance: Commit this script before running so the execution record
captures the git hash. See the catalog-operations-workflow skill.
"""

import argparse
from collections import Counter

from deriva_ml import DerivaML, ExecutionConfiguration

# ============================================================================
# CONFIGURATION — Edit this section for your use case
# ============================================================================

HOSTNAME = "localhost"
CATALOG_ID = "cifar10"

# Source dataset to filter from
SOURCE_DATASET_RID = "28J0"  # e.g., small training set
SOURCE_VERSION = None  # None = current version

# Tables to include in the denormalized view.
# Must include the element table and any feature/related tables needed for filtering.
INCLUDE_TABLES = ["Image", "Execution_Image_Image_Classification"]

# The element table whose RIDs will be collected for the new dataset
ELEMENT_TABLE = "Image"

# New dataset metadata
DATASET_DESCRIPTION = "Top 2 most frequent classes from small training set"
DATASET_TYPES = ["Training", "Labeled"]

# Execution metadata
WORKFLOW_NAME = "Curated Subset Creation"
WORKFLOW_TYPE = "Data Management"


# ============================================================================
# FILTER STRATEGY — Choose one or write your own
# ============================================================================

def filter_records(df):
    """Filter the denormalized DataFrame and return selected element RIDs.

    The DataFrame has columns prefixed by table name with dots, e.g.:
      - Image.RID, Image.Filename, Image.URL
      - Execution_Image_Image_Classification.Image_Class

    Returns:
        tuple: (list of selected RIDs, description of what was selected)
    """
    # --- Strategy: Top-N classes by frequency ---
    class_column = "Execution_Image_Image_Classification.Image_Class"
    n = 2

    counts = Counter(df[class_column])
    top_classes = [cls for cls, _ in counts.most_common(n)]
    selected = df[df[class_column].isin(top_classes)]
    rids = selected[f"{ELEMENT_TABLE}.RID"].unique().tolist()

    desc = (
        f"Selected {len(rids)} images from top {n} classes: "
        f"{', '.join(top_classes)} "
        f"(counts: {', '.join(f'{c}={counts[c]}' for c in top_classes)})"
    )
    return rids, desc

    # --- Strategy: Filter by specific values ---
    # class_column = "Execution_Image_Image_Classification.Image_Class"
    # target_values = ["cat", "dog"]
    # selected = df[df[class_column].isin(target_values)]
    # rids = selected[f"{ELEMENT_TABLE}.RID"].unique().tolist()
    # desc = f"Selected {len(rids)} images with classes: {', '.join(target_values)}"
    # return rids, desc

    # --- Strategy: Numeric range ---
    # value_column = "Execution_Image_Image_Classification.Confidence"
    # selected = df[df[value_column] > 0.8]
    # rids = selected[f"{ELEMENT_TABLE}.RID"].unique().tolist()
    # desc = f"Selected {len(rids)} images with confidence > 0.8"
    # return rids, desc

    # --- Strategy: Custom predicate ---
    # selected = df[
    #     (df["Image.Length"] > 2000) &
    #     (df["Execution_Image_Image_Classification.Image_Class"] == "cat")
    # ]
    # rids = selected[f"{ELEMENT_TABLE}.RID"].unique().tolist()
    # desc = f"Selected {len(rids)} large cat images"
    # return rids, desc


# ============================================================================
# EXECUTION — No need to edit below this line
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Create a curated dataset subset")
    parser.add_argument("--dry-run", action="store_true", help="Preview without creating")
    args = parser.parse_args()

    ml = DerivaML(HOSTNAME, CATALOG_ID)

    # Denormalize the source dataset
    dataset = ml.lookup_dataset(SOURCE_DATASET_RID)
    print(f"Source dataset: {dataset.description} (RID: {SOURCE_DATASET_RID})")

    version = SOURCE_VERSION or dataset.current_version
    print(f"Denormalizing version {version} with tables: {INCLUDE_TABLES}")

    df = dataset.denormalize_as_dataframe(INCLUDE_TABLES, version=version)
    print(f"Denormalized: {len(df)} rows, {len(df.columns)} columns")
    print(f"Columns: {list(df.columns)}")

    # Apply the filter
    rids, selection_desc = filter_records(df)
    print(f"\n{selection_desc}")

    if args.dry_run:
        print(f"\n[DRY RUN] Would create dataset with {len(rids)} members")
        print(f"  Description: {DATASET_DESCRIPTION}")
        print(f"  Types: {DATASET_TYPES}")
        return

    # Create the dataset within an execution for provenance
    workflow = ml.create_workflow(
        name=WORKFLOW_NAME,
        workflow_type=WORKFLOW_TYPE,
        description=selection_desc,
    )

    config = ExecutionConfiguration(
        workflow=workflow,
        description=f"{DATASET_DESCRIPTION}\n\n{selection_desc}",
    )

    with ml.create_execution(config) as exe:
        new_dataset = exe.create_dataset(
            description=DATASET_DESCRIPTION,
            dataset_types=DATASET_TYPES,
        )

        new_dataset.add_dataset_members(
            members=rids,
            description=selection_desc,
        )

        print(f"\nCreated dataset: {new_dataset.dataset_rid}")
        print(f"  Description: {DATASET_DESCRIPTION}")
        print(f"  Types: {DATASET_TYPES}")
        print(f"  Members: {len(rids)}")
        print(f"  Version: {new_dataset.current_version}")


if __name__ == "__main__":
    main()
