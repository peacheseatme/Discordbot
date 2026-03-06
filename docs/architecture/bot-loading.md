# Bot Loading

How the bot starts and loads modules.

## Startup flow

1. Load `.env` (DISCORD_TOKEN, etc.)
2. Create `bot = commands.Bot(command_prefix=".", intents=...)` and `tree = bot.tree`
3. Load `Modules.modules_cmd` (always first)
4. Load remaining modules from `Storage/Config/modules.json` via `load_module_registry()`
5. For each module: `await bot.load_extension(extension)`
6. Start bot: `await bot.start(token)`

## Extension loading

`bot.load_extension("Modules.automod")`:

1. Imports the module
2. Calls `await setup(bot)` (or `setup(bot_instance)`)

The module’s `setup()` either:

- `await bot.add_cog(cog)` — for Cog modules
- `tree.add_command(group)` — for standalone Group modules

## on_ready

When the bot connects:

```python
@bot.event
async def on_ready():
    bot.add_view(VerifyStartView("placeholder"))
    bot.http_session = aiohttp.ClientSession()
    _get_tickets_module().register_persistent_views(bot)
    _get_automod_module()   # Preload
    _get_leveling_module()  # Preload
    synced = await tree.sync()
```

- **Persistent views**: Ticket panels and similar views are re-registered so buttons/selects work after restart
- **Preload**: Automod and leveling are imported early to avoid first-use delay in `on_message`
- **tree.sync()**: Syncs slash commands with Discord

## Lazy module loading

Some modules are imported on demand via `_get_*_module()`:

- `_get_tickets_module()` — for `register_persistent_views`
- `_get_automod_module()` — for `process_automod`, `process_member_join`
- `_get_leveling_module()` — for `award_message_xp`, `award_reaction_xp`, `award_voice_xp`

These are called from `Bot.py` event handlers. The modules are still loaded as extensions; the lazy loader avoids circular imports and ensures the module is imported when needed.

## Event flow (message example)

1. `on_message` fires in `Bot.py`
2. `_get_automod_module().process_automod(message)` — if it returns True, message handling stops
3. Adaptive slowmode, XP, etc.
4. `_get_leveling_module().award_message_xp(bot, message)`

## Skipped modules

Modules whose `path` in the registry does not exist are skipped. `validate_registry_paths()` reports these at startup.
