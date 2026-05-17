---
name: evolve-schema
description: "ALWAYS use this skill when restructuring an existing Deriva catalog's schema — splitting a table into two, moving a foreign key to a new target, merging tables, changing a column's type, dropping columns or tables, or any operation where existing data has to migrate to a new structure. This is the runbook for catalog evolution after the initial schema is in place; for the initial schema creation use /deriva:create-table, for naming conventions and the rename mechanics use /deriva:entity-naming. Triggers on: 'migrate schema', 'evolve schema', 'restructure tables', 'split a table', 'merge tables', 'move a foreign key', 'change column type', 'drop a column', 'backfill column', 'rename a column', 'restructure the catalog', 'schema migration', 'how do I refactor', 'change the table structure', 'pull X out into a separate table', 'old design needs to change'."
disable-model-invocation: true
---

# Evolving a Deriva Catalog's Schema

This is the runbook for **restructuring an existing catalog** — the operations you reach for after the initial design proves wrong, the requirements change, or the data outgrows its original shape. For initial schema creation, use `/deriva:create-table`. For what to call new entities and the cost framing of renames, see `/deriva:entity-naming` — its `references/naming-conventions.md` has the 7-step rename procedure, which this skill won't duplicate.

> **Before you start: catalog evolution is mostly Python-API work, not MCP-tool work.** The MCP surface has `create_table` and `add_column` (additive operations) but not `drop_table`, `drop_column`, or FK mutation. Renames and drops happen through `deriva-py`'s model API (`Schema.alter`, `Table.alter`, `Column.alter`, `Column.drop`, `ForeignKey.drop`, etc.). Plan to write a committed Python migration script per `/deriva-ml:catalog-operations-workflow` discipline — interactive MCP calls aren't the right surface for migrations.

## The four-step shape

Every catalog evolution follows the same arc regardless of which specific change you're making:

1. **Plan the cutover state.** Name where the catalog is, where it will be after, and the operations to get there in order. Identify what survives the migration unchanged and what changes shape.
2. **Take a snapshot before mutating.** The pre-migration catalog state remains queryable through its snaptime forever; this is your rollback safety net. Capture the snaptime *before* running the migration script. See `/deriva:load-data` "Snapshot before any bulk mutation" for the mechanics.
3. **Run the migration as a tracked operation.** A committed Python script via the `/deriva-ml:catalog-operations-workflow` pattern (if you're in a deriva-ml project) or a documented standalone script otherwise. The script does the structural mutations + the row-data backfill + the validation queries, all in one place so the migration itself has provenance.
4. **Validate, then update downstream consumers.** Confirm the migration landed correctly (validation queries for each shape, below). Then bump versions on downstream Datasets affected by the change so consumers see the drift; update any scripts, configs, or notebooks that reference moved/renamed columns. Use `grep -r '\bOldName\b'` across your codebase as a starting point for finding hardcoded references.

## The four canonical migration shapes

Pick the shape that matches your change. Each has a specific FK-safe operation order, a backfill pattern, and a validation query.

### Shape A: Split a table into two (normalization)

*"Image currently has Subject_Name and Subject_DOB columns; pull Subject out into its own table so Image FKs to Subject."*

```python
# In your migration script — runs against a connected ErmrestCatalog instance.
from deriva.core import DerivaServer, get_credential
from deriva.core.ermrest_model import Table, Column, builtin_types, ForeignKey

server = DerivaServer("https", "data.example.org", credentials=get_credential("data.example.org"))
catalog = server.connect_ermrest("1")
model = catalog.getCatalogModel()
schema = model.schemas["myproject"]

# Step 1: Create the new Subject table (additive — uses /deriva:create-table mechanics)
subject_table = schema.create_table(Table.define(
    "Subject",
    column_defs=[
        Column.define("Name", builtin_types.text, nullok=False, comment="Subject's name (was Image.Subject_Name)"),
        Column.define("DOB", builtin_types.date, nullok=True, comment="Date of birth (was Image.Subject_DOB)"),
    ],
    comment="Patient/subject records, normalized out of the Image table 2026-05-17",
))

# Step 2: Backfill Subject from Image using a query (avoid Python-side join when possible)
#         Insert one Subject row per distinct (Subject_Name, Subject_DOB) pair from Image.
pb = catalog.getPathBuilder()
image_path = pb.schemas["myproject"].tables["Image"]
existing = image_path.attributes(image_path.Subject_Name, image_path.Subject_DOB).fetch()
unique_subjects = {(r["Subject_Name"], r["Subject_DOB"]) for r in existing}

subject_path = pb.schemas["myproject"].tables["Subject"]
subject_path.insert([{"Name": name, "DOB": dob} for name, dob in unique_subjects])

# Step 3: Add Subject_RID FK column on Image, nullable for now (so the catalog stays writable while you backfill)
image_table = schema.tables["Image"]
subject_rid_col = image_table.create_column(Column.define(
    "Subject_RID", builtin_types.text, nullok=True,
    comment="FK to Subject; backfilled 2026-05-17 from (Subject_Name, Subject_DOB)",
))

# Step 4: Backfill the FK by joining Image to Subject on the natural key
#         (Subject_Name, Subject_DOB), capturing Subject.RID for each Image row.
subject_lookup = {(s["Name"], s["DOB"]): s["RID"] for s in subject_path.entities().fetch()}
for img in image_path.entities().fetch():
    key = (img["Subject_Name"], img["Subject_DOB"])
    img["Subject_RID"] = subject_lookup[key]
image_path.update(list(image_path.entities().fetch()))

# Step 5: Create the FK constraint (Image.Subject_RID -> Subject.RID)
image_table.create_fkey(ForeignKey.define(
    ["Subject_RID"],
    "myproject", "Subject", ["RID"],
    constraint_names=[["myproject", "Image_Subject_RID_fkey"]],
    comment="Image -> Subject, established by 2026-05-17 normalization migration",
))

# Step 6: Validation queries (see "Validation queries" section below)
# Step 7: After validation passes, set Subject_RID NOT NULL and drop the old columns:
image_table.columns["Subject_RID"].alter(nullok=False)
image_table.columns["Subject_Name"].drop()
image_table.columns["Subject_DOB"].drop()
```

**Why this order:** FKs come last because they require the target table to exist with the values they reference. Setting `Subject_RID` NOT NULL comes after backfill because the column has to be NULLable while the rows are being populated.

### Shape B: Move a foreign key to a new target

*"Asset rows used to FK directly to Subject; new design has them FK to Specimen which FKs to Subject. Existing Asset rows need their Subject reference re-routed through a Specimen row."*

```python
# Pattern: add the new FK column NULLable, backfill from a join through the old FK,
# validate every row has a new value, drop the old FK.

# Step 1: Add Specimen_RID column on Asset (NULLable)
asset_table = schema.tables["Asset"]
asset_table.create_column(Column.define(
    "Specimen_RID", builtin_types.text, nullok=True,
    comment="FK to Specimen; backfilled 2026-05-17 from Asset->Subject->Specimen path",
))

# Step 2: Backfill via the join. For each Asset, find the Specimen that links to
#         the Asset's old Subject_RID.
pb = catalog.getPathBuilder()
# Walk Asset -> Subject -> Specimen via the existing FK chain
asset_to_specimen = {}  # asset_rid -> specimen_rid
for row in (pb.schemas["myproject"].tables["Asset"]
            .link(pb.schemas["myproject"].tables["Subject"])
            .link(pb.schemas["myproject"].tables["Specimen"])
            .attributes(pb.schemas["myproject"].tables["Asset"].RID,
                        pb.schemas["myproject"].tables["Specimen"].RID)
            .fetch()):
    asset_to_specimen[row["Asset_RID"]] = row["Specimen_RID"]

# Update Asset rows with their new Specimen_RID
asset_path = pb.schemas["myproject"].tables["Asset"]
updates = [{"RID": a_rid, "Specimen_RID": s_rid} for a_rid, s_rid in asset_to_specimen.items()]
asset_path.update(updates)

# Step 3: Create the new FK constraint
asset_table.create_fkey(ForeignKey.define(
    ["Specimen_RID"], "myproject", "Specimen", ["RID"],
    constraint_names=[["myproject", "Asset_Specimen_RID_fkey"]],
    comment="Asset -> Specimen, replacing the direct Asset -> Subject FK (2026-05-17)",
))

# Step 4: Validation (see "Validation queries" below). Confirm every Asset row has
#         a non-NULL Specimen_RID before proceeding to step 5.

# Step 5: Drop the old FK constraint, then the old column
old_fk = next(fk for fk in asset_table.foreign_keys
              if [c.name for c in fk.foreign_key_columns] == ["Subject_RID"])
old_fk.drop()
asset_table.columns["Subject_RID"].drop()

# Step 6: Set the new FK column NOT NULL
asset_table.columns["Specimen_RID"].alter(nullok=False)
```

**Why this order:** The new FK column must accept NULLs during backfill (no value yet for newly-added rows during the migration window). The old FK constraint blocks dropping the old column, so the FK has to go first. The NOT NULL switch comes last because it's the final integrity assertion.

### Shape C: Merge tables (consolidation)

*"Inpatient_Visit and Outpatient_Visit need to become one Visit table with a Visit_Type FK to a new vocabulary."*

```python
# Step 1: Create the Visit_Type vocabulary (see /deriva:manage-vocabulary)
#         Add "Inpatient" and "Outpatient" terms.

# Step 2: Create the new Visit table with all columns from both source tables,
#         plus the Visit_Type FK column
visit_table = schema.create_table(Table.define(
    "Visit",
    column_defs=[
        # ... all the common columns ...
        Column.define("Visit_Type", builtin_types.text, nullok=False,
                      comment="Inpatient or Outpatient — FK to Visit_Type vocab"),
    ],
    fkey_defs=[
        ForeignKey.define(["Visit_Type"], "myproject", "Visit_Type", ["Name"],
                          constraint_names=[["myproject", "Visit_Visit_Type_fkey"]]),
    ],
    comment="Unified Visit table consolidating Inpatient_Visit and Outpatient_Visit (2026-05-17)",
))

# Step 3: Copy rows from each source table into Visit, tagging with the right type
pb = catalog.getPathBuilder()
inpatient = pb.schemas["myproject"].tables["Inpatient_Visit"].entities().fetch()
outpatient = pb.schemas["myproject"].tables["Outpatient_Visit"].entities().fetch()

visit_path = pb.schemas["myproject"].tables["Visit"]
visit_path.insert([{**row, "Visit_Type": "Inpatient"} for row in inpatient])
visit_path.insert([{**row, "Visit_Type": "Outpatient"} for row in outpatient])

# Step 4: Migrate downstream FK references that pointed at the old tables.
#         If other tables had FKs to Inpatient_Visit/Outpatient_Visit, those references
#         now need to point at Visit rows. Build a RID-mapping table and update them
#         the same way Shape B does (add new column, backfill, validate, drop old).

# Step 5: Validate row counts: rows(Visit) == rows(Inpatient_Visit) + rows(Outpatient_Visit)
#         and that the Visit_Type distribution matches the source.

# Step 6: After validation passes and all downstream FKs are migrated, drop the source tables
schema.tables["Inpatient_Visit"].drop()
schema.tables["Outpatient_Visit"].drop()
```

**The trickiest part of a merge isn't the rows — it's the FK references.** If anything in the catalog held an FK to `Inpatient_Visit.RID`, those references won't resolve to the same RID in the new `Visit` table (insertion mints new RIDs). Build a `old_rid -> new_rid` lookup during step 3 and use it to backfill every downstream FK in step 4. **If you can't enumerate everything that referenced the old tables, the merge isn't safe** — run `list_foreign_keys` on the source tables before starting to verify the scope.

### Shape D: Change a column's type

*"Quality_Score was originally text holding strings like '0.85'; needs to be float8 for numeric comparison."*

ERMrest doesn't support in-place type changes that lose or coerce data. The pattern is the same as Shape B (add-new, backfill, validate, drop-old) but applied to a column rather than an FK:

```python
# Step 1: Add the new column with the right type, NULLable
image_table = schema.tables["Image"]
image_table.create_column(Column.define(
    "Quality_Score_v2", builtin_types.float8, nullok=True,
    comment="Numeric Quality_Score; backfilled from text column 2026-05-17",
))

# Step 2: Backfill, coercing the string values
pb = catalog.getPathBuilder()
image_path = pb.schemas["myproject"].tables["Image"]
for img in image_path.entities().fetch():
    if img["Quality_Score"] is not None:
        try:
            img["Quality_Score_v2"] = float(img["Quality_Score"])
        except ValueError:
            # Log and decide: skip this row, or fail the migration?
            print(f"Cannot coerce Quality_Score={img['Quality_Score']!r} on RID {img['RID']}")
image_path.update(list(image_path.entities().fetch()))

# Step 3: Validate that every non-NULL old value has a corresponding non-NULL new value
#         (see "Validation queries" below).

# Step 4: Drop the old column. Note: if any annotations, display rules, or downstream
#         queries referenced the old column name, update them first.
image_table.columns["Quality_Score"].drop()

# Step 5: Rename the new column to take over the old name
image_table.columns["Quality_Score_v2"].alter(name="Quality_Score")
```

**Why the temporary v2 name + rename:** ERMrest treats column names as part of the constraint identity. You can't have two columns named `Quality_Score` simultaneously, so the new one starts under a temporary name and gets renamed once the old one is gone.

## Validation queries

Every migration shape needs validation. The queries below use `query_attribute` with ERMrest path syntax (see the `query_guide` MCP prompt or `/deriva:query-catalog-data` for path mechanics). Run each one **before** dropping anything, and confirm the expected result.

### "Every row has a value for the new FK / column"

After a backfill, the new column should be non-NULL for every row that had a value in the source:

```
# After Shape A or B — every Image should now have a Subject_RID
query_attribute(hostname="data.example.org", catalog_id="1",
    path="myproject:Image/Subject_RID::null::",
    attributes=["RID", "Filename"])
# Expected: empty result. If non-empty, your backfill missed those rows.
```

### "No dangling FK targets"

After creating an FK, every value in the FK column must resolve to an existing row in the target table. ERMrest enforces this on FK creation, but if you backfilled before creating the FK, run this:

```
# Find Image.Subject_RID values that don't match any Subject.RID
query_attribute(hostname="data.example.org", catalog_id="1",
    path="myproject:Image",
    attributes=["RID", "Subject_RID"])
# Then in Python: compare Subject_RIDs to the set of actual Subject RIDs.
# Or use a path query that joins and asserts equality if your shape allows.
```

### "Row counts match before and after"

For merge/split shapes, capture row counts before mutating and verify after:

```
# Before
count_table(hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Inpatient_Visit")    # → 1234
count_table(hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Outpatient_Visit")   # → 5678

# After
count_table(hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Visit")              # should be 6912

# Or with filter to verify the split
count_table(hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Visit",
    filters={"Visit_Type": "Inpatient"})            # should be 1234
```

### "Annotations and display rules updated"

If you renamed or dropped columns, Chaise display annotations that referenced the old names will now be stale. Check:

```
get_table_annotations(hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Image")
# Look for the old column name in visible_columns, row_name, or any
# Markdown patterns. Update via the annotation tools — see /deriva:customize-display.
```

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
- **Chaise display annotations** referencing dropped or renamed columns (see the validation query above).
- **Downstream datasets** whose members are unchanged but whose schema-context changed. This is a soft drift that the auto-versioning detection doesn't catch — the dataset's member RIDs are the same, but the data shape they expose is different. If you're in a deriva-ml project and your migration changed a column that's part of a dataset's denormalized view, that dataset's consumers will see different output for the same member RID. Bump the dataset's version manually to record the drift.
- **External citations** referencing the catalog by raw URL with the old structure. URLs that included a snaptime (e.g., a published paper citing `https://host/id/1@<snaptime>/<rid>`) keep working forever because the snaptime addresses the catalog as it was; URLs without a snaptime point at the live catalog and now show the new structure.

## Anti-patterns

- **Mutating the live catalog without a snapshot first.** Take the snaptime before the migration runs — the cost is one MCP call, the benefit is a permanent rollback address.
- **Running the migration interactively via MCP tool calls.** The `/deriva-ml:catalog-operations-workflow` discipline applies: a committed Python script means the migration itself has provenance and is reproducible. Interactive migrations are unrepeatable and unauditable.
- **Dropping anything before validation passes.** The old column / FK / table is your safety net until the new structure is confirmed correct. Drops are irreversible without restoring from a snapshot.
- **Skipping the downstream update.** A migration that succeeds in the catalog but leaves dangling references in scripts and configs is half-done. Use `grep -r` aggressively.
- **Attempting in-place rename of a column that's an FK target.** `Column.alter(name=...)` doesn't propagate to FK constraints pointing at the renamed column. Use the add-backfill-drop pattern (Shape D applied to a renamed column) when the column is referenced by FKs from other tables.

## When to NOT use this skill

- **Initial schema design** — use `/deriva:create-table` and `/deriva:entity-naming`. This skill is for *existing* catalogs being restructured.
- **Pure renames within the first day of an entity's existence** — see `/deriva:entity-naming` `references/naming-conventions.md` §"Renaming: what breaks and the migration procedure." That section has the 7-step procedure; this skill doesn't duplicate it.
- **Adding a new table or column to an existing catalog** without restructuring existing data — that's just `/deriva:create-table`. Migration starts when existing rows need to change shape.
- **Cross-server data movement or cross-catalog data slicing** — that's clone territory, not migration territory. The MCP `clone_catalog` tool clones same-server; cross-server slicing belongs to higher-layer skills.

## Reference resources

- `/deriva:entity-naming` — naming conventions, the rename mechanics, what breaks on rename
- `/deriva:create-table` — table / column / FK creation mechanics (the additive operations this skill builds on)
- `/deriva:manage-vocabulary` — creating new vocabulary tables that emerge from a migration
- `/deriva:load-data` — bulk row writes (this skill's backfill steps use the same patterns) and the snapshot-before-bulk-mutation discipline
- `/deriva:query-catalog-data` — `query_attribute` path syntax and `count_table` for validation queries
- `/deriva:customize-display` — updating Chaise annotations after structural changes
- `/deriva:deriva-context` — snaptime mechanics, the "evolve, don't overwrite" pillar
- `/deriva:troubleshoot-deriva-errors` — when migration scripts hit auth, FK-constraint, or vocabulary-term-not-found errors during the backfill steps
- `deriva-py` `Column.alter`, `Column.drop`, `ForeignKey.drop`, `Table.drop`, `Schema.alter` — the Python API for non-additive mutations not exposed via MCP
