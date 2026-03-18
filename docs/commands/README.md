# Commands

Coffeecord supports two command systems: **slash commands** (Discord application commands) and **prefix commands** (text-based with `.`).

## Overview

| Type | Trigger | Example | Registration |
|------|---------|---------|--------------|
| Slash | `/command` | `/level`, `/automod on` | `tree` (via Cog or `tree.add_command`) |
| Prefix | `.command` | `.synccommands`, `.help` | `@bot.command()` or `@bot.group()` |

## Contents

- [Slash commands](slash-commands.md) — groups, choices, autocomplete, describe
- [Prefix commands](prefix-commands.md) — bot.command, bot.group
- [Checks and permissions](checks-and-permissions.md) — has_permissions, owner checks
- [Permissions reference](permissions.md) — per-command permissions and bot requirements
