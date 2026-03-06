# Module Registry

The module registry controls which modules are loaded and how they appear in `/modules status`.

## Files

| File | Purpose |
|------|---------|
| `Storage/Config/modules.json` | List of loadable modules (id, extension, path, metadata) |
| `Storage/Config/module_states.json` | Per-guild enable/disable state |
| `Modules/module_registry.py` | Registry logic, discovery, state management |

## Registry Entry Format

Each module in `modules.json` has:

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique identifier (lowercase, used in `/modules toggle`) |
| `extension` | string | Python import path, e.g. `Modules.automod` |
| `path` | string | Relative path, e.g. `Modules/automod.py` |
| `display_name` | string | Shown in `/modules status` |
| `description` | string | Shown in `/modules status` |
| `default_enabled` | bool | Default per-guild state (default: `true`) |
| `category` | string | Grouping: `moderation`, `configuration`, `utilities`, `engagement`, `integrations` |

## Discovery

`discover_modules_on_disk()` scans `Modules/*.py` and builds a registry entry for each file, excluding:

- `module_registry`
- `kofi_webhook`

Metadata is read from module-level variables (if present):

```python
__module_display_name__ = "My Module"
__module_description__ = "Does something useful."
__module_category__ = "utilities"
```

If absent, `display_name` is derived from the filename (e.g. `my_module` → `My Module`).

## refresh_registry

```bash
c-cord module refresh
```

Or with dry-run:

```bash
c-cord module refresh --dry-run
```

`refresh_registry()`:

1. Reads existing `modules.json`
2. Calls `discover_modules_on_disk()`
3. Appends entries for modules not already in the registry
4. Writes merged data back (unless `--dry-run`)

Existing entries are never modified; only new modules are added.

## Per-Guild State

- `get_guild_module_states(guild_id)` — returns `{module_id: bool}` for a guild
- `is_module_enabled(guild_id, module_id)` — returns whether a module is enabled
- `set_module_enabled(guild_id, module_id, enabled)` — sets state (persisted to `module_states.json`)

`modules_cmd` cannot be disabled; attempts to disable it are ignored.

## Loading Order

1. `Modules.modules_cmd` is always loaded first
2. Other modules from the registry are loaded in order
3. Modules whose `path` does not exist are skipped (with a warning)

## Validation

`validate_registry_paths()` checks that each module’s `path` exists. Missing paths cause the module to be skipped at startup.
