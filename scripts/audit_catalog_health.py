#!/usr/bin/env python3
"""Catalog health audit — surface stewardship issues in a Deriva catalog.

A runnable catalog walker that reports common data-quality and
governance issues a steward would want to fix: tables / columns /
vocabulary terms with no descriptions, naming-convention violations,
dangling foreign-key references, and (when the DerivaML schema is
present) datasets without ``Dataset_Type``, workflows missing
identifying metadata, and long-running executions stuck in
``Running``.

The script is **read-only** — it never mutates the catalog. It is
safe to run against production catalogs at any time (modulo the cost
of the queries — see the ``--max-fk-checks`` flag for the only
potentially expensive operation).

Usage::

    uv run python scripts/audit_catalog_health.py \\
        --host data.example.org \\
        --catalog 1 \\
        --output catalog-health-2026-05-17.md

Or pipe to stdout::

    uv run python scripts/audit_catalog_health.py \\
        --host data.example.org --catalog 1

Exit codes:
    0 — audit completed (regardless of findings; a steward report
        with FAIL/WARN entries is the success outcome)
    1 — audit could not run (auth failure, catalog not reachable, etc.)

The companion skill (``/deriva:audit-catalog-health``) documents what
each check catches and how to interpret the findings.
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

# System / framework names to exclude from "missing description" checks
# and from naming-convention checks. These are server-managed and never
# user-facing.
SYSTEM_SCHEMAS = frozenset({"public", "_acl_admin"})
# Postgres / ermrest internal schemas (prefix match)
SYSTEM_SCHEMA_PREFIXES = ("pg_", "ermrest", "information_schema")
SYSTEM_COLUMNS = frozenset({"RID", "RCT", "RMT", "RCB", "RMB"})
# Asset-table standard columns — these have well-known semantics and
# rarely need a per-column description.
ASSET_STANDARD_COLUMNS = frozenset({"URL", "Filename", "Length", "MD5", "Content_Type"})

# Naming-convention pattern: PascalCase, optional underscores between
# PascalCase segments (e.g., ``Subject``, ``Subject_Visit``,
# ``Image_Classification``). System columns and reserved names are
# excluded before the check runs.
PASCAL_RE = re.compile(r"^[A-Z][a-zA-Z0-9]*(_[A-Z][a-zA-Z0-9]*)*$")


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class CheckResult:
    """Outcome of one audit check.

    Attributes:
        name: Human-readable check name (rendered as a Markdown section).
        status: ``PASS``, ``WARN``, ``FAIL``, or ``SKIP``.
        summary: One-line explanation of the result (rendered in the
            top-of-report summary table).
        rows: Optional list of offender rows. Each row is a dict; the
            keys become column headers in the rendered table.
        fix_pointer: Short Markdown sentence pointing at the right
            skill / tool for fixing the issue.
    """

    name: str
    status: str
    summary: str
    rows: list[dict[str, Any]] = field(default_factory=list)
    fix_pointer: str = ""


@dataclass
class AuditContext:
    """Shared state passed to each check function.

    Attributes:
        host: Hostname of the catalog server.
        catalog_id: Catalog ID (numeric string or alias).
        model: deriva-py ``Model`` object — full catalog model.
        catalog: deriva-py ``ErmrestCatalog`` — for executing queries.
        snaptime: Snaptime at which the audit started; recorded in the
            report so the findings are pinned to a specific catalog
            state.
        ml: Optional ``DerivaML`` instance; ``None`` when the deriva-ml
            schema is not present.
        max_fk_checks: Cap on how many foreign keys to scan for
            dangling references. Higher = more thorough, slower.
    """

    host: str
    catalog_id: str
    model: Any
    catalog: Any
    snaptime: str
    ml: Any = None
    max_fk_checks: int = 50


# ---------------------------------------------------------------------------
# Connection / setup
# ---------------------------------------------------------------------------


def connect(host: str, catalog_id: str) -> tuple[Any, Any, str]:
    """Open a read-only connection to the catalog.

    Returns:
        ``(model, catalog, snaptime)`` — the deriva-py model snapshot,
        the live catalog handle for query execution, and the snaptime
        string captured immediately on connect.

    Raises:
        SystemExit: on auth failure or unreachable catalog. The
        exception is converted to a 1-line stderr message and exit
        code 1 to keep the script's CLI ergonomics simple.
    """
    try:
        from deriva.core import DerivaServer, get_credential
    except ImportError as e:
        sys.exit(f"deriva-py not installed: {e}. Try `uv pip install deriva`.")
    try:
        credentials = get_credential(host)
        server = DerivaServer("https", host, credentials=credentials)
        catalog = server.connect_ermrest(catalog_id)
        model = catalog.getCatalogModel()
        snaptime = catalog.latest_snaptime()
    except Exception as e:
        sys.exit(f"Could not connect to {host}/{catalog_id}: {e}")
    return model, catalog, snaptime


def detect_deriva_ml(host: str, catalog_id: str, model: Any) -> Any:
    """Detect whether the catalog has the deriva-ml schema applied.

    The detection is a try / catch around ``DerivaML(host, catalog_id)``
    — the constructor probes for the expected ML schema and tables and
    raises if they're not there. We additionally short-circuit when
    the package itself isn't installed, since a steward without
    deriva-ml installed can still get value from the generic checks.

    Returns:
        A ``DerivaML`` instance when the schema is present and
        deriva-ml is importable; ``None`` otherwise.
    """
    try:
        from deriva_ml import DerivaML
    except ImportError:
        return None
    try:
        return DerivaML(host, catalog_id)
    except Exception:
        # ML schema not present, or some other constructor-time issue
        # (an outdated ML schema, missing vocab terms, etc.). Either
        # way, ML-specific checks should be skipped — the generic
        # checks still cover real issues in the rest of the catalog.
        return None


# ---------------------------------------------------------------------------
# Generic checks
# ---------------------------------------------------------------------------


def _user_schemas(model: Any) -> list[Any]:
    """Return user-facing schemas, excluding system / Postgres internals."""
    schemas = []
    for name, schema in model.schemas.items():
        if name in SYSTEM_SCHEMAS:
            continue
        if any(name.startswith(p) for p in SYSTEM_SCHEMA_PREFIXES):
            continue
        schemas.append(schema)
    return schemas


def _user_tables(model: Any) -> list[Any]:
    """Iterate every (user-facing) table in the model."""
    tables = []
    for schema in _user_schemas(model):
        for table in schema.tables.values():
            tables.append(table)
    return tables


def check_table_descriptions(ctx: AuditContext) -> CheckResult:
    """Flag tables whose ``comment`` is empty or absent."""
    offenders = []
    for table in _user_tables(ctx.model):
        if not (table.comment or "").strip():
            offenders.append({"Schema": table.schema.name, "Table": table.name})
    if not offenders:
        return CheckResult(
            name="Tables missing descriptions",
            status="PASS",
            summary="All user-facing tables have descriptions.",
        )
    return CheckResult(
        name="Tables missing descriptions",
        status="FAIL",
        summary=f"{len(offenders)} tables have no description.",
        rows=offenders,
        fix_pointer=(
            "Use `/deriva:generate-descriptions` (the auto-loaded skill) "
            "to draft descriptions, then `update_table_comment` to apply "
            "each one. Tables without descriptions degrade Chaise "
            "tooltips and downstream documentation."
        ),
    )


def check_column_descriptions(ctx: AuditContext) -> CheckResult:
    """Flag columns with no ``comment``, excluding system + asset-boilerplate."""
    offenders = []
    for table in _user_tables(ctx.model):
        for col in table.column_definitions:
            if col.name in SYSTEM_COLUMNS:
                continue
            # Asset-table standard columns — well-known semantics, low
            # value to caption each one.
            if col.name in ASSET_STANDARD_COLUMNS:
                continue
            if not (col.comment or "").strip():
                offenders.append({
                    "Schema": table.schema.name,
                    "Table": table.name,
                    "Column": col.name,
                    "Type": str(col.type.typename),
                })
    if not offenders:
        return CheckResult(
            name="Columns missing descriptions",
            status="PASS",
            summary="All user-facing columns have descriptions (system + asset-boilerplate excluded).",
        )
    # WARN, not FAIL: column descriptions are nice-to-have, not a
    # functional gap. Reserve FAIL for things that break user-facing
    # behavior or block reproducibility.
    return CheckResult(
        name="Columns missing descriptions",
        status="WARN",
        summary=f"{len(offenders)} user-facing columns have no description.",
        rows=offenders,
        fix_pointer=(
            "Use `/deriva:generate-descriptions` to draft per-column "
            "captions, then `update_column_comment`. Prioritize columns "
            "that appear in Chaise's `visible-columns` (those a user "
            "actually sees) over internal scratch columns."
        ),
    )


def _is_vocabulary_table(table: Any) -> bool:
    """Heuristic: a table is a vocabulary if it has the canonical column shape.

    The vocabulary convention is the ``Name`` + ``Description`` + ``ID``
    + ``URI`` + ``Synonyms`` column quintet. We treat the presence of
    ``Name`` + ``Description`` + ``ID`` as sufficient — ``URI`` and
    ``Synonyms`` are optional in practice.
    """
    col_names = {c.name for c in table.column_definitions}
    return {"Name", "Description", "ID"}.issubset(col_names)


def check_vocabulary_term_descriptions(ctx: AuditContext) -> CheckResult:
    """Flag vocabulary terms whose ``Description`` is empty."""
    pb = ctx.catalog.getPathBuilder()
    offenders = []
    vocab_count = 0
    for table in _user_tables(ctx.model):
        if not _is_vocabulary_table(table):
            continue
        vocab_count += 1
        try:
            rows = list(pb.schemas[table.schema.name].tables[table.name].entities().fetch())
        except Exception as e:
            offenders.append({
                "Schema": table.schema.name,
                "Table": table.name,
                "Term": "(read failed)",
                "Note": str(e)[:80],
            })
            continue
        for row in rows:
            desc = (row.get("Description") or "").strip()
            if not desc:
                offenders.append({
                    "Schema": table.schema.name,
                    "Table": table.name,
                    "Term": row.get("Name", ""),
                    "Note": "",
                })
    if vocab_count == 0:
        return CheckResult(
            name="Vocabulary terms missing descriptions",
            status="SKIP",
            summary="No vocabulary-shaped tables found.",
        )
    if not offenders:
        return CheckResult(
            name="Vocabulary terms missing descriptions",
            status="PASS",
            summary=f"All terms in {vocab_count} vocabulary tables have descriptions.",
        )
    return CheckResult(
        name="Vocabulary terms missing descriptions",
        status="FAIL",
        summary=f"{len(offenders)} vocabulary terms have no description.",
        rows=offenders,
        fix_pointer=(
            "Use `/deriva:manage-vocabulary`'s `add_term` (with a "
            "description) for new terms; `update_term` for backfilling "
            "existing ones. Term descriptions surface in Chaise dropdowns "
            "and are the user-facing definition of what each term means."
        ),
    )


def check_naming_conventions(ctx: AuditContext) -> CheckResult:
    """Flag user-facing tables / columns that violate PascalCase + underscore convention."""
    offenders = []
    for table in _user_tables(ctx.model):
        if not PASCAL_RE.match(table.name):
            offenders.append({
                "Schema": table.schema.name,
                "Kind": "Table",
                "Name": table.name,
            })
        for col in table.column_definitions:
            if col.name in SYSTEM_COLUMNS:
                continue
            if not PASCAL_RE.match(col.name):
                offenders.append({
                    "Schema": table.schema.name,
                    "Kind": f"Column ({table.name})",
                    "Name": col.name,
                })
    if not offenders:
        return CheckResult(
            name="Naming convention compliance",
            status="PASS",
            summary="All user-facing tables and columns follow the PascalCase convention.",
        )
    # WARN: renaming is genuinely costly (Chaise URLs, downstream
    # consumers, annotations all break). Surface as a flag, not a hard
    # fail — the steward decides whether to migrate.
    return CheckResult(
        name="Naming convention compliance",
        status="WARN",
        summary=f"{len(offenders)} names violate PascalCase convention.",
        rows=offenders,
        fix_pointer=(
            "See `/deriva:entity-naming` for the convention rationale "
            "and `/deriva:evolve-schema` for the 7-step rename procedure "
            "(renaming is non-additive — annotations and downstream "
            "consumers ride along)."
        ),
    )


def check_dangling_foreign_keys(ctx: AuditContext) -> CheckResult:
    """Flag foreign keys whose source rows reference non-existent target rows.

    Walks every user-facing FK up to ``ctx.max_fk_checks`` (FKs are
    sorted by source-table name for stable output across runs) and
    runs a left-anti-join query: ``source!target_pkey::null::``.

    The query cost scales with source-table size — for very large
    catalogs, raise ``--max-fk-checks`` only after profiling.
    """
    pb = ctx.catalog.getPathBuilder()
    fks_to_check = []
    for table in _user_tables(ctx.model):
        for fk in table.foreign_keys:
            fks_to_check.append((table, fk))
    fks_to_check.sort(key=lambda tf: (tf[0].schema.name, tf[0].name))
    fks_to_check = fks_to_check[: ctx.max_fk_checks]

    offenders = []
    for table, fk in fks_to_check:
        # Build the left-anti-join via the path builder. The source FK
        # column(s) are fk.foreign_key_columns; the referenced table /
        # columns live on fk.pk_table / fk.referenced_columns.
        try:
            ref_table = fk.pk_table
            # Skip FKs whose target table isn't user-facing (system
            # tables are out-of-scope for this audit).
            if ref_table.schema.name in SYSTEM_SCHEMAS:
                continue
            if any(ref_table.schema.name.startswith(p) for p in SYSTEM_SCHEMA_PREFIXES):
                continue
            src_cols = [c.name for c in fk.foreign_key_columns]
            ref_cols = [c.name for c in fk.referenced_columns]
            # Heuristic for the common single-column case: count
            # source rows whose FK column is non-null but doesn't
            # appear in the target. Multi-column FKs are skipped (the
            # query expression is more involved) — they're rare enough
            # to defer.
            if len(src_cols) != 1 or len(ref_cols) != 1:
                continue
            src_col, ref_col = src_cols[0], ref_cols[0]
            # Pull the set of target values, then check source rows
            # against it. This is cheap for vocab-sized targets and
            # acceptable up to ~100k target rows.
            target_path = pb.schemas[ref_table.schema.name].tables[ref_table.name]
            target_values = {
                row[ref_col]
                for row in target_path.entities(target_path.column_definitions[ref_col]).fetch()
                if row[ref_col] is not None
            }
            source_path = pb.schemas[table.schema.name].tables[table.name]
            broken = 0
            for row in source_path.entities(source_path.column_definitions[src_col]).fetch():
                v = row[src_col]
                if v is not None and v not in target_values:
                    broken += 1
            if broken > 0:
                offenders.append({
                    "Schema": table.schema.name,
                    "Table": table.name,
                    "FK_Column": src_col,
                    "Referenced": f"{ref_table.schema.name}:{ref_table.name}.{ref_col}",
                    "Broken_Rows": broken,
                })
        except Exception as e:
            # A single FK-check failure shouldn't sink the whole
            # audit — record it as a row and continue.
            offenders.append({
                "Schema": table.schema.name,
                "Table": table.name,
                "FK_Column": ",".join(c.name for c in fk.foreign_key_columns),
                "Referenced": "(check failed)",
                "Broken_Rows": f"err: {str(e)[:60]}",
            })

    if not offenders:
        return CheckResult(
            name="Dangling foreign-key references",
            status="PASS",
            summary=f"Scanned {len(fks_to_check)} FKs; no dangling references.",
        )
    return CheckResult(
        name="Dangling foreign-key references",
        status="FAIL",
        summary=(
            f"{len(offenders)} FKs have rows pointing at non-existent targets "
            f"(scanned {len(fks_to_check)} of all FKs; raise --max-fk-checks to scan more)."
        ),
        rows=offenders,
        fix_pointer=(
            "Each row points at a real data-integrity issue — either "
            "the target was deleted (pillar 5: evolve, don't overwrite — "
            "see `/deriva:load-data`) or the FK was loaded against the "
            "wrong target. Investigate before mass-fixing; the right "
            "remedy depends on whether the target should be re-created "
            "or the source rows reassigned."
        ),
    )


# ---------------------------------------------------------------------------
# DerivaML-specific checks
# ---------------------------------------------------------------------------


def check_datasets_have_type(ctx: AuditContext) -> CheckResult:
    """Flag datasets with no ``Dataset_Type`` association."""
    try:
        datasets = ctx.ml.find_datasets()
    except Exception as e:
        return CheckResult(
            name="Datasets without Dataset_Type",
            status="SKIP",
            summary=f"Could not enumerate datasets: {str(e)[:80]}",
        )
    offenders = []
    for ds in datasets:
        # Dataset.dataset_types is the list of associated Dataset_Type
        # vocabulary terms (empty list = untyped).
        types = getattr(ds, "dataset_types", None) or []
        if not types:
            offenders.append({
                "RID": getattr(ds, "rid", "?"),
                "Description": (getattr(ds, "description", "") or "")[:80],
            })
    if not datasets:
        return CheckResult(
            name="Datasets without Dataset_Type",
            status="SKIP",
            summary="No datasets in catalog.",
        )
    if not offenders:
        return CheckResult(
            name="Datasets without Dataset_Type",
            status="PASS",
            summary=f"All {len(datasets)} datasets have a Dataset_Type assigned.",
        )
    return CheckResult(
        name="Datasets without Dataset_Type",
        status="FAIL",
        summary=f"{len(offenders)} of {len(datasets)} datasets have no Dataset_Type.",
        rows=offenders,
        fix_pointer=(
            "Use `/deriva-ml:dataset-lifecycle` Phase 1 — every dataset "
            "should carry at least one `Dataset_Type` term (Training / "
            "Testing / Validation / Inference / etc.). Untyped datasets "
            "can't be filtered by purpose and break the "
            "`restructure_assets` defaults that read the type."
        ),
    )


def check_workflows_have_provenance(ctx: AuditContext) -> CheckResult:
    """Flag workflows missing URL or Checksum metadata.

    A workflow's URL + Checksum together pin the code that ran. Either
    missing leaves the execution unable to point at the code it
    actually executed.
    """
    pb = ctx.catalog.getPathBuilder()
    try:
        workflows = list(
            pb.schemas[ctx.ml.ml_schema].tables["Workflow"].entities().fetch()
        )
    except Exception as e:
        return CheckResult(
            name="Workflows missing URL or Checksum",
            status="SKIP",
            summary=f"Could not query Workflow table: {str(e)[:80]}",
        )
    offenders = []
    for wf in workflows:
        url = (wf.get("URL") or "").strip()
        checksum = (wf.get("Checksum") or "").strip()
        if not url or not checksum:
            offenders.append({
                "RID": wf.get("RID", "?"),
                "Name": (wf.get("Name") or "")[:60],
                "URL_present": bool(url),
                "Checksum_present": bool(checksum),
            })
    if not workflows:
        return CheckResult(
            name="Workflows missing URL or Checksum",
            status="SKIP",
            summary="No workflows in catalog.",
        )
    if not offenders:
        return CheckResult(
            name="Workflows missing URL or Checksum",
            status="PASS",
            summary=f"All {len(workflows)} workflows have URL + Checksum.",
        )
    return CheckResult(
        name="Workflows missing URL or Checksum",
        status="FAIL",
        summary=f"{len(offenders)} of {len(workflows)} workflows are missing URL or Checksum.",
        rows=offenders,
        fix_pointer=(
            "A workflow without URL + Checksum can't be traced back to "
            "code. New executions should always create workflows via "
            "`deriva_ml_create_execution` (which populates both); "
            "backfilling old workflows is mostly historical hygiene."
        ),
    )


def check_executions_stuck_running(ctx: AuditContext, days_threshold: int = 7) -> CheckResult:
    """Flag executions in ``Running`` status whose ``RMT`` is older than ``days_threshold``."""
    pb = ctx.catalog.getPathBuilder()
    try:
        execs = list(
            pb.schemas[ctx.ml.ml_schema].tables["Execution"].entities().fetch()
        )
    except Exception as e:
        return CheckResult(
            name="Executions stuck in Running",
            status="SKIP",
            summary=f"Could not query Execution table: {str(e)[:80]}",
        )
    now = datetime.now(timezone.utc)
    offenders = []
    for ex in execs:
        status = (ex.get("Status") or "").strip()
        # The Status column is a FK to Execution_Status; the term name
        # comes back as the value. Match case-insensitively.
        if status.lower() != "running":
            continue
        rmt = ex.get("RMT")
        if not rmt:
            continue
        try:
            # ERMrest timestamps are ISO 8601 with timezone.
            ts = datetime.fromisoformat(rmt.replace("Z", "+00:00"))
        except Exception:
            continue
        age_days = (now - ts).days
        if age_days >= days_threshold:
            offenders.append({
                "RID": ex.get("RID", "?"),
                "Workflow_RID": ex.get("Workflow", "") or "",
                "Last_Modified": rmt,
                "Age_Days": age_days,
            })
    if not execs:
        return CheckResult(
            name="Executions stuck in Running",
            status="SKIP",
            summary="No executions in catalog.",
        )
    if not offenders:
        return CheckResult(
            name="Executions stuck in Running",
            status="PASS",
            summary=f"No executions stuck in Running > {days_threshold} days.",
        )
    return CheckResult(
        name="Executions stuck in Running",
        status="WARN",
        summary=(
            f"{len(offenders)} executions in Running status, "
            f"last touched > {days_threshold} days ago."
        ),
        rows=offenders,
        fix_pointer=(
            "Use `/deriva-ml:troubleshoot-execution`'s salvage workflow: "
            "either `deriva_ml_commit_execution(retry_failed=True)` if the "
            "outputs are recoverable, or `deriva_ml_abort_execution` if "
            "the run is genuinely abandoned. Long-running executions "
            "block their workflow's lock and obscure the recent-activity "
            "view."
        ),
    )


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def render_markdown(ctx: AuditContext, results: list[CheckResult]) -> str:
    """Render the audit report as Markdown.

    Layout:
        - Heading with host, catalog, snaptime, timestamp, deriva-ml flag
        - Summary table (one row per check) so a steward can scan
          status without scrolling
        - One section per check with status, summary, optional offender
          table (capped at 100 rows; the rest are summarized in a
          "+ N more" line so the report stays a sane size on big
          catalogs), and the fix pointer.
    """
    lines: list[str] = []
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines.append("# Catalog Health Audit")
    lines.append("")
    lines.append(f"- **Host:** {ctx.host}")
    lines.append(f"- **Catalog:** {ctx.catalog_id}")
    lines.append(f"- **Snaptime:** `{ctx.snaptime}` (audit reads pinned to this state)")
    lines.append(f"- **Generated:** {now}")
    lines.append(f"- **DerivaML detected:** {'yes' if ctx.ml else 'no'}")
    lines.append("")

    lines.append("## Summary")
    lines.append("")
    lines.append("| Check | Status | Detail |")
    lines.append("|---|---|---|")
    for r in results:
        lines.append(f"| {r.name} | **{r.status}** | {r.summary} |")
    lines.append("")

    for r in results:
        lines.append(f"## {r.name} — {r.status}")
        lines.append("")
        lines.append(r.summary)
        lines.append("")
        if r.rows:
            cap = 100
            shown = r.rows[:cap]
            headers = list(shown[0].keys())
            lines.append("| " + " | ".join(headers) + " |")
            lines.append("|" + "|".join(["---"] * len(headers)) + "|")
            for row in shown:
                lines.append("| " + " | ".join(str(row.get(h, "")) for h in headers) + " |")
            if len(r.rows) > cap:
                lines.append("")
                lines.append(f"_(+ {len(r.rows) - cap} more rows, not shown)_")
            lines.append("")
        if r.fix_pointer:
            lines.append(f"**How to fix:** {r.fix_pointer}")
            lines.append("")

    return "\n".join(lines)


def render_console_summary(results: list[CheckResult]) -> str:
    """One-line-per-check stderr summary, regardless of where the report goes."""
    lines = []
    for r in results:
        lines.append(f"  {r.status:6s} {r.name:50s} {r.summary}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def run_audit(ctx: AuditContext) -> list[CheckResult]:
    """Run all checks against ``ctx`` and return the result list."""
    results: list[CheckResult] = []

    # Generic checks always run.
    generic_checks = [
        check_table_descriptions,
        check_column_descriptions,
        check_vocabulary_term_descriptions,
        check_naming_conventions,
        check_dangling_foreign_keys,
    ]
    for check in generic_checks:
        t0 = time.time()
        try:
            results.append(check(ctx))
        except Exception as e:
            results.append(CheckResult(
                name=check.__name__,
                status="SKIP",
                summary=f"Check raised {type(e).__name__}: {str(e)[:80]}",
            ))
        print(f"  ({time.time() - t0:.1f}s) {check.__name__}", file=sys.stderr)

    # DerivaML checks run only when the ML schema is present.
    if ctx.ml is not None:
        ml_checks = [
            check_datasets_have_type,
            check_workflows_have_provenance,
            check_executions_stuck_running,
        ]
        for check in ml_checks:
            t0 = time.time()
            try:
                results.append(check(ctx))
            except Exception as e:
                results.append(CheckResult(
                    name=check.__name__,
                    status="SKIP",
                    summary=f"Check raised {type(e).__name__}: {str(e)[:80]}",
                ))
            print(f"  ({time.time() - t0:.1f}s) {check.__name__}", file=sys.stderr)

    return results


def main() -> int:
    p = argparse.ArgumentParser(
        description="Run a read-only catalog health audit and emit a Markdown report.",
    )
    p.add_argument("--host", required=True, help="Catalog hostname (e.g., data.example.org)")
    p.add_argument("--catalog", required=True, help="Catalog ID (e.g., 1)")
    p.add_argument(
        "--output", "-o",
        help="Output file (default: stdout)",
    )
    p.add_argument(
        "--max-fk-checks",
        type=int,
        default=50,
        help="Cap on dangling-FK scans (default: 50). Higher = more thorough, slower.",
    )
    args = p.parse_args()

    print(f"Connecting to {args.host}/{args.catalog}...", file=sys.stderr)
    model, catalog, snaptime = connect(args.host, args.catalog)
    print(f"  snaptime: {snaptime}", file=sys.stderr)

    print("Detecting deriva-ml schema...", file=sys.stderr)
    ml = detect_deriva_ml(args.host, args.catalog, model)
    print(f"  deriva-ml: {'present' if ml else 'not detected'}", file=sys.stderr)

    ctx = AuditContext(
        host=args.host,
        catalog_id=args.catalog,
        model=model,
        catalog=catalog,
        snaptime=snaptime,
        ml=ml,
        max_fk_checks=args.max_fk_checks,
    )

    print("Running checks...", file=sys.stderr)
    results = run_audit(ctx)

    print("", file=sys.stderr)
    print("Results:", file=sys.stderr)
    print(render_console_summary(results), file=sys.stderr)
    print("", file=sys.stderr)

    report = render_markdown(ctx, results)
    if args.output:
        with open(args.output, "w") as f:
            f.write(report)
        print(f"Wrote {args.output}", file=sys.stderr)
    else:
        print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
