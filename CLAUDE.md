# CLAUDE.md

This file provides guidance to Claude Code when working with the deriva-skills codebase.

## Project Overview

Claude Code plugin providing 10 tier-1 skills for the **core Deriva** ecosystem (`deriva-mcp-core` + `deriva-py`). Skills are organized as Markdown documents with optional Python scripts — no package build step required.

This plugin is the **tier-1** surface — skills that work on any Deriva catalog. The companion [`deriva-ml-skills`](https://github.com/informatics-isi-edu/deriva-ml-skills) plugin (tier-2) adds the DerivaML domain skills (Datasets, Workflows, Executions, Features, Asset_Type vocabularies). The two plugins are independently versioned and released; users with DerivaML workflows install both. See `docs/superpowers/plans/2026-04-27-skills-restructure.md` for the rationale and migration history.

## Commands

See [`../CLAUDE.md`](../CLAUDE.md) for shared `uv` and `bump-version`
conventions. Repo-specific commands:

> **CWD:** every command below assumes you are in
> `/Users/carl/GitHub/DerivaML/deriva-skills`. The Bash tool's cwd is **not**
> reliably persistent across turns — always chain `cd` into a single call,
> e.g. `cd /Users/carl/GitHub/DerivaML/deriva-skills && python3 skills/...`.
> See the workspace-level `CLAUDE.md` ("CWD discipline") for the rule.

```bash
# Load locally for development (no install needed)
claude --plugin-dir /path/to/deriva-skills

# Install from marketplace
/plugin install deriva

# Run version checker (use python3, NOT uv run — the script finds uv itself)
python3 skills/check-deriva-versions/scripts/check_versions.py
python3 skills/check-deriva-versions/scripts/check_versions.py --update
python3 skills/check-deriva-versions/scripts/check_versions.py --component deriva-py --json
```

**Release mechanics:** `bump-version` triggers GitHub Actions, which
bumps version in `plugin.json` + `marketplace.json`, commits back to
main, and creates the release archive. `bump_version("patch")` via the
MCP tool is also supported.

## Architecture

```
├── .claude-plugin/
│   ├── plugin.json           # Plugin metadata (name, version, description)
│   └── marketplace.json      # Marketplace registration (lists all 10 tier-1 skills)
├── skills/                   # 10 tier-1 skills, each in its own directory
│   ├── {skill-name}/
│   │   ├── SKILL.md          # Frontmatter (YAML) + skill content (Markdown)
│   │   ├── scripts/          # Optional Python helper scripts
│   │   └── references/       # Optional extended documentation
│   └── ...
├── evals/                    # Eval test cases (gitignored from releases)
│   └── {skill-name}/
│       └── trigger-eval.json
├── docs/superpowers/         # Design specs and implementation plans (not shipped)
└── .github/
    ├── workflows/release.yml # Tag-triggered release automation
    └── release-drafter.yml   # Release notes template
```

### Skill Organization (tier-1)

The tier-1 skills cover the core Deriva surface — what works on any Deriva catalog.

**User-invocable (`/deriva:<name>`):**

| Skill | Covers |
|-------|--------|
| `check-deriva-versions` | Version checking for deriva-py / deriva-mcp-core / deriva plugin |
| `create-table` | Create domain tables with columns + foreign keys |
| `customize-display` | Chaise display annotations via MCP tools |
| `entity-naming` | Naming conventions for schemas, tables, columns, vocabulary terms |
| `manage-vocabulary` | Vocabulary CRUD |
| `query-catalog-data` | Querying / browsing catalog data (also the cold-start exploration entry point) |
| `troubleshoot-deriva-errors` | Generic catalog troubleshooting (auth, RIDs, missing records, generic vocab terms) |

**Always-on (auto-invoked, no `/command`):**

| Skill | Purpose |
|-------|---------|
| `deriva-context` | Plugin-wide context: concept index, modeling checklist, pointers |
| `generate-descriptions` | Auto-generate descriptions for new catalog entities |
| `semantic-awareness` | Check for duplicates before creating entities |


### Skill Anatomy (`SKILL.md`)

```yaml
---
name: skill-name
description: >
  Trigger description — Claude uses this to decide when to auto-invoke.
  Be specific about when to trigger and when NOT to trigger.
disable-model-invocation: true   # Optional: only invoke via /skill-name
user-invocable: false             # Optional: auto-invoked only, no /command
---

# Skill Content

Markdown instructions that Claude follows when the skill is active.
```

### Eval Structure

Skills with evals have files under `evals/<skill-name>/`. Workspace iteration outputs (`evals/<skill>/iteration-*/`) are gitignored from releases.

## Release Process

1. Commit changes
2. Run `bump-version patch|minor|major` (creates tag and pushes automatically)
3. GitHub Actions automatically:
   - Bumps version in `plugin.json` and `marketplace.json`
   - Commits version bump back to main
   - Creates `deriva-skills-{VERSION}.tar.gz` (excludes `.git`, `.github`, `evals/`, `docs/superpowers`)
   - Publishes GitHub Release with auto-generated notes
4. Users with `autoUpdate: true` get the new version on next Claude Code restart. First-time install uses `/plugin install deriva`.

**Never create git tags manually** — always use `bump-version` from deriva-ml or the `bump_version` MCP tool.

## Cross-plugin coordination

The companion `deriva-ml-skills` plugin (tier-2) ships separately:

- **Cross-references:** When a tier-1 skill needs to point at ML-domain workflows (datasets, executions, features), use the cross-reference pattern: ``> See the `dataset-lifecycle` skill in `deriva-ml-skills` (tier-2) for ...``. Don't link as if the tier-2 skill is local — users may not have it installed.
- **Steering principle:** When BOTH plugins are loaded, the deriva-ml abstractions take precedence over the raw catalog primitives this plugin documents. The relevant tier-1 skills (`troubleshoot-deriva-errors`, `manage-vocabulary`) carry inline steering callouts; the upcoming `deriva-context` always-on skill will carry the principle plugin-wide.
- **Shared script (legacy):** `skills/check-deriva-versions/scripts/check_versions.py` currently knows about the entire ecosystem (deriva-py + deriva-mcp-core + deriva-ml + deriva-ml-mcp + both plugins). Phase 4 of the restructure (the v1.4 MCP surface sweep) will split it; until then, the `--component` flag is the boundary.

## Gotchas

- **Description field is critical** — the `description` in SKILL.md frontmatter controls when Claude auto-invokes the skill. Poorly written descriptions cause false triggers or missed triggers.
- **No build step** — skills are pure Markdown + optional scripts. Changes take effect immediately when loaded locally.
- **Release requires tag** — the workflow only triggers on `v*.*.*` tags pushed to origin. Commits alone won't create a release.
- **marketplace.json must list all skills** — if you add or remove a skill, update the skills array in `.claude-plugin/marketplace.json`.
- **Eval workspace dirs are not skills** — `evals/<skill>/iteration-*/` directories contain eval outputs and must NOT be listed in marketplace.json.
- **Scripts must handle minimal PATH** — Claude Code (especially inside the Desktop app) may not source shell profiles, so `$PATH` can be incomplete. Use `_find_uv()` pattern: try `shutil.which()` first, then check well-known locations (`~/.local/bin/`, `~/.cargo/bin/`, `/opt/homebrew/bin/`). Never assume `uv` or other tools are on PATH.
- **Marketplace cache can break** — The local git clone at `~/.claude/plugins/marketplaces/deriva-plugins/` can become corrupted (no commits, duplicate directories like `skills 2/`). The `_refresh_marketplace_cache()` function detects this and re-clones. If users report stale skills, check the marketplace cache health first.
- **MCP server version comes from the MCP resource** — The `check_versions.py` script only fetches the latest GitHub release tag for the MCP server. The *running* server version is obtained by Claude via `deriva://server/version`. The script does NOT inspect Docker containers or installed packages for MCP.
- **`/plugin update` is unreliable** — The interactive `/plugin update` command does not always work. The supported update path is `autoUpdate: true` in `~/.claude/settings.json` + restart Claude Code. The script's `--update` flag refreshes the marketplace cache (or re-clones if broken) so auto-update picks up the new version.
- **Skill names must be unique** — the directory name under `skills/` is the skill identifier. Renaming a directory changes the `/deriva:` command.
- **Cross-references matter** — when renaming or removing a skill, grep for its name across all other skills' `SKILL.md` and `references/*.md` files. Pay special attention to cross-references into `deriva-ml-skills` — those land at `/deriva-ml:<skill>` and are informational (the user may not have the tier-2 plugin installed).
- **`[tool.bumpversion]` config required** — `bump-version` wraps `bump-my-version` which needs `[tool.bumpversion]` in `pyproject.toml` with `tag = true` and `commit = true`. Without it, no tag or commit is created. See `deriva-mcp/pyproject.toml` for the reference config.
- **Never use `bump-my-version` directly** — always use `uv run bump-version patch|minor|major` which is the DerivaML CLI wrapper. Using `bump-my-version bump` directly bypasses project-specific logic.
