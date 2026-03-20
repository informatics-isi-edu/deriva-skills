# Deriva ML Apps SPA Restructure Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure the deriva-ml-apps repo from 3 separate Vite projects + standalone proxy into a single installable SPA shell with app registry, served by a Python package installable via `uv`.

**Architecture:** One Vite project produces a unified SPA. A Python package (`deriva-ml-apps`) provides the CLI entry point, proxy server, and app registry API. Built-in apps are lazy-loaded SPA routes. Dynamic (Claude-generated) apps load in iframes.

**Tech Stack:** React 19, TypeScript, Vite, Tailwind CSS, shadcn/ui, React Router, Python 3.12+, `uv`

**Spec:** `~/GitHub/deriva-skills/docs/superpowers/specs/2026-03-20-deriva-ml-apps-redesign.md`

**Repos:**
- Primary: `~/GitHub/deriva-ml-apps` — all frontend and Python changes
- Follow-up (separate plans): `~/GitHub/deriva-mcp` (simplify tools), `~/GitHub/deriva-skills` (new skill)

---

## File Structure

### New files to create

```
deriva-ml-apps/
  pyproject.toml                          # Python package config (uv-installable)
  src/
    deriva_apps/
      __init__.py                         # Package init, version
      cli.py                              # CLI entry point: `deriva-ml-apps serve`
      server.py                           # HTTP server: proxy + static + API
      registry.py                         # App registry (static + dynamic)
  frontend/
    package.json                          # Single Vite project (replaces 3 separate ones)
    vite.config.ts
    tsconfig.json
    tailwind.config.js
    postcss.config.js
    index.html
    src/
      main.tsx                            # React entry point
      App.tsx                             # Shell: router, nav, catalog context
      pages/
        HomePage.tsx                      # App grid (from app-launcher/App.tsx)
        SchemaWorkbenchPage.tsx           # Lazy wrapper for schema workbench
        StorageManagerPage.tsx            # Lazy wrapper for storage manager
        DynamicAppPage.tsx                # Iframe host for dynamic apps
      components/
        AppGrid.tsx                       # App cards (from app-launcher)
        Navbar.tsx                        # Top nav with catalog picker (from app-launcher)
        ServerPanel.tsx                   # Server/catalog browser (from app-launcher)
        IframeHost.tsx                    # Iframe container for dynamic apps
      apps/
        schema-workbench/                 # Moved from schema-workbench/src/
          App.tsx
          ermrest-client.ts
          annotation-registry.ts
          annotation-io.ts
          annotation-validator.ts
          catalog-config.ts
          layout.ts
          types.ts
          components/erd/                 # Moved as-is
          components/ui/                  # Shared with root
        storage-manager/                  # Moved from storage-manager/src/
          App.tsx
          api.ts
          types.ts
          components/                     # StorageTable, ConfirmDialog
      api/
        registry.ts                       # Registry API client
        storage.ts                        # Storage API client (from storage-manager/api.ts)
      lib/
        catalog-context.tsx               # React context for hostname/catalog
        format.ts                         # Shared utilities
      components/ui/                      # Shared shadcn/ui components
```

### Files to delete (after migration)

```
schema-workbench/         # Entire directory (merged into frontend/src/apps/)
storage-manager/          # Entire directory (merged into frontend/src/apps/)
app-launcher/             # Entire directory (merged into frontend/src/pages/ + components/)
proxy.py                  # Replaced by src/deriva_apps/server.py
```

### Files to keep

```
apps.json                 # Built-in app metadata (read by registry.py)
CLAUDE.md                 # Updated for new structure
README.md                 # Updated
.github/                  # CI (updated for new build)
```

---

## Chunk 1: Python Package Foundation

### Task 1: Create pyproject.toml

**Files:**
- Create: `~/GitHub/deriva-ml-apps/pyproject.toml`

- [ ] **Step 1: Create pyproject.toml**

```toml
[project]
name = "deriva-ml-apps"
dynamic = ["version"]
description = "Web applications and proxy server for DerivaML catalogs"
requires-python = ">=3.12"
license = "Apache-2.0"
authors = [
    { name = "ISRD", email = "isrd-dev@isi.edu" },
]
dependencies = [
    "bump-my-version",
]

[project.scripts]
deriva-ml-apps = "deriva_apps.cli:main"
bump-version = "deriva_apps.version:bump"

[build-system]
requires = ["setuptools>=80", "setuptools_scm[toml]>=8", "wheel"]
build-backend = "setuptools.build_meta"

[tool.uv]
python-preference = "only-managed"

[tool.setuptools_scm]
version_scheme = "post-release"

[tool.setuptools.packages.find]
where = ["src"]

[tool.setuptools.package-data]
deriva_apps = ["static/**/*", "apps.json"]

[tool.bumpversion]
parse = "(?P<major>\\d+)\\.(?P<minor>\\d+)\\.(?P<patch>\\d+)"
serialize = ["{major}.{minor}.{patch}"]
commit = true
tag = true
tag_name = "v{new_version}"
tag_message = "Bump version: {current_version} → {new_version}"
allow_dirty = false
message = "Bump version: {current_version} → {new_version}"
post_commit_hooks = ["git push", "git push --tags"]
```

This follows the same pattern as `deriva-ml`:
- `setuptools` + `setuptools_scm` for dynamic version from git tags
- `bump-my-version` for incrementing (via `uv run bump-version patch|minor|major`)
- `uv` as the package manager
- No hardcoded version — derived from git tags at build/install time

- [ ] **Step 2: Create package directory structure**

```bash
mkdir -p ~/GitHub/deriva-ml-apps/src/deriva_apps
touch ~/GitHub/deriva-ml-apps/src/deriva_apps/__init__.py
```

- [ ] **Step 3: Commit**

```bash
cd ~/GitHub/deriva-ml-apps
git add pyproject.toml src/
git commit -m "feat: add Python package skeleton for uv-installable app server"
```

### Task 2: Create the app registry

**Files:**
- Create: `~/GitHub/deriva-ml-apps/src/deriva_apps/registry.py`
- Test: `~/GitHub/deriva-ml-apps/tests/test_registry.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_registry.py
import json
import pytest
from pathlib import Path
from deriva_apps.registry import AppRegistry


@pytest.fixture
def apps_json(tmp_path):
    """Create a minimal apps.json for testing."""
    data = {
        "apps": [
            {
                "id": "schema-workbench",
                "name": "Schema Workbench",
                "description": "ER diagram browser",
                "requires_catalog": True,
                "builtin": True,
            }
        ]
    }
    path = tmp_path / "apps.json"
    path.write_text(json.dumps(data))
    return path


@pytest.fixture
def registry(apps_json, tmp_path):
    return AppRegistry(apps_json=apps_json, dynamic_dir=tmp_path / "dynamic")


class TestAppRegistry:
    def test_list_apps_includes_builtins(self, registry):
        apps = registry.list_apps()
        assert len(apps) == 1
        assert apps[0]["id"] == "schema-workbench"

    def test_register_dynamic_app(self, registry, tmp_path):
        app_dir = tmp_path / "my-app"
        app_dir.mkdir()
        (app_dir / "index.html").write_text("<html></html>")

        registry.register(
            app_id="my-viz",
            name="My Visualization",
            description="Custom chart",
            path=str(app_dir),
        )
        apps = registry.list_apps()
        assert len(apps) == 2
        assert any(a["id"] == "my-viz" for a in apps)

    def test_unregister_dynamic_app(self, registry, tmp_path):
        app_dir = tmp_path / "my-app"
        app_dir.mkdir()
        (app_dir / "index.html").write_text("<html></html>")

        registry.register("my-viz", "My Viz", "desc", str(app_dir))
        registry.unregister("my-viz")
        apps = registry.list_apps()
        assert len(apps) == 1

    def test_cannot_unregister_builtin(self, registry):
        with pytest.raises(ValueError, match="built-in"):
            registry.unregister("schema-workbench")

    def test_registry_persists(self, apps_json, tmp_path):
        dynamic_dir = tmp_path / "dynamic"
        reg1 = AppRegistry(apps_json=apps_json, dynamic_dir=dynamic_dir)

        app_dir = tmp_path / "my-app"
        app_dir.mkdir()
        (app_dir / "index.html").write_text("<html></html>")
        reg1.register("my-viz", "My Viz", "desc", str(app_dir))

        # New instance should load persisted state
        reg2 = AppRegistry(apps_json=apps_json, dynamic_dir=dynamic_dir)
        apps = reg2.list_apps()
        assert len(apps) == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ~/GitHub/deriva-ml-apps && uv run pytest tests/test_registry.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Implement AppRegistry**

```python
# src/deriva_apps/registry.py
"""App registry: static (built-in) + dynamic (runtime-registered) apps."""

from __future__ import annotations

import json
from pathlib import Path


class AppRegistry:
    """Manages the catalog of available web applications.

    Built-in apps come from apps.json (shipped with the package).
    Dynamic apps are registered at runtime and persisted to a JSON file.
    """

    def __init__(self, apps_json: Path, dynamic_dir: Path) -> None:
        self._apps_json = apps_json
        self._dynamic_dir = dynamic_dir
        self._dynamic_file = dynamic_dir / "registry.json"
        self._builtin: list[dict] = []
        self._dynamic: list[dict] = []

        self._load_builtin()
        self._load_dynamic()

    def _load_builtin(self) -> None:
        if self._apps_json.exists():
            data = json.loads(self._apps_json.read_text())
            self._builtin = data.get("apps", [])
            for app in self._builtin:
                app["builtin"] = True
                app["dynamic"] = False

    def _load_dynamic(self) -> None:
        if self._dynamic_file.exists():
            self._dynamic = json.loads(self._dynamic_file.read_text())
        else:
            self._dynamic = []

    def _save_dynamic(self) -> None:
        self._dynamic_dir.mkdir(parents=True, exist_ok=True)
        self._dynamic_file.write_text(json.dumps(self._dynamic, indent=2))

    def list_apps(self) -> list[dict]:
        """Return all registered apps (built-in + dynamic)."""
        return self._builtin + self._dynamic

    def get_app(self, app_id: str) -> dict | None:
        """Look up a single app by ID."""
        for app in self.list_apps():
            if app["id"] == app_id:
                return app
        return None

    def register(
        self,
        app_id: str,
        name: str,
        description: str,
        path: str,
    ) -> dict:
        """Register a dynamic app."""
        if any(a["id"] == app_id for a in self.list_apps()):
            raise ValueError(f"App '{app_id}' already exists")

        app = {
            "id": app_id,
            "name": name,
            "description": description,
            "path": path,
            "builtin": False,
            "dynamic": True,
        }
        self._dynamic.append(app)
        self._save_dynamic()
        return app

    def unregister(self, app_id: str) -> None:
        """Remove a dynamic app. Cannot remove built-in apps."""
        if any(a["id"] == app_id for a in self._builtin):
            raise ValueError(f"Cannot unregister built-in app '{app_id}'")

        self._dynamic = [a for a in self._dynamic if a["id"] != app_id]
        self._save_dynamic()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd ~/GitHub/deriva-ml-apps && uv run pytest tests/test_registry.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add src/deriva_apps/registry.py tests/test_registry.py
git commit -m "feat: add AppRegistry with static + dynamic app support"
```

### Task 3: Create the server (proxy + API + static serving)

**Files:**
- Create: `~/GitHub/deriva-ml-apps/src/deriva_apps/server.py`
- Test: `~/GitHub/deriva-ml-apps/tests/test_server.py`

- [ ] **Step 1: Write failing tests for API endpoints**

```python
# tests/test_server.py
import json
import threading
import time
import urllib.request
import pytest
from pathlib import Path
from deriva_apps.server import create_server


@pytest.fixture
def server_with_registry(tmp_path):
    """Start a test server with a minimal registry."""
    apps_json = tmp_path / "apps.json"
    apps_json.write_text(json.dumps({"apps": [
        {"id": "test-app", "name": "Test", "description": "A test app",
         "requires_catalog": False, "builtin": True}
    ]}))

    # Create a minimal static dir with index.html
    static_dir = tmp_path / "dist"
    static_dir.mkdir()
    (static_dir / "index.html").write_text("<html><body>SPA Shell</body></html>")

    srv = create_server(
        backend="https://example.org",
        static_dir=static_dir,
        apps_json=apps_json,
        dynamic_dir=tmp_path / "dynamic",
        port=0,  # auto-select
    )
    port = srv.server_address[1]
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{port}", srv
    srv.shutdown()


class TestRegistryAPI:
    def test_get_registry(self, server_with_registry):
        url, _ = server_with_registry
        with urllib.request.urlopen(f"{url}/api/registry") as resp:
            data = json.loads(resp.read())
            assert "apps" in data
            assert len(data["apps"]) == 1
            assert data["apps"][0]["id"] == "test-app"

    def test_register_dynamic_app(self, server_with_registry, tmp_path):
        url, _ = server_with_registry
        app_dir = tmp_path / "custom"
        app_dir.mkdir()
        (app_dir / "index.html").write_text("<html></html>")

        body = json.dumps({
            "id": "custom-viz",
            "name": "Custom Viz",
            "description": "A viz",
            "path": str(app_dir),
        }).encode()
        req = urllib.request.Request(
            f"{url}/api/registry",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())
            assert data["status"] == "registered"

    def test_serves_index_html(self, server_with_registry):
        url, _ = server_with_registry
        with urllib.request.urlopen(url) as resp:
            body = resp.read().decode()
            assert "SPA Shell" in body
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ~/GitHub/deriva-ml-apps && uv run pytest tests/test_server.py -v`
Expected: FAIL

- [ ] **Step 3: Implement server.py**

Port the existing `proxy.py` into `src/deriva_apps/server.py` with these additions:
- `/api/registry` GET/POST/DELETE endpoints backed by `AppRegistry`
- `/api/storage` endpoints (ported from MCP proxy)
- `/apps/{id}/` serving for dynamic app static files
- `create_server()` factory function for testability

The proxy logic (forwarding `/ermrest`, `/authn`, `/chaise` to backend) stays the same as the existing `proxy.py`. The key changes are:
- Handler gets an `AppRegistry` instance
- New API routes for registry management
- Dynamic app static file serving

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd ~/GitHub/deriva-ml-apps && uv run pytest tests/test_server.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/deriva_apps/server.py tests/test_server.py
git commit -m "feat: add HTTP server with proxy, registry API, and static serving"
```

### Task 4: Create the CLI entry point

**Files:**
- Create: `~/GitHub/deriva-ml-apps/src/deriva_apps/cli.py`

- [ ] **Step 1: Implement CLI**

```python
# src/deriva_apps/cli.py
"""CLI entry point: deriva-ml-apps serve."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _find_static_dir() -> Path:
    """Find the built SPA dist directory.

    Searches in order:
    1. frontend/dist relative to this file (development)
    2. Package data share/deriva-ml-apps/dist (installed)
    """
    # Development: repo layout
    repo_dist = Path(__file__).parent.parent.parent / "frontend" / "dist"
    if (repo_dist / "index.html").exists():
        return repo_dist

    # Installed: package data
    import importlib.resources
    try:
        pkg_dist = importlib.resources.files("deriva_apps") / ".." / ".." / "share" / "deriva-ml-apps" / "dist"
        if Path(str(pkg_dist) + "/index.html").exists():
            return Path(str(pkg_dist))
    except Exception:
        pass

    print("Error: Cannot find built SPA. Run 'cd frontend && pnpm build' first.", file=sys.stderr)
    sys.exit(1)


def _find_apps_json() -> Path:
    """Find apps.json."""
    repo_apps = Path(__file__).parent.parent.parent / "apps.json"
    if repo_apps.exists():
        return repo_apps

    import importlib.resources
    try:
        pkg_apps = importlib.resources.files("deriva_apps") / ".." / ".." / "share" / "deriva-ml-apps" / "apps.json"
        if Path(str(pkg_apps)).exists():
            return Path(str(pkg_apps))
    except Exception:
        pass

    return repo_apps  # Fall back, will be handled by registry


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="deriva-ml-apps",
        description="Serve DerivaML web applications with a Deriva proxy",
    )
    sub = parser.add_subparsers(dest="command")

    serve = sub.add_parser("serve", help="Start the app server")
    serve.add_argument("--backend", required=True, help="Deriva server hostname")
    serve.add_argument("--port", type=int, default=8080, help="Port (default: 8080)")
    serve.add_argument("--bind", default="127.0.0.1", help="Bind address")

    args = parser.parse_args()
    if args.command != "serve":
        parser.print_help()
        sys.exit(1)

    from deriva_apps.server import create_server

    static_dir = _find_static_dir()
    apps_json = _find_apps_json()
    dynamic_dir = Path.home() / ".deriva-ml" / "apps"

    srv = create_server(
        backend=args.backend,
        static_dir=static_dir,
        apps_json=apps_json,
        dynamic_dir=dynamic_dir,
        port=args.port,
        bind=args.bind,
    )

    port = srv.server_address[1]
    url = f"http://{args.bind}:{port}"
    print(f"DerivaML Apps: {url}")
    print(f"Backend: {args.backend}")
    print("Press Ctrl+C to stop\n")

    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        srv.server_close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Test CLI manually**

```bash
cd ~/GitHub/deriva-ml-apps
uv run deriva-ml-apps serve --backend dev.eye-ai.org --port 8080
# Should print URL and serve (Ctrl+C to stop)
```

- [ ] **Step 3: Commit**

```bash
git add src/deriva_apps/cli.py
git commit -m "feat: add CLI entry point for deriva-ml-apps serve"
```

---

## Chunk 2: Frontend SPA Unification

### Task 5: Create unified Vite project

**Files:**
- Create: `~/GitHub/deriva-ml-apps/frontend/package.json`
- Create: `~/GitHub/deriva-ml-apps/frontend/vite.config.ts`
- Create: `~/GitHub/deriva-ml-apps/frontend/tsconfig.json`
- Create: `~/GitHub/deriva-ml-apps/frontend/tailwind.config.js`
- Create: `~/GitHub/deriva-ml-apps/frontend/postcss.config.js`
- Create: `~/GitHub/deriva-ml-apps/frontend/index.html`

- [ ] **Step 1: Create frontend directory and init**

```bash
cd ~/GitHub/deriva-ml-apps
mkdir -p frontend/src
```

- [ ] **Step 2: Create package.json**

Base on the schema-workbench `package.json` since it has the most dependencies. Merge in any unique deps from the other two apps. Add `react-router-dom` for routing.

```json
{
  "name": "deriva-ml-apps",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "lint": "eslint .",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "react-router-dom": "^7.0.0",
    "@xyflow/react": "^12.0.0",
    "@dagrejs/dagre": "^1.1.0",
    "@rjsf/core": "^5.0.0",
    "@rjsf/utils": "^5.0.0",
    "@rjsf/validator-ajv8": "^5.0.0",
    "lucide-react": "^0.400.0",
    "zod": "^3.0.0"
  }
}
```

Exact versions should match the current apps. Run `pnpm install` after creating.

- [ ] **Step 3: Create vite.config.ts, tsconfig.json, tailwind.config.js, postcss.config.js**

Copy from schema-workbench and adjust paths. The vite config should output to `frontend/dist/`.

- [ ] **Step 4: Create index.html**

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>DerivaML Apps</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 5: Install dependencies**

```bash
cd ~/GitHub/deriva-ml-apps/frontend && pnpm install
```

- [ ] **Step 6: Commit**

```bash
git add frontend/
git commit -m "feat: create unified Vite project for SPA shell"
```

### Task 6: Create SPA shell with routing

**Files:**
- Create: `~/GitHub/deriva-ml-apps/frontend/src/main.tsx`
- Create: `~/GitHub/deriva-ml-apps/frontend/src/App.tsx`
- Create: `~/GitHub/deriva-ml-apps/frontend/src/lib/catalog-context.tsx`
- Create: `~/GitHub/deriva-ml-apps/frontend/src/pages/HomePage.tsx`
- Create: `~/GitHub/deriva-ml-apps/frontend/src/pages/DynamicAppPage.tsx`

- [ ] **Step 1: Create catalog context**

```typescript
// frontend/src/lib/catalog-context.tsx
import { createContext, useContext, useState, ReactNode } from "react";

interface CatalogContext {
  hostname: string | null;
  catalogId: string | null;
  setHostname: (h: string) => void;
  setCatalogId: (c: string) => void;
}

const CatalogCtx = createContext<CatalogContext | null>(null);

export function CatalogProvider({ children }: { children: ReactNode }) {
  const [hostname, setHostname] = useState<string | null>(null);
  const [catalogId, setCatalogId] = useState<string | null>(null);

  return (
    <CatalogCtx.Provider value={{ hostname, catalogId, setHostname, setCatalogId }}>
      {children}
    </CatalogCtx.Provider>
  );
}

export function useCatalog() {
  const ctx = useContext(CatalogCtx);
  if (!ctx) throw new Error("useCatalog must be used within CatalogProvider");
  return ctx;
}
```

- [ ] **Step 2: Create App.tsx with router**

```typescript
// frontend/src/App.tsx
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Suspense, lazy } from "react";
import { CatalogProvider } from "./lib/catalog-context";
import HomePage from "./pages/HomePage";
import DynamicAppPage from "./pages/DynamicAppPage";

const SchemaWorkbench = lazy(() => import("./apps/schema-workbench/App"));
const StorageManager = lazy(() => import("./apps/storage-manager/App"));

export default function App() {
  return (
    <CatalogProvider>
      <BrowserRouter>
        <Suspense fallback={<div className="p-8">Loading...</div>}>
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/schema-workbench" element={<SchemaWorkbench />} />
            <Route path="/storage-manager" element={<StorageManager />} />
            <Route path="/apps/:appId" element={<DynamicAppPage />} />
          </Routes>
        </Suspense>
      </BrowserRouter>
    </CatalogProvider>
  );
}
```

- [ ] **Step 3: Create HomePage (move from app-launcher)**

Move the content from `app-launcher/src/App.tsx` and its components into `frontend/src/pages/HomePage.tsx`. Adapt the app-launcher components to use the registry API at `/api/registry`.

- [ ] **Step 4: Create DynamicAppPage (iframe host)**

```typescript
// frontend/src/pages/DynamicAppPage.tsx
import { useParams } from "react-router-dom";
import { useCatalog } from "../lib/catalog-context";

export default function DynamicAppPage() {
  const { appId } = useParams<{ appId: string }>();
  const { hostname, catalogId } = useCatalog();

  const params = new URLSearchParams();
  if (hostname) params.set("host", hostname);
  if (catalogId) params.set("catalog", catalogId);
  const hash = params.toString() ? `#${params}` : "";

  return (
    <iframe
      src={`/apps/${appId}/index.html${hash}`}
      className="w-full h-screen border-0"
      title={appId}
    />
  );
}
```

- [ ] **Step 5: Verify it builds**

```bash
cd ~/GitHub/deriva-ml-apps/frontend && pnpm build
```

- [ ] **Step 6: Commit**

```bash
git add frontend/src/
git commit -m "feat: create SPA shell with router, catalog context, and page stubs"
```

### Task 7: Migrate schema-workbench into SPA

**Files:**
- Create: `~/GitHub/deriva-ml-apps/frontend/src/apps/schema-workbench/` (moved from `schema-workbench/src/`)

- [ ] **Step 1: Copy schema-workbench source**

```bash
cp -r ~/GitHub/deriva-ml-apps/schema-workbench/src/* ~/GitHub/deriva-ml-apps/frontend/src/apps/schema-workbench/
```

- [ ] **Step 2: Update imports**

The schema-workbench components import from relative paths and use their own `components/ui/`. Update imports to use the shared UI components where possible, and adjust any absolute paths.

- [ ] **Step 3: Export the App component**

Ensure `frontend/src/apps/schema-workbench/App.tsx` has a default export that can be lazy-loaded. It should accept catalog context from props or use the `useCatalog` hook.

- [ ] **Step 4: Verify build**

```bash
cd ~/GitHub/deriva-ml-apps/frontend && pnpm build
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/apps/schema-workbench/
git commit -m "feat: migrate schema-workbench into unified SPA"
```

### Task 8: Migrate storage-manager into SPA

**Files:**
- Create: `~/GitHub/deriva-ml-apps/frontend/src/apps/storage-manager/` (moved from `storage-manager/src/`)

- [ ] **Step 1: Copy storage-manager source**

```bash
cp -r ~/GitHub/deriva-ml-apps/storage-manager/src/* ~/GitHub/deriva-ml-apps/frontend/src/apps/storage-manager/
```

- [ ] **Step 2: Update imports and exports**

Same as schema-workbench. Update relative imports, share UI components.

- [ ] **Step 3: Verify build**

```bash
cd ~/GitHub/deriva-ml-apps/frontend && pnpm build
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/apps/storage-manager/
git commit -m "feat: migrate storage-manager into unified SPA"
```

### Task 9: Remove old app directories

- [ ] **Step 1: Remove old directories**

```bash
cd ~/GitHub/deriva-ml-apps
rm -rf schema-workbench/ storage-manager/ app-launcher/ proxy.py
```

- [ ] **Step 2: Update .gitignore**

Add `frontend/node_modules/` and `frontend/dist/` to `.gitignore`.

- [ ] **Step 3: Update CLAUDE.md**

Update the project overview, directory structure, and commands to reflect the new layout. Specify `uv` for Python installation.

- [ ] **Step 4: Verify full build**

```bash
cd ~/GitHub/deriva-ml-apps/frontend && pnpm build
cd ~/GitHub/deriva-ml-apps && uv run deriva-ml-apps serve --backend dev.eye-ai.org
# Open http://localhost:8080 — should show homepage with app grid
```

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "refactor: remove old app directories, update docs for SPA layout"
```

---

## Chunk 3: Integration Testing

### Task 10: End-to-end test

- [ ] **Step 1: Build the frontend**

```bash
cd ~/GitHub/deriva-ml-apps/frontend && pnpm build
```

- [ ] **Step 2: Start the server**

```bash
cd ~/GitHub/deriva-ml-apps && uv run deriva-ml-apps serve --backend dev.eye-ai.org --port 8080
```

- [ ] **Step 3: Verify homepage**

Open `http://localhost:8080` — should show the app grid with built-in apps.

- [ ] **Step 4: Verify schema workbench**

Click "Schema Workbench" — should navigate to `/schema-workbench` and load the ERD viewer.

- [ ] **Step 5: Verify storage manager**

Click "Storage Manager" — should navigate to `/storage-manager` and show the storage table.

- [ ] **Step 6: Verify registry API**

```bash
curl http://localhost:8080/api/registry | python3 -m json.tool
# Should list all built-in apps
```

- [ ] **Step 7: Verify dynamic app registration**

```bash
# Create a test app
mkdir -p /tmp/test-app
echo '<html><body>Hello from dynamic app</body></html>' > /tmp/test-app/index.html

# Register it
curl -X POST http://localhost:8080/api/registry \
  -H 'Content-Type: application/json' \
  -d '{"id":"test-app","name":"Test App","description":"Testing","path":"/tmp/test-app"}'

# Verify it appears in the grid
curl http://localhost:8080/api/registry | python3 -m json.tool

# Open it
open http://localhost:8080/apps/test-app/
```

- [ ] **Step 8: Verify proxy**

With the server running against a real backend, verify that the SPA can make ERMrest calls (check Network tab in browser devtools).

- [ ] **Step 9: Final commit**

```bash
git add -A
git commit -m "test: verify end-to-end SPA shell with proxy and registry"
```
