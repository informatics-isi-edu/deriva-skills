---
name: query-catalog-data
description: "ALWAYS use this skill when querying, filtering, searching, browsing, or exploring data and schema in a Deriva catalog — including the cold-start case of 'I just connected to a catalog, what's in it?' Use this skill *before* any catalog mutation so you understand what already exists. The skill leads with `rag_search` for natural-language discovery (the recommended starting point for almost any exploration question) and falls through to ERMrest queries for precise / programmatic reads. Triggers on: 'query table', 'find records', 'filter by', 'how many records', 'count rows', 'look up RID', 'get record by RID', 'show me the data', 'explore the catalog', 'discover schema', 'discover the schema', 'what tables exist', 'what vocabularies exist', 'what columns does this table have', 'rag_search', 'semantic search the catalog', 'natural language search the catalog', 'find by description', 'wide table', 'flat table', 'denormalize', 'join tables', 'select columns', 'project columns', 'first time looking at this catalog', 'cold start exploration'."
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
| `deriva://catalog/{hostname}/{catalog_id}/tables` (resource) | All tables with row counts (read via `ReadMcpResourceTool`) |
| `list_vocabulary_terms(hostname, catalog_id, schema, table)` | Complete vocabulary term list |
| `lookup_term(hostname, catalog_id, schema, table, name)` | Look up a vocabulary term (synonym-aware) |

## Key Tools

| Tool | Signature | Purpose |
|------|-----------|---------|
| `rag_search` | `rag_search(query, doc_type="catalog-schema"|"catalog-data")` | **Primary discovery tool** — semantic search across schema, data, and docs |
| `get_entities` | `get_entities(hostname, catalog_id, schema, table, filters=..., limit=, after_rid=, preflight_count=)` | Fetch whole rows from one table. Use `filters={"RID": "..."}` for a specific record. |
| `count_table` | `count_table(hostname, catalog_id, schema, table, filters=...)` | Count matching records (faster than fetching). |
| `query_attribute` | `query_attribute(hostname, catalog_id, path, attributes=, limit=, after_rid=)` | Column projection + multi-table joins via an ERMrest path expression. |
| `query_aggregate` | `query_aggregate(hostname, catalog_id, path, aggregates=[...])` | Aggregate functions (count, sum, avg, max, min) — also via path expression. |
| `get_table_sample_data` | `get_table_sample_data(hostname, catalog_id, schema, table, limit=3)` | First N rows of a table — quick preview. |

> **Important:** `query_attribute` and `query_aggregate` take a `path` (ERMrest path expression like `"myproject:Subject/Species=Mouse"`), **not** `schema` + `table` + `filters` arguments. Read the `query_guide` MCP prompt before constructing paths. `get_entities` and `count_table` keep the `schema, table, filters` shape because they're single-table whole-row tools.

## Choosing the right tool

| You want… | Tool |
|-----------|------|
| All columns of one table, optionally filtered | `get_entities` |
| One record by RID | `get_entities(..., filters={"RID": "..."})` |
| Just the row count, optionally filtered | `count_table` |
| Specific columns from one or more tables, including joins across FKs | `query_attribute` |
| Aggregate (count, sum, avg, max, min) over one or more tables | `query_aggregate` |
| Quick "what's in this table?" preview | `get_table_sample_data` |

If your need is a single-table whole-row read, prefer `get_entities` — the path-expression syntax of `query_attribute` is overkill. Reach for `query_attribute` when you need column projection or to traverse foreign keys.

## Common Patterns

```python
# Get all columns of one table, filtered
get_entities(
    hostname="data.example.org",
    catalog_id="1",
    schema="myproject",
    table="Subject",
    filters={"Species": "Mouse"},
    limit=50,
)

# Get a specific record by RID
get_entities(
    hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Subject",
    filters={"RID": "2-B4C8"},
)

# Count matching records (no row fetch)
count_table(
    hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Subject",
    filters={"Species": "Mouse"},
)

# Project specific columns (use query_attribute with path expression)
query_attribute(
    hostname="data.example.org", catalog_id="1",
    path="myproject:Subject/Species=Mouse",
    attributes=["RID", "Internal_ID", "Sex"],
    limit=50,
)

# Multi-table join (Subject -> Sample), project columns
query_attribute(
    hostname="data.example.org", catalog_id="1",
    path="myproject:Subject/Species=Mouse/myproject:Sample",
    attributes=["RID", "Sample_ID", "Collection_Date"],
    limit=100,
)

# Cursor-based pagination — pass after_rid from the last row of the prior page
query_attribute(
    hostname="data.example.org", catalog_id="1",
    path="myproject:Image",
    limit=100,
    after_rid="2-IMG99",
)

# Sample preview (first 3 rows by default; raise with limit)
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
    filters={"RID": "2-B4C8"},
)
if not result:
    # RID does not exist (or is in a different table)
    ...
```

For RID validation across multiple candidate tables, query each in turn — there is no single-tool cross-table RID lookup in the new surface.

## Aggregations

For COUNT, SUM, AVG, MIN, MAX queries, use `query_aggregate` with a path expression and aggregate expressions:

```python
# Count rows in one table
query_aggregate(
    hostname="data.example.org", catalog_id="1",
    path="myproject:Image",
    aggregates=["cnt:=cnt(RID)"],
)

# Count + group via an aggregate alias
query_aggregate(
    hostname="data.example.org", catalog_id="1",
    path="myproject:Image/QC_Status=Pass",
    aggregates=["cnt:=cnt(RID)"],
)
```

Aggregate expressions follow ERMrest syntax: `cnt(col)`, `cnt_d(col)` (count distinct), `avg(col)`, `sum(col)`, `min(col)`, `max(col)`, `array(col)`, `array_d(col)`. The `name:=expression` syntax names the result column. For grouping, see the `query_guide` MCP prompt — it covers `attributegroup` semantics in depth.

## Tips

- Always use `limit` for large tables to avoid timeouts.
- For pagination, use cursor-based `after_rid`, **not** offset — there is no `offset` parameter on these tools.
- Schema and column names are case-sensitive — check schema first via `rag_search` or `get_schema`.
- If a table or column name is misspelled, the MCP server's response includes a `suggestions` field with "did you mean?" candidates — check for that before retrying.
- Read the **`query_guide` MCP prompt** before writing complex paths — it covers operators (`::lt::`, `=any(...)`, `!Col=val`), aliases, multi-hop joins, and URL encoding.

## Related Skills

- **`/deriva:create-table`** — schema operations (creating domain tables, columns, FKs)
- **`/deriva:load-data`** — populate the tables you've queried: row inserts, CSV/JSON imports, asset uploads, updates, and the rare delete
- **`/deriva:manage-vocabulary`** — vocabulary CRUD on any Deriva catalog

For the full guide with query patterns, vocabulary queries, and troubleshooting, read `references/workflow.md`.
