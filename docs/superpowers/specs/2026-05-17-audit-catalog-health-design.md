# `DerivaML.audit()` — design for a catalog health audit API

**Status:** design / not implemented. Records the design work from the closed
PR #11 ("Add audit-catalog-health skill + runnable audit script") so the
eventual implementer in `deriva-ml` has the inventory and rationale.

**Decision:** the audit belongs as an **API method on `DerivaML`**, not as a
standalone CLI script in a Claude Code skill plugin. The skill-plugin
implementation in PR #11 was correct in its check inventory but wrong in
location — once `DerivaML.audit()` exists, the value flows everywhere:
notebooks, scripts, MCP tools (`deriva_ml_audit_catalog_health(...)`), CI
checks. A CLI script is reusable from none of those without copy-paste.

**Where the documenting skill lands:** when the API exists, a
`/deriva-ml:audit-catalog-health` skill in `deriva-ml-skills` will document
how to invoke it (Python API / MCP tool / optional CLI wrapper) and how to
interpret the report. This deriva-skills repo is not the right home — the
audit is dominated by ML-specific checks that depend on the deriva-ml
schema being present.

---

## API shape

```python
class DerivaML:
    def audit(
        self,
        *,
        max_fk_checks: int = 50,
        executions_stuck_threshold_days: int = 7,
    ) -> AuditReport:
        """Run a read-only catalog health audit.

        Returns:
            AuditReport with one CheckResult per check. Renderable as
            Markdown via report.render_markdown() or JSON via
            report.to_dict() for piping into other tools.

        Notes:
            - Snaptime-pinned: captures latest_snaptime() at start so
              all reads represent a consistent point-in-time view.
            - Read-only: never mutates the catalog.
            - DerivaML checks (datasets, workflows, executions) always
              run from this entry point since the receiver implies the
              schema is present. For non-ML catalogs, expose the
              generic checks via a sibling Model.audit() helper on the
              deriva-py catalog model — or punt that case to direct
              use of the catalog primitives. Both are acceptable; we're
              not blocking the ML audit on the upstream change.
        """
```

```python
@dataclass
class CheckResult:
    name: str           # human-readable check name
    status: str         # "PASS" | "WARN" | "FAIL" | "SKIP"
    summary: str        # one-line explanation for the report's top table
    rows: list[dict]    # offender rows (empty when PASS / SKIP)
    fix_pointer: str    # short Markdown sentence pointing at the fix surface


@dataclass
class AuditReport:
    host: str
    catalog_id: str
    snaptime: str
    deriva_ml_detected: bool
    results: list[CheckResult]

    def render_markdown(self) -> str: ...
    def to_dict(self) -> dict: ...
    def has_failures(self) -> bool: ...   # convenient for CI gating
```

---

## Check inventory (v1)

Status-grading principle: **FAIL** is reserved for issues that affect
user-facing behavior, reproducibility, or data integrity. **WARN** is for
cosmetic / opportunistic fixes. **SKIP** when the check can't run (no
vocabularies, no datasets, etc.). The distinction matters for triage —
clear FAILs before next release / handoff; leave WARNs for the next pass.

### Generic catalog checks (always run)

**1. Tables missing descriptions — FAIL on hit.**
Tables with empty / absent `comment`. Descriptions appear in Chaise tooltips
and in any documentation tooling; missing descriptions degrade discoverability
and signal "this table was created in a hurry and never revisited."

Exclusions: system schemas (`public`, `_acl_admin`, `pg_*`, `ermrest*`,
`information_schema*`).

Fix surface: `/deriva:generate-descriptions` + `update_table_comment`.

**2. Columns missing descriptions — WARN on hit.**
Columns with empty / absent `comment` after excluding system columns
(`RID`, `RCT`, `RMT`, `RCB`, `RMB`) and asset-table standard columns
(`URL`, `Filename`, `Length`, `MD5`, `Content_Type`).

Why WARN, not FAIL: per-column descriptions are nice-to-have rather than
load-bearing. Reserve FAIL for things that block user-facing behavior.

Fix surface: `/deriva:generate-descriptions` + `update_column_comment`,
prioritizing columns that appear in Chaise's `visible-columns`.

**3. Vocabulary terms missing descriptions — FAIL on hit.**
Terms whose `Description` column is empty. Term descriptions surface in
Chaise dropdowns and are the user-facing definition of what each term means
— an empty description is functionally a broken UI.

Detection heuristic: a table is a vocabulary if it has the `Name` +
`Description` + `ID` column triple (URI and Synonyms are optional in
practice). Non-standard vocabulary shapes are silently skipped.

Fix surface: `/deriva:manage-vocabulary`'s `add_term` (with description) for
new terms, `update_term` for backfilling.

**4. Naming convention compliance — WARN on hit.**
Tables and user-facing columns violating the PascalCase + underscore
convention (`Subject`, `Subject_Visit`, `Image_Classification`).

Why WARN, not FAIL: renaming is genuinely costly (Chaise URLs, downstream
consumers, annotations all break). The steward decides whether the cost
of fixing exceeds the cost of the naming inconsistency.

Fix surface: `/deriva:entity-naming` for rationale; `/deriva:evolve-schema`
for the 7-step rename procedure.

**5. Dangling foreign-key references — FAIL on hit.**
For each FK (up to `max_fk_checks`, default 50), the check counts source
rows whose non-null FK value doesn't match any row in the target table. A
non-zero count means real data-integrity damage — either the target was
deleted (pillar 5 violation) or the FK was loaded against the wrong target.

Multi-column FKs are skipped in v1 (the left-anti-join expression is more
involved). They're rare in practice — most FKs are single-column references
to a parent table's RID.

Implementation note: for vocab-sized targets, "fetch target value set, then
scan source rows" is the simplest correct query and acceptable up to ~100k
target rows. For larger targets, use an ERMrest `::null::` server-side
expression.

Fix surface: each row is a real issue requiring investigation — the right
remedy depends on whether the target should be re-created or the source
rows reassigned. No mass-fix recommended.

### DerivaML checks (the rest)

**6. Datasets without Dataset_Type — FAIL on hit.**
A dataset with no `Dataset_Type` term assigned can't be filtered by purpose
(Training / Testing / Validation / Inference) and breaks `restructure_assets`
defaults that read the type. Implementation: iterate `self.find_datasets()`,
check each dataset's `dataset_types` attribute is non-empty.

Fix surface: `/deriva-ml:dataset-lifecycle` Phase 1.

**7. Workflows missing URL or Checksum — FAIL on hit.**
A workflow's URL + Checksum together pin the code that ran. Either missing
means the workflow can't be traced back to source — an execution that
references it has provenance (who, when, what) but no code link (how).

New executions created via `deriva_ml_create_execution` populate both
automatically; offenders are typically historical workflows. Backfilling
is mostly hygiene; the more useful action is preventing new ones from
entering this state.

**8. Executions stuck in Running — WARN on hit.**
Executions in `Running` status whose `RMT` is older than
`executions_stuck_threshold_days` (default 7). These block their workflow's
lock and clutter recent-activity views.

Fix surface: `/deriva-ml:troubleshoot-execution`'s salvage workflow
(commit with `retry_failed=True` for recoverable runs, abort for abandoned
ones).

---

## Deferred from v1

Each deferred item is named explicitly in the eventual skill's "What this
skill does *not* cover" section so users know what's intentional vs missed.

- **ACL review** — who can read / write what. Different domain (operational
  / governance) and warrants its own surface.
- **Orphan Hatrac objects** — files in the object store with no
  corresponding asset-table row. Detecting these requires a recursive
  Hatrac walk, which is slow and ACL-sensitive. Worth doing but not in v1.
- **Feature column-type drift** — when a DerivaML feature's declared
  columns don't match the actual catalog columns. Feasible but the
  comparison surface is fiddly (Pydantic field types vs ERMrest column
  types; nullability mapping; FK-to-vocab vs enum mapping). Punt to v2.
- **Catalog snapshot retention / size** — operational concerns better
  handled by ops dashboards than a per-catalog walker.

---

## Report rendering

The report has three required surfaces:

1. **Markdown** — for human review and check-in to a docs/ directory; the
   per-check sections include an offender table (capped at 100 rows; the
   rest are summarized as `+ N more rows`) and the fix pointer.
2. **JSON / dict** — for piping into other tools, dashboards, CI.
3. **`has_failures()` predicate** — a single bool for CI gating
   (`assert not ml.audit().has_failures()` in a pre-release script).

The Markdown report opens with a metadata header (host, catalog, snaptime,
timestamp, deriva-ml flag) and a summary table that lets a steward scan
status without scrolling, then one section per check. Snaptime pinning is
load-bearing — it's what makes the audit reproducible against a known
catalog state even under concurrent writes.

---

## Connection to existing infrastructure

- **Snaptime capture**: `catalog.latest_snaptime()` at constructor time;
  subsequent reads via the snaptime-scoped catalog handle. Already a
  primitive in deriva-py.
- **Model traversal**: `catalog.getCatalogModel().schemas` → iterate the
  user-facing schemas (excluding `public`, `_acl_admin`, `pg_*`, `ermrest*`,
  `information_schema*`).
- **FK introspection**: `table.foreign_keys` for each table; each FK has
  `.foreign_key_columns`, `.referenced_columns`, `.pk_table`.
- **Vocabulary queries**: `catalog.getPathBuilder().schemas[s].tables[t]
  .entities().fetch()`.
- **DerivaML queries**: `self.find_datasets()`, query Workflow + Execution
  tables via the path builder; ML schema name available as `self.ml_schema`.

No new MCP tools are required to implement; `DerivaML.audit()` returning an
`AuditReport` is the entire new public surface. The corresponding MCP tool
`deriva_ml_audit_catalog_health(hostname, catalog_id)` follows trivially.

---

## Out-of-scope for this design doc

- **Generic-only audit for non-ML catalogs.** Two viable paths: (a) add
  `Model.audit()` upstream in deriva-py with the five generic checks and
  have `DerivaML.audit()` extend it; (b) keep both in `DerivaML.audit()`
  and let non-ML catalogs use the catalog primitives directly. We're not
  blocking the ML audit on the upstream decision. If `Model.audit()` lands
  later, `DerivaML.audit()` becomes `super().audit() + ml_checks`.
- **CLI wrapper.** A `deriva-ml-audit-catalog-health` CLI is straightforward
  once the API exists (a 20-line `argparse` + `print(report.render_markdown())`
  wrapper); not part of the API design.

---

## Open questions for the deriva-ml implementer

1. Should the API live on `DerivaML` directly or on a `DerivaML.health`
   namespace (`ml.health.audit()`)? The latter scales better if more
   health-style methods accrete (`ml.health.salvage_executions()`,
   `ml.health.refresh_minids()`, etc.). Current recommendation: start on
   `DerivaML` directly; promote to a namespace when the second method
   appears.
2. Should each check be a method too (`ml.audit_table_descriptions()`,
   etc.) so users can run one without the others? Probably not in v1 —
   the report-and-skim workflow is the dominant use case and the audit is
   fast enough that running all checks is rarely wasteful.
3. The `executions_stuck_threshold_days=7` default — should this be
   configurable per-catalog (an annotation)? Probably overkill; 7 is a
   reasonable universal default and the kwarg is enough escape hatch.

---

## What lands in the deriva-ml-skills plugin (later)

Once `DerivaML.audit()` is implemented, a single `/deriva-ml:audit-catalog-health`
skill documents:

- When to run (quarterly review, project handoff, post-bulk-load,
  post-migration, spot-check on an unfamiliar catalog).
- How to run via the Python API (notebook / script use), via the
  `deriva_ml_audit_catalog_health` MCP tool (Claude-driven), and via the
  optional CLI wrapper if it exists.
- What each check catches with the PASS / WARN / FAIL / SKIP rationale.
- Triage order for non-clean reports.
- Explicit cross-references to the fix-side skills (`/deriva:generate-descriptions`,
  `/deriva:manage-vocabulary`, `/deriva:evolve-schema`, `/deriva:load-data`,
  and within deriva-ml-skills `/deriva-ml:dataset-lifecycle`,
  `/deriva-ml:execution-lifecycle`, `/deriva-ml:troubleshoot-execution`).
- An explicit "What this skill does *not* cover" section enumerating the
  deferred items above.

That skill body is straightforward; the design work for *what to put in
it* is what this doc captures.
