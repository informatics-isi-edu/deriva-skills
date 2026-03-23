---
name: manage-vocabulary
description: "ALWAYS use this skill when creating or managing controlled vocabularies in Deriva — creating vocabulary tables, adding terms with descriptions and synonyms, browsing existing vocabularies, extending built-in vocabularies (Dataset_Type, Workflow_Type), and deciding whether to create a new vocabulary vs extend an existing one. Triggers on: 'create vocabulary', 'add term', 'add synonym', 'vocabulary', 'controlled terms', 'categorical labels', 'what vocabularies exist', 'browse terms', 'extend vocabulary', 'dataset type', 'workflow type'."
user-invocable: true
disable-model-invocation: true
---

# Managing Controlled Vocabularies

Controlled vocabularies are the standard way to represent categorical data in Deriva. They provide consistent labeling, faceted search in Chaise, and synonym support for discoverability. Every vocabulary is a table with standard columns: Name, Description, Synonyms, ID, and URI.

Vocabularies are used by features (see `create-feature`), dataset types, workflow types, asset types, and any categorical column in your domain schema.


## Prerequisite: Connect to a Catalog

All operations in this skill require an active catalog connection. Before anything else:

```
connect_catalog(hostname="...", catalog_id="...")
```

If already connected (check `deriva://catalog/connections`), skip this step.


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

To **list all vocabularies**, read the `deriva://catalog/vocabularies` resource.

To **browse terms** in a specific vocabulary, read the `deriva://vocabulary/{vocab_name}` resource (e.g., `deriva://vocabulary/Species`). Alternatively, call `preview_table` with `table_name` set to the vocabulary name.

To **look up a specific term**, read the `deriva://vocabulary/{vocab_name}/{term_name}` resource. This matches against both names and synonyms — looking up `"Xray"` will find `"X-ray"`. In the Python API, `ml.lookup_term("Species", "Mouse")` provides the same synonym-aware lookup.

## Description Guidance

### Vocabulary Tables

The `comment` on a vocabulary table should explain the classification scheme, its scope, and how terms relate to each other.

**Good vocabulary descriptions:**
- "Classification of biological tissue types for histology analysis. Terms are mutually exclusive tissue categories used for slide-level labeling"
- "Image quality assessment grades assigned during manual QC review. Ordered from best to worst: excellent > acceptable > borderline > rejected"
- "CIFAR-10 object categories. 10 mutually exclusive classes spanning vehicles and animals"

**Bad vocabulary descriptions:**
- "Types" or "Categories" or "A vocabulary"

### Vocabulary Terms

Every term must have a description that defines its meaning in context — not just restating the name. Explain when to use the term, and how it relates to other terms.

**Good term descriptions:**
- "Pneumonia detected in chest X-ray. Use when radiological signs of pneumonia are present regardless of etiology. Mutually exclusive with 'normal'"
- "Borderline image quality — minor artifacts present but image is usable for training with caution. Review if model performance on this subset is unexpectedly poor"

**Bad term descriptions:**
- "Pneumonia" or "This is the pneumonia term" or leaving it empty

## Automatic Safeguards

> The MCP server automatically checks for near-duplicate vocabularies when calling `create_vocabulary`. If a similar vocabulary already exists, the tool response includes a `similar_existing` field with suggestions. It also provides "did you mean?" suggestions when `add_term` or `delete_term` references a vocabulary or term that doesn't exist.

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

Call `create_vocabulary` with:
- `vocabulary_name`: table name in PascalCase with underscores (e.g., `"Tissue_Type"`)
- `comment` (required): what this vocabulary classifies (e.g., `"Classification of biological tissue types for histology analysis"`)

This creates a table in the domain schema with the standard vocabulary columns.

**Naming conventions:**
- Use `PascalCase` with underscores between words: `Tissue_Type`, `Image_Quality`, `Stain_Protocol`
- Name should be the singular form of what the terms represent
- Keep names concise but specific

## Adding Terms

Call `add_term` with:
- `vocabulary_name`: the vocabulary table name
- `term_name`: the term to add
- `description`: what this term means (required — see `references/patterns.md` for guidance on writing good descriptions)
- `synonyms` (optional): list of alternate names to add at creation time (e.g., `["HE", "Hematoxylin and Eosin"]`)

**Every term should have a meaningful description.** Descriptions appear as tooltips in the Chaise UI. Avoid descriptions that just restate the name — explain what the term means in context.

## Adding Synonyms

Synonyms make terms discoverable under alternative names, abbreviations, or common misspellings.

Call `add_synonym` with `vocabulary_name`, `term_name`, and `synonym`.

Synonyms are searchable via the `deriva://vocabulary/{vocab_name}/{term_name}` resource and the Python API's `ml.lookup_term()`. For guidance on when to use synonyms vs creating new terms, see `references/patterns.md`.

## Removing Terms and Synonyms

To **remove a synonym**, call `remove_synonym` with `vocabulary_name`, `term_name`, and `synonym`.

To **delete a term**, call `delete_term` with `vocabulary_name` and `term_name`. This only works if the term is not referenced by any records — otherwise it will fail with a foreign key constraint error. Remove the references first.

## Updating Term Descriptions

Call `update_term_description` with `vocabulary_name`, `term_name`, and the new `description`.

## Workflow: Adding Terms to an Existing Vocabulary

1. **Search first** — read `deriva://vocabulary/{vocab_name}` to check if the term (or a synonym) already exists
2. **Add the term** with a meaningful description (and optional synonyms)
3. **Add additional synonyms** for common alternate names if not provided at creation
4. **Verify** — read `deriva://vocabulary/{vocab_name}` to confirm

## Reference Resources

- `deriva://catalog/vocabularies` — Browse all vocabularies and term counts
- `deriva://vocabulary/{vocab_name}` — Browse terms in a specific vocabulary
- `deriva://vocabulary/{vocab_name}/{term_name}` — Look up a specific term (synonym-aware)
- `references/patterns.md` — Built-in vocabularies, domain examples, FK patterns, description guidance, tips

## Related Skills

- **`create-feature`** — Features use vocabularies as their value domain. See this skill for creating features that reference vocabulary terms.
- **`create-table`** — Creating domain tables with FK columns to vocabulary tables.
