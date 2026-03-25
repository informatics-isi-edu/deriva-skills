"""Template: Dataset subset generation function.

The skill copies this template and customizes the filter for each use case.
Placeholders marked with {{PLACEHOLDER}} are replaced by the skill.

Run via:
    uv run deriva-ml-run +experiment={{EXPERIMENT_NAME}} dry_run=true
    uv run deriva-ml-run +experiment={{EXPERIMENT_NAME}}
"""

from __future__ import annotations

from deriva_ml import DerivaML
from deriva_ml.execution import Execution

from models.subset_filters import FILTER_REGISTRY


def {{FUNCTION_NAME}}(
    # Source datasets
    source_dataset_rids: list[str] | None = None,
    source_version: str | None = None,
    # Denormalization
    include_tables: list[str] | None = None,
    element_table: str = "Image",
    # Filter
    filter_name: str = "",
    filter_params: dict | None = None,
    # Output dataset
    output_description: str = "",
    output_types: list[str] | None = None,
    # DerivaML integration (injected by framework)
    ml_instance: DerivaML = None,
    execution: Execution | None = None,
) -> None:
    """Create a dataset subset by filtering denormalized source datasets.

    Downloads metadata-only bags (no asset files) for each source dataset,
    denormalizes them into DataFrames, applies the named filter, and creates
    a new dataset with the selected RIDs.
    """
    source_dataset_rids = source_dataset_rids or []
    include_tables = include_tables or []
    filter_params = filter_params or {}
    output_types = output_types or []

    if filter_name not in FILTER_REGISTRY:
        available = ", ".join(FILTER_REGISTRY.keys())
        raise ValueError(f"Unknown filter '{filter_name}'. Available: {available}")

    # Download and denormalize each source dataset
    dataframes: dict[str, object] = {}
    for rid in source_dataset_rids:
        dataset = ml_instance.lookup_dataset(rid)
        version = source_version or dataset.current_version
        print(f"Source: {dataset.description} (RID: {rid}, version: {version})")

        bag = dataset.download_dataset_bag(version=version, materialize=False)
        df = bag.denormalize_as_dataframe(include_tables)
        print(f"  Denormalized: {len(df)} rows, {len(df.columns)} columns")
        dataframes[rid] = df

    # Apply the filter
    filter_fn = FILTER_REGISTRY[filter_name]
    rids, selection_desc = filter_fn(
        dataframes, element_table=element_table, **filter_params
    )
    print(f"\n{selection_desc}")

    if execution is None:
        print(f"\n[DRY RUN] Would create dataset with {len(rids)} members")
        print(f"  Description: {output_description}")
        print(f"  Types: {output_types}")
        return

    # Create the new dataset
    new_dataset = execution.create_dataset(
        description=output_description,
        dataset_types=output_types,
    )

    new_dataset.add_dataset_members(
        members=rids,
        description=selection_desc,
    )

    print(f"\nCreated dataset: {new_dataset.dataset_rid}")
    print(f"  Description: {output_description}")
    print(f"  Types: {output_types}")
    print(f"  Members: {len(rids)}")
    print(f"  Version: {new_dataset.current_version}")
