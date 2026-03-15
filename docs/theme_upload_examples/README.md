# Theme Upload Test Files (Supporters Only)

Use these JSON files to test the supporter theme upload features.

## 1. Moderation Theme (`/theme upload`)

**File:** `star_trek_moderation_theme.json`

- Styles the **DM embeds** sent when users are banned, kicked, timed out, or warned
- **How to test:** Upload via `/theme upload` (attach the file), then run `/theme set star_trek_moderation_theme`
- **Requires:** Ko-fi supporter status + Manage Server permission

## 2. Command Response Overrides (`/theme responses upload`)

**File:** `star_trek_command_responses.json`

- Overrides the **channel success messages** for commands (ban, unban, mute, 8ball, etc.)
- **How to test:** Upload via `/theme responses upload` (attach the file)
- **Requires:** Ko-fi supporter status + Manage Server permission

## Notes

- Both uploads require your Discord account to be linked as a Ko-fi supporter
- Use `/kofi link` if you haven't linked yet
- Moderation theme: max 50KB, must have `actions` with ban/kick/timeout/warn
- Command responses: max 100KB, must have `overrides` object
