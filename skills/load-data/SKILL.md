---
name: load-data
description: "ALWAYS use this skill when loading data into a Deriva catalog: inserting single rows or batches, importing from CSV / JSON / dataframes, updating existing rows, uploading bulk objects to Hatrac and bridging them to asset-table rows (via the MCP tool, the deriva-upload-cli, or the DerivaUpload Python class with an upload spec / asset_mappings config), populating vocabularies, or deleting rows. Triggers on: 'insert rows', 'load data', 'import csv', 'import json', 'bulk insert', 'add records', 'populate the table', 'fill in the data', 'upload an asset', 'upload a file', 'hatrac upload', 'bridge file to row', 'asset_mappings', 'upload spec', 'deriva-upload-cli', 'bulk asset load', 'directory upload', 'update rows', 'edit records', 'modify rows', 'patch records', 'upsert', 'delete rows', 'remove records'."
user-invocable: true
disable-model-invocation: true
---

# Loading Data into a Deriva Catalog

This skill covers how to get data *into* a Deriva catalog after the schema exists: row inserts (single and batch), updates, asset uploads to Hatrac, and the few cases where deletion is the right move. The schema-creation step is a prerequisite handled by `/deriva:create-table` and `/deriva:manage-vocabulary`; querying the loaded data is `/deriva:query-catalog-data`.

> **Find before you load.** Before bulk-inserting, check whether the records already exist in the catalog. Re-inserting the "same" rows produces near-duplicates that have to be cleaned up later. Use `/deriva:query-catalog-data` (or `rag_search` for fuzzy matches) to verify.

## The five paths

| Path | When to use | Tool |
|---|---|---|
| **Single-row insert** | Adding one or a handful of rows interactively | `insert_entities` |
| **Batch insert** | Loading a CSV / JSON / dataframe (10s–10000s of rows) | `insert_entities` (passes a list) |
| **Update** | Modifying existing rows by RID | `update_entities` |
| **Asset upload (file + row)** | Adding a file to Hatrac and a corresponding asset-table row | `upload_file` + `insert_entities` |
| **Vocabulary populate** | Adding terms to a controlled vocabulary | `add_term` (per term) — see `/deriva:manage-vocabulary` |

Pick the path *before* writing tool calls. Mixing paths (e.g., one `insert_entities` per row in a 1000-row loop) produces N HTTP round trips instead of one and is the most common cause of "load took an hour" surprises.

## Single-row and batch insert

`insert_entities` takes a `records` list. **Same tool, two scales:**

```python
# Single row
insert_entities(
    hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Subject",
    records=[{"Name": "S001", "Age": 42, "Sex": "Male"}],
)

# Batch (one round-trip)
insert_entities(
    hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Subject",
    records=[
        {"Name": "S001", "Age": 42, "Sex": "Male"},
        {"Name": "S002", "Age": 35, "Sex": "Female"},
        # ... up to thousands of rows in one call
    ],
)
```

The server inserts atomically per call: either all rows succeed or all fail. The response includes the server-minted `RID` for each new row in input order — capture this if downstream calls need to FK to the new rows.

### Loading from a file

Read the file into memory, transform to the records shape, then call `insert_entities` once per table. Common patterns are in `references/workflow.md` for CSV (with pandas) and JSON.

### Batch sizing

For very large loads (tens of thousands of rows), split into batches of 1000–5000 records per call to stay within request-size limits and to give partial-failure feedback. The split is a client concern; the server handles each batch atomically.

### Required vs optional columns

System columns (`RID`, `RCT`, `RMT`, `RCB`, `RMB`) are server-minted — never include them in the input records. FK columns must reference *existing* RIDs (or vocabulary term names that already exist); load FK targets first.

## Update

`update_entities` modifies existing rows by RID. RID is the only legal lookup key for updates — there is no update-by-arbitrary-column path.

```python
update_entities(
    hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Subject",
    records=[
        {"RID": "1-A2B3", "Age": 43},      # only the RID and the changed columns
        {"RID": "1-A2B4", "Sex": "Female"},
    ],
)
```

Each record needs `RID` + only the columns you're changing. Omitted columns retain their existing values; set explicitly to `null` to clear.

The server updates `RMT` (modified timestamp) and `RMB` (modified by) automatically. The previous values remain in the catalog history (pillar 5: evolution, not overwrite) — you can query a snaptime from before the update to see what was there.

### Upsert (insert-or-update)

There is no native upsert tool. The pattern: query for existing rows by domain key, partition the input into "to insert" (no match) and "to update" (matched), then call `insert_entities` and `update_entities` separately. Wrap in a single workflow so partial failure is visible.

## Asset upload (file + row)

Asset tables bridge a catalog row to a bulk file in Hatrac. Loading an asset is fundamentally a two-step operation: upload the bytes, then create (or update) the catalog row that points at them. There are three loading paths with different scaling and ergonomic profiles — pick based on how many files and how repeatable the load needs to be.

### Three asset-loading paths

| Path | When to use | Tooling |
|---|---|---|
| **MCP `upload_file` + `insert_entities`** | One file or a handful, interactive use, ad-hoc | MCP tools (this SKILL.md) |
| **`deriva-upload-cli` with an upload spec** | Anything from dozens of files up to large datasets, repeatable loads, directory-tree imports | `deriva-py` CLI + JSON spec |
| **`DerivaUpload` Python class** | Programmatic loads embedded in your own scripts, custom processors | `deriva.transfer.upload` package |

**The CLI + upload spec is the production path** for any non-trivial asset load. The MCP path is for interactive convenience; the Python class is for cases where the CLI's spec format is too restrictive. All three end up calling the same Hatrac upload primitive and inserting the same shape of catalog row — what differs is how files are discovered, named, and bridged.

### Path 1 — MCP `upload_file` + `insert_entities` (interactive, one-off)

```python
# 1. Upload the file to Hatrac
result = upload_file(
    hostname="data.example.org",
    local_path="/path/to/image.jpg",
    namespace="myproject/images",
)
# result includes: URL, MD5, Length, Filename, Content_Type

# 2. Insert the asset-table row pointing at the uploaded object
insert_entities(
    hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Image",
    records=[{
        "URL": result["URL"],
        "Filename": result["Filename"],
        "Length": result["Length"],
        "MD5": result["MD5"],
        "Content_Type": result["Content_Type"],
        "Subject": "1-A2B3",          # FK to the row this asset belongs to
        "Asset_Type": "Photograph",   # FK to the Asset_Type vocabulary
    }],
)
```

Use this for "I have one image to attach to this Subject" or "let me try the asset-loading flow with a single test file before I commit to a spec." Beyond a handful of files, switch to the CLI path.

### Path 2 — `deriva-upload-cli` with an upload spec (production)

`deriva-upload-cli` is the canonical tool for bulk asset loading. You point it at a directory tree and an upload spec (a JSON file with an `asset_mappings` array); it discovers files, uploads each one to Hatrac, and inserts/updates the corresponding asset-table rows in a single coordinated pass. It's the right tool for ingesting an entire image collection, a sequencing run, a microscopy dataset, etc. It is idempotent on re-run.

```bash
# Install (provides the CLI)
uv pip install deriva

# Run the upload
deriva-upload-cli \
    --host data.example.org \
    --catalog 1 \
    --config-file upload-spec.json \
    /path/to/data/directory
```

The spec is the part that takes thought. Each entry in `asset_mappings` tells the uploader: "files matching *this* path regex get uploaded to *this* Hatrac URI and inserted into *this* catalog table with *these* column values, and we check for duplicates with *this* query." Real-world specs typically have one asset-mapping entry per directory layout the project uses, all targeting the same asset table.

For the full spec format — every field's purpose, the variable namespace, execution order, regex authoring patterns, idempotency / update semantics, multi-pattern and multi-table layouts, worked examples, common errors, and the iterative development workflow — see **`references/upload-spec.md`**. That reference is where to go before authoring a real spec; this skill body covers when to use the CLI path but not how to write the spec at depth.

### Path 3 — `DerivaUpload` Python class (custom processors)

When the upload spec format is too restrictive — typically when you need custom file processing (e.g., extract EXIF metadata, decompress and re-checksum, convert formats), or when the load logic needs to be embedded in a larger Python pipeline — drop down to the `DerivaUpload` Python class:

```python
from deriva.core import DerivaServer, get_credential
from deriva.transfer.upload.deriva_upload import GenericUploader

uploader = GenericUploader(
    config=upload_spec_dict,         # same shape as the JSON spec
    credentials=get_credential("data.example.org"),
)
uploader.scanDirectory("/path/to/data")
results = uploader.uploadFiles()
```

This gives you full control over file iteration, error handling, and retry logic. You can subclass `DerivaUpload` to add processors that run before upload (transformation, validation, metadata extraction).

### Hatrac is content-addressed

Uploading the same bytes twice produces one Hatrac object. The second upload is essentially free — Hatrac recognizes the checksum and short-circuits. This is why **duplicate asset rows in the catalog are bad even when storage isn't a concern**: they reference the same underlying object, but Chaise queries see two records. Use the `record_query_template` in the upload spec (or query before insert in the MCP path) to avoid creating them.

## Vocabulary populate

Adding terms to a vocabulary is a per-term operation through `/deriva:manage-vocabulary`'s `add_term`. Don't `insert_entities` directly into a vocabulary table — `add_term` enforces the canonical Name normalization, validates the description is non-empty, and assigns the RID through the proper machinery.

For bulk vocabulary loads, call `add_term` per term (the operations are cheap individually). If you have hundreds of terms, see `/deriva:manage-vocabulary` for the loop pattern.

## Delete (rare and discouraged)

> **Pillar 5: Evolve, don't overwrite.** Deletion erases history. Before reaching for `delete_entities`, ask whether the right move is to add a "superseded" status column, FK to a "Status" vocabulary, or simply leave the old row in place. Snapshot queries can address the previous state of any row, but only if the row still exists.

If deletion is genuinely the right move:

- **Mistakes from yesterday** (a row inserted with bad data that was never referenced) — `delete_entities` is fine.
- **Test catalogs and dev fixtures** — fine.
- **Production data with downstream references** — almost never. The FK constraints will block the delete; even if they don't (FK with `on_delete: SET NULL`), every Chaise URL and bookmark referencing the row 404s afterward.

```python
delete_entities(
    hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Subject",
    filter={"RID": "1-A2B3"},
)
```

`delete_entities` takes a `filter` (not a list of records) and deletes every matching row. Always preview with `query_attribute(..., filter=...)` before deleting to confirm the filter matches what you expect.

## Idempotency and re-run safety

Loads frequently get re-run (the script crashed halfway, the input was wrong, you're testing). Bake re-run safety into the load script:

- **For inserts**, query by domain key first and partition into "already exists" / "new". Skip the existing rows or upsert them.
- **For asset uploads**, Hatrac's content-addressing makes the upload itself idempotent — the same bytes always produce the same URL. The catalog row insert needs the same partition-and-skip discipline as any insert.
- **For updates**, updates are idempotent by construction (running the same update twice gives the same final state). Safe to re-run.
- **Dry-run first** for any load > 100 rows. Print the records that would be inserted; eyeball them; then run for real.

## Performance notes

- **Batch.** One `insert_entities` of 1000 records is ~50× faster than 1000 calls of one record each.
- **FK targets first.** Load parent tables before child tables so the FKs resolve. If you load a child row whose FK points at a not-yet-existing parent, the insert fails atomically.
- **Vocabulary terms first.** Same logic — categorical FKs resolve by term name; the term has to exist before any row references it.
- **Asset uploads parallelize.** Hatrac handles concurrent uploads well; client-side `asyncio.gather` (or `concurrent.futures`) speeds up bulk file loads substantially.
- **Stay under ~10MB per insert call.** Large per-row payloads (e.g., embedded JSON blobs) hit request-size limits faster than the row count suggests. Split payload-heavy loads into smaller batches.

## Reference Tools

### MCP tools (interactive, ad-hoc loads)

- `insert_entities(hostname, catalog_id, schema, table, records=[...])` — Insert one or many rows. Returns server-minted RIDs in input order.
- `update_entities(hostname, catalog_id, schema, table, records=[...])` — Update by RID. Each record needs `RID` plus only the changed columns.
- `delete_entities(hostname, catalog_id, schema, table, filter={...})` — Delete by filter. Preview first.
- `upload_file(hostname, local_path, namespace)` — Upload a file to Hatrac. Returns `{URL, MD5, Length, Filename, Content_Type}` for use in an asset-table row.
- `query_attribute(hostname, catalog_id, schema, table, filter=...)` — Use to check existence before inserting (idempotency) or to preview before deleting.

### deriva-py uploader (production asset loads)

- `deriva-upload-cli` — Command-line tool that walks a directory tree, matches files against an upload spec, uploads bytes to Hatrac, and inserts/updates the corresponding asset-table rows in one coordinated pass. Idempotent on re-run. Install via `uv pip install deriva` (or `pip install deriva`); the CLI is provided by the `deriva-py` package.
- `deriva.transfer.upload.deriva_upload.GenericUploader` — Python class behind the CLI. Use directly when you need custom processors (metadata extraction, format conversion) or to embed asset loading in a larger pipeline.
- **Upload spec format** (`asset_mappings` JSON) — The file-discovery + table-mapping declarative config that drives both the CLI and the Python class. See **`references/upload-spec.md`** for the full format reference: every field, the variable namespace, execution order, idempotency semantics, worked patterns, common errors, and the iterative development workflow.

For row-load script templates (CSV with pandas, JSON, upsert), read `references/workflow.md`.

## Related Skills

- **`/deriva:create-table`** — Create the table (and its FK structure) before loading data into it. The schema must exist first.
- **`/deriva:manage-vocabulary`** — Populate vocabulary tables (use `add_term`, not `insert_entities` directly). Also: when a row's FK column references a vocabulary, the term must exist before the row is loaded.
- **`/deriva:query-catalog-data`** — Verify FK targets exist before loading children, check for duplicates before bulk insert, preview deletes before running them, and read back the loaded data afterward.
- **`/deriva:troubleshoot-deriva-errors`** — When inserts fail with auth, FK-constraint, or vocabulary-term-not-found errors.
- **`/deriva:semantic-awareness`** — The duplicate-prevention discipline ("find before you create") applies to row loads as well as to schema entities.

The plugin-wide modeling checklist lives in the always-on `deriva-context` skill; pillar 5 (evolve, don't overwrite) is the load-time discipline that motivates the soft-delete preference and the snapshot-before-bulk-load pattern.
