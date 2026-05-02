---
name: deriva-context
description: "ALWAYS load this context when the deriva plugin is active. Establishes what the deriva plugin provides (Deriva catalog operations via deriva-mcp-core) and the core concepts that apply to every Deriva catalog: catalogs, schemas, tables, vocabularies, RIDs, and Chaise display annotations. Triggers on: 'deriva', 'catalog', 'schema', 'vocabulary', 'rid', 'ermrest'."
disable-model-invocation: false
---

# Deriva Plugin Context

The `deriva` plugin provides skills for working with any Deriva catalog via `deriva-mcp-core`: querying tables, creating schemas / tables / columns, managing vocabularies and terms, customizing display annotations, and troubleshooting catalog errors. The skills work on any Deriva catalog and depend only on the core `deriva-mcp-core` MCP server and the `deriva-py` Python client library.

## Core Deriva concepts (always available)

These concepts come from `deriva-mcp-core` itself and apply to every Deriva catalog you connect to:

| Concept | What | Skill |
|---|---|---|
| **Catalog** | A versioned namespace of schemas, tables, vocabularies, and rows. Identified by hostname + catalog ID (or alias). | `query-catalog-data`, `route-catalog-schema` |
| **Schema / Table / Column** | The relational structure inside a catalog. Tables can FK into other tables and into vocabularies. | `create-table`, `route-catalog-schema` |
| **Vocabulary** | A controlled-term table with standard columns (Name, Description, Synonyms, ID, URI). FK targets for categorical columns. | `manage-vocabulary` |
| **RID** | Resource Identifier — every row in every Deriva table has a unique RID (e.g., `1-A2B3`). | `query-catalog-data`, `troubleshoot-deriva-errors` |
| **Display annotations** | Per-table and per-column annotations that drive the Chaise web UI. | `customize-display` |
| **Naming conventions** | Standard naming for schemas, tables, columns, and vocabulary terms (PascalCase, singular, descriptive). | `entity-naming` |

For deeper definitions of each concept — what a catalog actually is, how RIDs are minted, the anatomy of a vocabulary table, how the metadata catalog and the object store fit together — see `references/concepts.md`. Read it on cold-start (first time touching a Deriva catalog in a session) or whenever a skill assumes a concept the LLM doesn't already have a working model of.

## Deriva design philosophy

Deriva is an opinionated platform for managing scientific data, not just a relational database with a web UI. Four load-bearing opinions shape what is easy and what fights the grain. (For *what each concept is* — RID format, vocabulary column shape, snaptime mechanics, asset-table columns — see `references/concepts.md`. This section is about the modeling opinions.)

### RIDs are the canonical identity

**Reference rows by RID, not by domain key.** Tables should FK to other tables' `RID` column, not to accession numbers, sample IDs, or file paths. Domain keys are for humans (search, citation, display); RIDs are for the system (joins, references, links). Domain keys break — accessions get re-issued, file paths move, vendor IDs collide across vendors — RIDs don't.

### Controlled vocabularies, not text columns

**Whenever you reach for `text` for a categorical column, build a vocabulary instead.** This costs more upfront (a small table, terms with descriptions and synonyms) but Chaise's faceted search, cross-catalog interoperability, and self-documenting term descriptions all depend on the categorical column being a FK to a vocabulary rather than free text. Use `add_synonym` to absorb historical spellings without rewriting data. See `manage-vocabulary` and `entity-naming`.

### Don't overwrite history

Every change to a Deriva catalog is recorded with a server-side timestamp, and any past state is addressable as a snapshot. **Treat the audit trail as a feature, not a side effect.** Add a new row, update in place, or annotate the old row as superseded — but don't `delete` to erase. Pipelines should pin to a snapshot for reproducibility; published results should cite a snapshot, not just a catalog ID.

### Bulk bytes belong in the object store

Deriva separates metadata (ERMrest, the catalog) from bulk bytes (Hatrac, the object store), bridged by **asset tables** — catalog rows that carry filename, size, checksum, and the Hatrac URL of the object. The split is deliberate: each system has its own scaling profile, access pattern, lifecycle, and ACLs.

The two modeling implications:

- **Don't store bulk bytes in catalog columns** (`bytea`, base64-encoded blobs in JSON). Put them in Hatrac and reference them from an asset table.
- **Don't bury structured metadata in file headers or JSON sidecars.** Promote it to catalog columns where it can be queried.

### Why this matters operationally

When you're creating a new table, ask:

- Will rows be referenced from elsewhere? → Make sure FKs use the RID, not a domain key.
- Are any columns categorical? → Build vocabularies for them, even if the initial term list is small.
- Will the data be cited or used in published results? → Tell users to pin to a snapshot, not just the catalog.
- Will rows have associated bulk files? → Use an asset table that bridges to Hatrac, not blob columns.

These four choices are what turn a Deriva catalog from "a Postgres database with a web UI" into a FAIR (Findable, Accessible, Interoperable, Reusable) data resource.

## When to use this plugin's skills

The skills in this plugin cover catalog-side concerns common to every Deriva catalog:

- **Custom domain tables** — `Subject`, `Sample`, `Image`, anything specific to your project's data model → `/deriva:create-table`, `/deriva:query-catalog-data`
- **Vocabularies** — `Tissue_Type`, `Image_Quality`, `Diagnosis`, etc. → `/deriva:manage-vocabulary`
- **Schema introspection** — listing tables, browsing columns → `/deriva:query-catalog-data`, `/deriva:route-catalog-schema`
- **Display customization** — Chaise annotations on any table → `/deriva:customize-display`
- **Catalog errors** — auth, permissions, invalid RIDs, missing records, vocab term not found → `/deriva:troubleshoot-deriva-errors`
- **Naming a new entity** — the conventions for schemas, tables, columns, vocab terms → `/deriva:entity-naming`

## Stateless model

The `deriva-mcp-core` server is stateless. Every tool call takes `hostname=` and `catalog_id=` arguments — there is no implicit "active catalog" or "default schema". Every example in every skill in this plugin shows the full parameter set; substitute your catalog's hostname and ID.

This framing applies plugin-wide and is documented here once. Per-skill `SKILL.md` files and reference docs should not restate it — the always-on `deriva-context` skill ensures the LLM has this context before any other skill triggers, and repeating the boilerplate in every file creates maintenance liability without adding signal.

## Server status

To verify the MCP server is reachable and check which plugins are loaded, call `server_status(hostname=...)` — the response includes the running `deriva-mcp-core` framework version plus the list of loaded plugins.
