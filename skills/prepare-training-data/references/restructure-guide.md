# Restructuring Assets for ML Training

## Table of Contents

- [Overview](#overview)
- [Basic Usage](#basic-usage)
- [group_by Options](#group_by-options)
- [Handling Multi-Valued Features](#handling-multi-valued-features)
- [File Transformation](#file-transformation)
- [Directory Layout Control](#directory-layout-control)
- [ML Framework Integration](#ml-framework-integration)
- [DatasetBag API for Training Data](#datasetbag-api-for-training-data)
- [Denormalization for Flat DataFrames](#denormalization-for-flat-dataframes)
- [Common Patterns](#common-patterns)

---

## Overview

After downloading a dataset bag, `restructure_assets` organizes asset files into directory hierarchies expected by ML frameworks like PyTorch ImageFolder or TensorFlow image_dataset_from_directory.

The tool reads the bag's metadata (dataset types, feature values, vocabulary terms) to determine how to place each file. It works with any asset type — images, model weights, CSVs — not just images.

## Basic Usage

### MCP tool

```
restructure_assets(
    dataset_rid="2-XXXX",
    asset_table="Image",
    output_dir="./ml_data",
    group_by=["Diagnosis"],
    version="1.0.0"
)
```

### Python API

```python
bag = dataset.download_dataset_bag(version="1.0.0")

bag.restructure_assets(
    output_dir="./ml_data",
    asset_table="Image",        # auto-detected if only one asset table
    group_by=["Diagnosis"],     # create subdirs by label
)
```

### Result

```
./ml_data/
  training/
    normal/
      img001.png
      img002.png
    pneumonia/
      img003.png
  testing/
    normal/
      img004.png
    pneumonia/
      img005.png
```

## group_by Options

The `group_by` list controls subdirectory creation. Items can be:

### Column names
Direct columns on the asset table:
```python
group_by=["Species"]
# Result: training/mouse/..., training/human/...
```

### Feature names
Features defined on the asset table or FK-reachable tables:
```python
group_by=["Diagnosis"]
# Looks up feature values for each asset, creates subdirs by value
```

### Feature.column
Specific column from a multi-column feature:
```python
group_by=["Classification.Label"]
# Uses only the "Label" column from the "Classification" feature
```

### Multiple group_by levels
Create nested hierarchies:
```python
group_by=["Species", "Diagnosis"]
# Result: training/human/normal/..., training/mouse/tumor/...
```

## Handling Multi-Valued Features

When an asset has multiple feature values (e.g., annotations from different executions or annotators), you need a `value_selector` to pick one:

### Built-in selectors

```python
from deriva_ml.dataset.dataset_bag import select_majority_vote, select_latest, select_first

# Most common label; ties broken by newest annotation
bag.restructure_assets(
    output_dir="./ml_data",
    group_by=["Diagnosis"],
    value_selector=select_majority_vote,
)

# Most recent annotation (by RCT timestamp)
bag.restructure_assets(
    output_dir="./ml_data",
    group_by=["Diagnosis"],
    value_selector=select_latest,
)

# Earliest annotation (by RCT timestamp)
bag.restructure_assets(
    output_dir="./ml_data",
    group_by=["Diagnosis"],
    value_selector=select_first,
)
```

### Custom selector

A selector receives a list of `FeatureValueRecord` objects and returns one:

```python
def select_highest_confidence(records):
    """Pick the annotation with the highest confidence score."""
    return max(records, key=lambda r: r.raw_record.get("Confidence", 0))

bag.restructure_assets(
    output_dir="./ml_data",
    group_by=["Diagnosis"],
    value_selector=select_highest_confidence,
)
```

Each `FeatureValueRecord` has:
- `.value` — the feature value (e.g., the vocabulary term name)
- `.raw_record` — the full row as a dict (all columns from the feature table)
- `.execution_rid` — which execution produced this annotation
- `.rct` — record creation timestamp

## File Transformation

Use `file_transformer` to convert file formats during restructuring:

```python
from PIL import Image as PILImage
import numpy as np

def oct_to_png(src, dest):
    """Convert OCT DICOM to PNG during restructuring."""
    img = load_oct_dcm(str(src))
    out = dest.with_suffix(".png")
    PILImage.fromarray((img * 255).astype(np.uint8)).save(out)
    return out

bag.restructure_assets(
    output_dir="./ml_data",
    group_by=["Diagnosis"],
    file_transformer=oct_to_png,
)
```

A transformer receives `(src_path, dest_path)` and returns the actual output path (which may differ from `dest_path` if the extension changes).

## Directory Layout Control

### Dataset type mapping

By default, dataset types map to directory names (Training → "training", Testing → "testing"). Customize with `type_to_dir_map`:

```python
bag.restructure_assets(
    output_dir="./ml_data",
    group_by=["Diagnosis"],
    type_to_dir_map={"Training": "train", "Testing": "test", "Validation": "val"},
)
# Result: train/normal/..., test/normal/..., val/normal/...
```

### Symlinks vs copies

```python
# Default: symlinks (saves disk space)
bag.restructure_assets(output_dir="./ml_data", use_symlinks=True)

# Copy files instead (portable, safe to delete the bag)
bag.restructure_assets(output_dir="./ml_data", use_symlinks=False)
```

### Datasets without types

Datasets that have no dataset type are treated as Testing. This is common for prediction/inference datasets.

### Assets without labels

Assets that have no matching feature value for a `group_by` entry are placed in an `"Unknown"` subdirectory.

### Vocabulary enforcement

By default, features used in `group_by` must have vocabulary terms:
```python
# Allow non-vocabulary features (e.g., numeric or free-text columns)
bag.restructure_assets(
    output_dir="./ml_data",
    group_by=["Score"],
    enforce_vocabulary=False,
)
```

## ML Framework Integration

### PyTorch ImageFolder

```python
from torchvision.datasets import ImageFolder
from torchvision import transforms

bag.restructure_assets(
    output_dir="./ml_data",
    group_by=["Diagnosis"],
    type_to_dir_map={"Training": "train", "Testing": "test"},
)

train_dataset = ImageFolder(
    root="./ml_data/train",
    transform=transforms.Compose([
        transforms.Resize(224),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])
)
```

### TensorFlow image_dataset_from_directory

```python
import tensorflow as tf

bag.restructure_assets(
    output_dir="./ml_data",
    group_by=["Diagnosis"],
)

train_ds = tf.keras.utils.image_dataset_from_directory(
    "./ml_data/training",
    image_size=(224, 224),
    batch_size=32,
)
```

### Tabular ML with denormalization

For non-image tasks, use `denormalize_as_dataframe` instead:

```python
df = bag.denormalize_as_dataframe(include_tables=["Subject", "Measurement"])
# Returns a flat DataFrame with joined columns
```

## DatasetBag API for Training Data

Once downloaded, a `DatasetBag` provides a rich API for accessing training data:

### Browsing data

```python
# List all tables
bag.list_tables()  # ["Image", "Subject", "Species", ...]

# Get table as DataFrame
images_df = bag.get_table_as_dataframe("Image")

# Get table as list of dicts
subjects = list(bag.get_table_as_dict("Subject"))

# List members grouped by table
members = bag.list_dataset_members()  # {"Image": [...], "Subject": [...]}
members = bag.list_dataset_members(recurse=True)  # includes nested datasets
```

### Feature values

```python
# Discover features on a table
features = bag.find_features("Image")  # [Feature(name="Diagnosis", ...)]

# Fetch feature values
feature_df = bag.fetch_table_features(
    table="Image",
    feature_name="Diagnosis",
    selector="newest",           # or: workflow="classify", execution="3-XYZ"
)

# List all feature values for a specific record
values = bag.list_feature_values(target="2-ABCD", feature="Diagnosis")
```

### Denormalization

```python
# Flatten to wide table — joins across FK paths
df = bag.denormalize_as_dataframe(include_tables=["Image", "Subject"])

# Same as dict
rows = bag.denormalize_as_dict(include_tables=["Image", "Subject"])
```

### Dataset hierarchy

```python
# Child datasets (e.g., train/test splits)
children = bag.list_dataset_children()
children = bag.list_dataset_children(recurse=True)

# Element types registered for this dataset
element_types = bag.list_dataset_element_types()
```

## Denormalization for Flat DataFrames

The `denormalize_dataset` MCP tool and `bag.denormalize_as_dataframe()` method join dataset tables into a single flat DataFrame, following FK relationships. This is the fastest path from catalog data to ML-ready tabular features.

### MCP tool

```
denormalize_dataset(
    dataset_rid="2-XXXX",
    include_tables=["Image", "Subject", "Diagnosis"],
    version="1.0.0",
    limit=5000
)
```

### Column naming

Denormalized columns follow the pattern `TableName_ColumnName`:
- `Image_Filename`, `Image_URL`
- `Subject_Age`, `Subject_Sex`
- `Diagnosis_Name` (vocabulary term name)

### Include tables

Only include tables you actually need — this keeps the join efficient and avoids pulling in unrelated data through FK chains.

## Common Patterns

### Image classification pipeline

```python
# 1. Download dataset
bag = dataset.download_dataset_bag(version="1.0.0")

# 2. Restructure for PyTorch
bag.restructure_assets(
    output_dir="./data",
    group_by=["Diagnosis"],
    value_selector=select_majority_vote,
    type_to_dir_map={"Training": "train", "Testing": "test"},
)

# 3. Create dataloaders
train_ds = ImageFolder("./data/train", transform=train_transform)
test_ds = ImageFolder("./data/test", transform=test_transform)
```

### Tabular classification

```python
# 1. Download dataset (metadata only — no asset files needed)
bag = dataset.download_dataset_bag(version="1.0.0", materialize=False)

# 2. Build flat DataFrame
df = bag.denormalize_as_dataframe(include_tables=["Subject", "Measurement"])

# 3. Split features and labels
X = df[["Subject_Age", "Subject_Weight", "Measurement_Value"]]
y = df["Subject_Diagnosis"]
```

### Multi-label with custom file conversion

```python
bag.restructure_assets(
    output_dir="./data",
    group_by=["Primary_Diagnosis", "Severity"],  # nested dirs
    value_selector=select_latest,
    file_transformer=dicom_to_png,
    use_symlinks=False,  # copy for portability
)
```

## Reference Resources

| Resource / Tool | Purpose |
|-----------------|---------|
| `download_dataset` | Download bag (supports `exclude_tables`, `timeout`, `materialize`) |
| `restructure_assets` | Organize assets into ML-ready directory layouts |
| `denormalize_dataset` | Flatten dataset tables for ML (without full bag download) |
| `estimate_bag_size` | Preview row counts and asset sizes per table |
| `fetch_table_features` | Access feature values within a bag |
| `deriva://dataset/{rid}` | Dataset details including version and element types |
| `deriva://catalog/features` | Available features for building training labels |
