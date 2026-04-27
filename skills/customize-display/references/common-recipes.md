# Common Annotation Recipes and Patterns

> All examples below assume `hostname="data.example.org"`, `catalog_id="1"`, and `schema="myproject"` — substitute your actual values. Every annotation tool persists the change immediately (no `apply_annotations()` step in the new MCP architecture).

## Column Display Formatting

Control how individual column values are rendered:

```python
set_column_display(
    hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Image", column="URL",
    annotation={"compact": {"markdown_pattern": "[Download]({{{URL}}})"}},
)

set_column_display(
    hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Measurement", column="Value",
    annotation={"compact": {"markdown_pattern": "{{{Value}}} {{{Units}}}"}},
)
```

## Common Recipes

### Hide system columns from compact view

```python
for col in ["RID", "RCT", "RMT", "RCB", "RMB"]:
    remove_visible_column(
        hostname="data.example.org", catalog_id="1",
        schema="myproject", table="Image",
        context="compact", column=col,
    )
```

### Make a table's compact view show key info only

```python
set_visible_columns(
    hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Subject",
    annotation={"compact": ["Name", "Age", "Sex", "Species", "Diagnosis"]},
)
set_row_name_pattern(
    hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Subject",
    pattern="{{{Name}}}",
)
```

### Configure a vocabulary table display

```python
set_visible_columns(
    hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Diagnosis",
    annotation={"compact": ["Name", "Description", "Synonyms"]},
)
set_row_name_pattern(
    hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Diagnosis",
    pattern="{{{Name}}}",
)
```
