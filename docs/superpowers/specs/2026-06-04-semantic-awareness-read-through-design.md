# Align find-before-create skills with read-through RAG indexing

**Date:** 2026-06-04
**Repos:** `deriva-skills` (Part A) + `deriva-ml-skills` (Part B)
**Status:** Approved (design)

## Problem

`deriva-ml-mcp-plugin` PR #70 replaced connect-time bulk indexing of
Dataset/Workflow/Execution rows with **read-through (index-on-find)**
indexing: those rows enter the `catalog-data` RAG index only after
they've been listed/fetched (the list/get tools warm them) or mutated
(surgical reindex), or via the manual `deriva_ml_resync_indexes` tool.
It also added structured `dataset_type` / `workflow_type` filters.

Two find-before-create skills now carry claims that are no longer
accurate, and miss the structured-vs-fuzzy routing the new filters
enable:

- **`deriva-skills/skills/semantic-awareness`** (the generic catalog
  guardrail) says "Search first with `rag_search` — the index covers
  schema, vocabulary terms, and data." Under read-through indexing,
  data records are only searchable *after* a list/fetch warms them, so
  "rag_search first" can miss un-warmed data rows.
- **`deriva-ml-skills/skills/deriva-ml-context`** ("entity resolution
  workflow" step 2) routes datasets/workflows/executions to
  `rag_search(doc_type="catalog-data")` without noting the warm
  dependency or the deterministic alternatives.

## Boundary decision

The read-through change has a **generic** part and an **ML-specific**
part, and they land in different plugins:

- **Generic truth → `semantic-awareness`** (`deriva-skills`): read-through
  indexing means *any* `catalog-data` row is searchable only after a
  list/fetch warms it, so do the structured `list`/`find` step **before**
  relying on `rag_search` for data records; and route a fully-structured
  query (by a type/status/ID) to the deterministic `list`/`find` filter
  rather than fuzzy search. **No ML tool names** — keeps the generic
  plugin generic (respects the standalone "works on any Deriva catalog"
  framing; see the 2026-05-25 audit P1.2).
- **ML-specific routing → `deriva-ml-context`** (`deriva-ml-skills`): the
  concrete tools (`deriva_ml_list_datasets(dataset_type=...)`,
  `deriva_ml_find_workflow_by_url` for content-addressed workflow dedup),
  which ML entities warm on read, and `deriva_ml_resync_indexes`.

## Part A — `deriva-skills/skills/semantic-awareness`

### A1. SKILL.md step 1 (the always-loaded discipline)

Current (line ~18):
> **Search first** with `rag_search` — the catalog's RAG index covers
> schema, vocabulary terms (with synonyms), and data, so it handles the
> fuzzy matching... Use `doc_type="catalog-schema"` for tables / columns
> / vocabulary terms; `doc_type="catalog-data"` for data records.

Reframe to (generic, no ML tool names) — the discipline becomes
*route then search*:
- `rag_search` is reliable for **schema and vocabulary terms** — these
  are indexed catalog-wide and searchable immediately.
- For **data records**, the `catalog-data` index is populated
  **read-through**: a row becomes searchable once it's been listed or
  fetched (the read warms it). So **do the structured `list`/`find`
  step first** — it both narrows deterministically *and* warms the
  index — then use `rag_search` for fuzzy ranking over the warmed rows.
- When a query is **fully specified by a structured attribute** (a type,
  a status, an ID), prefer the deterministic `list`/`find` filter — no
  fuzzy search needed.
- Keep the `doc_type` guidance (`catalog-schema` for tables/columns/
  vocab terms; `catalog-data` for data records).

### A2. references/find-before-you-create.md step 3 ("Query the catalog")

Same reframing at operational depth (lines ~30-55). Currently it leads
with "Use `rag_search` as the primary discovery tool" for everything.
Update to:
- Distinguish schema/vocab (search immediately) from data records
  (list/find first to warm + narrow, then rag_search to rank).
- Add the structured-vs-fuzzy-vs-hybrid routing: structured attribute →
  deterministic filter; free-text description → `rag_search`; both →
  filter to narrow, then rank. Stated generically.
- Keep the existing `rag_search` examples and the dedicated-tool
  fallbacks; reorder so the structured/warm step precedes the fuzzy step
  for data records.

### A3. Bonus: fix the duplicate `4.` (audit P1.4)

SKILL.md lines 21-22 both label `4.` (the EAV/wide-table item and the
"Decide: reuse, extend, or create" item collide; the list then has
5/6 mislabeled). Renumber 4→…→6 correctly while editing the file.

## Part B — `deriva-ml-skills/skills/deriva-ml-context` (concise, in place)

Two existing spots, edited in place — no new section.

### B1. "The entity resolution workflow" step 2 (lines ~225-228)

Currently: *"call `rag_search` with their phrase. Use the appropriate
`doc_type`: … `catalog-data` for datasets, workflows, executions."*

Add: datasets/workflows/executions are indexed **read-through** — they
become `rag_search`-able once you've listed/fetched them (the list/get
tools warm them) or after a mutation, or via
`deriva_ml_resync_indexes(hostname, catalog_id)` to warm a catalog's
rows on demand. So for these entities, prefer the structured path first:
- **"find Training datasets"** → `deriva_ml_list_datasets(dataset_type="Training")`
  (deterministic; also warms the index).
- **executions by status/type** → `deriva_ml_list_executions(...)`.
- **workflow dedup** → `deriva_ml_find_workflow_by_url` (workflows are
  content-addressed: same URL + commit = same row; this is the exact,
  deterministic dedup — better than fuzzy `rag_search`).
- **hybrid** ("Training datasets matching `<description text>`") →
  structured filter to narrow, then `rag_search` to rank within.

### B2. The line-152 RAG note

Currently: *"the `deriva_ml_*` tools fire surgical re-index hooks so
freshly mutated rows are searchable on the next `rag_search`."*

Extend: in addition to the surgical reindex on mutate, the read tools
(`deriva_ml_list_*` / `deriva_ml_get_*`) warm each row they return
(read-through), so listing/fetching a row makes it `rag_search`-able;
`deriva_ml_resync_indexes` warms a whole catalog's rows on demand.

## Out of scope

- Any code change (the plugin code already shipped in PR #70).
- New sections / restructuring of either skill — surgical edits only.
- Other audit items (P0/P1/P2) beyond the P1.4 numbering fix that sits
  in the file being edited anyway.

## Test / verification

These are prose-only skill docs (no executable tests). Verification:
- Re-read each edited section for accuracy against the shipped
  read-through behavior.
- Confirm `semantic-awareness` still references **zero** ML tool names
  after the edit (`grep -i "deriva_ml_\|dataset_type\|workflow_type\|
  find_workflow_by_url" skills/semantic-awareness/` → empty).
- Confirm the SKILL.md numbered list is sequential (no duplicate `4.`).
- If either plugin has a skill-doc linter / eval, run it.
