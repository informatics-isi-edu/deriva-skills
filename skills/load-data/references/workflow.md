# Row-Load Script Templates

Worked patterns for the row-load paths in `/deriva:load-data` (single-row insert, batch insert, update, upsert). Use this reference when you need a starting template for a load script — pandas CSV, raw JSON, dataframe ingestion, or an upsert workflow.

The parent `SKILL.md` covers when to use each path; this file covers what the actual script looks like. For asset-table / Hatrac / `deriva-upload-cli` patterns, see `upload-spec.md` instead — those have a different shape and live in their own reference.

## Conventions used in these templates

- All examples assume the table already exists (created via `/deriva:create-table`) and any vocabulary FK targets are populated (via `/deriva:manage-vocabulary`).
- All examples use the MCP tool surface (`insert_entities`, `update_entities`, `delete_entities`, `query_attribute`) — for the equivalent Python API calls via `deriva-py`'s `pathBuilder`, see deriva-py's own docs; the shape of the records is the same.
- Substitute your own `hostname`, `catalog_id`, `schema`, and `table` values throughout — the MCP server is stateless, every call needs them.
- Examples elide error handling for clarity. Real load scripts should wrap each MCP call in try/except and log failures with enough context (which row, which file, which batch) to retry intelligently.

## CSV with pandas

The most common shape: a CSV file on disk, one row per record, column names that map to (or can be transformed into) catalog column names.

```python
import pandas as pd

# 1. Read the file
df = pd.read_csv("/path/to/subjects.csv")

# 2. (Optional) Transform column names / types to match the catalog
df = df.rename(columns={"subject_id": "Name", "age_yrs": "Age"})
df["Age"] = df["Age"].astype(int)  # ensure int, not float64

# 3. (Optional) Filter rows that are missing required values
df = df.dropna(subset=["Name"])

# 4. Convert to the records shape and insert in batches
BATCH_SIZE = 1000
records = df.to_dict(orient="records")

for i in range(0, len(records), BATCH_SIZE):
    batch = records[i : i + BATCH_SIZE]
    result = insert_entities(
        hostname="data.example.org",
        catalog_id="1",
        schema="myproject",
        table="Subject",
        records=batch,
    )
    print(f"Inserted batch {i // BATCH_SIZE + 1}: {len(result)} rows")
```

**Things this pattern gets right and what to watch for:**

- **`to_dict(orient="records")`** is the canonical pandas → list-of-dicts conversion. It produces exactly the shape `insert_entities` wants.
- **Column-name renaming early** is preferable to renaming inside the dict comprehension — easier to debug, easier to dry-run.
- **Type coercion matters.** Pandas often reads numeric columns as `float64` even when they're really integers. Catalog columns with `int8` / `int4` will reject the float; coerce explicitly.
- **NaN values** in pandas don't translate to JSON `null` automatically with all serializers. If you see "invalid value" errors, replace NaN with `None` before sending: `df = df.where(pd.notna(df), None)`.
- **Batch sizing** of 1000 is a reasonable default. Smaller batches give better partial-failure feedback; larger batches reduce HTTP round-trip overhead. Stay under ~10 MB per call (so payload-heavy rows like long descriptions need smaller batches).

## JSON file (one document per record)

When the source is a JSON file containing a list of records — common for downstream-of-an-API loads or when previous tooling exported as JSON.

```python
import json

with open("/path/to/observations.json") as f:
    records = json.load(f)
# records is now a list of dicts

# (Optional) Transform / validate before insert
for r in records:
    # Drop any keys the catalog doesn't have a column for
    r.pop("source_system_internal_id", None)
    # Coerce types if the JSON has loose typing
    r["Sample_Count"] = int(r["Sample_Count"])

# Insert in batches
BATCH_SIZE = 1000
for i in range(0, len(records), BATCH_SIZE):
    batch = records[i : i + BATCH_SIZE]
    insert_entities(
        hostname="data.example.org",
        catalog_id="1",
        schema="myproject",
        table="Observation",
        records=batch,
    )
```

**Watch for:**

- **JSON's number type doesn't distinguish int from float.** A field that holds `5` in the JSON file might come in as `5` or `5.0`; coerce explicitly to match the catalog's column type.
- **Nested objects** in the JSON (`{"address": {"street": "..."}}`) won't fit relational columns directly. Flatten before insert (`r["Address_Street"] = r["address"]["street"]`) or — if the schema models nested data — split into parent and child inserts with the FK linking them.
- **JSON Lines format (`*.jsonl`)** is one JSON object per line, common for large exports. Read with `[json.loads(line) for line in open(path)]` instead of `json.load(f)`.

## In-memory dataframe (already in pandas)

When the data is already in pandas — typically because you computed it from another source (a query result, a transformation pipeline, a notebook).

```python
# df is your already-loaded DataFrame

records = df.to_dict(orient="records")

# Same batched insert as above
BATCH_SIZE = 1000
for i in range(0, len(records), BATCH_SIZE):
    insert_entities(
        hostname="data.example.org",
        catalog_id="1",
        schema="myproject",
        table="Measurement",
        records=records[i : i + BATCH_SIZE],
    )
```

This is the same as the CSV pattern minus the read-from-file step. Most real load scripts end up looking like this once you abstract the source.

## Upsert (insert-or-update)

There is no native upsert tool. The canonical pattern: query existing rows by the domain key, partition into "new" and "existing," then insert the new ones and update the existing ones in two separate calls.

```python
# Input: a list of records to upsert, each with a domain key (e.g., "Code")
input_records = [
    {"Code": "S001", "Name": "Subject 1", "Age": 42},
    {"Code": "S002", "Name": "Subject 2", "Age": 35},
    {"Code": "S003", "Name": "Subject 3", "Age": 28},
]

# 1. Query the catalog for existing rows with these domain keys
codes = [r["Code"] for r in input_records]
existing = query_attribute(
    hostname="data.example.org",
    catalog_id="1",
    schema="myproject",
    table="Subject",
    attributes=["RID", "Code"],
    filter={"Code": codes},   # IN-list filter
)
# existing is now a list of dicts: [{"RID": "1-A2B3", "Code": "S001"}, ...]

# 2. Build a Code -> RID map
existing_map = {row["Code"]: row["RID"] for row in existing}

# 3. Partition the input
to_insert = [r for r in input_records if r["Code"] not in existing_map]
to_update = [
    {**r, "RID": existing_map[r["Code"]]}  # add the RID for the update
    for r in input_records
    if r["Code"] in existing_map
]

# 4. Apply each side
if to_insert:
    insert_entities(
        hostname="data.example.org", catalog_id="1",
        schema="myproject", table="Subject",
        records=to_insert,
    )
    print(f"Inserted {len(to_insert)} new rows")

if to_update:
    update_entities(
        hostname="data.example.org", catalog_id="1",
        schema="myproject", table="Subject",
        records=to_update,
    )
    print(f"Updated {len(to_update)} existing rows")
```

**The shape that makes this safe:**

- **The domain key (`Code` here) must be unique** in the catalog table — otherwise the partition is ambiguous (which existing row do you update?). If the catalog enforces a uniqueness constraint, the upsert will fail loudly on insert; if not, you can silently create duplicates.
- **The query is a single round-trip** for the existence check, then up to two more for the insert + update. Three round-trips total regardless of input size — much better than per-row queries.
- **The update payload only needs the changed columns plus `RID`.** Including unchanged columns is harmless (the server just writes the same value back) but increases payload size.
- **Partial failure** — if the insert succeeds and the update fails, you have new rows in the catalog and stale data in the existing rows. For workflows where atomicity matters, run the entire load against a snapshot (record the snaptime before starting) so you can inspect the previous state if rollback is needed.

## Idempotent re-run safety

When a load script crashes halfway through (network blip, auth expiry, OOM), the second run should pick up where the first left off, not re-insert everything. The upsert pattern above is the building block: every load script that might be re-run should partition input against existing rows and only insert what's missing.

For loads that don't have a natural domain key (every row is genuinely new), a common pattern is to insert a "Load_Run" row first to track this load attempt, FK every loaded row to it, and use the Load_Run's `RID` as the partition key on re-run.

## Loading FK targets first

When loading data into a catalog with FK relationships — e.g., `Subject` rows that reference `Site` and `Cohort` vocabulary terms — the order matters: load the targets before the references, or the FK constraint will reject the inserts.

The general dependency order:

1. **Vocabularies** (use `/deriva:manage-vocabulary`'s `add_term`, not `insert_entities` directly)
2. **Independent reference tables** (no FKs, or only FKs to vocabularies) — `Site`, `Cohort`, etc.
3. **Tables with FKs to (1) and (2)** — `Subject`, `Study`
4. **Tables with FKs to (3)** — `Sample`, `Observation`
5. **Asset tables** that bridge bulk files to (3) or (4) rows — `Image`, `Document` (typically loaded via `deriva-upload-cli` rather than `insert_entities`; see `upload-spec.md`)

If you load in the wrong order, the failures are usually clear (`foreign key violation: referenced row does not exist`) but they waste time. A `--dry-run` flag on the load script that checks FK targets exist for all input rows before attempting any insert is worth the small upfront cost.

## Dry-run pattern

For loads above ~100 rows, a dry-run mode that prints what *would* be inserted (without actually inserting) catches bad data before it hits the catalog. Add a flag to the script:

```python
def load_subjects(records, dry_run=False):
    if dry_run:
        print(f"Would insert {len(records)} rows")
        for r in records[:5]:
            print(f"  Sample: {r}")
        if len(records) > 5:
            print(f"  ...and {len(records) - 5} more")
        return

    # Real insert
    for i in range(0, len(records), BATCH_SIZE):
        insert_entities(...)
```

The dry-run output should also verify that FK targets exist (query for the unique vocabulary terms / referenced RIDs the load assumes) — that's where most "looks fine on the local file but fails on insert" errors come from.

## Performance notes

Restating from `SKILL.md` for self-contained reference:

- **Batch.** One `insert_entities` of 1000 records is ~50× faster than 1000 calls of one record each.
- **FK targets first.** Load parent tables before child tables.
- **Vocabulary terms first.** Categorical FKs resolve by term name; the term has to exist before any row references it.
- **Stay under ~10 MB per insert call.** Payload-heavy rows hit request-size limits faster than the row count suggests.
- **Re-run safety isn't free.** The query-then-partition pattern adds a round-trip. For one-shot loads that you'll never re-run, skip it; for loads that might be re-run, it's worth the round-trip.
