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
- [Python Annotation Builders](#python-annotation-builders)
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

### Python API

```python
from deriva_ml.model import Display, NameStyle

# Simple display name
handle.set_annotation(Display(name="Research Subjects"))

# With markdown name (mutually exclusive with name)
handle.set_annotation(Display(markdown_name="**Bold** Name"))

# With description/tooltip
handle.set_annotation(Display(name="Subjects", comment="Individuals in the study"))

# Name styling (convert underscores to spaces, apply title case)
handle.set_annotation(Display(name_style=NameStyle(underline_space=True, title_case=True)))

# Show/hide null values per context
display = Display(name="Value", show_null={
    "compact": False,           # Hide nulls in lists
    "detailed": '"N/A"'         # Show "N/A" in detail view
})
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

### Python API

```python
from deriva_ml.model import VisibleColumns, PseudoColumn, fk_constraint

vc = VisibleColumns()
vc.compact(["RID", "Name", "Status"])
vc.detailed(["RID", "Name", "Status", "Description", "Created"])
vc.entry(["Name", "Status", "Description"])

# Include FK references
vc.compact(["RID", "Name", fk_constraint("domain", "Subject_Species_fkey")])

# Include pseudo-columns (computed values)
vc.detailed(["RID", "Name", PseudoColumn(source="Description", markdown_name="Notes")])

# Default for all contexts
vc.default(["RID", "Name"])

# Reference another context
vc.set_context("compact/brief", "compact")

handle.set_annotation(vc)
```

## Visible Foreign Keys

Control which related tables appear as sections on the detail page.

### MCP tools

```
# Add
add_visible_foreign_key(
    table_name="Subject", context="detailed",
    foreign_key=["deriva-ml", "Image_Subject_fkey"]
)

# Remove
remove_visible_foreign_key(
    table_name="Subject", context="detailed",
    foreign_key=["deriva-ml", "Image_Subject_fkey"]
)

# Reorder
reorder_visible_foreign_keys(
    table_name="Subject", context="detailed",
    new_order=[
        ["deriva-ml", "Image_Subject_fkey"],
        ["deriva-ml", "Sample_Subject_fkey"]
    ]
)

# Set all at once
set_visible_foreign_keys(
    table_name="Subject",
    annotation={"detailed": [
        {"source": [{"inbound": ["deriva-ml", "Image_Subject_fkey"]}, "RID"]},
        {"source": [{"inbound": ["deriva-ml", "Sample_Subject_fkey"]}, "RID"]}
    ]}
)
```

### Python API

```python
from deriva_ml.model import VisibleForeignKeys, fk_constraint

vfk = VisibleForeignKeys()
vfk.detailed([
    fk_constraint("domain", "Image_Subject_fkey"),
    fk_constraint("domain", "Diagnosis_Subject_fkey"),
])
handle.set_annotation(vfk)
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

### Python API

```python
from deriva_ml.model import TableDisplay, TableDisplayOptions, SortKey, TemplateEngine

td = TableDisplay()

# Simple row name
td.row_name("{{{Name}}}")

# Multi-column row name
td.row_name("{{{Name}}} - {{{RID}}}")

# Explicit template engine
td.row_name("{{{Name}}} ({{{Species}}})", template_engine=TemplateEngine.HANDLEBARS)

# Compact view options
td.compact(TableDisplayOptions(
    row_order=[SortKey("Name"), SortKey("Created", descending=True)],
    page_size=50
))

# Detailed view options
td.detailed(TableDisplayOptions(
    collapse_toc_panel=True,
    hide_column_headers=False
))

handle.set_annotation(td)
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

### Python API

```python
from deriva_ml.model import ColumnDisplay, ColumnDisplayOptions, PreFormat

cd = ColumnDisplay()

# Number formatting
cd.default(ColumnDisplayOptions(pre_format=PreFormat(format="%.2f")))

# Boolean formatting
cd.default(ColumnDisplayOptions(pre_format=PreFormat(bool_true_value="Yes", bool_false_value="No")))

# Markdown pattern (clickable URL)
cd.default(ColumnDisplayOptions(markdown_pattern="[Link]({{{_value}}})"))

# Context-specific formatting
cd.compact(ColumnDisplayOptions(markdown_pattern="[{{{_value}}}]({{{_value}}})"))
cd.detailed(ColumnDisplayOptions(markdown_pattern="**URL**: [{{{_value}}}]({{{_value}}})"))

col_handle = handle.column("URL")
col_handle.annotations[ColumnDisplay.tag] = cd.to_dict()
col_handle.apply()
```

## Pseudo-Columns

Display computed values, values from related tables, or custom formatting.

### Foreign key traversal

```python
from deriva_ml.model import PseudoColumn, OutboundFK, InboundFK, Aggregate

# Outbound: follow FK to get related value
# Image -> Subject → get Subject name
PseudoColumn(
    source=[OutboundFK("domain", "Image_Subject_fkey"), "Name"],
    markdown_name="Subject Name"
)

# Inbound: follow FK from another table
# Subject ← Images → count images per subject
PseudoColumn(
    source=[InboundFK("domain", "Image_Subject_fkey"), "RID"],
    aggregate=Aggregate.CNT,
    markdown_name="Image Count"
)

# Multi-hop: Image -> Subject -> Species
PseudoColumn(
    source=[
        OutboundFK("domain", "Image_Subject_fkey"),
        OutboundFK("domain", "Subject_Species_fkey"),
        "Name"
    ],
    markdown_name="Species"
)
```

### Aggregates

| Aggregate | Description |
|-----------|-------------|
| `CNT` | Count related records |
| `CNT_D` | Count distinct values |
| `MIN` | Minimum value |
| `MAX` | Maximum value |
| `ARRAY` | Array of values |

### Display options

```python
from deriva_ml.model import PseudoColumnDisplay, ArrayUxMode

PseudoColumn(
    source="URL",
    display=PseudoColumnDisplay(
        markdown_pattern="[Download]({{{_value}}})",
        show_foreign_key_link=False
    )
)

# Array display
PseudoColumn(
    source=[InboundFK("domain", "Tag_Subject_fkey"), "Name"],
    aggregate=Aggregate.ARRAY,
    display=PseudoColumnDisplay(array_ux_mode=ArrayUxMode.CSV)
)
```

## Faceted Search

Configure the filter panel in the Chaise data browser.

```python
from deriva_ml.model import Facet, FacetList, FacetRange, FacetUxMode

facets = FacetList()

# Simple choice facet
facets.add(Facet(source="Status", open=True, markdown_name="Status"))

# FK-based facet (filter by related table value)
facets.add(Facet(
    source=[OutboundFK("domain", "Subject_Species_fkey"), "Name"],
    markdown_name="Species", open=True
))

# Range facet for numeric values
facets.add(Facet(
    source="Age", ux_mode=FacetUxMode.RANGES,
    ranges=[FacetRange(min=0, max=18), FacetRange(min=18, max=65), FacetRange(min=65)],
    markdown_name="Age Group"
))

# Check presence facet
facets.add(Facet(source="Notes", ux_mode=FacetUxMode.CHECK_PRESENCE, markdown_name="Has Notes"))

# Apply to visible columns
vc = VisibleColumns()
vc.compact(["RID", "Name", "Status"])
vc._contexts["filter"] = facets.to_dict()
handle.set_annotation(vc)
```

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

## Python Annotation Builders

For production use (scripts, notebooks, version-controlled configurations), the Python API provides type-safe annotation builders. **These builders currently live in the `deriva-ml` Python package** (`from deriva_ml.model import ...`) — the annotations themselves are core Chaise concepts that work on any Deriva catalog, but the typed Python wrappers ride along with deriva-ml. If you only have `deriva-py` installed and don't want the deriva-ml dependency, write annotations as plain dicts using the JSON shapes documented in the sections above. See the dedicated `use-annotation-builders` skill for the full builder workflow.

```python
from deriva_ml.model import (
    TableHandle, Display, VisibleColumns, VisibleForeignKeys,
    TableDisplay, TableDisplayOptions, ColumnDisplay, ColumnDisplayOptions,
    PseudoColumn, OutboundFK, InboundFK, Facet, FacetList,
    fk_constraint, SortKey, Aggregate, FacetUxMode, PreFormat,
    CONTEXT_COMPACT, CONTEXT_DETAILED
)

# Get table handle
table = ml.model.name_to_table("Subject")
handle = TableHandle(table)

# Set annotations
handle.set_annotation(Display(name="Research Subjects"))
handle.set_annotation(td)   # TableDisplay
handle.set_annotation(vc)   # VisibleColumns
handle.set_annotation(vfk)  # VisibleForeignKeys
```

For the interactive MCP tool approach (recommended for iterative customization), use the SKILL.md directly.

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
# (changes apply immediately — no apply_annotations step in deriva-mcp-core)
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

> **Architectural notes:** Annotations apply immediately when set — there is no `apply_annotations()` step in `deriva-mcp-core` (the legacy `deriva-mcp` server staged edits and required a final apply call; that pattern is gone). The `apply_catalog_annotations()` "set defaults across all tables" tool was also not ported — set defaults per-table using the `set_*` tools shown above.
| `deriva://docs/annotations` | Full annotation guide |
