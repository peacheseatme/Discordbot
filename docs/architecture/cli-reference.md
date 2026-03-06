# CLI Reference (bot.sh / c-cord)

The bot is controlled via `bot.sh` or the `c-cord` symlink.

## Commands

| Command | Description |
|---------|-------------|
| `start` | Start bot in background |
| `start -f` / `start --force` | Start, ignore non-fatal errors |
| `stop` | Graceful stop (SIGTERM, then SIGKILL if needed) |
| `stop -9` / `stop --kill` | Hard stop (SIGKILL immediately) |
| `restart` | stop + start |
| `restart -f` | stop + start with force |
| `status` | Show PID and uptime |
| `status -v` / `status --verbose` | Status + last 10 log lines |
| `logs` | Follow log (tail -f) |
| `logs -n N` | Last N lines, no follow |
| `update` | git pull → pip install → restart |
| `update -f` | Continue even if git pull fails |
| `module refresh` | Scan Modules/, add new files to registry |
| `module refresh_registry` | Alias for module refresh |
| `module refresh --dry-run` | Preview additions without writing |

## Paths

- **Entry**: `Src/Bot.py`
- **Env**: `Src/.env` (DISCORD_TOKEN, etc.)
- **Logs**: `Storage/Logs/bot.log`
- **PID**: `Storage/Temp/bot.pid`
- **Venv**: `.venv/`

## Module refresh

```bash
c-cord module refresh
```

Scans `Modules/*.py`, excludes `module_registry` and `kofi_webhook`, and appends any new modules to `Storage/Config/modules.json`. Use `--dry-run` to see what would be added without writing.
