# Versioning and Updates for the Deriva Ecosystem

When errors start happening "out of nowhere," a version mismatch between the three core Deriva components is a common cause. This reference covers how to check installed versions, how to find the latest, and how to update each one. The parent `SKILL.md` covers the error-troubleshooting surface; come here when the diagnosis is "something is out of sync between deriva-py, deriva-mcp-core, and the deriva plugin."

## The three components

The Deriva ecosystem you interact with through this plugin is three separately-versioned things, each with its own update path:

- **`deriva-py`** — the Python client library, installed in your project venv.
- **`deriva-mcp-core`** — the MCP server (the running process Claude talks to).
- **`deriva` plugin** — this Claude Code plugin (the marketplace-installed package that ships these skills).

There is no unified update command. Each lives in a different world (Python packaging, server deployment, Claude Code marketplace) with its own update mechanics.

## Check installed versions

| Component | How to check installed version |
|---|---|
| **deriva-mcp-core** (the MCP server) | `server_status(hostname=...)` — returns the running framework version plus the list of loaded plugins. Or read the `deriva://server/version` resource directly. |
| **deriva-py** (the Python client) | `uv pip show deriva-py` (in your project venv), or `python -c "import deriva; print(deriva.__version__)"` |
| **`deriva` plugin** (this Claude Code plugin) | `cat ~/.claude/plugins/cache/deriva-plugins/deriva/*/plugin.json` — the `version` field |

## Check whether a newer version exists

The latest release of each component is the most recent tag at:

- **deriva-mcp-core**: https://github.com/informatics-isi-edu/deriva-mcp-core/releases
- **deriva-py**: https://pypi.org/project/deriva/ (or the GitHub releases page)
- **deriva-skills** (this plugin): https://github.com/informatics-isi-edu/deriva-skills/releases

## Update each component

| Component | Update path |
|---|---|
| **`deriva` plugin** | Enable `"autoUpdate": true` in `~/.claude/settings.json` for the `deriva-plugins` marketplace, then restart Claude Code. The new version is picked up automatically. (The interactive `/plugin` menu also works for one-off updates.) |
| **deriva-mcp-core (Docker, most common)** | `docker pull ghcr.io/informatics-isi-edu/deriva-mcp-core:latest && docker restart deriva-mcp-core`. The MCP connection drops mid-restart; reconnect from Claude after the server comes back. |
| **deriva-mcp-core (native install)** | In the project where the server is installed: `uv lock --upgrade-package deriva-mcp-core && uv sync`, then restart the server. |
| **deriva-py** | In your project: `uv lock --upgrade-package deriva-py && uv sync` |

## Why no single "update everything" command

The three components live in different worlds: the plugin updates through Claude Code's marketplace machinery, the MCP server updates through whatever deployment owns it (Docker, native install, etc.), and the Python library updates through standard Python tooling. The MCP server can't be restarted from inside Claude (the connection is stateful and would die mid-update), so MCP updates are inherently a user-driven step.

Keep all three reasonably current together. Bumping just one occasionally produces "this tool exists in the server but the plugin doesn't know about it" errors, or vice versa — the surfaces are designed to evolve together.

## When errors might point at a version issue

Some error patterns are specific to version mismatch:

- **"Tool not found"** when the LLM tries to call an MCP tool whose name is documented in the plugin's skill — the server is older than the plugin (server doesn't have the tool yet).
- **"Unknown parameter"** in a successful tool call — the plugin's documented signature is newer than the server's.
- **Plugin documentation references a workflow that doesn't work** — the plugin is older than the server (server has changed; plugin docs still describe the old API).
- **`deriva-py` errors that mention a method that should exist** — the project's locked deriva-py is older than what the catalog deployment expects.

The general rule: if errors started right after an update of one component, verify the other two are also current. A server upgrade may have introduced a tool the plugin's docs don't yet cover; a plugin update may reference a server feature the running server doesn't have yet.
