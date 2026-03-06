# Module Types

Coffeecord supports two module patterns: **Cog-based** and **standalone Group**.

## Cog-based Modules

**Examples**: `leveling`, `modules_cmd`, `logging`, `translate`, `autorole`, `welcome_leave`, `setup_wizard`, `reactionrole`, `test_module`

### Characteristics

- Define a class inheriting from `commands.Cog` (or `commands.GroupCog`)
- Use `@app_commands.command` and `@app_commands.Group` as class attributes
- In `setup(bot)`: `await bot.add_cog(YourCog(bot))`
- No need to import `bot` or `tree` from `__main__`
- `add_cog()` automatically registers slash commands from the Cog

### Example

```python
class LevelingCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    xp_group = app_commands.Group(name="xp", description="XP config")
    levelcard_group = app_commands.Group(name="levelcard", description="Level card")

    @levelcard_group.command(name="customize", description="Customize level card")
    async def levelcard_customize(self, interaction: discord.Interaction, ...) -> None:
        ...

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(LevelingCog(bot))
```

### GroupCog

For a Cog that is also a top-level slash group:

```python
class ModulesCommandCog(commands.GroupCog, group_name="modules", group_description="View and toggle server modules."):
    ...
```

This creates `/modules` as a group with subcommands.

## Standalone Group Modules

**Examples**: `automod`, `tickets`

### Characteristics

- Do **not** use a Cog
- Define `app_commands.Group` at module level
- Must obtain `bot` and `tree` from `sys.modules["__main__"]`
- In `setup(bot_instance)`: `tree.add_command(group)`
- Often provide functions called by `Bot.py` event handlers (e.g. `process_automod`, `register_persistent_views`)

### Why Standalone?

- Need `tree` to add a top-level group before the Cog system existed
- Need to be imported by `Bot.py` for `on_message`, `on_member_join`, etc.
- Use `register_persistent_views(bot)` called from `on_ready`

### Example

```python
import sys
_main = sys.modules.get("__main__")
if _main and hasattr(_main, "bot") and hasattr(_main, "tree"):
    bot = _main.bot
    tree = _main.tree
else:
    raise RuntimeError("automod.py must be imported from the main bot script")

automod_group = app_commands.Group(name="automod", description="Automod management")
automod_set_group = app_commands.Group(name="set", parent=automod_group)

@automod_group.command(name="on", description="Enable automod")
async def automod_on(interaction: discord.Interaction) -> None:
    ...

async def setup(bot_instance) -> None:
    if tree.get_command("automod") is None:
        tree.add_command(automod_group)
```

## When to Use Which

| Use Cog | Use Standalone Group |
|---------|----------------------|
| New modules | Legacy modules (automod, tickets) |
| Only slash commands | Need `tree.add_command` + event hooks |
| Self-contained logic | Must be called from `Bot.py` events |
| Simpler setup | More setup, but flexible |

For new modules, prefer **Cog-based** unless you need event integration or persistent views that require `Bot.py` to call into the module.
