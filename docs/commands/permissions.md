# Command Permissions

Required permissions for Coffeecord commands and features.

## Bot permissions

The bot must have these permissions in your server to use the listed features:

| Permission | Used by |
|------------|---------|
| **Manage Channels** | `/call create`, `/call join`, `/call add`, `/call remove`, `/call end`, adaptive slowmode, ticket export/import |
| **Manage Roles** | Mute, unmute, giverole, removerole, muterole, autorole |
| **Move Members** | `/call remove` (kick user from VC) |
| **Manage Messages** | Purge, specific_purge |
| **Ban Members** | Ban, unban |
| **Send Messages** | All commands that reply in channels |
| **Embed Links** | Embeds (help, level cards, etc.) |
| **Attach Files** | Level cards, ticket export |
| **Read Message History** | Purge, message processing |
| **Use Slash Commands** | Required for slash commands |

**Tip:** Use the bot's invite link when adding it to your server. It requests the correct permissions. If you get "Forbidden: missing permission" on a command, ensure the bot has the permission listed above for that feature.

## Call feature: "Forbidden: missing permission"

If `/call create` fails with "Forbidden: missing permission":

1. **Bot needs Manage Channels** — The bot creates a temporary voice channel. Ensure the bot has **Manage Channels** permission in the server (or Administrator).
2. **User needs Manage Channels** — The invoker must have **Manage Channels** (or Administrator) to use `/call create`.

Server admins: grant the bot role **Manage Channels** in Server Settings → Roles → [Bot Role] → Permissions.

### Call behavior

- **Auto-delete:** If a call channel is empty for 15 seconds, it is automatically deleted.
- **Join enforcement:** Users must use `/call join` (with the correct password if set) to join. Anyone who tries to connect directly without using the command is kicked and DMed instructions.

## User permissions by command

| Command | User permission |
|---------|------------------|
| **Ko-fi** | |
| `/kofi add`, `/kofi remove` | Administrator |
| **Moderation** | |
| `/ban`, `/unban` | Ban Members |
| `/giverole`, `/removerole` | Manage Roles OR Moderate Members OR Manage Server |
| `/mute`, `/unmute`, `/hardmute` | Manage Roles OR Moderate Members OR Manage Server |
| `/muterole create`, `/muterole update` | Manage Roles OR Moderate Members OR Manage Server |
| `/purge`, `/specific_purge` | Manage Messages |
| **General** | |
| `/say` | Manage Server |
| `/dm` | Moderate Members |
| `/verifyconfig` | Manage Server |
| `/nickname` | Manage Nicknames |
| **Staff applications** | |
| `/application addquestion`, `remove`, `list`, `setpass` | Manage Server |
| **Calls** | |
| `/call create` | Manage Channels |
| `/call join`, `/call add`, `/call remove`, `/call end`, `/call promote` | None (host-only or invitee) |
| **Other** | |
| `/adaptive_slowmode` | Manage Channels |
| `/debugcommands` | Manage Server |
| `/uninstall` | Administrator |
| `/ticket setup` | Manage Server |
| `/ticket_export`, `/ticket_import` | Manage Channels |
| **Modules** | |
| `/modules status`, `toggle`, `enable`, `disable`, `info` | Manage Server |
| **Logging** | |
| `/logging status`, `setup`, `toggle`, `module`, `disable` | Manage Server |
| **Autorole** | |
| `/autorole status`, `toggle`, `add`, `remove`, `test` | Manage Server |
| **Reaction roles** | |
| `/reactionrole create`, `list`, `delete`, `config`, `edit` | Manage Server |
| **Welcome & Leave** | |
| `/welcome config`, `test` | Manage Server |
| `/leave config`, `test` | Manage Server |
| **Leveling** | |
| `/xpset`, `/xp config` | Manage Server |
| `/levelreward add`, `remove`, `mode` | Manage Roles OR Moderate Members OR Manage Server |
| **Themes** | |
| `/theme list`, `set`, `preview`, `info`, `upload`, `delete` | Manage Server |
| `/theme responses preset`, `list`, `upload`, `discover`, `keys`, `clear` | Manage Server |
| **Setup wizard** | |
| `/setup`, `/setup_resume`, `/setup_cancel` | Manage Server |
| **Translate** | |
| `/translate reset` | Administrator |

## Commands with no permission check

These commands are available to all users (subject to module enable/disable):

- `/help`, `/about`, `/support us`
- `/kofi link`, `/kofi status`, `/kofi claim`
- `/optout`, `/optin`
- `/poll`, `/application`
- `/remindme`, `/starttimer`, `/checktimers`, `/endtimer`
- `/level`, `/levelcard customize`, `/levelcard preset`
- `/call join` (invitee only)
- `/8ball`, `/bet`, `/flipcoin`, `/hug`, `/kiss`, `/petpet`, `/dog`, `/cat`, etc.
- `/automod overview`, `status` (read-only)
- `/translate text`, `/translate settings`, `/translate usage`
