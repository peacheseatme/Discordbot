# Codex Prompt: Automod Command Merging & Warn System

## Context

You are modifying a Discord bot built with `discord.py` (v2.x+). The bot lives at:

- **Main bot script**: `Main/Bot.py`
- **Automod module**: `Modules/automod.py`
- **Config file**: `Storage/Config/automod.json`
- **Warns data**: `Storage/Data/warns.json`
- **Strikes data**: `Storage/Data/automod_strikes.json`

The automod module is imported from `Bot.py` at import time. It accesses `bot` and `tree` (which is `bot.tree`) from `__main__`:

```python
_main = sys.modules.get("__main__")
bot = _main.bot
tree = _main.tree
```

All automod slash commands must live under a single top-level `app_commands.Group(name="automod")` to stay within Discord's 100 global command limit. The bot currently has ~65 other commands.

Discord limits slash command nesting to **2 levels**: `/automod <subgroup> <command>`.

---

## Task 1: Merge Domain Blocking & Invite Blocking into `/automod rule blocker`

### What to merge

Currently there are two separate blocking concepts stored under the `"links"` config key:
- **Invite blocking**: detects `discord.gg` / `discordapp.com/invite` links
- **Domain blocking**: detects non-whitelisted URLs

These should be exposed through ONE command: `/automod rule blocker`.

### Command signature

```
/automod rule blocker
    enabled: bool | None         — enable/disable the entire blocker rule
    block_invites: bool | None   — toggle invite-link blocking
    block_links: bool | None     — toggle general-link/domain blocking
    action: Choice[str] | None   — action on violation (delete/warn/timeout/kick/ban/log_only)
    delete_message: bool | None  — whether to also delete the offending message
```

All parameters are optional. When `None`, the existing config value is preserved.

### Config key

Both settings live under the same JSON key `"links"`:

```json
"links": {
    "enabled": true,
    "block_invites": true,
    "block_links": true,
    "allowed_domains": [],
    "allowed_invite_codes": [],
    "action": "delete",
    "delete_message": true,
    "escalation": []
}
```

### Supporting list/add/remove commands

These must also exist under the automod group:

| Command | Description |
|---------|-------------|
| `/automod list domains` | Show all whitelisted domains |
| `/automod list invites` | Show all whitelisted invite codes |
| `/automod add domain <domain>` | Add a domain to the whitelist |
| `/automod remove domain <domain>` | Remove a domain from the whitelist |
| `/automod add invite <code>` | Allow a specific Discord invite code |
| `/automod remove invite <code>` | Remove an allowed invite code |

### Response embed

When `/automod rule blocker` is run, respond with an embed titled **"Automod: Blocker"** containing:

| Field | Value |
|-------|-------|
| Enabled | Yes / No |
| Action | (current action) |
| Block Invites | Yes / No |
| Block Links | Yes / No |
| Allowed Domains | (count) |
| Allowed Invites | (count) |

Color: green if enabled, red if disabled.

### Check function

The `check_links(message, cfg)` function handles both:

1. If `block_invites` is true → scan for Discord invite URLs, reject if code not in `allowed_invite_codes`
2. If `block_links` is true → scan for all URLs, reject if domain not in `allowed_domains`
   - Skip Discord's own domains (discord.gg, discord.com, discordapp.com) to avoid double-flagging invites
3. Domain normalization: strip `www.`, lowercase, support subdomain matching (`foo.example.com` matches `example.com`)

---

## Task 2: Warn Management Commands

### Command group

All warn commands live under `/automod warn <command>`.

### Commands

#### `/automod warn add`
```
member: discord.Member  — the user to warn
reason: str             — reason for the warning
```
- Appends a warn entry to `Storage/Data/warns.json`
- Each entry: `{"reason": "...", "timestamp": unix_epoch, "by": "Manual (DisplayName)"}`
- After adding, check warn thresholds for automatic escalation
- Respond with the updated warns embed for that user

#### `/automod warn remove`
```
member: discord.Member     — the user
index: int | None = None   — 1-based warn index to remove (if None, removes the latest)
```
- Removes a specific warn by index, or the most recent if no index given
- Respond with the updated warns embed

#### `/automod warn clear`
```
member: discord.Member  — the user
```
- Removes ALL warns for the given user in the current guild
- Respond with confirmation embed

#### `/automod warn list`
```
member: discord.Member  — the user
page: int = 1           — page number (10 warns per page)
```
- Paginated display of all warns
- Each warn line format: `` `#1` <t:TIMESTAMP:f> by **Issuer** \n Reason text ``
- Footer: `Total warns: X | Page Y/Z`
- Thumbnail: user's avatar

#### `/automod warn threshold_set`
```
count: int                   — number of warns to trigger action
action: Choice[str]          — timeout/kick/ban
seconds: int | None = None   — timeout duration (only for timeout action)
```
- Sets an automatic escalation when a user reaches `count` total warns
- Stored in `warn_thresholds` config key: `{"3": {"action": "timeout", "seconds": 300}}`

#### `/automod warn threshold_rm`
```
count: int  — the threshold count to remove
```
- Removes the escalation entry for that warn count

#### `/automod warn thresholds`
No parameters.
- Lists all configured warn thresholds in an embed

### Warn data format (`Storage/Data/warns.json`)

```json
{
    "GUILD_ID": {
        "USER_ID": [
            {
                "reason": "Spam detected (5/5 in 6s)",
                "timestamp": 1718900000,
                "by": "Automod"
            },
            {
                "reason": "Being rude",
                "timestamp": 1718900500,
                "by": "Manual (AdminName)"
            }
        ]
    }
}
```

### Warn threshold escalation logic

After every warn is added (both manual and automod), call `apply_warn_threshold_action`:

```python
async def apply_warn_threshold_action(member, warn_count, guild_cfg):
    thresholds = guild_cfg.get("warn_thresholds", {})
    action_data = thresholds.get(str(warn_count))
    if not action_data:
        return None
    # Execute: timeout/kick/ban based on action_data
    # Log to mod-log channel
```

---

## Task 3: Anti-Spam Consolidation (already done, verify)

The four anti-spam rules (`spam`, `duplicate_messages`, `caps`, `mentions`) should be configurable through one command:

```
/automod rule antispam
    enabled: bool | None         — toggle all four rules at once
    max_messages: int | None     — spam: max messages in window
    per_seconds: int | None      — spam: window size
    timeout_seconds: int | None  — spam: timeout duration
    min_duplicates: int | None   — duplicates: threshold
    dup_window: int | None       — duplicates: window in seconds
    caps_percent: int | None     — caps: percentage threshold
    caps_min_length: int | None  — caps: minimum message length
    max_mentions: int | None     — mentions: max allowed
    action: Choice[str] | None   — shared action for all four
    delete_message: bool | None  — shared delete setting
```

When `enabled` is set, it applies to ALL four sub-rules. When `action` is set, it applies to all four. Individual numeric parameters only affect their respective rule.

Response: a combined embed showing the status of all four sub-rules.

---

## Existing Command Tree (preserve these)

```
/automod overview           — dashboard showing all rule statuses
/automod toggle             — enable/disable automod globally
/automod log                — set mod-log channel
/automod reload             — reload config from disk

/automod rule set_value     — advanced: set any rule setting by key
/automod rule antispam      — configure spam/duplicates/caps/mentions
/automod rule blocker       — configure invite/domain blocking
/automod rule attachments   — configure attachment limits
/automod rule newuser       — configure new-account restrictions
/automod rule raid          — configure anti-raid
/automod rule selfbot       — configure anti-selfbot
/automod rule regex         — view custom regex rules

/automod warn add           — manually warn a user
/automod warn remove        — remove a warn
/automod warn clear         — clear all warns
/automod warn list          — list warns (paginated)
/automod warn threshold_set — set warn escalation
/automod warn threshold_rm  — remove warn escalation
/automod warn thresholds    — list warn escalations

/automod list badwords      — list blocked words
/automod list domains       — list allowed domains
/automod list invites       — list allowed invite codes
/automod list whitelist     — list whitelisted channels/roles

/automod add badword        — add a blocked word
/automod add domain         — add an allowed domain
/automod add invite         — allow an invite code
/automod add whitelist_ch   — whitelist a channel
/automod add whitelist_role — whitelist a role

/automod remove badword     — remove a blocked word
/automod remove domain      — remove an allowed domain
/automod remove invite      — remove an invite code
/automod remove whitelist_ch   — remove whitelisted channel
/automod remove whitelist_role — remove whitelisted role

/automod override set       — set per-channel rule override
/automod override clear     — clear per-channel override
```

---

## Implementation Requirements

1. **All commands require `Manage Server` permission** — check via `interaction.user.guild_permissions.manage_guild`
2. **All responses are ephemeral** — use `ephemeral=True` on every send
3. **Per-guild config** — every guild has its own config derived from merging `config["default"]` with `config["GUILD_ID"]`
4. **Channel overrides** — individual channels can override any rule setting via `channel_overrides.CHANNEL_ID.RULE_NAME`
5. **Use `app_commands.Group`** — the entire automod is ONE top-level group. Subgroups: `rule`, `warn`, `list`, `add`, `remove`, `override`
6. **Register at module load** — at the bottom of `automod.py`, call `tree.add_command(automod_group)`
7. **Config auto-saves** — after every config change, call `_save_config()` which writes to `Storage/Config/automod.json`
8. **Don't break existing checks** — the `process_automod(message)` function and `process_member_join(member)` hooks in `Bot.py` must continue working unchanged

---

## Files to Modify

| File | What to do |
|------|-----------|
| `Modules/automod.py` | All changes go here. Verify/create the command groups, slash commands, check functions, embed builders, and data helpers described above. |
| `Storage/Config/automod.json` | Will be auto-managed by the code. Default config includes all rule keys. |
| `Storage/Data/warns.json` | Auto-managed. Structure: `{guild_id: {user_id: [warn_entries]}}` |

**Do NOT modify** `Main/Bot.py` — the automod module is already imported there and hooks are in place.

---

## Verification Checklist

- [ ] `/automod rule blocker` merges invite + domain blocking into one command
- [ ] `/automod add domain`, `/automod remove domain`, `/automod list domains` work
- [ ] `/automod add invite`, `/automod remove invite`, `/automod list invites` work
- [ ] `/automod warn add` creates a warn and checks thresholds
- [ ] `/automod warn remove` removes by index or latest
- [ ] `/automod warn clear` wipes all warns for a user
- [ ] `/automod warn list` shows paginated warns with timestamps
- [ ] `/automod warn threshold_set` / `threshold_rm` / `thresholds` manage escalation
- [ ] `/automod rule antispam` configures all four sub-rules simultaneously
- [ ] `/automod overview` shows a dashboard grouping Anti-Spam and Blocker
- [ ] All commands are ephemeral and require Manage Server
- [ ] Total slash command count stays under 100 (automod = 1 top-level group)
- [ ] `process_automod(message)` and `process_member_join(member)` still work
