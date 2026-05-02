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
| Vocabulary table | `create_vocabulary` | Controlled term lists for categorical data — **vocabulary CRUD lives in `/deriva:manage-vocabulary`**; come back here only for non-vocabulary tables |

> **Asset tables:** create asset tables via `create_table` with the standard hatrac column setup (`URL`, `Filename`, `Length`, `MD5`, `Description`) and then add the `Asset_Type` FK column separately. There is no dedicated single-call asset-table convenience tool in `deriva-mcp-core`.

### Vocabularies first when a categorical column needs one

If the table you're creating has a categorical column (anything that records a value from a known set — diagnosis, status, type, label) and the vocabulary it should FK to **doesn't exist yet**, create the vocabulary *before* you create the table. The sequence:

1. Plan all categorical columns up front. For each, identify the vocabulary it should reference.
2. For every vocabulary that doesn't already exist in the catalog, hand off to `/deriva:manage-vocabulary` to create it (and populate at least the initial terms).
3. Come back to this skill to create the table, declaring each categorical column as a FK to its vocabulary.

Doing it in this order avoids two-pass schema mutation (create table with `text` columns → realize you wanted vocabularies → drop the columns and re-add as FKs). The drift cost of even briefly using `text` for what should be a vocabulary FK is non-trivial: any rows inserted in the interim carry free-text values that have to be normalized later.

If you're not sure whether a vocabulary already exists, search first with `rag_search("<concept>", doc_type="catalog-schema")` — same find-before-you-create discipline as for tables.

## Find before you create

> The MCP server does NOT perform automatic duplicate detection on `create_table`. The skill-level workflow is the only guardrail. Before calling `create_table`, run the "find before you create" workflow from the `semantic-awareness` skill: search via `rag_search` for similar tables, present a picker if multiple plausible matches turn up, and only fall through to creation if the user confirms a new table is needed.

**Search by name AND by column shape.** A new table that carries similar columns to an existing one is often a duplicate even if the names differ — `Image` and `Scan` and `Photograph` can all be the same kind of row. Pick 2-3 distinctive columns from the user's intended schema (e.g., `Tissue_Type`, `Acquisition_Date` rather than generic ones like `Name`), `rag_search` for them, and compare column lists with any matches. When the column overlap is high, present the user with three options before creating:

1. **Add the user's new columns to the existing table** (with `add_column`) — the simplest move when the new columns are naturally optional for non-specialized rows. Preserves all existing labels, asset uploads, and Chaise display work on the existing table.
2. **Keep the existing table; add a small "extra fields" table that FKs back to it** — the cleanest move when the user is describing a specialization (e.g., the existing `Image` plus a new `CT_Image_Detail` that carries CT-specific fields). The base table accumulates all rows; the specialization carries only the variant-specific data; queries that need everything join base + specialization. Maps directly to RID-based FKs.
3. **Create a separate parallel table** — only when the new entity is genuinely disjoint from the existing one (no useful shared queries, no need to treat both as "the same kind of thing" anywhere). Most "I think we need a new table" intuitions are actually option 2 in disguise.

For the column-overlap detection heuristic, the three-pattern decision guide with worked ML-flavored examples (`Image` → `CT_Image_Detail`, etc.), and the antipatterns to avoid, see `semantic-awareness/references/find-before-you-create.md`.

**Two extremes to steer away from when designing the table:**

- **EAV (everything in a generic key-value table):** when modeling feels hard, it's tempting to dodge by creating a table like `Entity_RID, Attribute_Name, Attribute_Value` and stuffing every "flexible" field into it as rows. This breaks faceted search, kills type safety, makes vocabulary FKs impossible, and forces every reader to reconstruct the schema from the data. **Don't.** If a column is categorical, model it as a controlled vocabulary FK (`/deriva:manage-vocabulary`). If a column is genuinely sparse and unstructured, use a single `jsonb` column on the existing table — not an EAV side table.
- **One giant wide table:** the opposite mistake — flatten every related entity into one big table with every field as a column. This forces repeated values (each subject's data repeats on every measurement row), breaks multi-valued relationships (you can't represent "this image has three annotators"), and makes many-to-many impossible (study × subject). **Normalize into multiple tables linked by FKs**, with **association tables** (a table with two FKs, one to each side, plus optional relationship-level columns) for many-to-many. See `deriva-context/references/concepts.md` for the association-table pattern.

The Deriva-native middle is what the platform is built for: one table per entity, controlled vocabularies for categorical values, FKs for one-to-many, association tables for many-to-many. When you find yourself sliding toward either extreme, the answer is almost always one of those four primitives.

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

## Related Skills

- **`/deriva:manage-vocabulary`** — Vocabulary CRUD (`create_vocabulary`, `add_term`, `add_synonym`). Use this first when a categorical column needs a vocabulary that doesn't exist yet (see "Vocabularies first" above), and after table creation when you need to extend a vocabulary.
- **`/deriva:entity-naming`** — Naming conventions for schemas, tables, columns, and FK columns (PascalCase, singular, FK columns match the referenced table). Read before naming a new table — names are hard to change later.
- **`/deriva:semantic-awareness`** — Find-before-you-create workflow. The MCP server does NOT auto-detect duplicate tables; this skill is the only guardrail.
- **`/deriva:generate-descriptions`** — Auto-drafted descriptions for tables and columns (always-on; runs when you create something without a description).
- **`/deriva:load-data`** — After you create the table, this is how you populate it: row inserts, batch loads from CSV/JSON, asset uploads to Hatrac (via the MCP tool, `deriva-upload-cli`, or the `DerivaUpload` Python class), updates, and the rare cases where deletion is the right move.
- **`/deriva:query-catalog-data`** — After you create the table, this is how you read from it (and how you should explore the existing schema before adding to it).
- **`/deriva:customize-display`** — Chaise display annotations on the table you just created (visible columns, row name patterns, foreign-key display). Treat the UI as part of the data model — see pillar 6 in the design philosophy.
- **`/deriva:troubleshoot-deriva-errors`** — When `create_table` or `add_column` fails with auth, RID, or connection errors.

The plugin-wide modeling checklist (when to use FKs, vocabularies, asset tables, snapshots, display annotations) lives in the always-on `deriva-context` skill; the full design rationale is in `deriva-context/references/philosophy.md`.
