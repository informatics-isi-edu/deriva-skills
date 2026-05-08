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
- `code` formatting for column names, config values, or literal RID strings you want shown verbatim (not as a link)
- **Markdown links to RIDs** — see below
- Markdown tables for parameter summaries or comparisons
- Headers for long descriptions that cover multiple aspects

### Linking to RIDs

Any RID can be turned into a clickable link using the catalog's `id` resolver. Use the **catalog-relative** form so the link works regardless of which host is serving the catalog (and survives catalog clones / staging-vs-prod deployments):

```markdown
[Image_Type vocabulary](/id/<catalog-id>/<rid>)
```

For example, a column description on `Image.Image_Type_RID` might read:

> Foreign key to the [Image_Type](/id/1/W-ABC1) controlled vocabulary. Each image is classified by exactly one type.

Notes:

- **Catalog-relative, not absolute.** Don't hardcode a hostname (`https://my-host.example.org/id/...`) — descriptions live in the catalog itself, and a deployment may be served from multiple hosts. The leading `/` makes the resolver hop relative to whichever host Chaise is rendering under.
- **Relative, not Chaise-specific.** Link via `/id/...`, not via a Chaise UI path like `/chaise/record/#1/schema:Table/RID=...`. The `id` resolver is UI-agnostic — it redirects to whatever client is appropriate. Chaise-specific URLs break if the deployment changes UIs.
- **Use only for entities that already exist** at description-write time. A column description that links to its FK target's vocabulary is fine; a description that links to "the rows that will be added later" is not.
- **Use `code` formatting (backticks) when you want the literal RID shown** without making it a link — e.g., when documenting a sentinel value: "Records with `Type_RID = W-ABC1` are excluded from the default view."

**When to reach for markdown:**

| Entity type | Markdown usage | RID linking |
|---|---|---|
| Vocabulary terms | Almost always plain text — terms are atomic concepts; structure rarely helps | Rarely useful — terms describe themselves; linking would mostly point at the term's own row |
| Columns | Plain text usually; reach for `code` formatting if mentioning a literal value or a column name | **Often useful for FK columns** — link to the target vocabulary or table so a reader can jump to the controlled-value list or the related entity |
| Tables | Mixed — short descriptions stay plain text; tables that link multiple other tables benefit from a bulleted "Links to" list | **Often useful** — when the description names related tables (parents, children, asset targets), make those names links to the related table's RID rather than just code-formatting them |
| Vocabularies | Often benefit from a list of subgroups when the vocabulary has internal structure (e.g., "Diagnoses are grouped into: respiratory (...), cardiac (...), other (...)") | Use sparingly — link to a parent vocabulary if there is one, but linking individual subgroup terms inline gets noisy fast |

Keep simple descriptions as plain text — markdown is most useful for tables and vocabularies whose descriptions need to convey several facets at once. A two-sentence vocabulary-term description doesn't need bullets, and a column whose description is "Subject's age in years at enrollment" doesn't need a link.

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
