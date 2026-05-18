---
name: audit-catalog-health
description: "ALWAYS use this skill when reviewing a Deriva catalog for stewardship issues — missing descriptions on tables / columns / vocabulary terms, naming-convention violations, dangling foreign-key references, and (when the DerivaML schema is present) datasets without Dataset_Type, workflows missing URL or Checksum, executions stuck in Running. Covers the runnable audit script (`scripts/audit_catalog_health.py`), how to interpret each check's findings, and where to fix each kind of issue. Read-only — never mutates the catalog, safe to run against production. Triggers on: 'audit the catalog', 'catalog health', 'data quality check', 'find issues with this catalog', 'review descriptions', 'check naming', 'find dangling FKs', 'broken foreign keys', 'orphan records', 'catalog handoff', 'inheriting a project', 'review before handoff', 'quarterly review', 'what needs to be fixed', 'check vocabulary completeness', 'stewardship audit'."
user-invocable: true
disable-model-invocation: true
---

# Auditing a Deriva Catalog's Health

A read-only walker that surfaces stewardship issues in a Deriva catalog — the things a data manager would want to fix on a quarterly review or before handing the project to a new team. Runs in a few seconds to a few minutes depending on catalog size; never mutates anything.

For *modeling* an entity correctly the first time, see `/deriva:semantic-awareness` (find-before-you-create) and `/deriva:generate-descriptions` (draft descriptions for new entities). This skill is for catching what's *already* in the catalog and shouldn't be — the post-hoc complement to the pre-creation disciplines.

## When to run

- **Quarterly review** — schedule the audit on the calendar so issues don't accumulate silently.
- **Before a project handoff** — present the report to the new owner alongside the catalog; they shouldn't be discovering missing descriptions for themselves.
- **After a bulk load** — `/deriva:load-data` doesn't enforce description completeness; a post-load audit catches what slipped through.
- **After a schema migration** — `/deriva:evolve-schema` can leave dangling FK references if a rename or table drop missed downstream consumers; an audit confirms the migration landed cleanly.
- **Spot-check on an unfamiliar catalog** — when investigating a catalog you didn't build, the audit gives a quick "is this thing well-tended or held together with tape?" read.

## How to run

```bash
# Defaults: write Markdown to stdout, scan 50 foreign keys for dangling refs
uv run python scripts/audit_catalog_health.py \
    --host data.example.org \
    --catalog 1

# Write to a file (timestamped names are good for diffing across audits)
uv run python scripts/audit_catalog_health.py \
    --host data.example.org --catalog 1 \
    --output catalog-health-$(date -u +%Y-%m-%d).md

# Increase the FK scan depth for a thorough run (slower)
uv run python scripts/audit_catalog_health.py \
    --host data.example.org --catalog 1 \
    --max-fk-checks 200 \
    --output catalog-health-thorough.md
```

The script is **read-only**. It captures the catalog snaptime at the start of the run and pins all reads to that snaptime, so the report represents a consistent point-in-time view even if other clients are mutating the catalog mid-audit.

## What each check catches

Each check produces one of four statuses:

| Status | Meaning | Steward action |
|---|---|---|
| **PASS** | No issues found. | None. |
| **WARN** | Issues found but they're cosmetic / non-blocking. | Address opportunistically. |
| **FAIL** | Issues found that affect user-facing behavior, reproducibility, or data integrity. | Address before next major release / handoff. |
| **SKIP** | Check couldn't run (catalog state didn't support it, or a dependency was missing). | Investigate if unexpected. |

### Generic catalog checks (always run)

**1. Tables missing descriptions — FAIL on hit.**
Tables with no `comment` value. Descriptions appear in Chaise tooltips and in any documentation tooling; missing descriptions degrade discoverability and signal "this table was created in a hurry and never revisited." Fix via `/deriva:generate-descriptions` + `update_table_comment`.

**2. Columns missing descriptions — WARN on hit.**
Columns with no `comment` value, after excluding system columns (`RID`, `RCT`, `RMT`, `RCB`, `RMB`) and asset-table standard columns (`URL`, `Filename`, `Length`, `MD5`, `Content_Type`). Reported as WARN because per-column descriptions are nice-to-have rather than load-bearing. Fix via `/deriva:generate-descriptions` + `update_column_comment`, prioritizing columns that appear in Chaise's `visible-columns` (the ones users actually see).

**3. Vocabulary terms missing descriptions — FAIL on hit.**
Terms whose `Description` column is empty. Term descriptions surface in Chaise dropdowns and are the user-facing definition of what each term means — an empty description is functionally a broken UI. The check detects vocabulary-shaped tables heuristically (tables with `Name` + `Description` + `ID` columns); if your catalog uses a non-standard vocabulary shape, those tables are silently skipped. Fix via `/deriva:manage-vocabulary`'s `add_term` (with a description) for new terms or `update_term` for backfilling existing ones.

**4. Naming convention compliance — WARN on hit.**
Tables and user-facing columns that violate the PascalCase + underscore convention (`Subject`, `Subject_Visit`, `Image_Classification`). System columns and `public` / `pg_*` schemas are excluded. Reported as WARN because renaming is genuinely costly (Chaise URLs, downstream consumers, annotations all break). See `/deriva:entity-naming` for the convention rationale and `/deriva:evolve-schema` for the 7-step rename procedure.

**5. Dangling foreign-key references — FAIL on hit.**
For each foreign key (up to `--max-fk-checks`, default 50), the check counts source rows whose non-null FK value doesn't match any row in the target table. A non-zero count means data-integrity damage — either the target was deleted (pillar 5 violation; see `/deriva:load-data` "Delete (rare and discouraged)") or the FK was loaded against the wrong target. Each row in the report points at a real issue that needs investigation before mass-fixing — the right remedy depends on whether the target should be re-created or the source rows reassigned.

> **Multi-column FKs are skipped** in the dangling-FK check (the query expression is more involved). They're rare in practice — most FKs are single-column references to a parent table's `RID`. If your catalog uses composite FKs at scale, the dangling check will silently under-report.

### DerivaML-specific checks (run when the deriva-ml schema is present)

The script auto-detects the deriva-ml schema by attempting to construct a `DerivaML` instance. If the schema isn't present or deriva-ml isn't installed, these checks are skipped and the report header shows `DerivaML detected: no`.

**6. Datasets without Dataset_Type — FAIL on hit.**
A dataset with no `Dataset_Type` term assigned can't be filtered by purpose (Training / Testing / Validation / Inference) and breaks `restructure_assets` defaults that read the type. Fix via `/deriva-ml:dataset-lifecycle` Phase 1 — assign at least one type per dataset.

**7. Workflows missing URL or Checksum — FAIL on hit.**
A workflow's URL + Checksum together pin the code that ran. Either missing means the workflow can't be traced back to source — an execution that references it has provenance (who, when, what) but no code link (how). New executions created via `deriva_ml_create_execution` populate both automatically; offenders are typically historical workflows from before the discipline was enforced. Backfilling is mostly hygiene; the more useful action is to make sure no *new* workflows enter this state.

**8. Executions stuck in Running — WARN on hit.**
Executions in `Running` status whose `RMT` is older than 7 days. These block their workflow's lock and clutter recent-activity views. Each row needs a salvage decision (commit the partial outputs, or abort) — see `/deriva-ml:troubleshoot-execution`'s salvage workflow.

## Interpreting the report

The report opens with a metadata header (host, catalog, snaptime, timestamp, deriva-ml flag) and a summary table that lets you scan status without scrolling. Then one section per check, each with:

- The status (PASS / WARN / FAIL / SKIP) in the heading
- A one-sentence summary
- A table of offender rows (capped at 100; the rest are summarized as `+ N more rows`)
- A "How to fix" pointer to the right skill / tool

**Triage order on a non-clean report:**

1. **All FAILs first.** These are real integrity / reproducibility issues.
2. **Dangling FKs before description gaps.** A broken FK reference is a data correctness issue; a missing description is a discoverability issue. Bigger blast radius gets earlier attention.
3. **Vocabulary terms before column descriptions.** Vocab terms are user-facing (Chaise dropdowns); columns are sometimes hidden behind annotations.
4. **Naming-convention WARNs only when you're already touching the table.** A standalone rename for convention's sake usually isn't worth it — but if you're already editing the table for another reason, that's a good moment to fix the name too.
5. **Diff successive audits** to catch new regressions early. Naming the report file with the date (e.g., `catalog-health-2026-05-17.md`) makes this trivial.

## Defaults and what they protect against

- **`--max-fk-checks 50`** — scans 50 FKs by default. Most catalogs have well under 50; large schemas may have many more. The cap exists so a quarterly audit on a big catalog doesn't take an hour for the dangling-FK check alone. Raise it for a thorough run after profiling.
- **Snaptime pinning** — every read uses the snaptime captured at script start. Concurrent mutations don't bias the audit; conversely, very recent fixes won't show in this run (they'll be reflected in the next).
- **System schema exclusion** — `public`, `_acl_admin`, and any `pg_*` / `ermrest*` / `information_schema*` schemas are skipped. The audit is about *your* schema, not Postgres's.
- **System column exclusion** — `RID`, `RCT`, `RMT`, `RCB`, `RMB` are excluded from description / naming checks because they're server-managed and have universal meaning.

## What this skill does *not* cover

- **ACL review** — who can read / write what. Auditing ACLs is a different skill (deferred); use `/deriva:troubleshoot-deriva-errors` for ad-hoc permission diagnosis.
- **Orphan Hatrac objects** — files in the object store with no corresponding asset-table row. Detecting these requires a recursive Hatrac walk, which is slow and ACL-sensitive; deferred to a future check.
- **Feature column-type drift** — when a DerivaML feature's declared columns don't match the actual catalog columns. Feasible but the comparison surface is fiddly; deferred.
- **Catalog snapshot retention / size** — operational concerns better handled by ops dashboards than a per-catalog walker.
- **Pre-creation duplicate prevention** — that's `/deriva:semantic-awareness`'s job, run before creating each new entity.

## Reference Tools

- `scripts/audit_catalog_health.py` — the audit runner. Read-only; takes `--host`, `--catalog`, optional `--output`, `--max-fk-checks`.

## Related Skills

- **`/deriva:generate-descriptions`** *(auto-loaded)* — Drafting descriptions for offender tables / columns / vocab terms surfaced by checks 1–3.
- **`/deriva:semantic-awareness`** *(auto-loaded)* — The pre-creation discipline whose post-hoc complement this skill is.
- **`/deriva:manage-vocabulary`** — Fixing vocabulary-term descriptions (check 3); creating well-formed vocabularies that don't trip the audit in the first place.
- **`/deriva:entity-naming`** — The naming convention checked by check 4; the cost framing for whether to rename existing offenders.
- **`/deriva:evolve-schema`** — The 7-step rename procedure when you decide to fix a check-4 offender; also relevant when an audit follows a recent schema migration to confirm it landed cleanly.
- **`/deriva:load-data`** — Pillar 5 (evolve, don't overwrite) is what makes dangling-FK offenders typically the result of well-intentioned but mistaken deletes.
- **`/deriva:troubleshoot-deriva-errors`** — Diagnosing auth / connection failures if the audit can't even connect to the catalog.

> **If `deriva-ml` is loaded**, the ML-specific check failures route into the ML skills: `/deriva-ml:dataset-lifecycle` for Dataset_Type assignment (check 6), `/deriva-ml:execution-lifecycle` for the workflow-creation discipline that prevents check-7 issues, and `/deriva-ml:troubleshoot-execution`'s salvage workflow for check-8 cleanups.
