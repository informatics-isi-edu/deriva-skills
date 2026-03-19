---
name: route-run-workflows
description: "Use this skill for configuring DerivaML experiments, running notebooks, writing Hydra-Zen configs, creating new model functions, and troubleshooting execution failures. For running experiments and the execution lifecycle itself, use the execution-lifecycle skill directly. Choose this router when users want to configure, create notebooks, write configs, or debug ML workflows."
---

# ML Workflows — Experiments, Notebooks, Executions, and Configuration

You are a router skill. Based on the user's request, load the appropriate specialized skill.


## Prerequisite: Connect to a Catalog

Most skills routed from here require an active catalog connection:

```
connect_catalog(hostname="...", catalog_id="...")
```

If already connected (check `deriva://catalog/connections`), skip this step.


## Routing Rules

Analyze the user's intent and read the matching skill:

### Preparing data for ML training
- **Restructuring assets for PyTorch/TensorFlow, building training DataFrames, DatasetBag API, value selectors for multi-annotator data, file format conversion during restructuring** → Read and follow `../prepare-training-data/SKILL.md`

### Running notebooks
- **Creating, developing, or running DerivaML Jupyter notebooks, notebook structure, run_notebook(), deriva-ml-run-notebook, papermill parameters** → Read and follow `../run-notebook/SKILL.md`

### Configuration
- **Writing or editing Hydra-Zen config files — DatasetSpecConfig, AssetSpecConfig, builds(), experiment_config, multirun_config, with_description, notebook_config** → Read and follow `../write-hydra-config/SKILL.md`
- **Setting up experiment project structure, understanding config composition, hydra defaults, DerivaModelConfig** → Read and follow `../configure-experiment/SKILL.md`

### Creating new models
- **Creating a new model function, scaffolding model code, wiring a model into configs/workflows/experiments** → Read and follow `../new-model/SKILL.md`

### Troubleshooting
- **Any execution failure, error, stuck status, authentication issue, upload timeout, missing files, version mismatch, permission denied** → Read and follow `../troubleshoot-execution/SKILL.md`

## Important

After identifying the correct skill, read its SKILL.md file completely and follow its instructions. Do not attempt to handle the request from this routing skill alone.
