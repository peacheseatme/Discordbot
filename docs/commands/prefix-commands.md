# Prefix Commands

Prefix commands are text-based commands triggered by a prefix (default: `.`). They are defined in `Src/Bot.py` with `@bot.command()` and `@bot.group()`.

## Configuration

```python
bot = commands.Bot(command_prefix=".", intents=intents)
```

Users invoke commands with `.commandname` (e.g. `.help`, `.synccommands`).

## Simple command

```python
@bot.command(name="synccommands")
async def sync_commands_prefix(ctx: commands.Context):
    if ctx.author.id != BOT_OWNER_ID:
        return
    try:
        synced = await tree.sync()
        await ctx.send(f"✅ Synced {len(synced)} commands!")
    except Exception as e:
        await ctx.send(f"❌ Failed to sync: {e}")
```

## Command group

```python
@bot.group(name="kofi", invoke_without_command=True)
async def kofi_group(ctx: commands.Context):
    if ctx.invoked_subcommand is None:
        await ctx.send("Use .kofi link, .kofi unlink, etc.")

@kofi_group.command()
async def link(ctx: commands.Context, code: str):
    ...
```

- `invoke_without_command=True` — running `.kofi` without a subcommand calls the group handler
- Subcommands: `.kofi link <code>`, `.kofi unlink`, etc.

## Context

`ctx: commands.Context` provides:

- `ctx.author` — user who invoked
- `ctx.guild` — guild (or None in DMs)
- `ctx.channel` — channel
- `ctx.send(...)` — send a message
- `ctx.invoked_subcommand` — subcommand that was invoked (for groups)

## Owner-only

Prefix commands often use manual owner checks:

```python
@bot.command(name="clearchache")
async def clearchache_prefix(ctx: commands.Context):
    if ctx.author.id != BOT_OWNER_ID:
        return
    # ... owner-only logic
```

## Where prefix commands live

Prefix commands are defined in `Src/Bot.py`. They are **not** in modules; they are part of the core bot. Common examples:

- `.synccommands` — sync slash commands (owner)
- `.clearchache` — clear and resync commands (owner)
- `.kofi link` / `.kofi unlink` — Ko-fi linking

## Slash vs prefix

| Aspect | Slash | Prefix |
|--------|-------|--------|
| Trigger | `/command` | `.command` |
| Location | Modules or Bot.py | Bot.py only |
| Discovery | Discord UI | User must know |
| Permissions | `@app_commands.checks.has_permissions` | Manual checks |

For new functionality, prefer slash commands; use prefix for owner utilities or legacy behavior.
