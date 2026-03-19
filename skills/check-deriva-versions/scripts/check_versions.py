#!/usr/bin/env python3
"""Check and update the DerivaML ecosystem.

Checks installed versions of deriva-ml, deriva-skills plugin, and the MCP
server against the latest releases. Can optionally perform updates.

Usage:
    python check_versions.py              # Check only
    python check_versions.py --update     # Check and update outdated components
    python check_versions.py --json       # Output as JSON

Exit codes:
    0 - Check completed (components may be outdated or up to date)
    1 - Update failed (only when --update is used)
    2 - Error checking versions
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, asdict, field
from pathlib import Path


PLUGIN_CACHE_DIR = Path.home() / ".claude" / "plugins" / "cache" / "deriva-plugins" / "deriva"
SKILLS_GITHUB_REPO = "informatics-isi-edu/deriva-skills"
MCP_GITHUB_REPO = "informatics-isi-edu/deriva-mcp"


@dataclass
class VersionStatus:
    component: str
    installed: str | None
    latest: str | None
    up_to_date: bool | None
    message: str
    update_commands: list[str] = field(default_factory=list)
    updated: bool = False
    update_message: str = ""


def run_cmd(
    cmd: list[str], capture: bool = True, timeout: int = 120, cwd: str | None = None
) -> subprocess.CompletedProcess:
    """Run a command and return the result."""
    return subprocess.run(
        cmd, capture_output=capture, text=True, timeout=timeout, cwd=cwd
    )


def get_installed_version(package: str) -> str | None:
    """Get the installed version of a Python package.

    Tries in-process importlib.metadata first (works in any Python environment),
    then falls back to 'uv run' for projects that use uv.
    """
    # Try in-process first — works regardless of uv/pip/conda
    try:
        from importlib.metadata import version, PackageNotFoundError
        try:
            return version(package)
        except PackageNotFoundError:
            pass
    except ImportError:
        pass

    # Fall back to uv if available and we're in a uv project
    if shutil.which("uv"):
        try:
            result = run_cmd(
                ["uv", "run", "python", "-c",
                 f"from importlib.metadata import version; print(version('{package}'))"],
                timeout=30,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

    # Fall back to pip
    if shutil.which("pip"):
        try:
            result = run_cmd(
                ["pip", "show", package],
                timeout=15,
            )
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    if line.startswith("Version:"):
                        return line.split(":", 1)[1].strip()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

    return None


def get_latest_git_tag(repo: str) -> str | None:
    """Get the latest semver tag from a GitHub repository.

    Args:
        repo: GitHub repo in 'owner/name' format.
    """
    if not shutil.which("git"):
        return None

    try:
        result = run_cmd(
            ["git", "ls-remote", "--tags", "--sort=-v:refname",
             f"https://github.com/{repo}.git", "v*"],
            timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            for line in result.stdout.strip().split("\n"):
                ref = line.split("\t")[1] if "\t" in line else ""
                if ref.endswith("^{}"):
                    continue
                tag = ref.replace("refs/tags/", "")
                if re.match(r"v\d+\.\d+\.\d+$", tag):
                    return tag
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def extract_base_version(version_str: str) -> str:
    """Extract the base semver version from a setuptools_scm version string.

    Examples:
        '1.18.0' -> '1.18.0'
        '1.17.17.post10+g95607b8ec' -> '1.17.17'
        '0.5.0.dev0' -> '0.5.0'
    """
    match = re.match(r"(\d+\.\d+\.\d+)", version_str)
    return match.group(1) if match else version_str


def is_dev_version(version_str: str) -> bool:
    """Check if a version string indicates a dev/post-release version."""
    return ".post" in version_str or ".dev" in version_str or "+" in version_str


def parse_semver(version: str) -> tuple[int, ...]:
    """Parse a semver string (with optional v prefix) into a tuple of ints."""
    version = version.lstrip("v")
    return tuple(int(x) for x in version.split("."))


def version_is_outdated(installed: str, latest_tag: str) -> bool | None:
    """Compare installed version against latest tag. Returns True if outdated."""
    base_installed = extract_base_version(installed)
    latest_version = latest_tag.lstrip("v")
    try:
        return parse_semver(base_installed) < parse_semver(latest_version)
    except (ValueError, IndexError):
        return None


# ---------------------------------------------------------------------------
# Component checks
# ---------------------------------------------------------------------------

def check_deriva_ml() -> VersionStatus:
    """Check if deriva-ml is up to date."""
    installed = get_installed_version("deriva_ml")
    if not installed:
        return VersionStatus("deriva-ml", None, None, None, "Not installed")

    latest_tag = get_latest_git_tag("informatics-isi-edu/deriva-ml")
    if not latest_tag:
        return VersionStatus("deriva-ml", installed, None, None,
                             "Could not fetch latest version from GitHub")

    outdated = version_is_outdated(installed, latest_tag)
    if outdated is None:
        return VersionStatus("deriva-ml", installed, latest_tag, None,
                             "Could not compare versions")

    base = extract_base_version(installed)
    if not outdated and not is_dev_version(installed):
        return VersionStatus("deriva-ml", installed, latest_tag, True, "Up to date")
    elif not outdated:
        return VersionStatus("deriva-ml", installed, latest_tag, True,
                             f"Dev version (based on {base}, latest release is {latest_tag})")
    else:
        # Build update commands based on available tools
        update_cmds = []
        if shutil.which("uv"):
            update_cmds = ["uv lock --upgrade-package deriva-ml", "uv sync"]
        elif shutil.which("pip"):
            update_cmds = ["pip install --upgrade deriva-ml"]

        return VersionStatus(
            "deriva-ml", installed, latest_tag, False,
            f"Outdated: installed {base}, latest is {latest_tag}",
            update_commands=update_cmds,
        )


def update_deriva_ml(status: VersionStatus) -> VersionStatus:
    """Update deriva-ml in the local environment."""
    if not status.update_commands:
        status.update_message = "No package manager found (uv or pip required)"
        return status

    print(f"  Updating deriva-ml to {status.latest}...")
    for cmd_str in status.update_commands:
        cmd = cmd_str.split()
        print(f"    $ {cmd_str}")
        try:
            result = run_cmd(cmd, timeout=300)
        except FileNotFoundError:
            status.update_message = f"Command not found: {cmd[0]}"
            return status
        if result.returncode != 0:
            status.update_message = f"Failed: {cmd_str}\n{result.stderr or result.stdout}"
            return status

    # Verify the update
    new_version = get_installed_version("deriva_ml")
    if new_version:
        new_base = extract_base_version(new_version)
        latest = status.latest.lstrip("v") if status.latest else ""
        if parse_semver(new_base) >= parse_semver(latest):
            status.updated = True
            status.up_to_date = True
            status.installed = new_version
            status.update_message = f"Updated to {new_version}"
        else:
            status.update_message = f"Update ran but version is still {new_version}"
    else:
        status.update_message = "Update ran but could not verify new version"
    return status


def _get_cached_plugin_version() -> str | None:
    """Get the installed plugin version from the Claude Code plugin cache.

    The plugin cache lives at ~/.claude/plugins/cache/deriva-plugins/deriva/<version>/
    with a plugin.json file containing the version metadata.
    """
    if not PLUGIN_CACHE_DIR.exists():
        return None

    # Find cached version directories (e.g., "0.1.0", "0.10.3")
    version_dirs = [d for d in PLUGIN_CACHE_DIR.iterdir() if d.is_dir()]
    if not version_dirs:
        return None

    # If multiple versions cached, pick the highest
    best_version = None
    best_tuple = (0, 0, 0)
    for d in version_dirs:
        plugin_json = d / ".claude-plugin" / "plugin.json"
        if plugin_json.exists():
            try:
                data = json.loads(plugin_json.read_text())
                ver = data.get("version", d.name)
                ver_tuple = parse_semver(ver)
                if ver_tuple > best_tuple:
                    best_version = ver
                    best_tuple = ver_tuple
            except (json.JSONDecodeError, ValueError):
                pass
        else:
            # Fall back to directory name
            try:
                ver_tuple = parse_semver(d.name)
                if ver_tuple > best_tuple:
                    best_version = d.name
                    best_tuple = ver_tuple
            except (ValueError, IndexError):
                pass

    return best_version


def check_skills() -> VersionStatus:
    """Check if the cached skills plugin is up to date.

    Compares the version in ~/.claude/plugins/cache/deriva-plugins/deriva/<ver>/
    against the latest release tag on GitHub.
    """
    installed = _get_cached_plugin_version()
    if not installed:
        return VersionStatus("skills", None, None, None,
                             "Not installed (run: /plugin install deriva)")

    latest_tag = get_latest_git_tag(SKILLS_GITHUB_REPO)
    if not latest_tag:
        return VersionStatus("skills", installed, None, None,
                             "Could not fetch latest version from GitHub")

    outdated = version_is_outdated(installed, latest_tag)
    if outdated is None:
        return VersionStatus("skills", installed, latest_tag, None,
                             "Could not compare versions")

    if not outdated:
        return VersionStatus("skills", installed, latest_tag, True, "Up to date")
    else:
        return VersionStatus(
            "skills", installed, latest_tag, False,
            f"Outdated: installed {installed}, latest is {latest_tag}",
            update_commands=["Tell user: /plugin update deriva"],
        )


def update_skills(status: VersionStatus) -> VersionStatus:
    """Update the skills plugin.

    Plugin updates require running '/plugin update deriva' in Claude Code.
    This function cannot do it programmatically, so it provides instructions.
    """
    status.update_message = (
        "Skills plugin must be updated from within Claude Code.\n"
        "    Run: /plugin update deriva"
    )
    return status


def _is_registry_image(image: str) -> bool:
    """Check if the image name looks like a registry image (ghcr.io/...)."""
    return "/" in image and ("ghcr.io" in image or "docker.io" in image
                            or "." in image.split("/")[0])


def check_mcp_server() -> VersionStatus:
    """Check if the MCP Docker container is up to date.

    Handles two deployment modes:
    - Local dev: image built from local repo (e.g., 'deriva-mcp:dev').
      Compares container creation time against latest repo commit.
    - Registry: image pulled from GHCR (e.g., 'ghcr.io/.../deriva-mcp:latest').
      Compares local image digest against remote registry digest.
    """
    if not shutil.which("docker"):
        # No Docker — check if MCP server runs natively
        return _check_native_mcp_server()

    try:
        result = run_cmd(
            ["docker", "ps", "--filter", "name=deriva-mcp", "--format", "{{.Image}}"],
        )
    except FileNotFoundError:
        return _check_native_mcp_server()

    if result.returncode != 0 or not result.stdout.strip():
        # No Docker container — check if MCP server runs natively
        return _check_native_mcp_server()

    image = result.stdout.strip()

    if _is_registry_image(image):
        return _check_registry_mcp_server(image)
    else:
        return _check_local_dev_mcp_server(image)


def _check_native_mcp_server() -> VersionStatus:
    """Check for a natively-running MCP server (no Docker)."""
    installed = get_installed_version("deriva_mcp")
    if not installed:
        installed = get_installed_version("deriva_ml_mcp")
    if not installed:
        return VersionStatus("mcp-server", None, None, None,
                             "No running Docker container or installed package found")

    latest_tag = get_latest_git_tag(MCP_GITHUB_REPO)
    if not latest_tag:
        return VersionStatus("mcp-server", installed, None, None,
                             "Could not fetch latest version from GitHub")

    outdated = version_is_outdated(installed, latest_tag)
    if outdated is None:
        return VersionStatus("mcp-server", installed, latest_tag, None,
                             "Could not compare versions")

    base = extract_base_version(installed)
    if not outdated:
        return VersionStatus("mcp-server", installed, latest_tag, True,
                             "Up to date")
    else:
        update_cmds = []
        if shutil.which("uv"):
            update_cmds = ["uv lock --upgrade-package deriva-mcp", "uv sync"]
        elif shutil.which("pip"):
            update_cmds = ["pip install --upgrade deriva-mcp"]

        return VersionStatus(
            "mcp-server", installed, latest_tag, False,
            f"Outdated: installed {base}, latest is {latest_tag}",
            update_commands=update_cmds,
        )


def _check_registry_mcp_server(image: str) -> VersionStatus:
    """Check a registry-pulled Docker image against the remote registry.

    Compares local image digest against remote manifest digest to detect
    whether a newer image is available.
    """
    # Get local image digest
    try:
        result = run_cmd(["docker", "inspect", "--format", "{{.Id}}", image])
    except FileNotFoundError:
        return VersionStatus("mcp-server", image, None, None,
                             "Docker not available")
    local_digest = result.stdout.strip() if result.returncode == 0 else None

    # Get local image repo digest (the digest used to pull)
    local_repo_digest = None
    try:
        result = run_cmd(
            ["docker", "inspect", "--format",
             "{{index .RepoDigests 0}}", image],
        )
        if result.returncode == 0 and "@sha256:" in result.stdout:
            local_repo_digest = result.stdout.strip().split("@", 1)[1]
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Check remote registry manifest digest
    try:
        result = run_cmd(
            ["docker", "manifest", "inspect", "--verbose", image],
            timeout=30,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        result = None

    if result and result.returncode == 0:
        # Parse manifest to get remote digest
        remote_digest = None
        try:
            manifest_data = json.loads(result.stdout)
            if isinstance(manifest_data, list):
                manifest_data = manifest_data[0]
            descriptor = manifest_data.get("Descriptor", {})
            remote_digest = descriptor.get("digest")
        except (json.JSONDecodeError, KeyError, IndexError):
            pass

        if local_repo_digest and remote_digest:
            if local_repo_digest == remote_digest:
                return VersionStatus(
                    "mcp-server", image, "latest", True,
                    "Up to date (image digest matches remote)",
                )
            else:
                return VersionStatus(
                    "mcp-server", image, "newer image available", False,
                    "Remote registry has a newer image",
                    update_commands=[
                        f"docker pull {image}",
                        "docker restart deriva-mcp",
                    ],
                )

    # Fall back to checking the latest git tag
    latest_tag = get_latest_git_tag(MCP_GITHUB_REPO)
    return VersionStatus("mcp-server", image, latest_tag or "unknown", None,
                         "Could not compare image digests. "
                         "Try: docker pull " + image)


def _check_local_dev_mcp_server(image: str) -> VersionStatus:
    """Check a locally-built Docker image against the repo commit history."""
    repo_dir = _find_repo_dir()
    if not repo_dir:
        return VersionStatus("mcp-server", image, None, None,
                             "Could not find deriva-mcp repo to check for updates")

    # Compare container creation time vs latest commit time
    try:
        result = run_cmd(
            ["docker", "inspect", "--format", "{{.Created}}", "deriva-mcp"],
        )
        container_created = result.stdout.strip() if result.returncode == 0 else None
    except FileNotFoundError:
        container_created = None

    # Get latest repo commit hash and time
    latest_commit = None
    latest_commit_time = None
    try:
        result = run_cmd(
            ["git", "log", "-1", "--format=%h %aI"],
            cwd=repo_dir,
        )
        if result.returncode == 0 and result.stdout.strip():
            parts = result.stdout.strip().split(" ", 1)
            latest_commit = parts[0]
            latest_commit_time = parts[1] if len(parts) > 1 else None
    except FileNotFoundError:
        pass

    # Try to get the commit hash the container was built from via OCI label
    container_commit = None
    try:
        result = run_cmd(
            ["docker", "inspect", "--format",
             '{{index .Config.Labels "org.opencontainers.image.revision"}}',
             "deriva-mcp"],
        )
        if result.returncode == 0 and result.stdout.strip() and result.stdout.strip() != "<no value>":
            container_commit = result.stdout.strip()[:7]
    except FileNotFoundError:
        pass

    # Fall back: find the repo commit closest to container creation time
    if not container_commit and container_created:
        try:
            result = run_cmd(
                ["git", "log", "-1", "--format=%h", f"--before={container_created}"],
                cwd=repo_dir,
            )
            if result.returncode == 0 and result.stdout.strip():
                container_commit = result.stdout.strip()
        except FileNotFoundError:
            pass

    # Build version strings showing commit hashes
    installed_str = f"commit {container_commit}" if container_commit else image
    latest_str = f"commit {latest_commit}" if latest_commit else "unknown"

    # Find compose files for rebuild command
    # docker-compose.dev.yaml is an override that requires the base docker-compose.mcp.yaml
    compose_files = []
    base_compose = os.path.join(repo_dir, "docker-compose.mcp.yaml")
    dev_compose = os.path.join(repo_dir, "docker-compose.dev.yaml")
    if os.path.exists(base_compose) and os.path.exists(dev_compose):
        compose_files = [base_compose, dev_compose]
    elif os.path.exists(base_compose):
        compose_files = [base_compose]
    elif os.path.exists(dev_compose):
        compose_files = [dev_compose]

    if container_created and latest_commit_time:
        if latest_commit_time > container_created:
            if compose_files:
                file_args = " ".join(f"-f {f}" for f in compose_files)
                rebuild_cmd = f"docker compose {file_args} up -d --build"
            else:
                rebuild_cmd = f"docker build -t {image} {repo_dir} && docker restart deriva-mcp"
            return VersionStatus(
                "mcp-server", installed_str, latest_str,
                False,
                "Container is older than latest repo commit",
                update_commands=[rebuild_cmd],
            )

    return VersionStatus("mcp-server", installed_str, latest_str, True,
                         "Container appears up to date")


def _find_repo_dir() -> str | None:
    """Find the deriva-mcp git repo dynamically.

    Discovery strategy (no hardcoded paths):
    1. Walk up from CWD looking for a deriva-mcp repo
    2. Check sibling directories of CWD (common monorepo layout)
    3. Use 'git' to find repos in common parent directories
    """
    target_marker = Path("src") / "deriva_mcp"

    # 1. Walk up from CWD
    cwd = Path.cwd()
    for parent in [cwd, *cwd.parents]:
        if parent.name == "deriva-mcp" and (parent / ".git").is_dir() and (parent / target_marker).is_dir():
            return str(parent)

    # 2. Check sibling directories of CWD and its parents
    #    (handles being in e.g. ~/GitHub/deriva-ml-model-template while repo is ~/GitHub/deriva-mcp)
    for parent in [cwd, *list(cwd.parents)[:3]]:
        candidate = parent / "deriva-mcp"
        if (candidate / ".git").is_dir() and (candidate / target_marker).is_dir():
            return str(candidate)
        # Also check parent's siblings
        if parent.parent.exists():
            candidate = parent.parent / "deriva-mcp"
            if (candidate / ".git").is_dir() and (candidate / target_marker).is_dir():
                return str(candidate)

    # 3. Check common dev directory patterns relative to home
    #    (only structure, not specific usernames or absolute paths)
    home = Path.home()
    for dev_dir_name in ["GitHub", "github", "src", "projects", "code", "dev", "repos"]:
        candidate = home / dev_dir_name / "deriva-mcp"
        if (candidate / ".git").is_dir() and (candidate / target_marker).is_dir():
            return str(candidate)

    return None


def update_mcp_server(status: VersionStatus) -> VersionStatus:
    """Rebuild and restart the MCP Docker container."""
    if not shutil.which("docker"):
        status.update_message = "Docker not found on PATH"
        return status

    print("  Rebuilding MCP server...")
    for cmd_str in status.update_commands:
        # Use shell=True for compose commands with pipes
        print(f"    $ {cmd_str}")
        try:
            result = subprocess.run(
                cmd_str, shell=True, capture_output=True, text=True, timeout=600,
            )
        except FileNotFoundError:
            status.update_message = f"Command not found: {cmd_str}"
            return status
        if result.returncode != 0:
            status.update_message = f"Failed: {cmd_str}\n{result.stderr or result.stdout}"
            return status

    status.updated = True
    status.up_to_date = True
    status.update_message = "Rebuilt and restarted MCP server"
    return status


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

UPDATERS = {
    "deriva-ml": update_deriva_ml,
    "skills": update_skills,
    "mcp-server": update_mcp_server,
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Check and update DerivaML ecosystem")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--update", action="store_true",
                        help="Automatically update outdated components")
    parser.add_argument("--component", choices=["deriva-ml", "skills", "mcp-server"],
                        help="Check/update only this component")
    args = parser.parse_args()

    checks = {
        "deriva-ml": check_deriva_ml,
        "skills": check_skills,
        "mcp-server": check_mcp_server,
    }

    if args.component:
        checks = {args.component: checks[args.component]}

    results = []
    for name, check_fn in checks.items():
        status = check_fn()
        if args.update and status.up_to_date is False and status.update_commands:
            updater = UPDATERS.get(name)
            if updater:
                status = updater(status)
        results.append(status)

    if args.json:
        print(json.dumps([asdict(r) for r in results], indent=2))
    else:
        any_outdated = False
        for r in results:
            if r.updated:
                label = "UPDATED"
            elif r.up_to_date is True:
                label = "UP TO DATE"
            elif r.up_to_date is False:
                label = "OUTDATED"
                any_outdated = True
            else:
                label = "UNKNOWN"

            print(f"  {r.component}: {label}")
            print(f"    Installed: {r.installed or 'N/A'}")
            print(f"    Latest:    {r.latest or 'N/A'}")
            print(f"    {r.message}")
            if r.updated:
                print(f"    -> {r.update_message}")
            elif r.up_to_date is False and r.update_commands:
                print(f"    Update: {' && '.join(r.update_commands)}")
            if r.update_message and not r.updated:
                print(f"    Note: {r.update_message}")
            print()

        if any_outdated:
            print("Some components are outdated. Run with --update to update them.")

    # Exit code 0 for check-only mode (informational), even if outdated.
    # Exit code 1 only when --update was requested and an update failed.
    if args.update:
        has_failed_update = any(
            r.up_to_date is False and not r.updated for r in results
        )
        return 1 if has_failed_update else 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
