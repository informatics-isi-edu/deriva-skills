---
name: troubleshoot-deriva-errors
description: "Use when ANY Deriva catalog operation fails with auth, permissions, missing record, invalid RID, vocabulary term not found, or generic catalog connection / state errors. Tier-1: covers errors that don't depend on the deriva-ml execution machinery. Triggers on: 'permission denied', 'auth error', 'globus login', 'invalid RID', 'record not found', 'wrong catalog', 'vocabulary term missing', 'connect failed', 'catalog connection', 'unauthorized'."
user-invocable: false
disable-model-invocation: true
---

# Troubleshooting Generic Deriva Catalog Errors

This guide covers errors that surface in **any** Deriva catalog operation — they don't require the DerivaML execution / dataset / feature machinery to reproduce. If the error is specific to a DerivaML execution lifecycle (stuck `Running` status, `asset_file_path()` failing, `upload_execution_outputs()` timing out, dataset version mismatch), see the `troubleshoot-execution` skill in `deriva-ml-skills`.

> **Steering principle (deriva-ml environments):** Datasets, Workflows, Executions, Features, and Asset_Type vocabularies are first-class DerivaML concepts that happen to be stored as Deriva tables underneath. **If you're working in a catalog where the deriva-ml-mcp plugin is loaded, you must use the DerivaML abstractions** (`/deriva-ml:dataset-lifecycle`, `/deriva-ml:execution-lifecycle`, `/deriva-ml:create-feature`, the deriva-ml Python API) for those concepts — not the raw `insert_records` / `update_record` / `get_record` core tools. The raw tools bypass DerivaML's business logic, FK validation, provenance tracking, and version management. Reach for the raw catalog surface only for catalog objects that are NOT one of the DerivaML domain concepts (custom domain tables, generic vocabularies, schema introspection). The same principle applies in reverse: in a non-deriva-ml catalog, the DerivaML tools / skills won't apply, so you fall back to the generic surface this skill documents.

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
- Re-running `connect_catalog` after a fresh `login` picks up the new credential.

---

## Problem: "Invalid RID"

**Symptom**: A tool rejects a RID value or returns "not found".

**Cause**: The RID is malformed, belongs to a different table than expected, or refers to a deleted record.

**Solution**:
- **Tool**: `validate_rids` to check whether the RID exists and what table it belongs to.
- RIDs are case-sensitive alphanumeric strings (e.g., `1-A2B3`). Ensure there are no extra spaces or characters.
- If the RID comes from a different catalog, it will not resolve in the current catalog. Verify you are connected to the right catalog with `connect_catalog` (or check the active catalog via the registry resource).
- If the RID was recently created, it should be visible immediately — there is no propagation delay for catalog reads.

---

## Problem: "Record Not Found"

**Symptom**: Attempting to read a record by RID returns an error or empty result.

**Cause**: Wrong catalog connection, the record was deleted, or the RID is incorrect.

**Solution**:
- **Search first with `rag_search`**: Use `rag_search("description of what you want", doc_type="catalog-data")` to find records by description. This is the best way to discover the correct RID when you are unsure.
- Verify you are connected to the correct catalog. List active catalog connections via the registry resource.
- Use `validate_rids` to confirm the RID exists and belongs to the table you expect.
- Use `get_record` (or `preview_table` with a filter) to verify the row is reachable.

---

## Problem: "Vocabulary Term Not Found"

**Symptom**: An operation fails because a required vocabulary term does not exist (e.g., when adding a row that FKs into a vocabulary).

**Cause**: The term was not added to the vocabulary, or the name does not match exactly.

**Solution**:
- **Search first with `rag_search`**: Use `rag_search("term meaning or synonyms", doc_type="catalog-schema")` to find vocabulary terms. The RAG index includes term descriptions and synonyms, so fuzzy matching works (e.g., searching for "X-ray" will surface a term named `Xray` if it has the synonym set).
- Read the relevant vocabulary resource to list existing terms. Vocabulary URIs follow the pattern `deriva://vocabulary/{vocab_name}` (or `deriva://vocabulary/{vocab_name}/{term_name}` for a specific term, which is synonym-aware).
- Vocabulary term names are case-sensitive.
- **Tool**: `add_term` to add the missing term to the appropriate vocabulary. See the `manage-vocabulary` skill for the full vocabulary surface.

---

## Problem: "Cannot Connect to Catalog"

**Symptom**: `connect_catalog` fails with a network error, "host not found", "connection refused", or an SSL/certificate error.

**Cause**: Network unreachable, hostname typo, server down, or your local CA store is missing the issuing CA for the host's certificate.

**Solution**:
- Verify the hostname spelling. Read the registry resource (`deriva://registry/{hostname}`) to confirm the catalog ID resolves.
- Check basic connectivity: `curl -I https://<hostname>/ermrest/` should return `200 OK`.
- For SSL/cert errors, verify your system CA bundle is current. On macOS, run `Install Certificates.command` for your Python install. For self-signed dev hosts, the host admin must give you the CA cert to add to your trust store.
- If multiple hosts are in play (e.g., a staging vs production catalog), confirm you used the right one — `connect_catalog` does not warn about ambiguity.

---

## Reference Resources

- `deriva://registry/{hostname}` — List available catalogs and aliases on a host
- `deriva://catalog/connections` — List active catalog connections in this session
- `deriva://catalog/vocabularies` — Browse vocabularies in the connected catalog (verify term existence here)

## General Debugging Tips

### Enable Verbose Logging

When using the Python API, enable verbose logging to see detailed request/response information:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Verify the Catalog Connection

Before debugging anything else, confirm the active catalog matches what you expect. The registry resource (`deriva://registry/{hostname}`) and connections resource (`deriva://catalog/connections`) are the source of truth.

### Inspect Catalog State

- Use the catalog schema resources to review the current schemas, tables, and vocabularies.
- **Tool**: `preview_table` (with `limit=1`) to quickly verify data exists in expected tables.
- **Tool**: `get_record` to fetch a known RID and confirm the row is accessible to your credential.

### Re-authenticate If Anything Smells Like Auth

If errors are inconsistent (some reads work, some don't), or operations were working in an earlier session and are now failing, re-run `deriva-globus-auth-utils login --host <hostname>` and reconnect. Token expiry is the single most common cause of mid-session failures.

## Related Skills

- **`manage-vocabulary`** *(tier-1)* — When the fix is "add the missing vocabulary term", this is the skill that owns the vocabulary CRUD surface.
- **`check-deriva-versions`** *(tier-1)* — If errors started after an update, this skill verifies the deriva-py / deriva-mcp-core / deriva plugin versions match what's expected.
- **`troubleshoot-execution`** *(tier-2, deriva-ml-skills)* — For errors specific to the DerivaML execution machinery: stuck `Running` status, `asset_file_path()` failures, upload timeouts, dataset version mismatches.
