# Querying and Exploring Data in a Deriva Catalog

This skill covers how to query, filter, and explore data stored in a Deriva catalog using MCP tools and resources.

## Understanding the Schema

Before querying, understand what tables and columns are available.

### Start with RAG Search (Preferred)

**Always use `rag_search` first** for discovery and exploration. It indexes the catalog schema (tables, columns, FKs, features, vocabulary terms) and returns focused results:

```
# What tables and features exist?
rag_search("Image tables and features", doc_type="catalog-schema")

# What vocabulary terms are available?
rag_search("classification categories", doc_type="catalog-schema")

# What datasets exist?
rag_search("training labeled dataset", doc_type="catalog-data")
```

RAG search avoids dumping large schema JSON into context and finds relevant results semantically.

### Raw Resources (When You Need Complete Output)

Only use these when RAG results are insufficient or you need the full machine-readable schema:

- `deriva://catalog/tables` -- Lists all tables in the current schema with descriptions and row counts.
- `deriva://catalog/schema` -- Full schema overview with table relationships (can be very large).

### Table-Level Details

For a specific table:

- `deriva://table/{table_name}/schema` -- Column names, types, nullability, and descriptions.
- Or use RAG: `rag_search("Image columns and types", doc_type="catalog-schema")`

Use `get_table_sample_data(table_name="...")` to preview sample rows.

## Simple Queries

### Query All Rows

Use the `preview_table` MCP tool:

```
preview_table(table_name="Subject")
```

This returns all rows. For large tables, use `limit` and `offset` for pagination.

### Specific Columns

```
preview_table(table_name="Subject", columns=["RID", "Name", "Species"])
```

### Limit Results

```
preview_table(table_name="Subject", limit=10)
```

### Paginate Through Results

```
preview_table(table_name="Subject", limit=100, offset=0)    # First 100
preview_table(table_name="Subject", limit=100, offset=100)   # Next 100
preview_table(table_name="Subject", limit=100, offset=200)   # Next 100
```

## Filter Queries

### Equality Filter

```
preview_table(table_name="Subject", filters={"Species": "Mouse"})
```

### Multiple AND Conditions

```
preview_table(
    table_name="Subject",
    filters={"Species": "Mouse", "Status": "Active"}
)
```

This returns rows where Species is "Mouse" AND Status is "Active".

### Count Rows

Use the `preview_table` (with limit=1) MCP tool to get the number of matching rows without fetching data:

```
preview_table(table_name="Subject")
preview_table(table_name="Subject", filters={"Species": "Mouse"})
```

## Get Specific Records

### By RID

Use the `get_record` MCP tool to fetch a single record by its RID (Row ID):

```
get_record(table_name="Subject", rid="2-B4C8")
```

This returns the complete record with all columns.

### Validate Known RIDs

Use `validate_rids` to check that dataset, asset, workflow, or execution RIDs exist before using them:

```
validate_rids(dataset_rids=["2-B4C8"], asset_rids=["2-D1E2"])
```

To resolve an unknown RID to its table, read the `deriva://rid/{rid}` resource instead.

## Query Related Data

### Denormalize for ML

Use the `preview_denormalized_dataset` MCP tool to explore denormalized table shapes and get ML-ready joined data. The `dataset_rid` is optional — omit it to explore the schema without needing a dataset:

```
# Schema shape + global row counts (no dataset needed)
preview_denormalized_dataset(include_tables=["Image", "Subject"])

# Dataset-scoped info (no rows)
preview_denormalized_dataset(include_tables=["Image", "Subject"], dataset_rid="2-B4C8")

# Dataset-scoped info + actual rows
preview_denormalized_dataset(include_tables=["Image", "Subject"], dataset_rid="2-B4C8", limit=50)
```

The tool always returns column names/types, the join path, and per-table row counts and asset size estimates. When `limit > 0` and a dataset RID is provided, it also returns actual row data. Denormalize follows multi-hop FK chains automatically — tables don't need to be explicit dataset members. If ambiguous FK paths exist between tables, add intermediate tables to `include_tables` to disambiguate.

### Exploring Schema Shape Before Denormalizing

Call `preview_denormalized_dataset` with just `include_tables` (no dataset RID) to see the schema shape — useful for debugging FK paths, finding column names for stratification, or estimating data sizes:

```
preview_denormalized_dataset(include_tables=["Image", "Subject"])
```

Returns columns, join path, per-table row counts, and asset size estimates. Use this when:
- You need the correct column name for `stratify_by_column` in `split_dataset`
- You want to verify FK paths resolve before running an expensive query
- You hit an ambiguous FK path error and want to iterate quickly
- You want to estimate how much data a denormalization would produce

### Query a Single Table

For simpler needs, `preview_table` on the relevant table is sufficient:

```
preview_table(table_name="Image", filters={"Subject": "2-A1B2"})
```

### Download a Full Dataset

Use the Python API `dataset.download_dataset_bag(version)` MCP tool to get a complete local copy of a dataset:

```
download_dataset(dataset_rid="2-B4C8", version="3")
```

This downloads all dataset members and assets to a local directory.

## Vocabulary Lookups

Deriva uses controlled vocabularies for categorical values. Look them up via MCP resources:

- `deriva://vocabulary/{vocab_name}` -- Lists all terms in a vocabulary with descriptions.
- `deriva://vocabulary/{vocab_name}/{term}` -- Details for a specific term.

Common vocabularies include dataset types, workflow types, species, and status values.

Use `preview_table` to query vocabulary tables directly:

```
preview_table(table_name="Species")
preview_table(table_name="Dataset_Type")
```

## Feature Queries

Features in DerivaML represent measured or computed properties of entities.

### Discover Features

Use RAG search first to find features by meaning:

```
rag_search("diagnosis labels and confidence", doc_type="catalog-schema")
rag_search("what features exist on Image", doc_type="catalog-schema")
```

For the complete feature list on a specific table, read the MCP resource:

- `deriva://table/{table_name}/features` -- Lists all features associated with a table.

### Feature Structure

Features have:
- A **feature name** (e.g., "Cell_Count", "Mean_Intensity").
- A **feature table** that stores the values.
- An **association** to a base table (e.g., Image, Subject).

### Query Feature Values

Use `preview_table` on the feature table:

```
preview_table(table_name="Image_Cell_Count")
```

Or use the `get_table_sample_data` MCP tool for a quick preview:

```
get_table_sample_data(table_name="Image_Cell_Count")
```

## Common Query Patterns

### Find Images for a Subject

```
preview_table(table_name="Image", filters={"Subject": "2-A1B2"})
```

### Find All Subjects in a Dataset

First get the dataset members:
```
resource deriva://dataset/{rid}/members (dataset_rid="2-B4C8")
```

### Date Range Queries

Deriva supports date filtering. Use ISO 8601 format:

```
preview_table(
    table_name="Execution",
    filters={"Status": "Complete"},
    limit=20
)
```

Note: `preview_table` does not support a `sort` parameter. For sorted or complex date range queries, filter results client-side or use the ERMrest API directly.

### Export Data for ML

To get data ready for ML training:

1. **Identify the dataset**: `get_record(table_name="Dataset", rid="2-B4C8")`
2. **Get the members**: `resource deriva://dataset/{rid}/members (dataset_rid="2-B4C8")`
3. **Explore shape**: `preview_denormalized_dataset(include_tables=["Image", "Subject"])`, then add `dataset_rid="2-B4C8", limit=50` for data
4. **Download assets**: `download_dataset(dataset_rid="2-B4C8", version="3")`

## Historical Queries with Versions

Datasets in Deriva can be versioned. Query specific versions:

```
download_dataset(dataset_rid="2-B4C8", version="3")
```

To see available versions, read:

- `deriva://dataset/{rid}` -- Includes version history.

Always pin to a specific version for reproducible experiments.

## View in Web Interface

To get the Chaise (web UI) URL for any record, use the MCP resource:

- `deriva://chaise-url/{table_or_rid}` -- Pass a table name for the record set view, or a RID for a specific record.

These URLs are useful for sharing records with collaborators or viewing complex relationships that are easier to navigate in the web interface.

## Complete Example Workflow

Here is a typical workflow for exploring and extracting data from a catalog:

1. **Orient yourself**: Use `rag_search("what tables and features exist", doc_type="catalog-schema")` to discover the catalog structure. Only fall back to `deriva://catalog/tables` if RAG doesn't answer your question.

2. **Explore a table**: Use `rag_search("Subject columns and relationships", doc_type="catalog-schema")` to understand columns, then `get_table_sample_data(table_name="Subject")` for sample rows.

3. **Count records**: `preview_table(table_name="Subject")` and `preview_table(table_name="Subject", filters={"Species": "Mouse"})`.

4. **Query with filters**: `preview_table(table_name="Subject", filters={"Species": "Mouse"}, limit=50)`.

5. **Inspect a specific record**: `get_record(table_name="Subject", rid="2-A1B2")`.

6. **Find related data**: `preview_table(table_name="Image", filters={"Subject": "2-A1B2"})`.

7. **Check features**: Read `deriva://table/Image/features`, then `preview_table(table_name="Image_Cell_Count", filters={"Image": "2-C3D4"})`.

8. **Get dataset for ML**: `preview_denormalized_dataset(include_tables=["Image", "Subject"])` to explore the schema shape, then add `dataset_rid="2-B4C8", limit=50` for actual data. Or `download_dataset(dataset_rid="2-B4C8", version="3")` for a full local copy.

9. **Share with a colleague**: Read `deriva://chaise-url/2-A1B2` to get a shareable URL for a specific record, or `deriva://chaise-url/Subject` for the table view.

## Asset Provenance

Every asset can be traced back to the execution(s) that produced or consumed it:

```
# Find executions that created or used an asset
list_asset_executions(asset_rid="2-IMG1")
# Returns executions with role "Output" (created it) or "Input" (consumed it)

# Look up a specific asset by RID
get_record(table_name="Slide_Image", rid="2-IMG1")

# Download a specific asset
download_asset(asset_rid="2-IMG1")
```

## Tips and Troubleshooting

- **Large tables**: Always use `limit` and `offset` for tables with more than a few hundred rows. Fetching the entire table can be slow and may time out.
- **Column names are case-sensitive**: Use the exact column names from the schema. `"Species"` is not the same as `"species"`.
- **RID format**: RIDs look like `2-B4C8` (a number, a dash, and an alphanumeric string). They are unique within a catalog.
- **Foreign keys**: Many columns contain RIDs referencing other tables. Use `preview_denormalized_dataset(include_tables=[...])` to resolve these into readable values (no dataset RID needed for schema exploration), or `get_record` to look up individual references.
- **Empty results**: If a query returns no rows, double-check the filter values. Use `preview_table` without filters first to verify the table has data, then add filters incrementally.
- **Schema mismatch**: If a table is not found, verify you are connected to the correct schema. Use `set_default_schema` if needed.
- **Stale data**: Catalog data can change. If you need a stable snapshot, use versioned datasets.
