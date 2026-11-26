#!/usr/bin/env python3
"""Zero-dependency installer & configurator for Google Workspace Remote MCP Servers.

Supports both Free Standard Tier (Personal Mode) and Paid Scaled Tier across:
  - Hermes Agent (default ~/.hermes, named profiles ~/.hermes/profiles/<name>, and custom HERMES_HOME)
  - Claude Code (~/.claude.json & ~/.claude/skills)
  - Cursor (~/.cursor/mcp.json & ~/.cursor/skills)
  - OpenCode (~/.config/opencode/opencode.json & ~/.config/opencode/skills)
  - Codex CLI (~/.codex/config.toml & ~/.agents/skills)
  - Antigravity / Gemini CLI (~/.gemini/config/mcp_config.json & ~/.agents/skills)
"""

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import sys

SERVICES = {
    "gmail": {
        "server_name": "google-gmail",
        "url": "https://gmailmcp.googleapis.com/mcp/v1",
        "readonly_tools": ["search_threads", "list_messages", "get_message", "get_thread", "list_labels"],
    },
    "drive": {
        "server_name": "google-drive",
        "url": "https://drivemcp.googleapis.com/mcp/v1",
        "readonly_tools": ["search_files", "get_file_metadata", "read_file_content"],
    },
    "calendar": {
        "server_name": "google-calendar",
        "url": "https://calendarmcp.googleapis.com/mcp/v1",
        "readonly_tools": ["list_calendars", "list_events", "get_event", "search_events", "suggest_time"],
    },
    "docs": {
        "server_name": "google-docs",
        "url": "https://docsmcp.googleapis.com/mcp/v1",
        "readonly_tools": ["read_doc"],
    },
    "sheets": {
        "server_name": "google-sheets",
        "url": "https://sheetsmcp.googleapis.com/mcp/v1",
        "readonly_tools": ["get_spreadsheet", "read_range"],
    },
    "slides": {
        "server_name": "google-slides",
        "url": "https://slidesmcp.googleapis.com/mcp/v1",
        "readonly_tools": ["get_presentation", "read_slide"],
    },
    "chat": {
        "server_name": "google-chat",
        "url": "https://chatmcp.googleapis.com/mcp/v1",
        "readonly_tools": ["list_spaces", "list_messages", "get_message"],
    },
    "tasks": {
        "server_name": "google-tasks",
        "url": "https://tasksmcp.googleapis.com/mcp/v1",
        "readonly_tools": ["list_tasklists", "list_tasks", "get_task"],
    },
}

CORE_SERVICES = ["gmail", "drive", "calendar", "docs", "sheets", "slides"]
SKILL_FOLDER_NAME = "google-workspace-mcp"


def resolve_hermes_home(profile: str | None = None) -> Path:
    """Resolve HERMES_HOME for a named profile, active HERMES_HOME env var, or default ~/.hermes."""
    home = Path.home()
    if profile:
        if profile == "default":
            return home / ".hermes"
        # Check standard Hermes profiles dir (~/.hermes/profiles/<name>)
        std_profile = home / ".hermes" / "profiles" / profile
        if std_profile.exists():
            return std_profile
        # Check container/custom profiles dir (/opt/data/profiles/<name>)
        opt_profile = Path("/opt/data/profiles") / profile
        if opt_profile.exists():
            return opt_profile
        # Check if active HERMES_HOME already points to this profile name
        env_val = os.environ.get("HERMES_HOME", "").strip()
        if env_val and Path(env_val).name == profile:
            return Path(env_val).expanduser()
        return std_profile

    env_val = os.environ.get("HERMES_HOME", "").strip()
    if env_val:
        return Path(env_val).expanduser()
    return home / ".hermes"


def discover_hermes_profiles() -> list[dict]:
    """Discover default, ~/.hermes/profiles/*, /opt/data/profiles/*, and active HERMES_HOME profiles."""
    home = Path.home()
    seen_paths: set[Path] = set()
    profiles: list[dict] = []

    def _add_profile(name: str, path: Path, is_standard_named: bool) -> None:
        resolved = path.expanduser()
        if resolved in seen_paths:
            return
        seen_paths.add(resolved)
        profiles.append({
            "profile": name,
            "hermes_home": str(resolved),
            "exists": resolved.exists(),
            "is_standard_named": is_standard_named,
        })

    # 1. Active HERMES_HOME from environment (highest priority if set)
    env_val = os.environ.get("HERMES_HOME", "").strip()
    if env_val:
        env_path = Path(env_val).expanduser()
        is_std = env_path.parent == (home / ".hermes" / "profiles")
        prof_name = "default" if env_path == (home / ".hermes") else env_path.name
        _add_profile(prof_name, env_path, is_std)

    # 2. Default ~/.hermes profile
    default_home = home / ".hermes"
    if default_home.exists() or not profiles:
        _add_profile("default", default_home, False)

    # 3. Standard named profiles under ~/.hermes/profiles/*
    std_profiles_dir = default_home / "profiles"
    if std_profiles_dir.is_dir():
        for child in sorted(std_profiles_dir.iterdir()):
            if child.is_dir() and not child.name.startswith("."):
                _add_profile(child.name, child, True)

    # 4. Container/fleet profiles under /opt/data/profiles/* (if accessible)
    opt_profiles_dir = Path("/opt/data/profiles")
    try:
        if opt_profiles_dir.is_dir():
            for child in sorted(opt_profiles_dir.iterdir()):
                if child.is_dir() and not child.name.startswith("."):
                    _add_profile(child.name, child, False)
    except OSError:
        pass

    return profiles


def get_skill_source_dir() -> Path:
    """Locate the google-workspace-mcp skill root directory relative to this script."""
    script_dir = Path(__file__).resolve().parent
    candidate = script_dir.parent
    if (candidate / "SKILL.md").exists():
        return candidate
    repo_candidate = Path.cwd() / "skills" / SKILL_FOLDER_NAME
    if (repo_candidate / "SKILL.md").exists():
        return repo_candidate
    if (Path.cwd() / "SKILL.md").exists():
        return Path.cwd()
    return candidate


def get_agent_registry(profile: str | None = None) -> dict[str, dict]:
    hermes_home = resolve_hermes_home(profile)
    home = Path.home()

    # Hermes places productivity skills under <HERMES_HOME>/skills/productivity/google-workspace-mcp
    hermes_skill_dir = hermes_home / "skills" / "productivity" / SKILL_FOLDER_NAME

    return {
        "hermes": {
            "label": "Hermes Agent",
            "binaries": ["hermes"],
            "home_markers": [hermes_home],
            "config_path": hermes_home / "config.yaml",
            "config_format": "yaml",
            "skill_dir": hermes_skill_dir,
            "env_path": hermes_home / ".env",
        },
        "claude": {
            "label": "Claude Code",
            "binaries": ["claude"],
            "home_markers": [home / ".claude", home / ".claude.json"],
            "config_path": home / ".claude.json",
            "config_format": "claude_json",
            "skill_dir": home / ".claude" / "skills" / SKILL_FOLDER_NAME,
            "env_path": None,
        },
        "cursor": {
            "label": "Cursor",
            "binaries": ["cursor"],
            "home_markers": [home / ".cursor"],
            "config_path": home / ".cursor" / "mcp.json",
            "config_format": "mcp_servers_json",
            "skill_dir": home / ".cursor" / "skills" / SKILL_FOLDER_NAME,
            "env_path": None,
        },
        "opencode": {
            "label": "OpenCode",
            "binaries": ["opencode"],
            "home_markers": [home / ".config" / "opencode"],
            "config_path": home / ".config" / "opencode" / "opencode.json",
            "config_format": "opencode_json",
            "skill_dir": home / ".config" / "opencode" / "skills" / SKILL_FOLDER_NAME,
            "env_path": None,
        },
        "codex": {
            "label": "Codex CLI",
            "binaries": ["codex"],
            "home_markers": [home / ".codex"],
            "config_path": home / ".codex" / "config.toml",
            "config_format": "toml",
            "skill_dir": home / ".agents" / "skills" / SKILL_FOLDER_NAME,
            "env_path": None,
        },
        "antigravity": {
            "label": "Antigravity / Gemini CLI",
            "binaries": ["antigravity", "gemini"],
            "home_markers": [home / ".gemini"],
            "config_path": home / ".gemini" / "config" / "mcp_config.json",
            "config_format": "antigravity_json",
            "skill_dir": home / ".agents" / "skills" / SKILL_FOLDER_NAME,
            "env_path": None,
        },
    }


def _check_hermes_skill_installed(hermes_home: Path) -> Path | None:
    """Check both <HERMES_HOME>/skills/productivity/google-workspace-mcp and <HERMES_HOME>/skills/google-workspace-mcp."""
    for rel in (Path("skills/productivity") / SKILL_FOLDER_NAME, Path("skills") / SKILL_FOLDER_NAME):
        candidate = hermes_home / rel
        if (candidate / "SKILL.md").exists():
            return candidate
    return None


def detect_agents(profile: str | None = None) -> list[dict]:
    """Scan PATH, Hermes profiles, and local config directories to detect installed CLIs / AI agents."""
    registry = get_agent_registry(profile)
    results = []

    for key, info in registry.items():
        found_bin = None
        for b in info["binaries"]:
            resolved = shutil.which(b)
            if resolved:
                found_bin = resolved
                break

        if key == "hermes":
            discovered = discover_hermes_profiles()
            existing_profiles = [p for p in discovered if p["exists"]]
            marker_exists = bool(existing_profiles)
            detected = bool(found_bin or marker_exists)

            profile_details = []
            for p in (existing_profiles or discovered):
                p_home = Path(p["hermes_home"])
                cfg_path = p_home / "config.yaml"
                active_svcs: list[str] = []
                if cfg_path.exists():
                    text = cfg_path.read_text(encoding="utf-8", errors="ignore")
                    active_svcs = [svc for svc, meta in SERVICES.items() if meta["url"] in text]
                installed_path = _check_hermes_skill_installed(p_home)
                target_skill_dir = installed_path or (p_home / "skills" / "productivity" / SKILL_FOLDER_NAME)
                profile_details.append({
                    "profile": p["profile"],
                    "hermes_home": str(p_home),
                    "is_standard_named": p["is_standard_named"],
                    "config_path": str(cfg_path),
                    "configured_services": active_svcs,
                    "skill_dir": str(target_skill_dir),
                    "skill_installed": installed_path is not None,
                })

            primary = profile_details[0]
            results.append({
                "key": key,
                "label": info["label"],
                "detected": detected,
                "binary": found_bin,
                "config_path": primary["config_path"],
                "config_exists": Path(primary["config_path"]).exists(),
                "configured_services": primary["configured_services"],
                "skill_dir": primary["skill_dir"],
                "skill_installed": primary["skill_installed"],
                "profiles": profile_details,
            })
            continue

        marker_exists = any(p.exists() for p in info["home_markers"])
        detected = bool(found_bin or marker_exists)

        config_path: Path = info["config_path"]
        configured_services: list[str] = []
        if config_path.exists():
            text = config_path.read_text(encoding="utf-8", errors="ignore")
            configured_services = [svc for svc, meta in SERVICES.items() if meta["url"] in text]

        skill_dir: Path = info["skill_dir"]
        skill_installed = (skill_dir / "SKILL.md").exists()

        results.append({
            "key": key,
            "label": info["label"],
            "detected": detected,
            "binary": found_bin,
            "config_path": str(config_path),
            "config_exists": config_path.exists(),
            "configured_services": configured_services,
            "skill_dir": str(skill_dir),
            "skill_installed": skill_installed,
        })

    return results


def print_detected_agents(agents: list[dict]) -> None:
    """Display detected CLIs, AI agents, and Hermes profiles in a readable summary."""
    print("=== Detected CLIs & AI Agents ===")
    installed = [a for a in agents if a["detected"]]
    missing = [a for a in agents if not a["detected"]]

    if not installed:
        print("  (No supported AI agent CLIs or config directories detected on this system)")
    else:
        for idx, a in enumerate(installed, start=1):
            bin_str = a["binary"] if a["binary"] else "config dir found (CLI not in PATH)"
            print(f"  [{idx}] {a['label']} ({a['key']})")
            print(f"      CLI / Binary : {bin_str}")
            if a["key"] == "hermes" and a.get("profiles"):
                for p in a["profiles"]:
                    skill_str = f"YES ({p['skill_dir']})" if p["skill_installed"] else f"NO  -> {p['skill_dir']}"
                    mcp_str = ", ".join(p["configured_services"]) if p["configured_services"] else "none"
                    print(f"      Profile [{p['profile']}] (HERMES_HOME={p['hermes_home']})")
                    print(f"        Skill Folder : {skill_str}")
                    print(f"        MCP Config   : {p['config_path']} [active: {mcp_str}]")
            else:
                skill_str = f"YES ({a['skill_dir']})" if a["skill_installed"] else f"NO  -> {a['skill_dir']}"
                mcp_str = ", ".join(a["configured_services"]) if a["configured_services"] else "none"
                print(f"      Skill Folder : {skill_str}")
                print(f"      MCP Config   : {a['config_path']} [active: {mcp_str}]")

    if missing:
        names = ", ".join(f"{a['label']} ({a['key']})" for a in missing)
        print(f"\n  Not detected: {names}")
    print("=" * 33)


def parse_services(raw: str) -> list[str]:
    val = raw.strip().lower()
    if val == "all":
        return list(SERVICES.keys())
    if val == "core":
        return CORE_SERVICES
    selected = [s.strip() for s in val.split(",") if s.strip()]
    invalid = [s for s in selected if s not in SERVICES]
    if invalid:
        raise ValueError(f"Unknown service(s): {', '.join(invalid)}. Valid: {', '.join(SERVICES.keys())}")
    return selected


def read_env_file(env_path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    if not env_path.exists():
        return data
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        data[k.strip()] = v.strip().strip('"').strip("'")
    return data


def write_env_credentials(client_id: str, client_secret: str, profile: str | None = None) -> Path:
    hermes_home = resolve_hermes_home(profile)
    hermes_home.mkdir(parents=True, exist_ok=True)
    env_path = hermes_home / ".env"

    existing_lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
    updates = {
        "GOOGLE_MCP_CLIENT_ID": client_id.strip(),
        "GOOGLE_MCP_CLIENT_SECRET": client_secret.strip(),
    }
    written = set()
    new_lines = []

    for line in existing_lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            if key in updates:
                new_lines.append(f'{key}="{updates[key]}"')
                written.add(key)
                continue
        new_lines.append(line)

    for key, val in updates.items():
        if key not in written:
            new_lines.append(f'{key}="{val}"')

    env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    try:
        os.chmod(env_path, 0o600)
    except OSError:
        pass
    return env_path


def install_skill_files(agent_key: str, profile: str | None = None, source_dir: Path | None = None) -> dict:
    """Copy the google-workspace-mcp skill directory into the target agent's skill folder without destructive deletes."""
    registry = get_agent_registry(profile)
    if agent_key not in registry:
        raise ValueError(f"Unsupported agent: {agent_key}")

    src = (source_dir or get_skill_source_dir()).resolve()
    if not (src / "SKILL.md").exists():
        raise FileNotFoundError(f"SKILL.md not found in source directory: {src}")

    if agent_key == "hermes":
        hermes_home = resolve_hermes_home(profile)
        existing = _check_hermes_skill_installed(hermes_home)
        dst = (existing or registry[agent_key]["skill_dir"]).expanduser().resolve()
    else:
        dst = registry[agent_key]["skill_dir"].expanduser().resolve()

    if src == dst:
        return {
            "agent": agent_key,
            "status": "already_in_place",
            "source": str(src),
            "destination": str(dst),
        }

    dst.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src / "SKILL.md", dst / "SKILL.md")

    ignore_patterns = shutil.ignore_patterns("__pycache__", "*.pyc", ".git", ".DS_Store")
    for sub in ("scripts", "references"):
        sub_src = src / sub
        sub_dst = dst / sub
        if sub_src.is_dir():
            shutil.copytree(sub_src, sub_dst, ignore=ignore_patterns, dirs_exist_ok=True)

    installed_script = dst / "scripts" / "setup_mcp.py"
    if installed_script.exists():
        try:
            os.chmod(installed_script, 0o755)
        except OSError:
            pass

    return {
        "agent": agent_key,
        "status": "installed",
        "source": str(src),
        "destination": str(dst),
    }


def _build_hermes_server_block(svc: str, idx: int, headless: bool, base_port: int, readonly: bool) -> str:
    meta = SERVICES[svc]
    lines = [
        f"  {meta['server_name']}:",
        f'    url: "{meta["url"]}"',
        "    auth: oauth",
        "    oauth:",
        '      client_id: "${GOOGLE_MCP_CLIENT_ID}"',
        '      client_secret: "${GOOGLE_MCP_CLIENT_SECRET}"',
    ]
    if headless:
        lines.append('      redirect_host: "127.0.0.1"')
        lines.append(f"      redirect_port: {base_port + idx}")
    if readonly:
        tools_str = ", ".join(meta["readonly_tools"])
        lines.append("    tools:")
        lines.append(f"      include: [{tools_str}]")
        lines.append("      resources: false")
        lines.append("      prompts: false")
    return "\n".join(lines)


def _strip_existing_yaml_server(lines: list[str], mcp_start: int, mcp_end: int, server_name: str) -> list[str]:
    """Remove an existing `  <server_name>:` block inside `mcp_servers:` so updates are idempotent."""
    target_prefix = f"  {server_name}:"
    new_lines: list[str] = []
    i = 0
    while i < len(lines):
        if mcp_start < i < mcp_end and lines[i].startswith(target_prefix):
            i += 1
            while i < mcp_end:
                line = lines[i]
                if line.strip() == "" or line.startswith("    ") or line.lstrip().startswith("#"):
                    i += 1
                else:
                    break
            continue
        new_lines.append(lines[i])
        i += 1
    return new_lines


def apply_hermes_yaml(config_path: Path, services: list[str], headless: bool, base_port: int, readonly: bool) -> dict:
    """Safely merge Google Workspace MCP servers into Hermes config.yaml with .bak backup."""
    config_path.parent.mkdir(parents=True, exist_ok=True)
    backup_path = None

    if config_path.exists():
        original_text = config_path.read_text(encoding="utf-8")
        backup_path = config_path.with_suffix(config_path.suffix + ".bak")
        backup_path.write_text(original_text, encoding="utf-8")
    else:
        original_text = ""

    server_blocks = [
        _build_hermes_server_block(svc, idx, headless, base_port, readonly)
        for idx, svc in enumerate(services)
    ]
    joined_blocks = "\n".join(server_blocks)

    if not original_text.strip():
        updated_text = f"mcp_servers:\n{joined_blocks}\n"
        config_path.write_text(updated_text, encoding="utf-8")
        return {
            "config_path": str(config_path),
            "backup_path": str(backup_path) if backup_path else None,
            "added_servers": [SERVICES[s]["server_name"] for s in services],
        }

    lines = original_text.splitlines()
    mcp_idx = None
    for idx, line in enumerate(lines):
        if re.match(r"^mcp_servers\s*:", line):
            mcp_idx = idx
            break

    if mcp_idx is None:
        sep = "\n" if original_text.endswith("\n") else "\n\n"
        updated_text = f"{original_text}{sep}mcp_servers:\n{joined_blocks}\n"
        config_path.write_text(updated_text, encoding="utf-8")
        return {
            "config_path": str(config_path),
            "backup_path": str(backup_path) if backup_path else None,
            "added_servers": [SERVICES[s]["server_name"] for s in services],
        }

    if re.match(r"^mcp_servers\s*:\s*(\{\}|null|~)\s*$", lines[mcp_idx]):
        lines[mcp_idx] = "mcp_servers:"

    for svc in services:
        server_name = SERVICES[svc]["server_name"]
        mcp_end = len(lines)
        for idx in range(mcp_idx + 1, len(lines)):
            line = lines[idx]
            if line.strip() and not line.startswith(" ") and not line.startswith("#"):
                mcp_end = idx
                break
        lines = _strip_existing_yaml_server(lines, mcp_idx, mcp_end, server_name)

    insert_at = len(lines)
    for idx in range(mcp_idx + 1, len(lines)):
        line = lines[idx]
        if line.strip() and not line.startswith(" ") and not line.startswith("#"):
            insert_at = idx
            break

    while insert_at > mcp_idx + 1 and lines[insert_at - 1].strip() == "":
        insert_at -= 1

    new_server_lines = joined_blocks.splitlines()
    lines[insert_at:insert_at] = new_server_lines
    updated_text = "\n".join(lines).rstrip() + "\n"
    config_path.write_text(updated_text, encoding="utf-8")

    return {
        "config_path": str(config_path),
        "backup_path": str(backup_path) if backup_path else None,
        "added_servers": [SERVICES[s]["server_name"] for s in services],
    }


def build_json_entries(fmt: str, services: list[str], headless: bool, base_port: int) -> dict:
    servers = {}
    for idx, svc in enumerate(services):
        meta = SERVICES[svc]
        if fmt == "antigravity_json":
            entry = {
                "serverUrl": meta["url"],
                "auth": {
                    "type": "oauth",
                    "clientId": "${GOOGLE_MCP_CLIENT_ID}",
                    "clientSecret": "${GOOGLE_MCP_CLIENT_SECRET}",
                },
            }
        elif fmt == "opencode_json":
            entry = {
                "type": "remote",
                "url": meta["url"],
                "enabled": True,
                "oauth": {
                    "clientId": "{env:GOOGLE_MCP_CLIENT_ID}",
                    "clientSecret": "{env:GOOGLE_MCP_CLIENT_SECRET}",
                },
            }
        else:
            oauth_cfg = {
                "clientId": "${GOOGLE_MCP_CLIENT_ID}",
                "clientSecret": "${GOOGLE_MCP_CLIENT_SECRET}",
            }
            if headless:
                oauth_cfg["callbackPort"] = base_port + idx
            entry = {
                "type": "http",
                "url": meta["url"],
                "oauth": oauth_cfg,
            }
        servers[meta["server_name"]] = entry
    return servers


def apply_json_config(config_path: Path, fmt: str, services: list[str], headless: bool, base_port: int) -> dict:
    """Safely merge Google Workspace MCP servers into JSON config files with .bak backup."""
    config_path.parent.mkdir(parents=True, exist_ok=True)
    backup_path = None
    data: dict = {}

    if config_path.exists():
        raw = config_path.read_text(encoding="utf-8")
        backup_path = config_path.with_suffix(config_path.suffix + ".bak")
        backup_path.write_text(raw, encoding="utf-8")
        if raw.strip():
            data = json.loads(raw)

    root_key = "mcp" if fmt == "opencode_json" else "mcpServers"
    if root_key not in data or not isinstance(data[root_key], dict):
        data[root_key] = {}

    entries = build_json_entries(fmt, services, headless, base_port)
    data[root_key].update(entries)

    config_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return {
        "config_path": str(config_path),
        "backup_path": str(backup_path) if backup_path else None,
        "added_servers": list(entries.keys()),
    }


def apply_agent_config(
    agent_key: str,
    services: list[str],
    headless: bool,
    base_port: int,
    readonly: bool,
    profile: str | None = None,
) -> dict:
    registry = get_agent_registry(profile)
    if agent_key not in registry:
        raise ValueError(f"Unsupported agent: {agent_key}")

    info = registry[agent_key]
    fmt = info["config_format"]
    cfg_path: Path = info["config_path"]

    if fmt == "yaml":
        return apply_hermes_yaml(cfg_path, services, headless, base_port, readonly)
    if fmt == "toml":
        lines = [f"# Add to {cfg_path}"]
        for svc in services:
            meta = SERVICES[svc]
            lines.append(f"[mcp_servers.{meta['server_name']}]")
            lines.append(f'url = "{meta["url"]}"')
            lines.append('bearer_token_env_var = "GOOGLE_MCP_ACCESS_TOKEN"')
            lines.append("")
        return {
            "config_path": str(cfg_path),
            "status": "manual_toml_printed",
            "snippet": "\n".join(lines),
        }
    return apply_json_config(cfg_path, fmt, services, headless, base_port)


def print_next_steps(agent_key: str, services: list[str], headless: bool, base_port: int, profile: str | None = None) -> None:
    print(f"\n--- Next Steps for {agent_key} ---")
    if agent_key == "hermes":
        hermes_home = resolve_hermes_home(profile)
        home = Path.home()
        if hermes_home == home / ".hermes":
            cmd_prefix = "hermes"
        elif hermes_home.parent == home / ".hermes" / "profiles":
            cmd_prefix = f"hermes -p {hermes_home.name}"
        else:
            cmd_prefix = f"HERMES_HOME={hermes_home} hermes"

        print("1. Authenticate each enabled MCP server:")
        for svc in services:
            print(f"   {cmd_prefix} mcp login {SERVICES[svc]['server_name']} --connect-timeout 300")
        if headless:
            forwards = " ".join(
                f"-L {base_port + i}:127.0.0.1:{base_port + i}" for i in range(len(services))
            )
            print("2. Open SSH port forwarding from your local machine with a browser:")
            print(f"   ssh {forwards} user@your-server-ip")
        print("3. Verify & reload tools:")
        print(f"   {cmd_prefix} mcp test {SERVICES[services[0]]['server_name']}")
        print("   # Inside active Hermes chat: /reload-mcp")
    elif agent_key == "claude":
        print("1. Start Claude Code (`claude`) and run `/mcp`")
        print("2. Select each `google-*` server and click Authenticate")
        print("3. Verify the skill appears in `/skills` as `google-workspace-mcp`")
    else:
        print("1. Open MCP settings in your agent client and authenticate each `google-*` server")
        print("2. Ensure GOOGLE_MCP_CLIENT_ID and GOOGLE_MCP_CLIENT_SECRET are exported in your environment")


def interactive_wizard(
    agents: list[dict],
    services: list[str],
    headless: bool,
    base_port: int,
    readonly: bool,
    profile: str | None = None,
) -> int:
    installed = [a for a in agents if a["detected"]]
    if not installed:
        print("\nNo AI agent CLIs detected automatically.")
        print("Run with `--client hermes --install` (or `claude`, `cursor`, `opencode`, `codex`, `antigravity`) to force install.")
        return 0

    print("\nSelect target agent(s) to install skill files & add MCP servers:")
    print("  [A] All detected agents")
    for idx, a in enumerate(installed, start=1):
        print(f"  [{idx}] {a['label']} ({a['key']})")
    print("  [Q] Quit without changes")

    choice = input("\nChoice [A / 1..N / Q]: ").strip().lower()
    if choice in ("q", "quit", "exit", ""):
        print("Exited without making changes.")
        return 0

    if choice in ("a", "all"):
        targets = [a["key"] for a in installed]
    else:
        try:
            indices = [int(x.strip()) for x in choice.split(",") if x.strip()]
            targets = [installed[i - 1]["key"] for i in indices if 1 <= i <= len(installed)]
        except ValueError:
            print("Invalid selection.", file=sys.stderr)
            return 1
        if not targets:
            print("No valid agent selected.", file=sys.stderr)
            return 1

    svc_input = input(f"Services to enable [{','.join(services)}]: ").strip()
    if svc_input:
        services = parse_services(svc_input)

    headless_input = input(f"Headless/SSH port-forwarding mode? [{'y' if headless else 'N'}]: ").strip().lower()
    if headless_input in ("y", "yes"):
        headless = True
    elif headless_input in ("n", "no"):
        headless = False

    for key in targets:
        skill_res = install_skill_files(key, profile=profile)
        cfg_res = apply_agent_config(key, services, headless, base_port, readonly, profile=profile)
        print(f"\n[OK] {key}:")
        print(f"  Skill  -> {skill_res['status']} ({skill_res['destination']})")
        print(f"  Config -> {json.dumps(cfg_res)}")
        print_next_steps(key, services, headless, base_port, profile=profile)

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Auto-detect AI agents, install google-workspace-mcp skill, and configure Google Workspace Remote MCP Servers."
    )
    parser.add_argument("--detect", "--check", dest="detect", action="store_true", help="Detect installed CLIs/agents and check status")
    parser.add_argument("--install", action="store_true", help="Copy skill files AND automatically add MCP servers to config")
    parser.add_argument("--copy-skill-only", action="store_true", help="Only copy skill files to the target agent skill folder")
    parser.add_argument("--apply", action="store_true", help="Only add MCP servers to the target agent config file")
    parser.add_argument("--all-detected", action="store_true", help="Apply action across all detected CLIs/agents")
    parser.add_argument("--write-env", action="store_true", help="Write Client ID/Secret to <HERMES_HOME>/.env")
    parser.add_argument("--client-id", help="Google OAuth Client ID (with isAgent=true)")
    parser.add_argument("--client-secret", help="Google OAuth Client Secret")
    parser.add_argument("--profile", help="Target Hermes profile name (e.g. default, programmer)")
    parser.add_argument(
        "--client",
        choices=["hermes", "claude", "cursor", "opencode", "codex", "antigravity"],
        help="Target AI agent (auto-detected if omitted)",
    )
    parser.add_argument(
        "--services",
        default="gmail,drive,calendar",
        help="Comma-separated services (gmail,drive,calendar,docs,sheets,slides,chat,tasks) or 'core'/'all'",
    )
    parser.add_argument("--headless", action="store_true", help="Pin localhost redirect ports for SSH/Docker tunneling")
    parser.add_argument("--base-port", type=int, default=8765, help="Starting port for --headless mode (default: 8765)")
    parser.add_argument("--readonly", action="store_true", help="Restrict Hermes tools to read-only allowlist")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")

    args = parser.parse_args()

    agents = detect_agents(args.profile)
    if not args.json:
        print_detected_agents(agents)

    if args.write_env:
        if not args.client_id or not args.client_secret:
            print("Error: --write-env requires --client-id and --client-secret", file=sys.stderr)
            return 1
        env_path = write_env_credentials(args.client_id, args.client_secret, profile=args.profile)
        print(json.dumps({"status": "saved", "env_file": str(env_path)}, indent=2))
        return 0

    if args.detect:
        if args.json:
            hermes_home = resolve_hermes_home(args.profile)
            env_vars = read_env_file(hermes_home / ".env")
            has_id = bool(os.environ.get("GOOGLE_MCP_CLIENT_ID") or env_vars.get("GOOGLE_MCP_CLIENT_ID"))
            has_secret = bool(os.environ.get("GOOGLE_MCP_CLIENT_SECRET") or env_vars.get("GOOGLE_MCP_CLIENT_SECRET"))
            print(json.dumps({
                "hermes_home": str(hermes_home),
                "credentials_configured": has_id and has_secret,
                "agents": agents,
            }, indent=2))
        return 0

    try:
        services = parse_services(args.services)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if not (args.install or args.copy_skill_only or args.apply):
        if sys.stdin.isatty() and not args.json:
            return interactive_wizard(agents, services, args.headless, args.base_port, args.readonly, profile=args.profile)
        print("\nTip: Run with `--install --client hermes` (or `--all-detected`) to copy skill files and update config automatically.")
        return 0

    if args.all_detected:
        targets = [a["key"] for a in agents if a["detected"]]
        if not targets:
            print("Error: --all-detected specified, but no supported agents were detected.", file=sys.stderr)
            return 1
    elif args.client:
        targets = [args.client]
    elif args.profile:
        targets = ["hermes"]
    else:
        detected_keys = [a["key"] for a in agents if a["detected"]]
        if len(detected_keys) == 1:
            targets = detected_keys
        else:
            print("Error: Multiple or zero agents detected. Specify `--client <name>` or `--all-detected`.", file=sys.stderr)
            return 1

    for key in targets:
        print(f"\n>>> Processing {key} ...")
        if args.install or args.copy_skill_only:
            skill_res = install_skill_files(key, profile=args.profile)
            print(f"  [Skill]  {skill_res['status']} -> {skill_res['destination']}")
        if args.install or args.apply:
            cfg_res = apply_agent_config(key, services, args.headless, args.base_port, args.readonly, profile=args.profile)
            print(f"  [Config] updated {cfg_res['config_path']} (backup: {cfg_res.get('backup_path')})")
            if "snippet" in cfg_res:
                print(cfg_res["snippet"])
            print_next_steps(key, services, args.headless, args.base_port, profile=args.profile)

    return 0


if __name__ == "__main__":
    sys.exit(main())
