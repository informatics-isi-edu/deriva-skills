# Querying and Exploring Data in a Deriva Catalog

This guide covers how to query, filter, and explore data in a Deriva catalog using the `deriva-mcp-core` MCP tools and resources.

## Understanding the Schema

Before querying, understand what tables and columns are available.

### Start with RAG Search (Preferred)

**Always use `rag_search` first** for discovery and exploration. It indexes the catalog schema (tables, columns, FKs, vocabulary terms) and returns focused results without flooding context:

```python
# What tables and features exist?
rag_search("Image tables and features", doc_type="catalog-schema")

# What vocabulary terms are available?
rag_search("classification categories", doc_type="catalog-schema")

# What datasets exist? (tier-2; requires deriva-ml-mcp loaded)
rag_search("training labeled dataset", doc_type="catalog-data")
```

RAG search avoids dumping large schema JSON into context and finds relevant results semantically.

### Raw Schema Tools (When You Need Complete Output)

Only use these when RAG results are insufficient or you need the full machine-readable schema:

```python
# All tables in the catalog
catalog_tables(hostname="data.example.org", catalog_id="1")

# Full schema overview
get_schema(hostname="data.example.org", catalog_id="1")

# One specific table's complete structure
get_table(
    hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Subject",
)
```

### Sample Rows

Use `get_table_sample_data` to preview a few rows from a table:

```python
get_table_sample_data(
    hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Subject",
)
```

## Simple Queries

### Query All Rows

Use `query_attribute` (the new replacement for the legacy `preview_table`):

```python
query_attribute(
    hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Subject",
)
```

This returns all rows. For large tables, use `limit` and `offset` for pagination.

### Specific Columns

```python
query_attribute(
    hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Subject",
    attributes=["RID", "Name", "Species"],
)
```

### Limit Results

```python
query_attribute(
    hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Subject",
    limit=10,
)
```

### Paginate Through Results

```python
query_attribute(..., schema="myproject", table="Subject", limit=100, offset=0)    # First 100
query_attribute(..., schema="myproject", table="Subject", limit=100, offset=100)  # Next 100
query_attribute(..., schema="myproject", table="Subject", limit=100, offset=200)  # Next 100
```

## Filter Queries

### Equality Filter

```python
query_attribute(
    hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Subject",
    filter={"Species": "Mouse"},
)
```

### Multiple AND Conditions

```python
query_attribute(
    hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Subject",
    filter={"Species": "Mouse", "Status": "Active"},
)
```

This returns rows where Species is "Mouse" AND Status is "Active".

### Count Rows

Use `count_table` for fast counting without fetching data:

```python
# Total rows
count_table(
    hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Subject",
)

# Filtered count
count_table(
    hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Subject",
    filter={"Species": "Mouse"},
)
```

## Get Specific Records

### By RID

The new MCP surface does not have a dedicated `get_record` tool. Use `get_entities` with a RID filter:

```python
get_entities(
    hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Subject",
    filter={"RID": "2-B4C8"},
)
```

This returns the record (as a single-element list) or an empty list if the RID does not exist in that table.

### Validate Known RIDs

The new surface does not have a `validate_rids` tool. Validate by attempting `get_entities` per candidate table; an empty result means the RID does not exist there:

```python
result = get_entities(
    hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Subject",
    filter={"RID": "2-B4C8"},
)
exists = bool(result)
```

For ML-domain RIDs (Datasets, Workflows, Executions, Features, Assets), the tier-2 `deriva-ml-mcp` plugin provides typed get tools (`deriva_ml_get_dataset`, `deriva_ml_get_execution`, etc.) that return `None` cleanly when the RID doesn't exist; prefer those when you have `deriva-ml-skills` installed.

## Aggregations

For COUNT, SUM, AVG, MIN, MAX queries, use `query_aggregate`:

```python
query_aggregate(
    hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Image",
    group_by=["Subject.Species"],
    aggregates={"image_count": "COUNT(*)"},
    filter={"QC_Status": "Pass"},
)
```

## Vocabulary Lookups

Deriva uses controlled vocabularies for categorical values. Look them up via the dedicated vocabulary tools:

```python
# All terms in a vocabulary
list_vocabulary_terms(
    hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Species",
)

# Look up a specific term (synonym-aware — finds "X-ray" via the synonym "Xray")
lookup_term(
    hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Species", name="Mouse",
)
```

For vocabulary management (creating new vocabularies, adding terms, managing synonyms), see the `manage-vocabulary` skill.

## Querying Related Data

### Cross-Table Filters via FK Path

`query_attribute` supports filtering on related tables via FK paths:

```python
# Images for a specific subject
query_attribute(
    hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Image",
    filter={"Subject": "2-A1B2"},
)
```

For multi-table denormalized views (joining Image + Subject + Diagnosis into one wide table), use the **tier-2 `deriva-ml-mcp`** tool `deriva_ml_denormalize_dataset` (requires `deriva-ml-skills` installed). The `deriva-mcp-core` surface deliberately does not include denormalization — that's a DerivaML-specific concept.

## Common Query Patterns

### Find Images for a Subject

```python
query_attribute(
    hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Image",
    filter={"Subject": "2-A1B2"},
)
```

### Find Records by Multiple FKs

```python
query_attribute(
    hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Image",
    filter={"Subject": "2-A1B2", "Modality": "MRI"},
)
```

### Date Range Queries

Deriva supports date filtering. Use ISO 8601 format:

```python
query_attribute(
    hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Sample",
    filter={"Collected_Date__after__": "2024-01-01"},
)
```

(Range operators are encoded as suffixes on the filter key; consult the `query_attribute` tool docstring for the full list of supported operators.)

## Complete Example Workflow

A typical workflow for exploring and extracting data from a catalog:

1. **Orient yourself**: `rag_search("what tables and features exist", doc_type="catalog-schema")` to discover the catalog structure. Fall back to `catalog_tables(...)` only if RAG doesn't answer your question.

2. **Explore a table**: `rag_search("Subject columns and relationships", doc_type="catalog-schema")` to understand columns, then `get_table_sample_data(..., schema="myproject", table="Subject")` for sample rows.

3. **Count records**: `count_table(..., schema="myproject", table="Subject")` and `count_table(..., schema="myproject", table="Subject", filter={"Species": "Mouse"})`.

4. **Query with filters**: `query_attribute(..., schema="myproject", table="Subject", filter={"Species": "Mouse"}, limit=50)`.

5. **Inspect a specific record**: `get_entities(..., schema="myproject", table="Subject", filter={"RID": "2-A1B2"})`.

6. **Find related data**: `query_attribute(..., schema="myproject", table="Image", filter={"Subject": "2-A1B2"})`.

7. **For dataset / ML workflows**: switch to the tier-2 `dataset-lifecycle` skill in `deriva-ml-skills` — datasets, denormalization, bag downloads, version pinning all live in `deriva-ml-mcp`.

## Tips and Troubleshooting

- **Schema names are mandatory**: every tool that operates on a table needs `schema=` AND `table=`. There is no `set_default_schema` in the new surface.
- **Large tables**: always use `limit` and `offset` for tables with more than a few hundred rows. Fetching the entire table can be slow and may time out.
- **Column names are case-sensitive**: use the exact column names from the schema. `"Species"` is not the same as `"species"`.
- **RID format**: RIDs look like `2-B4C8` (a number, a dash, and an alphanumeric string). They are unique within a catalog.
- **Foreign keys**: many columns contain RIDs referencing other tables. For ML-domain denormalization (resolving FK chains into readable values), use the tier-2 `deriva_ml_denormalize_dataset` tool. For one-off FK lookups, use `get_entities` on the referenced table.
- **Empty results**: if a query returns no rows, double-check the filter values. Use `query_attribute` without filters first to verify the table has data, then add filters incrementally.
- **Schema mismatch**: if a table is not found, verify you are using the correct `schema=` argument. The MCP server's response includes a `suggestions` field with "did you mean?" candidates if the name is misspelled.
- **Stale data**: catalog data can change. For ML reproducibility, use versioned datasets (tier-2 `deriva-ml-skills`).
