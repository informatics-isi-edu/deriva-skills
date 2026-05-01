---
name: route-catalog-schema
description: "Use this skill for Deriva catalog structure and data exploration. Covers creating or modifying tables and columns, querying or browsing catalog data, looking up records by RID, and customizing how tables appear in the Chaise web UI. Also covers annotation builder scripts. For vocabularies use manage-vocabulary directly. For DerivaML-specific surfaces (assets, scripted operations with execution provenance, deriva-ml API naming) use the corresponding /deriva-ml: skills if the deriva-ml-skills plugin is installed."
---

# Catalog Schema, Data, and Display

You are a router skill. Based on the user's request, load the appropriate specialized skill.


## Routing Rules

Analyze the user's intent and read the matching skill:

### Creating or modifying catalog structure
- **Creating tables, asset tables, adding columns, foreign keys, column types, constraints** → Read and follow `../create-table/SKILL.md`

### Scripted catalog operations
- **Writing Python scripts for batch data loading, ETL, or generic catalog operations** *(tier-2; deriva-ml-skills)* → If the `deriva-ml-skills` plugin is installed, read and follow `/deriva-ml:catalog-operations-workflow`. The catalog-operations-workflow skill emphasizes execution-provenance wrapping, which is a deriva-ml concept; without that plugin, write the script directly using the deriva-py API and the MCP tools listed in this router's other sections.

### Querying and exploring data
- **Schema discovery questions** ("what tables exist", "describe the schema", "what features are available", "what datasets are there") → **Use `rag_search` with `doc_type="catalog-schema"` or `"catalog-data"` directly** — no need to route to a sub-skill for simple discovery
- **Querying tables, filtering records, looking up by RID, counting records, sampling data, pagination** → Read and follow `../query-catalog-data/SKILL.md`

### Customizing display
- **Setting visible columns, display names, row name patterns, column ordering, Chaise UI configuration using MCP tools** → Read and follow `../customize-display/SKILL.md`
- **Writing Python scripts with annotation builders (ColumnAnnotation, TableAnnotation, VisibleColumns, FacetList, PseudoColumn)** → Read and follow `../use-annotation-builders/SKILL.md`

### API reference (DerivaML naming)
- **Understanding DerivaML method naming conventions (lookup_ vs find_ vs list_ vs get_ vs create_ vs add_)** *(tier-2; deriva-ml-skills)* → If the `deriva-ml-skills` plugin is installed, read and follow `/deriva-ml:api-naming-conventions`. These conventions are specific to the deriva-ml Python API; the deriva-py and deriva-mcp-core surfaces use plain CRUD verbs.

## Important

After identifying the correct skill, read its SKILL.md file completely and follow its instructions. Do not attempt to handle the request from this routing skill alone.
