# Checks and Permissions

How to restrict commands to certain users or roles.

## Slash command checks

### has_permissions

Require Discord permissions:

```python
@app_commands.command(name="toggle", description="Toggle a module")
@app_commands.checks.has_permissions(manage_guild=True)
async def toggle(self, interaction: discord.Interaction, module: str) -> None:
    ...
```

If the user lacks the permission, Discord shows an error automatically.

### Manual guild check

```python
async def my_command(self, interaction: discord.Interaction) -> None:
    if interaction.guild is None:
        await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
        return
    ...
```

### Manual admin check

```python
async def _require_admin(interaction: discord.Interaction) -> bool:
    if not interaction.guild_id:
        await interaction.response.send_message("Guild-only.", ephemeral=True)
        return False
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message("You need Manage Server.", ephemeral=True)
        return False
    return True

@automod_group.command(name="on", description="Enable automod")
async def automod_on(interaction: discord.Interaction) -> None:
    if not await _require_admin(interaction):
        return
    ...
```

## Prefix command checks

Prefix commands use manual checks (no decorator):

```python
@bot.command(name="synccommands")
async def sync_commands_prefix(ctx: commands.Context):
    if ctx.author.id != BOT_OWNER_ID:
        return  # Silent fail for non-owners
    ...
```

## Module enable check

For module-gated commands, check if the module is enabled for the guild:

```python
from .module_registry import is_module_enabled

async def levelcard_customize(self, interaction: discord.Interaction, ...) -> None:
    if not await is_module_enabled(interaction.guild.id, "leveling"):
        await interaction.response.send_message(
            "This module is currently disabled. An admin can enable it with /modules.",
            ephemeral=True,
        )
        return
    ...
```

## Common patterns

| Check | Slash | Prefix |
|-------|-------|--------|
| Guild only | `if interaction.guild is None` | `if ctx.guild is None` |
| Manage Server | `@app_commands.checks.has_permissions(manage_guild=True)` | `ctx.author.guild_permissions.manage_guild` |
| Owner only | Custom decorator or manual | `ctx.author.id != BOT_OWNER_ID` |
| Module enabled | `is_module_enabled(guild_id, "module_id")` | N/A (prefix commands are in Bot.py) |
