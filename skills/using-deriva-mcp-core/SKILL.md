---
name: using-deriva-mcp-core
description: "ALWAYS load before the first deriva-mcp-core MCP call in any conversation. The deriva-mcp-core server ships four guide prompts (query_guide, entity_guide, annotation_guide, catalog_guide) describing the conventions for each generic-catalog tool group; Claude Code does not auto-inject them, so read the one that covers the tool group you are about to use, before that first call. This skill carries the generic cold-start discipline: the (hostname, catalog_id) rule, the pagination preflight->page->advance contract, the error envelope, and which guide to fetch for which tool group. Triggers on: first-time use of generic deriva-mcp-core tools (query_attribute, query_aggregate, count_table, get_entities, insert_entities, update_entities, delete_entities, get_schema, get_catalog_info, create_catalog, set_*_display, set_visible_columns, add_term, create_table, etc.) or deriva:// resources, AND any catalog inspection / mutation request where you are about to reach for one of those tools ('query the catalog', 'insert rows', 'change the schema', 'set up display', 'create a catalog'). Do NOT trigger for the DerivaML domain layer — when the deriva-ml plugin is loaded, its /deriva-ml:using-deriva-mcp owns cold-start (it layers the deriva_ml_primer on top of this); and do NOT trigger for shell-only / deriva-py-script workflows that never cross the MCP boundary."
user-invocable: true
disable-model-invocation: false
---

# Cold-start for the deriva-mcp-core MCP surface

You are about to make a call against a Deriva catalog through the
`deriva-mcp-core` MCP server — a generic-catalog tool (`query_attribute`,
`get_entities`, `set_visible_columns`, `create_catalog`, `add_term`, …) or a
`deriva://...` resource. **Before the first such call in a conversation, read
the guide prompt for the tool group you are about to use.** The server ships
the guides precisely so the LLM loads each group's conventions once per
conversation rather than rediscovering them by trial and error; Claude Code
does not inject them automatically, so you have to fetch them.

This skill is the trigger; the guide prompts are the rules. The conceptual
frame (what a catalog/schema/RID/vocabulary/asset-table *is*, and the
resource-first reads rule) lives in the always-on `/deriva:deriva-context`
skill — this skill makes sure you've read the server's own procedural
material before the first tool fires.

> **Reads first: prefer the `deriva://` resource over a list-style tool.**
> For read-shaped questions ("what tables are in this catalog?", "what's the
> schema?", "server status?") the resource form is one round trip, page-free,
> cached, and emits no audit row. The four core resource templates and the
> resource-first rule are documented in `/deriva:deriva-context` ("Reads:
> resource URIs first, tools as fallback"). Reach for a tool only when the
> question has a filter or needs pagination the resource doesn't expose.

## The cold-start, in two moves

**Move 1 — read the guide for your tool group, once.** Each guide describes
the path syntax, argument shapes, preflight rules, and display conventions for
its group. Read whichever applies to your first call; you only need each one
once per conversation (they are stable references, not per-call setup):

| If your first call uses... | Read this guide first |
|----|----|
| `query_attribute`, `query_aggregate`, `count_table` | `/<server>:query_guide` |
| `get_entities`, `insert_entities`, `update_entities`, `delete_entities` | `/<server>:entity_guide` |
| `get_table_annotations`, `get_column_annotations`, `set_*_display`, `set_visible_columns`, `add_visible_column`, `reorder_visible_columns`, etc. | `/<server>:annotation_guide` |
| `create_catalog`, `clone_catalog`, `delete_catalog`, `get_catalog_info`, `get_schema` | `/<server>:catalog_guide` |

Replace `<server>` with whatever the MCP server is registered as — commonly
`deriva`, sometimes `dev-localhost`, sometimes project-specific. Claude Code
surfaces MCP prompts under the fully-qualified form
`/mcp__<server>__<name>` (e.g. `/mcp__deriva__query_guide`); the
`/<server>:<name>` form here is the same prompt written for brevity. If
`ListMcpResourcesTool({server: "<name>"})` returns successfully, that's the
right name.

**Move 2 — honor the two generic conventions that every tool group shares.**
These are not in any single guide because they apply across all of them:

- **The `(hostname, catalog_id)` rule.** Every generic catalog tool takes
  `hostname=` and `catalog_id=` explicitly. There is no implicit "current
  catalog" and no `connect` step — the server is stateless. Pass the same pair
  on every call; different values just address different catalogs.
- **The preflight -> page -> advance pagination contract.** For tools that can
  return many rows, call once to learn the count, choose a limit, fetch a page,
  and advance with the returned cursor when the result is truncated. Don't
  fetch unboundedly. The per-tool specifics (argument names, cursor token) are
  in the relevant guide; the *shape* is the same everywhere.
- **The error envelope.** A failing tool returns a structured error payload
  rather than the success shape. Read the message — it usually names the
  failing RID or qname — and correct the call rather than retrying verbatim.

## What you should NOT do

- **Skip the guide and hit a tool directly.** Without `query_guide` you will
  pass `schema` + `table` + `filter` to `query_attribute` instead of a `path`
  expression; without `entity_guide` you will miss the preflight-count rule on
  bulk writes. The guides exist to prevent exactly these wasted calls.
- **Re-read a guide you've already loaded.** Once per conversation per group is
  enough — they describe stable conventions.
- **Reach for a list-style tool when a `deriva://` resource answers the same
  read.** See the resource-first rule in `/deriva:deriva-context`.

## Relationship to other skills

- **`/deriva:deriva-context`** *(always-loaded sibling)* — the conceptual
  frame and the resource-first reads rule. That skill teaches *what* the
  catalog is and *why* resources beat list-tools for reads; this skill makes
  sure you've read the server's procedural guides before the first tool call.
  Both should be active before the first MCP call.
- **`/deriva:getting-started`** *(this plugin)* — the human-facing five-step
  onboarding walkthrough (verify connection -> explore -> sample -> mutate ->
  load). That is a *user* journey; this skill is the *LLM's* protocol
  cold-start. They sit at different layers and don't overlap.
- **`/deriva-ml:using-deriva-mcp`** *(deriva-ml-skills, if loaded)* — the
  DerivaML domain cold-start. When the deriva-ml plugin is present, it owns
  cold-start: it routes the four generic guides above exactly as this skill
  does, and additionally bootstraps the DerivaML orientation via the
  `deriva_ml_primer` tool. If both plugins are loaded, the domain skill is the
  entry point and this skill is the generic half it builds on.
