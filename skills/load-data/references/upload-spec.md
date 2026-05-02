# Authoring `deriva-upload-cli` Upload Specs

The upload spec (the `asset_mappings` JSON file consumed by `deriva-upload-cli` and the `DerivaUpload` Python class) is a small declarative language for "walk this directory tree, match files against patterns, upload them to Hatrac, and insert/update catalog rows that bridge to them." It's the production path for any non-trivial asset load. The parent `SKILL.md` covers the headline use case; this reference is for authoring real specs against real directory layouts.

The canonical schema for the format lives in `deriva-py` at `deriva/core/schemas/bulk_upload.schema.json` (the `tag:isrd.isi.edu,2019:bulk-upload` annotation schema). When the docs here disagree with the schema, the schema is right; please file an issue.

## Table of contents

- [Top-level structure](#top-level-structure)
- [The asset-mapping object](#the-asset-mapping-object)
- [The variable namespace](#the-variable-namespace)
- [How an asset gets loaded (execution order)](#how-an-asset-gets-loaded-execution-order)
- [Authoring `file_pattern` and `dir_pattern`](#authoring-file_pattern-and-dir_pattern)
- [`metadata_query_templates`: looking up FK targets from the path](#metadata_query_templates-looking-up-fk-targets-from-the-path)
- [`column_value_templates`: computed columns](#column_value_templates-computed-columns)
- [`record_query_template`: idempotency and update semantics](#record_query_template-idempotency-and-update-semantics)
- [`hatrac_templates`: where the file goes](#hatrac_templates-where-the-file-goes)
- [`hatrac_options.versioned_uris` (and the `versioned_urls` synonym)](#hatrac_optionsversioned_uris-and-the-versioned_urls-synonym)
- [Multi-pattern specs (one table, many layouts)](#multi-pattern-specs-one-table-many-layouts)
- [Multi-table specs](#multi-table-specs)
- [Worked patterns](#worked-patterns)
- [Iterative spec development](#iterative-spec-development)
- [Common error messages and what they mean](#common-error-messages-and-what-they-mean)
- [Custom processors (escape hatch)](#custom-processors-escape-hatch)

---

## Top-level structure

```json
{
  "version_compatibility": [[">=1.7.0", "<2.0.0"]],
  "asset_mappings": [
    { ...one asset-mapping object per file pattern... }
  ],
  "mime_overrides": { "text/plain": ["bed"], "image/x-nifti": ["nii", "nii.gz"] },
  "file_ext_mappings": { ... },
  "version_update_url": "https://github.com/informatics-isi-edu/deriva-client"
}
```

| Key | Required | Purpose |
|---|---|---|
| `asset_mappings` | yes | Array of asset-mapping objects (described below). Each one matches a class of files. |
| `version_compatibility` | recommended | Array of `[min, max]` version ranges for `deriva-py`. The CLI refuses to run if its version is outside any listed range. |
| `mime_overrides` | optional | Map of MIME type → list of file extensions, for cases where the system's MIME database doesn't know your file types. |
| `file_ext_mappings` | optional | Map of file extension → properties that get merged into the env when a file with that extension matches. Useful for setting per-extension defaults without per-mapping repetition. |
| `version_update_url` | optional | URL the CLI suggests when it refuses to run due to version mismatch. |

`asset_mappings` is the only required key.

## The asset-mapping object

Each entry under `asset_mappings` describes one *kind* of file the uploader should look for and what to do with it. The full surface:

| Field | Required | Type | Purpose |
|---|---|---|---|
| `asset_type` | optional (default `"file"`) | string `"file"` or `"table"` | `"file"` = upload bytes to Hatrac and insert a catalog row. `"table"` = bulk-load CSV/JSON rows into a catalog table without uploading bytes. |
| `dir_pattern` | one of `dir_pattern` / `file_pattern` is required when `asset_type=file` | regex string | Match a directory name; named groups merge into the env. Use when the directory name carries metadata (e.g., `subject_S001/`). |
| `file_pattern` | one of `dir_pattern` / `file_pattern` is required when `asset_type=file`; required when `asset_type=table` | regex string | Match the full file path; named groups merge into the env. The typical workhorse. |
| `ext_pattern` | optional | regex string | A regex that also matches against the filename to extract `file_ext`. Falls back to `pathlib`'s suffix detection if absent. |
| `checksum_types` | optional (default `["md5", "sha256"]`) | array of `"md5"`/`"sha256"` | Which checksums get computed and made available in the env (`{md5}`, `{sha256}`, `{md5_base64}`, `{sha256_base64}`). |
| `target_table` | required for `asset_type=file` | `[schema, table]` | Where the row goes. |
| `metadata_query_templates` | optional | array of URI templates | Catalog queries (relative ERMrest URIs) whose results merge into the env. Used to look up FK targets, e.g., resolve a `Subject` RID from a domain key in the path. |
| `record_query_template` | required for `asset_type=file` | URI template | Catalog query that decides whether this is an insert or an update. If it returns a row, the existing row is updated; if it returns nothing, a new row is inserted. |
| `column_map` | required for `asset_type=file` | object | Map of catalog column → template that produces the value. The primary insert/update payload. |
| `column_value_templates` | optional | object | Same shape as `column_map`, but evaluated *after* metadata queries — use for columns that depend on other computed values. |
| `default_columns` | optional | array of column names | Columns to leave at server defaults during insert (the system columns `RID`, `RCT`, `RMT`, `RCB`, `RMB` are always implicitly defaulted; this is for additional ones). |
| `hatrac_templates` | required for `asset_type=file` | object with `hatrac_uri` (required) plus optional `content-disposition` and other HTTP headers | Where the file lands in Hatrac and what HTTP headers accompany the upload. |
| `hatrac_options` | optional | object | Per-mapping Hatrac behavior. Currently only `versioned_uris` (boolean, see below). |
| `create_record_before_upload` | optional (default `false`) | boolean | If `true`, insert the catalog row first and then upload the bytes. Useful when the row's RID has to exist before the file is named (rare; normally the order is upload → insert). |

## The variable namespace

Every template (`hatrac_uri`, `column_map` entries, `metadata_query_templates`, `record_query_template`, `column_value_templates`) is a Python `str.format`-style template that substitutes from a single namespace ("the env"). The reserved names — what's always available once a file matches — are documented in `deriva-py` as `UploadMetadataReservedKeyNames`:

| Variable | What it holds |
|---|---|
| `{file_name}` | The filename portion of the matched file path |
| `{file_ext}` | The file extension (with leading dot stripped per the regex) |
| `{file_size}` | File size in bytes |
| `{base_path}` | Path components above the matched file |
| `{base_name}` | Filename with the extension stripped |
| `{md5}`, `{sha256}` | Hex-encoded checksums (if listed in `checksum_types`) |
| `{md5_base64}`, `{sha256_base64}` | Base64 versions of the same |
| `{URI}` | The Hatrac URI of the uploaded object — populated *after* upload, available in `column_map` |
| `{content-disposition}` | The Content-Disposition header used during upload (see hatrac_templates) |
| `{schema}`, `{table}` | The `target_table` parts, also exposed individually |
| `{target_table}` | Convenience: `"schema:table"` form |
| `{_upload_year_}`, `{_upload_month_}`, `{_upload_day_}`, `{_upload_time_}` | Components of the upload time (the time the CLI is running, not the file's mtime) |
| `{_identity_id}`, `{_identity_display_name}`, `{_identity_full_name}`, `{_identity_email}` | Properties of the user account running the upload |

Plus, additively:

- **Named groups from `file_pattern` / `dir_pattern`** become variables in the env. `(?P<subject>[A-Z0-9]+)` makes `{subject}` available.
- **First-row results from `metadata_query_templates`** merge into the env. If the query returns `[{"observation_rid": "1-A2B3"}]`, the `{observation_rid}` variable is now bound. The first row's keys take precedence over earlier env entries with the same name.
- **`column_value_templates`** entries are computed after all of the above and bind their result column name as a variable too. This is how you build columns whose value depends on other computed values.

A name collision between a regex group and a query result resolves to the query result (the query runs after the regex, and the merge overwrites).

## How an asset gets loaded (execution order)

When the uploader processes a single matched file, it does the following in order. Knowing the order helps you place templates in the right field:

1. **Match the path** against `dir_pattern` and/or `file_pattern`. If neither matches, this mapping doesn't apply; try the next one.
2. **Compute file metadata** — `file_name`, `file_ext` (from `ext_pattern` if present, else `pathlib`), `file_size`, checksums per `checksum_types`. Bind into the env.
3. **Bind regex named groups** into the env.
4. **Run `metadata_query_templates` queries** in order. For each, format the template against the current env, GET the URI from the catalog, and merge the first result row into the env. An empty result here aborts the load with `RuntimeError("Metadata query did not return any results: ...")` — this is by design, since the typical use is to look up a required FK target.
5. **Apply `file_ext_mappings`** for the file's extension (top-level; merges per-extension defaults into the env).
6. **Evaluate `column_value_templates`** to compute derived columns from the env. A `KeyError` here is logged and the column is skipped (not a fatal error, but the column won't appear in the insert/update payload).
7. **Compute `hatrac_templates.hatrac_uri`** from the env to produce the Hatrac URI for upload.
8. **Run `record_query_template`** to check whether a row already exists for this asset. The result determines insert vs update semantics (see "record_query_template" section below).
9. **Upload the bytes to Hatrac** at the computed URI.
10. **Set `{URI}` in the env** to the Hatrac URI returned by the upload (versioned or unversioned per `hatrac_options`).
11. **Evaluate `column_map`** to produce the insert/update payload. (`{URI}` is now valid here because of step 10.)
12. **Insert or update the catalog row** per the record-query result.

The sequence makes two things obvious that aren't from the spec alone: `{URI}` is *only* available in `column_map`, not in any earlier template; and `metadata_query_templates` happens before the upload, so it's perfectly safe to use those queries to validate that prerequisites exist (e.g., the FK target Subject row).

## Authoring `file_pattern` and `dir_pattern`

These are Python regexes (PCRE-flavored, case-sensitive by default — use `(?i)` at the start to make the whole pattern case-insensitive). They match against the **full path** the uploader sees while walking the directory tree.

Common conventions in real specs:

```
"file_pattern": "(?i)^.*/(?P<subject>S[0-9]+)/(?P<observation>[0-9]+)_(?P<side>Left|Right)\\.(?P<file_ext>jpg|jpeg|png)$"
```

Patterns to follow:

- **Anchor with `^.*/`** at the start. This makes the pattern relative to whatever portion of the path comes after the directory the user passes to the CLI — you don't have to know in advance whether `/data/` or `/Users/x/data/` is the root.
- **Anchor with `$`** at the end so a partial-extension match doesn't accidentally pick up sibling files.
- **Use named groups for everything you'll need downstream.** A bare capture group `([A-Z0-9]+)` doesn't make `\1` available in the env; only `(?P<name>...)` does.
- **Be specific about the extension** with a named `file_ext` group. The uploader uses this for the env variable; if your pattern doesn't capture it, the fallback `pathlib`-based extension detection has to handle it (and it gets multi-suffix files like `.nii.gz` wrong).
- **Escape literal dots.** `\\.` in JSON (which is `\.` in the regex). A bare `.` matches any character.
- **Use `(?i)` for case-insensitivity** rather than enumerating `[Jj][Pp][Gg]` patterns. Eye-AI's specs all start with `(?i)` for exactly this reason — real-world filenames have inconsistent case.

`dir_pattern` works the same way but matches the *directory name* and is useful when metadata lives in folder names rather than filenames. The two can compose: a `dir_pattern` extracts a `Subject` group from a folder, and a `file_pattern` then extracts the per-file metadata from its name.

## `metadata_query_templates`: looking up FK targets from the path

These templates run as `GET` requests against the catalog after path matching. The typical use case is "the directory or filename has a domain key that I need to convert to a RID before I can FK to it."

```json
"metadata_query_templates": [
  "/attribute/eye-ai:Observation/Observation_ID=AIREADI_{observation}/observation_rid:=RID"
]
```

This query says: find the `Observation` row whose `Observation_ID` equals `AIREADI_{observation}`, and project its `RID` under the alias `observation_rid`. After it runs, `{observation_rid}` is bound in the env and can be referenced by `column_map` (e.g., `"Observation": "{observation_rid}"`).

Two important behaviors:

- **Aliases are how you control variable names.** ERMrest's `column_alias:=column_name` syntax lets you rename query result columns into the env. Without an alias, the column name comes from the catalog (e.g., `RID`, `Name`) — and those names tend to clash with reserved env names. Always alias.
- **An empty result is a fatal error.** The uploader raises `RuntimeError("Metadata query did not return any results: ...")` if the query returns no rows. Use this on purpose — it's how you ensure required FK targets exist before loading. If the result genuinely should be optional, encode that with a `column_value_templates` default fallback or split into two asset mappings.

Multiple queries run in array order; each one's result merges into the env, so later queries can reference variables from earlier ones.

## `column_value_templates`: computed columns

Use this when a column's value depends on *other* env variables that aren't directly available from the regex or the metadata queries:

```json
"column_value_templates": {
  "Display_Label": "{subject} - {observation} - {side}"
}
```

Behavior to know:

- Runs after `metadata_query_templates`, so query results are available.
- A `KeyError` (referenced variable not in env) is logged as a warning and the column is skipped. The load doesn't abort — the row just won't have that column set. Use `default_columns` if you want the server to default it.
- Differs from `column_map` only in *when* it runs: `column_map` runs after the upload (so `{URI}` is available); `column_value_templates` runs before. If you want `{URI}` in the value, put the column in `column_map`.

## `record_query_template`: idempotency and update semantics

This template is what makes the uploader idempotent on re-run. After file metadata is computed but before upload, the uploader runs:

```json
"record_query_template": "/entity/{target_table}/MD5={md5}&Filename={file_name}"
```

If the query returns a row, the uploader **updates** that row instead of inserting a new one (and skips re-upload to Hatrac if the bytes already match). If the query returns nothing, it **inserts** a new row.

The choice of uniqueness key matters:

| Pattern | Use when |
|---|---|
| `MD5={md5}` | "Same bytes = same record." Best for content-addressed loads where the file's identity is its content. Surfaces accidental duplicate uploads. |
| `MD5={md5}&Filename={file_name}` | "Same content with the same filename." Allows the same image to appear in two different observations (different filenames, both stored once in Hatrac). |
| `Image={image_id}&Filename={file_name}` | "Same domain key + filename." Use when the asset has a domain identifier from the upstream system that should be the uniqueness key. |
| Domain-key only (no MD5) | "One asset per domain key, regardless of bytes." Use cautiously — re-upload of a *different* file with the same domain key will silently overwrite the catalog row's URL while leaving the old Hatrac object orphaned. |

If a record exists, the uploader merges its columns into the env (so the existing `RID` is available for FK references in column_map). This also means `{target_table}` and column names from the existing row are bound in the env — handy for "update if exists; insert if new" logic.

## `hatrac_templates`: where the file goes

`hatrac_uri` is the only required key — the URI template that produces the Hatrac path:

```json
"hatrac_templates": {
  "hatrac_uri": "/hatrac/myproject/images/{subject}/{filename}.{file_ext}",
  "content-disposition": "filename*=UTF-8''{file_name}"
}
```

Common patterns for `hatrac_uri`:

- **Domain-keyed paths** (`/hatrac/<namespace>/{subject}/{observation}/{file_name}.{file_ext}`): human-readable, browseable in Hatrac directly. Useful for exploratory use.
- **Checksum-named paths** (`/hatrac/<namespace>/{subject}/{md5}.{file_ext}`): collision-free by construction, content-addressed. Useful when domain keys aren't unique enough on their own or when files might be revised.
- **Mixed** (`/hatrac/.../subject/{subject}/observation/{observation}/image/{image}/{md5}.{file_ext}`, the eye-ai pattern): browseable hierarchy plus content-addressing at the leaf. Handles versions cleanly.

`content-disposition` is optional; if present, it sets the HTTP `Content-Disposition` header on the upload (controls the filename a browser uses on download). The eye-ai pattern is a canonical version: `"filename*=UTF-8''{file_name}"`.

Other keys under `hatrac_templates` get treated as additional HTTP headers for the upload. Most of the time you only need `hatrac_uri` plus optionally `content-disposition`.

## `hatrac_options.versioned_uris` (and the `versioned_urls` synonym)

```json
"hatrac_options": { "versioned_uris": true }
```

Hatrac's content-addressing produces a **versioned URI** for each upload (e.g., `/hatrac/.../foo.jpg:2T-J3M4-K56N`). With `versioned_uris: true` (the default), `{URI}` is bound to the versioned form — every upload of new bytes gets a fresh, citable URI; old `URL` values in the catalog still resolve to their original bytes. With `versioned_uris: false`, `{URI}` is the unversioned base form — `URL` always resolves to whatever was last uploaded at that path.

Production specs almost always want `versioned_uris: true` for the citability and the immutability of citations. Use `false` only for "always-overwriting-with-the-current-version" workflows.

**Spelling note:** the schema documents the field as `versioned_uris` (with an "s" instead of an "l"). The implementation also accepts `versioned_urls` as a synonym (real production specs in the wild use both spellings — see eye-ai). New specs should use `versioned_uris` for forward compatibility.

## Multi-pattern specs (one table, many layouts)

It's common for the same target table to be populated from files that live in different directory layouts (e.g., one upstream system uses `subject_S001/img1.jpg`; another uses `S001-001-Cropped.jpg`). The pattern: one asset-mapping object per layout, all targeting the same `target_table`:

```json
{
  "asset_mappings": [
    { "file_pattern": "...layout A regex...", "target_table": ["myproject", "Image"], ... },
    { "file_pattern": "...layout B regex...", "target_table": ["myproject", "Image"], ... },
    { "file_pattern": "...layout C regex...", "target_table": ["myproject", "Image"], ... }
  ]
}
```

The eye-ai spec has 7+ asset_mappings entries, all targeting the `Image` table — one per directory layout the project encountered over its history. The uploader tries each entry in array order; the first whose pattern matches a given file wins.

## Multi-table specs

Same array, different `target_table` values:

```json
{
  "asset_mappings": [
    { "file_pattern": "...subjects.csv pattern...", "target_table": ["myproject", "Subject"], "asset_type": "table", ... },
    { "file_pattern": "...image pattern...", "target_table": ["myproject", "Image"], "asset_type": "file", ... }
  ]
}
```

Order matters when there are FK dependencies: load parent tables before child tables so the child's `metadata_query_templates` can resolve the FK target. The CLI processes asset mappings in the order they appear in the array.

## Worked patterns

### Per-subject image folders

Layout: `/data/Subject_<RID-or-name>/<observation_id>_<side>.jpg`

```json
{
  "file_pattern": "(?i)^.*/Subject_(?P<subject_name>[A-Z0-9]+)/(?P<observation>[0-9]+)_(?P<side>Left|Right)\\.(?P<file_ext>jpg|jpeg|png)$",
  "target_table": ["myproject", "Image"],
  "checksum_types": ["md5", "sha256"],
  "metadata_query_templates": [
    "/attribute/myproject:Subject/Name={subject_name}/subject_rid:=RID"
  ],
  "hatrac_templates": {
    "hatrac_uri": "/hatrac/myproject/images/{subject_name}/{observation}_{side}.{file_ext}"
  },
  "record_query_template": "/entity/{target_table}/Subject={subject_rid}&Filename={file_name}",
  "column_map": {
    "URL": "{URI}",
    "Filename": "{file_name}",
    "Length": "{file_size}",
    "MD5": "{md5}",
    "Subject": "{subject_rid}",
    "Side": "{side}",
    "Observation_ID": "{observation}"
  }
}
```

### Flat directory with metadata in the filename

Layout: `/data/IMG_<study>_<patient>_<modality>.dcm`

```json
{
  "file_pattern": "(?i)^.*/IMG_(?P<study>[A-Z0-9]+)_(?P<patient>P[0-9]+)_(?P<modality>CT|MR|XR)\\.(?P<file_ext>dcm)$",
  "target_table": ["myproject", "Scan"],
  "metadata_query_templates": [
    "/attribute/myproject:Patient/Code={patient}/patient_rid:=RID",
    "/attribute/myproject:Study/Code={study}/study_rid:=RID"
  ],
  "hatrac_templates": {
    "hatrac_uri": "/hatrac/myproject/scans/{study}/{patient}/{md5}.{file_ext}"
  },
  "record_query_template": "/entity/{target_table}/MD5={md5}",
  "column_map": {
    "URL": "{URI}",
    "Filename": "{file_name}",
    "Length": "{file_size}",
    "MD5": "{md5}",
    "Patient": "{patient_rid}",
    "Study": "{study_rid}",
    "Modality": "{modality}"
  }
}
```

### Computed column from regex captures

```json
"column_value_templates": {
  "Display_Label": "{subject_name} - {observation} ({side})"
}
```

Then reference `{Display_Label}` in `column_map` if you want the same value also stored elsewhere — or just put `Display_Label` directly in `column_map` instead, since `column_value_templates` and `column_map` produce the same kind of output (the difference is timing relative to the upload step).

## Iterative spec development

A spec for a real layout is rarely correct on the first try. The fastest path:

1. **Write the simplest possible mapping** — one regex matching one file, hardcoded everything else.
2. **Validate the regex** against representative paths *outside* the CLI:
   ```python
   import re
   pattern = r"(?i)^.*/Subject_(?P<subject>[A-Z0-9]+)/.*\.(?P<file_ext>jpg)$"
   m = re.match(pattern, "/data/Subject_S001/img1.jpg")
   print(m.groupdict() if m else "NO MATCH")
   ```
   If the regex is wrong here, no amount of CLI debugging will help.
3. **Run the CLI on a directory containing one file**:
   ```bash
   deriva-upload-cli --host data.example.org --catalog 1 --config-file spec.json /tmp/one-file-test
   ```
4. **Add `--debug`** to see the env at each step:
   ```bash
   deriva-upload-cli --debug --host ... --catalog ... --config-file spec.json /tmp/one-file-test
   ```
   The debug output shows the matched regex groups, the metadata-query results, and the final column_map values that get sent to ERMrest.
5. **Expand to a second pattern** once the first works. Add a second asset_mappings entry; verify both still match the right files.
6. **Run the full load** only after every pattern matches at least one file in a small test set.

The transfer-state file (`.deriva-upload-state-<host>-<catalog>.json` written into the upload directory) is also useful for debugging — it records what each file's resolved URI and metadata were, so you can inspect why an upload behaved unexpectedly.

## Common error messages and what they mean

| Error | Cause | Fix |
|---|---|---|
| `Metadata query did not return any results: <URI>` | A `metadata_query_templates` lookup returned an empty result | The FK target the path implies doesn't exist in the catalog. Either load the parent table first, or fix the regex/template if the lookup is computing the wrong URI. |
| `Metadata query template substitution error: KeyError <name>` | A template references a variable that isn't in the env at the time the template runs | Check the execution order — `{URI}` is only valid in `column_map`; metadata-query results are only valid after their query runs; etc. |
| `Column value template substitution error: <name>` | Same root cause as above, but for `column_value_templates`. Logged as warning, not fatal. | Add the missing variable to an earlier step, or move the column to `column_map`. |
| `Hatrac upload failed: 409 Conflict` | The Hatrac URI already exists with different content (when `versioned_uris=false`) | Switch to `versioned_uris=true`, or rewrite the `hatrac_uri` template to incorporate the checksum. |
| `Insert failed: foreign key violation` | A `column_map` value references a RID (or term name) that doesn't exist | The metadata-query result is wrong, or the FK target genuinely doesn't exist. Check the resolved value with `--debug`. |
| `Insert failed: not-null constraint violation on <column>` | A required column isn't in `column_map` (and wasn't defaulted via `default_columns`) | Add the column to `column_map` or to `default_columns`. |
| Regex matches nothing on the test set | The pattern is wrong — usually anchoring (`^.*/`) or escaping (`\\.` for a literal dot in JSON) | Validate against representative paths in Python before running the CLI. |
| `version_compatibility` mismatch | The installed `deriva-py` version is outside any range listed | Update the spec's `version_compatibility` if the new version is actually compatible, or upgrade/downgrade `deriva-py`. |

## Custom processors (escape hatch)

When the spec format doesn't fit the workflow — typically because the load needs custom file processing (extract EXIF metadata, decompress and re-checksum, format conversion, validation against external schemas, custom retry logic), drop down to the `DerivaUpload` Python class:

```python
from deriva.core import get_credential
from deriva.transfer.upload.deriva_upload import GenericUploader

uploader = GenericUploader(
    config=upload_spec_dict,         # same shape as the JSON spec
    credentials=get_credential("data.example.org"),
)
uploader.scanDirectory("/path/to/data")
results = uploader.uploadFiles()
```

You can subclass `GenericUploader` to override:

- `validateFile()` — pre-upload validation, can raise to skip files
- `getCatalogTable()` / `getFileHatracMetadata()` — alter how the upload metadata gets computed
- `_queryFileMetadata()` — replace or augment metadata-query behavior

The custom-processor path is rarely necessary; most projects can express their loads as a multi-mapping spec. Reach for it when you've genuinely hit the spec format's expressive limits.
