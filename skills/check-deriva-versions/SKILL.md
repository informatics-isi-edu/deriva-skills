---
name: check-deriva-versions
description: "Check if the DerivaML ecosystem (deriva-ml, skills plugin, MCP server) is up to date and offer to update outdated components. Use when the user asks about versions, updates, or whether their environment is current. Triggers on: 'check versions', 'am I up to date', 'update deriva', 'what version', 'upgrade packages'."
disable-model-invocation: true
---

# Check and Update DerivaML Ecosystem

Check whether the user's DerivaML components are up to date, then offer to update each outdated component.

**Important:** Skills (including this one) are a Claude Code feature. Claude Desktop does not have plugins or skills — it only has MCP servers. If running in Claude Desktop, you can only check the MCP server version.

## Components to Check

| Component | What | How to check | Who can update |
|-----------|------|-------------|----------------|
| **deriva-ml** | Python library in the project's `.venv` | Script (needs project venv) | Claude (automated) |
| **skills** | Claude Code plugin | Script (reads plugin cache) | User (`/plugin update`) |
| **mcp-server** | Running MCP server | `deriva://server/version` resource | User (restart required) |

## Workflow

### Step 1: Check deriva-ml version

The script must run in the **project's Python environment**. Follow this sequence:

1. **Check if CWD has a `pyproject.toml`** — if yes, run from here:
   ```bash
   uv run python3 <skill-dir>/scripts/check_versions.py --component deriva-ml --json
   ```

2. **If no `pyproject.toml` in CWD**, ask the user:
   > "I need to check the `deriva-ml` version in your project's virtual environment. What directory is your DerivaML project in?"

   Then `cd` to that directory and run with `uv run python3`.

3. **If the user has no local project** (MCP-only workflow), skip this component — they don't have a local `deriva-ml` install to check.

### Step 2: Check skills plugin version

```bash
python3 <skill-dir>/scripts/check_versions.py --component skills --json
```

This reads the plugin cache at `~/.claude/plugins/cache/deriva-plugins/` and compares against the latest GitHub release tag. No project venv needed — uses system Python.

**Skip this in Claude Desktop** — Desktop doesn't have plugins.

### Step 3: Check MCP server version

Read the `deriva://server/version` resource. This returns the running server's version directly — no Docker inspection or pip needed.

Compare the returned version against the latest release tag for `informatics-isi-edu/deriva-mcp` (the script can check this: `python3 <skill-dir>/scripts/check_versions.py --component mcp-server --json` only checks the GitHub tag).

If the MCP server is not reachable (resource read fails), report as "UNKNOWN — MCP server not running".

### Step 4: Present results

Show a summary table:

| Component | Status | Installed | Latest |
|-----------|--------|-----------|--------|
| deriva-ml | UP TO DATE | 1.25.1 | v1.25.1 |
| skills | OUTDATED | 0.12.1 | v0.12.2 |
| mcp-server | UP TO DATE | 0.13.1 | v0.13.1 |

If everything is up to date, say so and stop. Otherwise, proceed to Step 5.

### Step 5: Offer updates for outdated components

#### deriva-ml (automated)

```bash
uv run python3 <skill-dir>/scripts/check_versions.py --component deriva-ml --update
```

This runs `uv lock --upgrade-package deriva-ml && uv sync` and verifies the new version.

#### skills (Claude Code only — two steps)

First, check if auto-update is enabled. Read `~/.claude/settings.json` and look for:
```json
"extraKnownMarketplaces": {
  "deriva-plugins": {
    "autoUpdate": true
  }
}
```

If `autoUpdate` is **not set or false**, suggest the user enable it:
> "Auto-update is not enabled for the deriva skills plugin. To enable it, add `\"autoUpdate\": true` to your `~/.claude/settings.json` under `extraKnownMarketplaces.deriva-plugins`. This will keep skills up to date automatically."

Regardless of auto-update setting, to update now:

1. Refresh the marketplace cache (fixes stale `/plugin update` results):
   ```bash
   python3 <skill-dir>/scripts/check_versions.py --component skills --update
   ```

2. Tell the user to run the final install:
   > "Marketplace cache refreshed. Now run `/plugin update deriva` in Claude Code to complete the update."

   The `/plugin update` step cannot be automated because Claude Code manages its plugin manifest with internal locking.

#### mcp-server (user action — restart required)

The MCP server cannot be updated by Claude because restarting it breaks the MCP connection mid-session. Tell the user how to update based on their deployment:

- **Docker** (most common): `docker pull ghcr.io/informatics-isi-edu/deriva-mcp:latest && docker restart deriva-mcp`
- **Native install**: `cd <project-dir> && uv lock --upgrade-package deriva-mcp && uv sync`, then restart the server

### Step 6: Confirm

After updates, re-run the relevant checks to confirm everything is current.

## Status Values

- **UP TO DATE** — No action needed
- **OUTDATED** — Newer version available; offer to update
- **UPDATED** — Successfully updated (shown after `--update`)
- **UNKNOWN** — Could not determine status (not installed, server not running, network issue)
- **Dev version** — Installed from git HEAD, at or ahead of latest release. Normal for developers working on the library itself.
