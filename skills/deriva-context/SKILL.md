---
name: deriva-context
description: "ALWAYS load this context when the deriva plugin is active. Establishes what the deriva plugin provides (Deriva catalog operations via deriva-mcp-core), the core concepts that apply to every Deriva catalog (catalogs, schemas, tables, vocabularies, RIDs, foreign keys, asset tables, snapshots, Chaise display annotations), and Deriva's data-centric design philosophy (data is the primary artifact and the platform manages its evolution over time — Wikipedia-for-data — supported by seven pillars: stable identifiers, object/metadata separation, controlled vocabularies + FKs, deliberately relational, evolution-not-overwrite, configured UI, full web API). Triggers on: 'deriva', 'catalog', 'schema', 'vocabulary', 'rid', 'ermrest', 'hatrac', 'chaise', 'data modeling', 'controlled vocabulary', 'data-centric', 'FAIR data'."
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

### Data is the artifact

Most software platforms treat code as the primary asset and data as something the code processes. Deriva inverts that: **the data is the artifact**, and the platform exists to manage how a collection of data evolves over time — who added what, when it changed, what the previous version looked like, how a downstream result was derived, what was cited where.

The closest analogy is Wikipedia, but for structured scientific data: a continuously evolving, collaboratively curated, version-tracked, citable, openly accessible body of knowledge — except the "articles" are typed rows in tables, vocabularies, and asset references rather than prose, and the contributors are scientists, instruments, and pipelines rather than encyclopedia editors. Like Wikipedia, every change is recorded, every state is recoverable, every entity is citable, and the whole thing is accessible without special client software. Unlike Wikipedia, the data is structured: you can query it, join it, validate it, and feed it to analytical tools.

### Seven pillars that follow from data-centricity

The seven opinions below aren't arbitrary; they're the choices that fall out of taking "the data is the artifact and it evolves over time" seriously. Stable identifiers (1) so you can refer to a piece of data forever. Separation of bulk objects from metadata (2) so the structured part stays queryable while the bulk part stays scalable. Controlled vocabularies and FKs (3) so the meaning is in the data, not in a side document. The relational model (4) because that's how you get queryable evolution at scale. Snapshot-based history (5) because evolution requires that the past stays addressable. A configurable UI (6) so the data is browsable without bespoke front-end code per project. A complete web-services interface (7) so the data is reachable from any tool, any language, any pipeline.

Apply them when designing tables, choosing column types, deciding where data lives, or evaluating whether an existing model fits the platform.

### 1. Everything has an identifier

**Reference rows by RID, not by domain key.** Every row in every table gets a stable, server-minted, resolvable `RID`. Tables should FK to other tables' `RID` column, not to accession numbers, sample IDs, or file paths. Domain keys are for humans (search, citation, display); RIDs are for the system (joins, references, links, citations). Domain keys break — accessions get re-issued, file paths move, vendor IDs collide across vendors — RIDs don't.

### 2. Separate objects from metadata

Deriva keeps structured metadata (ERMrest, the catalog) and bulk bytes (Hatrac, the object store) in different systems with different scaling profiles, access patterns, lifecycles, and ACLs. They're bridged by **asset tables** — catalog rows that carry filename, size, checksum, and the Hatrac URL of the underlying object.

Two modeling implications:

- **Don't store bulk bytes in catalog columns** (`bytea`, base64-encoded blobs in JSON). Put them in Hatrac and reference them from an asset table.
- **Don't bury structured metadata in file headers or JSON sidecars.** Promote it to catalog columns where it can be queried.

### 3. Controlled vocabularies and foreign keys, not free-form values

The catalog's structure carries meaning. **Whenever you reach for `text` for a categorical column, build a vocabulary instead** and FK to it. **Whenever a column refers to another entity, declare the FK** rather than storing a stringly-typed reference.

Both choices push semantic structure into the catalog rather than leaving it implicit in data values. The payoffs: Chaise faceted search works, joins are well-typed, synonyms (`add_synonym`) absorb historical spellings without rewriting data, and the schema is self-documenting because every controlled value lives in a queryable table. Free-text categorical columns and stringly-typed references both drift over time; the relational scaffolding doesn't.

See `/deriva:manage-vocabulary`, `/deriva:create-table`, and `/deriva:entity-naming`.

### 4. Choose the relational model deliberately

Deriva is a relational platform. Not a document store, not a graph database, not a flat dump of files with a search index on top. **Model your data as tables of typed rows with explicit relationships, not as JSON blobs or as nodes-and-edges.**

This is a real choice with real implications. Document stores let you stuff anything into a record at the cost of queryability and schema discipline; graph databases optimize for arbitrary traversal at the cost of bulk analytics; flat storage punts modeling entirely. The relational model gives you structured queries, well-typed joins, schema validation, faceted UI, and an enormous ecosystem of analysis tools — provided you do the work of normalizing the data into tables. **Don't fight the model:** don't pile JSON into a single column to "preserve structure," don't model many-to-many as parent-pointer chains, don't use a vocabulary table as a dumping ground for unrelated tags. When the data really is graph-shaped or document-shaped, that's a signal it may not belong in a Deriva catalog at all.

### 5. Evolve, don't overwrite

Every change to a Deriva catalog — schema edits, row inserts, updates, deletes — is recorded with a server-side timestamp, and any past state is addressable as a snapshot. **Treat the audit trail as a feature, not a side effect.** Add a new row, update in place, or annotate the old row as superseded — but don't `delete` to erase history. Pipelines should pin to a snapshot for reproducibility; published results should cite a snapshot, not just a catalog ID. Schema evolution is supported (add columns, add tables, retire others) and old snapshots query through the schema as it was at that time.

### 6. The UI is configured, not coded

Chaise renders any Deriva catalog without per-catalog frontend code. The catalog **configures its own UI** through display annotations on schemas, tables, columns, and foreign keys: which columns are visible, what their display names are, how rows are titled, which foreign-key references are shown on detail pages, how an asset column renders (download link, image preview, etc.).

The implication: **treat the UI as part of the data model.** When you create a table, plan its display annotations alongside its columns. A catalog with no display annotations is functional but feels raw; a well-annotated catalog feels like a purpose-built application — built without writing application code. See `/deriva:customize-display`.

### 7. Everything is reachable over HTTP

ERMrest, Hatrac, and the surrounding services expose a **complete web-services interface**: schema introspection and evolution, row CRUD, vocabulary management, file upload and download, snapshot queries, display-annotation updates, ACL changes — all over HTTP. There is no out-of-band channel. The MCP tools, `deriva-py`, and Chaise are all just clients of the same API; what you can do through one, you can do through any.

The implication for modelers and operators: **don't build sneakernet data paths.** Don't manually edit the underlying database; don't email CSVs around for someone to import by hand; don't script around the API by hitting Postgres directly. Every load, mutation, and admin task should go through the documented API surface so it's auditable, scriptable, and reproducible.

### Why this matters operationally

When you're creating a new table or evaluating an existing model, ask:

- Will rows be referenced from elsewhere? → FKs use the RID, not a domain key. (1)
- Will rows have associated bulk files? → Use an asset table that bridges to Hatrac, not blob columns. (2)
- Are any columns categorical or referential? → Build vocabularies and declare FKs, even if the initial scope is small. (3)
- Is the shape really tabular? → If it's truly graph-shaped or document-shaped, reconsider the platform. (4)
- Will the data be cited or used in published results? → Pin to a snapshot, not just the catalog. (5)
- How will the data be browsed? → Plan display annotations alongside the schema. (6)
- How will data get in and out? → Through the API, not around it. (7)

Together, these choices make a Deriva catalog FAIR (Findable, Accessible, Interoperable, Reusable) by construction — not as an afterthought.

### Deliberately not pillars

A few important Deriva concepts aren't called out as design-philosophy pillars because they're load-bearing mechanics rather than modeling stances: **association tables** (the standard many-to-many pattern — a consequence of the relational model in (4); see concepts.md) and **ACLs** (catalog and Hatrac each have their own access control, but configuring them is a deployment concern, not a modeling one). The seven pillars are the choices a *modeler* or *operator* makes about how data is shaped, stored, evolved, displayed, and accessed; the rest is plumbing.

<!--
Maintainer note: this skill is the canonical home for the stateless-model
framing and for plugin-wide context. Per-skill SKILL.md files and
reference docs in this plugin should NOT restate either — the always-on
load of this skill ensures the framing is in context before any other
skill triggers, and repeating it elsewhere creates drift without adding
signal. If you find yourself wanting to restate a pillar in another
skill, link back here instead.
-->
