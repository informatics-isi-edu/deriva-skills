---
name: generate-descriptions
description: "ALWAYS use when creating any Deriva catalog entity (table, column, vocabulary, vocabulary term) and the user hasn't provided a description. Auto-generate a meaningful description from context."
user-invocable: false
---

# Generate Descriptions for Catalog Entities

Every catalog entity that accepts a description MUST have one. If the user doesn't provide a description, generate a meaningful one based on context from the repository, conversation, and catalog state. Descriptions support GitHub-flavored Markdown which renders in the Chaise web UI.

## Entities Requiring Descriptions

Catalog entities that accept a description:

- **Vocabularies**: `create_vocabulary` -- comment parameter
- **Vocabulary Terms**: `add_term` -- description parameter
- **Tables and Columns**: `create_table` (uses `comment` parameter), `set_table_description`, `set_column_description`

The description-quality guidance below applies uniformly across all of these — what makes a good description doesn't change between vocabularies, terms, tables, and columns.

## How to Generate Descriptions

Gather context from:

1. The user's request and stated intent
2. Repository structure (README, config files, existing code)
3. Existing catalog entities and their descriptions (for consistency)
4. Conversation history and decisions made

Create a description that answers:

- **What** is this entity?
- **Why** does it exist?
- **How** is it used?
- **What does it contain** (for tables)?

Always confirm the generated description with the user before creating the entity.

## Templates by Entity Type

### Vocabularies

Vocabulary table descriptions explain the classification scheme and its scope:

```
<What this vocabulary classifies>. <Domain context>. <How terms relate to each other>.
```

Example: "Classification of chest X-ray diagnostic findings. Terms are mutually exclusive primary diagnoses. Used as the value domain for the Image_Diagnosis foreign-key column."

### Vocabulary Terms

Term descriptions define the term's meaning in context — not just restating the name. Include when to use (and when not to), and how the term relates to other terms in the vocabulary.

```
<Definition>. <When to use>. <Relationship to other terms>.
```

Example: "Pneumonia detected in chest X-ray. Use when radiological signs of pneumonia are present regardless of etiology. Mutually exclusive with 'normal'; may co-occur with 'pleural effusion'."

### Tables

```
<What records represent>. <Key relationships>. <Primary use case>.
```

Example: "Individual chest X-ray images with associated metadata. Links to Subject (patient) and Study (imaging session) tables. Primary asset table for the imaging archive."

### Columns

```
<What value represents>. <Format/units>. <Constraints or valid values>.
```

Example: "Patient age at time of imaging in years. Integer value, range 0-120. Required for demographic stratification."

## Formatting with Markdown

Descriptions support **GitHub-flavored Markdown** which renders in the Chaise web UI. Use markdown to make descriptions more readable, especially for longer or structured content:

- **Bold** and *italic* for emphasis
- Bulleted or numbered lists for multi-part descriptions
- `code` formatting for RIDs, column names, or config values
- Markdown tables for parameter summaries or comparisons
- Headers for long descriptions that cover multiple aspects

Keep simple descriptions as plain text — markdown is most useful for tables and vocabularies whose descriptions need to convey several facets at once.

## Quality Checklist

Before finalizing any description, verify it is:

- **Specific**: Avoids generic language like "a table" or "some values"
- **Informative**: Provides enough context for someone unfamiliar with the project
- **Accurate**: Correctly reflects the entity's actual contents and purpose
- **Concise**: No unnecessary words, but complete enough to be useful
- **Consistent**: Matches the tone and style of existing descriptions in the catalog
- **Actionable**: Helps users understand how to use the entity

## Workflow

1. Check if the user provided a description
2. If not, gather context from all available sources
3. Draft a description using the appropriate template
4. Present the draft to the user for confirmation
5. Create the entity with the approved description
