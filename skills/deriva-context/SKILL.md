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
