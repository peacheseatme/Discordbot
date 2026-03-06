# Architecture

High-level structure of the Coffeecord bot.

## Contents

- [Bot loading](bot-loading.md) — startup, extension loading, on_ready
- [Events and logging](events-and-logging.md) — custom events, module event dispatch

## Project layout

```
Discordbot/
├── Src/
│   ├── Bot.py          # Main entry, bot, tree, event handlers
│   └── .env            # DISCORD_TOKEN, etc.
├── Modules/
│   ├── module_registry.py
│   ├── json_cache.py
│   ├── automod.py
│   ├── leveling.py
│   ├── tickets.py
│   └── ...
├── Storage/
│   ├── Config/         # modules.json, module_states.json, etc.
│   ├── Data/           # Runtime data (tickets, xp, warns, etc.)
│   ├── Logs/
│   └── Temp/
├── bot.sh              # CLI: start, stop, restart, logs, module refresh
└── install.sh
```

## Entry point

- **CLI**: `bot.sh` (or `c-cord` symlink) — start, stop, restart, logs, update, module refresh
- **Python**: `Src/Bot.py` — `python Src/Bot.py` or via `bot.sh start`
