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


def _find_uv() -> str | None:
    """Find the ``uv`` binary, checking well-known locations as fallback.

    ``shutil.which`` only searches ``$PATH``, which may be incomplete when
    running inside Claude Code (especially in the Desktop app where the
    shell profile is not sourced).  This helper checks common install
    locations so the script works even with a minimal ``$PATH``.
    """
    found = shutil.which("uv")
    if found:
        return found

    home = Path.home()
    candidates = [
        home / ".local" / "bin" / "uv",
        home / ".cargo" / "bin" / "uv",
        Path("/opt/homebrew/bin/uv"),
        Path("/usr/local/bin/uv"),
    ]
    for candidate in candidates:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)

    return None


def _find_marketplace_cache_dir() -> Path | None:
    """Find the marketplace cache directory dynamically.

    Reads ~/.claude/plugins/known_marketplaces.json to find the install
    location for the deriva-plugins marketplace. Falls back to the
    conventional path if the config file doesn't exist.
    """
    known_marketplaces = Path.home() / ".claude" / "plugins" / "known_marketplaces.json"
    if known_marketplaces.exists():
        try:
            data = json.loads(known_marketplaces.read_text())
            entry = data.get("deriva-plugins", {})
            install_loc = entry.get("installLocation")
            if install_loc:
                return Path(install_loc)
        except (json.JSONDecodeError, KeyError):
            pass

    # Fall back to conventional path
    fallback = Path.home() / ".claude" / "plugins" / "marketplaces" / "deriva-plugins"
    return fallback if fallback.is_dir() else None


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
    uv = _find_uv()
    if uv:
        try:
            result = run_cmd(
                [uv, "run", "python", "-c",
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
        uv = _find_uv()
        if uv:
            update_cmds = [f"{uv} lock --upgrade-package deriva-ml", f"{uv} sync"]
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


def _refresh_marketplace_cache() -> bool:
    """Pull latest commits into the local marketplace cache.

    Claude Code's '/plugin update' reads from a local git clone at
    ~/.claude/plugins/marketplaces/deriva-plugins/ (or wherever
    known_marketplaces.json points). If this clone is stale,
    '/plugin update' reports "already at latest" even when newer versions
    exist on GitHub. Running 'git pull' fixes this.

    Returns:
        True if the cache was successfully refreshed, False otherwise.
    """
    cache_dir = _find_marketplace_cache_dir()
    if cache_dir is None or not cache_dir.is_dir():
        return False
    git_dir = cache_dir / ".git"
    if not git_dir.is_dir():
        return False

    try:
        result = run_cmd(
            ["git", "pull", "origin", "main"],
            cwd=str(cache_dir),
            timeout=30,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def update_skills(status: VersionStatus) -> VersionStatus:
    """Update the skills plugin.

    First refreshes the local marketplace cache (git pull) so that
    '/plugin update' sees the latest version. Then instructs the user
    to run the plugin update command.

    The final '/plugin update deriva' step must be run by the user because
    Claude Code manages its plugin cache with internal locking that external
    processes cannot safely bypass.
    """
    # Step 1: Refresh the marketplace cache
    print("  Refreshing marketplace cache...")
    refreshed = _refresh_marketplace_cache()
    if refreshed:
        print("    Marketplace cache updated successfully.")
    else:
        print("    Could not refresh marketplace cache (this is non-fatal).")

    # Step 2: Instruct user to run the plugin update
    status.update_message = (
        "Marketplace cache has been refreshed. "
        "Now run '/plugin update deriva' in Claude Code to complete the update."
    )
    return status


def check_mcp_server() -> VersionStatus:
    """Return the latest release tag for the MCP server.

    The *running* server version is obtained by Claude via the
    ``deriva://server/version`` MCP resource — not by this script.
    This function only fetches the latest GitHub release tag so the
    caller (Claude) can compare the two.
    """
    latest_tag = get_latest_git_tag(MCP_GITHUB_REPO)
    if not latest_tag:
        return VersionStatus("mcp-server", None, None, None,
                             "Could not fetch latest version from GitHub")

    return VersionStatus("mcp-server", None, latest_tag, None,
                         "Use deriva://server/version resource for installed version")


def update_mcp_server(status: VersionStatus) -> VersionStatus:
    """MCP server updates require user action (restart breaks connection)."""
    status.update_message = (
        "MCP server cannot be updated automatically (restart breaks connection). "
        "Update manually and restart the server."
    )
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
