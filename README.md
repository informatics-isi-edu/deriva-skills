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

Or check the entire core Deriva ecosystem:

```
/deriva:check-deriva-versions
```

If you also have the deriva-ml plugin installed, run the tier-2 sibling afterward:

```
/deriva-ml:check-deriva-ml-versions
```

## Available Skills

**User-invocable** — invoke with `/deriva:<skill-name>`:

| Category | Skill | Description |
|----------|-------|-------------|
| **Catalog schema** | `/deriva:create-table` | Create domain tables with columns and foreign keys |
| | `/deriva:customize-display` | Customize Chaise web UI using MCP annotation tools |
| | `/deriva:manage-vocabulary` | Create and manage controlled vocabularies |
| | `/deriva:query-catalog-data` | Query and explore data in a Deriva catalog |
| | `/deriva:route-catalog-schema` | Router for catalog structure / data exploration tasks |
| **Troubleshooting** | `/deriva:troubleshoot-deriva-errors` | Generic catalog errors (auth, permissions, invalid RID, missing record, generic vocab term) |
| **Maintenance** | `/deriva:check-deriva-versions` | Check the core Deriva ecosystem (deriva-py, deriva-mcp-core, deriva plugin) |

**Auto-invoked** — Claude loads these automatically when relevant:

| Skill | When it activates |
|-------|-------------------|
| `semantic-awareness` | Before creating any new catalog entity |
| `generate-descriptions` | When creating entities without descriptions |

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
