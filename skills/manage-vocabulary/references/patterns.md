# Vocabulary Patterns and Reference

Reference material for vocabulary conventions and common usage patterns. For the step-by-step workflow, see the main `SKILL.md`.

## Table of Contents

- [Discovering Existing Vocabularies](#discovering-existing-vocabularies)
- [Domain-Specific Vocabulary Examples](#domain-specific-vocabulary-examples)
- [Using Vocabularies as Column Values](#using-vocabularies-as-column-values)
- [Writing Good Descriptions](#writing-good-descriptions)
- [Synonyms vs New Terms](#synonyms-vs-new-terms)
- [Tips](#tips)
- [Domain-plugin built-in vocabularies](#domain-plugin-built-in-vocabularies)

---

## Discovering Existing Vocabularies

Browse vocabularies in a catalog by listing all tables and filtering for those with the standard vocabulary columns (Name, Description, Synonyms, ID, URI). The `catalog_tables(hostname=..., catalog_id=...)` tool returns the table list. Use `rag_search(..., doc_type="catalog-schema")` to find vocabularies and terms by concept (the RAG index includes term descriptions and synonyms, so fuzzy matching works).

A fresh Deriva catalog typically has **no** built-in vocabularies — you create them as your domain schema needs them. Some Deriva-based applications (e.g., DerivaML) ship their own built-in vocabularies; see the [Domain-plugin built-in vocabularies](#domain-plugin-built-in-vocabularies) section at the bottom for cross-references.

## Domain-Specific Vocabulary Examples

Common patterns for scientific data:

**Species vocabulary:**
1. Call `create_vocabulary` with `vocabulary_name`: `"Species"`, `comment`: `"Biological species for experimental subjects"`
2. Call `add_term` with `vocabulary_name`: `"Species"`, `term_name`: `"Homo sapiens"`, `description`: `"Human"`
3. Call `add_term` with `vocabulary_name`: `"Species"`, `term_name`: `"Mus musculus"`, `description`: `"House mouse, common lab strain"`, `synonyms`: `["Mouse"]`

**Diagnosis vocabulary:**
1. Call `create_vocabulary` with `vocabulary_name`: `"Diagnosis"`, `comment`: `"Clinical diagnostic categories"`
2. Call `add_term` with terms like `"Normal"` (`"No pathological findings"`), `"Benign"` (`"Non-cancerous abnormality"`), `"Malignant"` (`"Cancerous, requires staging"`)

**Stain type vocabulary:**
1. Call `create_vocabulary` with `vocabulary_name`: `"Stain_Type"`, `comment`: `"Histological staining protocols"`
2. Call `add_term` with `term_name`: `"H&E"`, `description`: `"Hematoxylin and eosin, standard morphology stain"`, `synonyms`: `["HE", "Hematoxylin and Eosin"]`
3. Call `add_term` with `term_name`: `"IHC"`, `description`: `"Immunohistochemistry for protein detection"`

## Using Vocabularies as Column Values

To use a vocabulary as a column type in a domain table, create a foreign key from the column to the vocabulary table. For example, a `Subject` table with a `Species` column would have an FK to the `Species` vocabulary table.

Call `create_table` with a `foreign_keys` entry linking the column to the vocabulary:
- `column`: the column name (e.g., `"Species"`)
- `referenced_table`: the vocabulary table name (e.g., `"Species"`)

The FK to the vocabulary table enables dropdown selection in the Chaise entry form and faceted search in the compact view.

## Writing Good Descriptions

Term-level description guidance — what a good description answers, good/bad examples, and the relationship to vocabulary table comments — moved to `term-naming-strategy.md` ("Term Descriptions" section). That file is the single source of truth for term-level design conventions across all Deriva vocabularies.

## Synonyms vs New Terms

The decision between "add a synonym" and "add a new term" — including the candidate-by-candidate table (variant spelling → synonym, abbreviation → synonym, related-but-distinct concept → new term, etc.) — moved to `term-naming-strategy.md` ("Synonyms" section).

## Tips

- Vocabulary tables support faceted search in Chaise automatically — no extra configuration needed
- Terms are ordered alphabetically by name in the UI by default
- The `ID` and `URI` columns are auto-generated — you only need to provide Name and Description
- For large vocabularies (100+ terms), consider hierarchical naming (e.g., "Carcinoma:Ductal", "Carcinoma:Lobular") or multiple smaller vocabularies
- For tier-2 (deriva-ml) installations, when a vocabulary is used by a feature, the feature creates an association table. See the `create-feature` skill in `deriva-ml-skills` for details

## Domain-plugin built-in vocabularies

Some Deriva domain plugins ship built-in vocabularies. The vocabularies themselves are managed via the standard `add_term` / `delete_term` / `add_synonym` tools documented in the main SKILL — pass the right `schema=` and `table=` arguments:

| Plugin | Built-in vocabularies | Schema | Tools to use |
|---|---|---|---|
| `deriva-ml-mcp` (with `deriva-ml-skills`) | `Dataset_Type`, `Workflow_Type`, `Asset_Type`, `Execution_Status_Type` | `deriva-ml` | Standard `add_term(schema="deriva-ml", table="Dataset_Type", ...)` etc. |

For example, to add a new `Augmented` dataset type:

```python
add_term(
    hostname="data.example.org", catalog_id="1",
    schema="deriva-ml", table="Dataset_Type",
    name="Augmented",
    description="Dataset whose members were generated by augmenting a parent dataset (e.g., image rotations, color shifts)",
)
```

The new MCP architecture deliberately does NOT ship dedicated wrapper tools (`create_dataset_type_term`, `add_workflow_type`, `add_asset_type`) for these vocabularies — the generic `add_term` machinery handles them transparently because vocabulary tables are managed by `deriva-mcp-core` directly. (The legacy `deriva-mcp` server had wrappers; they were removed during the deriva-mcp-core split.)

For broader ML workflows that touch these vocabularies (creating typed datasets, registering workflow types, etc.), see the `dataset-lifecycle`, `route-run-workflows`, and `work-with-assets` skills in `deriva-ml-skills`.
