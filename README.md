# Deriva Skills Plugin

[Claude Code](https://claude.ai/claude-code) skills plugin for working with [Deriva](https://github.com/informatics-isi-edu/deriva-py) catalogs via [`deriva-mcp-core`](https://github.com/informatics-isi-edu/deriva-mcp-core). Provides 14 skills covering schema operations, vocabulary management, query patterns, Chaise display customization, and generic catalog troubleshooting.

This is the **tier-1** skills plugin — the surface that works on any Deriva catalog. For DerivaML ML workflows (datasets, executions, features, experiments, model development), additionally install the companion [`deriva-ml-skills`](https://github.com/informatics-isi-edu/deriva-ml-skills) plugin (tier-2).

## Installation

```bash
# Add the marketplace (one-time)
/plugin marketplace add informatics-isi-edu/deriva-skills

# Install the deriva plugin
/plugin install deriva
```

For DerivaML workflows, additionally:

```bash
/plugin marketplace add informatics-isi-edu/deriva-ml-skills
/plugin install deriva-ml
```

## Updating

```
/plugin install deriva
```

## Available Skills

### User commands

These are the skills you invoke directly by typing `/deriva:<name>` or by asking Claude something that maps to one of them. Each one is a real tool that does work on a catalog.

| Category | Command | Description |
|----------|-------|-------------|
| **Onboarding** | `/deriva:getting-started` | Five-step orientation for a new user or a new catalog: connection → explore schema → look at data → small safe mutation → load data |
| **Catalog schema** | `/deriva:create-table` | Create domain tables with columns and foreign keys |
| | `/deriva:customize-display` | Customize Chaise web UI using MCP annotation tools |
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

The DerivaML-specific surface (datasets, executions, features, experiments, model development, Hydra-zen configs) lives in the companion [`deriva-ml-skills`](https://github.com/informatics-isi-edu/deriva-ml-skills) plugin. It depends on this plugin as its tier-1 foundation; install both for full ML workflow support.

When the deriva-ml plugin is loaded, **its abstractions take precedence over the raw catalog surface this plugin documents**: Datasets, Workflows, Executions, Features, and Asset_Type vocabularies are first-class DerivaML concepts (stored as Deriva tables underneath) — use the `/deriva-ml:` skills and the deriva-ml Python API for them, not the raw `insert_records` / `update_record` core tools.

## Development

Load the plugin from a local path without installing:

```bash
claude --plugin-dir /path/to/deriva-skills
```

## Related Projects

- [`deriva-mcp-core`](https://github.com/informatics-isi-edu/deriva-mcp-core) — Core MCP framework + generic Deriva catalog tools
- [`deriva-py`](https://github.com/informatics-isi-edu/deriva-py) — Python SDK for Deriva scientific data management
- [`deriva-ml-skills`](https://github.com/informatics-isi-edu/deriva-ml-skills) — Companion tier-2 plugin: DerivaML ML workflow skills
- [`deriva-ml-mcp`](https://github.com/informatics-isi-edu/deriva-ml-mcp) — DerivaML MCP plugin (loaded by deriva-mcp-core)
- [`deriva-ml`](https://github.com/informatics-isi-edu/deriva-ml) — Core library for ML workflows on Deriva

## License

Apache 2.0
