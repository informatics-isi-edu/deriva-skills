---
name: route-data-management
description: "Use this skill for DerivaML assets, data preparation, bag troubleshooting, and scripted catalog operations. For dataset operations use the dataset-lifecycle skill directly. For features, labels, and annotations use the create-feature skill directly."
---

# Data Management — Features, Assets, and Preparation

You are a router skill. Based on the user's request, load the appropriate specialized skill.

**Note:** Dataset operations are handled by the `dataset-lifecycle` skill and feature operations by the `create-feature` skill — both are top-level skills invoked directly, not through this router.


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

### Assets
- **Finding asset tables, downloading assets, checking asset provenance, tracing which executions created an asset** → Read and follow `../work-with-assets/SKILL.md`

### Troubleshooting data exports
- **Missing data in downloaded dataset bags, FK traversal issues, materialization problems, bag export timeouts, validate_dataset_bag** → Read and follow `../debug-bag-contents/SKILL.md`

### Scripted catalog operations
- **Writing Python scripts for batch data loading, ETL, dataset creation pipelines, or any catalog operation needing code provenance** → Read and follow `../catalog-operations-workflow/SKILL.md`

## Important

After identifying the correct skill, read its SKILL.md file completely and follow its instructions. Do not attempt to handle the request from this routing skill alone.
