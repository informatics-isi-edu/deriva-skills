---
name: customize-display
description: "Customize the Chaise web UI display for Deriva catalog tables using MCP annotation tools. Use when setting visible columns, reordering columns, changing display names, configuring row name patterns, or adjusting how tables and records appear in the browser UI."
disable-model-invocation: true
---

# Customizing Chaise Web UI Display

Deriva catalogs are browsed through the Chaise web application. The display is controlled by annotations -- JSON metadata attached to schemas, tables, and columns. MCP tools provide a high-level interface for setting these annotations without writing raw JSON.

**This skill covers the interactive MCP tool approach.** Production Python code can write annotations as plain dicts using the JSON shapes documented in `references/annotation-reference.md`.

## Immediate apply

The legacy `deriva-mcp` server staged annotation edits locally and required a final `apply_annotations()` call to commit them. The new `deriva-mcp-core` applies every annotation change immediately. There is no staging; there is no `apply_annotations` or `apply_catalog_annotations` tool. Each tool call you make in the steps below mutates the catalog at the moment of the call.

## Step 1: Check Current Annotations

**Start with `rag_search`** to find the table and columns you want to customize:
```python
rag_search("Image table columns", doc_type="catalog-schema")
```

Then inspect the current state with the dedicated annotation-read tools:
```python
# Inspect table-level annotations
get_table_annotations(
    hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Image",
)

# Inspect column-level annotations
get_column_annotations(
    hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Image", column="URL",
)

# View sample data to understand what users see
get_table_sample_data(
    hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Image",
)
```

## Step 2: Understand Display Contexts

Annotations can be set per-context, controlling how data appears in different Chaise views:

| Context | Description |
|---------|-------------|
| `compact` | Table/record list view (summary rows) |
| `compact/brief` | Inline compact display (e.g., in popups) |
| `compact/select` | Record selector dropdowns |
| `detailed` | Single record detail view |
| `entry` | Record creation form |
| `entry/edit` | Record edit form |
| `entry/create` | Record creation form (overrides entry) |
| `filter/compact` | Facet panel display |
| `row_name` | How a record is identified (used in FK links, breadcrumbs) |
| `row_name/compact` | Row name in compact context |
| `row_name/detailed` | Row name in detailed context |
| `*` | Default for all contexts |

## Step 3: Customize Display Names

### Table display name
```python
set_table_display_name(
    hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Image",
    display_name="Images",
)
```

### Column display name
```python
set_column_display_name(
    hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Image", column="URL",
    display_name="Image File",
)
set_column_display_name(
    hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Subject", column="Age_At_Enrollment",
    display_name="Age at Enrollment",
)
```

### Column description (tooltip)
```python
set_column_description(
    hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Image", column="URL",
    description="Direct download link for the image file",
)
```

## Step 4: Configure Visible Columns

Control which columns appear and in what order for each context.

### Add a column to a context
```python
add_visible_column(
    hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Image",
    context="compact", column="Filename",
)
add_visible_column(
    hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Image",
    context="compact", column="Subject",
)
```

### Remove a column from a context
```python
remove_visible_column(
    hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Image",
    context="compact", column="RCT",
)
```

### Reorder columns
```python
reorder_visible_columns(
    hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Image",
    context="compact",
    new_order=["Filename", "Subject", "Diagnosis", "Image_Type", "URL"],
)
```

### Set all visible columns at once
```python
set_visible_columns(
    hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Image",
    annotation={"compact": ["Filename", "Subject", "Diagnosis", "Image_Type", "URL"]},
)
```

### Different columns per context
```python
set_visible_columns(
    hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Image",
    annotation={
        "compact": ["Filename", "Subject", "Diagnosis"],
        "detailed": ["Filename", "Subject", "Diagnosis", "Image_Type", "URL", "File_Size", "Description"],
        "entry": ["Filename", "Subject", "Diagnosis", "Image_Type", "Description"],
    },
)
```

## Step 5: Configure Row Names

Row names determine how a record is identified when referenced from other tables (e.g., in foreign key links, breadcrumbs, and search results).

### Simple row name from a column
```python
set_row_name_pattern(
    hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Subject",
    pattern="{{{Name}}}",
)
```

### Composite row name with multiple columns
```python
set_row_name_pattern(
    hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Subject",
    pattern="{{{Last_Name}}}, {{{First_Name}}}",
)
```

### Row name with related data using Handlebars
```python
set_row_name_pattern(
    hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Image",
    pattern="{{{Filename}}} ({{{Diagnosis}}})",
)
```

### Table display with row ordering
```python
set_table_display(
    hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Subject",
    annotation={
        "compact": {
            "row_markdown_pattern": "{{{Name}}} (Age: {{{Age}}})",
            "row_order": [{"column": "Name", "descending": false}],
        },
    },
)
```

## Step 6: Configure Visible Foreign Keys

Control which related tables are shown as sections on the detail page of a record.

### Add a related table section
```python
add_visible_foreign_key(
    hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Subject",
    context="detailed",
    foreign_key=["myproject", "Image_Subject_fkey"],
)
```

### Remove a related table section
```python
remove_visible_foreign_key(
    hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Subject",
    context="detailed",
    foreign_key=["myproject", "Image_Subject_fkey"],
)
```

### Reorder related table sections
```python
reorder_visible_foreign_keys(
    hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Subject",
    context="detailed",
    new_order=[
        ["myproject", "Image_Subject_fkey"],
        ["myproject", "Sample_Subject_fkey"],
        ["myproject", "Diagnosis_Subject_fkey"],
    ],
)
```

### Set all visible foreign keys at once
```python
set_visible_foreign_keys(
    hostname="data.example.org", catalog_id="1",
    schema="myproject", table="Subject",
    annotation={
        "detailed": [
            {"source": [{"inbound": ["myproject", "Image_Subject_fkey"]}, "RID"]},
            {"source": [{"inbound": ["myproject", "Sample_Subject_fkey"]}, "RID"]},
        ],
    },
)
```

## That's it — no apply step

Every tool above persists the change immediately. There is no `apply_annotations()` step in the new MCP architecture. Verify your changes by re-running `get_table_annotations(...)` and viewing the table in Chaise.

For the full annotation reference — all contexts, pseudo-columns, faceted search, Handlebars patterns, and Python annotation builders — see `references/annotation-reference.md`. For quick recipes, see `references/common-recipes.md`.

## Reference Tools

For a complete picture of what's set on a table or column:

- `get_table_annotations(hostname, catalog_id, schema, table)` — All annotations on a table
- `get_column_annotations(hostname, catalog_id, schema, table, column)` — All annotations on a column
- `apply_navbar_annotations(hostname, catalog_id, ...)` — Catalog-level navbar configuration

The legacy `apply_catalog_annotations()` "apply sensible defaults to all tables" tool was not ported to `deriva-mcp-core` — set defaults per-table using the tools above. (If a bulk-defaults convenience is needed, file an upstream issue against `deriva-mcp-core`.)

## Tips

- All annotation changes apply immediately — no separate commit step.
- The `compact` context is the most commonly customized -- it controls the table listing view.
- Row name patterns use Handlebars syntax: `{{{column_name}}}` for column values.
- Foreign key columns are automatically rendered as links to the related record in Chaise.
- Test your changes by viewing the table in Chaise after each call.
- If something looks wrong, use `get_table_annotations(...)` and `get_column_annotations(...)` to inspect the current state.
- The `["myproject", "Image_Subject_fkey"]` two-element form for foreign keys is `[schema_name, fkey_constraint_name]`. Replace `myproject` with your actual schema name.
