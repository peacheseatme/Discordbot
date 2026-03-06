# Common Module Patterns

Recurring patterns used across modules.

## HTTP requests

Use the shared `bot.http_session` when available (set in `on_ready`). Fall back to a temporary session if the bot has not finished starting:

```python
session = getattr(self.bot, "http_session", None)
close_session = session is None
if session is None:
    session = aiohttp.ClientSession()
try:
    async with session.get(url) as resp:
        ...
finally:
    if close_session:
        await session.close()
```

## Blocking work (PIL, etc.)

Run CPU-heavy work in a thread pool to avoid blocking the event loop:

```python
await asyncio.to_thread(_render_levelcard_sync, ...)
```

## Supporter check

Supporters are stored in `Storage/Data/supporters.json`. Modules that need supporter checks implement their own helper (e.g. `_supporter_active` in leveling, `_is_supporter` in translate). To gate a feature for supporters:

```python
# Implement or reuse a helper that reads supporters.json
def _supporter_active(user_id: int) -> bool:
    data = json_cache.get(SUPPORTERS_FILE, {"supporters": {}})
    record = data.get("supporters", {}).get(str(user_id))
    return isinstance(record, dict) and bool(record.get("active", False))

if not _supporter_active(interaction.user.id):
    await interaction.response.send_message("🚫 Supporters only.", ephemeral=True)
    return
```

## Guild-only command

```python
if interaction.guild is None:
    await interaction.response.send_message("This command can only be used in servers.", ephemeral=True)
    return
```

## Defer for long operations

If a command may take more than a few seconds (e.g. fetching images, rendering):

```python
await interaction.response.defer()
# ... do work ...
await interaction.followup.send(...)
```

## Constants

Define string literals and fixed values as constants at the top of the file or in a shared `constants` module:

```python
PRESET_LIGHT = "light"
PRESET_MEDIUM = "medium"
PRESET_LABELS = {
    PRESET_LIGHT: "Light",
    PRESET_MEDIUM: "Medium",
}
```
