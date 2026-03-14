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
| `console` | Live console — tail bot log (commands, errors, etc.) |
| `console -n N` | Last N lines, no follow |
| `console clear` | Clear the bot log file |
| `update` | git pull → pip install → restart |
| `update -f` | Continue even if git pull fails |
| `module refresh` | Scan Modules/, add new files to registry |
| `module refresh_registry` | Alias for module refresh |
| `module refresh --dry-run` | Preview additions without writing |

## Config file

`Storage/Config/c-cord.json` optionally overrides paths and limits for `c-cord start` / `restart`:

| Key | Default | Description |
|-----|---------|-------------|
| `bot_entry` | `Src/Bot.py` | Bot entry script |
| `env_file` | `Src/.env` | Environment file |
| `log_dir` | `Storage/Logs` | Log directory |
| `temp_dir` | `Storage/Temp` | Temp directory |
| `ticket_env_file` | `Src/ticket.env` | Ticket config |
| `max_log_bytes` | `10485760` | Rotate log when larger (bytes) |
| `max_rotated` | `5` | Max rotated log files to keep |
| `ngrok_enabled` | `true` | Start ngrok with bot when Ko-fi is configured |
| `kofi_webhook_host` | *(none)* | Your ngrok host (e.g. `xxx.ngrok-free.dev`) — used to display the Ko-fi webhook URL on start |

Paths are relative to the project root unless absolute. The config is loaded automatically when present.

## ngrok (Ko-fi webhooks)

When `KOFI_VERIFICATION_TOKEN` is set in `Src/.env`, `c-cord start` and `restart` automatically:

1. Install ngrok if missing (download to `Storage/Tools/` or try `snap install`)
2. Start ngrok to expose `KOFI_PORT` (default 5000)
3. Stop ngrok when `c-cord stop` runs

Set `ngrok_enabled: false` in `Storage/Config/c-cord.json` to run ngrok manually. Run `ngrok config add-authtoken <token>` once after installing.

Add `kofi_webhook_host` (your ngrok host, e.g. `postmyxedematous-meadow-unswaggering.ngrok-free.dev`) to display the full webhook URL when ngrok starts.

## Paths

- **Entry**: `Src/Bot.py` (overridable via config)
- **Env**: `Src/.env` (DISCORD_TOKEN, etc.)
- **Logs**: `Storage/Logs/bot.log`
- **PID**: `Storage/Temp/bot.pid`
- **Venv**: `.venv/`

## Ko-fi setup

Use the helper script to add Ko-fi webhook configuration:

```bash
./scripts/add_kofi.sh
```

This prompts for `KOFI_VERIFICATION_TOKEN` and `KOFI_PORT`, updates `Src/.env`, and prints next steps. Then run `c-cord restart` — ngrok starts automatically.

## Module refresh

```bash
c-cord module refresh
```

Scans `Modules/*.py`, excludes `module_registry` and `kofi_webhook`, and appends any new modules to `Storage/Config/modules.json`. Use `--dry-run` to see what would be added without writing.
