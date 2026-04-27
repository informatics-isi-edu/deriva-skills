---
name: semantic-awareness
description: "ALWAYS use before creating new tables, vocabularies, features, datasets, or workflows in Deriva catalogs. Search for existing entities to prevent duplicates — even if names are misspelled, abbreviated, or use synonyms. Also use when looking up or referencing any catalog entity by name or concept."
user-invocable: false
---

> **Note (2026-03-16):** The Deriva MCP server now performs automatic duplicate detection (Layer 3) on all creation tools (`create_table`, `create_asset_table`, `create_vocabulary`, `create_feature`). When a near-duplicate entity is detected, the tool response includes a `similar_existing` field with suggestions and a warning message. This skill remains available as a behavioral guardrail for users on older MCP server versions that lack built-in duplicate detection.

# Catalog Semantic Awareness — Find Before You Create

Before creating ANY new catalog entity (table, vocabulary term, feature, dataset, workflow), search for existing entities that serve the same or similar purpose. Duplicate entities fragment data, confuse users, and undermine the catalog as a single source of truth.

This skill also applies when looking up any entity by name — catalog entities are created by different people at different times, so the same concept often appears under different names, spellings, or structures.


## Stateless model

The new MCP server is stateless — every tool below takes `hostname=` and `catalog_id=` arguments explicitly. There is no `connect_catalog` step. Substitute your catalog's hostname and catalog ID wherever the examples show them.


## Why This Matters

Deriva catalogs are shared, long-lived systems. When someone creates a "Diagnosis" feature without noticing that "Disease_Classification" already exists on the same table, data gets split, queries become ambiguous, and downstream consumers don't know which to use. A two-minute search before creation prevents hours of cleanup later.

## The Process

### 1. Parse Semantic Intent

Understand what the user actually needs — not just the literal name, but the underlying concept. "I need a table for patient demographics" might match an existing "Subject" table. "Add a quality label" might match an existing "Image_Quality" feature.

### 2. Expand the Search Term

Before querying, expand the user's term into a set of candidates:

- **Synonyms**: "Patient" → also search "Subject", "Participant", "Individual"
- **Abbreviations**: "DR" → also search "Diabetic_Retinopathy"
- **Spelling variants**: "Xray" → also search "X-ray", "X_ray", "X-Ray"
- **Misspellings**: "Diagnossis" → also search "Diagnosis"; "fundus" → "Fundus"
- **Singular/plural**: "Image" → also search "Images"
- **Formatting variants**: underscores vs spaces vs camelCase, capitalization differences

### 3. Query the Catalog

**Use `rag_search` as the primary discovery tool.** The RAG index includes the catalog's schema (tables, columns, FKs, feature definitions, vocabulary terms with descriptions and synonyms) and catalog data (datasets with types/versions, executions with workflow/status). Semantic embeddings make it ideal for fuzzy matching across synonyms, misspellings, and related concepts — exactly what this skill needs.

**For tables, columns, features, and vocabulary terms** — use `doc_type="catalog-schema"`:
```
rag_search("patient demographics subject", doc_type="catalog-schema")
rag_search("quality label score", doc_type="catalog-schema")
rag_search("diagnosis classification", doc_type="catalog-schema")
```

**For datasets and executions** — use `doc_type="catalog-data"`:
```
rag_search("training split labeled images", doc_type="catalog-data")
rag_search("ResNet training workflow", doc_type="catalog-data")
```

**Fall back to dedicated tools** only when you need full structured details of a specific entity already identified via RAG:
```python
get_table(hostname=..., catalog_id=..., schema=..., table=...)        # Full table structure
lookup_term(hostname=..., catalog_id=..., schema=..., table=..., name=...)  # Synonym-aware term lookup
deriva_ml_get_dataset(hostname=..., catalog_id=..., dataset_rid=...)  # Tier-2: full dataset details (deriva-ml-skills)
```

For queries that need actual data, use `query_attribute(...)` for filtered queries with column projection, `count_table(...)` for fast counts, or `get_entities(..., filter={"RID": "..."})` for a specific record by RID.

### 4. Score Closeness Across Multiple Signals

For each candidate entity, assess how close it is to what the user is looking for. No single signal is sufficient — weigh them together:

| Signal | What to check | Strong match indicator |
|--------|--------------|----------------------|
| **Name** | Edit distance, synonym match, abbreviation expansion, misspelling tolerance | Edit distance ≤ 2, or known synonym |
| **Description** | Keyword overlap, stated purpose, domain context | 3+ shared domain keywords |
| **Values/Contents** | For vocabs: term overlap. For tables: column overlap. For datasets: member overlap | 50%+ overlap in values or 3+ matching columns |
| **Relationships** | FK count, features referencing it, datasets containing it, record count | Entity with many relationships is well-established |
| **Structure** | Column types, vocabulary references, FK targets | Structural alignment suggests same purpose |

**Thresholds:**
- Match on **1 signal**: Mention as a possibility, low confidence
- Match on **2+ signals**: Present as a likely match
- Match on **name + description + data/relationships**: Almost certainly the same entity

### 5. Decide: Reuse, Extend, or Create

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

**Features:**
- Feature exists on same table, same purpose → **Reuse the existing feature**
- Feature exists but its vocabulary needs new terms → **Add terms** to the vocabulary (`add_term`)
- Feature exists on a different table → **Clarify intent** — may need a new one or may be targeting wrong table
- No match → **Create new** with a good description

**Datasets:**
- Dataset exists and matches → **Reuse**, possibly with a new version
- Dataset exists but needs more members → **Add members** (`add_dataset_members`)
- Dataset exists but needs a different split → **Split the existing dataset** (`split_dataset`)
- No match → **Create new** with a good description

**Workflows:**
- Workflow exists with same purpose → **Reuse** with different execution parameters
- No match → **Create new** with a good description

### 6. Present Matches with Evidence

When you find close matches, present them with the evidence AND a specific recommended action:

```markdown
I found existing entities that may match what you need:

### "Subject" table (RID: 1-ABC)
- **Description**: "Research participants enrolled in the study"
- **Matching columns**: Name, Age, Gender (3 of 4 requested columns match)
- **Relationships**: 5 FK references from other tables, 2 features, 450 records
- **Gap**: Missing "Enrollment_Date" column

**Recommended action**: Add an "Enrollment_Date" column to the existing Subject table
rather than creating a duplicate "Patient" table. This preserves all existing
relationships and data.
```

Let the user decide. Never create without presenting findings first.

### 7. Create with a Good Description

If no match exists, create the new entity with a clear, searchable description. Future searches depend on descriptions being informative — a vague description like "data" or "labels" makes the entity invisible.

See the `generate-descriptions` skill for templates and detailed guidance.

## Entity-Specific Gotchas

**Tables**: "Subject" vs "Patient" vs "Participant" — these are often the same concept. Check column structure and record count, not just names. A table with 500 records and 5 FK relationships is worth extending, not duplicating.

**Vocabulary terms**: Always search synonyms. "X-ray" might have synonym "Xray" or "radiograph". The right action is usually `add_synonym`, not `add_term`. Use `lookup_term(hostname=..., catalog_id=..., schema=..., table=..., name=...)` which matches against synonyms automatically.

**Features**: A feature named "Quality" and one named "Image_Quality" on the same table are almost certainly duplicates. The combination of target table + vocabulary is the strongest duplicate signal. Check how many values already exist — a feature with thousands of values is definitely established.

**Datasets**: Before creating a new training dataset, check member counts on existing datasets. An existing complete dataset with 10,000 members can be split rather than built from scratch. Check children/parents — the needed dataset may already exist as a split.

**Workflows**: Before creating "ResNet Training v2", check if "ResNet Training" already exists — you might just need different execution parameters. Check description and type.

## Recommended Invocation Order

When creating new catalog entities, multiple skills apply. Follow this order:

1. **`semantic-awareness`** — Check for duplicates first. Search for existing entities that serve the same or similar purpose before designing anything new.
2. **Domain skill** — Design and create the entity using the appropriate skill's workflow:
   - Tier-1 (this plugin): `manage-vocabulary`, `create-table`
   - Tier-2 (`deriva-ml-skills`, if installed): `create-feature`, `dataset-lifecycle`, `execution-lifecycle`, `work-with-assets`
3. **`generate-descriptions`** — Auto-generate descriptions if the user didn't provide one. Good descriptions make entities discoverable in future searches.
4. **`maintain-experiment-notes`** *(tier-2; deriva-ml-skills)* — If installed, log the decision and rationale to `experiment-decisions.md`. Record what was created, why, and any alternatives that were considered. In a tier-1-only environment, capture the rationale in your project's normal change log or PR description instead.

## The Flow

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
