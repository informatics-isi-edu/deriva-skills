---
name: troubleshoot-deriva-errors
description: "Use when ANY Deriva catalog operation fails with auth, permissions, missing record, invalid RID, vocabulary term not found, or generic catalog connection / state errors. Tier-1: covers errors that don't depend on the deriva-ml execution machinery. Triggers on: 'permission denied', 'auth error', 'globus login', 'invalid RID', 'record not found', 'wrong catalog', 'vocabulary term missing', 'connect failed', 'catalog connection', 'unauthorized'."
user-invocable: false
disable-model-invocation: true
---

# Troubleshooting Generic Deriva Catalog Errors

This guide covers errors that surface in **any** Deriva catalog operation — they don't require the DerivaML execution / dataset / feature machinery to reproduce. If the error is specific to a DerivaML execution lifecycle (stuck `Running` status, `asset_file_path()` failing, `upload_execution_outputs()` timing out, dataset version mismatch), see the `troubleshoot-execution` skill in `deriva-ml-skills`.

> **Steering principle (deriva-ml environments):** Datasets, Workflows, Executions, Features, and Asset_Type vocabularies are first-class DerivaML concepts that happen to be stored as Deriva tables underneath. **If you're working in a catalog where the deriva-ml-mcp plugin is loaded, you must use the DerivaML abstractions** (`/deriva-ml:dataset-lifecycle`, `/deriva-ml:execution-lifecycle`, `/deriva-ml:create-feature`, the `deriva_ml_*` MCP tools, the deriva-ml Python API) for those concepts — not the raw `insert_entities` / `update_entities` / `get_entities` core tools. The raw tools bypass DerivaML's business logic, FK validation, provenance tracking, and version management. Reach for the raw catalog surface only for catalog objects that are NOT one of the DerivaML domain concepts (custom domain tables, generic vocabularies, schema introspection). The same principle applies in reverse: in a non-deriva-ml catalog, the DerivaML tools / skills won't apply, so you fall back to the generic surface this skill documents.

---

## Problem: "Permission Denied"

**Symptom**: Operations fail with authentication or authorization errors. The HTTP status is typically 401 (auth required / expired) or 403 (authenticated but lacking the role).

**Cause**: Your credentials have expired, or your account lacks the required role for the requested operation.

**Solution**:
- Re-authenticate using `deriva-globus-auth-utils`:
  ```bash
  deriva-globus-auth-utils login --host <hostname>
  ```
- Check that your user account has the necessary group membership for the operation (read, write, or admin).
- Some operations (like creating tables, modifying schemas, or applying annotations) require elevated permissions. Confirm with your catalog administrator.
- After a fresh `login`, the next MCP tool call automatically picks up the new credential — the new MCP server is stateless, so there is no `connect_catalog` step to re-run.

---

## Problem: "Invalid RID"

**Symptom**: A tool rejects a RID value or returns "not found".

**Cause**: The RID is malformed, belongs to a different table than expected, or refers to a deleted record.

**Solution**:
- **Tool**: `get_entities(hostname=..., catalog_id=..., schema=..., table=..., filter={"RID": "..."})` to check whether the RID exists in the expected table. An empty result means the RID does not exist there. (The legacy `validate_rids` tool was not ported to `deriva-mcp-core` — there is no single-tool cross-table RID lookup; query each candidate table.)
- RIDs are case-sensitive alphanumeric strings (e.g., `1-A2B3`). Ensure there are no extra spaces or characters.
- If the RID comes from a different catalog, it will not resolve in the current catalog. Pass the correct `hostname=` and `catalog_id=` to your tool call (the new MCP server is stateless — there is no implicit "current catalog").
- If the RID was recently created, it should be visible immediately — there is no propagation delay for catalog reads.

---

## Problem: "Record Not Found"

**Symptom**: Attempting to read a record by RID returns an error or empty result.

**Cause**: Wrong catalog connection, the record was deleted, or the RID is incorrect.

**Solution**:
- **Search first with `rag_search`**: Use `rag_search("description of what you want", doc_type="catalog-data")` to find records by description. This is the best way to discover the correct RID when you are unsure.
- Verify you are connected to the correct catalog. List active catalog connections via the registry resource.
- Use `get_entities(..., filter={"RID": "..."})` to confirm the RID exists and belongs to the table you expect.
- Use `query_attribute(..., filter={"RID": "..."})` if you want to project specific columns instead of all columns.

---

## Problem: "Vocabulary Term Not Found"

**Symptom**: An operation fails because a required vocabulary term does not exist (e.g., when adding a row that FKs into a vocabulary).

**Cause**: The term was not added to the vocabulary, or the name does not match exactly.

**Solution**:
- **Search first with `rag_search`**: Use `rag_search("term meaning or synonyms", doc_type="catalog-schema")` to find vocabulary terms. The RAG index includes term descriptions and synonyms, so fuzzy matching works (e.g., searching for "X-ray" will surface a term named `Xray` if it has the synonym set).
- Use `list_vocabulary_terms(hostname=..., catalog_id=..., schema=..., table=...)` to list existing terms; or `lookup_term(hostname=..., catalog_id=..., schema=..., table=..., name=...)` for synonym-aware lookup of a specific term.
- Vocabulary term names are case-sensitive.
- **Tool**: `add_term` to add the missing term to the appropriate vocabulary. See the `manage-vocabulary` skill for the full vocabulary surface.

---

## Problem: "Cannot Connect to Catalog"

**Symptom**: A tool call fails with a network error, "host not found", "connection refused", or an SSL/certificate error.

**Cause**: Network unreachable, hostname typo, server down, or your local CA store is missing the issuing CA for the host's certificate.

**Solution**:
- Verify the hostname spelling. Use `get_catalog_info(hostname=..., catalog_id=...)` to confirm the catalog ID resolves and your credential reaches it.
- Check basic connectivity: `curl -I https://<hostname>/ermrest/` should return `200 OK`.
- For SSL/cert errors, verify your system CA bundle is current. On macOS, run `Install Certificates.command` for your Python install. For self-signed dev hosts, the host admin must give you the CA cert to add to your trust store.
- If multiple hosts are in play (e.g., a staging vs production catalog), double-check the `hostname=` argument on the failing call — the stateless server has no implicit "active host" to fall back to.

---

## Reference Resources

- `get_catalog_info(hostname, catalog_id)` — Verify the catalog exists and your credential reaches it
- `server_status(hostname=None)` — MCP server health + loaded plugins (returns the new `deriva-mcp-core` framework version + the list of loaded plugins like `deriva-ml-mcp`)
- `catalog_tables(hostname, catalog_id)` — List all tables in the catalog (filter for vocabulary tables to verify term existence)

## General Debugging Tips

### Enable Verbose Logging

When using the Python API, enable verbose logging to see detailed request/response information:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Verify the Catalog Connection

The new MCP server is stateless — there is no "active catalog". Every tool call takes `hostname=` and `catalog_id=` arguments, so confirm the values you're passing match what you expect. Use `get_catalog_info(hostname=..., catalog_id=...)` to verify the target catalog exists and your credential reaches it.

### Inspect Catalog State

- Use the catalog schema resources to review the current schemas, tables, and vocabularies.
- **Tool**: `get_table_sample_data(hostname=..., catalog_id=..., schema=..., table=...)` to quickly verify data exists in expected tables.
- **Tool**: `get_entities(hostname=..., catalog_id=..., schema=..., table=..., filter={"RID": "..."})` to fetch a known RID and confirm the row is accessible to your credential.

### Re-authenticate If Anything Smells Like Auth

If errors are inconsistent (some reads work, some don't), or operations were working in an earlier session and are now failing, re-run `deriva-globus-auth-utils login --host <hostname>` and reconnect. Token expiry is the single most common cause of mid-session failures.

## Related Skills

- **`manage-vocabulary`** *(tier-1)* — When the fix is "add the missing vocabulary term", this is the skill that owns the vocabulary CRUD surface.
- **`check-deriva-versions`** *(tier-1)* — If errors started after an update, this skill verifies the deriva-py / deriva-mcp-core / deriva plugin versions match what's expected.
- **`troubleshoot-execution`** *(tier-2, deriva-ml-skills)* — For errors specific to the DerivaML execution machinery: stuck `Running` status, `asset_file_path()` failures, upload timeouts, dataset version mismatches.
