---
name: manage-storage
description: "ALWAYS use this skill when managing DerivaML local storage — checking disk usage, cleaning up cached datasets or execution directories, pre-fetching datasets into cache, diagnosing what's using space, or understanding cache vs working directory. Triggers on: 'disk full', 'clean up cache', 'what's cached', 'storage', 'free space', 'delete old data', 'cache management', 'prefetch dataset', 'warm cache', 'working directory', 'cache directory', '~/.deriva-ml'."
disable-model-invocation: true
---

# Managing DerivaML Local Storage

DerivaML stores downloaded datasets, execution working directories, and cached assets on the local filesystem. This skill covers browsing, cleaning up, pre-fetching, and configuring that storage.

## Prerequisite: Connect to a Catalog

Most storage operations require an active catalog connection to validate RIDs and versions.

```
connect_catalog(hostname="...", catalog_id="...")
```

If already connected (check `deriva://catalog/connections`), skip this step.

## Understanding the Storage Layout

All DerivaML local data lives under a **working directory**, typically `~/.deriva-ml/{hostname}/{catalog_id}/`. Within that:

| Directory | Contents | Grows from |
|-----------|----------|------------|
| `cache/` | Downloaded dataset bags (BDBags), keyed by RID + checksum | Python API `dataset.download_dataset_bag(version)`, Python API `exe.download_dataset_bag()`, `cache_dataset` |
| `cache/assets/` | Individually cached assets (model weights, etc.), keyed by RID + MD5 | `AssetSpec(cache=True)` |
| `execution_{RID}/` | Execution working directories — staged output files, logs | `create_execution` |
| Other dirs | Hydra configs, client exports, temporary files | Various |

### Cache vs Working Directory

These are **different concepts** that users often confuse:

| | Cache directory | Working directory |
|---|---|---|
| **Purpose** | Stores downloaded data for reuse | Base for all DerivaML operations |
| **Location** | `{working_dir}/cache/` | `~/.deriva-ml/{host}/{catalog}/` by default |
| **Configurable?** | Yes — `cache_dir` parameter in DerivaML config | Yes — `working_dir` parameter |
| **Shared across executions?** | Yes — multiple executions reuse the same cached bags | No — each execution gets its own directory |
| **Safe to delete?** | Yes — can be re-downloaded from catalog | Caution — may contain un-uploaded execution outputs |

**When to configure a custom cache directory:**
- Shared compute clusters where `~/.deriva-ml` is on a small home partition
- When you want the cache on fast local SSD instead of network storage
- When multiple users should share a single cache to avoid duplicate downloads

In Python:
```python
ml = DerivaML(hostname, catalog_id, cache_dir="/fast-ssd/deriva-cache")
```

In hydra-zen config:
```python
default_deriva(hostname="...", catalog_id="...", cache_dir="/fast-ssd/deriva-cache")
```

## Phase 1: Assess — What's Using Space

### Browse all storage

```
# Python API or Bash: inspect ~/.deriva-ml/ ()
```

Returns every cached bag, execution directory, and other artifact with size, category, and last-modified date.

**Filter by category:**

```
# Python API or Bash: inspect ~/.deriva-ml/ (filter="cache")       # Only cached dataset bags
# Python API or Bash: inspect ~/.deriva-ml/ (filter="executions")  # Only execution working directories
```

### Check a specific dataset's cache status

```
bag_info(dataset_rid="28CT", version="0.9.0")
```

Returns:
- `cache_status`: one of `not_cached`, `cached_metadata_only`, `cached_materialized`, `cached_incomplete`
- `total_asset_bytes` / `total_asset_size`: how much space the bag uses
- `tables`: per-table row counts and asset sizes
- `cache_path`: where it lives on disk

### Estimate download size before caching

```
estimate_bag_size(dataset_rid="28CT", version="0.9.0")
```

Same as `bag_info` but does not require the bag to be cached — estimates from catalog metadata.

## Phase 2: Clean Up — Free Disk Space

### Preview what would be deleted (dry run)

```
# Python API: ml.clean_storage(rids=["28CT"], confirm=false)
```

Returns a preview of matching entries without deleting anything. A single RID may match multiple entries (e.g., a dataset cached at several versions, or an execution working directory).

### Delete cached data

```
# Python API: ml.clean_storage(rids=["28CT", "3WSE"], confirm=true)
```

**What's safe to delete:**
- Cached dataset bags — can always be re-downloaded from the catalog
- Cached assets — can be re-downloaded
- Completed execution directories — outputs already uploaded to catalog

**What's NOT safe to delete:**
- Execution directories where Python API `exe.# Python API: exe.upload_execution_outputs()` was never called — those outputs are **only** on local disk

### Bulk cleanup workflow

1. Bash: `ls -la ~/.deriva-ml/` — see everything
2. Identify old or large entries
3. Bash: `du -sh ~/.deriva-ml/cache/*` — check sizes
4. Bash: `rm -rf ~/.deriva-ml/cache/...` — delete

## Phase 2b: Find and Resume Incomplete Executions

Execution working directories may contain outputs that were never uploaded — from interrupted runs, crashes, or forgotten Python API `exe.# Python API: exe.upload_execution_outputs()` calls. These are the **only** local data that can't be re-downloaded from the catalog.

### Find incomplete executions

```
# Python API or Bash: inspect ~/.deriva-ml/ (filter="executions")
```

Look for execution directories that:
- Have files in them (non-empty) but the execution status is not `completed`
- Were created recently but never uploaded

### Check execution status in the catalog

For each execution directory found, check its catalog status:

```
get_record(table_name="Execution", rid="<execution_rid>")
```

If status is `running` or `pending` (not `completed`), the outputs may not have been uploaded.

### Resume and upload

```
restore_execution(execution_rid="<execution_rid>")
```

This restores the execution context so you can:
1. Inspect the working directory contents
2. Register any output files with Python API `exe.asset_file_path()`
3. Call `stop_execution()` then `# Python API: exe.upload_execution_outputs()` to save them to the catalog

### After successful upload, clean up

Once outputs are safely in the catalog, the local execution directory can be deleted:

```
# Python API: ml.clean_storage(rids=["<execution_rid>"], confirm=true)
```

## Phase 3: Pre-fetch — Warm the Cache

Download datasets or assets into the local cache **without creating an execution**. Useful before long-running experiments to avoid download delays mid-run.

### Cache a dataset bag

```
cache_dataset(dataset_rid="28CT", version="0.9.0")
```

Downloads the full bag (including materialized assets) into the cache. Subsequent calls to Python API `exe.download_dataset_bag()` with the same RID and version will reuse the cached copy.

### Cache metadata only (no asset files)

```
cache_dataset(dataset_rid="28CT", version="0.9.0", materialize=false)
```

Downloads table data but skips large asset files. Useful for inspecting schema and row counts.

### Cache an individual asset

```
cache_dataset(asset_rid="3WSE")
```

Downloads a single asset (e.g., pre-trained model weights) into the asset cache.

### Verify cache after pre-fetching

```
bag_info(dataset_rid="28CT", version="0.9.0")
```

Confirm `cache_status` is `cached_materialized`.

## Pre-flight Pattern (Before Running Experiments)

The recommended pre-flight sequence:

1. **Validate** — `validate_rids(dataset_rids=[...], asset_rids=[...])` — confirm everything exists
2. **Check cache** — `bag_info(dataset_rid=..., version=...)` — see what's already cached
3. **Pre-fetch** — `cache_dataset(...)` — download anything that's `not_cached`
4. **Verify** — `bag_info(...)` — confirm `cached_materialized`
5. **Run** — `create_execution(...)` → downloads hit cache instantly

## Storage Manager Web App

For a visual dashboard of storage usage, use the Storage Manager app:

```
start_app(app_id="storage-manager")
```

This launches a web UI that shows all cached data with filters, sizes, and bulk delete. Requires the `deriva-ml-apps` repo to be built.

## Reference Resources

- Bash `ls -la ~/.deriva-ml/` — Browse all local storage
- Bash `rm -rf ~/.deriva-ml/...` — Remove cached items by RID
- `bag_info` — Check cache status and size for a specific dataset version
- `cache_dataset` — Pre-fetch a dataset or asset into cache
- `estimate_bag_size` — Estimate download size before caching

## Related Skills

- **`execution-lifecycle`** — Pre-flight checklist includes cache warming
- **`dataset-lifecycle`** — Downloading and working with BDBags
- **`configure-experiment`** — Setting `cache_dir` in hydra-zen configs
- **`work-with-assets`** — Asset caching with `AssetSpec(cache=True)`
