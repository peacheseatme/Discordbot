# Events and Logging

Custom events and how they integrate with the Logging module.

## Custom events

Coffeecord uses custom events for cross-module communication and logging:

| Event | Args | Purpose |
|-------|------|---------|
| `coffeecord_module_event` | guild, module_name, action, actor, details, channel_id | Generic module action (for logging) |
| `coffeecord_ticket_event` | guild, actor, action, channel_id, details | Ticket-specific actions |
| `coffeecord_warn` | (warn payload) | Automod warn issued |
| `coffeecord_automod_action` | (action payload) | Automod took action (delete, timeout, etc.) |

## Dispatching module events

### From Bot.py

```python
def _dispatch_module_log_event(
    guild: discord.Guild | None,
    module_name: str,
    action: str,
    actor: discord.abc.User | None = None,
    details: str = "",
    channel_id: int | None = None,
) -> None:
    if guild is None:
        return
    try:
        bot.dispatch("coffeecord_module_event", guild, module_name, action, actor, details, channel_id)
    except Exception:
        pass
```

### From a module

```python
async def _dispatch_module_event(
    bot: commands.Bot,
    guild: discord.Guild | None,
    module_name: str,
    action: str,
    actor: discord.abc.User | None = None,
    details: str = "",
    channel_id: int | None = None,
) -> None:
    if guild is None:
        return
    try:
        bot.dispatch("coffeecord_module_event", guild, module_name, action, actor, details, channel_id)
    except Exception:
        return
```

Example usage:

```python
await _dispatch_module_event(
    self.bot,
    interaction.guild,
    "leveling",
    "levelcard_customize",
    actor=interaction.user,
    details="; ".join(f"{k}={v}" for k, v in updates.items()),
    channel_id=interaction.channel.id if interaction.channel else None,
)
```

## Listening for events

The Logging module listens for these events:

```python
@commands.Cog.listener("on_coffeecord_module_event")
async def on_coffeecord_module_event(
    self,
    guild: discord.Guild,
    module_name: str,
    action: str,
    actor: discord.abc.User | None,
    details: str,
    channel_id: int | None,
) -> None:
    # Log to configured channel
    ...
```

Other modules can also listen:

```python
@commands.Cog.listener("on_coffeecord_module_event")
async def on_coffeecord_module_event(self, guild, module_name, action, ...) -> None:
    if module_name == "autorole":
        # React to autorole changes
        ...
```

## Event naming

- Use `coffeecord_` prefix for custom events
- `coffeecord_module_event` is the generic “something happened in a module” event
- Module-specific events (e.g. `coffeecord_ticket_event`) carry extra context
