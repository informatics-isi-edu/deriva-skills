# CLAUDE.md

This file provides guidance to Claude Code when working with the deriva-skills codebase.

## Project Overview

Claude Code plugin providing 33 skills for DerivaML workflows. Skills are organized as Markdown documents with optional Python scripts — no package build step required.

## Commands

```bash
# Load locally for development (no install needed)
claude --plugin-dir /path/to/deriva-skills

# Install from marketplace
/plugin install deriva

# Release process — always use bump-version from deriva-ml
bump-version patch    # v0.12.1 -> v0.12.2
bump-version minor    # v0.12.2 -> v0.13.0
bump-version major    # v0.13.0 -> v1.0.0
# GitHub Actions: bumps version in plugin.json + marketplace.json, commits back to main, creates archive + release

# Run version checker
python skills/check-versions/scripts/check_versions.py
python skills/check-versions/scripts/check_versions.py --update
python skills/check-versions/scripts/check_versions.py --component deriva-ml --update

# Run skill description optimizer
python skills/optimization/run_all.py
```

## Architecture

```
├── .claude-plugin/
│   ├── plugin.json           # Plugin metadata (name, version, description)
│   └── marketplace.json      # Marketplace registration
├── skills/                   # 33 skills, each in its own directory
│   ├── {skill-name}/
│   │   ├── SKILL.md          # Frontmatter (YAML) + skill content (Markdown)
│   │   ├── scripts/          # Optional Python helper scripts
│   │   └── references/       # Optional extended documentation
│   └── ...
└── .github/
    ├── workflows/release.yml # Tag-triggered release automation
    └── release-drafter.yml   # Release notes template
```

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

### Skill Types

| Type | Frontmatter | Invocation | Examples |
|------|------------|------------|----------|
| User-invocable | `disable-model-invocation: true` | `/deriva:skill-name` | create-table, run-experiment |
| Auto-invoked | `user-invocable: false` | Claude triggers automatically | semantic-awareness, generate-descriptions |
| Hybrid | (default) | Both manual and auto | maintain-experiment-notes |

### Router Skills

`route-*` skills (e.g., `route-catalog-schema`, `route-run-workflows`) are auto-invoked dispatchers that load specialized sub-skills based on the task at hand.

## Release Process

1. Commit changes
2. Run `bump-version patch|minor|major` (creates tag and pushes automatically)
3. GitHub Actions automatically:
   - Bumps version in `plugin.json` and `marketplace.json`
   - Commits version bump back to main
   - Creates `deriva-skills-{VERSION}.tar.gz` (excludes `.git`, `.github`)
   - Publishes GitHub Release with auto-generated notes
4. Users update via `/plugin install deriva`

**Never create git tags manually** — always use `bump-version` from deriva-ml.

## Gotchas

- **Description field is critical** — the `description` in SKILL.md frontmatter controls when Claude auto-invokes the skill. Poorly written descriptions cause false triggers or missed triggers.
- **No build step** — skills are pure Markdown + optional scripts. Changes take effect immediately when loaded locally.
- **Release requires tag** — the workflow only triggers on `v*.*.*` tags pushed to origin. Commits alone won't create a release.
- **Scripts must be portable** — Python scripts in `scripts/` must work in both Claude Code (full shell) and Claude Desktop (restricted environment). Use `shutil.which()` guards, no hardcoded paths, handle missing dependencies gracefully.
- **Skill names must be unique** — the directory name under `skills/` is the skill identifier. Renaming a directory changes the `/deriva:` command.
