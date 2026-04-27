---
name: deriva-context
description: "ALWAYS load this context when the deriva plugin is active. Establishes what the deriva plugin provides (Deriva catalog operations via deriva-mcp-core), the relationship to the optional deriva-ml-skills plugin (which adds DerivaML domain abstractions), and the principle that domain abstractions take precedence over raw catalog primitives when both are available. Triggers on: 'deriva', 'catalog', 'deriva-mcp', 'derivaml', 'dataset', 'workflow', 'execution', 'feature', 'vocabulary', 'rid', 'ermrest'."
disable-model-invocation: false
---

# Deriva Plugin Context

The `deriva` plugin provides skills for working with **any Deriva catalog** via `deriva-mcp-core`: connecting to catalogs, querying tables, creating schemas / tables / columns, managing vocabularies and terms, customizing display annotations, scaffolding Chaise web apps, and troubleshooting generic catalog errors. The skills work on plain Deriva — they do not require any DerivaML-specific plugin or domain layer.

## Core Deriva concepts (always available)

These concepts come from `deriva-mcp-core` itself and apply to every Deriva catalog you connect to:

| Concept | What | Skill |
|---|---|---|
| **Catalog** | A versioned namespace of schemas, tables, vocabularies, and rows. Identified by hostname + catalog ID (or alias). | `query-catalog-data`, `route-catalog-schema` |
| **Schema / Table / Column** | The relational structure inside a catalog. Tables can FK into other tables and into vocabularies. | `create-table`, `route-catalog-schema` |
| **Vocabulary** | A controlled-term table with standard columns (Name, Description, Synonyms, ID, URI). FK targets for categorical columns. | `manage-vocabulary` |
| **RID** | Resource Identifier — every row in every Deriva table has a unique RID (e.g., `1-A2B3`). | `query-catalog-data`, `troubleshoot-deriva-errors` |
| **Display annotations** | Per-table and per-column annotations that drive the Chaise web UI. | `customize-display`, `use-annotation-builders` |

## Relationship to the deriva-ml plugin

If the `deriva-ml` plugin is also loaded (typically via `deriva-ml-skills` + the `deriva-ml-mcp` MCP plugin), it adds **DerivaML domain abstractions** on top of plain Deriva: Datasets, Workflows, Executions, Features, and Asset_Type vocabularies. Those are first-class DerivaML concepts that happen to be stored as Deriva tables underneath — but they have business logic, FK constraints, provenance hooks, and version semantics that the raw catalog surface doesn't enforce.

> **Steering principle:** in a deriva-ml-loaded catalog you **must use the deriva-ml abstractions** (`/deriva-ml:dataset-lifecycle`, `/deriva-ml:execution-lifecycle`, `/deriva-ml:create-feature`, `/deriva-ml:work-with-assets`, the deriva-ml Python API and the dedicated MCP tools like `create_dataset`, `start_execution`, `add_feature_value`, `create_dataset_type_term`) for those concepts — **not** the raw `insert_records` / `update_record` / `get_record` core tools. The raw tools bypass DerivaML's business logic, FK validation across the Dataset/Workflow/Execution graph, provenance tracking, version management, and RAG re-indexing.

The same principle applies to four built-in DerivaML vocabularies:
- `Dataset_Type` → use `create_dataset_type_term`, not generic `add_term`
- `Workflow_Type` → use `add_workflow_type`
- `Asset_Type` → use `add_asset_type`
- `Execution_Status_Type` → managed automatically by the execution-state machine; don't extend manually

## When to use this plugin's raw catalog surface

Reach for the skills documented in *this* plugin only for catalog objects that are NOT one of the DerivaML domain concepts:

- **Custom domain tables** — `Subject`, `Sample`, `Image`, anything specific to your project's data model → `create-table`, `query-catalog-data`
- **Generic vocabularies** — anything that isn't `Dataset_Type` / `Workflow_Type` / `Asset_Type` / `Execution_Status_Type`. For example `Sample_Type`, `Tissue_Type`, `Image_Quality`, `Stain_Protocol` → `manage-vocabulary`
- **Schema introspection** — listing tables, browsing columns, reading the ERD → `browse-erd`, `query-catalog-data`
- **Display customization** — Chaise annotations on any table → `customize-display`, `use-annotation-builders`
- **Generic catalog errors** — auth, permissions, invalid RIDs, missing records, generic vocab term not found → `troubleshoot-deriva-errors`

## In a non-deriva-ml catalog

If you're connected to a Deriva catalog where the `deriva-ml-mcp` plugin is **not** loaded (a plain-Deriva research catalog, a FaceBase-style data warehouse, or an internal IT-style catalog), the DerivaML abstractions don't exist — there's no `Dataset` table, no `Execution` row, no `Feature` machinery. The skills in this plugin are then your full surface; the steering principle above doesn't apply because there's no alternative to defer to.

To check what's loaded in a given session, read `deriva://server/version` — the response includes the running deriva-mcp-core version plus the list of loaded plugins.
