---
name: check-deriva-versions
description: "Check if the DerivaML ecosystem (deriva-ml, skills plugin, MCP server) is up to date and offer to update outdated components. Use when the user asks about versions, updates, or whether their environment is current. Triggers on: 'check versions', 'am I up to date', 'update deriva', 'what version', 'upgrade packages'."
disable-model-invocation: true
---

# Check and Update DerivaML Ecosystem

Check whether the user's DerivaML components are up to date, then offer to update each outdated component.

## Workflow

### Step 1: Run the version check

```bash
python <skill-dir>/scripts/check_versions.py --json
```

Use `--json` to get structured output you can parse. The script checks three components:

| Component | What it checks | How it detects updates |
|-----------|---------------|----------------------|
| **deriva-ml** | Installed Python package vs latest GitHub release tag | Compares semver versions |
| **skills** | Plugin cache version vs latest `deriva-skills` GitHub release tag | Compares semver versions |
| **mcp-server** | Docker container or native install vs latest available | Compares image digests or semver versions |

### Step 2: Present results as a summary table

Parse the JSON and show the user a table like:

| Component | Status | Installed | Latest |
|-----------|--------|-----------|--------|
| deriva-ml | UP TO DATE | 1.25.1 | v1.25.1 |
| skills | OUTDATED | 0.12.1 | v0.12.2 |
| mcp-server | UP TO DATE | (image digest matches) | latest |

Map `up_to_date` values: `true` = "UP TO DATE", `false` = "OUTDATED", `null` = "UNKNOWN".

If everything is up to date, say so and stop. Otherwise, proceed to Step 3.

### Step 3: Offer to update each outdated component

For each component where `up_to_date` is `false`, offer to update it. Handle each component differently:

#### deriva-ml (automated)

Offer to run the update. If the user agrees:

```bash
python <skill-dir>/scripts/check_versions.py --component deriva-ml --update
```

This runs `uv lock --upgrade-package deriva-ml && uv sync` (or pip equivalent) and verifies the new version.

#### skills (user action required)

The skills plugin can only be updated through a Claude Code slash command — it cannot be automated by a script. Claude Code manages its plugin cache and manifest with internal locking that external processes cannot safely bypass. Tell the user:

> The skills plugin is outdated (installed X, latest Y). To update, run `/plugin update deriva` in Claude Code.

After they've run it, you can re-check with `--component skills` to confirm.

#### mcp-server (automated, but confirm first)

The MCP server update briefly interrupts the connection to Deriva MCP tools. Ask the user before proceeding. If they agree:

```bash
python <skill-dir>/scripts/check_versions.py --component mcp-server --update
```

The script handles the appropriate update command based on deployment mode:
- **Registry Docker** (e.g., `ghcr.io/.../deriva-mcp:latest`): `docker pull` + `docker restart`
- **Local dev Docker**: `docker compose up -d --build`
- **Native install**: `uv lock --upgrade-package deriva-mcp && uv sync`

Warn the user that MCP tools will be briefly unavailable during the restart.

### Step 4: Confirm results

After updates complete, re-run the check to confirm everything is current:

```bash
python <skill-dir>/scripts/check_versions.py
```

## Interpreting Status Values

- **UP TO DATE** — No action needed
- **OUTDATED** — Newer version available; offer to update
- **UPDATED** — Successfully updated (shown after `--update`)
- **UNKNOWN** — Could not determine status (network issue, not installed, etc.)
- **Dev version** — Installed from git HEAD, at or ahead of latest release. Normal for developers working on the library itself.

## Checking a Single Component

To check or update just one component:

```bash
python <skill-dir>/scripts/check_versions.py --component deriva-ml --json
python <skill-dir>/scripts/check_versions.py --component mcp-server --update
```

Valid component names: `deriva-ml`, `skills`, `mcp-server`.
