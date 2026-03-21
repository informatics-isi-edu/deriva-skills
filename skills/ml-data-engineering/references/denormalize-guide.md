# Denormalization Guide

Denormalization joins related tables into a single flat table (a "wide table") suitable for ML frameworks. It follows foreign key relationships automatically, handling both direct and multi-hop FK chains.

## Quick Reference

**MCP tool (catalog-side):**
```
denormalize_dataset(
    dataset_rid="2-XXXX",
    include_tables=["Image", "Subject", "Diagnosis"],
    version="1.0.0",
    limit=5000
)
```

**Python API (bag-side):**
```python
df = bag.denormalize_as_dataframe(include_tables=["Image", "Subject"])

# Memory-efficient streaming
for row in bag.denormalize_as_dict(include_tables=["Image", "Subject"]):
    process(row)
```

**Column naming:**

| Source | Pattern | Example |
|--------|---------|---------|
| Catalog (MCP tool, `Dataset.denormalize_as_dataframe`) | `Table_Column` | `Image_Filename`, `Subject_Age` |
| Bag (`DatasetBag.denormalize_as_dataframe`) | `Table.Column` | `Image.Filename`, `Subject.Age` |

## How FK Traversal Works

Denormalization starts from a **primary table** — the first table in `include_tables` that has dataset members. It then joins other tables by following FK relationships.

### Direct FK joins

The simplest case: two tables connected by a single FK.

```
Schema:  Image --FK--> Subject
Query:   include_tables=["Image", "Subject"]
Result:  Each Image row joined with its Subject
```

Tables don't need to be explicit dataset members to appear in the output. If Image is the only table with dataset members, Subject records are fetched by following the FK from each Image to its Subject.

### Multi-hop FK chains

When tables aren't directly connected, denormalize follows chains of FKs through intermediate tables.

```
Schema:  Image --FK--> Observation --FK--> Subject
Query:   include_tables=["Image", "Observation", "Subject"]
Result:  Each Image joined with its Observation, then each Observation joined with its Subject
```

The algorithm:
1. Start with primary table members (Image records from the dataset)
2. Follow FK from Image to Observation — fetch matching Observation records
3. Follow FK from Observation to Subject — fetch matching Subject records
4. Combine all columns into a single wide row per Image

All intermediate tables must be listed in `include_tables`. If you request `["Image", "Subject"]` but the only FK path goes through Observation, you need to include Observation.

### Association table traversal (M:N joins)

Many-to-many relationships use association tables. Denormalize traverses them transparently — association table columns do NOT appear in the output.

```
Schema:  Observation <--FK-- ClinicalRecord_Observation --FK--> ClinicalRecord
Query:   include_tables=["Image", "Observation", "ClinicalRecord"]
Result:  Image → Observation → (through association) → ClinicalRecord
         Association table columns excluded from output
```

### Outer join semantics

Denormalize uses outer join semantics. If an Image has no Observation FK set (null), the Observation columns in that row will all be null. No rows are dropped — every primary table member always appears in the output.

```python
df = bag.denormalize_as_dataframe(include_tables=["Image", "Observation"])
# Row count == number of Image dataset members (never fewer)
# Images with null Observation FK → Observation columns are null
```

## Ambiguous FK Paths

When multiple FK paths exist between the same pair of tables, denormalize raises a `DerivaMLException` asking you to disambiguate.

### When it happens

```
Schema:  Image --FK--> Subject           (direct FK)
         Image --FK--> Observation --FK--> Subject  (multi-hop)
```

Here, Subject is reachable from Image via two different paths. Requesting `["Image", "Subject"]` is ambiguous — which path should be used for the join?

### The error

```
DerivaMLException: Ambiguous path between Image and Subject: found 2 FK paths:
  Image → Subject
  Image → Observation → Subject
Include an intermediate table to disambiguate (e.g., add Observation to include_tables).
```

### How to resolve

Include the intermediate table to tell denormalize which path to use:

```python
# Ambiguous — raises error
df = bag.denormalize_as_dataframe(include_tables=["Image", "Subject"])

# Disambiguated — uses Image → Observation → Subject path
df = bag.denormalize_as_dataframe(include_tables=["Image", "Observation", "Subject"])
```

When you include Observation, denormalize uses the multi-hop path (Image → Observation → Subject) because all intermediate tables on that path are present in `include_tables`.

### Checking for ambiguity

If you're unsure whether a schema has ambiguous paths, try the query. The error message lists all paths and suggests which intermediate tables to add. You can also inspect the schema:

```
# Via MCP — check FK relationships
rag_search("what tables reference Subject?")
```

## Best Practices

### Only include tables you need

Each table in `include_tables` adds columns and potentially triggers FK chain lookups. Including unnecessary tables:
- Increases query time (especially for multi-hop chains that require catalog fetches)
- Adds columns that clutter the DataFrame
- Can trigger ambiguous path errors for tables you don't even care about

### Start with the member table

The first table in `include_tables` that has dataset members becomes the primary table. The output has one row per primary table member. If you list a non-member table first, it may produce no results.

```python
# Good — Image has members, drives the output
df = bag.denormalize_as_dataframe(include_tables=["Image", "Subject"])

# Risky — if Observation has no members, result may be empty
df = bag.denormalize_as_dataframe(include_tables=["Observation", "Image"])
```

### Verify FK integrity

After denormalization, you can verify FK relationships in the output:

```python
df = bag.denormalize_as_dataframe(include_tables=["Image", "Observation"])

# Check FK values match
valid = df.dropna(subset=["Image.Observation", "Observation.RID"])
for _, row in valid.iterrows():
    assert row["Image.Observation"] == row["Observation.RID"]
```

## Troubleshooting

### All joined columns are null

**Symptom:** Denormalize returns rows but all columns from a joined table are null.

**Cause:** The joined table's records are not FK-reachable from the primary table members. This can happen when:
- The FK column on the primary table is null for all members
- The joined table has no records matching the FK values
- The FK path requires intermediate tables not listed in `include_tables`

**Fix:** Check that the FK column has values and include any intermediate tables in the path.

### DerivaMLException: Ambiguous path

**Symptom:** `DerivaMLException` raised with "Ambiguous path between X and Y".

**Cause:** Multiple FK paths exist between two tables in `include_tables`.

**Fix:** Read the error message — it lists all paths and suggests intermediate tables to add. Include the intermediate table for the path you want.

### Empty result (no rows)

**Symptom:** Denormalize returns an empty DataFrame.

**Cause:** No table in `include_tables` has dataset members. Denormalize needs at least one table with members to drive the output.

**Fix:** Ensure at least one table in `include_tables` is a registered element type with members in this dataset. Check with `list_dataset_members`.

### Row count doesn't match expectations

**Symptom:** More or fewer rows than expected.

**Cause:** Row count equals the number of primary table members (the first table in `include_tables` with members). It is NOT the count of the joined table. One-to-many or many-to-many joins do not duplicate rows — each primary member appears exactly once.

**Fix:** Check `list_dataset_members` for the primary table to confirm the expected count.
