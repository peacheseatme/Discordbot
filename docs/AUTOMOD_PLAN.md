# Automod Rewrite Plan for Coffeecord

> **Target audience:** GPT 5.3 Codex or equivalent AI agent.
> **Goal:** Rewrite `Modules/automod.py` from scratch so that it is easy to use,
> intuitive for server admins, has advanced features, and stays within Discord's
> 100 global slash-command limit.

---

## 1. Critical Constraint: The 100-Command Limit

Discord allows a maximum of **100 global slash commands** per bot.
The current command inventory is:

| Source | File | Count |
|---|---|---|
| Core bot | `Main/Bot.py` | 63 |
| Tickets | `Modules/tickets.py` | 3 |
| **Automod** | **`Modules/automod.py`** | **none yet** |
| **Total** | | **98** |

The old automod design registered each sub-feature as a separate top-level
`@tree.command`. That approach is **not scalable**. The rewrite **must use
`app_commands.Group`** to nest automod commands under a single `/automod`
parent, consuming only **1** top-level slot instead of 32.

### How `app_commands.Group` works

```python
from discord import app_commands

# This counts as 1 top-level command no matter how many subcommands it has.
# Discord supports up to 25 subcommands per group, and groups can have
# sub-groups (max depth = 2, i.e. /automod rule spam).
automod_group = app_commands.Group(
    name="automod",
    description="Automod configuration",
    default_permissions=discord.Permissions(manage_guild=True),
    guild_only=True,
)

# Subcommand: /automod overview
@automod_group.command(name="overview", description="View automod status")
async def overview(interaction: discord.Interaction):
    ...

# Sub-group: /automod rule <subcommand>
rule_group = app_commands.Group(
    name="rule",
    description="Configure automod rules",
    parent=automod_group,
)

# Subcommand: /automod rule spam
@rule_group.command(name="spam", description="Configure spam rule")
async def rule_spam(interaction: discord.Interaction, ...):
    ...

# Register the top-level group on the tree (1 slot)
tree.add_command(automod_group)
```

### Required command layout (25-subcommand limit per group)

```
/automod                          <-- 1 top-level slot
  overview                        <-- show dashboard embed
  toggle          enabled:bool    <-- enable/disable automod
  log             channel:TextChannel|None
  reload
  rule            <sub-group, max 25 subcommands>
    spam          max_messages:int? per_seconds:int? timeout_seconds:int?
                  action:Choice? delete_message:bool? enabled:bool?
    caps          min_length:int? caps_percent:int? action:Choice?
                  delete_message:bool? enabled:bool?
    mentions      max_mentions:int? action:Choice? delete_message:bool?
                  enabled:bool?
    links         block_invites:bool? action:Choice? delete_message:bool?
                  enabled:bool?
    attachments   max_attachments:int? max_embeds:int? action:Choice?
                  delete_message:bool? enabled:bool?
    duplicates    window_seconds:int? min_duplicates:int? action:Choice?
                  delete_message:bool? enabled:bool?
    newuser       max_account_age_days:int? action:Choice? delete_message:bool?
                  enabled:bool?
    raid          window_seconds:int? join_threshold:int? cooldown_seconds:int?
                  timeout_seconds:int? action:Choice? enabled:bool?
    selfbot       action:Choice? enabled:bool?
    regex         (show/edit custom regex rules -- respond with embed)
  warn            <sub-group>
    add           member:Member reason:str
    remove        member:Member index:int?
    clear         member:Member
    list          member:Member page:int?
    threshold_set count:int action:Choice timeout_seconds:int?
    threshold_rm  count:int
    thresholds    (list all thresholds)
  list            <sub-group>
    badwords
    domains
    invites
    whitelist
  add             <sub-group>
    badword       word:str
    domain        domain:str
    invite        code:str
    whitelist_ch  channel:TextChannel
    whitelist_role role:Role
  remove          <sub-group>
    badword       word:str
    domain        domain:str
    invite        code:str
    whitelist_ch  channel:TextChannel
    whitelist_role role:Role
  override        <sub-group>
    set           channel:TextChannel rule:Choice setting:str value:str
    clear         channel:TextChannel rule:Choice
```

**Important:** Discord limits nesting to 2 levels. A sub-group counts as level 1,
its commands as level 2. You cannot nest a group inside a sub-group.
The layout above respects this: `/automod` -> `rule` (sub-group) -> `spam` (command).

---

## 2. Project Structure

```
Coffeecord/
  Main/
    Bot.py                          # Main bot script; defines `bot` and `tree`
  Modules/
    automod.py                      # THIS FILE IS WHAT YOU REWRITE
    tickets.py                      # Untouched
  Storage/
    Config/
      automod.json                  # Per-guild config (keep schema, see below)
    Data/
      warns.json                    # Per-guild warn data
      automod_strikes.json          # Per-guild per-rule strike counters
  docs/
    AUTOMOD_PLAN.md                 # This file
```

### How `automod.py` connects to `Bot.py`

`Bot.py` does:
```python
import automod  # at module level, after bot/tree are defined
```

`automod.py` grabs `bot` and `tree` from `__main__`:
```python
import sys
_main = sys.modules.get("__main__")
bot = _main.bot
tree = _main.tree
```

Then at the bottom of `automod.py`, you call:
```python
tree.add_command(automod_group)
```

`Bot.py` hooks automod into two events:
```python
# In on_message:
if await automod.process_automod(message):
    return

# In on_member_join:
await automod.process_member_join(member)
```

**Do NOT change Bot.py.** Keep the same two public functions:
- `async def process_automod(message: discord.Message) -> bool`
- `async def process_member_join(member: discord.Member)`

---

## 3. Config Schema (`Storage/Config/automod.json`)

The file uses a `"default"` key for fallback values and guild-ID keys for
per-guild overrides. When reading config for guild `12345`, merge
`config["default"]` with `config.get("12345", {})` (guild wins).

**Keep the existing schema exactly.** Here is the full default block with types
and descriptions for every field:

```jsonc
{
  "default": {
    "enabled": false,              // bool: master switch
    "log_channel_id": null,        // int|null: channel ID for mod-log embeds
    "whitelist": {
      "roles": [],                 // list[int]: role IDs exempt from automod
      "channels": []               // list[int]: channel IDs exempt from automod
    },
    "protected_roles": [],         // list[int]: role IDs that can never be actioned
    "channel_overrides": {
      // "<channel_id>": { "<rule_name>": { ...partial rule config... } }
    },

    // ── Per-rule blocks ──────────────────────────────────────────────
    "bad_words": {
      "enabled": true,             // bool
      "words": [],                 // list[str]: lowercased blocked words/phrases
      "action": "warn",            // str: delete|warn|timeout|kick|ban|log_only
      "delete_message": true,      // bool: also delete the triggering message
      "escalation": []             // list (reserved, keep empty)
    },
    "spam": {
      "enabled": true,
      "max_messages": 5,           // int: messages allowed in window
      "per_seconds": 6,            // int: window size in seconds
      "action": "timeout",
      "timeout_seconds": 60,       // int: timeout duration (used when action=timeout)
      "escalation": []
    },
    "duplicate_messages": {
      "enabled": false,
      "window_seconds": 30,        // int: lookback window
      "min_duplicates": 3,         // int: how many identical msgs before trigger
      "action": "delete",
      "escalation": []
    },
    "links": {
      "enabled": true,
      "block_invites": true,       // bool: block discord.gg / discord.com/invite
      "allowed_domains": [],       // list[str]: e.g. ["youtube.com","github.com"]
      "allowed_invite_codes": [],  // list[str]: e.g. ["abc123"]
      "action": "delete",
      "escalation": []
    },
    "mentions": {
      "enabled": true,
      "max_mentions": 5,           // int: unique @user/@role mentions per message
      "action": "warn",
      "escalation": []
    },
    "caps": {
      "enabled": true,
      "min_length": 10,            // int: ignore messages shorter than this
      "caps_percent": 70,          // int (0-100): uppercase % to trigger
      "action": "delete",
      "escalation": []
    },
    "attachments": {
      "enabled": false,
      "max_attachments": 6,        // int
      "max_embeds": 3,             // int
      "action": "delete",
      "escalation": []
    },
    "custom_regex": {
      "enabled": false,
      "rules": [],                 // list[{"pattern":str,"action":str,"name":str}]
      "escalation": []
    },
    "anti_selfbot": {
      "enabled": false,
      "action": "delete",
      "use_builtin_patterns": true,
      "builtin_patterns": [        // list[str]: regex strings for token detection
        "[MN][A-Za-z\\d]{23}\\.[\\w-]{6}\\.[\\w-]{27}",
        "mfa\\.[\\w-]{60,}",
        "(?:discord|bot).{0,20}(?:token|auth)"
      ],
      "extra_patterns": [],
      "escalation": []
    },
    "new_user": {
      "enabled": false,
      "max_account_age_days": 7,   // int
      "action": "warn",
      "channels_only": [],         // list[int]: only check these channels (empty=all)
      "escalation": []
    },
    "anti_raid": {
      "enabled": false,
      "window_seconds": 10,        // int: detection window
      "join_threshold": 10,        // int: joins in window to trigger raid mode
      "cooldown_seconds": 60,      // int: how long raid mode lasts
      "action": "timeout",         // action applied to new joins during raid mode
      "timeout_seconds": 300       // int: timeout duration during raid mode
    },
    "warn_thresholds": {
      // "<count>": {"action": str, "seconds": int (optional)}
      "3": {"action": "timeout", "seconds": 300},
      "5": {"action": "kick"}
    }
  }
}
```

### Per-guild override example

```json
{
  "default": { ... },
  "1384771470860746753": {
    "enabled": true,
    "log_channel_id": 1388577818752974970,
    "bad_words": {
      "enabled": true,
      "words": ["lol"]
    }
  }
}
```

Only the keys present in the guild block override the default. Use a recursive
dict merge: `merged = {**default}; deep_update(merged, guild_override)`.

---

## 4. Warn System Design

### Data format (`Storage/Data/warns.json`)

```json
{
  "<guild_id>": {
    "<user_id>": [
      {
        "reason": "Excessive caps",
        "timestamp": 1718900000,
        "by": "Automod"
      },
      {
        "reason": "Spam detected",
        "timestamp": 1718901234,
        "by": "Manual (AdminName)"
      }
    ]
  }
}
```

### `add_warn(guild_id, user_id, reason, by="Automod") -> int`

Appends a warn entry and returns the new total count.
After adding, check `warn_thresholds` and apply the matching action if count
hits a threshold (e.g. at 3 warns -> timeout, at 5 -> kick).

### Warn threshold escalation

When `add_warn` returns count `N`, look up `warn_thresholds[str(N)]`.
If it exists, apply its action to the member:
- `"timeout"` -> `member.timeout(seconds)`
- `"kick"` -> `member.kick()`
- `"ban"` -> `member.ban()`
- anything else -> log only

This applies both to automod-generated warns AND manual `/automod warn add`.

### Warn embeds

When displaying warns (`/automod warn list`):
- Show **10 per page**
- Each entry: `#<index> <timestamp:f> by **<by>**\n<reason>`
- Embed thumbnail = member's avatar
- Footer = `Total warns: N | Page X/Y`
- If >10 warns, send multiple embeds (one per page) via `followup.send`

---

## 5. Message Processing Pipeline

`process_automod(message)` runs these checks **in order** and stops at the first match:

1. Skip if `message.guild` is None or `message.author.bot`
2. Load `guild_cfg = get_guild_config(message.guild.id)`
3. Skip if `guild_cfg["enabled"]` is False
4. Skip if author's channel or roles are whitelisted
5. Skip if author has a protected role
6. For each rule in order:
   `bad_words, spam, duplicate_messages, links, mentions, caps, attachments,
   custom_regex, anti_selfbot, new_user`
   - Resolve rule config with channel overrides
   - Skip if rule is not enabled
   - Run the check function
   - If triggered: apply action, log, return `True`
7. Return `False`

### Check functions

Each check function has the signature:
```python
def check_<rule>(message: discord.Message, cfg: dict) -> AutomodResult | None
```

`AutomodResult` is a dataclass:
```python
@dataclasses.dataclass
class AutomodResult:
    rule: str           # e.g. "spam"
    action: str         # e.g. "timeout"
    reason: str         # human-readable explanation
    extra: dict = {}    # optional: {"seconds": 60, "delete_message": True}
```

### `apply_action(message, result, guild_cfg, rule_cfg)`

Actions:
| Action | Behavior |
|---|---|
| `delete` | Delete the message |
| `warn` | Delete if `delete_message` is set; add warn; check escalation |
| `timeout` | Timeout member for `result.extra["seconds"]` (default 60); optionally delete |
| `kick` | Kick member |
| `ban` | Ban member (delete_message_days=0) |
| `log_only` | Only send a mod-log embed |

Always check permissions before acting (`can_perform_action`).
Always send a mod-log embed after acting.

---

## 6. Anti-Raid (`process_member_join`)

Tracks join timestamps per guild in an in-memory dict.

```python
join_tracker: dict[int, list[float]] = defaultdict(list)  # guild_id -> [timestamps]
raid_mode_until: dict[int, float] = defaultdict(float)    # guild_id -> expiry time
```

Logic:
1. Skip if `anti_raid` not enabled
2. `now = time.time()`
3. If `now < raid_mode_until[guild_id]`: we are in raid mode -> apply action to member
4. Else: prune `join_tracker[guild_id]` to keep only last `window_seconds`
5. Append `now`
6. If `len(join_tracker[guild_id]) >= join_threshold`:
   - Set `raid_mode_until[guild_id] = now + cooldown_seconds`
   - Apply action to the joining member

---

## 7. Slash Command UX Design

### Design principles

- **All responses use embeds** (never plain text for config commands)
- **Color coding:** green = enabled/success, red = disabled/error, blurple = info
- **Every config command responds with the full updated rule config** so the admin
  immediately sees the current state
- **All parameters are optional** (except where noted). If no parameters are
  passed, the command shows the current config without changing anything.
- **`enabled:bool` is a parameter on every rule command** so admins can toggle
  a rule and configure it in one command

### Action Choice parameter

Reuse this everywhere an `action` parameter is needed:
```python
ACTION_CHOICES = [
    app_commands.Choice(name="Delete", value="delete"),
    app_commands.Choice(name="Warn", value="warn"),
    app_commands.Choice(name="Timeout", value="timeout"),
    app_commands.Choice(name="Kick", value="kick"),
    app_commands.Choice(name="Ban", value="ban"),
    app_commands.Choice(name="Log Only", value="log_only"),
]
```

### Rule Choice parameter (for override commands)

```python
RULE_CHOICES = [
    app_commands.Choice(name="Bad Words", value="bad_words"),
    app_commands.Choice(name="Spam", value="spam"),
    app_commands.Choice(name="Duplicate Messages", value="duplicate_messages"),
    app_commands.Choice(name="Links", value="links"),
    app_commands.Choice(name="Mentions", value="mentions"),
    app_commands.Choice(name="Caps", value="caps"),
    app_commands.Choice(name="Attachments", value="attachments"),
    app_commands.Choice(name="Custom Regex", value="custom_regex"),
    app_commands.Choice(name="Anti Selfbot", value="anti_selfbot"),
    app_commands.Choice(name="New User", value="new_user"),
    app_commands.Choice(name="Anti Raid", value="anti_raid"),
]
```

### `/automod overview` embed layout

```
Title: "Automod Overview"
Color: green if enabled, red if disabled
Fields:
  Status: ON/OFF (inline)
  Log Channel: #channel or "Not set" (inline)
  -- then one field per rule (inline=False): --
  Spam: ON | action=timeout | 5 msgs / 6s
  Caps: ON | action=delete  | 70% @ len>=10
  Links: ON | action=delete  | invites=ON domains=2
  ... etc for all 11 rules ...
```

### `/automod rule spam` response embed

```
Title: "Automod: Spam"
Color: green/red based on enabled
Fields:
  enabled: Yes (inline)
  action: timeout (inline)
  delete_message: No (inline)
  max_messages: 5 (inline)
  per_seconds: 6 (inline)
  timeout_seconds: 60 (inline)
```

---

## 8. Full Command Reference

Below is every subcommand with exact parameter names, types, and descriptions.
"?" after a type means optional (default = current config value, no change).

### Top-level subcommands

| Command | Parameters | Description |
|---|---|---|
| `/automod overview` | (none) | Show dashboard embed with all rules |
| `/automod toggle` | `enabled:bool` | Enable/disable automod globally |
| `/automod log` | `channel:TextChannel?` | Set log channel (omit to clear) |
| `/automod reload` | (none) | Reload config from disk |

### `/automod rule` sub-group

| Command | Parameters | Description |
|---|---|---|
| `spam` | `max_messages:int?` `per_seconds:int?` `timeout_seconds:int?` `action:Choice?` `delete_message:bool?` `enabled:bool?` | Configure spam rule |
| `caps` | `min_length:int?` `caps_percent:int?` `action:Choice?` `delete_message:bool?` `enabled:bool?` | Configure caps rule |
| `mentions` | `max_mentions:int?` `action:Choice?` `delete_message:bool?` `enabled:bool?` | Configure mentions rule |
| `links` | `block_invites:bool?` `action:Choice?` `delete_message:bool?` `enabled:bool?` | Configure links rule |
| `attachments` | `max_attachments:int?` `max_embeds:int?` `action:Choice?` `delete_message:bool?` `enabled:bool?` | Configure attachments rule |
| `duplicates` | `window_seconds:int?` `min_duplicates:int?` `action:Choice?` `delete_message:bool?` `enabled:bool?` | Configure duplicate messages rule |
| `newuser` | `max_account_age_days:int?` `action:Choice?` `delete_message:bool?` `enabled:bool?` | Configure new-user rule |
| `raid` | `window_seconds:int?` `join_threshold:int?` `cooldown_seconds:int?` `timeout_seconds:int?` `action:Choice?` `enabled:bool?` | Configure anti-raid rule |
| `selfbot` | `action:Choice?` `enabled:bool?` | Configure anti-selfbot rule |
| `regex` | (none) | Show custom regex rules (edit via JSON config) |

### `/automod warn` sub-group

| Command | Parameters | Description |
|---|---|---|
| `add` | `member:Member` `reason:str` | Manually warn a user (triggers escalation) |
| `remove` | `member:Member` `index:int?` | Remove warn by 1-based index (default: latest) |
| `clear` | `member:Member` | Clear all warns for a user |
| `list` | `member:Member` `page:int?` | Show warns with pagination (10/page) |
| `threshold_set` | `count:int` `action:Choice` `timeout_seconds:int?` | Set escalation at N warns |
| `threshold_rm` | `count:int` | Remove an escalation threshold |
| `thresholds` | (none) | List all warn thresholds |

### `/automod list` sub-group

| Command | Parameters | Description |
|---|---|---|
| `badwords` | (none) | List all blocked words |
| `domains` | (none) | List all allowed domains |
| `invites` | (none) | List all allowed invite codes |
| `whitelist` | (none) | List whitelisted channels and roles |

### `/automod add` sub-group

| Command | Parameters | Description |
|---|---|---|
| `badword` | `word:str` | Add a blocked word (lowercased) |
| `domain` | `domain:str` | Add an allowed domain (e.g. youtube.com) |
| `invite` | `code:str` | Allow a Discord invite code |
| `whitelist_ch` | `channel:TextChannel` | Whitelist a channel from automod |
| `whitelist_role` | `role:Role` | Whitelist a role from automod |

### `/automod remove` sub-group

| Command | Parameters | Description |
|---|---|---|
| `badword` | `word:str` | Remove a blocked word |
| `domain` | `domain:str` | Remove an allowed domain |
| `invite` | `code:str` | Remove an allowed invite code |
| `whitelist_ch` | `channel:TextChannel` | Remove a channel from whitelist |
| `whitelist_role` | `role:Role` | Remove a role from whitelist |

### `/automod override` sub-group

| Command | Parameters | Description |
|---|---|---|
| `set` | `channel:TextChannel` `rule:Choice` `setting:str` `value:str` | Set a per-channel rule override |
| `clear` | `channel:TextChannel` `rule:Choice` | Clear a per-channel override |

---

## 9. Implementation Checklist

Complete these in order. Each step should leave the bot in a runnable state.

### Step 1: Scaffold and groups
- [ ] Delete all existing code in `Modules/automod.py`
- [ ] Re-import `bot` and `tree` from `__main__`
- [ ] Define `automod_group = app_commands.Group(...)` with sub-groups:
      `rule_group`, `warn_group`, `list_group`, `add_group`, `remove_group`, `override_group`
- [ ] Register `tree.add_command(automod_group)` at bottom of file
- [ ] Implement `process_automod` and `process_member_join` as no-op stubs returning `False`
- [ ] Verify bot starts with `python3 -m py_compile Modules/automod.py`

### Step 2: Config layer
- [ ] Define `DEFAULT_GUILD_CONFIG` dict matching schema above
- [ ] Implement `load_json`, `save_json`, `normalize_config`
- [ ] Implement `get_guild_config(guild_id) -> dict` (merge default + guild override)
- [ ] Implement `get_rule_config(guild_cfg, rule_name, channel_id) -> dict`
- [ ] Implement `update_guild_override(guild_id) -> dict`
- [ ] Implement `_save_config()`

### Step 3: Check functions
- [ ] Implement `AutomodResult` dataclass
- [ ] Implement all check functions (see section 5)
- [ ] Implement spam tracker (in-memory `defaultdict(list)` of message timestamps)
- [ ] Implement duplicate tracker (in-memory `defaultdict(list)` of `(content_hash, timestamp)`)

### Step 4: Action system
- [ ] Implement `can_perform_action(guild, member, action) -> (bool, str)`
- [ ] Implement `apply_action(message, result, guild_cfg, rule_cfg)`
- [ ] Implement `add_warn(guild_id, user_id, reason, by) -> int`
- [ ] Implement warn threshold escalation

### Step 5: Mod-log
- [ ] Implement `send_modlog_embed(guild, guild_cfg, embed)`
- [ ] Implement `log_message_action(message, guild_cfg, result, action_taken)`
- [ ] Implement `log_member_action(guild, member, guild_cfg, reason, action_taken)`

### Step 6: `process_automod` and `process_member_join`
- [ ] Wire up the full message processing pipeline (section 5)
- [ ] Wire up anti-raid join tracking (section 6)

### Step 7: Slash commands
- [ ] Implement all commands listed in section 8
- [ ] Every command response must use embeds (section 7)
- [ ] Verify total command count: should be `63 (Bot.py) + 3 (tickets) + 1 (automod group) = 67`

### Step 8: Validation
- [ ] `python3 -m py_compile Modules/automod.py` passes
- [ ] Bot starts without `CommandLimitReached`
- [ ] `/automod overview` responds correctly
- [ ] `/automod rule spam max_messages:3` updates config and responds with embed
- [ ] `/automod warn add @user "test"` adds warn and shows embed
- [ ] `process_automod` catches a test bad word and deletes + warns

---

## 10. Things NOT to Do

- **Do NOT modify `Main/Bot.py`** -- the `import automod`, `process_automod`, and
  `process_member_join` hooks must remain unchanged.
- **Do NOT modify `automod.json` schema** -- only add new keys if absolutely needed;
  never rename or remove existing keys.
- **Do NOT use `@tree.command()`** -- use `@automod_group.command()` or
  `@<sub_group>.command()` so everything nests under `/automod`.
- **Do NOT create more than 1 top-level command** -- the whole point is to stay
  under Discord's 100-command limit.
- **Do NOT use plain text responses** for config commands -- always use embeds.
- **Do NOT break the `process_automod(message) -> bool` contract** -- it must
  return `True` if a rule matched and action was taken, `False` otherwise.
