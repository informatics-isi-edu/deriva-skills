---
name: deriva-context
description: "ALWAYS load this context when the deriva plugin is active. Establishes what the deriva plugin provides (Deriva catalog operations via deriva-mcp-core), the core concepts that apply to every Deriva catalog (catalogs, schemas, tables, vocabularies, RIDs, foreign keys, asset tables, snapshots, Chaise display annotations), and Deriva's data-centric design (data is the primary artifact and the platform manages its evolution over time — Wikipedia-for-data — with an operational checklist for whether a model fits the platform; full philosophy in references/philosophy.md). Triggers on: 'deriva', 'catalog', 'schema', 'vocabulary', 'rid', 'ermrest', 'hatrac', 'chaise', 'data modeling', 'controlled vocabulary', 'data-centric', 'FAIR data'."
disable-model-invocation: false
---

# Deriva Plugin Context

## What is Deriva?

Deriva is a data-centric platform for managing scientific data: structured metadata (in a versioned, queryable catalog) plus bulk objects (in an object store) plus a configurable web UI (Chaise) plus a complete HTTP API. Think Wikipedia for structured data — every change recorded, every state recoverable, every entity citable, accessible from any tool. The `deriva` plugin lets you work with any Deriva catalog through the `deriva-mcp-core` MCP server and the `deriva-py` Python client.

**First time touching a Deriva catalog this session, or new to Deriva entirely?** Run `/deriva:getting-started` for a five-step onboarding walkthrough (verify the connection → explore the schema → look at real rows → make a small safe mutation → load data) with explicit handoffs to the per-task skills. Already oriented and just want to explore? `/deriva:query-catalog-data` covers cold-start exploration via `rag_search`. Hit an auth or permission error? `/deriva:troubleshoot-deriva-errors`.

**Out of scope for this plugin:** domain-specific abstractions that build *on top of* a catalog (project-specific concepts like "experiment," "sample lineage," "ML execution"). Those layered models live in their own plugins or libraries. When a user mentions a concept that's specific to a domain layer rather than the catalog primitives below, hand off to the relevant domain plugin if one is loaded.

> **DerivaML work?** If the user's task involves training models, running experiments, managing datasets-as-first-class-objects, features (per-row labels/scores), or DerivaML asset lifecycles, the companion [`deriva-ml`](https://github.com/informatics-isi-edu/deriva-ml-skills) plugin is the right surface. Install it from the same `informatics-isi-edu/deriva-plugins` marketplace (`/plugin install deriva-ml`) and route to `/deriva-ml:help` for orientation. If `deriva-ml` is loaded, its abstractions (Datasets, Workflows, Executions, Features, Asset_Type vocabularies) take precedence over the raw catalog primitives this plugin documents — don't apply `insert_entities` / `update_entities` to those concepts; use the `/deriva-ml:` skills instead. If `deriva-ml` is *not* loaded, this plugin's catalog primitives are the right surface for everything.

## Concept and skill index

These concepts come from `deriva-mcp-core` and apply to every Deriva catalog. Each row points at the skill that handles operations on it; this table doubles as the task router. For deeper definitions, see `references/concepts.md`.

| Concept | What it is | Skill |
|---|---|---|
| **Catalog** | A versioned namespace of schemas, tables, vocabularies, and rows. Identified by hostname + catalog ID (or alias). | `/deriva:query-catalog-data` |
| **Schema / Table / Column** | The relational structure inside a catalog. Tables can FK into other tables and into vocabularies. | `/deriva:create-table`, `/deriva:query-catalog-data`; for non-additive changes (rename, split, merge, retype, FK move) → `/deriva:evolve-schema` |
| **Vocabulary** | A controlled-term table with standard columns (Name, Description, Synonyms, ID, URI). FK target for categorical columns. | `/deriva:manage-vocabulary` |
| **RID** | Resource Identifier — every row in every Deriva table has a unique, server-minted, resolvable RID (e.g., `1-A2B3`). | `/deriva:query-catalog-data`, `/deriva:troubleshoot-deriva-errors` |
| **Foreign keys** | The relational glue. FKs target RID columns; FKs to vocabularies model categorical values. | `/deriva:create-table` |
| **Association tables** | The standard pattern for many-to-many relationships: a table with two FKs, one to each side. | `/deriva:create-table` |
| **Asset tables + Hatrac** | Catalog rows that bridge to objects in Deriva's object store (filename, size, checksum, URL). | `/deriva:create-table`, `/deriva:customize-display` |
| **Catalog snapshots** | Time-travelable history. Any past state is queryable by snaptime; pin a snaptime for reproducibility — and capture one before any bulk load or schema change as a rollback reference. | `/deriva:load-data` (load-side use), `/deriva:evolve-schema` (migration-side use); mechanics in `references/concepts.md` |
| **Display annotations** | Per-table / per-column JSON that drives the Chaise web UI. | `/deriva:customize-display` |
| **Naming conventions** | PascalCase, singular nouns, descriptive — for schemas, tables, columns, and vocabulary terms. | `/deriva:entity-naming` |
| **Loading data** | Row inserts, batch loads from CSV/JSON, asset uploads to Hatrac (MCP tool, `deriva-upload-cli`, or `DerivaUpload` Python class with an upload spec), updates, deletes. | `/deriva:load-data` |
| **Exporting data as a BDBag** | Self-describing, checksummed archive of a catalog slice + FK-reachable rows + Hatrac assets. Two paths: server-side export service (`DerivaExport`) or client-side orchestration (`deriva-download-cli` / `DerivaDownload`). Inverse of loading. | `/deriva:download-bag` |
| **Catalog errors** | Auth, permissions, invalid RIDs, missing records, vocab term not found. | `/deriva:troubleshoot-deriva-errors` |
| **Server reachability** | Read the `deriva://server/status` resource — returns the running framework version and loaded plugins. | (no skill — direct resource read) |

> **When to read `references/concepts.md`:** on cold-start (first Deriva-related action of the session), or any time you encounter a concept above whose mechanics you don't have a working model of — RID format, vocabulary column shape, snaptime semantics, asset-table column shape, association-table conventions. The reference is mechanics-focused (what each thing *is* and how it works); the design philosophy in `references/philosophy.md` is opinion-focused (what to *do* with it).

> **Linking to RIDs: use `/id/`, not Chaise URIs.** When a description, annotation, or any other piece of stored catalog content needs to link to a row, use the catalog's UI-agnostic `/id/` resolver — `/id/<catalog>/<rid>` (catalog-relative is the default; absolute `https://<host>/id/<catalog>/<rid>` is only for contexts outside the catalog). **Never** link via a Chaise-specific path like `/chaise/record/#<catalog>/schema:Table/RID=<rid>`. The `/id/` form survives UI changes and works under any host serving the catalog; the `/chaise/...` form ties the link to one particular UI and breaks if the deployment changes.

> **RIDs are opaque: equality only, no literals, no parsing.** A RID's only valid operation is equality comparison. **Never** hard-code a RID as a literal in tests, fixtures, scripts, or configs — obtain RIDs from a fresh catalog lookup or fixture call, never from a string written by a human. **Never** parse, slice, regex, or `.startswith()` on a RID — the format is an implementation detail. **Never** compare RIDs across catalogs (the unit of identity across catalogs is `(host, catalog_id, RID)`), and don't infer column values from a RID across snaptimes (RID identity is constant; row data is not). The failure mode for violating any of these is silent: literal/derived RIDs round-trip in dev and break in prod the first time a real RID flows through the same code. Full discussion in `references/concepts.md` under "RID opacity rule."

## Stateless model

The `deriva-mcp-core` server is stateless. Every tool call takes `hostname=` and `catalog_id=` arguments — there is no implicit "active catalog" or "default schema". Every example in every skill in this plugin shows the full parameter set; substitute your catalog's hostname and ID.

## Reads: resource URIs first, tools as fallback

For read-shaped questions ("what tables are in this catalog?", "what's the schema look like?", "show me one table's columns"), prefer the `deriva://` resource form over the equivalent tool call. The resource form is one round trip, page-free, cached, and produces no audit-log entries — strictly preferable for reads.

`deriva-mcp-core` ships four resource templates:

| URI | Returns | Equivalent tool (use only when you need filters / paginated browsing) |
|---|---|---|
| `deriva://server/status` | Server health, framework version, list of loaded plugins | (no tool equivalent — resource is the only path) |
| `deriva://catalog/{hostname}/{catalog_id}/schema` | Full catalog schema JSON | `get_schema(hostname, catalog_id)` |
| `deriva://catalog/{hostname}/{catalog_id}/tables` | All tables, grouped by schema, with row counts | (no tool equivalent — resource is the only path) |
| `deriva://catalog/{hostname}/{catalog_id}/table/{schema}/{table}` | One table's complete structure | `get_table(hostname, catalog_id, schema, table)` |

Read a resource with `ReadMcpResourceTool(uri="...")` — the URI is constructable from the hostname and catalog_id, no tool lookup needed. **The failure mode this rule prevents:** reaching reflexively for a list-style tool when the same answer is already cached at a resource URI. The cost of an unnecessary tool call is one audit row + one round trip; the cost of an unnecessary list-fetch + filter cycle is several.

For read-shaped questions with **filters** (e.g., "tables in this schema whose names contain `Image`"), or paginated browsing beyond what a single resource fetch returns, the corresponding tool is the right answer. The rule is "resource first, tool as fallback when the shape genuinely doesn't fit."

## Modeling checklist

When you're creating a new table or evaluating an existing model, work through these seven questions. Each maps to one of the seven design pillars; the full rationale for each pillar is in `references/philosophy.md`.

| Question | Action | Pillar |
|---|---|---|
| Will rows be referenced from elsewhere? | FKs use the RID, not a domain key. | 1. Stable identifiers |
| Will rows have associated bulk files? | Use an asset table that bridges to Hatrac, not blob columns. | 2. Object/metadata separation |
| Are any columns categorical or referential? | Build vocabularies and declare FKs, even if the initial scope is small. | 3. Vocabularies + FKs carry meaning |
| Is the shape really tabular? | If it's truly graph-shaped or document-shaped, reconsider the platform. | 4. Deliberately relational |
| Will the data be cited or used in published results? | Pin to a snapshot, not just the catalog. | 5. Evolve, don't overwrite |
| How will the data be browsed? | Plan display annotations alongside the schema. | 6. Configured UI |
| How will data get in and out? | Through the API, not around it — see `/deriva:load-data` for the load side and `/deriva:query-catalog-data` for the read side. | 7. Full HTTP interface |

Together, these choices make a Deriva catalog FAIR (Findable, Accessible, Interoperable, Reusable) by construction. Read `references/philosophy.md` when designing a new schema, evaluating whether Deriva fits a project, or explaining the platform's worldview to a collaborator.

<!--
Maintainer note: this skill is the canonical home for the stateless-model
framing and for plugin-wide context. Per-skill SKILL.md files and
reference docs in this plugin should NOT restate either — the always-on
load of this skill ensures the framing is in context before any other
skill triggers, and repeating it elsewhere creates drift without adding
signal. The full design philosophy lives in references/philosophy.md;
the in-context checklist above is the only philosophy content that
loads on every conversation.
-->
