# Slash Commands

Slash commands are Discord application commands invoked with `/command`. They are registered on the `tree` (command tree) and synced with Discord.

## Registration

### Via Cog (automatic)

When you add a Cog with `bot.add_cog(cog)`, any `@app_commands.command` and `app_commands.Group` attributes are automatically registered. Do **not** call `tree.add_command()` for Cog commands.

```python
class MyCog(commands.Cog):
    my_group = app_commands.Group(name="mygroup", description="My group")

    @my_group.command(name="do", description="Do something")
    async def do(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message("Done.", ephemeral=True)
```

### Via tree.add_command (standalone)

For standalone modules (e.g. automod, tickets):

```python
tree.add_command(automod_group)
```

## Command Structure

### Top-level command

```python
@app_commands.command(name="level", description="Show level card")
async def level(self, interaction: discord.Interaction, user: discord.Member | None = None) -> None:
    ...
```

### Nested groups

```python
parent = app_commands.Group(name="automod", description="Automod management")
child = app_commands.Group(name="set", description="Set values", parent=parent)

@child.command(name="log", description="Set log channel")
async def automod_set_log(interaction: discord.Interaction, channel: discord.TextChannel | None = None) -> None:
    ...
```

Result: `/automod set log [channel]`

### GroupCog (Cog as group)

```python
class ModulesCommandCog(commands.GroupCog, group_name="modules", group_description="View and toggle modules."):
    @app_commands.command(name="status", description="Show module status")
    async def status(self, interaction: discord.Interaction) -> None:
        ...
```

Result: `/modules status`

## Parameters

### Basic types

- `discord.Member`, `discord.User`, `discord.TextChannel`, `discord.Role`
- `str`, `int`, `float`, `bool`
- `Optional[T]` for optional parameters

### describe

Add descriptions for parameters (shown in Discord UI):

```python
@app_commands.describe(
    url="Background image URL (GIFs require supporter)",
    name_text="Display name color (hex, e.g. #50FF78)",
)
async def levelcard_customize(
    self,
    interaction: discord.Interaction,
    url: Optional[str] = None,
    name_text: Optional[str] = None,
) -> None:
    ...
```

## Choices

Restrict a string parameter to predefined options:

```python
EXEMPT_ACTION_CHOICES = [
    app_commands.Choice(name="Add", value="add"),
    app_commands.Choice(name="Remove", value="remove"),
]

@automod_exempt_group.command(name="role", description="Add/remove role exemption")
@app_commands.choices(action=EXEMPT_ACTION_CHOICES)
async def automod_exempt_role(
    interaction: discord.Interaction,
    action: app_commands.Choice[str],
    role: discord.Role,
) -> None:
    ...
```

## Autocomplete

Provide dynamic choices as the user types:

```python
async def _module_autocomplete(
    self,
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    query = (current or "").strip().lower()
    modules = await load_module_registry()
    choices = []
    for module in modules:
        if query and query not in str(module.get("id", "")).lower():
            continue
        choices.append(app_commands.Choice(name=module["display_name"][:100], value=module["id"]))
        if len(choices) >= 25:
            break
    return choices

@app_commands.command(name="toggle", description="Toggle a module")
@app_commands.autocomplete(module=_module_autocomplete)
async def toggle(self, interaction: discord.Interaction, module: str) -> None:
    ...
```

## Response

- `await interaction.response.send_message(...)` — initial response (required within ~3 seconds)
- `await interaction.followup.send(...)` — follow-up (after `defer()`)
- `ephemeral=True` — only the invoker sees the message
- `await interaction.response.defer()` — defer if processing takes longer than a few seconds

## Syncing

Slash commands are synced to Discord on `on_ready` via `tree.sync()`. For manual sync (e.g. after adding commands at runtime), use the owner-only prefix command:

```
.synccommands
```
