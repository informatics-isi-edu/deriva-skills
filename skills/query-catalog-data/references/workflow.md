# Querying and Exploring Data in a Deriva Catalog

This guide covers how to query, filter, and explore data in a Deriva catalog using the `deriva-mcp-core` MCP tools and resources.

## Two query surfaces

The MCP surface has two distinct query patterns. Pick the right one for the task:

| Pattern | Tools | When to use |
|---------|-------|-------------|
| **Whole-row, single-table** | `get_entities`, `count_table`, `delete_entities`, `update_entities`, `insert_entities` | You want all columns from one table, optionally filtered. Argument shape: `schema=, table=, filters=`. |
| **ERMrest path expression** | `query_attribute`, `query_aggregate` | You want column projection, FK joins, or aggregates. Argument shape: `path=, attributes=` (or `aggregates=`). |

The two share nothing structurally — `query_attribute` does **not** take `schema`/`table`/`filters`. It takes a single `path` string in ERMrest path syntax. Read the **`query_guide` MCP prompt** before constructing complex paths.

## Understanding the Schema

Before querying, understand what tables and columns are available.

### Start with RAG Search (Preferred)

**Always use `rag_search` first** for discovery and exploration. It indexes the catalog schema (tables, columns, FKs, vocabulary terms) and returns focused results without flooding context:

```python
# What tables and features exist?
rag_search("Image tables and features", doc_type="catalog-schema")

# What vocabulary terms are available?
rag_search("classification categories", doc_type="catalog-schema")

# What records match a description?
rag_search("subjects with diabetes diagnosis", doc_type="catalog-data")
```

RAG search avoids dumping large schema JSON into context and finds relevant results semantically.

### Raw Schema Tools (When You Need Complete Output)

Only use these when RAG results are insufficient or you need the full machine-readable schema:

```python
# Full schema overview
get_schema(hostname="data.example.org", catalog_id="1", schema="myproject")

# Catalog-level info (schema names + table counts)
get_catalog_info(hostname="data.example.org", catalog_id="1")

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
    limit=5,  # default is 3
)
```

## Whole-Row Queries with `get_entities`

`get_entities` is the right tool when you want all columns from one table, optionally filtered, with cursor-based pagination.

### Get All Rows

```python
get_entities(
    hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Subject",
    limit=100,
)
```

> **Preflight count rule.** When the table's row count is unknown, you MUST call with `preflight_count=True` first. It returns only the count, never rows. Present the count, confirm a limit with the user, then call again with `preflight_count=False` to fetch.

### Filtered

`filters=` is a dict of equality filters (column-value pairs). Multiple keys are AND-ed:

```python
# Single equality filter
get_entities(
    hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Subject",
    filters={"Species": "Mouse"},
)

# Multiple AND conditions
get_entities(
    hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Subject",
    filters={"Species": "Mouse", "Status": "Active"},
)
```

### By RID

```python
get_entities(
    hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Subject",
    filters={"RID": "2-B4C8"},
)
```

Returns the record (single-element list) or an empty list if the RID doesn't exist in that table.

### Cursor-based Pagination

Pagination uses `after_rid`, **not** offset (no offset parameter exists):

```python
# Page 1
page1 = get_entities(
    hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Image",
    limit=100,
)

# Page 2 — pass the RID of the last row from page 1
page2 = get_entities(
    hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Image",
    limit=100,
    after_rid="<RID of last row from page 1>",
)
```

Stop when the returned count is less than `limit`.

## Counting with `count_table`

Use `count_table` for fast counting without fetching rows:

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
    filters={"Species": "Mouse"},
)
```

## Validate Known RIDs

The MCP surface does not have a `validate_rids` tool. Validate by attempting `get_entities` per candidate table; an empty result means the RID does not exist there:

```python
result = get_entities(
    hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Subject",
    filters={"RID": "2-B4C8"},
)
exists = bool(result and result.get("entities"))
```

## Column Projection and Joins with `query_attribute`

Use `query_attribute` when you want specific columns, FK joins, or comparison operators beyond equality. The shape is **completely different** from `get_entities` — it takes a single `path` argument in ERMrest path syntax, not `schema`/`table`/`filters`.

### Project Specific Columns from One Table

```python
query_attribute(
    hostname="data.example.org", catalog_id="1",
    path="myproject:Subject",
    attributes=["RID", "Internal_ID", "Species"],
    limit=50,
)
```

### Filter (in the path)

Filters are part of the path expression, not a separate argument:

```python
# Equality filter
query_attribute(
    hostname="data.example.org", catalog_id="1",
    path="myproject:Subject/Species=Mouse",
    attributes=["RID", "Internal_ID"],
    limit=100,
)

# Multiple AND filters (chain with /)
query_attribute(
    hostname="data.example.org", catalog_id="1",
    path="myproject:Subject/Species=Mouse/Status=Active",
    attributes=["RID", "Internal_ID"],
)

# Comparison operators
query_attribute(
    hostname="data.example.org", catalog_id="1",
    path="myproject:Subject/Age::gt::30",
    attributes=["RID", "Age"],
)

# IN-list (any-of)
query_attribute(
    hostname="data.example.org", catalog_id="1",
    path="myproject:Subject/Species=any(Mouse,Rat,Human)",
    attributes=["RID", "Species"],
)

# Negation
query_attribute(
    hostname="data.example.org", catalog_id="1",
    path="myproject:Subject/!Status=Inactive",
    attributes=["RID", "Status"],
)
```

### Multi-Hop Joins

Chain table names in the path to traverse foreign keys. ERMrest resolves the FK automatically when there's exactly one between the two tables:

```python
# Subject -> Sample (one-hop join)
query_attribute(
    hostname="data.example.org", catalog_id="1",
    path="myproject:Subject/Species=Mouse/myproject:Sample",
    attributes=["RID", "Sample_ID", "Collection_Date"],
    limit=100,
)

# Subject -> Sample -> Measurement (two-hop)
query_attribute(
    hostname="data.example.org", catalog_id="1",
    path="myproject:Subject/RID=2-SUB1/myproject:Sample/myproject:Measurement",
    attributes=["RID", "Value", "Units"],
    limit=100,
)
```

By default, the projected columns come from the **final** table in the path. To project columns from earlier tables, use aliases.

### Aliases for Multi-Table Projection

```python
# Bind alias "s" to Subject; project columns from both Subject and the final Sample
query_attribute(
    hostname="data.example.org", catalog_id="1",
    path="s:=myproject:Subject/Species=Mouse/myproject:Sample",
    attributes=["subject_rid:=s:RID", "s:Internal_ID", "RID", "Sample_ID"],
    limit=50,
)
```

The `name:=expression` syntax names output columns to disambiguate when the same column name appears in multiple tables (e.g., `RID`).

### Cursor-based Pagination

```python
# Page 1
query_attribute(
    hostname="data.example.org", catalog_id="1",
    path="myproject:Image",
    attributes=["RID", "Filename"],
    limit=100,
)

# Page 2
query_attribute(
    hostname="data.example.org", catalog_id="1",
    path="myproject:Image",
    attributes=["RID", "Filename"],
    limit=100,
    after_rid="<RID of last row from page 1>",
)
```

## Aggregations with `query_aggregate`

Same path-expression syntax as `query_attribute`, but with `aggregates=` instead of `attributes=`. Aggregate expressions follow ERMrest syntax: `cnt(col)`, `cnt_d(col)` (count distinct), `avg(col)`, `sum(col)`, `min(col)`, `max(col)`, `array(col)`, `array_d(col)`. The `name:=expression` syntax names the output column.

```python
# Count rows
query_aggregate(
    hostname="data.example.org", catalog_id="1",
    path="myproject:Image",
    aggregates=["cnt:=cnt(RID)"],
)

# Filtered count
query_aggregate(
    hostname="data.example.org", catalog_id="1",
    path="myproject:Image/QC_Status=Pass",
    aggregates=["cnt:=cnt(RID)"],
)

# Multiple aggregates at once
query_aggregate(
    hostname="data.example.org", catalog_id="1",
    path="myproject:Sample",
    aggregates=["cnt:=cnt(RID)", "max_size:=max(Volume_mL)", "avg_size:=avg(Volume_mL)"],
)

# Aggregate over a join
query_aggregate(
    hostname="data.example.org", catalog_id="1",
    path="myproject:Subject/Species=Mouse/myproject:Sample",
    aggregates=["cnt:=cnt(RID)"],
)
```

For grouped aggregates (one row per group), see the `query_guide` MCP prompt's `attributegroup` semantics — that's a different endpoint not covered by `query_aggregate`.

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

## Common Query Patterns

### Find Images for a Subject

```python
# If you want all columns of Image filtered by Subject FK:
get_entities(
    hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Image",
    filters={"Subject": "2-A1B2"},
)

# If you want specific columns or a join:
query_attribute(
    hostname="data.example.org", catalog_id="1",
    path="myproject:Image/Subject=2-A1B2",
    attributes=["RID", "Filename", "Modality"],
)
```

### Find Records by Multiple Filters

```python
get_entities(
    hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Image",
    filters={"Subject": "2-A1B2", "Modality": "MRI"},
)
```

### Date / Range Comparison Queries

For range queries (greater-than, less-than), `get_entities`'s equality-only `filters=` won't work — use `query_attribute` with comparison operators:

```python
# Samples collected after 2024-01-01
query_attribute(
    hostname="data.example.org", catalog_id="1",
    path="myproject:Sample/Collected_Date::gt::2024-01-01",
    attributes=["RID", "Sample_ID", "Collected_Date"],
)

# Subjects with age between 18 and 65
query_attribute(
    hostname="data.example.org", catalog_id="1",
    path="myproject:Subject/Age::geq::18/Age::leq::65",
    attributes=["RID", "Age"],
)
```

Available comparison operators (from the `query_guide`): `::lt::`, `::leq::`, `::gt::`, `::geq::`, `::null::`, `::regexp::`, `::ciregexp::`, `::ts::`. Combine within a single filter element using `&` (AND) or `;` (OR).

## Complete Example Workflow

A typical workflow for exploring and extracting data from a catalog:

1. **Orient yourself**: `rag_search("what tables and features exist", doc_type="catalog-schema")` to discover the catalog structure. Fall back to `get_catalog_info(...)` only if RAG doesn't answer your question.

2. **Explore a table**: `rag_search("Subject columns and relationships", doc_type="catalog-schema")` to understand columns, then `get_table_sample_data(..., schema="myproject", table="Subject")` for sample rows.

3. **Count records**: `count_table(..., schema="myproject", table="Subject")` and `count_table(..., schema="myproject", table="Subject", filters={"Species": "Mouse"})`.

4. **Filtered fetch**: `get_entities(..., schema="myproject", table="Subject", filters={"Species": "Mouse"}, limit=50)` for whole rows, or `query_attribute(..., path="myproject:Subject/Species=Mouse", attributes=["RID", "Internal_ID"], limit=50)` for projected columns.

5. **Inspect a specific record**: `get_entities(..., schema="myproject", table="Subject", filters={"RID": "2-A1B2"})`.

6. **Find related data**: `query_attribute(..., path="myproject:Subject/RID=2-A1B2/myproject:Sample", attributes=["RID", "Sample_ID"])`.

## Tips and Troubleshooting

- **Pick the right tool.** Whole-row from one table → `get_entities`. Specific columns or joins → `query_attribute`. Aggregates → `query_aggregate`. Counts → `count_table`. Mixing them up wastes time and produces confusing API errors.
- **Path expressions for `query_attribute` / `query_aggregate`.** Read the `query_guide` MCP prompt for the full syntax (operators, joins, aliases, URL encoding). The MCP server returns a 400 error with details when the path is malformed.
- **Empty results are valid.** A query that returns 0 rows is a complete answer — the path is correct, the data simply doesn't match. Don't loop with reformulations expecting different results.
- **Cursor pagination, not offset.** `get_entities` and `query_attribute` paginate via `after_rid`, not `offset`. Pass the RID of the last row in the previous page.
- **Large tables**: always use `limit` for tables with more than a few hundred rows. Fetching the entire table can be slow and may time out.
- **Schema names are mandatory** for the single-table tools (`get_entities`, `count_table`, `get_table`, etc.) — every call needs `schema=` AND `table=`. There is no `set_default_schema` in the new surface.
- **Column names are case-sensitive**: use the exact column names from the schema. `"Species"` is not the same as `"species"`.
- **RID format**: RIDs look like `2-B4C8` (a number, a dash, and an alphanumeric string). They are unique within a catalog.
- **Schema mismatch**: if a table is not found, verify you are using the correct `schema=` argument. The MCP server's response includes a `suggestions` field with "did you mean?" candidates if the name is misspelled.
