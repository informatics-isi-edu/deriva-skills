---
name: query-catalog-data
description: "ALWAYS use this skill when querying, filtering, searching, or browsing data in a Deriva catalog. Triggers on: 'query table', 'find records', 'filter by', 'how many records', 'look up RID', 'what tables exist', 'show me the data', 'explore the catalog', 'get record by RID', 'wide table', 'flat table', 'denormalize', 'join tables'."
disable-model-invocation: true
---

# Querying and Exploring Data in a Deriva Catalog

This skill covers how to find, filter, and explore data in a Deriva catalog using MCP tools and resources.


## Prerequisite: Connect to a Catalog

All operations in this skill require an active catalog connection. Before anything else:

```
connect_catalog(hostname="...", catalog_id="...")
```

If already connected (check `deriva://catalog/connections`), skip this step.


## Discovery: Start with RAG Search

**Always use `rag_search` first** for discovery and exploration questions — "what tables exist", "what features are available", "how are images classified", "what datasets are there". RAG search indexes the catalog schema, vocabulary terms, feature definitions, datasets, and executions, and returns focused, relevant results without flooding context.

| Query type | RAG call |
|------------|----------|
| Tables, columns, relationships | `rag_search("...", doc_type="catalog-schema")` |
| Feature definitions and columns | `rag_search("...", doc_type="catalog-schema")` |
| Vocabulary terms and meanings | `rag_search("...", doc_type="catalog-schema")` |
| Datasets by purpose or type | `rag_search("...", doc_type="catalog-data")` |
| Executions by workflow or status | `rag_search("...", doc_type="catalog-data")` |
| DerivaML API how-to | `rag_search("...", include_schema=False, include_data=False)` |

**Only use raw resources when you need the complete, machine-readable output** — e.g., for programmatic processing or when RAG results don't answer the question:

| Resource | Purpose |
|----------|---------|
| `deriva://catalog/schema` | Full schema JSON (large — use only when needed) |
| `deriva://table/{name}/schema` | One table's complete structure |
| `deriva://catalog/tables` | All tables with row counts |
| `deriva://vocabulary/{name}` | Complete vocabulary term list |
| `deriva://dataset/{rid}` | Dataset details and versions |
| `deriva://chaise-url/{table_or_rid}` | Web UI link (pass table name or RID) |

## Key Tools

| Tool | Purpose |
|------|---------|
| `rag_search` | **Primary discovery tool** — semantic search across schema, data, and docs |
| `preview_table` | Query with filters, columns, limit/offset |
| `get_table_sample_data` | Preview sample rows from a table |
| `preview_table` (with limit=1) | Count matching records |
| `get_record` | Fetch a single record by RID |
| `validate_rids` | Check if RIDs exist |
| `preview_denormalized_dataset` | Schema shape + size estimates (no dataset needed), or join dataset tables into flat DataFrame |
| Python API `dataset.download_dataset_bag(version)` | Download full dataset as BDBag |
| resource `deriva://dataset/{rid}/members` | List records in a dataset |
| `list_asset_executions` | Find executions that created/used an asset |

## Common Patterns

```
# Query with filter
preview_table(table_name="Subject", filters={"Species": "Mouse"}, limit=50)

# Paginate
preview_table(table_name="Image", limit=100, offset=200)

# Get specific record
get_record(table_name="Subject", rid="2-B4C8")

# Explore schema shape + size estimates (no dataset needed)
preview_denormalized_dataset(include_tables=["Image", "Subject"])

# Dataset-scoped info (no rows)
preview_denormalized_dataset(include_tables=["Image", "Subject"], dataset_rid="2-B4C8")

# ML-ready flat data with row preview
preview_denormalized_dataset(include_tables=["Image", "Subject"], dataset_rid="2-B4C8", limit=50)
```

## Re-querying Cached Results

When you run `preview_table` or `preview_denormalized_dataset`, the results are cached server-side. You can re-query them with different sort, filter, or pagination without re-executing the original query:

```
# See what's cached
list_cached_results()

# Re-query with different sort/filter/pagination
query_cached_result(cache_key="...", sort_by="Image.CDR", sort_desc=True, limit=50)
query_cached_result(cache_key="...", filter_col="Subject.Species", filter_val="Mouse")
query_cached_result(cache_key="...", limit=100, offset=200)
```

This is useful when exploring large result sets interactively — the first query fetches data from the catalog, and subsequent `query_cached_result` calls paginate/sort/filter locally.

## Tips

- Always use `limit` for large tables to avoid timeouts
- Column names are case-sensitive — check schema first
- Use `preview_denormalized_dataset` to resolve FK RIDs into readable values — works without a dataset RID for schema exploration
- Pin to specific dataset versions for reproducibility
- If a table or column name is misspelled, the MCP server will suggest similar entities in the error response — check for a `suggestions` field with "did you mean?" candidates

For the full guide with query patterns, feature queries, provenance tracking, and troubleshooting, read `references/workflow.md`.
