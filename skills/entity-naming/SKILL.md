---
name: entity-naming
description: "Use this skill when naming or renaming any data-modeling entity in a Deriva catalog: schemas, tables, columns, foreign-key columns, vocabulary tables, or vocabulary terms. Triggers on: 'what should I name', 'naming convention', 'PascalCase', 'singular or plural', 'rename a table', 'rename a column', 'should this be one word or two', 'good name for', 'bad name', 'is this name OK', 'specific enough', and on any catalog-design discussion where naming is being proposed. Do NOT use for Python code style or general project file naming."
user-invocable: true
disable-model-invocation: true
---

# Entity Naming Conventions for Deriva Catalogs

The naming of catalog entities — schemas, tables, columns, vocabulary tables, vocabulary terms — has long-lived consequences. Names appear in URLs, FK constraints, exported bag manifests, Chaise UI labels, scripts, and configs. Renaming is possible but expensive. This skill is the canonical source for *what to name things* across all of those entity classes; for the deeper rationale, character restrictions, the specificity test, edge cases, and migration procedure, see `references/naming-conventions.md`.

## The four conventions at a glance

| Entity | Case | Word separator | Form | Example | Counter-example |
|--------|------|----------------|------|---------|------------------|
| **Schema** | lowercase | none | short noun | `myproject`, `medical`, `genomics` | `MyProject`, `my_project` |
| **Table** | PascalCase | underscore | singular noun | `Subject`, `Blood_Sample`, `Image_Annotation` | `subjects`, `blood_samples` |
| **Column** | PascalCase | underscore | descriptive | `Age_At_Enrollment`, `Sample_Date`, `Cell_Count` | `age`, `sampleDate` |
| **Vocabulary term** | PascalCase | underscore | singular, no embedded dimension | `Training`, `Hyaline_Cartilage`, `Expert_Reviewed` | `TrainingSet`, `Hyaline-Cartilage`, `RoleTraining` |

> **Rename within the first day of an entity's existence, or not at all.** Once an entity is in active use, the cost of a rename usually outweighs the benefit. See "Renaming" below for what specifically breaks.

## Schema-specific rules

Schemas are namespaces inside a catalog. They're created once and referenced many times by every tool call (`schema=`).

- **Lowercase, no underscores, no hyphens.** Chaise URL routing treats schema names case-insensitively in some path constructors but case-sensitively in others; lowercase eliminates the bug class entirely. `myproject`, `medical`, `genomics`. NOT `My_Project` or `My-Project`.
- **Short.** Schemas appear in every URL and every tool call's `schema=` argument. 1-2 words is ideal; long compound names (`my_research_project_2026`) become noise.
- **Stable.** Schemas are *much* harder to rename than tables — every tool call across every script that touches the catalog mentions the schema name. Pick one early and stick with it.

Pre-existing catalogs may carry hyphenated or underscored schema names from earlier eras; accept those rather than rename. New schemas should follow the lowercase-no-separator pattern.

## Shared rules for tables, columns, and vocabulary terms

These rules apply across the three PascalCase-with-underscores entity classes.

### Use PascalCase with underscores

`Tissue_Type`, `Hyaline_Cartilage`, `Age_At_Enrollment`. The first letter of each word is uppercase; multi-word names use underscores between words. ERMrest preserves case, and Chaise displays names as-is — `tissue_type` would render as a lowercase facet label.

### Singular form for tables and vocabulary terms

A row is *a subject*, not *a subjects*. The table holds many; the name names what one row is. Same for vocabulary terms: a record tagged with `Training` *is* one of these things, not many of them.

### Descriptive form for columns

Columns describe a property of the row. The name should be specific enough to read in isolation — `Cell_Count`, not just `Count`. Columns appear in CSV exports and faceted search where the table context is implicit.

### Be specific enough to distinguish, but not redundantly long

A name should distinguish its referent from neighboring entities. `Image` is too generic if the catalog also has `Image_Annotation` and `Image_Asset` — but `Captured_Microscope_Image` is too long. The test: if you read the name in a Chaise filter chip, does it tell you what it refers to without context? See the "specificity test" section in `references/naming-conventions.md` for worked examples.

### Don't embed the dimension in the name

A vocabulary term lives inside a vocabulary table that already names its dimension. `Training` belongs in `Dataset_Type` — repeating "Type" or "Role" inside the term name (`RoleTraining`, `Training_Type`) is redundant. Same for tables: a column called `Subject_Name` inside a `Subject` table redundantly repeats the table name; just call it `Name`.

### Don't compound dimensions in a single name

`TrainingLabeled` as one term is the wrong shape — `Training` and `Labeled` describe independent concerns. Compound names cause combinatorial explosion (you'd need `TrainingUnlabeled`, `TestingLabeled`, etc.) and break the ability to filter on each dimension independently. Use multiple tags or multiple columns instead. The vocabulary version of this anti-pattern is documented in detail in `/deriva:manage-vocabulary` (`references/term-naming-strategy.md`).

### Be aware of case sensitivity

Deriva entity names are case-sensitive everywhere — in URLs, in tool calls, in FK constraints. `Subject` and `subject` are different tables; `Training` and `training` are different terms. The convention exists to make case unambiguous: PascalCase for tables/columns/terms, lowercase for schemas.

## Foreign-key column conventions

When a table has a foreign-key column referencing another table, the column name should match the referenced table's name. Example: a `Sample` table referencing `Subject` has a column called `Subject` (not `Subject_ID`, not `Subject_Ref`, not `subject_fk`).

This convention makes Chaise's display unambiguous (the column header is the name of what it references) and lets ERMrest's `pathBuilder` API generate readable join chains, since the column name on each side reflects what's being linked.

If a table has *two* FKs to the same target table (e.g., `Parent_Subject` and `Child_Subject` both referencing `Subject`), the columns disambiguate by role: `<Role>_<TargetTableName>`. Both columns then declare an FK constraint to `Subject`.

For the full FK pattern (including FKs to vocabulary tables and the path-builder reasoning in detail), see `references/naming-conventions.md`.

## Renaming

Renaming is expensive because names are referenced from many places that don't update in lockstep:

| Reference type | Update on rename? |
|---|---|
| FK constraints by name | Yes — schema migration to drop and recreate |
| URL bookmarks (Chaise) | No — break silently with 404 |
| Hardcoded references in scripts and configs | Yes — find every script and config |
| Bag manifests already exported | Cannot update — old bags reference old names |
| Audit logs | Cannot update — historical record |
| RID references | Not affected (RIDs are immutable, name-independent) |

**Practical rule: rename within the first day of an entity's existence, or not at all.** For the full migration procedure when a rename is unavoidable (drop FKs, rename, re-create FKs, update every script, communicate to humans), see `references/naming-conventions.md`.

## When you can't follow the convention

The conventions describe the design *target*. Real catalogs sometimes have entities that predate the convention or come from external sources:

- **Imported schemas** (e.g., from a published dataset) keep their original naming even if it doesn't match. Don't rename to "fix" them — external references will break.
- **Pre-existing catalogs** may have inconsistent naming. New entities should follow the convention; renaming existing entities is usually not worth the cascade of breakage.
- **Vocabulary terms with non-Western characters or multi-word phrases** (taxonomic names like `Mus musculus`, chemical names like `H&E`) — accept the deviation. Add the canonical PascalCase form as a synonym for searchability.

When you encounter a deviation, document it in the entity's description so future readers understand why.

## Where naming stops

Naming is *one* of several decisions you make when creating an entity. This skill does not cover:

- **Whether the entity should exist at all.** That's a modeling question — handled in `/deriva:create-table` and `/deriva:manage-vocabulary` (their "is this needed?" framing).
- **What the entity's description should say.** Descriptions are auto-drafted by the always-on `generate-descriptions` skill in this plugin.
- **How the entity displays in Chaise.** Display annotations are separate from naming — see `/deriva:customize-display`.
- **Python code style or project file naming.** Different concern; out of scope.

## Reference

- `references/naming-conventions.md` — Why each convention exists, character restrictions per entity class, the specificity test in detail, FK column patterns at depth, edge cases (established acronyms, names with special characters), and the full renaming-migration procedure.

## Related skills

- **`/deriva:manage-vocabulary`** — Vocabulary CRUD operations (`add_term`, `add_synonym`, `create_vocabulary`). For vocabulary-term-specific naming concerns beyond the general rules here (synonyms, anti-patterns, substitution test, semantic checking), that skill carries `references/term-naming-strategy.md`.
- **`/deriva:create-table`** — Table and column CRUD operations.
