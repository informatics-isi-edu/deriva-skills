---
name: create-table
description: "ALWAYS use this skill when creating tables, asset tables, or adding columns in a Deriva catalog. Triggers on: 'create table', 'add column', 'asset table', 'foreign key', 'define schema', 'new table for images/subjects/samples', 'column types'."
disable-model-invocation: true
---

# Creating Domain Tables in Deriva

Tables are the foundation of a Deriva catalog schema. Choose the right table type, follow naming conventions, and document everything.



## Table Types

| Type | Tool | When to Use |
|------|------|-------------|
| Standard table | `create_table` | Regular data with columns and foreign keys |
| Vocabulary table | `create_vocabulary` | Controlled term lists for categorical data |

> **Asset tables:** create asset tables via `create_table` with the standard hatrac column setup (`URL`, `Filename`, `Length`, `MD5`, `Description`) and then add the `Asset_Type` FK column separately. There is no dedicated single-call asset-table convenience tool in `deriva-mcp-core`.

## Find before you create

> The MCP server does NOT perform automatic duplicate detection on `create_table`. The skill-level workflow is the only guardrail. Before calling `create_table`, run the "find before you create" workflow from the `semantic-awareness` skill: search via `rag_search` for similar tables, present a picker if multiple plausible matches turn up, and only fall through to creation if the user confirms a new table is needed.

For detailed guidance on interpreting search hits and deciding whether to reuse, extend, or create a new table, see the `semantic-awareness` skill.

## Key Decisions

### Naming Conventions
Names for tables, columns, and FK columns follow the canonical conventions documented in the `entity-naming` skill (PascalCase with underscores, singular tables, descriptive columns, FK columns match the referenced table). Read it before creating a new table — names are hard to change later because every reference (URLs, FK constraints, scripts, configs, bag exports) carries the literal name.

### Column Type Selection
- Prefer `float8` over `float4` for scientific data (precision matters)
- Prefer `timestamptz` over `timestamp` (avoid timezone ambiguity)
- Prefer `jsonb` over `json` (better query performance)
- Use `markdown` only when you need rich text rendering in the UI

#### `text` is for textual content, not for values

`text` (and `markdown`) columns are for genuinely free-form textual content: descriptions, notes, comments, abstracts, narrative fields. **They are not for recording values from a known set.**

If the column's purpose is to record a *value* — a category, a status, a type, a controlled label, a member of any enumerable set, even if the set is small or seems obvious — **use a controlled vocabulary instead.** Create a vocabulary table with the legal values and FK the column to it. This is one of Deriva's load-bearing modeling opinions (pillar 3 in the design philosophy: "controlled vocabularies and foreign keys, not free-form values").

Why it matters in practice:

- Free-text categorical columns drift over time. `Stage` as `text` will accumulate `"Stage I"`, `"stage 1"`, `"I"`, `" Stage I "` — all meaning the same thing. A vocabulary FK enforces one canonical spelling and lets `add_synonym` absorb the rest.
- Chaise renders vocabulary-backed columns as faceted filters (clickable, aggregable). Free-text columns become text-search boxes that don't aggregate.
- The vocabulary table itself documents the legal values — each term has a `Description` that lives in the catalog, queryable, not in a side document.
- Cross-catalog interoperability requires that "the same value" is literally the same row in a shared vocabulary, not two free-text strings that happen to spell the same thing.

The "even if the set is small" caveat matters: it's tempting to use `text` for a 2-3-value field ("active"/"inactive", "draft"/"published") because creating a vocabulary feels like overkill. Don't. The vocabulary cost is small and one-time; the drift cost of the alternative compounds over the catalog's lifetime.

For vocabulary CRUD (creating the table, adding terms, managing synonyms), see the `manage-vocabulary` skill (`/deriva:manage-vocabulary`).

### Foreign Key on_delete
- `CASCADE` — Delete children when parent is deleted (strong ownership)
- `SET NULL` — Nullify FK when parent is deleted (optional relationship)
- `NO ACTION` (default) — Prevent parent deletion if children exist

### Documentation (Required)
- Always set `comment` on tables and columns — these are the primary way users understand catalog structure
- Use `set_row_name_pattern` so records are identifiable in the UI
- Use `set_table_display_name` / `set_column_display_name` for user-friendly names

**Table descriptions** should explain what records represent, key relationships, and primary use case:
- Good: "Individual chest X-ray images with associated metadata. Links to Subject (patient) and Study (imaging session). Primary asset table for classification experiments."
- Bad: "Images" or "Table for storing image data"

**Column descriptions** should explain what the value represents, units/format, and constraints:
- Good: "Patient age at time of imaging in years. Integer 0-120. Used for demographic stratification in training splits."
- Bad: "Age" or "The age column"

For description templates and quality guidelines, see the `generate-descriptions` skill.

## Quick Reference

```python
# Standard table with FK
create_table(
    hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Sample",
    columns=[...], foreign_keys=[...],
    comment="...",
)

# Add column to existing table
add_column(
    hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Subject",
    column_name="Weight_kg", column_type="float8",
    comment="...",
)
```

## Reference Tools

- `rag_search("your concept", doc_type="catalog-schema")` — **Search first** to find existing tables, columns, and relationships by concept
- `get_schema(hostname, catalog_id)` — Full catalog schema as structured JSON (large; use when you need the complete output)
- `get_table(hostname, catalog_id, schema, table)` — Table details including columns and foreign keys
- `catalog_tables(hostname, catalog_id)` — All tables with row counts

For the full guide with column types table, FK specification, common patterns, and examples, read `references/workflow.md`.
