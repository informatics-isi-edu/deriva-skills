---
name: query-catalog-data
description: "ALWAYS use this skill when querying, filtering, searching, or browsing data in a Deriva catalog. Triggers on: 'query table', 'find records', 'filter by', 'how many records', 'look up RID', 'what tables exist', 'show me the data', 'explore the catalog', 'get record by RID', 'wide table', 'flat table', 'denormalize', 'join tables'."
disable-model-invocation: true
---

# Querying and Exploring Data in a Deriva Catalog

This skill covers how to find, filter, and explore data in a Deriva catalog using the `deriva-mcp-core` MCP tools and resources.

## Discovery: Start with RAG Search

**Always use `rag_search` first** for discovery and exploration questions — "what tables exist", "what features are available", "how are images classified", "what datasets are there". RAG search indexes the catalog schema, vocabulary terms, feature definitions, datasets, and executions, and returns focused, relevant results without flooding context.

| Query type | RAG call |
|------------|----------|
| Tables, columns, relationships | `rag_search("...", doc_type="catalog-schema")` |
| Vocabulary terms and meanings | `rag_search("...", doc_type="catalog-schema")` |
| Records by description or content | `rag_search("...", doc_type="catalog-data")` |

**Only use raw schema tools when you need the complete, machine-readable output** — e.g., for programmatic processing or when RAG results don't answer the question:

| Tool | Purpose |
|------|---------|
| `get_schema(hostname, catalog_id)` | Full schema JSON (large — use only when needed) |
| `get_table(hostname, catalog_id, schema, table)` | One table's complete structure |
| `catalog_tables(hostname, catalog_id)` | All tables with row counts |
| `list_vocabulary_terms(hostname, catalog_id, schema, table)` | Complete vocabulary term list |
| `lookup_term(hostname, catalog_id, schema, table, name)` | Look up a vocabulary term (synonym-aware) |

## Key Tools

| Tool | Purpose |
|------|---------|
| `rag_search(query, doc_type="catalog-schema"|"catalog-data")` | **Primary discovery tool** — semantic search across schema, data, and docs |
| `query_attribute(hostname, catalog_id, schema, table, ...)` | Filtered query with column projection, limit, offset |
| `query_aggregate(hostname, catalog_id, schema, table, ...)` | Aggregation queries (counts, group-by) |
| `count_table(hostname, catalog_id, schema, table, filter=...)` | Count matching records (faster than fetching) |
| `get_table_sample_data(hostname, catalog_id, schema, table)` | Preview sample rows from a table |
| `get_entities(hostname, catalog_id, schema, table, filter=...)` | Fetch records (use `filter={"RID": "..."}` to get a single record by RID) |

## Common Patterns

```python
# Query with filter (substitute your hostname + catalog_id everywhere)
query_attribute(
    hostname="data.example.org",
    catalog_id="1",
    schema="myproject",
    table="Subject",
    filter={"Species": "Mouse"},
    limit=50,
)

# Paginate
query_attribute(
    hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Image",
    limit=100, offset=200,
)

# Get a specific record by RID
get_entities(
    hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Subject",
    filter={"RID": "2-B4C8"},
)

# Count matching records (no row fetch)
count_table(
    hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Subject",
    filter={"Species": "Mouse"},
)

# Sample preview (no filter; first N rows)
get_table_sample_data(
    hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Image",
)
```

## Validating RIDs

The new MCP surface does not have a dedicated `validate_rids` tool. Use `get_entities` with a RID filter and check the result:

```python
result = get_entities(
    hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Subject",
    filter={"RID": "2-B4C8"},
)
if not result:
    # RID does not exist (or is in a different table)
    ...
```

For RID validation across multiple candidate tables, query each in turn — there is no single-tool cross-table RID lookup in the new surface.

## Aggregations

For COUNT, SUM, AVG, MIN, MAX queries over a table, use `query_aggregate`:

```python
query_aggregate(
    hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Image",
    group_by=["Subject.Species"],
    aggregates={"image_count": "COUNT(*)"},
    filter={"QC_Status": "Pass"},
)
```

## Tips

- Always use `limit` for large tables to avoid timeouts.
- Schema and column names are case-sensitive — check schema first via `rag_search` or `get_schema`.
- If a table or column name is misspelled, the MCP server's response includes a `suggestions` field with "did you mean?" candidates — check for that before retrying.

## Related Skills

- **`/deriva:route-catalog-schema`** — router for catalog structure / data exploration tasks
- **`/deriva:create-table`** — schema operations (creating domain tables, columns, FKs)
- **`/deriva:manage-vocabulary`** — vocabulary CRUD on any Deriva catalog

For the full guide with query patterns, vocabulary queries, and troubleshooting, read `references/workflow.md`.
