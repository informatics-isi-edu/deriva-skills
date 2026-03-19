# Steps Before Running Next Experiment

Your training config references dataset 28EA at version 0.3.0. You've since added 200 new fundus images and fixed labels on ~30 mislabeled images. Before running your next experiment, you need to update the dataset to capture these changes and bump its version so the new training run is traceable to the correct data snapshot.

Here is the exact sequence of steps and tool calls:

---

## Step 1: Verify the current state of the dataset

Confirm the dataset RID and its current version before making changes.

```
mcp__deriva__get_dataset_spec(
  dataset_rid="28EA"
)
```

Expected: confirms the dataset exists, shows version 0.3.0, and shows current member list.

---

## Step 2: Add the 200 new fundus images as dataset members

The new images need to be added to dataset 28EA. Assuming each image is represented by a RID in the catalog:

```
mcp__deriva__add_dataset_members(
  dataset_rid="28EA",
  member_rids=["<RID_1>", "<RID_2>", ..., "<RID_200>"]
)
```

Note: If you already know the RIDs of the new images (e.g., from the catalog upload process), pass them here. If not, you would first query the catalog to retrieve the newly added image RIDs, then call this tool.

---

## Step 3: Verify the label fixes are reflected in the dataset

The ~30 relabeled images were already in the dataset. Since their labels are stored as catalog record attributes (not as membership), the fixes you made to those records are already visible through the existing dataset membership — no membership changes are needed for those.

However, confirm the fixes are present:

```
mcp__deriva__list_dataset_members(
  dataset_rid="28EA"
)
```

Inspect that the corrected labels are reflected in the member records. If labels are stored in a separate annotation/vocabulary column on the image table, verify via:

```
mcp__deriva__get_table_sample_data(
  table_name="Image",   # or whatever the fundus image table is called
  schema_name="deriva-ml"
)
```

---

## Step 4: Increment the dataset version

Now that the dataset membership has changed (200 new images added) and the underlying records have changed (30 label fixes), increment the version. Since this is a meaningful data update — new samples added and labels corrected — a minor version bump from 0.3.0 → 0.4.0 is appropriate.

```
mcp__deriva__increment_dataset_version(
  dataset_rid="28EA"
)
```

This records the new version in the catalog and makes the dataset snapshot stable and reproducible.

---

## Step 5: Confirm the new version

Verify the version was bumped correctly:

```
mcp__deriva__get_dataset_spec(
  dataset_rid="28EA"
)
```

Expected: version is now 0.4.0 (or whatever the incremented value is).

---

## Step 6: Update your training config

Update your training configuration to reference the new version. Change:

```
dataset_rid: "28EA"
dataset_version: "0.3.0"
```

to:

```
dataset_rid: "28EA"
dataset_version: "0.4.0"   # or the actual new version returned in Step 5
```

---

## Step 7: (Optional but recommended) Validate the dataset bag before training

Before kicking off a long training run, validate that the dataset bag is consistent and all members resolve correctly:

```
mcp__deriva__validate_dataset_bag(
  dataset_rid="28EA"
)
```

This catches any broken references or missing files before they cause a training failure mid-run.

---

## Summary

| Step | Action | Tool |
|------|--------|------|
| 1 | Confirm current dataset state | `get_dataset_spec` |
| 2 | Add 200 new images to dataset | `add_dataset_members` |
| 3 | Verify label fixes are visible | `list_dataset_members` / `get_table_sample_data` |
| 4 | Bump dataset version | `increment_dataset_version` |
| 5 | Confirm new version | `get_dataset_spec` |
| 6 | Update training config | (manual edit) |
| 7 | Validate dataset bag | `validate_dataset_bag` |

The key principle: your training run should always reference a specific, immutable version of the dataset. Bumping the version after data changes ensures reproducibility — if you need to re-run or debug results, version 0.3.0 still points to the original data and 0.4.0 points to the updated set.
