---
name: check-deriva-versions
description: "Check if the DerivaML ecosystem (deriva-ml, skills plugin, MCP server) is up to date and offer to update outdated components. Use when the user asks about versions, updates, or whether their environment is current. Triggers on: 'check versions', 'am I up to date', 'update deriva', 'what version', 'upgrade packages'."
disable-model-invocation: true
---

# Check and Update DerivaML Ecosystem

Check whether the user's DerivaML components are up to date, then offer to update each outdated component.

## Workflow

### Step 1: Find the project environment and run the check

The script must run in the **project's Python environment** to accurately check the `deriva-ml` version. Follow this sequence:

1. **Check if CWD has a `pyproject.toml`** — if yes, run from here:
   ```bash
   uv run python3 <skill-dir>/scripts/check_versions.py --json
   ```

2. **If no `pyproject.toml` in CWD**, ask the user where their DerivaML project is:
   > "I need to check the `deriva-ml` version in your project's virtual environment. What directory is your DerivaML project in?"

   Then `cd` to that directory and run with `uv run python3`.

3. **If the user doesn't have a project** (e.g., Claude Desktop, or they only use MCP tools), run with system Python:
   ```bash
   python3 <skill-dir>/scripts/check_versions.py --json
   ```
   The script will report "Not installed" for `deriva-ml`, which is expected — they interact with Deriva through the MCP server, not a local Python install.

**Why this matters:** Running the script with the wrong Python will either report "Not installed" (misleading) or report the wrong version. Always run in the project's `.venv` when one exists.

Use `--json` to get structured output you can parse. The script checks two components:

| Component | What it checks | How it detects updates |
|-----------|---------------|----------------------|
| **deriva-ml** | Installed Python package vs latest GitHub release tag | Compares semver versions |
| **skills** | Plugin cache version vs latest `deriva-skills` GitHub release tag | Compares semver versions |

**Note:** The script only checks `deriva-ml` and `skills`. For the MCP server version, use the MCP resource directly (see Step 1b).

### Step 1b: Check MCP server version via MCP resource

Read the `deriva://server/version` resource to get the running MCP server's version. Then compare it against the latest GitHub release tag for `informatics-isi-edu/deriva-mcp`.

This is more accurate than Docker inspection because it checks the **actually running server**, regardless of whether it's deployed via Docker, native install, or any other method.

If the MCP server is not running (resource read fails), report as "UNKNOWN — MCP server not reachable".

### Step 2: Present results as a summary table

Combine the script output (deriva-ml, skills) with the MCP resource result into a single table:

| Component | Status | Installed | Latest |
|-----------|--------|-----------|--------|
| deriva-ml | UP TO DATE | 1.25.1 | v1.25.1 |
| skills | OUTDATED | 0.12.1 | v0.12.2 |
| mcp-server | UP TO DATE | 0.13.1 | v0.13.1 |

Map `up_to_date` values: `true` = "UP TO DATE", `false` = "OUTDATED", `null` = "UNKNOWN".

If everything is up to date, say so and stop. Otherwise, proceed to Step 3.

### Step 3: Offer to update each outdated component

For each component where `up_to_date` is `false`, offer to update it. Handle each component differently:

#### deriva-ml (automated)

Offer to run the update. If the user agrees:

```bash
uv run python3 <skill-dir>/scripts/check_versions.py --component deriva-ml --update
```

This runs `uv lock --upgrade-package deriva-ml && uv sync` (or pip equivalent) and verifies the new version.

#### skills (two-step: automated refresh + user command)

The update script first refreshes the local marketplace cache (`git pull`), which fixes a common issue where `/plugin update` reports "already at latest" despite newer versions on GitHub. Then the user must run the final install step manually:

```bash
uv run python3 <skill-dir>/scripts/check_versions.py --component skills --update
```

This refreshes the cache. Then tell the user:

> Marketplace cache refreshed. Now run `/plugin update deriva` in Claude Code to complete the update.

The final `/plugin update` step cannot be automated because Claude Code manages its plugin manifest with internal locking. After they've run it, re-check with `--component skills` to confirm.

#### mcp-server (manual — tell the user)

The MCP server cannot be updated by Claude because restarting it breaks the MCP connection mid-session. Tell the user how to update based on their deployment:

- **Registry Docker** (most common): `docker pull ghcr.io/informatics-isi-edu/deriva-mcp:latest && docker restart deriva-mcp`
- **Local dev Docker**: `cd deriva-mcp && docker compose -f docker-compose.mcp.yaml -f docker-compose.dev.yaml up -d --build`
- **Native install**: `cd deriva-mcp && uv lock --upgrade-package deriva-mcp && uv sync`

Warn that MCP tools will be briefly unavailable during the restart.

### Step 4: Confirm results

After updates complete, re-run the check to confirm everything is current:

```bash
uv run python3 <skill-dir>/scripts/check_versions.py
```

## Interpreting Status Values

- **UP TO DATE** — No action needed
- **OUTDATED** — Newer version available; offer to update
- **UPDATED** — Successfully updated (shown after `--update`)
- **UNKNOWN** — Could not determine status (network issue, not installed, etc.)
- **Dev version** — Installed from git HEAD, at or ahead of latest release. Normal for developers working on the library itself.

## Checking a Single Component

To check or update just one component via the script:

```bash
uv run python3 <skill-dir>/scripts/check_versions.py --component deriva-ml --json
uv run python3 <skill-dir>/scripts/check_versions.py --component skills --json
```

Valid script component names: `deriva-ml`, `skills`.

For the MCP server, read the `deriva://server/version` resource directly — no script needed.
