# Description Templates and Quality Guidelines

Templates and depth content for `/deriva:generate-descriptions`. Read this when you're actually drafting a description for a specific entity type — the parent `SKILL.md` has the trigger logic and the four-question quality frame; this file has the per-entity templates, worked examples, markdown-formatting guidance, and the quality checklist.

## Templates by entity type

### Vocabularies

Vocabulary table descriptions explain the classification scheme and its scope:

```
<What this vocabulary classifies>. <Domain context>. <How terms relate to each other>.
```

**Example:** "Classification of chest X-ray diagnostic findings. Terms are mutually exclusive primary diagnoses. Used as the value domain for the Image_Diagnosis foreign-key column."

Note what makes this work: it says what the vocabulary covers, what *kind* of values its terms are (mutually exclusive primary diagnoses — not free-form notes), and where it's referenced from. A reader landing on this vocabulary's Chaise page knows immediately whether their value belongs in this list.

### Vocabulary terms

Term descriptions define the term's meaning *in context* — not just restating the name. Include when to use (and when not to), and how the term relates to other terms in the vocabulary.

```
<Definition>. <When to use>. <Relationship to other terms>.
```

**Example:** "Pneumonia detected in chest X-ray. Use when radiological signs of pneumonia are present regardless of etiology. Mutually exclusive with 'normal'; may co-occur with 'pleural effusion'."

Why the "when to use" matters: term descriptions get read by annotators trying to decide which term applies. A term named "Pneumonia" with description "Pneumonia" tells them nothing they didn't already know from the name. A term whose description tells them how to choose vs. neighboring terms makes the annotation reliable.

### Tables

```
<What records represent>. <Key relationships>. <Primary use case>.
```

**Example:** "Individual chest X-ray images with associated metadata. Links to Subject (patient) and Study (imaging session) tables. Primary asset table for the imaging archive."

The "key relationships" line is what makes the description searchable: someone searching for "subject images" via `rag_search` finds this table because the description mentions Subject explicitly, even though the table name is "Image."

### Columns

```
<What value represents>. <Format/units>. <Constraints or valid values>.
```

**Example:** "Patient age at time of imaging in years. Integer value, range 0-120. Required for demographic stratification."

Units are the most-frequently-omitted piece. "Age" alone leaves the reader wondering if it's years, months, or days — which becomes a real bug when downstream analysis reads the column without checking. Always state the unit when there could be more than one reasonable choice.

## Markdown formatting

Descriptions support **GitHub-flavored Markdown** which renders in the Chaise web UI. Use markdown to make descriptions more readable, especially for longer or structured content:

- **Bold** and *italic* for emphasis
- Bulleted or numbered lists for multi-part descriptions
- `code` formatting for RIDs, column names, or config values
- Markdown tables for parameter summaries or comparisons
- Headers for long descriptions that cover multiple aspects

**When to reach for markdown:**

| Entity type | Markdown usage |
|---|---|
| Vocabulary terms | Almost always plain text — terms are atomic concepts; structure rarely helps |
| Columns | Plain text usually; reach for `code` formatting if mentioning a literal value or a column name |
| Tables | Mixed — short descriptions stay plain text; tables that link multiple other tables benefit from a bulleted "Links to" list |
| Vocabularies | Often benefit from a list of subgroups when the vocabulary has internal structure (e.g., "Diagnoses are grouped into: respiratory (...), cardiac (...), other (...)") |

Keep simple descriptions as plain text — markdown is most useful for tables and vocabularies whose descriptions need to convey several facets at once. A two-sentence vocabulary-term description doesn't need bullets.

## Quality checklist

Before finalizing any description, verify it is:

- **Specific**: Avoids generic language like "a table" or "some values"
- **Informative**: Provides enough context for someone unfamiliar with the project
- **Accurate**: Correctly reflects the entity's actual contents and purpose
- **Concise**: No unnecessary words, but complete enough to be useful
- **Consistent**: Matches the tone and style of existing descriptions in the catalog
- **Actionable**: Helps users understand how to use the entity

## Common failure modes

These are the patterns that produce descriptions which fail the checklist — watch for them in drafts:

- **Restatement of the name.** Description: "The Subject table." That's the name; the description has to add information.
- **Vague stand-ins for content.** "Various data about images" / "Different kinds of patient information" / "Records related to the study." None of these tell a reader anything actionable.
- **Internal jargon without expansion.** "Used by the LAC pipeline." If "LAC" isn't defined elsewhere in the catalog, the description is opaque to anyone outside the original team.
- **Overlong narrative.** Two sentences usually suffice. A six-paragraph description for a column is a sign the description is doing the job of documentation that should live elsewhere (a project README, a paper).
- **Unit-omission.** "Age", "Duration", "Size" with no units. Always specify.
- **Stale references.** "Used by the v1 ResNet pipeline (deprecated)" when the v1 pipeline is long gone. Descriptions are part of the catalog — keep them current along with the data.

## Workflow when the user already provided a description

If the user supplied a description, don't auto-rewrite it — use the quality checklist above to evaluate, and ask the user before changing anything. The user's wording often carries domain context (correct terminology, regulatory framing, project-specific conventions) that an auto-generated draft can lose.

If the user-supplied description fails the checklist, surface the issue ("the description doesn't say what units the value is in") rather than silently rewriting.
