---
name: getting-started
description: "ALWAYS use this skill when a user is new to Deriva or new to a specific catalog and asks where to start, what they can do, how to begin, or any variation of 'I just installed this' / 'I'm new to Deriva' / 'I have no idea what to do' / 'walk me through this' / 'first time' / 'getting started'. Also use when a user asks open-ended exploration questions about a Deriva catalog they haven't worked with before. Provides a five-step onboarding walk-through (verify the connection → explore the catalog's structure → look at some real data → make a small safe mutation → load some data) with explicit handoffs to the per-task skills (query-catalog-data, create-table, manage-vocabulary, load-data, troubleshoot-deriva-errors). Triggers on: 'getting started', 'get started', 'where do I start', 'how do I begin', 'I am new to deriva', 'first time with deriva', 'first session', 'just installed deriva', 'new to this catalog', 'walk me through deriva', 'help me start', 'orientation', 'onboarding', 'I have no idea where to start', 'show me how to use this'."
user-invocable: true
disable-model-invocation: true
---

# Getting Started with Deriva

This skill is the orientation for a user who has never touched a Deriva catalog (or hasn't touched *this* catalog) and needs a path through their first session. It's organized as five steps in the order they make sense — each step does just enough to learn one thing and produce a visible result, with an explicit handoff to the per-task skill that owns the deeper work.

If you (the LLM) land here because the user said "where do I start" or similar, walk them through the steps below in order. Don't skip ahead unless the user redirects. Each step has a "what to ask the user" prompt — use those rather than assuming context.

## Before you start: what is Deriva?

Deriva is a data-centric platform — the data is the artifact, and the platform manages how a collection of data evolves over time (every change recorded, every state recoverable, every entity citable). Think Wikipedia, but for structured scientific data. The full framing is in the always-on `deriva-context` skill; the operational checklist (what to think about when designing a model that fits the platform) is the modeling table in that skill's body.

You'll be working through:

- **Catalogs** (the top-level container, identified by hostname + catalog ID)
- **Schemas** (namespaces within a catalog)
- **Tables** (rows of data, with columns and foreign keys)
- **Vocabularies** (controlled-term tables; categorical columns FK to these)
- **RIDs** (every row has a unique, server-minted, citable identifier)

If the user is unfamiliar with any of these, the `deriva-context` concept index has one-line definitions; the `deriva-context/references/concepts.md` reference has the depth.

## The five steps

### Step 1 — Verify the connection

Before doing anything, confirm the MCP server is reachable and you know which catalog you're working with.

**Ask the user:** "What hostname and catalog ID are you working with? (For example, `data.example.org` and `1`.)"

If they don't know, point them at the deployment they got the credentials from — the server administrator can tell them. If they're testing locally or with a sandbox, common hostnames are `localhost` (Docker dev setup) or a project-specific dev host.

**Verify reachability:** call `server_status(hostname="...")`. The response includes the running `deriva-mcp-core` framework version plus the list of loaded plugins. If this fails with a connection error, jump to `/deriva:troubleshoot-deriva-errors` immediately — there is no point continuing until the connection works.

**If it returns successfully**, mention to the user what they're connected to (server version, hostname). This grounds the rest of the session in a known good state.

### Step 2 — Explore the catalog's structure

Now that the connection works, find out what's in the catalog. The right tool for cold-start exploration is `rag_search` against the schema index.

**Ask the user:** "What kind of data are you expecting to find / want to look at? Even a rough description helps — 'imaging studies', 'sequencing data', 'clinical trial records', 'just curious what's here'."

Then:

- For "just curious" or no specific interest, call `rag_search("overview of what's in this catalog", doc_type="catalog-schema")` to surface the major tables.
- For a specific topic, search for it: `rag_search("imaging studies", doc_type="catalog-schema")` or `rag_search("subject demographics", doc_type="catalog-schema")`.

This lands the user in the relevant part of the schema without forcing them to know the exact table names. Hand off to `/deriva:query-catalog-data` for the deeper exploration patterns (denormalized views, foreign-key traversal, how to read the schema systematically).

**Tell the user what you found** — name the major tables, note any vocabularies, mention any obvious relationships. A reader who can name three tables in their catalog after this step has a working mental model.

### Step 3 — Look at some real data

Schema alone isn't enough — the user needs to see what the rows actually look like. Pick one of the tables you surfaced in Step 2 and read a small sample.

**Ask the user:** "Which of those tables looks most relevant to you? I'll show you a few rows."

Then call `get_table_sample_data(hostname=..., catalog_id=..., schema=..., table=...)` to fetch a small sample (default is 10 rows, which is plenty for orientation).

**Show the user what came back** — the columns, their values, anything that stands out (asset URLs, vocabulary FKs, descriptive columns). If the table has an `RID` column whose value resolves in Chaise, mention that they can paste any RID into the URL `https://<host>/id/<catalog>/<rid>` to open the row in the web UI.

For deeper queries (filters, joins, denormalized views), hand off to `/deriva:query-catalog-data`. The body of that skill leads with `rag_search` and covers everything from "find rows by a value" to "build a flat view across multiple tables."

### Step 4 — Make a small, safe mutation

The user now knows the catalog exists, what's in it, and what real rows look like. The next learning step is to *change* something — a small, reversible mutation that demonstrates the create / update path without risking real data.

The right first mutation depends on the user's permissions and whether they have write access to anything beyond a personal sandbox. Two safe options:

- **Add a vocabulary term** to an existing vocabulary (small, reversible, the catalog gracefully handles even a "test" term that gets deleted later). Hand off to `/deriva:manage-vocabulary`.
- **Add a column** to a table the user owns (in a sandbox catalog, not production). Hand off to `/deriva:create-table`. Mention `add_column` specifically — adding is much less risky than creating a whole table.

**Important:** before any creation, the always-on `semantic-awareness` skill will check for duplicates — if the user wants to add a term that already exists (even with a different spelling), `semantic-awareness` will surface that and offer to add a synonym instead. This is the catalog's core guardrail; let it run.

**If the user has only read access**, skip Step 4 entirely and tell them so. Read-only is a perfectly valid role; not everyone needs to mutate the catalog. Move to Step 5 if it's relevant; otherwise wrap up.

### Step 5 — Load some data

The most common new-user task after the orientation is "I have a CSV / a directory of files that needs to go into the catalog." The full surface is in `/deriva:load-data`.

**Ask the user:** "Do you have data you want to load? If yes, what shape — CSV / JSON / a directory of files like images?"

The handoff differs by data shape:

- **Tabular data (CSV / JSON / dataframe)** → `/deriva:load-data` body, "Single-row and batch insert" section. The `references/workflow.md` reference has worked templates with pandas.
- **A directory of files (images, sequencing reads, microscopy data)** → `/deriva:load-data` body, "Asset upload" section. For anything beyond a handful of files, the production path is `deriva-upload-cli` with an upload spec — see the `references/upload-spec.md` reference for spec authoring.
- **Vocabulary terms in bulk** → `/deriva:manage-vocabulary` for the per-term `add_term` loop pattern.

Loading is where new users hit their first real complexity, but the skill above covers the patterns; this orientation skill's job is to point there and let it own the depth.

## What this skill does NOT cover

This skill is *orientation*. It does not cover:

- **Schema design at depth** — that's `/deriva:create-table` plus `/deriva:entity-naming` plus the modeling checklist in `deriva-context`.
- **Production data loads** — that's `/deriva:load-data` with its references.
- **Chaise UI customization** — that's `/deriva:customize-display`.
- **Domain-specific abstractions on top of the catalog** (e.g., DerivaML's Datasets, Workflows, Executions) — those live in companion plugins like `deriva-ml`. If a user mentions one of those by name, hand off to the relevant plugin rather than improvising.

The five steps above will get a new user through their first session productively. After that, they should be able to navigate to the per-task skills on their own; this orientation has done its job.

## Related skills

- **`/deriva:query-catalog-data`** — Step 2 (exploration) and Step 3 (sampling) hand off here for depth. Also the cold-start landing point if a user lands on `query-catalog-data` directly without going through this skill first.
- **`/deriva:create-table`** — Step 4 hand-off for column / table creation.
- **`/deriva:manage-vocabulary`** — Step 4 hand-off for adding terms.
- **`/deriva:load-data`** — Step 5 hand-off for any real data ingestion.
- **`/deriva:troubleshoot-deriva-errors`** — Step 1 hand-off when the connection fails; also where to land for any error during the walkthrough.
- **`/deriva:entity-naming`** — Reference when Step 4 needs naming guidance.
- **`deriva-context`** (always-on) — The concept index and modeling checklist that ground every step. The data-centric framing in its body is the right "what is Deriva for?" answer to give the user up front.

The plugin-wide context (concept index, modeling checklist, design philosophy) is always loaded via `deriva-context`; this skill assumes that's available and doesn't restate it.
