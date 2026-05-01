# Naming Conventions for Deriva Entities — Deeper Reference

This file provides the rationale, character-level restrictions, and edge-case guidance behind the four conventions documented in the parent `SKILL.md`. Read the SKILL.md for the rules; read this file when you need to understand *why* a rule exists, want to test a borderline name, or are planning a rename.

## Table of contents

- [Why naming matters in catalogs](#why-naming-matters-in-catalogs)
- [Per-entity rationale](#per-entity-rationale)
- [Foreign-key column conventions in detail](#foreign-key-column-conventions-in-detail)
- [Character restrictions and length](#character-restrictions-and-length)
- [The specificity test](#the-specificity-test)
- [Renaming: what breaks and how to migrate](#renaming-what-breaks-and-how-to-migrate)
- [Edge cases](#edge-cases)

---

## Why naming matters in catalogs

A Deriva catalog is read far more often than written. Every name is referenced from many places, by many tools, by many people. Names appear in:

- **URLs** — both Chaise web URLs and ERMrest API URLs embed schema, table, and column names as path segments. Bookmarks, citations, and shared links all carry these names verbatim.
- **FK constraints** — declared by name; ERMrest joins resolve names not RIDs.
- **Tool calls** — every MCP tool takes `schema=`, `table=`, sometimes `column=` arguments. Misspelling a name produces a "not found" error rather than a silent fallback.
- **Bag manifests** — exported BDBags include schema and table names in the data layout. Old bags reference old names indefinitely.
- **Chaise UI** — column headers, facet labels, and entity titles render the literal name (with optional display annotations layered on top).
- **Hydra-zen configs** (DerivaML) — `DatasetSpecConfig` and similar reference vocabulary terms by name.
- **Scripts and notebooks** — anything that uses `pathBuilder` or hand-constructs ERMrest URLs hardcodes names.
- **Audit logs** — every mutation event records the schema/table/column names involved.

A bad name doesn't fail loudly. It accumulates references, and each reference is a tiny migration cost the catalog will pay forever. The conventions exist to keep that cost low.

## Per-entity rationale

### Schemas: lowercase, no separators

Schemas are the top-level namespace. Their names appear in every URL path and every tool argument.

- **Lowercase** because Chaise's URL routing treats schema names case-insensitively in some path constructors but case-sensitively in others; lowercase eliminates the bug class entirely. Lowercase URLs are also more readable and more conventional for path components.
- **No underscores or hyphens** because schemas are short by convention; multi-word schemas indicate a missing layer of organization (use multiple schemas instead). The historical exception is `deriva-ml`, which predates the convention and is grandfathered.
- **Stable** because schema names appear in the most places. A schema rename touches every script, every config, every bookmark — the cost is roughly N times the cost of a table rename, where N is the table count in that schema.

### Tables: PascalCase with underscores, singular

Tables are *things*; their rows are individuals.

- **PascalCase** because ERMrest preserves case in stored names and in API responses. Chaise displays table names in titles and breadcrumbs verbatim — `Subject` reads as a proper title; `subject` looks like a mistake.
- **Singular** because each row is one of the named thing. `Subject` table → "this row is a Subject." If the name were `Subjects`, every reading would be off-by-one ("this row is a Subjects" doesn't parse).
- **Underscores between words** because PascalCase's word boundaries get ambiguous with longer compound names. `BloodSample` and `Blood_Sample` are both legal; underscores win for readability of multi-word names. Pick one convention per catalog and apply it consistently.

### Columns: PascalCase with underscores, descriptive

Columns describe properties of their row.

- **Same casing rules as tables** — PascalCase with underscores. Chaise displays column headers verbatim.
- **Descriptive** because columns are read in isolation in faceted search, in CSV exports, in API responses where the table context is implicit. A column named `Count` could mean anything; `Cell_Count` is unambiguous.
- **Don't repeat the table name** in the column name. Inside a `Subject` table, the column should be `Name`, not `Subject_Name` — the table context is implicit. The exception is when a column references *another* table (FK columns), where the column should be named after the referenced table; see the next section.

### Vocabulary terms: PascalCase with underscores, singular, no embedded dimension

Vocabulary terms are values that records get tagged with.

- **PascalCase with underscores, singular** — same rules as tables. `Hyaline_Cartilage` not `hyaline cartilage` or `hyalineCartilage` or `Hyaline-Cartilage`. The term names a kind of thing; one record carries one tag.
- **No embedded dimension** because the vocabulary table the term belongs to already names the dimension. `Tissue_Type` table contains `Hyaline_Cartilage`, not `Tissue_Hyaline_Cartilage` or `Hyaline_Cartilage_Tissue_Type`. Repeating the dimension is noise.
- **No compound dimensions** because that's the compound-tag anti-pattern, documented in detail in `manage-vocabulary/references/term-naming-strategy.md`.

## Foreign-key column conventions in detail

The rule: **FK column name matches the referenced table name.** Reasoning:

1. **Path-builder API ergonomics.** ERMrest's `pathBuilder` chains joins by FK target table name. When the FK column has the same name as the target table, joins read like English: `pb.Image.link(pb.Subject)` joins through whatever Image column points at Subject.

2. **Chaise display.** Chaise's compact view renders the FK column's *value* as a clickable reference to the target row. The column header is the column name, which (under this convention) is the target table name — so the header reads as the type of thing being linked to.

3. **Self-documenting schemas.** Reading a table's column list tells you immediately which other tables it links to. A `Sample` table with columns `[Sample_ID, Subject, Collection_Date]` clearly references `Subject`.

### When a table has multiple FKs to the same target

The convention bends to accommodate disambiguation. If a `Pedigree` table references `Subject` twice (one for parent, one for child), the columns are `Parent_Subject` and `Child_Subject`. Each declares its FK to `Subject` with an explicit constraint name; Chaise can render both as Subject references with the role label inline.

The pattern is: `<Role>_<TargetTableName>`. Keep the target table name as the suffix so the reference relationship is still readable from the column name.

### When the FK target is a vocabulary table

A column referencing a vocabulary table follows the same rule: the column name matches the vocabulary table name. A `Subject` table with a species column references `Species` (the vocab table) via a column named `Species`. The column type is `text` (vocabulary terms are looked up by name); Chaise renders the FK as a dropdown of the vocabulary's terms.

This gives the catalog a uniform shape: every column whose value is constrained to a controlled set is an FK to a vocabulary table, and the column name is the vocabulary name.

## Character restrictions and length

Per ERMrest:

| Entity | Allowed characters | Length practical limit |
|---|---|---|
| Schema | `[a-z0-9]` (lowercase letters, digits) | Keep under ~20 chars; appears in every URL |
| Table | `[A-Za-z0-9_]` (letters, digits, underscore) | Keep under ~40 chars; longer names are display-clipped in Chaise |
| Column | `[A-Za-z0-9_]` | Keep under ~30 chars; column headers in tables get cramped beyond this |
| Vocabulary term | `[A-Za-z0-9_ \-&.]` (more permissive — terms include real-world names like `H&E`, `Mus musculus`) | Keep under ~40 chars; longer names should use a short canonical name and a long description |

### What ERMrest accepts but you should avoid

- **Leading digits or underscores.** Legal, but break some downstream tooling. Always start with a letter.
- **All-caps names** (`SUBJECT`, `URL`). Legal but visually shouty in Chaise. Use `Subject` and `URL` (the latter is a borderline acceptable exception for established acronyms — see edge cases).
- **Trailing underscores or whitespace.** Legal but invisible in many contexts; a name with a trailing space is a different name from one without and produces baffling "not found" errors.

### Reserved-ish names

A few names are *not* technically reserved by ERMrest but should be avoided because they collide with standard catalog columns or Chaise behavior:

- `RID`, `RCT`, `RMT`, `RCB`, `RMB` — system columns added to every table; never use these as user column names.
- `Name`, `Description`, `Synonyms`, `ID`, `URI` — standard vocabulary table columns; avoid as table names or as columns in non-vocabulary tables.

## The specificity test

A name is sufficiently specific if a reader can answer "what does this refer to?" without context.

**Test:** if you saw the name in a Chaise filter chip, in a CSV export header, or in a tool error message — would you know what it referred to?

| Name | Specific enough? | Why |
|---|---|---|
| `Image` | No (in most catalogs) | Could be microscope image, screenshot, photograph. What's the modality? |
| `Fundus_Image` | Yes | Distinguishes from `OCT_Image`, `External_Photo`, etc. |
| `Image_Annotation` | Yes | Distinguishes from `Image` (the asset) and from generic annotation tables. |
| `Count` | No (in most catalogs) | Count of what? |
| `Cell_Count` | Yes | Specifically the count of cells. |
| `Patient` vs `Subject` | Domain-dependent | A clinical trial says `Subject`; a hospital says `Patient`. Pick one and use it consistently. |

The test fails most often in two directions:

- **Too generic** (`Image`, `Count`, `Type`, `Data`) — the name doesn't distinguish from neighbors and forces every reader to consult context.
- **Too specific** (`Image_Captured_With_External_Photographic_Equipment_For_Analysis`) — the name is a sentence rather than a label. Move the detail to the description.

## Renaming: what breaks and how to migrate

Renaming touches everything that references the entity by name:

### What breaks immediately on rename

- **All FK constraints declared by name** — drop and recreate.
- **All Chaise URLs and bookmarks** — silent 404 on visit.
- **All hardcoded references in user scripts and configs** — broken until edited.
- **Hydra-zen configs** referencing the old name — `DatasetSpecConfig(rid=..., version=...)` doesn't reference the table name, but configs that read FK column values do.
- **Active queries and bag exports** in flight at the moment of rename.

### What survives a rename

- **RIDs** — every row's RID is independent of any name. Citations or external systems that reference rows by RID are unaffected.
- **Audit logs** — historical entries preserve the names as they were at the time of the action. They never get rewritten.
- **Old bag exports** — already-exported bags continue to work in their original form; they just reference a name that no longer exists in the live catalog.

### Migration approach when a rename is unavoidable

1. **Pause writes** to the affected entity for the migration window.
2. **Drop FK constraints** that reference the old name (`update_fk_constraint` or schema-level mutation).
3. **Rename** via `update_entity` on the catalog model (renames are schema mutations, not data mutations).
4. **Re-create FK constraints** with the new name.
5. **Update every script, config, and notebook** that references the old name. Use `grep -r '\bOldName\b'` across the codebase as a starting point, but understand that some references are dynamic (constructed from variables).
6. **Communicate the change** to humans who have the old name in their muscle memory or bookmarked URLs.
7. **Don't try to alias** — Deriva does not have a "rename with backward-compat alias" feature. The old name is gone after step 3.

In practice, the cost of all this usually exceeds the cost of living with a suboptimal name. Rename within the first day of an entity's existence, or accept the name as permanent.

## Edge cases

### Established acronyms

Some acronyms are so established that breaking them up reads as wrong:
- `URL`, `URI`, `ID` — these survive as all-caps within a name (`Image_URL`, `External_ID`).
- `MD5`, `SHA256` — same.
- `H&E` (Hematoxylin and Eosin), `IHC` (Immunohistochemistry) — domain acronyms in vocabulary terms.

The rule: if writing the acronym in mixed case would look stranger than writing it in all-caps, leave it all-caps. `Image_URL` not `Image_Url`.

### Names with periods or special characters in vocabulary terms

Vocabulary terms accept a wider character set than tables/columns because they often capture real-world names (taxonomic, chemical, drug, anatomical). Examples:

- `Mus musculus` (with space) — taxonomic name; accept the space, add `Mouse` as a synonym.
- `H&E` — chemical staining acronym; accept the ampersand.
- `Type-I` — Roman numeral with hyphen; accept it if the underlying classification uses Roman numerals.

Add a PascalCase synonym if you want the term findable through programmatic search that filters on `[A-Za-z0-9_]` patterns.

### Renaming a vocabulary

Vocabulary tables are tables, so they follow the table convention (PascalCase, singular, underscores). Renaming a vocabulary is *especially* expensive because every record that uses a term references the vocabulary by name through its FK column. Treat vocabulary names as permanent.

### Schema name in flight

Renaming a schema is the most expensive operation in this whole list. Every table moves; every URL changes; every script breaks. The only realistic "rename" is to create the new schema, copy or recreate the entities into it, and deprecate the old schema over a transition period. There is no in-place schema rename worth doing.
