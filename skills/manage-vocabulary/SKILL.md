---
name: manage-vocabulary
description: "ALWAYS use this skill when creating or managing controlled vocabularies in Deriva — creating vocabulary tables, adding terms with descriptions and synonyms, browsing existing vocabularies, and deciding whether to create a new vocabulary vs extend an existing one. Triggers on: 'create vocabulary', 'add term', 'add synonym', 'vocabulary', 'controlled terms', 'categorical labels', 'what vocabularies exist', 'browse terms', 'extend vocabulary'."
user-invocable: true
disable-model-invocation: true
---

# Managing Controlled Vocabularies

Controlled vocabularies are the standard way to represent categorical data in Deriva. They provide consistent labeling, faceted search in Chaise, and synonym support for discoverability. Every vocabulary is a table with standard columns: Name, Description, Synonyms, ID, and URI.

Vocabularies are referenced as foreign-key targets from any categorical column in your domain schema — subject species, sample type, image quality grade, instrument calibration status, and so on.


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

Every term must have a description that defines its meaning in context — explaining what the term means, when to apply it, and how it relates to neighboring terms. Bare restatements of the name (`"Pneumonia"`) or meta-commentary (`"This is the pneumonia term"`) are not sufficient and produce empty Chaise tooltips.

For the canonical guidance on writing term descriptions — including good/bad examples, the relationship between term descriptions and table comments, and what a description should answer — see `references/term-naming-strategy.md` ("Term Descriptions" section).

## Find before you create

> The MCP server does NOT perform automatic duplicate detection on `create_vocabulary` or `add_term`, and does NOT provide "did you mean?" suggestions on missing references. The skill-level workflow is the only guardrail: before creating a vocabulary or adding a term, run `rag_search` against the catalog schema (`doc_type="catalog-schema"`) to find similar entities. Present a picker if multiple plausible matches turn up. See the `semantic-awareness` skill for the full workflow.

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

This same principle applies *within* a vocabulary: terms should describe a single conceptual dimension, never compounded dimensions. The same anti-patterns (compound tags, hierarchical encoding, vocabulary creep) and the substitution test for catching them are documented in `references/term-naming-strategy.md`. Read it before adding terms that you suspect might overlap with existing ones.

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

**Naming conventions** for vocabulary tables and the terms they hold split across two skills: the general entity-naming rules (PascalCase with underscores, singular form, short and specific — applies to all tables, columns, and terms) live in the `entity-naming` skill; vocabulary-term-specific elaborations (don't embed the dimension, the substitution test for catching duplicates, anti-patterns) live in `references/term-naming-strategy.md` here. Read both before naming the vocabulary or its first terms — choices made here are hard to change later because existing records reference terms by name. Renaming a vocabulary or term is significantly more expensive than renaming a non-FK-target table; see `entity-naming/references/naming-conventions.md` ("Renaming" section) for the cost breakdown.

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

Synonyms are searchable via `lookup_term(...)` (the new MCP surface's synonym-aware lookup). For guidance on when to use synonyms vs creating new terms — including the test for whether two candidate names are the same concept under different formatting versus genuinely separate concepts — see `references/term-naming-strategy.md` ("Synonyms" section).

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
- `references/term-naming-strategy.md` — Canonical guidance for term-level design: orthogonal tagging, dimension identification, naming conventions, term descriptions, synonyms, anti-patterns, the substitution test, semantic checking. Read before adding any new term.
- `references/patterns.md` — Domain examples, FK patterns, common usage tips. (Term-level descriptions, naming, and synonym design have moved to `term-naming-strategy.md`.)

## Related Skills

- **`entity-naming`** — Canonical naming conventions for all data-modeling entities (schemas, tables, columns, vocabulary tables, vocabulary terms). Read first when designing a new vocabulary or its terms; this skill (`manage-vocabulary`) covers vocabulary mechanics and `references/term-naming-strategy.md` adds vocabulary-term-specific concerns on top of the general rules.
- **`create-table`** — Creating domain tables with FK columns to vocabulary tables.
- **`generate-descriptions`** — Description templates and quality guidelines for vocabulary tables and terms.
