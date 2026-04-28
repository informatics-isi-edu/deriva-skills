---
name: manage-vocabulary
description: "ALWAYS use this skill when creating or managing controlled vocabularies in Deriva — creating vocabulary tables, adding terms with descriptions and synonyms, browsing existing vocabularies, and deciding whether to create a new vocabulary vs extend an existing one. Triggers on: 'create vocabulary', 'add term', 'add synonym', 'vocabulary', 'controlled terms', 'categorical labels', 'what vocabularies exist', 'browse terms', 'extend vocabulary'."
user-invocable: true
disable-model-invocation: true
---

# Managing Controlled Vocabularies

Controlled vocabularies are the standard way to represent categorical data in Deriva. They provide consistent labeling, faceted search in Chaise, and synonym support for discoverability. Every vocabulary is a table with standard columns: Name, Description, Synonyms, ID, and URI.

Vocabularies are referenced as foreign-key targets from any categorical column in your domain schema — subject species, sample type, image quality grade, instrument calibration status, and so on.

> **Note (deriva-ml environments):** if the `deriva-ml-mcp` plugin is loaded in this catalog, DerivaML ships several built-in vocabularies (`Dataset_Type`, `Workflow_Type`, `Asset_Type`, `Execution_Status_Type`) under the `deriva-ml` schema. Use the generic `add_term` / `delete_term` / `add_synonym` tools documented here to manage these vocabularies — pass `schema="deriva-ml"` and `table="Dataset_Type"` (etc.) to the standard tools. The `deriva-ml-mcp` plugin used to ship dedicated extender tools (`create_dataset_type_term`, `add_workflow_type`, `add_asset_type`) but those were removed in favor of the generic vocabulary surface; the new tools handle the same business logic transparently because vocabulary tables are managed by `deriva-mcp-core` directly. See the `dataset-lifecycle`, `create-feature`, and `work-with-assets` skills in `deriva-ml-skills` for the broader DerivaML domain workflows.


## Stateless model

The new MCP server is stateless — every tool below takes `hostname=` and `catalog_id=` arguments explicitly. There is no `connect_catalog` step. Substitute your catalog's hostname and catalog ID wherever the examples show them.


## Phase 1: Assess

Before creating or modifying a vocabulary, determine whether one is needed and whether it already exists.

### Do I need a new vocabulary?

| Situation | Action |
|-----------|--------|
| Need categorical labels for features | Create a vocabulary (features require vocab terms) |
| Need consistent values for a table column | Create a vocabulary and FK-reference it |
| Adding terms to an existing category | Extend the existing vocabulary with `add_term` |
| Need a variant of an existing vocabulary | Usually extend, not duplicate. Add terms or synonyms |
| Values are free-text, not categorical | Don't use a vocabulary — use a text column |

### Search existing vocabularies

**Start with `rag_search`** to discover vocabularies and terms by concept. The RAG index includes all vocabulary terms with their descriptions and synonyms, making it ideal for fuzzy matching:
```
rag_search("species organism", doc_type="catalog-schema")
rag_search("image quality grade", doc_type="catalog-schema")
```

Then use the dedicated tools for full structured details:

```python
# Browse terms in a specific vocabulary
list_vocabulary_terms(
    hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Species",
)

# Look up a specific term (synonym-aware — finds "X-ray" if there's a "Xray" synonym)
lookup_term(
    hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Species", name="Mouse",
)
```

To **list all vocabulary tables in a catalog**, call `catalog_tables(...)` and filter for tables that have the standard vocabulary columns (Name, Description, Synonyms, ID, URI), or use `rag_search(..., doc_type="catalog-schema")` to find them by concept.

## Description Guidance

### Vocabulary Tables

The `comment` on a vocabulary table should explain the classification scheme, its scope, and how terms relate to each other.

**Good vocabulary descriptions:**
- "Classification of biological tissue types for histology analysis. Terms are mutually exclusive tissue categories used for slide-level labeling"
- "Image quality assessment grades assigned during manual QC review. Ordered from best to worst: excellent > acceptable > borderline > rejected"
- "CIFAR-10 object categories. 10 mutually exclusive classes spanning vehicles and animals"

**Bad vocabulary descriptions:**
- "Types" or "Categories" or "A vocabulary"

For description templates and quality guidelines, see the `generate-descriptions` skill.

### Vocabulary Terms

Every term must have a description that defines its meaning in context — not just restating the name. Explain when to use the term, and how it relates to other terms.

**Good term descriptions:**
- "Pneumonia detected in chest X-ray. Use when radiological signs of pneumonia are present regardless of etiology. Mutually exclusive with 'normal'"
- "Borderline image quality — minor artifacts present but image is usable for training with caution. Review if model performance on this subset is unexpectedly poor"

**Bad term descriptions:**
- "Pneumonia" or "This is the pneumonia term" or leaving it empty

## Find before you create

> The current `deriva-mcp-core` + `deriva-ml-mcp` server stack does NOT perform automatic duplicate detection on `create_vocabulary` or `add_term`, and does NOT provide "did you mean?" suggestions on missing references (the legacy `deriva-mcp` server had both; neither was ported to the cut-over architecture). Restoring them is an open upstream item. Until then, the skill-level workflow is the only guardrail: before creating a vocabulary or adding a term, run `rag_search` against the catalog schema (`doc_type="catalog-schema"`) to find similar entities. Present a picker if multiple plausible matches turn up. See the `semantic-awareness` skill for the full workflow.

## Phase 2: Design

### Vocabulary design decisions

| Question | Guidance |
|----------|---------|
| Flat vs hierarchical? | Deriva vocabularies are flat (no parent-child terms). Use separate vocabularies for different levels of hierarchy (e.g., `Organ` and `Tissue_Type` rather than a single nested vocabulary) |
| How many terms? | Start small, add terms as needed. A vocabulary with 3-10 terms is typical. Hundreds is fine for standardized ontologies |
| Granularity? | Terms should be at the level where you'll filter/group data. Too fine = unused terms. Too coarse = lost information |
| Naming? | PascalCase with underscores: `Tissue_Type`, `Image_Quality`. Singular form |
| Who should add terms? | Anyone with write access can add terms. Vocabularies are shared across the catalog — coordinate with your team |

### Orthogonal vocabularies

Prefer separate, orthogonal vocabularies over one large vocabulary that combines concepts. For example:
- **Good**: `Image_Modality` (MRI, CT, X-ray) + `Image_Quality` (Good, Acceptable, Poor)
- **Bad**: `Image_Category` (MRI_Good, MRI_Poor, CT_Good, CT_Poor, ...)

Orthogonal vocabularies compose — you can filter by modality AND quality independently. Combined vocabularies create a combinatorial explosion.

## Phase 3: Create

```python
create_vocabulary(
    hostname="data.example.org", catalog_id="1",
    schema="myproject",                   # which schema to create the vocab table in
    vocabulary_name="Tissue_Type",        # PascalCase with underscores
    comment="Classification of biological tissue types for histology analysis",  # required
)
```

This creates a table in the named schema with the standard vocabulary columns (Name, Description, Synonyms, ID, URI).

**Naming conventions:**
- Use `PascalCase` with underscores between words: `Tissue_Type`, `Image_Quality`, `Stain_Protocol`
- Name should be the singular form of what the terms represent
- Keep names concise but specific

## Adding Terms

```python
add_term(
    hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Tissue_Type",
    name="Hyaline Cartilage",
    description="Smooth, glassy cartilage covering joint surfaces; lacks blood vessels and nerves",
    synonyms=["Articular Cartilage"],     # optional
)
```

**Every term must have a meaningful description.** Descriptions appear as tooltips in the Chaise UI. Avoid descriptions that just restate the name — explain what the term means in context.

## Adding Synonyms

Synonyms make terms discoverable under alternative names, abbreviations, or common misspellings.

```python
add_synonym(
    hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Tissue_Type",
    name="Hyaline Cartilage",
    synonym="Articular Cartilage",
)
```

Synonyms are searchable via `lookup_term(...)` (the new MCP surface's synonym-aware lookup). For guidance on when to use synonyms vs creating new terms, see `references/patterns.md`.

## Removing Terms and Synonyms

```python
# Remove a synonym
remove_synonym(
    hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Tissue_Type",
    name="Hyaline Cartilage", synonym="Articular Cartilage",
)

# Delete a term (only works if no records reference it; otherwise fails with FK error)
delete_term(
    hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Tissue_Type",
    name="Hyaline Cartilage",
)
```

## Updating Term Descriptions

```python
update_term_description(
    hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Tissue_Type",
    name="Hyaline Cartilage",
    description="Updated description...",
)
```

## Workflow: Adding Terms to an Existing Vocabulary

1. **Search first** — `lookup_term(...)` to check if the term (or a synonym) already exists
2. **Add the term** with a meaningful description (and optional synonyms)
3. **Add additional synonyms** for common alternate names if not provided at creation
4. **Verify** — `list_vocabulary_terms(...)` to confirm

## Reference Tools

- `create_vocabulary(hostname, catalog_id, schema, vocabulary_name, comment)` — Create a new vocabulary table
- `add_term(hostname, catalog_id, schema, table, name, description, synonyms=...)` — Add a term
- `delete_term(hostname, catalog_id, schema, table, name)` — Remove a term
- `add_synonym(hostname, catalog_id, schema, table, name, synonym)` — Add a synonym to an existing term
- `remove_synonym(hostname, catalog_id, schema, table, name, synonym)` — Remove a synonym
- `update_term(hostname, catalog_id, schema, table, name, ...)` — General-purpose term update
- `update_term_description(hostname, catalog_id, schema, table, name, description)` — Description-only update
- `list_vocabulary_terms(hostname, catalog_id, schema, table)` — Browse all terms
- `lookup_term(hostname, catalog_id, schema, table, name)` — Synonym-aware term lookup
- `references/patterns.md` — Domain examples, FK patterns, description guidance, tips

## Related Skills

- **`create-table`** — Creating domain tables with FK columns to vocabulary tables.
- **`generate-descriptions`** — Description templates and quality guidelines for vocabulary tables and terms.
- **`create-feature`** *(tier-2, deriva-ml-skills)* — Features use vocabularies as their value domain. See this skill if you have `deriva-ml-skills` installed and want to create features that reference vocabulary terms.
