# Config and Data

How config and data files are stored and accessed.

## Paths

Paths are typically defined relative to the project root (parent of `Modules/`):

```python
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent  # Discordbot root
CONFIG_PATH = BASE_DIR / "Storage" / "Config" / "automod.json"
DATA_PATH = BASE_DIR / "Storage" / "Data" / "warns.json"
```

Or with `os.path`:

```python
_TICKETS_BASE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Storage")
TICKETS_FILE = os.path.join(_TICKETS_BASE, "Data", "tickets.json")
```

## json_cache

`Modules/json_cache` provides in-memory caching for JSON files to reduce disk I/O.

### get

```python
from Modules import json_cache

data = json_cache.get(path, default=None)
```

- Returns cached data if the path was previously loaded
- Otherwise reads from disk, caches, and returns
- If the file does not exist, returns `default` (or `{}` if `default` is None)

### set_

```python
json_cache.set_(path, data)
```

- Writes `data` to disk (creates parent dirs if needed)
- Updates the in-memory cache

### invalidate

```python
json_cache.invalidate(path)
```

- Removes the path from the cache (e.g. after external write)

### Usage in modules

```python
def load_json(path: Path, default=None):
    return json_cache.get(path, default if default is not None else {})

def save_json(path: Path, data) -> None:
    json_cache.set_(path, data)
```

## Common file locations

| Path | Purpose |
|------|---------|
| `Storage/Config/modules.json` | Module registry |
| `Storage/Config/module_states.json` | Per-guild module enable/disable |
| `Storage/Config/automod.json` | Automod config |
| `Storage/Data/tickets.json` | Ticket state |
| `Storage/Data/warns.json` | Automod warns |
| `Storage/Data/supporters.json` | Ko-fi supporters |
| `Storage/Data/xp.json` | XP/leveling (legacy path: `Main/xp.json`) |
| `Storage/Temp/level_cache/` | Level card image cache |
| `Storage/Logs/` | Bot logs |

## Legacy paths

Some modules still use `Main/` for config (e.g. `Main/xp.json`, `Main/leveling.json`). New modules should prefer `Storage/Config/` and `Storage/Data/`.

## Creating directories

When writing files, ensure parent directories exist:

```python
path.parent.mkdir(parents=True, exist_ok=True)
```

`json_cache.set_()` does this automatically.
