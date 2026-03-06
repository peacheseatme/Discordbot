# Modules

Modules are the primary way to extend Coffeecord. Each module lives in `Modules/*.py` and is loaded at startup via discord.py extensions.

## Overview

- **Registry**: `Storage/Config/modules.json` lists all loadable modules.
- **Discovery**: New `.py` files in `Modules/` can be added with `c-cord module refresh`.
- **Per-server toggle**: Admins enable/disable modules per guild via `/modules toggle`.

## Module Types

| Type | Example | Registration |
|------|---------|--------------|
| **Cog** | `leveling`, `modules_cmd` | `bot.add_cog(cog)` — commands auto-register |
| **Standalone Group** | `automod`, `tickets` | `tree.add_command(group)` in `setup()` |

See [module-types.md](module-types.md) for details.

## Key Files

| Path | Purpose |
|------|---------|
| `Modules/module_registry.py` | Discovery, `modules.json`, `module_states.json` |
| `Modules/json_cache.py` | In-memory JSON cache for config/data |
| `Storage/Config/modules.json` | Module registry (id, extension, path, metadata) |
| `Storage/Config/module_states.json` | Per-guild enable/disable state |

## See also

- [Common patterns](common-patterns.md) — HTTP, blocking work, supporter checks
