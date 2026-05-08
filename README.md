# Deriva Skills Plugin

[Claude Code](https://claude.ai/claude-code) skills plugin for working with [Deriva](https://github.com/informatics-isi-edu/deriva-py) catalogs via [`deriva-mcp-core`](https://github.com/informatics-isi-edu/deriva-mcp-core). Provides 12 skills covering schema operations, vocabulary management, query patterns, Chaise display customization, and generic catalog troubleshooting.

The plugin is self-contained — install it on its own and it works on any Deriva catalog. A separate companion plugin, [`deriva-ml-skills`](https://github.com/informatics-isi-edu/deriva-ml-skills), exists for users doing DerivaML ML workflows (datasets, executions, features, experiments, model development); see [DerivaML workflows](#derivaml-workflows) below.

## Installation

Install via the unified [`deriva-plugins`](https://github.com/informatics-isi-edu/deriva-plugins) marketplace:

```bash
# Add the marketplace (one-time) — covers both deriva and deriva-ml
/plugin marketplace add informatics-isi-edu/deriva-plugins

# Install this plugin
/plugin install deriva

# For DerivaML workflows, also install the deriva-ml plugin
/plugin install deriva-ml
```

> **Migrating from the old per-repo marketplace?** Earlier versions of this plugin were installed via `/plugin marketplace add informatics-isi-edu/deriva-skills`. That single-plugin marketplace has been retired in favor of the unified one above. To migrate, first remove the old cache:
> ```
> /plugin marketplace remove deriva-plugins
> ```
> (the old per-repo marketplace was *also* internally named `deriva-plugins`, so the cache name collides — removing it before re-adding ensures Claude Code re-clones from the new repo). Then run the two commands above.

## Updating

Enable `"autoUpdate": true` in `~/.claude/settings.json` for the `deriva-plugins` marketplace and restart Claude Code; new versions are picked up automatically.

## Available Skills

### User commands

These are the skills you invoke directly by typing `/deriva:<name>` or by asking Claude something that maps to one of them. Each one is a real tool that does work on a catalog.

| Category | Command | Description |
|----------|-------|-------------|
| **Onboarding** | `/deriva:getting-started` | Five-step orientation for a new user or a new catalog: connection → explore schema → look at data → small safe mutation → load data |
| **Catalog schema** | `/deriva:create-table` | Create domain tables with columns and foreign keys |
| | `/deriva:customize-display` | Customize Chaise web UI using MCP annotation tools (interactive path) |
| | `/deriva:use-annotation-builders` | Type-safe Python builder classes for production deployment scripts (Python path) |
| | `/deriva:manage-vocabulary` | Create and manage controlled vocabularies |
| | `/deriva:entity-naming` | Naming conventions for schemas, tables, columns, and vocabulary terms |
| **Data loading** | `/deriva:load-data` | Insert rows, batch-load CSV/JSON, upload assets to Hatrac (MCP tool, `deriva-upload-cli`, or `DerivaUpload` Python class), update, delete |
| **Querying** | `/deriva:query-catalog-data` | Query and explore data in a Deriva catalog (cold-start exploration via `rag_search`, then row-level queries) |
| **Troubleshooting** | `/deriva:troubleshoot-deriva-errors` | Generic catalog errors (auth, permissions, invalid RID, missing record, generic vocab term) — also covers the version-and-update path for deriva-py / deriva-mcp-core / deriva plugin |

### Auto-invoked behaviors (not commands)

The plugin also ships three skills that **Claude loads on its own** when the situation calls for them. They do not appear in the `/deriva:` slash-command picker, and you should not type them as commands — they're internal disciplines that shape how Claude handles catalog work, not tools you reach for directly.

| Skill | When Claude loads it |
|-------|----------------------|
| `deriva-context` | Always — establishes the plugin's concept index and the modeling checklist on every conversation |
| `semantic-awareness` | Before Claude creates any new catalog entity (table, vocabulary, term) — enforces the find-before-you-create discipline |
| `generate-descriptions` | When Claude is about to create a catalog entity without a user-supplied description — auto-drafts one from context |

You'll see their effects in Claude's behavior (it asks "did you mean this existing table?" before creating one; it proposes a description when you didn't write one); you won't see them as commands you can invoke.

## DerivaML workflows

DerivaML-specific work (datasets, executions, features, experiments, model development, Hydra-zen configs) is covered by a separate companion plugin, [`deriva-ml-skills`](https://github.com/informatics-isi-edu/deriva-ml-skills), available from the same `deriva-plugins` marketplace. It builds on the same Deriva ecosystem this plugin uses; install both if your work spans both surfaces.

When the deriva-ml plugin is loaded alongside this one, **its abstractions take precedence over the raw catalog surface this plugin documents**: Datasets, Workflows, Executions, Features, and Asset_Type vocabularies are first-class DerivaML concepts (stored as Deriva tables underneath) — use the `/deriva-ml:` skills and the deriva-ml Python API for them, not the raw `insert_records` / `update_record` core tools. This rule only matters if you have the deriva-ml plugin installed; without it, this plugin's catalog primitives are the right surface for everything.

## Development

Load the plugin from a local path without installing:

```bash
claude --plugin-dir /path/to/deriva-skills
```

## Related Projects

- [`deriva-mcp-core`](https://github.com/informatics-isi-edu/deriva-mcp-core) — Core MCP framework + generic Deriva catalog tools
- [`deriva-py`](https://github.com/informatics-isi-edu/deriva-py) — Python SDK for Deriva scientific data management
- [`deriva-ml-skills`](https://github.com/informatics-isi-edu/deriva-ml-skills) — Companion plugin for DerivaML ML workflow skills (datasets, executions, features, experiments)
- [`deriva-ml-mcp`](https://github.com/informatics-isi-edu/deriva-ml-mcp) — DerivaML MCP plugin (loaded by deriva-mcp-core)
- [`deriva-ml`](https://github.com/informatics-isi-edu/deriva-ml) — Core library for ML workflows on Deriva

## License

Apache 2.0
