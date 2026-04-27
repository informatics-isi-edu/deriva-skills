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

Browse all vocabularies by reading the `deriva://catalog/vocabularies` resource. Use `rag_search(..., doc_type="catalog-schema")` to find vocabularies and terms by concept (the RAG index includes term descriptions and synonyms, so fuzzy matching works).

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

Every term should have a description. Descriptions appear as tooltips in the Chaise UI and help collaborators understand exactly what each term means. Avoid descriptions that just restate the name.

| Term | Bad | Good |
|---|---|---|
| Grade I | "Grade one" | "Well-differentiated, low mitotic rate, favorable prognosis" |
| Normal | "Normal tissue" | "No pathological findings, intact cellular architecture" |
| Artifact | "An artifact" | "Non-biological element (air bubble, fold, ink mark) in image" |

## Synonyms vs New Terms

| Situation | Action |
|---|---|
| Same concept, different spelling ("X-ray" vs "Xray") | Add synonym |
| Same concept, different language ("Hund" for "Dog") | Add synonym |
| Common abbreviation ("CT" for "Connective Tissue") | Add synonym |
| Related but distinct concept ("Cartilage" vs "Connective") | Add new term |
| More specific version ("Hyaline Cartilage") | Add new term |

## Tips

- Vocabulary tables support faceted search in Chaise automatically — no extra configuration needed
- Terms are ordered alphabetically by name in the UI by default
- The `ID` and `URI` columns are auto-generated — you only need to provide Name and Description
- For large vocabularies (100+ terms), consider hierarchical naming (e.g., "Carcinoma:Ductal", "Carcinoma:Lobular") or multiple smaller vocabularies
- For tier-2 (deriva-ml) installations, when a vocabulary is used by a feature, the feature creates an association table. See the `create-feature` skill in `deriva-ml-skills` for details

## Domain-plugin built-in vocabularies

Some Deriva domain plugins ship built-in vocabularies and dedicated tools to extend them. These are out of scope for this tier-1 skill, but if the relevant plugin is installed in your environment:

| Plugin | Built-in vocabularies | Dedicated extender tools |
|---|---|---|
| `deriva-ml-mcp` (with `deriva-ml-skills`) | `Dataset_Type`, `Workflow_Type`, `Asset_Type`, `Execution_Status_Type` | `create_dataset_type_term`, `add_workflow_type`, `add_asset_type` |

The dedicated extender tools are convenience wrappers — they ultimately call the same `add_term` machinery this skill documents, but with domain-specific defaults (e.g., they may auto-link to default schemas or apply naming conventions). Use them when available; fall back to `add_term` directly if you need to bypass the convenience layer.

For ML vocabulary workflows (e.g., extending `Dataset_Type` with a new `Augmented` term), see the `dataset-lifecycle` skill in `deriva-ml-skills`.
