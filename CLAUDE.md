# CLAUDE.md

This file provides guidance to Claude Code when working with the deriva-skills codebase.

## Project Overview

Claude Code plugin providing 12 skills for the **core Deriva** ecosystem (`deriva-mcp-core` + `deriva-py`). Skills are organized as Markdown documents with optional Python scripts — no package build step required.

The plugin is self-contained — it works on any Deriva catalog, with no other plugins required. A separate companion plugin, [`deriva-ml-skills`](https://github.com/informatics-isi-edu/deriva-ml-skills), exists for users doing DerivaML ML workflows (datasets, workflows, executions, features); when both are loaded, the two cooperate via the steering principle described under "Cross-plugin coordination" below. Without it, this plugin still does its job. See `docs/superpowers/plans/2026-04-27-skills-restructure.md` for the rationale and migration history of the two-plugin split.

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
```

Versioning and updates are documented in `skills/troubleshoot-deriva-errors/SKILL.md` ("Versioning and updates" section). The three core components — deriva-py, deriva-mcp-core, the `deriva` plugin — each have their own update path; there is no unified version-checker tool in the plugin (the previous `check-deriva-versions` skill was removed once `autoUpdate: true` for plugins, the `server_status` MCP resource for the server, and `uv pip show` for the library all became reliable enough that wrapping them in a custom script no longer earned its weight).

**Release mechanics:** `bump-version` triggers GitHub Actions, which
bumps version in `plugin.json`, commits back to main, and creates the
release archive. `bump_version("patch")` via the MCP tool is also
supported. Note: the version field in the
[`deriva-plugins`](https://github.com/informatics-isi-edu/deriva-plugins)
meta-marketplace's `marketplace.json` is **not** auto-bumped — see
"Cross-plugin coordination" below.

## Architecture

```
├── .claude-plugin/
│   └── plugin.json           # Plugin manifest (name, version, description) — read by Claude Code after install
├── skills/                   # 12 skills, each in its own directory; auto-discovered by Claude Code from `skills/*/SKILL.md`
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

### Skill Organization

The skills cover the core Deriva surface — what works on any Deriva catalog.

The 12 skills divide into two shapes — user commands (what a person invokes) and auto-invoked behaviors (what Claude triggers on its own to enforce a discipline). The split matters when editing: command-shaped skills can assume the user typed `/deriva:<name>` and should produce a useful response on their own; behavior-shaped skills run as background context and should never produce a standalone "here's what I did" message.

**User commands (`/deriva:<name>`)** — `user-invocable: true` in frontmatter:

| Skill | Covers |
|-------|--------|
| `create-table` | Create domain tables with columns + foreign keys |
| `customize-display` | Chaise display annotations via MCP tools (interactive path) |
| `use-annotation-builders` | Type-safe Python builder classes for production deployment scripts (Python path) |
| `entity-naming` | Naming conventions for schemas, tables, columns, vocabulary terms |
| `getting-started` | Five-step new-user onboarding walkthrough; routes through the per-task skills |
| `load-data` | Loading data into tables: row inserts, batch CSV/JSON, asset uploads via deriva-upload-cli or MCP, updates, deletes |
| `manage-vocabulary` | Vocabulary CRUD |
| `query-catalog-data` | Querying / browsing catalog data (cold-start exploration via rag_search; row-level reads) |
| `troubleshoot-deriva-errors` | Generic catalog troubleshooting (auth, RIDs, missing records, generic vocab terms) — also carries the versioning-and-updates guidance for deriva-py / deriva-mcp-core / deriva plugin |

**Auto-invoked behaviors (no slash command)** — `user-invocable: false` in frontmatter; should NOT be surfaced in user-facing skill lists as if they were tools:

| Skill | When Claude triggers it |
|-------|-------------------------|
| `deriva-context` | Always — establishes plugin context, concept index, and modeling checklist on every conversation |
| `semantic-awareness` | Before any catalog-entity creation — enforces the find-before-you-create discipline |
| `generate-descriptions` | When a catalog entity is being created without a user-supplied description — auto-drafts one |

These three are disciplines, not commands. They live alongside the user-invocable skills under `skills/` and the meta-marketplace lists them so Claude Code loads them into the plugin, but a user typing `/deriva:semantic-awareness` is using the plugin wrong — those skills are designed to fire from Claude's own decision-making, not from user invocation. Documentation surfaces (README, marketing copy, help blurbs) should keep them in a clearly-separated section so users don't reach for them.


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
   - Bumps version in `plugin.json` (the bump-my-version config in `pyproject.toml` runs as part of `bump-version`, before the tag push)
   - Commits version bump back to main
   - Creates `deriva-skills-{VERSION}.tar.gz` (the tar invocation packages `.claude-plugin/` and `skills/`; everything else — `.git`, `.github`, `evals/`, `docs/`, `tests/`, `pyproject.toml`, `uv.lock` — is excluded by virtue of not being passed)
   - Publishes GitHub Release with auto-generated notes
4. **Manual step — bump the meta-marketplace.** See "Bumping the meta-marketplace" below. Without this step, users on `autoUpdate: true` will stay pinned to the previous version.

After step 4 lands, users with `autoUpdate: true` pick up the new version on next Claude Code restart. First-time install uses `/plugin install deriva` after `/plugin marketplace add informatics-isi-edu/deriva-plugins`.

**Never create git tags manually** — always use `bump-version` from deriva-ml or the `bump_version` MCP tool.

### Bumping the meta-marketplace

The [`deriva-plugins`](https://github.com/informatics-isi-edu/deriva-plugins) meta-marketplace pins each plugin to a specific version (`version` field per plugin entry in its `marketplace.json`). That pin is **not** updated by this repo's release workflow — `autoUpdate` users on the meta-marketplace will not see a new release until the pin is bumped. After every `bump-version` here:

```bash
# In a checkout of informatics-isi-edu/deriva-plugins:
cd /path/to/deriva-plugins
git pull

# Bump the deriva entry (replace 1.2.2 with the new version)
jq '(.plugins[] | select(.name == "deriva") | .version) = "1.2.2"' \
  .claude-plugin/marketplace.json > /tmp/m.json && \
  mv /tmp/m.json .claude-plugin/marketplace.json

git add .claude-plugin/marketplace.json
git commit -m "Bump deriva to 1.2.2"
git push
```

Sanity-check the diff before pushing — `jq` rewrites the whole file, so the diff should be exactly one line changed.

This step is currently manual. A future improvement (deferred for now) is a GitHub Actions workflow on this repo that fires on `v*.*.*` tag push and opens a PR against `deriva-plugins` with the version bump. Until that lands, treat the manual step as part of the release.

## Cross-plugin coordination

This plugin is standalone — install it on its own and it works on any Deriva catalog. The `deriva-ml-skills` plugin is a separate, optional companion for users doing DerivaML ML workflows. Two coordination details apply only when *both* plugins are loaded:

- **Steering principle (load-bearing).** When the `deriva-ml-skills` plugin is also loaded, its DerivaML abstractions (Datasets, Workflows, Executions, Features, Asset_Type vocabularies) take precedence over the raw catalog primitives this plugin documents — users should reach for `/deriva-ml:<skill>` and the deriva-ml Python API for those concepts, not the raw `insert_records` / `update_record` core tools. The always-on `deriva-context` skill carries this principle plugin-wide; the `troubleshoot-deriva-errors` and `manage-vocabulary` skills carry inline steering callouts as reinforcement. None of this affects users who only have *this* plugin installed — the steering only fires when the deriva-ml surface actually exists.
- **Cross-references out to deriva-ml-skills.** A few skills in this plugin point users at the companion plugin's skills (e.g. ``> For dataset lifecycle, see `dataset-lifecycle` in `deriva-ml-skills` ``). Always frame these as conditional ("if you have the deriva-ml plugin loaded") rather than inline links — users may not have it installed.

### Distribution: the `deriva-plugins` marketplace

The supported install path is the [`informatics-isi-edu/deriva-plugins`](https://github.com/informatics-isi-edu/deriva-plugins) marketplace. Users `/plugin marketplace add` it once, then `/plugin install deriva`. The marketplace also lists the `deriva-ml` plugin alongside this one, but installing this plugin doesn't pull in the other — they're independent.

Practical implications for this repo:

- This repo carries only `.claude-plugin/plugin.json` — the per-plugin manifest Claude Code reads after install. There is no `marketplace.json` here; the marketplace lives in the `deriva-plugins` repo.
- `bump-version` rewrites `plugin.json` (and the `[tool.bumpversion] current_version` in `pyproject.toml`). It does **not** touch the meta-marketplace's pin — see "Bumping the meta-marketplace" under Release Process for the manual follow-up.
- The skill list is **auto-discovered** by Claude Code from `skills/*/SKILL.md` in the cloned repo — no enumeration is needed in either `plugin.json` or the meta-marketplace's `marketplace.json`. Add a skill by creating `skills/<name>/SKILL.md`; it loads on the next plugin update.

## Gotchas

- **Description field is critical** — the `description` in SKILL.md frontmatter controls when Claude auto-invokes the skill. Poorly written descriptions cause false triggers or missed triggers.
- **No build step** — skills are pure Markdown + optional scripts. Changes take effect immediately when loaded locally.
- **Release requires tag** — the workflow only triggers on `v*.*.*` tags pushed to origin. Commits alone won't create a release.
- **Skills are auto-discovered, not enumerated** — Claude Code walks `skills/*/SKILL.md` in the cloned plugin repo at install time. Neither this repo's `plugin.json` nor the meta-marketplace's `marketplace.json` lists individual skills. Adding a new skill is just `mkdir skills/<name> && touch skills/<name>/SKILL.md` (with valid frontmatter); it'll appear on the next plugin update without touching any manifest.
- **Eval workspace dirs would auto-discover as skills if they had a SKILL.md** — `evals/<skill>/iteration-*/` directories live under `evals/`, not `skills/`, so auto-discovery won't pick them up. But don't accidentally drop a `SKILL.md` into `skills/` for a workspace artifact, or it will load.
- **Scripts must handle minimal PATH** — Claude Code (especially inside the Desktop app) may not source shell profiles, so `$PATH` can be incomplete. Use `_find_uv()` pattern: try `shutil.which()` first, then check well-known locations (`~/.local/bin/`, `~/.cargo/bin/`, `/opt/homebrew/bin/`). Never assume `uv` or other tools are on PATH.
- **Marketplace cache can break** — The local git clone at `~/.claude/plugins/marketplaces/deriva-plugins/` can become corrupted (no commits, duplicate directories like `skills 2/`). If users report stale skills after enabling `autoUpdate`, check the marketplace cache health first; the fix is to delete the cache directory and let Claude Code re-clone on next restart.
- **MCP server version comes from the MCP resource** — Claude reads the running server version via the `deriva://server/version` resource (or `server_status(hostname=...)`). There is no Docker / pip inspection path; the server has to be reachable for the version to be visible.
- **`/plugin update` is unreliable** — The interactive `/plugin update` command does not always work. The supported update path is `autoUpdate: true` in `~/.claude/settings.json` + restart Claude Code.
- **Skill names must be unique** — the directory name under `skills/` is the skill identifier. Renaming a directory changes the `/deriva:` command.
- **Cross-references matter** — when renaming or removing a skill, grep for its name across all other skills' `SKILL.md` and `references/*.md` files. Pay special attention to cross-references into `deriva-ml-skills` — those land at `/deriva-ml:<skill>` and are informational (the user may not have that plugin installed).
- **`[tool.bumpversion]` config required** — `bump-version` wraps `bump-my-version` which needs `[tool.bumpversion]` in `pyproject.toml` with `tag = true` and `commit = true`. Without it, no tag or commit is created. See `deriva-mcp/pyproject.toml` for the reference config.
- **Never use `bump-my-version` directly** — always use `uv run bump-version patch|minor|major` which is the DerivaML CLI wrapper. Using `bump-my-version bump` directly bypasses project-specific logic.
