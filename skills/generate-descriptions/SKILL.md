---
name: generate-descriptions
description: "ALWAYS use when creating any Deriva catalog entity (table, column, vocabulary, vocabulary term) and the user hasn't provided a description. Auto-generate a meaningful description from context (the user's request, repository structure, conversation history, existing catalog entities) and present it for confirmation before creating the entity."
user-invocable: false
---

# Generate Descriptions for Catalog Entities

Every catalog entity that accepts a description should have one. Descriptions appear in Chaise (so users browsing the catalog can understand what each table / column / vocabulary / term means without consulting external documentation), drive `rag_search` discovery (so future `semantic-awareness` searches find the entity by concept and not just by name), and support GitHub-flavored Markdown for richer rendering.

When the user creates an entity without supplying a description, draft one from context, present it for confirmation, then proceed with creation. **Never create with a missing or empty description; never silently auto-generate without confirmation.**

## Entities that take a description

| Entity | Where the description is set |
|---|---|
| **Tables** | `create_table` — `comment` parameter; or `set_table_description` afterward |
| **Columns** | `create_table` columns — `comment` parameter; or `set_column_description` afterward |
| **Vocabularies** | `create_vocabulary` — `comment` parameter |
| **Vocabulary terms** | `add_term` — `description` parameter |

The quality criteria are the same across all four — what makes a good description doesn't change between vocabularies, terms, tables, and columns.

## Drafting workflow

1. **Check whether the user provided a description.** If they did, evaluate against the quality criteria below; if it's good, use as-is. If it's vague or unit-omits, surface the issue rather than silently rewriting.
2. **If no description was provided, gather context** from the user's request and stated intent, the repository (README, configs, related code), conversation history, and existing catalog entities of the same type (for tone and style consistency).
3. **Draft a description** that answers four questions: **What** is this entity? **Why** does it exist? **How** is it used? **What does it contain** (for tables and vocabularies)?
4. **Present the draft for confirmation** before creating the entity. Descriptions are persistent and become hard to change later (they're referenced from Chaise, from `rag_search` results, from anywhere a downstream consumer reads catalog metadata) — get them right before they harden.
5. **Create the entity with the approved description.**

## What good looks like

A description should let a reader who has never seen the catalog understand what the entity is, what kind of values or rows it carries, and when they would interact with it. Two sentences usually suffice; markdown is for tables and vocabularies whose descriptions genuinely need structure.

**Bad:** "Images" / "Table for storing image data" / "Various information about subjects"
**Good:** "Individual chest X-ray images with associated metadata. Links to Subject (patient) and Study (imaging session) tables. Primary asset table for the imaging archive."

The good example: specific (chest X-ray images, not "images"), names the relationships, names the use case. Searchable by `rag_search` because it mentions Subject and Study explicitly.

## Per-entity templates and depth

For per-entity templates (vocabularies, vocabulary terms, tables, columns), worked examples that explain *why* each example works, markdown-formatting guidance for when structure helps vs. when plain text is better, the full quality checklist, common failure modes to watch for in drafts, and workflow guidance for the case where the user already provided a description — see **`references/templates.md`**.

Read the reference whenever you're actually drafting a description for a specific entity type. The body above is the trigger logic and quality framing that earns always-on weight; the templates are depth that only matters when a description is being written.
