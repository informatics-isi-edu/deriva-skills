---
name: route-catalog-schema
description: "Use this skill for Deriva catalog structure and data exploration. Covers creating or modifying tables and columns, querying or browsing catalog data, looking up records by RID, and customizing how tables appear in the Chaise web UI. For vocabularies use manage-vocabulary directly."
---

# Catalog Schema, Data, and Display

You are a router skill. Based on the user's request, load the appropriate specialized skill.


## Routing Rules

Analyze the user's intent and read the matching skill:

### Creating or modifying catalog structure
- **Creating tables, asset tables, adding columns, foreign keys, column types, constraints** → Read and follow `../create-table/SKILL.md`

### Querying and exploring data
- **Schema discovery questions** ("what tables exist", "describe the schema", "what features are available", "what datasets are there") → **Use `rag_search` with `doc_type="catalog-schema"` or `"catalog-data"` directly** — no need to route to a sub-skill for simple discovery
- **Querying tables, filtering records, looking up by RID, counting records, sampling data, pagination** → Read and follow `../query-catalog-data/SKILL.md`

### Customizing display
- **Setting visible columns, display names, row name patterns, column ordering, Chaise UI configuration using MCP tools** → Read and follow `../customize-display/SKILL.md`

## Important

After identifying the correct skill, read its SKILL.md file completely and follow its instructions. Do not attempt to handle the request from this routing skill alone.
