---
name: route-project-setup
description: "Use this skill whenever the user asks about DerivaML versions, updates, environment setup, or troubleshooting data exports — including 'check versions', 'am I up to date', 'update deriva-ml', 'bag export problems', 'missing data in bag', 'materialization issues'. Also covers setting up the DerivaML development environment: installing Jupyter kernels, configuring nbstripout, authenticating with Deriva/Globus, setting up pyproject.toml, managing uv dependencies, and establishing coding standards and Git workflow."
---

# Project Setup — Environment, Versions, and Standards

You are a router skill. Based on the user's request, load the appropriate specialized skill.


## Prerequisite: Connect to a Catalog

Most skills routed from here require an active catalog connection:

```
connect_catalog(hostname="...", catalog_id="...")
```

If already connected (check `deriva://catalog/connections`), skip this step.


## Routing Rules

Analyze the user's intent and read the matching skill:

### Environment setup for notebooks
- **Setting up Jupyter environment, installing kernels, uv sync --group=jupyter, configuring nbstripout, Deriva/Globus authentication, PyTorch dependencies** → Read and follow `../setup-notebook-environment/SKILL.md`

### Version checking and updates
- **Checking if DerivaML packages are up to date, updating packages, version queries, deriva-ml version, deriva-mcp MCP server version, deriva-mcp skills plugin version** → Read and follow `../check-deriva-versions/SKILL.md`

### Coding standards and project setup
- **Project setup from scratch, pyproject.toml structure, uv configuration, Git workflow, Google docstrings, ruff linting, type hints, version bumping** → Read and follow `../coding-guidelines/SKILL.md`

### Troubleshooting data exports
- **Missing data in downloaded dataset bags, FK traversal issues, materialization problems, bag export timeouts, validate_dataset_bag** → Read and follow `../debug-bag-contents/SKILL.md`

## Important

After identifying the correct skill, read its SKILL.md file completely and follow its instructions. Do not attempt to handle the request from this routing skill alone.
