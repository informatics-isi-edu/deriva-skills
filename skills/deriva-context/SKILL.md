---
name: deriva-context
description: "ALWAYS load this context when the deriva plugin is active. Establishes what the deriva plugin provides (Deriva catalog operations via deriva-mcp-core), the core concepts that apply to every Deriva catalog (catalogs, schemas, tables, vocabularies, RIDs, foreign keys, asset tables, snapshots, Chaise display annotations), and Deriva's data-centric design (data is the primary artifact and the platform manages its evolution over time — Wikipedia-for-data — with an operational checklist for whether a model fits the platform; full philosophy in references/philosophy.md). Triggers on: 'deriva', 'catalog', 'schema', 'vocabulary', 'rid', 'ermrest', 'hatrac', 'chaise', 'data modeling', 'controlled vocabulary', 'data-centric', 'FAIR data'."
disable-model-invocation: false
---

# Deriva Plugin Context

## What is Deriva?

Deriva is a data-centric platform for managing scientific data: structured metadata (in a versioned, queryable catalog) plus bulk objects (in an object store) plus a configurable web UI (Chaise) plus a complete HTTP API. Think Wikipedia for structured data — every change recorded, every state recoverable, every entity citable, accessible from any tool. The `deriva` plugin lets you work with any Deriva catalog through the `deriva-mcp-core` MCP server and the `deriva-py` Python client.

**First time touching a Deriva catalog this session?** Start with `/deriva:route-catalog-schema` to explore an existing catalog before you mutate anything. Hit an auth or permission error? Go straight to `/deriva:troubleshoot-deriva-errors`.

**Out of scope for this plugin:** domain-specific abstractions that build *on top of* a catalog (project-specific concepts like "experiment," "sample lineage," "ML execution"). Those layered models live in their own plugins or libraries (e.g., the companion `deriva-ml` plugin handles ML workflows). When a user mentions a concept that's specific to a domain layer rather than the catalog primitives below, hand off to the relevant domain plugin if one is loaded.

## Concept and skill index

These concepts come from `deriva-mcp-core` and apply to every Deriva catalog. Each row points at the skill that handles operations on it; this table doubles as the task router. For deeper definitions, see `references/concepts.md`.

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
| **Catalog errors** | Auth, permissions, invalid RIDs, missing records, vocab term not found. | `/deriva:troubleshoot-deriva-errors` |
| **Server reachability** | `server_status(hostname=...)` returns the running framework version and loaded plugins. | (no skill — direct tool call) |

> **When to read `references/concepts.md`:** on cold-start (first Deriva-related action of the session), or any time you encounter a concept above whose mechanics you don't have a working model of — RID format, vocabulary column shape, snaptime semantics, asset-table column shape, association-table conventions. The reference is mechanics-focused (what each thing *is* and how it works); the design philosophy in `references/philosophy.md` is opinion-focused (what to *do* with it).

## Stateless model

The `deriva-mcp-core` server is stateless. Every tool call takes `hostname=` and `catalog_id=` arguments — there is no implicit "active catalog" or "default schema". Every example in every skill in this plugin shows the full parameter set; substitute your catalog's hostname and ID.

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
| How will data get in and out? | Through the API, not around it. | 7. Full HTTP interface |

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
