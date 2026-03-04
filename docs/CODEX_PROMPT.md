# Coffeecord — Codex / GPT 5.3 Project Prompt

Paste the contents of this file at the start of a Codex or GPT session to give the AI
full context for working on this project.

---

## Ready Prompt To Paste

Use this as your direct implementation request after sharing this file:

```text
You are working in the Coffeecord repository.

Please implement all of the following:

1) Improve the module system so I can drop a new file into Modules/ and run:
   c-cord module refresh
   It should discover and register new modules automatically.

2) Add force-start behavior:
   c-cord start -f
   This should ignore non-fatal startup errors and continue whenever possible.
   Only fail when startup is truly impossible (for example missing venv, missing token, or missing bot entry).

3) Add additional useful CLI flags:
   - stop -9 / --kill
   - status -v / --verbose
   - update -f / --force
   - module refresh --dry-run

Acceptance criteria:
- c-cord module refresh adds new module entries to Storage/Config/modules.json.
- c-cord module refresh --dry-run shows changes without writing files.
- c-cord start -f does not abort on syntax-check failures and reports warnings clearly.
- Help/usage output documents all flags and examples.
- install.sh post-install command list includes the new commands/flags.
- Existing behavior remains backward compatible.

After changes:
- Run relevant quick checks.
- Show what changed in plain language.
- List any follow-up steps I should run.
```

---

## What Is This Project

**Coffeecord** is a self-hosted Discord bot built with discord.py 2.x.
It has a pluggable module system: every feature lives in `Modules/` as a discord.py
extension (cog). Modules are registered in a JSON registry and toggled per-guild.
The CLI wrapper `c-cord` (installed to `~/.local/bin`) wraps `bot.sh` for everyday
operations.

---

## Repository Layout

```
Discordbot/
├── Main/
│   ├── Bot.py              # Bot instance, intents, event handlers, startup loader
│   └── .env                # Secrets — DISCORD_TOKEN, optional KOFI_*
├── Modules/                # Drop-in extensions (one .py = one module)
│   ├── module_registry.py  # Registry I/O + disk discovery (NOT a loadable cog)
│   ├── modules_cmd.py      # /modules slash commands — always loaded at startup
│   ├── kofi_webhook.py     # HTTP helper — excluded from auto-discovery
│   └── *.py                # All other files are loadable cogs
├── Storage/
│   ├── Config/
│   │   ├── modules.json        # Registered module list
│   │   └── module_states.json  # Per-guild enabled/disabled state
│   ├── Data/               # Runtime JSON (supporters, transcripts, XP, etc.)
│   ├── Logs/               # bot.log + rotated logs
│   └── Temp/               # bot.pid
├── docs/
│   └── CODEX_PROMPT.md     # ← this file
├── bot.sh                  # All runtime operations
├── install.sh              # One-time setup: venv, .env, c-cord symlink
└── requirements.txt
```

---

## c-cord CLI Reference

`c-cord` is a thin wrapper: `exec "$BOT_SH_PATH" "$@"`. Every command goes through `bot.sh`.

### Commands and Flags

```
c-cord start                Start bot in background
       start -f / --force   Ignore non-fatal errors (syntax warnings, immediate
                            crash after start). Still fails on missing venv/token.

c-cord stop                 Graceful SIGTERM (waits up to 10 s, then SIGKILL)
       stop -9 / --kill     Skip graceful — SIGKILL immediately

c-cord restart              stop + start
       restart -f           stop + start -f

c-cord status               One-line running/stopped indicator with PID and uptime
       status -v / --verbose  Also print last 10 log lines

c-cord logs                 tail -f (follow live)
       logs -n N            Last N lines, no follow (e.g. logs -n 50)

c-cord update               git pull → pip install -r requirements.txt → restart
       update -f / --force  Continue even if git pull fails

c-cord module refresh           Scan Modules/, add new .py files to modules.json
       module refresh --dry-run  Show what would be added — no file writes
```

### Rules for All Flags

- Short and long forms are equivalent (`-f` = `--force`, `-9` = `--kill`, `-v` = `--verbose`).
- Flags that are not recognised are silently ignored (safe to script).
- Exit codes: 0 = success/warn, 1 = hard failure.

---

## Module System

### How Modules Are Loaded at Startup

`Main/Bot.py` → `_run_bot_with_kofi()`:

1. Calls `validate_registry_paths()` — lists modules in `modules.json` whose `.py` is missing; they are skipped silently.
2. Always loads `Modules.modules_cmd` first (provides `/modules` slash commands).
3. Iterates `load_module_registry()` and calls `bot.load_extension(extension)` for each.
4. Failures on individual extensions are printed but do not abort startup.

### Adding a Drop-in Module

1. Create `Modules/my_module.py` with a `setup(bot)` async function (standard discord.py cog pattern).
2. Optionally declare metadata near the top:
   ```python
   __module_display_name__ = "My Module"
   __module_description__  = "Short description shown in /modules status."
   __module_category__     = "utilities"  # moderation | configuration | engagement | integrations | utilities
   ```
3. Run `c-cord module refresh` — this calls `refresh_registry()` in `module_registry.py`,
   scans `Modules/*.py`, and appends any new entries to `Storage/Config/modules.json`.
4. `c-cord restart` to load it.

If metadata variables are absent, `refresh_registry()` derives `display_name` from the
filename (snake_case → Title Case) and defaults `category` to `"utilities"`.

### Files Excluded from Auto-Discovery

`module_registry` and `kofi_webhook` — neither is a loadable cog.

### Registry Schema (`Storage/Config/modules.json`)

```json
{
  "modules": [
    {
      "id":              "my_module",          // unique, lowercase
      "extension":       "Modules.my_module",  // Python import path
      "path":            "Modules/my_module.py",
      "display_name":    "My Module",
      "description":     "...",
      "default_enabled": true,
      "category":        "utilities"
    }
  ]
}
```

### Per-Guild State (`Storage/Config/module_states.json`)

```json
{ "GUILD_ID": { "my_module": true, "automod": false } }
```

`is_module_enabled(guild_id, module_id)` is the canonical check inside any module.

---

## Coding Conventions

| Topic | Rule |
|-------|------|
| Constants | Define at top of file or import from a shared constants module — no bare strings |
| Commits | Conventional Commits: `feat:`, `fix:`, `docs:`, `chore:` — under 60 chars |
| Python `-c` calls | Single quotes outside, double inside: `python -c 'from X import Y; print("ok")'` |
| Incomplete work | Leave `# TODO: ...` comment instead of placeholder code |
| Module events | `bot.dispatch("coffeecord_module_event", guild, module_name, action, actor, details, channel_id)` |
| New modules | Must have `async def setup(bot: commands.Bot) -> None:` |

---

## Key Entry Points

| Task | Where |
|------|-------|
| Add a feature | New `Modules/<name>.py` cog |
| Change CLI behaviour | `bot.sh` |
| Change startup/login | `Main/Bot.py` → `_run_bot_with_kofi()` |
| Change module discovery | `Modules/module_registry.py` → `refresh_registry()` / `discover_modules_on_disk()` |
| Change per-guild toggle logic | `Modules/module_registry.py` → `set_module_enabled()` |
| Change /modules slash commands | `Modules/modules_cmd.py` |
