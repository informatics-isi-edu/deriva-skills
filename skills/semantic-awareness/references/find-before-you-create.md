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
