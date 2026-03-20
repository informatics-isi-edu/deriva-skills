# Deriva ML Apps: SPA Shell + App Registry Redesign

## Goal

Replace the current scattered proxy/app architecture with a single installable SPA that serves as the homepage for all DerivaML web tools — built-in apps, Claude-generated apps, and future additions.

## Current State

- `deriva-ml-apps/` repo has 3 standalone React apps (app-launcher, schema-workbench, storage-manager) + a standalone proxy
- `deriva-mcp/` has a copy of the proxy (700+ lines) with extra API endpoints
- MCP tools know too much about proxy internals (import ProxyHandler, manage threads directly)
- Each app is a separate Vite project that must be built independently
- No way to dynamically add apps at runtime

## Design

### Architecture

```
Browser → http://localhost:8080
  /                     → Homepage: app grid with registered apps
  /schema-workbench     → Schema workbench (SPA route)
  /storage-manager      → Storage manager (SPA route)
  /apps/custom-abc123   → Claude-generated app (iframe)
  /ermrest/...          → Proxied to Deriva backend
  /authn/...            → Proxied to Deriva backend
  /api/registry         → App registry API
  /api/storage          → Storage management API
```

Single process. Single port. One SPA shell serves everything.

### Components

**1. SPA Shell** — The main React application

- Homepage at `/` shows a grid of all registered apps
- Catalog picker in the nav bar (select hostname + catalog)
- Built-in apps are routes within the SPA (code-split, lazy-loaded)
- Claude-generated apps load in iframes at `/apps/{id}/`
- The shell passes catalog context to apps via URL params or postMessage

**2. Proxy** — Lives in this repo, serves the SPA + proxies Deriva

- Serves static files from `dist/`
- Proxies `/ermrest`, `/authn`, `/chaise` to the configured backend
- Serves `/api/registry` for app discovery
- Serves `/api/storage` for storage management
- Serves `/api/apps/{id}/` for Claude-generated app static files
- Single source of truth — no copy in deriva-mcp

**3. App Registry** — Dynamic app discovery

- Built-in apps defined in `apps.json` (shipped with package)
- Dynamic apps registered at runtime via `POST /api/registry`
- Dynamic app files stored in `~/.deriva-ml/apps/{id}/`
- Registry state persisted to `~/.deriva-ml/app-registry.json`

**4. CLI Entry Point** — Installable via `uv`

```bash
# Install
uv pip install deriva-ml-apps

# Run
deriva-ml-apps serve --backend dev.example.org --port 8080

# Or with uv run from the repo
uv run deriva-ml-apps serve --backend dev.example.org
```

### MCP Interface

The MCP server's interaction is minimal — it just starts/stops the server and manages the registry:

```python
# In deriva-mcp tools:
import subprocess

# Start the app server
proc = subprocess.Popen(["deriva-ml-apps", "serve", "--backend", hostname, "--port", "0"])

# Register a Claude-generated app
requests.post("http://localhost:8080/api/registry", json={
    "id": "analysis-abc",
    "name": "Custom Analysis",
    "description": "Generated visualization for dataset 28CT",
    "path": "/path/to/built/app",
    "dynamic": True,
})

# List available apps
requests.get("http://localhost:8080/api/registry")

# Remove a dynamic app
requests.delete("http://localhost:8080/api/registry/analysis-abc")
```

MCP tools in `deriva-mcp/tools/devtools.py` shrink to:
- `start_app_server(hostname, catalog_id, port)` — subprocess the CLI
- `stop_app_server()` — terminate the subprocess
- `register_app(id, name, path, description)` — POST to registry
- `list_apps()` — GET from registry
- `open_app(app_id)` — return the URL for a specific app

The 700-line proxy.py in deriva-mcp gets deleted.

### Claude-Generated Apps

When Claude needs to create a custom visualization:

1. Claude generates a self-contained React/HTML app
2. Builds it (if React) or just writes HTML (for simple cases)
3. Drops the output in `~/.deriva-ml/apps/{id}/`
4. Calls `register_app()` MCP tool
5. Returns the URL `http://localhost:8080/apps/{id}/`

The SPA shell shows the new app in the homepage grid. Clicking it loads it in an iframe. The iframe has access to the same proxy (same origin), so it can call `/ermrest` directly.

### Built-in App Migration

The existing apps (schema-workbench, storage-manager) become lazy-loaded route modules within the SPA shell rather than separate Vite projects:

```
src/
  App.tsx              # Shell: nav, catalog picker, router
  pages/
    Home.tsx           # App grid homepage
    SchemaWorkbench/   # Existing schema-workbench code
    StorageManager/    # Existing storage-manager code
  components/
    AppGrid.tsx        # Card grid of registered apps
    CatalogPicker.tsx  # Hostname + catalog selector
    IframeHost.tsx     # Hosts dynamic apps in iframes
  api/
    registry.ts        # Registry API client
    proxy.ts           # Storage API client
```

This is a monolith SPA — one `pnpm build` produces one `dist/` directory.

### Package Structure

```
deriva-ml-apps/
  pyproject.toml           # uv-installable package
  src/
    deriva_apps/
      __init__.py
      cli.py               # CLI entry point: `deriva-ml-apps serve`
      proxy.py             # Proxy server (the one source of truth)
      registry.py          # App registry (static + dynamic)
  frontend/
    package.json           # Single Vite project
    src/
      App.tsx
      pages/...
    dist/                  # Built SPA (shipped as package data)
  apps.json                # Built-in app metadata
```

### Registry API

```
GET  /api/registry
  → { "apps": [...], "backend": "dev.example.org" }

POST /api/registry
  Body: { "id": "custom-viz", "name": "...", "description": "...", "path": "/abs/path" }
  → { "status": "registered", "url": "/apps/custom-viz/" }

DELETE /api/registry/{id}
  → { "status": "removed" }
  (Only works for dynamic apps, not built-in)
```

### Catalog Context

Apps need to know which catalog they're talking to. The proxy already handles routing `/ermrest` to the right backend. For app-level context:

- URL hash params: `#host=dev.example.org&catalog=52`
- The SPA shell reads these and passes them to child routes/iframes
- When the user changes catalog in the picker, the URL updates and apps reload

### What Changes in Each Repo

**deriva-ml-apps:**
- Merge 3 separate Vite projects into one SPA
- Add Python package with CLI + proxy + registry
- Add `pyproject.toml` for `uv` installation
- Proxy becomes the single source of truth

**deriva-mcp:**
- Delete `src/deriva_mcp/proxy.py` (700 lines)
- Simplify `tools/devtools.py` to subprocess calls + HTTP requests
- Add `deriva-ml-apps` as a dependency (or discover it on PATH)

**deriva-skills:**
- Update `browse-erd` skill to use new `open_app("schema-workbench")` tool
- Update `manage-storage` skill to mention Storage Manager app
- Update CLAUDE.md files to specify `uv` for installation

### Resolved Decisions

1. **No hot reload for dynamic apps.** Simple iframe reload when Claude updates an app. Hot reload adds complexity for minimal gain — Claude can tell the user "refresh to see changes."

2. **No theming/branding.** Plain functional UI. Add later if needed.

3. **One backend per server instance.** If you need two different Deriva servers, start two instances on different ports. Keeps the proxy simple.
