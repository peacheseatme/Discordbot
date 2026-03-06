# Creating a Module

Step-by-step guide to adding a new module to Coffeecord.

## 1. Create the Module File

Create `Modules/your_module.py`. Choose one of two patterns:

### Option A: Cog-based Module (Recommended)

Use when your module only needs slash commands. Commands are registered automatically when the Cog is added.

```python
import discord
from discord import app_commands
from discord.ext import commands

# Optional: metadata for auto-discovery (see registry.md)
__module_display_name__ = "Your Module"
__module_description__ = "Short description for /modules status."
__module_category__ = "utilities"  # moderation, configuration, engagement, integrations


class YourModuleCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="hello", description="Say hello")
    async def hello(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message("Hello!", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(YourModuleCog(bot))
```

### Option B: Standalone Group Module

Use when you need a top-level command group (e.g. `/automod`, `/ticket`) or when the module is imported by `Bot.py` for event handling. You must obtain `bot` and `tree` from `__main__`:

```python
import sys
import discord
from discord import app_commands

_main = sys.modules.get("__main__")
if _main and hasattr(_main, "bot") and hasattr(_main, "tree"):
    bot = _main.bot
    tree = _main.tree
else:
    raise RuntimeError(
        "your_module.py must be imported from the main bot script after bot and tree are defined"
    )

my_group = app_commands.Group(name="mygroup", description="My group commands")

@my_group.command(name="do", description="Do something")
async def my_do(interaction: discord.Interaction) -> None:
    await interaction.response.send_message("Done.", ephemeral=True)


async def setup(bot_instance) -> None:
    existing = tree.get_command("mygroup")
    if existing is None:
        tree.add_command(my_group)
```

## 2. Add to the Registry

### Automatic (recommended)

Run:

```bash
c-cord module refresh
```

This scans `Modules/` and appends any new `.py` files to `Storage/Config/modules.json`. Existing entries are left unchanged.

### Manual

Edit `Storage/Config/modules.json` and add an entry:

```json
{
  "id": "your_module",
  "extension": "Modules.your_module",
  "path": "Modules/your_module.py",
  "display_name": "Your Module",
  "description": "Short description.",
  "default_enabled": true,
  "category": "utilities"
}
```

## 3. Respect Module Toggle

If your module should be disabled when an admin turns it off via `/modules toggle`, check before running:

```python
from .module_registry import is_module_enabled

async def my_command(self, interaction: discord.Interaction) -> None:
    if interaction.guild is None:
        await interaction.response.send_message("Guild-only.", ephemeral=True)
        return
    if not await is_module_enabled(interaction.guild.id, "your_module"):
        await interaction.response.send_message(
            "This module is disabled. An admin can enable it with /modules.",
            ephemeral=True,
        )
        return
    # ... rest of command
```

## 4. Persistent Views (Optional)

If your module uses `discord.ui.View` with buttons/selects that must survive bot restarts, register them in `on_ready`:

1. In your module, define a function:

   ```python
   def register_persistent_views(bot_instance) -> None:
       # Restore views from config/data
       bot_instance.add_view(MyPanelView(guild_id))
   ```

2. In `Src/Bot.py`, call it from `on_ready`:

   ```python
   _get_your_module().register_persistent_views(bot)
   ```

3. Add a lazy loader in `Bot.py`:

   ```python
   _your_module: typing.Any | None = None
   def _get_your_module() -> typing.Any:
       global _your_module
       if _your_module is None:
           _your_module = importlib.import_module("Modules.your_module")
       return _your_module
   ```

## 5. Event Integration (Optional)

If your module must react to `on_message`, `on_member_join`, etc., `Bot.py` must call into it. Add a lazy loader (as above) and invoke your module’s function from the event handler:

```python
# In Bot.py on_message:
await _get_your_module().process_message(message)
```

## 6. Module Events for Logging

To have actions logged by the Logging module, dispatch:

```python
bot.dispatch(
    "coffeecord_module_event",
    guild,
    "your_module",
    "action_name",
    actor=interaction.user,
    details="optional details",
    channel_id=interaction.channel.id if interaction.channel else None,
)
```

See [architecture/events-and-logging.md](../architecture/events-and-logging.md) for details.

## Excluded Files

These files in `Modules/` are **not** loadable as extensions:

- `module_registry.py` — registry logic
- `kofi_webhook` — webhook server (if present)

They are listed in `_DISCOVERY_EXCLUDE` in `module_registry.py`.
