---
name: evolve-schema
description: "ALWAYS use this skill when restructuring an existing Deriva catalog's schema — splitting a table into two, moving a foreign key to a new target, merging tables, changing a column's type, dropping columns or tables, or any operation where existing data has to migrate to a new structure. This is the runbook for catalog evolution after the initial schema is in place; for the initial schema creation use /deriva:create-table, for naming conventions and the rename mechanics use /deriva:entity-naming. Triggers on: 'migrate schema', 'evolve schema', 'restructure tables', 'split a table', 'merge tables', 'move a foreign key', 'change column type', 'drop a column', 'backfill column', 'rename a column', 'restructure the catalog', 'schema migration', 'how do I refactor', 'change the table structure', 'pull X out into a separate table', 'old design needs to change'."
user-invocable: true
disable-model-invocation: true
---

# Evolving a Deriva Catalog's Schema

This is the runbook for **restructuring an existing catalog** — the operations you reach for after the initial design proves wrong, the requirements change, or the data outgrows its original shape. For initial schema creation, use `/deriva:create-table`. For what to call new entities and the cost framing of renames, see `/deriva:entity-naming` — its `references/naming-conventions.md` has the 7-step rename procedure, which this skill won't duplicate.

> **Before you start: catalog evolution is mostly Python-API work, not MCP-tool work.** The MCP surface has `create_table` and `add_column` (additive operations) but not `drop_table`, `drop_column`, or FK mutation. Renames and drops happen through `deriva-py`'s model API (`Schema.alter`, `Table.alter`, `Column.alter`, `Column.drop`, `ForeignKey.drop`, etc.). Plan to write a committed Python migration script — interactive MCP calls aren't the right surface for migrations. If you have the `deriva-ml` plugin loaded, follow `/deriva-ml:generate-scripts` for the committed-script-with-provenance discipline.

## The four-step shape

Every catalog evolution follows the same arc regardless of which specific change you're making:

1. **Plan the cutover state.** Name where the catalog is, where it will be after, and the operations to get there in order. Identify what survives the migration unchanged and what changes shape.
2. **Take a snapshot before mutating.** The pre-migration catalog state remains queryable through its snaptime forever; this is your rollback safety net. Capture the snaptime *before* running the migration script. See `/deriva:load-data` "Snapshot before any bulk mutation" for the mechanics.
3. **Run the migration as a tracked operation.** A committed Python script via `/deriva-ml:generate-scripts` (if you have the `deriva-ml` plugin loaded — committed script + execution context manager gives you full git-hash provenance) or a documented standalone script otherwise. The script does the structural mutations + the row-data backfill + the validation queries, all in one place so the migration itself has provenance.
4. **Validate, then update downstream consumers.** Confirm the migration landed correctly (validation queries for each shape, below). Then bump versions on downstream Datasets affected by the change so consumers see the drift; update any scripts, configs, or notebooks that reference moved/renamed columns. Use `grep -r '\bOldName\b'` across your codebase as a starting point for finding hardcoded references.

## Pick a migration shape

Almost every catalog evolution is one of four shapes. Each has a specific FK-safe operation order, a backfill pattern, and a validation query — the full recipes (with worked Python migration script for each, plus the four validation-query patterns) live in [`references/migration-shapes.md`](references/migration-shapes.md). Pick the row whose situation matches yours, then jump to that shape in the reference.

| Shape | When to use | One-line pattern |
|-------|-------------|------------------|
| **A: Split a table into two** (normalization) | A column or pair of columns on one table really describes a separate entity, and you want to FK to it instead of inlining the values. E.g. `Image.Subject_Name`, `Image.Subject_DOB` → pull out a `Subject` table with `Image -> Subject` FK. | Create new table → backfill from `DISTINCT` of source columns → add NULLable FK column on source → backfill FK by joining on natural key → constrain FK → drop old columns. |
| **B: Move a foreign key to a new target** | The relationship between two tables now goes through an intermediate table. E.g. `Asset -> Subject` becomes `Asset -> Specimen -> Subject`. | Add new FK column NULLable → backfill via a join through the old FK → create FK constraint → validate → drop old FK then old column → set new column NOT NULL. |
| **C: Merge tables** (consolidation) | Two (or more) tables that represent the same kind of row need to become one, distinguished by a new vocabulary column. E.g. `Inpatient_Visit` + `Outpatient_Visit` → `Visit` with `Visit_Type` FK. | Create vocabulary → create merged table → copy rows tagging each with its type → migrate downstream FK references via a `old_rid -> new_rid` map → validate row counts → drop source tables. |
| **D: Change a column's type** | The column was created with the wrong type and needs a real type change (which ERMrest doesn't support in place). E.g. `Quality_Score` was `text` holding `"0.85"`, needs to be `float8`. | Add `Quality_Score_v2` with the new type → backfill with coercion → validate → drop old column → rename `_v2` to take over the old name. |

If your change doesn't fit any of these, you probably have a composition of two of them (e.g. a column-type change plus an FK retarget). Run them as separate phases in the same migration script, with validation between phases.

> **All four shapes need validation before any drop.** The reference file has four canonical validation queries — "every row has a value for the new FK/column", "no dangling FK targets", "row counts match before and after", "annotations and display rules updated" — that cover the failure modes for the shapes above. **Don't skip these.** The old column / FK / table is your safety net until the new structure is confirmed correct; once you drop it, the only way back is restoring from the pre-migration snaptime, which is more work than running a query.

## Snaptime as a rollback safety net

Every catalog mutation is timestamped server-side. Capture the snaptime *before* your migration runs, and you have a permanent address for the pre-migration state. If the migration goes wrong, you can:

- **Read pre-migration data** via `query_attribute(path=..., catalog_id="1@<snaptime>")` to recover values that the migration corrupted.
- **Diagnose what changed** by running the same query against both `1` and `1@<snaptime>` and diffing.
- **Restore specific rows** by reading them from the snapshot and `insert_entities` / `update_entities` to the live catalog.

What snaptime is **not**: an in-place "undo button." It's a read-only address. Restoring a corrupted catalog means writing the old data forward through ordinary inserts/updates, not "switching back to the snapshot." For more on the mechanism see `/deriva:deriva-context` "Catalog snapshots and provenance." For how to capture a snaptime around a bulk mutation see `/deriva:load-data` "Snapshot before any bulk mutation."

The snaptime-as-safety-net pattern is most valuable for migrations that touch large numbers of rows — a migration script that corrupts 10,000 rows is a real loss; the snaptime makes it recoverable. For small migrations (a few rows changed), the safety net is overkill but cheap.

## Downstream consumer updates

After a migration lands, things that referenced the old structure need to know:

- **Hydra-zen configs** referencing renamed/moved columns by name. `grep -r` for the old name across your codebase.
- **Scripts and notebooks** that hardcoded the old column or table names.
- **Chaise display annotations** referencing dropped or renamed columns. See the "Annotations and display rules updated" validation query in [`references/migration-shapes.md`](references/migration-shapes.md) for how to find them.
- **Downstream datasets** whose members are unchanged but whose schema-context changed. This is a soft drift that the auto-versioning detection doesn't catch — the dataset's member RIDs are the same, but the data shape they expose is different. If you're in a deriva-ml project and your migration changed a column that's part of a dataset's denormalized view, that dataset's consumers will see different output for the same member RID. Bump the dataset's version manually to record the drift.
- **External citations** referencing the catalog by raw URL with the old structure. URLs that included a snaptime (e.g., a published paper citing `https://host/id/1@<snaptime>/<rid>`) keep working forever because the snaptime addresses the catalog as it was; URLs without a snaptime point at the live catalog and now show the new structure.

## Anti-patterns

- **Mutating the live catalog without a snapshot first.** Take the snaptime before the migration runs — the cost is one MCP call, the benefit is a permanent rollback address.
- **Running the migration interactively via MCP tool calls.** A committed Python script means the migration itself has provenance and is reproducible; interactive migrations are unrepeatable and unauditable. If you have the `deriva-ml` plugin loaded, the `/deriva-ml:generate-scripts` discipline (script + execution context manager) is the natural fit.
- **Dropping anything before validation passes.** The old column / FK / table is your safety net until the new structure is confirmed correct. Drops are irreversible without restoring from a snapshot.
- **Skipping the downstream update.** A migration that succeeds in the catalog but leaves dangling references in scripts and configs is half-done. Use `grep -r` aggressively.
- **Attempting in-place rename of a column that's an FK target.** `Column.alter(name=...)` doesn't propagate to FK constraints pointing at the renamed column. Use the add-backfill-drop pattern (Shape D applied to a renamed column) when the column is referenced by FKs from other tables.

## When to NOT use this skill

- **Initial schema design** — use `/deriva:create-table` and `/deriva:entity-naming`. This skill is for *existing* catalogs being restructured.
- **Pure renames within the first day of an entity's existence** — see `/deriva:entity-naming` `references/naming-conventions.md` §"Renaming: what breaks and the migration procedure." That section has the 7-step procedure; this skill doesn't duplicate it.
- **Adding a new table or column to an existing catalog** without restructuring existing data — that's just `/deriva:create-table`. Migration starts when existing rows need to change shape.
- **Cross-server data movement or cross-catalog data slicing** — that's clone territory, not migration territory. The MCP `clone_catalog` tool clones same-server; cross-server slicing belongs to higher-layer skills.

## Reference resources

- [`references/migration-shapes.md`](references/migration-shapes.md) — the four canonical shapes (Split / Move-FK / Merge / Type-change) as full worked Python migration scripts, plus the four validation-query patterns. Read after picking a row from the "Pick a migration shape" table above.
- `/deriva:entity-naming` — naming conventions, the rename mechanics, what breaks on rename
- `/deriva:create-table` — table / column / FK creation mechanics (the additive operations this skill builds on)
- `/deriva:manage-vocabulary` — creating new vocabulary tables that emerge from a migration
- `/deriva:load-data` — bulk row writes (this skill's backfill steps use the same patterns) and the snapshot-before-bulk-mutation discipline
- `/deriva:query-catalog-data` — `query_attribute` path syntax and `count_table` for validation queries
- `/deriva:customize-display` — updating Chaise annotations after structural changes
- `/deriva:deriva-context` — snaptime mechanics, the "evolve, don't overwrite" pillar
- `/deriva:troubleshoot-deriva-errors` — when migration scripts hit auth, FK-constraint, or vocabulary-term-not-found errors during the backfill steps
- `deriva-py` `Column.alter`, `Column.drop`, `ForeignKey.drop`, `Table.drop`, `Schema.alter` — the Python API for non-additive mutations not exposed via MCP
