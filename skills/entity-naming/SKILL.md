---
name: entity-naming
description: "Use this skill when naming or renaming any data-modeling entity in a Deriva catalog: schemas, tables, columns, foreign-key columns, vocabulary tables, or vocabulary terms. Triggers on: 'what should I name', 'naming convention', 'PascalCase', 'singular or plural', 'rename a table', 'rename a column', 'should this be one word or two', 'good name for', 'bad name', 'is this name OK', 'specific enough', and on any catalog-design discussion where naming is being proposed. Do NOT use for Python code style or general project file naming."
user-invocable: true
disable-model-invocation: true
---

# Entity Naming Conventions for Deriva Catalogs

The naming of catalog entities — schemas, tables, columns, vocabulary tables, vocabulary terms — has long-lived consequences. Names appear in URLs, FK constraints, exported bag manifests, Chaise UI labels, scripts, and configs. Renaming is possible but expensive: every reference by name has to be updated in lockstep, and external bookmarks break.

This skill is the canonical source for *what to name things*. It does not cover the mechanics of *creating* the entities (those live in `create-table` and `manage-vocabulary`) or the higher-level question of whether a new entity is needed at all (those live in the same skills' "Phase 1: Assess" sections).

## What this skill covers

| Entity | Scope | Where mechanics live |
|--------|-------|----------------------|
| **Schemas** | Per-catalog namespaces (e.g., `myproject`, `deriva-ml`) | `create-table` (schemas are typically created with the first table) |
| **Tables** | Domain tables and vocabulary tables | `create-table` |
| **Columns** | Including foreign-key columns | `create-table` |
| **Vocabulary terms** | Rows in any vocabulary table | `manage-vocabulary` |

Vocabulary terms are subject to the conventions here **plus** vocabulary-specific concerns (synonyms, the substitution test, anti-patterns, semantic checking) documented in `manage-vocabulary/references/term-naming-strategy.md`.

## What this skill does NOT cover

- **Python code style** — variable names, function names, module layout. Different concern; out of scope for this skill.
- **Project file naming** — script filenames, config files, directory structure. Different concern; out of scope for this skill.

## Quick reference: the four conventions

| Entity | Case | Word separator | Form | Example | Counter-example |
|--------|------|----------------|------|---------|------------------|
| **Schema** | lowercase | none | short noun | `myproject`, `medical`, `genomics` | `MyProject`, `my_project` |
| **Table** | PascalCase | underscore | singular noun | `Subject`, `Blood_Sample`, `Image_Annotation` | `subjects`, `blood_samples` |
| **Column** | PascalCase | underscore | descriptive | `Age_At_Enrollment`, `Sample_Date`, `Cell_Count` | `age`, `sampleDate` |
| **Vocabulary term** | PascalCase | underscore | singular, no embedded dimension | `Training`, `Hyaline_Cartilage`, `Expert_Reviewed` | `TrainingSet`, `Hyaline-Cartilage`, `RoleTraining` |

## The shared rules

These apply across tables, columns, and vocabulary terms. Schemas follow their own lowercase-no-underscore pattern (rationale below).

### Use PascalCase with underscores

`Tissue_Type`, `Hyaline_Cartilage`, `Age_At_Enrollment`. The first letter of each word is uppercase; multi-word names use underscores between words. ERMrest preserves case, and Chaise displays names as-is — `tissue_type` would render as a lowercase facet label.

### Use singular form for things, descriptive form for attributes

| Entity class | Form | Why |
|---|---|---|
| Tables | Singular noun (`Subject`, not `Subjects`) | A row is *a subject*, not *a subjects*. The table holds many; the name names what one row is. |
| Vocabulary terms | Singular noun (`Training`, not `Trainings`) | A record tagged with the term *is* one of these things, not many of them. |
| Columns | Descriptive (`Cell_Count`, not just `Count`) | Columns describe a property of the row; the name should be specific enough to read in isolation. |

### Be specific enough to distinguish, but not redundantly long

A name should distinguish its referent from neighboring entities. `Image` is too generic if the catalog also has `Image_Annotation` and `Image_Asset` — but `Captured_Microscope_Image` is too long. The test: if you read the name in a Chaise filter chip, does it tell you what it refers to without context?

For vocabulary terms specifically, the substitution test (in `manage-vocabulary/references/term-naming-strategy.md`) catches near-duplicates that would fail this test in subtle ways.

### Don't embed the dimension in the name

A vocabulary term lives inside a vocabulary table that already names its dimension. `Training` belongs in `Dataset_Type` — repeating "Type" or "Role" inside the term name (`RoleTraining`, `Training_Type`) is redundant. Same for tables: a column called `Subject_Name` inside a `Subject` table redundantly repeats the table name; just call it `Name`.

### Don't compound dimensions in a single name

`TrainingLabeled` as one term is the wrong shape — `Training` and `Labeled` describe independent concerns. Compound names cause combinatorial explosion (you'd need `TrainingUnlabeled`, `TestingLabeled`, etc.) and break the ability to filter on each dimension independently. Use multiple tags or multiple columns instead. The vocabulary version of this anti-pattern is documented in detail in `manage-vocabulary/references/term-naming-strategy.md`.

### Be aware of case sensitivity

Deriva entity names are case-sensitive everywhere — in URLs, in tool calls, in FK constraints. `Subject` and `subject` are different tables; `Training` and `training` are different terms. The convention exists to make case unambiguous: PascalCase for tables/columns/terms, lowercase for schemas.

## Schema-specific rules

Schemas are namespaces inside a catalog. They're created once and referenced many times by every tool call (`schema=`).

- **Lowercase, no underscores, no hyphens.** The Chaise URL syntax routes through schemas with the literal schema name as a path segment; lowercase makes the URLs readable and avoids case-sensitivity bugs in route matching. `myproject`, `medical`, `genomics`. NOT `My_Project` or `My-Project`.
- **Short.** Schemas appear in every URL and every tool call's `schema=` argument. 1-2 words is ideal; long compound names (`my_research_project_2026`) become noise.
- **Stable.** Schemas are *much* harder to rename than tables — every tool call across every script that touches the catalog mentions the schema name. Pick one early and stick with it.

The DerivaML schemas (`deriva-ml`, plus your domain schema like `cifar10_e2e`) follow this convention. The hyphen in `deriva-ml` predates the convention and is grandfathered; new schemas should not use hyphens.

## Foreign-key column conventions

When a table has a foreign-key column referencing another table, the column name should match the referenced table's name. Example: a `Sample` table referencing `Subject` has a column called `Subject` (not `Subject_ID`, not `Subject_Ref`, not `subject_fk`).

This convention enables ERMrest's path-builder API to generate intuitive joins: `pb.schemas["x"].tables["Sample"].link(pb.schemas["x"].tables["Subject"])` works because the FK column name matches the target table. It also makes Chaise's display unambiguous — the column header is the name of what it references.

If a table has *two* FKs to the same target table (e.g., `Parent_Subject` and `Child_Subject` both referencing `Subject`), the FK column names disambiguate by role; both columns then declare an FK constraint to `Subject`.

## When you can't follow the convention

The conventions describe the design *target*. Real catalogs sometimes have entities that predate the convention or come from external sources:

- **Imported schemas** (e.g., from a published dataset) keep their original naming even if it doesn't match. Don't rename to "fix" them — external references will break.
- **Pre-existing catalogs** may have inconsistent naming. New entities should follow the convention; renaming existing entities is usually not worth the cascade of breakage.
- **Vocabulary terms with non-Western characters or multi-word phrases** (taxonomic names like `Mus musculus`, chemical names like `H&E`) — accept the deviation. Add the canonical form as a synonym for searchability.

When you encounter a deviation, document it in the entity's description so future readers understand why.

## Renaming considerations

Names are referenced from many places. A rename requires updating each:

| Reference type | Update required |
|---|---|
| FK constraints by name | Yes — schema migration to drop and recreate |
| URL bookmarks (Chaise) | Break silently; users hit 404 |
| Hardcoded references in scripts | Yes — find every script and config |
| Hydra-zen configs (DerivaML) | Yes — update `DatasetSpecConfig` and similar |
| Bag manifests (already exported) | Cannot update — old bags reference old names |
| Audit logs | Cannot update — historical record |
| RID references | Not affected (RIDs are immutable, name-independent) |

Practical rule: **rename within the first day of an entity's existence, or not at all.** If the entity is already in active use, the cost of a rename usually outweighs the benefit.

## Reference

- `references/naming-conventions.md` — Deeper rationale: why each convention exists, character restrictions per entity class, the specificity test in detail, FK column patterns, renaming pain in detail, and migration approaches when a rename is unavoidable.

## Related skills

- **`manage-vocabulary`** — Vocabulary CRUD operations (`add_term`, `add_synonym`, `create_vocabulary`). For vocabulary-term-specific naming concerns beyond the general rules here (synonyms, anti-patterns, substitution test, semantic checking), see `manage-vocabulary/references/term-naming-strategy.md`.
- **`create-table`** — Table and column CRUD operations.
