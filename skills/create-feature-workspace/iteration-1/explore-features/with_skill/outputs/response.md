# Exploring Features on the Image Table

## Step 1: Confirm catalog connection

Read resource `deriva://catalog/connections`

If no connection is active:
```
connect_catalog(hostname="<your-hostname>", catalog_id="<your-catalog-id>")
```

## Step 2: Browse all features in the catalog

```
Read resource: deriva://catalog/features
```

Filter results to those where target_table == "Image".

## Step 3: Get all feature values on the Image table (deduplicated)

```
Read resource: deriva://table/Image/feature-values/newest
```

Returns one value per Image record per feature (deduplicated to most recent by RCT).

## Step 4: Inspect each feature's structure in detail

For each feature discovered in Step 2:
```
Read resource: deriva://feature/Image/<feature_name>
```

Shows term columns, asset columns, metadata columns, and their types.

## Step 5: Fetch feature values with provenance (optional deep-dive)

```
fetch_table_features(table_name="Image", selector="newest")
```

## Summary

| # | Action | Call |
|---|--------|------|
| 1 | Verify connection | Read `deriva://catalog/connections` |
| 2 | List all catalog features | Read `deriva://catalog/features` |
| 3 | See existing Image feature values (newest) | Read `deriva://table/Image/feature-values/newest` |
| 4 | Inspect each Image feature's schema | Read `deriva://feature/Image/{feature_name}` |
| 5 | Browse all values with provenance | `fetch_table_features` or Read `deriva://feature/Image/{feature_name}/values` |
