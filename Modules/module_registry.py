import asyncio
import json
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "Storage" / "Config"
REGISTRY_PATH = CONFIG_DIR / "modules.json"
STATE_PATH = CONFIG_DIR / "module_states.json"

_REGISTRY_LOCK = asyncio.Lock()
_STATE_LOCK = asyncio.Lock()

REGISTRY_DEFAULT: dict[str, list[dict[str, Any]]] = {
    "modules": [
        {
            "id": "automod",
            "extension": "Modules.automod",
            "path": "Modules/automod.py",
            "display_name": "Automod",
            "description": "Spam, caps, link, mention, keyword filters, and escalation.",
            "default_enabled": True,
            "category": "moderation",
        },
        {
            "id": "logging",
            "extension": "Modules.logging",
            "path": "Modules/logging.py",
            "display_name": "Logging",
            "description": "Server event and module action logging.",
            "default_enabled": True,
            "category": "configuration",
        },
        {
            "id": "tickets",
            "extension": "Modules.tickets",
            "path": "Modules/tickets.py",
            "display_name": "Tickets",
            "description": "Ticket panel, ticket controls, and ticket management commands.",
            "default_enabled": True,
            "category": "utilities",
        },
        {
            "id": "translate",
            "extension": "Modules.translate",
            "path": "Modules/translate.py",
            "display_name": "Translation",
            "description": "Manual and live translation with per-user settings.",
            "default_enabled": True,
            "category": "utilities",
        },
        {
            "id": "reactionrole",
            "extension": "Modules.reactionrole",
            "path": "Modules/reactionrole.py",
            "display_name": "Reaction Roles",
            "description": "Reaction/button based self-role assignment.",
            "default_enabled": True,
            "category": "configuration",
        },
        {
            "id": "autorole",
            "extension": "Modules.autorole",
            "path": "Modules/autorole.py",
            "display_name": "Auto Roles",
            "description": "Rule-based automatic role assignment.",
            "default_enabled": True,
            "category": "configuration",
        },
        {
            "id": "welcome_leave",
            "extension": "Modules.welcome_leave",
            "path": "Modules/welcome_leave.py",
            "display_name": "Welcome & Leave",
            "description": "Welcome/leave messages and optional exit surveys.",
            "default_enabled": True,
            "category": "configuration",
        },
        {
            "id": "setup_wizard",
            "extension": "Modules.setup_wizard",
            "path": "Modules/setup_wizard.py",
            "display_name": "Setup Wizard",
            "description": "Interactive server setup wizard.",
            "default_enabled": True,
            "category": "configuration",
        },
        {
            "id": "modules_cmd",
            "extension": "Modules.modules_cmd",
            "path": "Modules/modules_cmd.py",
            "display_name": "Module Controls",
            "description": "Per-server module visibility and toggle commands.",
            "default_enabled": True,
            "category": "configuration",
        },
        {
            "id": "leveling",
            "extension": "Modules.leveling",
            "path": "Modules/leveling.py",
            "display_name": "Leveling & XP",
            "description": "XP gain, level-up logic, rewards, and level cards.",
            "default_enabled": True,
            "category": "engagement",
        },
        {
            "id": "kofi",
            "extension": "Modules.kofi",
            "path": "Modules/kofi.py",
            "display_name": "Ko-fi Supporters",
            "description": "Ko-fi linking/claims, supporter state, and webhook helpers.",
            "default_enabled": True,
            "category": "integrations",
        },
        {
            "id": "verification",
            "extension": "Modules.verification",
            "path": "Modules/verification.py",
            "display_name": "Verification",
            "description": "Verification UI, verification flow, and configuration.",
            "default_enabled": True,
            "category": "moderation",
        },
        {
            "id": "polls",
            "extension": "Modules.polls",
            "path": "Modules/polls.py",
            "display_name": "Polls",
            "description": "Poll creation, voting, and poll lifecycle events.",
            "default_enabled": True,
            "category": "engagement",
        },
        {
            "id": "applications",
            "extension": "Modules.applications",
            "path": "Modules/applications.py",
            "display_name": "Applications",
            "description": "Staff application questions, submissions, and review actions.",
            "default_enabled": True,
            "category": "utilities",
        },
        {
            "id": "adaptive_slowmode",
            "extension": "Modules.adaptive_slowmode",
            "path": "Modules/adaptive_slowmode.py",
            "display_name": "Adaptive Slowmode",
            "description": "Adaptive slowmode configuration and trigger handling.",
            "default_enabled": True,
            "category": "moderation",
        },
        {
            "id": "muterole",
            "extension": "Modules.muterole",
            "path": "Modules/muterole.py",
            "display_name": "Mute Role",
            "description": "Mute role creation and configuration commands.",
            "default_enabled": True,
            "category": "moderation",
        },
        {
            "id": "calls",
            "extension": "Modules.calls",
            "path": "Modules/calls.py",
            "display_name": "Calls",
            "description": "Private call channels and call membership management.",
            "default_enabled": True,
            "category": "utilities",
        },
        {
            "id": "nickname",
            "extension": "Modules.nickname",
            "path": "Modules/nickname.py",
            "display_name": "Nickname",
            "description": "Nickname management commands and related checks.",
            "default_enabled": True,
            "category": "utilities",
        },
        {
            "id": "support",
            "extension": "Modules.support",
            "path": "Modules/support.py",
            "display_name": "Support Us",
            "description": "Support information, perks, and support links command.",
            "default_enabled": True,
            "category": "integrations",
        },
    ]
}


def _read_json_sync(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as fp:
            json.dump(default, fp, indent=2, ensure_ascii=True)
        return default
    try:
        with path.open("r", encoding="utf-8") as fp:
            data = json.load(fp)
        return data if isinstance(data, dict) else default
    except (OSError, json.JSONDecodeError):
        return default


def _write_json_sync(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fp:
        json.dump(data, fp, indent=2, ensure_ascii=True)


def _normalize_registry(raw: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    modules_raw = raw.get("modules", [])
    if not isinstance(modules_raw, list):
        return REGISTRY_DEFAULT

    normalized: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for item in modules_raw:
        if not isinstance(item, dict):
            continue
        module_id = str(item.get("id", "")).strip().lower()
        extension = str(item.get("extension", "")).strip()
        path = str(item.get("path", "")).strip()
        if not module_id or not extension or not path or module_id in seen_ids:
            continue
        seen_ids.add(module_id)
        normalized.append(
            {
                "id": module_id,
                "extension": extension,
                "path": path,
                "display_name": str(item.get("display_name", module_id)).strip() or module_id,
                "description": str(item.get("description", "")).strip(),
                "default_enabled": bool(item.get("default_enabled", True)),
                "category": str(item.get("category", "utilities")).strip() or "utilities",
            }
        )

    if not normalized:
        return REGISTRY_DEFAULT
    return {"modules": normalized}


async def load_module_registry() -> list[dict[str, Any]]:
    async with _REGISTRY_LOCK:
        raw = await asyncio.to_thread(_read_json_sync, REGISTRY_PATH, REGISTRY_DEFAULT)
        normalized = _normalize_registry(raw)
        await asyncio.to_thread(_write_json_sync, REGISTRY_PATH, normalized)
        return list(normalized["modules"])


async def get_registry_map() -> dict[str, dict[str, Any]]:
    modules = await load_module_registry()
    return {str(m["id"]): m for m in modules}


async def validate_registry_paths() -> list[str]:
    errors: list[str] = []
    modules = await load_module_registry()
    for module in modules:
        module_path = BASE_DIR / str(module["path"])
        if not module_path.exists():
            errors.append(
                f"Module '{module['id']}' points to missing path: {module['path']}"
            )
    return errors


async def get_guild_module_states(guild_id: int) -> dict[str, bool]:
    module_map = await get_registry_map()
    defaults = {
        module_id: bool(entry.get("default_enabled", True))
        for module_id, entry in module_map.items()
    }
    async with _STATE_LOCK:
        raw = await asyncio.to_thread(_read_json_sync, STATE_PATH, {})
        guild_key = str(guild_id)
        stored = raw.get(guild_key, {})
        if not isinstance(stored, dict):
            stored = {}
        merged = dict(defaults)
        for module_id, value in stored.items():
            if module_id in merged:
                merged[module_id] = bool(value)
        raw[guild_key] = merged
        await asyncio.to_thread(_write_json_sync, STATE_PATH, raw)
    return merged


async def is_module_enabled(guild_id: int, module_id: str) -> bool:
    module_id = str(module_id).strip().lower()
    states = await get_guild_module_states(guild_id)
    return bool(states.get(module_id, True))


async def set_module_enabled(guild_id: int, module_id: str, enabled: bool) -> None:
    module_id = str(module_id).strip().lower()
    if module_id == "modules_cmd":
        return
    module_map = await get_registry_map()
    if module_id not in module_map:
        return
    async with _STATE_LOCK:
        raw = await asyncio.to_thread(_read_json_sync, STATE_PATH, {})
        guild_key = str(guild_id)
        stored = raw.get(guild_key, {})
        if not isinstance(stored, dict):
            stored = {}
        stored[module_id] = bool(enabled)
        raw[guild_key] = stored
        await asyncio.to_thread(_write_json_sync, STATE_PATH, raw)
