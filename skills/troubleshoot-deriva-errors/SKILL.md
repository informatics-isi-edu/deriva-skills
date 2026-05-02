---
name: troubleshoot-deriva-errors
description: "Use when any Deriva catalog operation fails with auth, permissions, missing record, invalid RID, vocabulary term not found, or generic catalog connection / state errors. Also covers checking and updating the three core Deriva components (deriva-py, deriva-mcp-core MCP server, deriva plugin) — version mismatches between them are a common cause of confusing errors. Triggers on: 'permission denied', 'auth error', 'globus login', 'invalid RID', 'record not found', 'wrong catalog', 'vocabulary term missing', 'connect failed', 'catalog connection', 'unauthorized', 'check versions', 'am I up to date', 'update deriva', 'what version', 'upgrade packages'."
user-invocable: false
disable-model-invocation: true
---

# Troubleshooting Generic Deriva Catalog Errors

This guide covers errors that surface in any Deriva catalog operation — auth, permissions, RID lookup failures, vocabulary term mismatches, connection state errors. It uses only the generic `deriva-mcp-core` MCP tools and the `deriva-py` Python API; no domain-layer machinery is required to reproduce or fix any of the errors documented here.

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
- After a fresh `login`, the next MCP tool call automatically picks up the new credential — the MCP server reads credentials per call, so there is no reconnect step.

---

## Problem: "Invalid RID"

**Symptom**: A tool rejects a RID value or returns "not found".

**Cause**: The RID is malformed, belongs to a different table than expected, or refers to a deleted record.

**Solution**:
- **Tool**: `get_entities(hostname=..., catalog_id=..., schema=..., table=..., filter={"RID": "..."})` to check whether the RID exists in the expected table. An empty result means the RID does not exist there. There is no single-tool cross-table RID lookup; query each candidate table.
- RIDs are case-sensitive alphanumeric strings (e.g., `1-A2B3`). Ensure there are no extra spaces or characters.
- If the RID comes from a different catalog, it will not resolve in the current catalog. Pass the correct `hostname=` and `catalog_id=` to your tool call — there is no implicit "current catalog" on the MCP server.
- If the RID was recently created, it should be visible immediately — there is no propagation delay for catalog reads.

---

## Problem: "Record Not Found"

**Symptom**: Attempting to read a record by RID returns an error or empty result.

**Cause**: Wrong catalog connection, the record was deleted, or the RID is incorrect.

**Solution**:
- **Search first with `rag_search`**: Use `rag_search("description of what you want", doc_type="catalog-data")` to find records by description. This is the best way to discover the correct RID when you are unsure.
- Verify the `hostname=` and `catalog_id=` arguments you are passing match the catalog where you expect the RID to exist.
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
- If multiple hosts are in play (e.g., a staging vs production catalog), double-check the `hostname=` argument on the failing call — the server has no implicit "active host" to fall back to.

---

## Reference Resources

- `get_catalog_info(hostname, catalog_id)` — Verify the catalog exists and your credential reaches it
- `server_status(hostname=None)` — MCP server health + framework version + the list of loaded plugins
- `catalog_tables(hostname, catalog_id)` — List all tables in the catalog (filter for vocabulary tables to verify term existence)

## General Debugging Tips

### Enable Verbose Logging

When using the Python API, enable verbose logging to see detailed request/response information:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Verify the Catalog Connection

The MCP server is stateless — there is no "active catalog". Every tool call takes `hostname=` and `catalog_id=` arguments, so confirm the values you're passing match what you expect. Use `get_catalog_info(hostname=..., catalog_id=...)` to verify the target catalog exists and your credential reaches it.

### Inspect Catalog State

- Use the catalog schema resources to review the current schemas, tables, and vocabularies.
- **Tool**: `get_table_sample_data(hostname=..., catalog_id=..., schema=..., table=...)` to quickly verify data exists in expected tables.
- **Tool**: `get_entities(hostname=..., catalog_id=..., schema=..., table=..., filter={"RID": "..."})` to fetch a known RID and confirm the row is accessible to your credential.

### Re-authenticate If Anything Smells Like Auth

If errors are inconsistent (some reads work, some don't), or operations were working in an earlier session and are now failing, re-run `deriva-globus-auth-utils login --host <hostname>` and reconnect. Token expiry is the single most common cause of mid-session failures.

## Versioning and updates

If errors started "out of nowhere" — especially "tool not found," "unknown parameter," or behavior that doesn't match the documentation — the cause is often a version mismatch between the three core Deriva components (the `deriva-py` Python client, the `deriva-mcp-core` MCP server, and the `deriva` Claude Code plugin). They each have their own update path; there is no unified update command.

**The short version of the fix:**

- **Check** which version is running: `server_status(hostname=...)` for the MCP server; `uv pip show deriva-py` for the Python library; `cat ~/.claude/plugins/cache/deriva-plugins/deriva/*/plugin.json` for the plugin.
- **Update the plugin** by setting `"autoUpdate": true` in `~/.claude/settings.json` (for the `deriva-plugins` marketplace) and restarting Claude Code.
- **Update the MCP server** by `docker pull ghcr.io/informatics-isi-edu/deriva-mcp-core:latest && docker restart deriva-mcp-core` (Docker), or `uv lock --upgrade-package deriva-mcp-core && uv sync` then restart the server (native install).
- **Update deriva-py** in the project that uses it: `uv lock --upgrade-package deriva-py && uv sync`.

For full details — the per-component check / latest-release / update tables, why there's no unified update command, and the specific error patterns that point at a version mismatch (so you know when to suspect this rather than a logic error in your call) — see `references/versioning.md`.

## Related Skills

- **`/deriva:manage-vocabulary`** — When the fix is "add the missing vocabulary term", this is the skill that owns the vocabulary CRUD surface.
- **`/deriva:load-data`** — When inserts, updates, asset uploads, or `deriva-upload-cli` runs fail with FK / vocab-term / asset-mapping errors, the load-side discipline (FK targets first, vocabulary terms first, idempotency, dry-run) usually catches the cause.
