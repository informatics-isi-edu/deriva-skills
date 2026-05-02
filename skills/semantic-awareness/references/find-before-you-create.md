# Find Before You Create — Operational Reference

Detailed workflow for the "find before you create" discipline that the parent `SKILL.md` enforces. Read this when you're actually evaluating whether an existing entity matches what the user wants — the SKILL.md body covers *why* and *when*; this file covers *how*.

## Why this matters at depth

Deriva catalogs are shared, long-lived systems. When someone creates a "Diagnosis" feature without noticing that "Disease_Classification" already exists on the same table, data gets split, queries become ambiguous, and downstream consumers don't know which to use. The cost of one duplicate compounds: every query that should aggregate across the concept now fragments; every reader has to learn both names; every script that summarizes the data has to reconcile them. A two-minute search before creation prevents hours of cleanup later, and the cleanup itself is destructive — merging two duplicate vocabularies after a year of annotations is not a one-evening task.

The MCP server does not enforce this. `create_table`, `add_term`, `create_vocabulary` accept any name without complaint. This skill is the only guardrail.

## The seven-step workflow

### 1. Parse semantic intent

Understand what the user actually needs — not just the literal name, but the underlying concept. "I need a table for patient demographics" might match an existing "Subject" table. "Add a quality label" might match an existing "Image_Quality" feature. The literal name is a starting point; the concept is what you search for.

### 2. Expand the search term

Before querying, expand the user's term into a set of candidates:

- **Synonyms**: "Patient" → also search "Subject", "Participant", "Individual"
- **Abbreviations**: "DR" → also search "Diabetic_Retinopathy"
- **Spelling variants**: "Xray" → also search "X-ray", "X_ray", "X-Ray"
- **Misspellings**: "Diagnossis" → also search "Diagnosis"; "fundus" → "Fundus"
- **Singular/plural**: "Image" → also search "Images"
- **Formatting variants**: underscores vs spaces vs camelCase, capitalization differences

The expansion is what makes the search robust against the catalog already containing the concept under a different surface form.

### 3. Query the catalog

**Use `rag_search` as the primary discovery tool.** The RAG index includes the catalog's schema (tables, columns, FKs, vocabulary terms with descriptions and synonyms). Semantic embeddings make it ideal for fuzzy matching across synonyms, misspellings, and related concepts.

**For tables, columns, and vocabulary terms** — use `doc_type="catalog-schema"`:

```
rag_search("patient demographics subject", doc_type="catalog-schema")
rag_search("quality label score", doc_type="catalog-schema")
rag_search("diagnosis classification", doc_type="catalog-schema")
```

**For data records** — use `doc_type="catalog-data"`:

```
rag_search("training split labeled images", doc_type="catalog-data")
```

**Fall back to dedicated tools** only when you need full structured details of a specific entity already identified via RAG:

```python
get_table(hostname=..., catalog_id=..., schema=..., table=...)              # Full table structure
lookup_term(hostname=..., catalog_id=..., schema=..., table=..., name=...)  # Synonym-aware term lookup
```

For queries that need actual data, use `query_attribute(...)` for filtered queries with column projection, `count_table(...)` for fast counts, or `get_entities(..., filter={"RID": "..."})` for a specific record by RID.

### 4. Score closeness across multiple signals

For each candidate entity, assess how close it is to what the user is looking for. No single signal is sufficient — weigh them together:

| Signal | What to check | Strong match indicator |
|--------|--------------|----------------------|
| **Name** | Edit distance, synonym match, abbreviation expansion, misspelling tolerance | Edit distance ≤ 2, or known synonym |
| **Description** | Keyword overlap, stated purpose, domain context | 3+ shared domain keywords |
| **Values/Contents** | For vocabs: term overlap. For tables: column overlap. | 50%+ overlap in values or 3+ matching columns |
| **Relationships** | FK count, references from other tables, record count | Entity with many relationships is well-established |
| **Structure** | Column types, vocabulary references, FK targets | Structural alignment suggests same purpose |

**Thresholds:**

- Match on **1 signal**: Mention as a possibility, low confidence
- Match on **2+ signals**: Present as a likely match
- Match on **name + description + data/relationships**: Almost certainly the same entity

### 4a. For new tables: also search by column shape

A "new table" question is rarely just about a name — it's about a shape. If your proposed table looks a lot like an existing one (same kinds of columns, same kind of row), creating it as a parallel new table fragments your dataset in ways that hurt later: queries that should aggregate across the concept now have to UNION two tables; downstream consumers don't know which to use; and the rich relationships (foreign keys, asset uploads, display annotations, RAG indexing) that the existing table already has don't transfer to the new one.

The detection signal here is **column overlap**, not name overlap. `Image`, `Scan`, and `Photograph` can all be the same kind of row under different names. `Subject`, `Participant`, and `Donor` can all be the same kind of row under different names. The way to spot this is to look at the columns, not the table name.

**How to detect column-shape overlap:**

1. Look at the columns the user is asking for. Pick 2-3 that are *distinctive* — the ones that say something specific about the domain (e.g., `Tissue_Type`, `Acquisition_Date`, `Genotype`) rather than generic columns that show up everywhere (e.g., `Name`, `Description`, `Created_At`).
2. Run `rag_search` for each in `doc_type="catalog-schema"`. The results will surface tables that already carry those distinctive columns.
3. For each candidate table, look at its full column list. Roughly: how many of the user's columns are already there, and how many extra columns does the candidate have?

**Three patterns, three different responses:**

| Column-overlap pattern | What's likely going on | What to offer the user |
|---|---|---|
| **The candidate table has most of your columns, and most of its columns are yours** | You're describing the same kind of row as an existing table — just with a different name in mind. | **Reuse the existing table.** Add any genuinely missing columns to it with `add_column`. |
| **The candidate table has most of your columns, and you have a few extra** | You're describing a specialization — "like the existing table, but for these particular rows we also need to record X and Y." | Offer two options: **(a)** add the extra columns directly to the existing table, leaving them null for rows that don't need them (works well when the specialization is small and the columns are naturally optional); or **(b)** create a small new table that links by FK to the existing one and carries just the extra columns (works well when the specialization is more meaningful, or when more variants might follow). See "Three patterns when your row is *like* an existing one" below for a fuller treatment. |
| **You have a subset of the candidate's columns** | You're describing a filtered or specialized view of an existing concept, not really a new entity. | **Use the existing table directly.** If you need a way to mark "these are the special rows," add a tag column (FK to a vocabulary like `Subject_Type`) rather than creating a new table. The same row in the existing table can then be selected when needed. |

**Present the comparison concretely.** Don't just say "I think this might be a duplicate" — show the columns side by side so the user can judge:

```
The catalog already has an `Image` table with these columns:
  Filename, URL, MD5, Length, Subject, Acquisition_Date, Modality

You're proposing a `Scan` table with these columns:
  Filename, URL, MD5, Length, Subject, Scan_Date, Modality, Slice_Thickness

5 of your 8 columns are an exact match (Filename, URL, MD5, Length, Subject, Modality).
Acquisition_Date and Scan_Date almost certainly mean the same thing.
The only genuinely new column is Slice_Thickness.

Three options:
  1. Reuse the existing Image table. Add Slice_Thickness as a new column
     on Image, nullable for non-CT/MRI rows. Simplest; preserves all
     existing labels, asset uploads, and Chaise display work.
  2. Keep using Image for the file metadata, and add a small CT_Scan_Detail
     table that links back to Image by FK and carries just Slice_Thickness
     (and any future CT-specific fields). Cleaner if you anticipate other
     scanner-specific fields.
  3. Create a separate Scan table only if you're certain Image and Scan
     should be disjoint — i.e., a row will never be both at once. The
     overlap above suggests they shouldn't be.

Which best matches what you're trying to capture?
```

### Three patterns when your row is *like* an existing one

ML schemas often grow in waves: you start with a generic `Image` table, then later need to record CT-specific or microscopy-specific fields, then later need to handle annotated vs unannotated images differently. The question "should I add columns or make a new table?" is exactly the question that shows up here — and there are three answers, each right for a different situation.

The mental model that works: this is the same problem you'd have in code if you had a base `Image` class and then needed a `CTImage` that adds two extra fields. You wouldn't reach for "subclass with a duplicate copy of every parent attribute" — you'd subclass and add only the new attributes, or you'd add an optional field to the base class. The three patterns below are the table-shaped versions of those choices.

| Pattern | The shape | When this is right |
|---|---|---|
| **Add columns to the existing table; mark the variant with a tag** | One table holds everything. New columns are nullable for rows that don't need them. A `Type` column (FK to a vocabulary like `Image_Type`) tags which variant each row is. | The variants overlap a lot (most columns are shared), most rows are one variant with only a few specialized, and the variant-specific columns are few. Simplest to query (one `SELECT FROM Image` returns everything). The risk: if the variants diverge a lot over time, you end up with many always-null columns and fragile queries. |
| **Keep the parent; add a small "extra fields" table that FKs back to it** | The base table (`Image`) carries the shared columns. One small child table per variant (`CT_Image_Detail`, `Microscopy_Image_Detail`) FKs back to the base via the parent's `RID` and carries only the variant-specific columns. | The variants share most columns but each has a meaningful set of extras, and you anticipate adding more variants later. This is the cleanest pattern in Deriva — the base table accumulates all rows; the child tables accumulate only the relevant specialization. Queries that need everything join base+child; queries that only need the base ignore the children. Maps directly to Deriva's RID-based FK semantics. |
| **Two truly separate tables, no shared parent** | Each variant has its own table, carrying the full column set including columns that happen to overlap with another table. | Rare. Right only when the variants are *truly disjoint* — there's no useful shared query, the shared columns happen to coincide but don't actually represent the same concept, and you have no need to treat both as "the same kind of thing" anywhere. **If you can't justify all three of those conditions, you don't have this case.** Most "two separate tables" intuitions are actually the second pattern in disguise. |

**Default to the second pattern** (parent + small specialization child) when the row really is a specialization of an existing one. It's the cleanest in Deriva, scales well as more variants accrue, and avoids both the null-sprawl risk of the first pattern and the duplication risk of the third.

### Two ways this question goes wrong

These are the antipatterns to watch for in the user's intuition (or in your own draft response):

1. **The "let's make it generic" escape hatch.** Faced with the difficulty of "should I extend or should I split?", a designer is sometimes tempted to create a generic `Attribute` table with columns `Row_RID, Attribute_Name, Attribute_Value` and then have every variant stuff its specialized fields in there as rows rather than columns. **Don't propose this.** It moves the problem from "schema design" to "your queries become impossible" — Chaise faceted search stops working, joins to vocabularies break, types become opaque, and every consumer of the data has to reconstruct a schema from the values. Pick one of the three patterns above instead. (For data scientists: this is the schema equivalent of stuffing every model's outputs into a single "results" dict and never knowing what fields exist where. The flexibility looks appealing right up until you have to write a real query against it.)

2. **Parallel "almost-duplicate" tables that quietly drift over time.** The path of least resistance — "this is *kind of* like Image but it's for the new project, so let's just make `Image_v2`" — produces a catalog that within a year has `Image`, `Image_2024`, `Image_For_Study_X`, `Image_For_Study_Y`. Each one started as a copy of an existing table and then evolved independently. Now they have 80% column overlap, no shared queries possible, and any cross-project analysis has to reconcile four schemas. The right move at the start was the second pattern (parent + variant-specific child). The right move now is a painful migration. **When you spot the user heading toward this, name it explicitly:** "I'd push back on creating a parallel table here — that pattern tends to fragment data as the project grows. Two cleaner alternatives are…"

### 5. Decide: reuse, extend, or create

Based on the candidates found, recommend one of these actions. The right action depends on the entity type and what gap exists:

**Tables:**
- Table exists and fully matches → **Reuse as-is**
- Table exists but missing columns → **Add columns** (`add_column`)
- Table exists but missing a relationship → **Add a foreign key**
- No match → **Create new** with a good description

**Vocabulary terms:**
- Term exists under different spelling → **Add a synonym** (`add_synonym`)
- Vocabulary exists but term is missing → **Add the term** (`add_term`)
- Term exists in a different vocabulary → **Point user to the correct vocabulary**
- No match → **Create new term** with a good description

**Vocabularies:**
- Vocabulary exists with the right scope → **Reuse, extend with terms as needed**
- Vocabulary exists but the scope is wrong (e.g., overlapping with a more general one) → **Surface the conflict**; reuse the more general one with a synonym, or split deliberately
- No match → **Create new vocabulary** with a clear scope description

**Asset tables and other domain tables:**
- Table exists with the right structure → **Reuse**
- Table exists but missing the asset columns → **Add asset columns** (rather than creating a parallel table)
- No match → **Create new** with a good description

### 6. Present matches with evidence

When you find close matches, present them with the evidence AND a specific recommended action:

```markdown
I found existing entities that may match what you need:

### "Subject" table (RID: 1-ABC)
- **Description**: "Research participants enrolled in the study"
- **Matching columns**: Name, Age, Gender (3 of 4 requested columns match)
- **Relationships**: 5 FK references from other tables, 450 records
- **Gap**: Missing "Enrollment_Date" column

**Recommended action**: Add an "Enrollment_Date" column to the existing Subject table
rather than creating a duplicate "Patient" table. This preserves all existing
relationships and data.
```

Let the user decide. Never create without presenting findings first.

### 7. Create with a good description

If no match exists, create the new entity with a clear, searchable description. Future searches depend on descriptions being informative — a vague description like "data" or "labels" makes the entity invisible.

See the `generate-descriptions` skill for templates and detailed guidance.

## Entity-specific gotchas

**Tables** — "Subject" vs "Patient" vs "Participant" — these are often the same concept. Check column structure and record count, not just names. A table with 500 records and 5 FK relationships is worth extending, not duplicating.

**Vocabulary terms** — Always search synonyms. "X-ray" might have synonym "Xray" or "radiograph". The right action is usually `add_synonym`, not `add_term`. Use `lookup_term(hostname=..., catalog_id=..., schema=..., table=..., name=...)` which matches against synonyms automatically.

**Vocabularies** — A "Diagnosis" vocabulary and a "Disease" vocabulary on the same domain are almost certainly duplicates. The combination of column FKs that reference them is the strongest duplicate signal. Check what already FKs to each.

**Asset tables** — Before creating an "Image" asset table, check if "File" or "Document" or a domain-specific asset table already covers it. The Hatrac URL + filename + MD5 columns are diagnostic; any table with that shape is an asset table.

## Recommended invocation order

When creating new catalog entities, multiple skills apply. Follow this order:

1. **`semantic-awareness`** — Check for duplicates first. Search for existing entities that serve the same or similar purpose before designing anything new.
2. **Domain skill** — Design and create the entity using the appropriate skill's workflow: `manage-vocabulary` for vocabularies and terms, `create-table` for domain tables, `entity-naming` for the naming conventions that govern all entities.
3. **`generate-descriptions`** — Auto-generate descriptions if the user didn't provide one. Good descriptions make entities discoverable in future searches.
4. **Capture the decision rationale** in the project's normal change log, PR description, or design notes — what was created, why, and what alternatives were considered. The catalog itself doesn't record design rationale; that's a project-side discipline.

## The flow at a glance

```
User requests creation or lookup
  → Parse semantic intent (what do they actually need?)
  → Expand search terms (synonyms, abbreviations, misspellings)
  → Query catalog resources for candidates
  → Score closeness across multiple signals
  → Assess: reuse, extend, or create?
  → Present matches with evidence and recommended action
  → User decides
  → Execute the chosen action (with good description if creating new)
```
