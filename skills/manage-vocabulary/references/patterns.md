# Vocabulary Patterns and Reference

Reference material for vocabulary conventions and common usage patterns. For the step-by-step workflow, see the main `SKILL.md`.

## Table of Contents

- [Discovering Existing Vocabularies](#discovering-existing-vocabularies)
- [Domain-Specific Vocabulary Examples](#domain-specific-vocabulary-examples)
- [Using Vocabularies as Column Values](#using-vocabularies-as-column-values)
- [Writing Good Descriptions](#writing-good-descriptions)
- [Synonyms vs New Terms](#synonyms-vs-new-terms)
- [Tips](#tips)

---

## Discovering Existing Vocabularies

Browse vocabularies in a catalog by listing all tables and filtering for those with the standard vocabulary columns (Name, Description, Synonyms, ID, URI). Read `deriva://catalog/{hostname}/{catalog_id}/tables` for the table list (resource form, single round trip). Use `rag_search(hostname=..., catalog_id=..., query="...", doc_type="catalog-schema")` to find vocabularies and terms by concept (the RAG index includes term descriptions and synonyms, so fuzzy matching works).

A fresh Deriva catalog typically has no built-in vocabularies — you create them as your domain schema needs them. Some Deriva-based applications and domain plugins ship their own built-in vocabularies in their own schemas; treat those as ordinary vocabulary tables and use the same `add_term` / `delete_term` / `add_synonym` tools, passing the appropriate `schema=` and `table=` arguments.

## Domain-Specific Vocabulary Examples

Common patterns for scientific data. All calls take `hostname=` and `catalog_id=` (stateless surface); `schema=` is your domain schema. Examples below show only the vocabulary-specific arguments for brevity.

**Species vocabulary:**

1. `create_vocabulary(hostname=..., catalog_id=..., schema=..., vocabulary_name="Species", comment="Biological species for experimental subjects")`
2. `add_term(hostname=..., catalog_id=..., schema=..., table="Species", name="Homo sapiens", description="Human")`
3. `add_term(hostname=..., catalog_id=..., schema=..., table="Species", name="Mus musculus", description="House mouse, common lab strain", synonyms=["Mouse"])`

**Diagnosis vocabulary:**

1. `create_vocabulary(hostname=..., catalog_id=..., schema=..., vocabulary_name="Diagnosis", comment="Clinical diagnostic categories")`
2. `add_term(hostname=..., catalog_id=..., schema=..., table="Diagnosis", name="Normal", description="No pathological findings")`
3. `add_term(hostname=..., catalog_id=..., schema=..., table="Diagnosis", name="Benign", description="Non-cancerous abnormality")`
4. `add_term(hostname=..., catalog_id=..., schema=..., table="Diagnosis", name="Malignant", description="Cancerous, requires staging")`

**Stain type vocabulary:**

1. `create_vocabulary(hostname=..., catalog_id=..., schema=..., vocabulary_name="Stain_Type", comment="Histological staining protocols")`
2. `add_term(hostname=..., catalog_id=..., schema=..., table="Stain_Type", name="H&E", description="Hematoxylin and eosin, standard morphology stain", synonyms=["HE", "Hematoxylin and Eosin"])`
3. `add_term(hostname=..., catalog_id=..., schema=..., table="Stain_Type", name="IHC", description="Immunohistochemistry for protein detection")`

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
