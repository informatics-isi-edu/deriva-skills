# Deriva Concepts Reference

Detailed definitions for the core concepts that show up in every Deriva catalog. The `SKILL.md` body has the one-line summary table and the design philosophy; this file is for "I know the name but I want a working model of what it actually is" lookups.

Read this on cold-start (first time touching a Deriva catalog in a session) or whenever a skill assumes a concept the LLM doesn't already have a working model of.

## Table of contents

1. [What is Deriva?](#what-is-deriva)
2. [Catalog](#catalog)
3. [Schema, table, column](#schema-table-column)
4. [RID — Resource Identifier](#rid--resource-identifier)
5. [Vocabulary](#vocabulary)
6. [Foreign keys](#foreign-keys)
7. [Association tables](#association-tables)
8. [Display annotations (Chaise)](#display-annotations-chaise)
9. [Asset tables and Hatrac (object store)](#asset-tables-and-hatrac-object-store)
10. [Catalog snapshots and provenance](#catalog-snapshots-and-provenance)
11. [Naming conventions (pointer)](#naming-conventions-pointer)

---

## What is Deriva?

Deriva is a platform for managing scientific data: structured metadata + bulk files + a web UI for human curation + an API surface for programmatic use, all bound together by stable identifiers and a reproducibility model.

The pieces:

- **ERMrest** — the metadata catalog server. A relational store (PostgreSQL underneath) that exposes catalogs over a REST API and tracks every change for time-travel queries.
- **Hatrac** — the object store. Content-addressed bulk file storage with its own access-control layer.
- **Chaise** — the web UI. A configurable browser that renders catalog tables, vocabularies, and assets without per-catalog frontend code.
- **deriva-py** — the Python client library. Schema introspection, queries, inserts, updates, asset upload/download, bag export.
- **deriva-mcp-core** — the MCP server. Exposes catalog operations (schema, query, vocab, annotations, file ops) to LLM clients via the Model Context Protocol.

A Deriva "deployment" is typically all five running together at one hostname, hosting one or more catalogs.

---

## Catalog

A **catalog** is the top-level container — roughly analogous to a database in PostgreSQL. Inside a catalog you have schemas, which contain tables and vocabularies, which contain rows.

**How catalogs are identified:**

- **Hostname** — the server (e.g., `data.example.org`).
- **Catalog ID** — a numeric ID assigned at creation (e.g., `1`, `42`).
- **Alias** (optional) — a human-friendly name (e.g., `cifars`) that resolves to a catalog ID.

A catalog reference is always (hostname, catalog_id-or-alias). The MCP server is stateless — every tool call passes both explicitly.

**What a catalog owns:**

- Its own schemas, tables, vocabularies, foreign keys, annotations
- Its own access-control policies (ACLs)
- Its own change history (every row insert/update/delete is recorded with a server-side timestamp)
- A `public` schema (always present) plus user-created schemas

**Multiple catalogs on one host** are fully isolated: separate ACLs, separate schemas, separate histories. Cloning a catalog produces a new catalog with its own ID and (typically) a copy-time snapshot of the source's contents — but the clone evolves independently afterward.

---

## Schema, table, column

### Schema

A **schema** is a namespace within a catalog. It groups related tables. Naming is by convention (e.g., `Image`, `Sequencing`, `deriva-ml`); there's no enforced grouping rule.

Every catalog has a `public` schema (system metadata, ACL-related views) and at least one user schema where domain tables live.

### Table

A **table** is a relational table — rows and columns — inside a schema. Two flavors:

- **Domain tables** — model your data (e.g., `Subject`, `Sample`, `Image`). Each has whatever columns the domain needs.
- **Vocabulary tables** — controlled-term lists with a standard column shape (see Vocabulary section). Distinguished from domain tables by their fixed schema, not by any flag.

Every table also has **system columns** added automatically:

| Column | What |
|---|---|
| `RID` | Catalog-wide unique resource identifier (see RID section). Primary key. |
| `RCT` | Row Creation Time (server timestamp). |
| `RMT` | Row Modification Time (server timestamp, updated on edits). |
| `RCB` | Row Created By (user ID of the inserter). |
| `RMB` | Row Modified By (user ID of the last editor). |

These are present on every table you'll ever encounter; you don't define them.

### Column

A **column** has a name, a type (text, int, float, timestamp, boolean, jsonb, and a few others), nullability, and optional defaults. Columns can be foreign keys to other tables (including vocabularies — that's the standard pattern for categorical columns).

---

## RID — Resource Identifier

A **RID** is a short, opaque, catalog-wide-unique string that identifies a row. Examples: `1-A2B3`, `2-XYZ9`. The format is roughly `<catalog-prefix>-<encoded-counter>`; the exact internal structure isn't meant to be parsed by clients.

Mechanics:

- **Server-minted at insert time.** You don't construct RIDs; the server assigns one when a row is created.
- **Universal.** Every row in every table in every Deriva catalog has a RID. There are no RID-less rows. The RID is each table's primary key.
- **Resolvable URL form.** Each RID resolves to a permanent URL: `https://<host>/id/<catalog>/<rid>`. Pasting that URL into a browser opens the row in Chaise.

For *why* RIDs are the canonical identity (and why you should FK to RIDs rather than domain keys), see the "RIDs are the canonical identity" pillar in the SKILL.md design philosophy section.

---

## Vocabulary

A **vocabulary** is a special-shaped table that holds a controlled list of terms. Vocabularies are how Deriva represents categorical values cleanly.

**Standard column shape** (created automatically when you call `create_vocabulary`):

| Column | What |
|---|---|
| `Name` | The canonical term spelling. Must be unique within the vocabulary. |
| `Description` | A definition for the term. Renders in Chaise; human-readable. |
| `Synonyms` | Alternative spellings that should resolve to this term (array). |
| `ID` | Optional external identifier (e.g., NCBI Taxonomy ID, ICD-10 code). |
| `URI` | Optional canonical URL for the term in an external ontology. |
| Plus the system columns (`RID`, `RCT`, `RMT`, `RCB`, `RMB`) | |

For *why* you'd use a vocabulary rather than a free-text column, see the "Controlled vocabularies, not text columns" pillar in the SKILL.md design philosophy section.

**Adding a term:** `add_term(schema, table, name, description, ...)`. The MCP server normalizes to canonical Name, validates the description is non-empty, and assigns a RID.

**Synonyms** are alternative names that should resolve to the same canonical term. Use `add_synonym` to register a historical spelling without rewriting any data.

See the `manage-vocabulary` skill for full CRUD patterns and the `entity-naming` skill for term naming conventions.

---

## Foreign keys

**Foreign keys (FKs)** in Deriva work the same way they do in any relational database, with two Deriva-specific conventions:

1. **FKs target RID columns**, not domain keys. The constraint is `FK(this_column) REFERENCES other_table(RID)`. This decouples the reference from any domain-level identifier that might change.
2. **FKs to vocabularies** are how you model categorical columns. `Image.Quality` is a column that FKs to `Image_Quality(RID)` where `Image_Quality` is a vocabulary table.

**Composite FKs** (multi-column) are supported but rare; most Deriva FKs are single-column → RID.

**Visible FKs in Chaise** — by default Chaise shows incoming FKs (rows that reference *this* row) on a record's detail page. The `customize-display` skill covers how to turn these on/off and reorder them.

---

## Association tables

An **association table** (also called a "linking table" or "junction table") models a many-to-many relationship between two other tables. It's a table whose primary purpose is to hold pairs of foreign keys, each pointing at one side of the relationship.

The minimum shape is two FK columns:

| Column | What |
|---|---|
| `<LeftTable>` | FK to the RID of a row in the left side of the relationship. |
| `<RightTable>` | FK to the RID of a row in the right side of the relationship. |
| Plus the system columns (`RID`, `RCT`, `RMT`, `RCB`, `RMB`) | |

Each row in the association table represents one link: "this left-side row is associated with this right-side row." Many-to-many is achieved by allowing multiple rows that share a left-side or right-side value.

### When to use an association table

| Cardinality | How to model it |
|---|---|
| **One-to-one** | A single FK column on one side. |
| **One-to-many** | A single FK column on the "many" side, pointing at the "one" side. |
| **Many-to-many** | An association table with FKs to both sides. |

The association table is the standard relational answer for many-to-many; it lets a single row on either side participate in multiple relationships without duplicating data.

### Examples

- `Subject_Study` — a Subject can be enrolled in many Studies, and a Study has many Subjects. The association table has `Subject` and `Study` FK columns.
- `Image_Tag` — an Image can carry many Tags, and a Tag is applied to many Images. The association table has `Image` and `Tag` FK columns.
- `Dataset_Image` (DerivaML) — a Dataset contains many Images, and an Image can belong to many Datasets across different experiments.

### Carrying extra metadata

Association tables can carry **additional columns beyond the two FKs** when the relationship itself has attributes:

- `Subject_Study.Enrollment_Date` — when this subject joined this study
- `Subject_Study.Role` — FK to a vocabulary of subject roles (control, case, etc.)
- `Image_Annotator.Confidence` — annotator's stated confidence for this image

When the relationship has its own data, the association table effectively becomes a first-class entity (sometimes called an "associative entity"). The system columns alone — `RCT` (created-at), `RCB` (created-by) — are often enough that no extra columns are needed; the link's existence and provenance are already recorded.

### Chaise rendering

Chaise renders association tables specially: when you view a row on either side of the relationship, Chaise can show the related rows from the other side as a list, hiding the intermediate association rows. This is controlled by the `pure-and-binary` annotation pattern (an association table is "pure and binary" if its only non-system columns are the two FKs). For details, see the `customize-display` skill.

### Naming convention

Association tables are typically named `<LeftTable>_<RightTable>` in alphabetical order (e.g., `Image_Tag`, not `Tag_Image`). For deeper conventions, see the `entity-naming` skill.

---

## Display annotations (Chaise)

**Annotations** are JSON attached to schemas, tables, columns, or foreign keys that influence Chaise's rendering. Examples:

- `tag:isrd.isi.edu,2016:visible-columns` — which columns show in row/list views, and in what order.
- `tag:misd.isi.edu,2015:display` — display name and row-name pattern for a table.
- `tag:isrd.isi.edu,2016:column-display` — pre/postfix HTML, markdown rendering, image preview for a column.

Annotations are **server-stored, web-rendered metadata** — they don't change the data, only how it's presented in Chaise. A catalog with no annotations renders functionally but with raw column names and unsorted FK lists; well-annotated catalogs feel like purpose-built apps.

The MCP server exposes annotation management as immediate (no staging step): `set_visible_columns`, `set_table_display`, `add_visible_column`, etc. apply on call. See the `customize-display` skill.

---

## Asset tables and Hatrac (object store)

**Hatrac** is Deriva's object store. It holds bulk bytes (image files, model weights, sequencing reads, anything that doesn't fit cleanly in a relational column). Each object is content-addressed by checksum and accessed by URL: `https://<host>/hatrac/<namespace>/<filename>`.

Hatrac is a separate system from the metadata catalog. It has its own ACLs, its own scaling profile, and its own API. The bridge between them is the **asset table**.

### Asset tables

An **asset table** is a regular catalog table with extra columns that describe an object in Hatrac:

| Column | What |
|---|---|
| `URL` | The Hatrac URL of the object. |
| `Filename` | The original filename (for display and download). |
| `Length` | File size in bytes. |
| `MD5` (and/or `SHA256`) | Checksum, used for content addressing and integrity verification. |
| `Content_Type` | MIME type (e.g., `image/jpeg`, `application/octet-stream`). |
| Plus any domain columns | (e.g., `Subject` FK, `Acquisition_Date`, etc.) |
| Plus the system columns | |

Asset tables are how the catalog "knows about" files in Hatrac. Queries, FKs, faceted search all work on asset rows the same as on any other table — the difference is that the row also points at bulk bytes via its URL column.

For *why* the split exists and the modeling implications (don't put bulk bytes in catalog columns; don't bury metadata in file headers), see the "Bulk bytes belong in the object store" pillar in the SKILL.md design philosophy section.

The `create-table` skill covers the asset-table column pattern; `customize-display` covers how Chaise renders asset columns (download links, image previews).

---

## Catalog snapshots and provenance

Every change to a Deriva catalog is recorded with a server-side timestamp. The catalog is **time-travelable**.

### Snaptime

A **snaptime** is a snapshot identifier — a token that addresses the catalog as of a specific moment. Format: a base32-encoded timestamp like `2T-J3M4-K56N`. You can append it to any URL: `https://<host>/ermrest/catalog/1@2T-J3M4-K56N/...`.

Querying with a snaptime returns rows as they existed at that moment, through the schema as it existed at that moment. Snaptime queries:

- See rows that were later deleted (they were live then).
- Don't see rows that were created later.
- See column values as they were then, not as they were later edited.
- Use the schema in effect then — added columns aren't visible, removed columns are.

For *why* this matters — reproducibility, citability, audit, the "don't overwrite history" modeling stance — see the "Don't overwrite history" pillar in the SKILL.md design philosophy section.

### Provenance via system columns

Every row carries `RCB` (created-by) and `RMB` (modified-by). Combined with `RCT` (created-at) and `RMT` (modified-at), every row has a basic audit trail. For deeper provenance — *which workflow run produced this row* — see the DerivaML domain layer (which is outside this plugin's scope).

---

## Naming conventions (pointer)

Deriva has consistent naming conventions for schemas, tables, columns, vocabularies, and vocabulary terms (PascalCase for tables/columns, singular nouns, descriptive names, etc.). These are documented in the `entity-naming` skill (`/deriva:entity-naming`) — read that skill before naming a new entity. The conventions are mechanical enough that a single skill handles all of them.
