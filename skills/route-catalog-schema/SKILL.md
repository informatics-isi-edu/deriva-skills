---
name: route-catalog-schema
description: "Use this skill for Deriva catalog structure, data exploration, and scripted operations. Covers creating or modifying tables and columns, querying or browsing catalog data, looking up records by RID, customizing how tables appear in the Chaise web UI, and writing Python scripts for catalog operations. Also covers annotation builder scripts. For vocabularies use manage-vocabulary directly. For assets use work-with-assets directly."
---

# Catalog Schema, Data, and Display

You are a router skill. Based on the user's request, load the appropriate specialized skill.


## Prerequisite: Connect to a Catalog

Most skills routed from here require an active catalog connection:

```
connect_catalog(hostname="...", catalog_id="...")
```

If already connected (check `deriva://catalog/connections`), skip this step.


## Routing Rules

Analyze the user's intent and read the matching skill:

### Creating or modifying catalog structure
- **Creating tables, asset tables, adding columns, foreign keys, column types, constraints** → Read and follow `../create-table/SKILL.md`

### Scripted catalog operations
- **Writing Python scripts for batch data loading, ETL, dataset creation pipelines, or any catalog operation needing code provenance** → Read and follow `../catalog-operations-workflow/SKILL.md`

### Querying and exploring data
- **Querying tables, filtering records, looking up by RID, counting records, sampling data, pagination, listing tables** → Read and follow `../query-catalog-data/SKILL.md`

### Customizing display
- **Setting visible columns, display names, row name patterns, column ordering, Chaise UI configuration using MCP tools** → Read and follow `../customize-display/SKILL.md`
- **Writing Python scripts with annotation builders (ColumnAnnotation, TableAnnotation, VisibleColumns, FacetList, PseudoColumn)** → Read and follow `../use-annotation-builders/SKILL.md`

### API reference
- **Understanding DerivaML method naming conventions (lookup_ vs find_ vs list_ vs get_ vs create_ vs add_)** → Read and follow `../api-naming-conventions/SKILL.md`

## Important

After identifying the correct skill, read its SKILL.md file completely and follow its instructions. Do not attempt to handle the request from this routing skill alone.
