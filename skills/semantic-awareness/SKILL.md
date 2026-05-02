---
name: semantic-awareness
description: "ALWAYS use before creating new tables, vocabularies, vocabulary terms, or any other catalog entity. Search the catalog for existing entities that serve the same or similar purpose — even if names are misspelled, abbreviated, or use synonyms. Also use when looking up or referencing any catalog entity by name or concept. The MCP server does not enforce duplicate prevention; this skill is the only guardrail."
user-invocable: false
---

# Catalog Semantic Awareness — Find Before You Create

This is the catalog's only guardrail against duplicate-entity creation. The MCP tool layer accepts any name without complaint — `create_table`, `add_term`, `create_vocabulary` will not warn you about a near-duplicate. **Before creating any new catalog entity, search for existing entities that serve the same or similar purpose. Reuse or extend if a match exists; create only if no match does.**

The discipline applies any time the user asks Claude to create something in the catalog (table, column, vocabulary, vocabulary term) and any time the user references an entity by name (where misspellings, abbreviations, or alternate spellings would otherwise lead to "not found" errors that should have been "did you mean ..." prompts).

## The discipline (always loaded)

When the user asks to create or reference a catalog entity:

1. **Search first** with `rag_search` — the catalog's RAG index covers schema, vocabulary terms (with synonyms), and data, so it handles the fuzzy matching against misspellings / abbreviations / synonyms that exact-name lookups miss. Use `doc_type="catalog-schema"` for tables / columns / vocabulary terms; `doc_type="catalog-data"` for data records.
2. **Score candidates across multiple signals** — name closeness, description overlap, structural alignment (matching columns / FK targets), and how well-established each candidate is (relationship count, record count). One signal alone isn't enough.
3. **For new tables specifically: also search by column shape**, not just by name and purpose. A table with similar columns to what the user is about to create is a duplicate signal even if the names differ — `Image` and `Scan` and `Photograph` can all be the same kind of row. When you find one, present three options: (a) add the user's new columns directly to the existing table; (b) keep the existing table and create a small "extra fields" table that links by FK back to it (the cleanest pattern when the user is describing a specialization of an existing entity); or (c) — only if truly necessary — create a separate parallel table. See the column-shape detection heuristic and the three-pattern decision guide in `references/find-before-you-create.md`.

4. **Steer away from both EAV and "one giant wide table."** Two opposite extremes that show up in users trying to avoid modeling work: stuffing every field into a generic `Entity_RID, Attribute_Name, Attribute_Value` table (loses types, breaks faceted search, kills vocabulary FKs) — or flattening every related entity into one wide table (forces repeated values, breaks multi-valued and many-to-many relationships, makes faceted search meaningless). **The Deriva-native middle is what the platform is designed for:** controlled vocabularies for categorical values (FK to a vocab table; see `/deriva:manage-vocabulary`), one table per entity with FKs for one-to-many relationships, and association tables (a table with two FKs, one to each side) for many-to-many. When you see the user reaching for either extreme, name it and propose the middle ground — the depth treatment with worked examples is in `references/find-before-you-create.md` ("The two extremes to avoid").
4. **Decide: reuse, extend, or create.** A close match means reuse the existing entity (or `add_synonym` / `add_column` / `add_term` to fill the gap). No match means create new — but with a good description so future searches find it.
5. **Present matches with evidence before creating.** Never create without first surfacing what exists. Let the user confirm.

The full operational workflow — search-term expansion patterns, the multi-signal scoring rubric with thresholds, the per-entity decision tree (tables / vocabularies / vocabulary terms / asset tables), entity-specific gotchas, and an example match-presentation template — lives in `references/find-before-you-create.md`. **Read that reference whenever you're actually evaluating duplicates** (which is most invocations of this skill); the body above is the discipline-level reminder that keeps the guardrail in always-on context without paying weight for the operational depth on every conversation.

## Recommended invocation order with sibling skills

When creating new catalog entities, multiple skills apply. The order:

1. **`semantic-awareness`** (this skill) — Check for duplicates first. Search before designing.
2. **Domain skill** — Use `/deriva:create-table` for domain tables, `/deriva:manage-vocabulary` for vocabularies and terms; reference `/deriva:entity-naming` for the naming conventions that apply across all entities.
3. **`generate-descriptions`** (auto-fires) — Auto-drafts a description if the user didn't supply one. Good descriptions make entities discoverable in future `semantic-awareness` searches; this is a closed-loop discipline.
4. **Capture decision rationale** in the project's change log / PR description / design notes — the catalog itself doesn't record *why* an entity was created the way it was; that's a project-side discipline.
