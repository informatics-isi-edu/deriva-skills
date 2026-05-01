# Annotation Reference

## Table of Contents

- [Understanding Contexts](#understanding-contexts)
- [Display Annotation](#display-annotation)
- [Visible Columns](#visible-columns)
- [Visible Foreign Keys](#visible-foreign-keys)
- [Table Display](#table-display)
- [Column Display](#column-display)
- [Pseudo-Columns](#pseudo-columns)
- [Faceted Search](#faceted-search)
- [Handlebars Templates](#handlebars-templates)
- [Template Variables](#template-variables)
- [Common Recipes](#common-recipes)

---

## Understanding Contexts

Annotations apply to specific **contexts** — different places where data appears in the Chaise UI:

| Context | Chaise View | Typical Use |
|---------|-------------|-------------|
| `*` | Default for all contexts | Fallback when no specific context is set |
| `compact` | Table/record list view | Search results, data browser — **most commonly customized** |
| `compact/brief` | Abbreviated inline previews | Tooltips, inline references |
| `compact/select` | Selection dropdowns | FK pickers, record selectors |
| `detailed` | Full record detail view | Single record page with all fields |
| `entry` | Record create/edit form | Data entry (shared create and edit defaults) |
| `entry/create` | Create form only | Overrides `entry` for new record creation |
| `entry/edit` | Edit form only | Overrides `entry` for existing record editing |
| `filter` / `filter/compact` | Facet panel | Search sidebar filters |
| `row_name` | Row identification | Used in FK links, breadcrumbs, search results |
| `row_name/compact` | Row name in list view | Context-specific row name |
| `row_name/detailed` | Row name in detail view | Context-specific row name |

Context inheritance: `entry/create` falls back to `entry`, which falls back to `*`. Set `*` for defaults, override specific contexts as needed.

## Display Annotation

Controls basic display properties for tables and columns.

### MCP tools

```
set_table_display_name(table_name="Image", display_name="Images")
set_column_display_name(table_name="Image", column_name="URL", display_name="Image File")
set_column_description(table_name="Image", column_name="URL", description="Direct download link")
set_table_description(table_name="Image", description="Microscopy images with metadata")
```

## Visible Columns

Control which columns appear and in what order per context.

### MCP tools

```
# Add individual columns
add_visible_column(table_name="Image", context="compact", column="Filename")

# Remove columns
remove_visible_column(table_name="Image", context="compact", column="RCT")

# Reorder
reorder_visible_columns(
    table_name="Image", context="compact",
    new_order=["Filename", "Subject", "Diagnosis", "URL"]
)

# Set all at once
set_visible_columns(
    table_name="Image",
    annotation={"compact": ["Filename", "Subject", "Diagnosis"]}
)

# Different columns per context
set_visible_columns(
    table_name="Image",
    annotation={
        "compact": ["Filename", "Subject", "Diagnosis"],
        "detailed": ["Filename", "Subject", "Diagnosis", "Image_Type", "URL", "File_Size"],
        "entry": ["Filename", "Subject", "Diagnosis", "Image_Type", "Description"]
    }
)
```

## Visible Foreign Keys

Control which related tables appear as sections on the detail page.

### MCP tools

```
# Add
add_visible_foreign_key(
    table_name="Subject", context="detailed",
    foreign_key=["myproject", "Image_Subject_fkey"]
)

# Remove
remove_visible_foreign_key(
    table_name="Subject", context="detailed",
    foreign_key=["myproject", "Image_Subject_fkey"]
)

# Reorder
reorder_visible_foreign_keys(
    table_name="Subject", context="detailed",
    new_order=[
        ["myproject", "Image_Subject_fkey"],
        ["myproject", "Sample_Subject_fkey"]
    ]
)

# Set all at once
set_visible_foreign_keys(
    table_name="Subject",
    annotation={"detailed": [
        {"source": [{"inbound": ["myproject", "Image_Subject_fkey"]}, "RID"]},
        {"source": [{"inbound": ["myproject", "Sample_Subject_fkey"]}, "RID"]}
    ]}
)
```

## Table Display

Controls table-level options: row naming, ordering, pagination.

### MCP tools

```
# Row name pattern (used in FK dropdowns, breadcrumbs)
set_row_name_pattern(table_name="Subject", pattern="{{{Name}}}")

# Composite row name
set_row_name_pattern(table_name="Subject", pattern="{{{Last_Name}}}, {{{First_Name}}}")

# Table display with ordering
set_table_display(
    table_name="Subject",
    annotation={
        "compact": {
            "row_markdown_pattern": "{{{Name}}} (Age: {{{Age}}})",
            "row_order": [{"column": "Name", "descending": false}]
        }
    }
)
```

## Column Display

Controls how column values are rendered.

### MCP tools

```
set_column_display(
    table_name="Image", column_name="URL",
    annotation={"compact": {"markdown_pattern": "[Download]({{{URL}}})"}}
)

set_column_display(
    table_name="Measurement", column_name="Value",
    annotation={"compact": {"markdown_pattern": "{{{Value}}} {{{Units}}}"}}
)
```

## Pseudo-Columns

Display computed values, values from related tables, or custom formatting.

### Aggregates

| Aggregate | Description |
|-----------|-------------|
| `CNT` | Count related records |
| `CNT_D` | Count distinct values |
| `MIN` | Minimum value |
| `MAX` | Maximum value |
| `ARRAY` | Array of values |

## Faceted Search

Configure the filter panel in the Chaise data browser. Set facet annotations via MCP tools (or write annotation JSON dicts directly) using the `tag:isrd.isi.edu,2018:facets` annotation namespace. The shape: `{"compact": [<facet>, ...], "filter": [<facet>, ...]}` where each `<facet>` is `{"source": "<column>" | <list-of-fk-hops>, "markdown_name": "...", "ux_mode": "ranges" | "check_presence" | ..., ...}`. See common-recipes.md for worked examples.

## Handlebars Templates

Many annotations support Handlebars templates for custom formatting.

### Syntax

| Pattern | Description |
|---------|-------------|
| `{{{ColumnName}}}` | Column value (triple braces = no HTML escaping) |
| `{{ColumnName}}` | Column value (double braces = HTML escaped) |
| `{{{_value}}}` | Current value (in column_display context) |
| `{{{_row.ColumnName}}}` | Row context access |
| `{{#if Notes}}...{{else}}...{{/if}}` | Conditional |
| `{{formatDate RCT 'YYYY-MM-DD'}}` | Date formatting |

### FK value access

```
{{{$fkeys.schema.constraint_name.values.ColumnName}}}
{{{$fkeys.schema.constraint_name.rowName}}}
```

### Common patterns

```
# Clickable filename
[{{{Filename}}}]({{{URL}}})

# Image preview
[![{{{Filename}}}]({{{URL}}})]({{{URL}}})

# Conditional display
{{#if Notes}}{{{Notes}}}{{else}}No notes{{/if}}

# FK value in row name
{{{$fkeys.domain.Subject_Species_fkey.values.Name}}}
```

## Template Variables

Use the `get_handlebars_template_variables` tool to discover available variables for a table:

```
get_handlebars_template_variables(table_name="Subject")
```

Or use `preview_handlebars_template` to test a template against actual data:

```
preview_handlebars_template(
    table_name="Subject",
    template="{{{Name}}} ({{{Species}}})"
)
```

## Plain-dict annotations in Python

Annotations are JSON objects; any Python code can construct them as plain dicts using the shapes documented in the sections above and write them via the standard catalog model write APIs (the same shapes the MCP tools accept). The MCP tools documented in `SKILL.md` are the recommended path for iterative customization; plain-dict construction in Python is the path for code-driven customization without additional library dependencies.

## Common Recipes

### Hide system columns from compact view
```
remove_visible_column(table_name="Image", context="compact", column="RID")
remove_visible_column(table_name="Image", context="compact", column="RCT")
remove_visible_column(table_name="Image", context="compact", column="RMT")
remove_visible_column(table_name="Image", context="compact", column="RCB")
remove_visible_column(table_name="Image", context="compact", column="RMB")
```

### Set up a domain table with key info

```
set_visible_columns(
    table_name="Subject",
    annotation={"compact": ["Name", "Age", "Sex", "Species", "Diagnosis"]}
)
set_row_name_pattern(table_name="Subject", pattern="{{{Name}}}")
# (changes apply immediately — no separate apply step)
```

### Configure vocabulary table display

```
set_visible_columns(
    table_name="Diagnosis",
    annotation={"compact": ["Name", "Description", "Synonyms"]}
)
set_row_name_pattern(table_name="Diagnosis", pattern="{{{Name}}}")
```

### Show image previews in compact view

```
set_column_display(
    table_name="Image", column_name="URL",
    annotation={"compact": {"markdown_pattern": "[![Preview]({{{URL}}})]({{{URL}}})"}}
)
```

### Add record count from related table

```python
# In visible columns, add a pseudo-column counting related images
vc.compact([
    "Name", "Species",
    PseudoColumn(
        source=[InboundFK("domain", "Image_Subject_fkey"), "RID"],
        aggregate=Aggregate.CNT,
        markdown_name="Images"
    )
])
```

### Configure an asset table for browsing

```
set_visible_columns(
    table_name="Image",
    annotation={
        "compact": ["Filename", "Subject", "Diagnosis", "URL"],
        "detailed": ["Filename", "Subject", "Diagnosis", "URL", "Length", "MD5", "Description"]
    }
)
set_row_name_pattern(table_name="Image", pattern="{{{Filename}}}")
set_column_display(
    table_name="Image", column_name="URL",
    annotation={"compact": {"markdown_pattern": "[Download]({{{URL}}})"}}
)
```

## Reference Tools

| Tool | Purpose |
|------|---------|
| `get_table_annotations(hostname, catalog_id, schema, table)` | View current annotations on a table |
| `get_column_annotations(hostname, catalog_id, schema, table, column)` | View column annotations |
| `apply_navbar_annotations(hostname, catalog_id, ...)` | Catalog-level navbar configuration |
| `get_handlebars_template_variables` | Discover available template variables for a table |
| `preview_handlebars_template` | Test a template against actual data |
| `validate_template_syntax` | Check template syntax without running it |

> **Architectural notes:** Annotations apply immediately when set — there is no separate apply step and no bulk "apply defaults across all tables" tool. Set defaults per-table using the `set_*` tools shown above.
| `deriva://docs/annotations` | Full annotation guide |
