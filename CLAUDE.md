# CLAUDE.md

This file provides guidance to Claude Code when working with the deriva-skills codebase.

## Project Overview

Claude Code plugin providing 29 skills for DerivaML workflows. Skills are organized as Markdown documents with optional Python scripts — no package build step required.

## Commands

```bash
# Load locally for development (no install needed)
claude --plugin-dir /path/to/deriva-skills

# Install from marketplace
/plugin install deriva

# Release process — always use bump-version from deriva-ml (never bump-my-version directly)
uv run bump-version patch    # v0.12.1 -> v0.12.2
uv run bump-version minor    # v0.12.2 -> v0.13.0
uv run bump-version major    # v0.13.0 -> v1.0.0
# Or via MCP tool: bump_version("patch")
# GitHub Actions: bumps version in plugin.json + marketplace.json, commits back to main, creates archive + release

# Run version checker (use python3, NOT uv run — the script finds uv itself)
python3 skills/check-deriva-versions/scripts/check_versions.py
python3 skills/check-deriva-versions/scripts/check_versions.py --update
python3 skills/check-deriva-versions/scripts/check_versions.py --component deriva-ml --json
```

## Architecture

```
├── .claude-plugin/
│   ├── plugin.json           # Plugin metadata (name, version, description)
│   └── marketplace.json      # Marketplace registration (lists all 29 skills)
├── skills/                   # 29 skills, each in its own directory
│   ├── {skill-name}/
│   │   ├── SKILL.md          # Frontmatter (YAML) + skill content (Markdown)
│   │   ├── evals/            # Optional eval test cases (evals.json)
│   │   ├── scripts/          # Optional Python helper scripts
│   │   └── references/       # Optional extended documentation
│   └── ...
├── docs/superpowers/         # Design specs and implementation plans (not shipped)
└── .github/
    ├── workflows/release.yml # Tag-triggered release automation
    └── release-drafter.yml   # Release notes template
```

### Skill Organization

**5 Top-Level Skills (core concepts — triggered directly):**

| Skill | Covers |
|-------|--------|
| `dataset-lifecycle` | Create, populate, split, version, browse, download datasets |
| `execution-lifecycle` | Pre-flight validation, run experiments, execution provenance |
| `create-feature` | Features, labels, annotations, selectors |
| `manage-vocabulary` | Controlled vocabularies, terms, synonyms |
| `work-with-assets` | File assets — upload, download, provenance, types |

**3 Routers (dispatch to specialized sub-skills):**

| Router | Sub-skills |
|--------|-----------|
| `route-run-workflows` | ml-data-engineering, run-notebook, write-hydra-config, configure-experiment, new-model, troubleshoot-execution |
| `route-catalog-schema` | create-table, query-catalog-data, customize-display, use-annotation-builders, api-naming-conventions, catalog-operations-workflow |
| `route-project-setup` | setup-notebook-environment, check-deriva-versions, coding-guidelines, debug-bag-contents |

**3 Always-On Skills (auto-invoked, no user command):**

| Skill | Purpose |
|-------|---------|
| `generate-descriptions` | Auto-generate descriptions for new catalog entities |
| `semantic-awareness` | Check for duplicates before creating entities |
| `maintain-experiment-notes` | Log decisions to experiment-decisions.md |

**2 Utility Skills:**
- `browse-erd` — Launch interactive ERD browser
- `help` — Help and onboarding

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

Skills with evals have `evals/evals.json`:
```json
{
  "skill_name": "skill-name",
  "evals": [
    {"id": 1, "prompt": "...", "expected_output": "...", "files": []}
  ]
}
```

Eval workspaces (`*-workspace/`) contain test outputs and are gitignored from releases.

## Release Process

1. Commit changes
2. Run `bump-version patch|minor|major` (creates tag and pushes automatically)
3. GitHub Actions automatically:
   - Bumps version in `plugin.json` and `marketplace.json`
   - Commits version bump back to main
   - Creates `deriva-skills-{VERSION}.tar.gz` (excludes `.git`, `.github`, `*-workspace`, `docs/superpowers`)
   - Publishes GitHub Release with auto-generated notes
4. Users with `autoUpdate: true` get the new version on next Claude Code restart. First-time install uses `/plugin install deriva`.

**Never create git tags manually** — always use `bump-version` from deriva-ml or the `bump_version` MCP tool.

## Gotchas

- **Description field is critical** — the `description` in SKILL.md frontmatter controls when Claude auto-invokes the skill. Poorly written descriptions cause false triggers or missed triggers.
- **No build step** — skills are pure Markdown + optional scripts. Changes take effect immediately when loaded locally.
- **Release requires tag** — the workflow only triggers on `v*.*.*` tags pushed to origin. Commits alone won't create a release.
- **marketplace.json must list all skills** — if you add or remove a skill, update the skills array in `.claude-plugin/marketplace.json`.
- **Workspace dirs are not skills** — `*-workspace/` directories contain eval outputs and must NOT be listed in marketplace.json.
- **Scripts must handle minimal PATH** — Claude Code (especially inside the Desktop app) may not source shell profiles, so `$PATH` can be incomplete. Use `_find_uv()` pattern: try `shutil.which()` first, then check well-known locations (`~/.local/bin/`, `~/.cargo/bin/`, `/opt/homebrew/bin/`). Never assume `uv` or other tools are on PATH.
- **Marketplace cache can break** — The local git clone at `~/.claude/plugins/marketplaces/deriva-plugins/` can become corrupted (no commits, duplicate directories like `skills 2/`). The `_refresh_marketplace_cache()` function detects this and re-clones. If users report stale skills, check the marketplace cache health first.
- **MCP server version comes from the MCP resource** — The `check_versions.py` script only fetches the latest GitHub release tag for the MCP server. The *running* server version is obtained by Claude via `deriva://server/version`. The script does NOT inspect Docker containers or installed packages for MCP.
- **`/plugin update` is unreliable** — The interactive `/plugin update` command does not always work. The supported update path is `autoUpdate: true` in `~/.claude/settings.json` + restart Claude Code. The script's `--update` flag refreshes the marketplace cache (or re-clones if broken) so auto-update picks up the new version.
- **Skill names must be unique** — the directory name under `skills/` is the skill identifier. Renaming a directory changes the `/deriva:` command.
- **Cross-references matter** — when renaming or removing a skill, grep for its name across all other skills' `SKILL.md` and `references/*.md` files.
- **`[tool.bumpversion]` config required** — `bump-version` wraps `bump-my-version` which needs `[tool.bumpversion]` in `pyproject.toml` with `tag = true` and `commit = true`. Without it, no tag or commit is created. See `deriva-mcp/pyproject.toml` for the reference config.
- **Never use `bump-my-version` directly** — always use `uv run bump-version patch|minor|major` which is the DerivaML CLI wrapper. Using `bump-my-version bump` directly bypasses project-specific logic.
