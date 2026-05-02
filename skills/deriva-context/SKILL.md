---
name: deriva-context
description: "ALWAYS load this context when the deriva plugin is active. Establishes what the deriva plugin provides (Deriva catalog operations via deriva-mcp-core), the core concepts that apply to every Deriva catalog (catalogs, schemas, tables, vocabularies, RIDs, foreign keys, asset tables, snapshots, Chaise display annotations), and Deriva's modeling philosophy (RIDs as identity, controlled vocabularies, audit-preserving history, metadata/object-store split — the choices that make a Deriva catalog FAIR). Triggers on: 'deriva', 'catalog', 'schema', 'vocabulary', 'rid', 'ermrest', 'hatrac', 'chaise', 'data modeling', 'controlled vocabulary'."
disable-model-invocation: false
---

# Deriva Plugin Context

The `deriva` plugin provides skills for working with any Deriva catalog via `deriva-mcp-core`. The skills cover catalog-side operations that apply to any Deriva deployment and depend only on `deriva-mcp-core` and the `deriva-py` Python client library.

**First time touching a Deriva catalog this session?** Start with `/deriva:route-catalog-schema` to explore the structure of an existing catalog before you mutate anything. Hit an auth or permission error early on? Go straight to `/deriva:troubleshoot-deriva-errors`.

**Out of scope for this plugin:** domain-specific abstractions that build *on top of* a Deriva catalog. Many Deriva deployments layer their own domain model on the catalog primitives — for example, a project may define its own concepts of "experiment," "sample lineage," "annotation pipeline," or "ML execution," each with its own tables, vocabularies, and conventions. Those layered models live in their own plugins, libraries, or projects (e.g., the companion `deriva-ml` plugin handles ML workflows, Datasets, Workflows, Executions, Features). When a user mentions a concept that's specific to a domain layer rather than the catalog primitives below, hand off to the relevant domain plugin if one is loaded.

## Concept index

These concepts come from `deriva-mcp-core` itself and apply to every Deriva catalog. Each row points at the skill that handles operations on it; deeper definitions live in `references/concepts.md`.

| Concept | What it is | Skill |
|---|---|---|
| **Catalog** | A versioned namespace of schemas, tables, vocabularies, and rows. Identified by hostname + catalog ID (or alias). | `/deriva:query-catalog-data`, `/deriva:route-catalog-schema` |
| **Schema / Table / Column** | The relational structure inside a catalog. Tables can FK into other tables and into vocabularies. | `/deriva:create-table`, `/deriva:route-catalog-schema` |
| **Vocabulary** | A controlled-term table with standard columns (Name, Description, Synonyms, ID, URI). FK target for categorical columns. | `/deriva:manage-vocabulary` |
| **RID** | Resource Identifier — every row in every Deriva table has a unique, server-minted, resolvable RID (e.g., `1-A2B3`). | `/deriva:query-catalog-data`, `/deriva:troubleshoot-deriva-errors` |
| **Foreign keys** | The relational glue. FKs target RID columns; FKs to vocabularies model categorical values. | `/deriva:create-table` |
| **Association tables** | The standard pattern for many-to-many relationships: a table with two FKs, one to each side. | `/deriva:create-table` |
| **Asset tables + Hatrac** | Catalog rows that bridge to objects in Deriva's object store (filename, size, checksum, URL). | `/deriva:create-table`, `/deriva:customize-display` |
| **Catalog snapshots** | Time-travelable history. Any past state is queryable by snaptime; pin a snaptime for reproducibility. | (resource: `concepts.md`) |
| **Display annotations** | Per-table / per-column JSON that drives the Chaise web UI. | `/deriva:customize-display` |
| **Naming conventions** | PascalCase, singular nouns, descriptive — for schemas, tables, columns, and vocabulary terms. | `/deriva:entity-naming` |

> **When to read `references/concepts.md`:** on cold-start (first Deriva-related action of the session), or any time you encounter a concept above whose mechanics you don't have a working model of — RID format, vocabulary column shape, snaptime semantics, asset-table column shape, association-table conventions. The reference is mechanics-focused (what each thing *is* and how it works); the design philosophy below is opinion-focused (what to *do* with it).

## Tasks → skills

The catalog-side concerns this plugin handles:

- **Custom domain tables** — `Subject`, `Sample`, `Image`, anything specific to your project's data model → `/deriva:create-table`, `/deriva:query-catalog-data`
- **Vocabularies** — `Tissue_Type`, `Image_Quality`, `Diagnosis`, etc. → `/deriva:manage-vocabulary`
- **Schema introspection** — listing tables, browsing columns → `/deriva:query-catalog-data`, `/deriva:route-catalog-schema`
- **Display customization** — Chaise annotations on any table → `/deriva:customize-display`
- **Catalog errors** — auth, permissions, invalid RIDs, missing records, vocab term not found → `/deriva:troubleshoot-deriva-errors`
- **Naming a new entity** — the conventions for schemas, tables, columns, vocab terms → `/deriva:entity-naming`
- **Verifying the server is reachable** — call `server_status(hostname=...)`. The response includes the running `deriva-mcp-core` framework version plus the list of loaded plugins.

## Stateless model

The `deriva-mcp-core` server is stateless. Every tool call takes `hostname=` and `catalog_id=` arguments — there is no implicit "active catalog" or "default schema". Every example in every skill in this plugin shows the full parameter set; substitute your catalog's hostname and ID.

## Deriva design philosophy

Four load-bearing modeling opinions. Apply them when designing tables, choosing column types, or evaluating whether an existing model fits the platform.

### RIDs are the canonical identity

**Reference rows by RID, not by domain key.** Tables should FK to other tables' `RID` column, not to accession numbers, sample IDs, or file paths. Domain keys are for humans (search, citation, display); RIDs are for the system (joins, references, links). Domain keys break — accessions get re-issued, file paths move, vendor IDs collide across vendors — RIDs don't.

### Controlled vocabularies, not text columns

**Whenever you reach for `text` for a categorical column, build a vocabulary instead.** This costs more upfront (a small table, terms with descriptions and synonyms) but Chaise's faceted search, cross-catalog interoperability, and self-documenting term descriptions all depend on the categorical column being a FK to a vocabulary rather than free text. Use `add_synonym` to absorb historical spellings without rewriting data. See `/deriva:manage-vocabulary` and `/deriva:entity-naming`.

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

These four choices are what turn a Deriva catalog from a relational database with a web UI into a FAIR (Findable, Accessible, Interoperable, Reusable) data resource.

### Deliberately not pillars

A few important Deriva concepts aren't called out as design-philosophy pillars because they're load-bearing mechanics rather than modeling stances: **foreign keys** (the standard FK semantics — see concepts.md), **association tables** (the standard many-to-many pattern — see concepts.md), and **ACLs** (catalog and Hatrac each have their own access control, but configuring them is a deployment concern, not a modeling one). The four pillars are the choices a *modeler* makes; the rest is plumbing.

<!--
Maintainer note: this skill is the canonical home for the stateless-model
framing and for plugin-wide context. Per-skill SKILL.md files and
reference docs in this plugin should NOT restate either — the always-on
load of this skill ensures the framing is in context before any other
skill triggers, and repeating it elsewhere creates drift without adding
signal. If you find yourself wanting to restate a pillar in another
skill, link back here instead.
-->
