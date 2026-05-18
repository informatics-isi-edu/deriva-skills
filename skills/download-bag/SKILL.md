---
name: download-bag
description: "ALWAYS use this skill when getting data OUT of a Deriva catalog as a BDBag — exporting a slice of rows + their FK-reachable relations + the bulk objects they reference into a portable, self-describing, checksummed archive. Covers what a BDBag is, the two export paths (server-side export service via `deriva-export` / `DerivaExport`, or client-side orchestration via `deriva-download-cli` / `DerivaDownload`), authoring the export spec (the JSON config that defines what to include), the `bdbag` CLI for validating and materializing bags, asset materialization and caching strategy. Standalone — works on any Deriva catalog. Triggers on: 'download a bag', 'export a bag', 'BDBag', 'export catalog data', 'pull data out', 'download dataset' (when the user means the bag-export mechanism, not the DerivaML Dataset entity), 'deriva-download-cli', 'deriva-export', 'export spec', 'snapshot the catalog', 'bag manifest', 'materialize assets', 'self-describing archive', 'portable export', 'reproducible data drop', 'data package', 'how do I get this data offline'."
user-invocable: true
disable-model-invocation: true
---

# Downloading a BDBag from a Deriva Catalog

This skill covers getting catalog data *out* as a **BDBag** (Big Data Bag) — a self-describing, portable, checksummed archive that packages a slice of rows + their FK-reachable relations + the bulk objects they reference, suitable for sharing, archiving, or offline use.

For loading data *into* a catalog, see `/deriva:load-data`. For querying / browsing without exporting, see `/deriva:query-catalog-data`.

> **If you have the `deriva-ml` plugin loaded** and the data lives inside a DerivaML `Dataset` entity (with a version, members, and a release lifecycle), use `/deriva-ml:dataset-lifecycle` (Phase 5) instead — its `dataset.download_dataset_bag(version)` API generates the export spec for you and handles version pinning. This skill is for the **catalog-primitive** path: exporting an arbitrary slice from any Deriva catalog, with or without DerivaML installed.

## What is a BDBag?

A **BDBag** is an extension of the [BagIt](https://datatracker.ietf.org/doc/html/rfc8493) packaging format with two additions that matter for Deriva:

1. **A fetch manifest (`fetch.txt`)** — lets a bag reference remote files (Hatrac assets) without bundling the bytes. The bag can be small (manifest only) or fully self-contained (with assets fetched and embedded), and convert between the two with `bdbag --materialize`.
2. **Metadata files** — a `manifest-{algorithm}.txt` per checksum algorithm (md5, sha256) lists every file and its expected hash; `bag-info.txt` carries human-readable metadata about the bag itself.

The shape on disk after extraction:

```
my-bag/
├── bag-info.txt              # bag metadata (creator, date, ...)
├── bagit.txt                 # BagIt version
├── manifest-md5.txt          # checksums of every file in data/
├── tagmanifest-md5.txt       # checksums of the metadata files themselves
├── fetch.txt                 # (optional) remote files to materialize
└── data/
    ├── records/              # CSV per exported table
    │   ├── MyProject.Subject.csv
    │   └── MyProject.Image.csv
    ├── assets/               # (after materialize) the actual Hatrac files
    │   └── Image/image-001.png
    └── schema.json           # catalog schema as of the export
```

The "self-describing" part is load-bearing. Hand a bag to a colleague six months from now and they can verify integrity (`bdbag --validate`), see what's inside (`manifest-md5.txt`), check the schema it was exported under (`schema.json`), and either use the assets directly (if materialized) or fetch them on demand (`bdbag --resolve-fetch`).

## The two export paths

| Path | When to use | Lives where |
|---|---|---|
| **Server-side export service** (`DerivaExport` / export annotation) | Production exports tied to a catalog's published export profiles; you want the server to do the work; you want the result available by URL | `deriva.transfer.download.DerivaExport`; backed by the catalog's `/deriva/export/bdbag/...` endpoint |
| **Client-side orchestrated** (`deriva-download-cli` / `DerivaDownload`) | Custom one-off exports; you control the spec; you want it run locally; you need custom processors | `deriva.transfer.download.DerivaDownload`; `deriva-download-cli` |

Both paths take the **same export spec format**. What differs is who executes it — the server (export service) or the client (download class). The server path is preferred when an export is part of a published workflow (e.g., "export this view" buttons in Chaise call the server endpoint); the client path is preferred when you're authoring a one-off spec and iterating, or when no server-side export profile fits.

> **There is no MCP tool for bag download.** The MCP server (`deriva-mcp-core`) does not expose a `download_bag` or `export_bag` tool. The skill below uses the deriva-py Python API and the `deriva-download-cli` directly. (Companion `/deriva-ml:dataset-lifecycle` documents a `deriva_ml_bag_info` MCP tool — that's for *previewing* a dataset bag before download, not for triggering the download itself.)

## Path 1 — Client-side: `deriva-download-cli` + export spec

`deriva-download-cli` is the production path for client-driven bag export. You point it at a host, catalog, and an export spec; it executes the spec's queries, fetches assets, assembles a bag, and writes it to a local directory.

```bash
# Install (provides the CLI; same package as deriva-upload-cli)
uv pip install deriva

# Run the export
deriva-download-cli \
    --host data.example.org \
    --catalog 1 \
    --config-file export-spec.json \
    --output-dir ./output \
    --envar DATASET_RID=2-XXXX        # template substitution into the spec
```

What you get: a bag directory under `./output`, ready to validate (`bdbag --validate`) or compress (`bdbag --archiver zip`).

### Python equivalent

```python
from deriva.core import get_credential
from deriva.transfer.download.deriva_download import DerivaDownload
import json

with open("export-spec.json") as f:
    config = json.load(f)

downloader = DerivaDownload(
    server={"host": "data.example.org", "catalog_id": "1", "protocol": "https"},
    output_dir="./output",
    config=config,
    credentials=get_credential("data.example.org"),
    timeout=(10, 1800),                 # (connect, read) in seconds
    envars={"DATASET_RID": "2-XXXX"},   # same template substitution
)
result = downloader.download()
# result is a dict with output paths / URLs
```

Use the Python class when you need to embed export in a larger pipeline, handle errors structurally (see "Exceptions" below), or subclass to add custom query / transform / post processors.

## Path 2 — Server-side: `DerivaExport`

```python
from deriva.transfer.download.deriva_export import DerivaExport

exporter = DerivaExport(
    host="data.example.org",
    config_file="export-spec.json",
    output_dir="./output",
    envars={"DATASET_RID": "2-XXXX"},
    export_type="bdbag",
    defer_download=False,               # True → return URLs, don't download
)
result = exporter.export()
```

This submits the spec to the catalog's `/deriva/export/bdbag/` endpoint. The server runs the export and either streams the bag back (`defer_download=False`) or returns a URL list (`defer_download=True`). The server path requires the host to have an export service running and the calling user to be authorized.

**Use `DerivaExport` when** an export is meant to be a *server-side* operation — bookmarked, shareable, runnable by other clients — rather than a one-off you run locally.

## The export spec

Both paths consume the **same JSON spec**. This is the part that takes thought, and it's the part with the thinnest documentation in the ecosystem.

### Top-level shape

```json
{
  "env": {
    "RID": "{DATASET_RID}",
    "hostname": "data.example.org"
  },
  "bag": {
    "bag_name": "MyProject_{DATASET_RID}",
    "bag_algorithms": ["md5"],
    "bag_archiver": "zip"
  },
  "catalog": {
    "host": "data.example.org",
    "catalog_id": "1",
    "query_processors": [
      {
        "processor": "csv",
        "processor_params": {
          "query_path": "/entity/MyProject:Subject/RID=any({DATASET_RID})",
          "output_path": "records/Subject"
        }
      },
      {
        "processor": "fetch",
        "processor_params": {
          "query_path": "/attribute/MyProject:Image/Subject=any({DATASET_RID})/URL,Filename,MD5,Length",
          "output_path": "assets/Image"
        }
      }
    ]
  }
}
```

The four sections:

- **`env`** — variables for template substitution. CLI `--envar K=V` and Python `envars=` populate these. Reference them inside the spec with `{K}` placeholders.
- **`bag`** — BagIt-level options: name, checksum algorithm(s), whether to archive (zip / tgz / none).
- **`catalog`** — the export work. `query_processors` is a list of operations executed in order.
- **`post_processors`** *(optional)* — things to do after the bag is built (e.g., upload to S3, mint a MINID).

### Query processors

Each processor in `query_processors` describes one thing to fetch:

| Processor | What it does | When to use |
|---|---|---|
| `csv` | Run an ERMrest query, write the rows to a CSV under `data/records/{output_path}.csv` | Tabular data from any table; the bread-and-butter processor |
| `json` | Same, but JSON output | When downstream tools prefer JSON over CSV |
| `fetch` | Run a query that yields asset URLs (must project `URL`, `Filename`, plus optionally `MD5`, `Length`), add each to `fetch.txt` for materialization | Asset tables |
| `download` | Like `fetch` but pull the bytes inline rather than deferring | Small asset sets where you don't want the two-phase materialize step |

The `query_path` uses [ERMrest path-expression syntax](https://docs.derivacloud.org/users-guide/query.html) — the same syntax `query_attribute` uses. Template substitution happens before the query runs.

### Authoring a spec from scratch — the honest gap

The export spec format is **runtime-generated by tooling** (e.g., `deriva-ml`'s `DatasetBagBuilder.generate_dataset_download_spec()` produces specs for dataset exports; Chaise's "Export this view" generates specs from `export` annotations on a table). There is **no published authoring guide** for writing one by hand.

Practical strategies in descending order:

1. **Crib from a generated spec.** If the catalog has an `export` annotation on a table (run `get_table_annotations` and look for `tag:isrd.isi.edu,2016:export`), that annotation *is* an export spec template. Run an export through Chaise's UI once, then inspect the spec it submitted (browser devtools → Network → look at the POST to `/deriva/export/bdbag/`). Crib heavily.
2. **Crib from `deriva-ml` for dataset exports.** If you have `deriva-ml` installed, `DatasetBagBuilder(dataset).generate_dataset_download_spec()` returns the spec it would use; print it, then adapt for non-dataset use.
3. **Build incrementally.** Start with one `csv` processor that grabs your root table. Run the CLI; inspect the bag; add the next processor; repeat. The CLI gives per-processor error messages, so a stepwise build localizes failures.
4. **Use the `env`/template substitution liberally.** Anything that varies per export (a RID, a date cutoff) goes in `env` and is referenced with `{NAME}` in the query paths.

### The annotation path (the easiest authoring shortcut)

If the same export will be run repeatedly from Chaise, **author it as an `export` annotation on the table** rather than as a standalone spec file. The annotation lives on the catalog (versioned, queryable, shared across clients), and Chaise's "Export" button picks it up automatically.

```python
# Pseudo-shape; see /deriva:customize-display for annotation tooling
table.annotations["tag:isrd.isi.edu,2016:export"] = {
    "templates": [{
        "type": "BAG",
        "displayname": "Subject + Images BDBag",
        "outputs": [
            {"source": [...], "destination": {"type": "csv", "name": "Subject"}},
            {"source": [...], "destination": {"type": "fetch", "name": "Image"}}
        ]
    }]
}
```

See [the ISRD export annotation spec](https://docs.derivacloud.org/annotations/export.html) for the full schema. The `templates` structure is the same shape that ends up in the runtime spec — different surface, same content.

## Materialization

A bag can be **manifest-only** (small; `fetch.txt` references remote assets) or **fully materialized** (asset bytes embedded under `data/assets/`).

```bash
# Validate a downloaded bag
bdbag --validate fast my-bag/

# Materialize fetch.txt entries (downloads the assets)
bdbag --resolve-fetch all my-bag/

# Re-validate including checksums of materialized assets
bdbag --validate full my-bag/
```

When to defer materialization:

- **Manifest-only first, materialize selectively** — you only need a few assets out of many, or you want to inspect the manifest before committing the bandwidth.
- **Materialize at download time** — set `materialize=true` in the bag section of the spec, or pass `--materialize` to `deriva-download-cli`, so the assets land alongside the manifest in one pass.
- **Manifest-only forever** — sharing a bag whose recipient already has the assets locally (mounted from S3, e.g.) and doesn't need them re-fetched.

Validation matters before consuming the bag. `--validate fast` confirms structure + bag-info checksums (cheap); `--validate full` rehashes every file in `data/` (expensive on big bags, but catches silent corruption).

## Caching

Bags are content-addressed by checksum. The deriva-py download orchestration uses a three-tier cache:

| Tier | Where | When it's checked |
|---|---|---|
| **1. Local** | `{cache_dir}/bags/{checksum}/` (default: `~/.deriva/cache/`) | Always checked first; same export → cached bag returned without re-running |
| **2. MINID / S3** | A persistent identifier that resolves to a bag URL | Checked if the local tier misses and the spec is configured for MINID lookup |
| **3. Generation** | Run the spec against the live catalog | Fallback; the result is then cached at tier 1 (and optionally minted as a MINID for tier 2) |

The cache key is `{spec_hash[:16]}_{snapshot}` — both the *export plan* and the *catalog snapshot* must match for a cache hit. This is why two exports against the same dataset at the same version produce the same bag (cache hit) but exports against `current` (no pinned snapshot) re-generate every time.

For a one-off export, the cache is a "free" speedup. For reproducible exports — same input → same bytes — pin the catalog snapshot in the spec (or via the dataset version, if going through the `dataset-lifecycle` path).

## Exceptions

`DerivaDownload` raises a small typed hierarchy. Catch the parent for "any download error"; catch a specific subclass to handle one kind specially.

```python
from deriva.transfer.download import (
    DerivaDownloadError,
    DerivaDownloadConfigurationError,
    DerivaDownloadAuthenticationError,
    DerivaDownloadAuthorizationError,
    DerivaDownloadTimeoutError,
    DerivaDownloadBaggingError,
)
```

| Exception | Meaning | Typical fix |
|---|---|---|
| `DerivaDownloadConfigurationError` | The spec is malformed or references a missing envar | Re-read the spec; check `{NAME}` placeholders against `envars` |
| `DerivaDownloadAuthenticationError` | No / expired credentials | `deriva-auth data.example.org` to refresh |
| `DerivaDownloadAuthorizationError` | Authenticated, but not allowed to read some queried table | Check ACLs on the table; see `/deriva:troubleshoot-deriva-errors` |
| `DerivaDownloadTimeoutError` | A query (often a deep FK join) exceeded `timeout` | Increase the read timeout in the second tuple element; or prune the query in the spec |
| `DerivaDownloadBaggingError` | BagIt-level packaging problem (disk full, write permission) | Check disk space and output dir permissions |
| `DerivaDownloadError` | Catch-all parent | Re-raise after logging; this is the umbrella for anything `deriva.transfer.download` knows about |

## Performance and ergonomics

- **Snapshot before exporting** — for reproducible exports, capture the catalog snaptime first (`/deriva:load-data` "Snapshot before any bulk mutation" — same primitive, opposite direction) and pin it in the spec. Otherwise the export drifts with the live catalog.
- **One spec, many runs** — template substitution + `envars` lets the same spec produce different bags (per-subject, per-study, per-date-range). Author the spec once; vary inputs at run time.
- **Validate before sharing** — `bdbag --validate full` once before handing a bag off. Cheap insurance against silent corruption during transfer.
- **`bdbag --archiver zip` for sharing** — a zipped bag is one file (vs. a directory tree). `bdbag --extract` on the receiving side; the round trip preserves checksums.
- **Asset count matters more than asset size** — 10,000 small assets is slower than 100 large ones, because each Hatrac fetch has overhead. Group small assets into tar-style aggregates upstream when possible (an asset-table column convention, not a bag-time concern).

## Reference Tools

### CLI

- `deriva-download-cli --host HOST --catalog ID --config-file SPEC --output-dir DIR [--envar K=V ...]` — Run an export spec locally; write the bag to `DIR`.
- `bdbag <command> <bag-path>` — BagIt-level operations: `--validate fast|full`, `--resolve-fetch all|missing`, `--materialize`, `--archiver zip|tgz`, `--extract`. From the `bdbag` Python package (a deriva-py dependency).

### Python

- `deriva.transfer.download.DerivaDownload(server={...}, output_dir=..., config=..., credentials=..., timeout=..., envars={...}).download()` — Client-side orchestration. Returns a dict with output paths.
- `deriva.transfer.download.DerivaExport(host=..., config_file=..., output_dir=..., envars={...}, export_type="bdbag", defer_download=False).export()` — Server-side submission. Returns paths or URLs.
- `bdbag.bdbag_api` — Programmatic BagIt operations (validate, materialize, archive) for when you need to manipulate a bag in code.

### Catalog annotations

- `tag:isrd.isi.edu,2016:export` — Per-table annotation that defines a reusable export spec; surfaced by Chaise as an "Export" button. See [the ISRD export annotation spec](https://docs.derivacloud.org/annotations/export.html) and `/deriva:customize-display` for how to install / edit it.

## Related Skills

- **`/deriva:load-data`** — The inverse operation. Loading data into a catalog (row inserts, asset uploads) is what produces the rows a bag later exports. The snapshot-before-mutating discipline applies in both directions.
- **`/deriva:query-catalog-data`** — Use to verify what rows a query path matches *before* baking that path into an export spec. The path-expression syntax is the same in both surfaces.
- **`/deriva:customize-display`** — When the export should be a Chaise "Export" button rather than a standalone spec file, the path is through the `tag:isrd.isi.edu,2016:export` annotation.
- **`/deriva:troubleshoot-deriva-errors`** — For auth / permission failures on export queries; for missing-record errors when an envar resolves to a RID that no longer exists.
- **`/deriva:evolve-schema`** — Schema changes invalidate cached bags whose `schema.json` no longer matches the live catalog. The migration runbook covers what to do for downstream consumers (re-export, or pin to a pre-migration snaptime).

> **If `deriva-ml` is loaded** and you're exporting a DerivaML `Dataset`, the right surface is `/deriva-ml:dataset-lifecycle` (Phase 5: Use) — it wraps this skill's mechanics with version-pinning, member-driven spec generation, and a `{rid}@{version}` cache key. Reach for that skill instead when the source is a `Dataset` entity; reach for *this* skill when you're exporting an arbitrary catalog slice that isn't part of a Dataset.
