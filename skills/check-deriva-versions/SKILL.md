---
name: check-deriva-versions
description: "Check if the core Deriva ecosystem (deriva-py client, deriva-mcp-core MCP server, deriva-skills plugin) is up to date and offer to update outdated components. Use when the user asks about versions, updates, or whether their environment is current. Triggers on: 'check versions', 'am I up to date', 'update deriva', 'what version', 'upgrade packages'."
disable-model-invocation: true
---

# Check and Update Core Deriva Ecosystem

Check whether the user's core Deriva components are up to date, then offer to update each outdated component.

This skill covers the core Deriva ecosystem: the `deriva-py` Python client library, the `deriva-mcp-core` MCP server, and this Claude Code plugin (`deriva-skills`). All three should be kept current together.

**Important:** Skills (including this one) are a Claude Code feature. Claude Desktop does not have plugins or skills — it only has MCP servers. If running in Claude Desktop, you can only check the MCP server version.

## Components to Check

| Component | What | How to check | Who can update |
|-----------|------|-------------|----------------|
| **deriva-skills** | The `deriva` Claude Code plugin (this plugin) | Script (reads plugin cache) | Automated (cache refresh + restart) |
| **deriva-mcp-core** | Running MCP server (the core framework) | `deriva://server/version` resource | User (restart required) |

> **Note:** A `deriva-py` Python-client version check is not yet implemented in this skill. Until the check function lands, verify deriva-py manually via your project's package manager (`uv pip show deriva-py` or `pip show deriva`).

## Workflow

### Step 1: Check deriva-skills plugin version

```bash
python3 <skill-dir>/scripts/check_versions.py --component skills --json
```

This reads the plugin cache at `~/.claude/plugins/cache/deriva-plugins/` and compares against the latest GitHub release tag for `informatics-isi-edu/deriva-skills`. No project venv needed — uses system Python.

**Skip this in Claude Desktop** — Desktop doesn't have plugins.

### Step 2: Check MCP server version

Read the `deriva://server/version` resource. This returns the running server's version directly — no Docker inspection or pip needed. **Note:** This requires an active MCP connection to the Deriva MCP server. If the MCP server is not configured or not running, this resource will not be available.

The running server is `deriva-mcp-core`; loaded plugins are listed separately in the same response. Each plugin reports its own version through its own channels and is not part of this skill's scope.

If the MCP server is not reachable (resource read fails), report as "UNKNOWN — MCP server not running".

### Step 3: Present results

Show a summary table:

| Component | Status | Installed | Latest |
|-----------|--------|-----------|--------|
| deriva-py | UP TO DATE | 1.7.7 | v1.7.7 |
| deriva-skills | OUTDATED | 0.12.1 | v0.12.2 |
| deriva-mcp-core | UP TO DATE | 0.5.1 | v0.5.1 |

If everything is up to date, say so and stop. Otherwise, proceed to Step 5.

### Step 4: Offer updates for outdated components

#### deriva-py (automated)

```bash
uv run python3 <skill-dir>/scripts/check_versions.py --component deriva-py --update
```

This runs `uv lock --upgrade-package deriva-py && uv sync` and verifies the new version.

#### deriva-skills (Claude Code only)

Run the update script, which refreshes the local marketplace cache (git pull, or re-clone if broken):
```bash
python3 <skill-dir>/scripts/check_versions.py --component skills --update
```

The script checks whether `autoUpdate` is enabled in `~/.claude/settings.json` and adjusts its advice:

- **autoUpdate enabled**: Tell the user to restart Claude Code — the new version will be picked up automatically.
- **autoUpdate not enabled**: Suggest the user enable it by adding `"autoUpdate": true` to `extraKnownMarketplaces.deriva-plugins` in settings.json, then restart. Alternatively, they can use the interactive `/plugin` menu to update manually.

**Note:** `/plugin update` opens an interactive menu — it cannot be used as a scripted CLI command.

#### deriva-mcp-core (user action — restart required)

The MCP server cannot be updated by Claude because restarting it breaks the MCP connection mid-session. Tell the user how to update based on their deployment:

- **Docker** (most common): `docker pull ghcr.io/informatics-isi-edu/deriva-mcp-core:latest && docker restart deriva-mcp-core`
- **Native install**: `cd <project-dir> && uv lock --upgrade-package deriva-mcp-core && uv sync`, then restart the server

### Step 5: Confirm

After updates, re-run the relevant checks to confirm everything is current.

## Status Values

- **UP TO DATE** — No action needed
- **OUTDATED** — Newer version available; offer to update
- **UPDATED** — Successfully updated (shown after `--update`)
- **UNKNOWN** — Could not determine status (not installed, server not running, network issue)
- **Dev version** — Installed from git HEAD, at or ahead of latest release. Normal for developers working on the library itself.
