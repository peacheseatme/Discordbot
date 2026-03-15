# Themes and Command Response Customization

Themes let you customize moderation DM messages (ban, kick, timeout, warn) and command response text. **Supporters** (Ko-fi linked) can upload custom themes and command response overrides.

## Moderation Themes

### Commands

| Command | Description |
|--------|-------------|
| `/theme list` | List available themes (presets and custom) |
| `/theme set <name>` | Set the server's moderation theme |
| `/theme preview <name>` | Preview a theme's moderation messages |
| `/theme info` | Show current theme and settings |
| `/theme upload` | Upload a custom theme JSON (supporters only) |
| `/theme delete <name>` | Delete a custom theme (supporters only) |

### Preset Themes

Presets live in `Storage/Config/theme_storage/`:

- **default** — Standard moderation notices
- **darth_vader** — Dark theme
- **professional** — Formal tone
- **friendly** — Casual tone

### Custom Theme JSON Format

Supporters can upload themes via `/theme upload`. Max 50KB, 3 custom themes per guild.

```json
{
  "name": "My Theme",
  "author": "Your Name",
  "version": "1.0",
  "description": "Custom moderation messages.",
  "actions": {
    "ban": {
      "title": "Moderation Notice: Ban",
      "description": "You have been banned from {guild_name}.\n\n**Reason:** {reason}",
      "color": "#E67E22"
    },
    "kick": {
      "title": "Moderation Notice: Kick",
      "description": "You have been kicked from {guild_name}.",
      "color": "#E67E22"
    },
    "timeout": {
      "title": "Moderation Notice: Timeout",
      "description": "You have been timed out for {duration}.",
      "color": "#E67E22"
    },
    "warn": {
      "title": "Moderation Notice: Warn",
      "description": "You have received a warning in {guild_name}.",
      "color": "#E67E22"
    }
  }
}
```

**Placeholders:** `{guild_name}`, `{user}`, `{reason}`, `{duration}`, `{rule}`

---

## Command Response Overrides

Supporters can customize the text sent after **every slash command** (prefix commands like `.synccommands` cannot be overridden). Use `/theme responses upload` with a JSON file.

### Commands

| Command | Description |
|--------|-------------|
| `/theme responses list` | List configured overrides for this server |
| `/theme responses discover` | List all slash commands you can override |
| `/theme responses keys` | List common keys and JSON format |
| `/theme responses upload` | Upload overrides JSON (supporters only) |
| `/theme responses clear` | Clear all overrides (supporters only) |

### JSON Format

```json
{
  "overrides": {
    "xpset": {
      "success": "✅ Set {user}'s XP to {xp} and Level to {level}."
    },
    "levelcard_customize": {
      "success": "✅ Level card updated: {preview}"
    },
    "levelreward_add": {
      "success": "✅ Added reward for level **{level}** -> {role}"
    },
    "ban": {
      "success": "🔨 {member} has been banned for {duration} minutes. Reason: {reason}",
      "success_permanent": "🔨 {member} has been permanently banned. Reason: {reason}"
    },
    "unban": {
      "success": "✅ Successfully unbanned {user}."
    },
    "ticket_setup": {
      "success": "✅ Ticket system set up!"
    },
    "ticket_create": {
      "success": "✅ Ticket created: {channel}"
    }
  }
}
```

Max 100KB per file. Values support `{placeholder}` substitution.

### Command Names

Command names use the slash path with spaces replaced by underscores: `level xpset` → `level_xpset`, `muterole create` → `muterole_create`. Run `/theme responses discover` to list all overrideable commands.

### Common Keys and Examples

| Command | Key | Placeholders |
|---------|-----|--------------|
| `ban` | `success`, `success_permanent` | `member`, `duration`, `reason` |
| `unban` | `success` | `user` |
| `giverole` | `success` | `role`, `member` |
| `mute` | `success` | `member`, `duration`, `unit`, `reason` |
| `unmute` | `success` | `member` |
| `level_xpset` | `success` | `user`, `xp`, `level` |
| `levelcard_customize` | `success` | `preview` |
| `levelreward_add` | `success` | `level`, `role` |
| `ticket_setup` | `success` | — |
| `ticket_create` | `success` | `channel` |

Prefix commands (`.synccommands`, `.help`, etc.) are **not** overrideable.

---

## Supporter Requirements

- **Custom themes** (`/theme upload`, `/theme delete`) require Ko-fi supporter status
- **Command response overrides** (`/theme responses upload`, `/theme responses clear`) require Ko-fi supporter status
- Link your Ko-fi via `/kofi link` to get perks
