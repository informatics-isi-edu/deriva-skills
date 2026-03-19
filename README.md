# Deriva Skills Plugin

[Claude Code](https://claude.ai/claude-code) skills plugin for working with [Deriva](https://github.com/informatics-isi-edu/deriva-py) catalogs and [DerivaML](https://github.com/informatics-isi-edu/deriva-ml) ML workflows.

This plugin provides 30+ skills that guide Claude through common Deriva and DerivaML workflows, including dataset management, ML execution, experiment configuration, and catalog operations.

## Installation

```bash
# Add the marketplace (one-time)
/plugin marketplace add informatics-isi-edu/deriva-skills

# Install the plugin
/plugin install deriva
```

## Updating

```
/plugin install deriva
```

Or check your entire DerivaML ecosystem:

```
/deriva:check-deriva-versions
```

## Available Skills

**User-invocable** — invoke with `/deriva:<skill-name>`:

| Category | Skill | Description |
|----------|-------|-------------|
| **Catalog** | `/deriva:create-table` | Create domain tables with columns and foreign keys |
| | `/deriva:create-feature` | Create and populate features for ML labeling |
| | `/deriva:customize-display` | Customize Chaise web UI using MCP annotation tools |
| | `/deriva:use-annotation-builders` | Python type-safe annotation builder classes |
| | `/deriva:manage-vocabulary` | Create and manage controlled vocabularies |
| | `/deriva:query-catalog-data` | Query and explore data in a Deriva catalog |
| **Datasets** | `/deriva:create-dataset` | Create, populate, and split datasets for ML |
| | `/deriva:prepare-training-data` | Prepare datasets for ML training via denormalization |
| | `/deriva:debug-bag-contents` | Diagnose missing data in dataset bag exports |
| **Execution** | `/deriva:run-ml-execution` | ML execution lifecycle with provenance tracking |
| | `/deriva:work-with-assets` | Asset lookup, provenance, and management |
| **Experiments** | `/deriva:configure-experiment` | Set up DerivaML experiment project structure |
| | `/deriva:run-experiment` | Pre-flight checklist and CLI for deriva-ml-run |
| | `/deriva:write-hydra-config` | Write and validate hydra-zen config files |
| **Notebooks** | `/deriva:setup-notebook-environment` | Set up Jupyter environment for DerivaML |
| | `/deriva:run-notebook` | Develop and run notebooks with execution tracking |
| **Standards** | `/deriva:coding-guidelines` | DerivaML project coding standards |
| **Maintenance** | `/deriva:check-deriva-versions` | Check ecosystem components against upstream and update |
| **Visualization** | `/deriva:browse-erd` | Interactive ERD browser for catalog schemas |

**Auto-invoked** — Claude loads these automatically when relevant:

| Skill | When it activates |
|-------|-------------------|
| `semantic-awareness` | Before creating any new catalog entity |
| `generate-descriptions` | When creating entities without descriptions |
| `maintain-experiment-notes` | After significant experiment design decisions |
| `dataset-versioning` | When working with dataset versions |
| `catalog-operations-workflow` | When performing catalog mutations |
| `api-naming-conventions` | When writing DerivaML Python code |
| `troubleshoot-execution` | When any execution fails or produces unexpected results |

## Development

Load the plugin from a local path without installing:

```bash
claude --plugin-dir /path/to/deriva-skills
```

## Related Projects

- [Deriva MCP Server](https://github.com/informatics-isi-edu/deriva-mcp) — MCP server for Deriva catalog operations
- [DerivaML](https://github.com/informatics-isi-edu/deriva-ml) — Core library for ML workflows on Deriva
- [Deriva](https://github.com/informatics-isi-edu/deriva-py) — Python SDK for Deriva scientific data management

## License

Apache 2.0
