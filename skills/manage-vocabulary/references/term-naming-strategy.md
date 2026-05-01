# Term Naming Strategy

Canonical guidance for designing, naming, and maintaining terms in any Deriva controlled vocabulary. Vocabularies are how the catalog organizes categorical information — getting the term-level design right makes catalogs self-describing, queries intuitive, and downstream curation tractable.

This reference applies to every Deriva vocabulary: domain vocabularies you create yourself (`Tissue_Type`, `Image_Quality`, `Diagnosis`), and any built-in vocabularies that ship with the catalog. The mechanics of `add_term` / `add_synonym` / `delete_term` live in the parent `SKILL.md`; this file covers the design questions those tools don't answer.

## Table of Contents

- [The Core Principle: Orthogonal Tagging](#the-core-principle-orthogonal-tagging)
- [Identifying Dimensions](#identifying-dimensions)
- [When to Create a New Term](#when-to-create-a-new-term)
- [Naming Conventions](#naming-conventions)
- [Term Descriptions](#term-descriptions)
- [Synonyms](#synonyms)
- [Anti-Patterns](#anti-patterns)
- [The Substitution Test](#the-substitution-test)
- [Semantic Checking Before Creating Terms](#semantic-checking-before-creating-terms)

---

## The Core Principle: Orthogonal Tagging

The terms in a vocabulary describe a single conceptual dimension. The terms in different vocabularies — or in different conceptual subsets within the same vocabulary — describe independent dimensions that compose freely.

This is faceted classification from information science. The same idea underlies Kubernetes labels, library faceted search, and biomedical ontology post-coordination. The alternative — a single flat list where compound concepts like `MRI_Good_Quality` become single tags — leads to combinatorial explosion and brittle queries.

**The rule:** if two candidate terms can both apply to the same record and you wouldn't swap one for the other, they belong on different dimensions and (ideally) in different vocabularies.

## Identifying Dimensions

A dimension is a single axis of description. All terms within a dimension are mutually exclusive (or nearly so) — you'd pick one, not stack several from the same dimension.

To identify dimensions:

1. **Group terms that compete.** `Training`, `Testing`, `Validation` compete for the same slot — a dataset's partition role. That's one dimension.
2. **Look for terms that combine freely.** `Labeled` combines with `Training` or `Testing` without conflict. It's on a different dimension — annotation status.
3. **Watch for terms that always co-occur.** If you always apply `Labeled` alongside `Training`, ask whether `Labeled` carries independent information. It does — an unlabeled training set is a valid concept (e.g., self-supervised learning).
4. **Count the combinations.** If you have 3 partition roles and 2 annotation states, you should have 5 terms across 2 dimensions, not 6 compound terms in 1 dimension.

The same principle applies at the vocabulary level: when you find yourself wanting compound terms like `MRI_Good`, that's a signal you have two dimensions (modality, quality) that should be two separate vocabularies (`Image_Modality`, `Image_Quality`) rather than one combined vocabulary with cartesian-product entries.

## When to Create a New Term

A vocabulary fits a single dimension well. Adding terms to it makes sense when:

- **The new term sits on the same dimension as existing terms.** It's an alternative — picking it excludes others on the same dimension.
- **You'll filter or query by it.** Terms earn their place by being useful for discovery, faceted search, or grouping. If you'll never search "show me all records tagged X," X probably belongs in a description field rather than as a vocabulary term.
- **The concept is stable.** Vocabularies are for permanent classifications, not transient states (see Anti-Patterns below).

When the concept doesn't fit any existing vocabulary, the right move may be a **new vocabulary** rather than a term in the wrong one. See "Orthogonal vocabularies" in the parent `SKILL.md` for that decision.

Common categories where domain vocabularies emerge:

- **Content or modality** — what kind of data is in the record? (`MRI`, `CT`, `X-ray` for imaging modality; `Genomic`, `Clinical` for data domain)
- **Source or provenance** — where did the data come from? (`Cohort_A`, `Cohort_B` for study cohort; `Synthetic`, `Real_World` for data origin)
- **Purpose or stage** — what is it for? (`Pilot`, `Production` for maturity; `Augmented`, `Preprocessed` for processing state)
- **Quality or curation level** — `Curated`, `Raw`; `Expert_Reviewed`, `Auto_Generated`

Each of these typically wants to be its own vocabulary, not entries in a single shared one — that keeps each vocabulary focused on one dimension and lets users compose tags freely.

## Naming Conventions

The general rules for naming any catalog entity (PascalCase with underscores, singular form, descriptive, short, specific) are documented once in the `entity-naming` skill — see its `SKILL.md` for the quick reference and `references/naming-conventions.md` for the rationale, character restrictions, and edge cases. Read that first; this section adds **vocabulary-term-specific** elaborations that the general rules don't cover.

### Vocabulary-term-specific rules

Beyond the general PascalCase + singular + descriptive rules:

- **Don't embed the dimension.** The vocabulary table the term belongs to already names the dimension. `Training` belongs in `Dataset_Type`; do NOT write the term as `RoleTraining`, `Partition_Training`, or `Training_Type`. Repeating the dimension is noise. (This rule has no analogue for tables/columns because there's no enclosing namespace they belong to in the same way; for vocabulary terms it's the most common avoidable mistake.)

- **Don't compound dimensions.** If a record needs to be both `Training` and `Labeled`, those are two separate terms (potentially in two separate vocabularies). Never one `TrainingLabeled` term. This is the compound-tag anti-pattern and gets its own section below.

- **Keep terms shorter than column or table names.** Terms appear in UI filter chips and faceted-search dropdowns where vertical space is at a premium. 1-2 words is ideal; the long-form name belongs in the description, with synonyms covering common variants.

- **Specificity test for terms is "what would this exclude?"** A term that doesn't exclude anything (`Image` in an image catalog where everything is an image) is too generic. The Substitution Test below catches a different failure — terms that compete with existing ones on the same dimension.

### Vocabulary table names

Vocabulary tables are tables, so they follow the standard table convention from `entity-naming` (PascalCase with underscores, singular form). The convention is the same as for any catalog table; what's vocabulary-specific is *what the name should describe* — the dimension, not the terms. `Tissue_Type` (the dimension) not `Tissues` (the collection) or `Tissue_Categories` (redundant with `_Type`).

## Term Descriptions

Every term must have a description that defines its meaning in context — not just restating the name. A good description explains:

- **What the term means** in concrete terms
- **When to apply it** — the conditions under which a record gets this tag
- **How it relates to neighboring terms** — what's the boundary against the other terms in this vocabulary?

**Good term descriptions:**

- *"Pneumonia detected in chest X-ray. Use when radiological signs of pneumonia are present regardless of etiology. Mutually exclusive with `Normal`."*
- *"Borderline image quality — minor artifacts present but image is usable for training with caution. Review if model performance on this subset is unexpectedly poor."*
- *"Smooth, glassy cartilage covering joint surfaces; lacks blood vessels and nerves. Distinct from `Fibrocartilage` (intervertebral discs) and `Elastic_Cartilage` (ear, epiglottis)."*

**Bad term descriptions:**

- `"Pneumonia"` — restates the name, adds no information
- `"This is the pneumonia term"` — meta-commentary about the term, not about pneumonia
- *empty* — leaves future readers (and tooltips in Chaise) blank

For the related guidance on writing **vocabulary table** descriptions (the `comment` field on the table itself), see the parent `SKILL.md`'s Description Guidance section. Term descriptions answer a different question — what is *this term*; table comments answer what is *this dimension*.

## Synonyms

Synonyms make terms discoverable under alternative names — abbreviations, variant spellings, common misspellings, translations, casual phrasings. They are searchable through `lookup_term` and via the catalog's RAG index.

**Good candidates for synonyms:**

| Situation | Example |
|-----------|---------|
| Variant spelling | `Xray` ↔ `X-ray` ↔ `X_Ray` |
| Abbreviation ↔ expansion | `H&E` ↔ `Hematoxylin and Eosin` |
| Casual ↔ formal | `Mouse` ↔ `Mus_musculus` |
| Synonym in another language | `Hund` ↔ `Dog` |
| Common misspellings | `Diagnossis` ↔ `Diagnosis` (yes, really — RAG search picks this up) |

**Bad candidates for synonyms — these should be separate terms:**

| Situation | Why |
|-----------|-----|
| Related but distinct concept | `Cartilage` and `Connective_Tissue` are different things, not the same thing under different names |
| More specific version | `Hyaline_Cartilage` is a *kind of* cartilage, not an alias for it |
| Different dimension | `Training` and `Labeled` describe different aspects, not the same aspect |

When in doubt, ask: "would I want a record tagged with X to also count as tagged with Y for filtering purposes?" If yes → synonym. If no → separate term.

## Anti-Patterns

### Compound tags

Terms like `TrainingLabeled`, `TestingUnlabeled`, or `MRI_Good_Quality` encode multiple dimensions in one value. Symptoms:

- **Combinatorial explosion**: N × M terms instead of N + M
- **Brittle queries**: finding "all labeled records" requires enumerating every compound containing `Labeled`
- **Vocabulary bloat**: adding a third dimension multiplies the problem

**Fix:** split into independent terms (and likely independent vocabularies). `TrainingLabeled` → `Training` + `Labeled`. `MRI_Good_Quality` → `MRI` (in `Image_Modality`) + `Good` (in `Image_Quality`).

### Hierarchical encoding

Terms like `Training/Labeled/Fundus` or `Training_Labeled` smuggle a hierarchy into a flat vocabulary. Deriva vocabularies are flat by design — there's no parent-child relationship between terms.

**Fix:** use multiple terms from independent vocabularies. If you genuinely need a hierarchy (e.g., `Organ` → `Tissue` → `Cell_Type`), use separate vocabularies linked by foreign keys, not a single vocabulary with namespaced names.

### Overloaded vocabulary

A single vocabulary containing terms that span multiple dimensions — for example, an `Image_Type` containing `Training`, `Testing`, `Labeled`, `MRI`, `Pilot`, `Expert_Reviewed`. This isn't catastrophically wrong, but it makes the vocabulary harder to reason about because some terms are alternatives and others compose. Document the implicit dimensions in term descriptions, or split into multiple vocabularies (one per dimension).

**Fix:** document the implicit dimensions in term descriptions so users know which terms compete and which compose. Consider whether some of the dimensions deserve their own vocabulary.

### Terms as status vs. classification

Mixing transient states (`In_Review`, `Needs_QC`, `Awaiting_Approval`) with permanent classifications (`Training`, `Fundus`, `Hyaline_Cartilage`) in the same vocabulary. States change over a record's lifecycle; classifications describe intrinsic properties.

**Fix:** use vocabulary terms for stable classifications. Track transient states in other mechanisms — a separate status column on the record, a state-machine FK, or a workflow-state column.

### Vocabulary creep

Adding a term for every edge case rather than recognizing that a new dimension is needed. If your new terms aren't mutually exclusive with existing ones and the vocabulary keeps growing, step back and identify the underlying dimension — that's the signal for a new vocabulary, not more terms in an old one.

## The Substitution Test

A quick test for whether two candidate terms belong on the same dimension:

**Can you swap one for the other?**

- `Training` ↔ `Testing` — yes, same dimension (partition role). A record is one or the other.
- `Labeled` ↔ `Unlabeled` — yes, same dimension (annotation status).
- `Training` ↔ `Labeled` — no, different dimensions. A record can be both.
- `Hyaline_Cartilage` ↔ `Fibrocartilage` — yes, same dimension (cartilage type).
- `Hyaline_Cartilage` ↔ `Articular_Cartilage` — yes, same concept (these are synonyms, not separate terms).

**Would applying both be contradictory?**

- `Training` + `Testing` on the same record — contradictory (same dimension, mutually exclusive). Pick one.
- `Training` + `Labeled` — not contradictory (different dimensions, compose freely).

If two candidate terms pass the substitution test (swappable), they're on the same dimension and a record should have at most one of them. If they fail (not swappable), they're on different dimensions and can co-occur.

The substitution test is also the right tool for catching **near-duplicates before creation**. Before adding a new term, list it alongside the closest existing terms and ask: "would I swap this for any of those?" If yes for any, the right action is a synonym on the existing term, not a new term.

## Semantic Checking Before Creating Terms

Before adding any new term, search for existing terms that may already cover the concept — including under different names, abbreviations, or spellings. The current `deriva-mcp-core` does NOT auto-deduplicate at the catalog layer (it accepts any new term name without complaint), so the discipline lives at the skill workflow level.

**The check:**

```
# Semantic search by concept (preferred — finds synonyms, fuzzy matches)
rag_search("description of the concept", doc_type="catalog-schema")

# Synonym-aware exact lookup (fast, definitive for known names)
lookup_term(hostname="data.example.org", catalog_id="1",
            schema="myproject", table="Tissue_Type", name="Articular Cartilage")

# Full structured list (when you want to scan everything)
list_vocabulary_terms(hostname="data.example.org", catalog_id="1",
                      schema="myproject", table="Tissue_Type")
```

Common patterns the check catches:

- `Training` vs `TrainingSet` vs `Train` — same concept, different names
- `Expert_Reviewed` vs `ExpertReviewed` vs `Gold_Standard` — same concept, different conventions
- `Xray` vs `X-ray` vs `X_Ray` — same concept, different formatting
- `trainings` vs `Training` — same concept, plural vs singular

**If a near-match is found:** the right action is usually to add the new name as a synonym of the existing term, not to create a parallel term. A second term that means the same thing splits future queries — anyone searching for one set won't find records tagged with the other.

**If creating a genuinely new term:** check the existing vocabulary first to understand:
- Which dimensions are already represented (so the new term doesn't accidentally span one)
- What naming conventions are established (PascalCase? underscores?)
- Whether the new term fills a gap in an existing dimension or introduces a new one (the latter may be a signal for a new vocabulary, not a new term)

The `semantic-awareness` skill (always-on in `deriva-skills`) automates the duplicate-check step on every catalog-entity creation — including vocabulary terms. When that skill is loaded, this discipline is enforced rather than aspirational.
