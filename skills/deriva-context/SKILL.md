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

Deriva is an opinionated platform for managing scientific data, not just a relational database with a web UI. The opinions are worth understanding before you start modeling — they shape what is easy and what fights the grain.

### RIDs as primary identity

Every row in every table in every Deriva catalog gets a **Resource Identifier (RID)** — a short, catalog-wide-unique, opaque string (e.g., `1-A2B3`) minted by the server at insert time. RIDs are the canonical identity for any record:

- **Stable across edits.** Renaming a row, changing its data, even changing which schema/table it lives in does not change its RID.
- **Resolvable.** A RID resolves to a permanent URL on the host (`https://<host>/id/<catalog>/<rid>`). You can cite it in a paper, paste it in chat, link to it from another catalog.
- **The unit of foreign-key reference.** Tables FK to each other by RID, not by domain keys (accession numbers, sample IDs, file paths). Domain keys live in their own columns and can be changed; the RID is the durable join target.

The implication for modeling: **prefer RID-based references over reusing domain keys as FK targets.** Domain keys break (accessions get re-issued, file paths move, vendor IDs collide across vendors); RIDs don't.

### Controlled vocabularies for categorical values

Anywhere a column is categorical — diagnosis, tissue type, instrument model, file type — Deriva expects you to define a **vocabulary table** and FK the categorical column to it, instead of storing the value as a free-text string or an enum.

This costs more upfront (you create a small table, populate terms with descriptions and synonyms) but pays back in:

- **Discoverability.** Vocabulary tables drive faceted search in Chaise. Free-text columns don't.
- **Curation.** Adding a synonym (`add_synonym`) lets historical free-text spellings resolve to the canonical term without rewriting the data.
- **Consistency across catalogs.** Multiple catalogs can share the same controlled vocabulary (e.g., an organism vocab populated from NCBI Taxonomy) and remain interoperable.
- **Self-describing data.** Each term carries its own `Description`, so the meaning of a value is in the catalog, not in a separate data dictionary that drifts out of sync.

The implication for modeling: **whenever you find yourself reaching for `text` for a categorical column, stop and create a vocabulary instead.** See `manage-vocabulary` and `entity-naming`.

### Catalog snapshots for reproducibility

Every change to a Deriva catalog — schema edits, row inserts, row updates, deletes — is recorded with a server-side timestamp. The catalog is **time-travelable**: any past state can be addressed by a snapshot identifier (snaptime) and queried as if it were the current state.

- **Citing a snapshot freezes a result.** A paper that cites `catalog/1@2T-...` references a specific frozen state, not "whatever is in the catalog today."
- **Schema changes don't invalidate old data.** A snapshot from before a column was added still queries cleanly — through the schema as it was at that time.
- **Reproducible pipelines** pin to a snapshot, not just a catalog, so a re-run reads the same bytes the original run did.

The implication for modeling: **never overwrite history if you can avoid it.** Add a new row, update an existing row in place, or annotate the old row as superseded — but don't `delete` to erase. The audit trail is a feature.

### Metadata catalog + object store, separated by design

Deriva splits responsibilities cleanly across two systems:

- **The catalog (ERMrest)** stores structured metadata — schemas, tables, vocabularies, foreign keys, the small relational descriptions of what data exists, who produced it, what it labels, how it relates.
- **The object store (Hatrac)** stores the bulk bytes — image files, model weights, FASTQ files, large binary blobs. Each object is content-addressed by checksum and accessed by URL.

The two are bridged by **asset tables** in the catalog: rows that carry filename, size, checksum, MIME type, and the Hatrac URL of the underlying object. The catalog row is the searchable, queryable, FK-able handle; the object store holds the bytes.

This separation is deliberate:

- **Different scaling profiles.** Catalogs handle millions of small structured rows efficiently; object stores handle terabytes of opaque bytes efficiently. Forcing one system to do both jobs leaves both jobs badly served.
- **Different access patterns.** Metadata is read by Chaise queries, faceted search, and SQL-like joins. Bulk data is read by streaming downloads, often in bulk via bag exports.
- **Different lifecycles.** Metadata edits are cheap and frequent; object-store writes are expensive, rare, and immutable. Content-addressing in Hatrac means the same bytes uploaded twice resolve to one object — deduplication for free.
- **Different access control.** Metadata can be world-readable while underlying objects remain restricted, or vice versa, since the two systems have independent ACLs.

The implication for modeling: **don't store bulk bytes in catalog columns** (`bytea`, base64-encoded blobs in JSON, etc.). Put them in Hatrac and reference them from an asset table. Conversely, **don't put structured metadata as ad-hoc fields inside file headers or JSON sidecars** — promote it to catalog columns where it can be queried.

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
