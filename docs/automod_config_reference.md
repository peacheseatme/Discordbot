# Automod Config Reference

This file documents `Storage/Config/automod.json`.

## Structure

- Root object:
  - `default`: Base config used for every guild.
  - `<guild_id>`: Optional per-guild override object (example: `"1212210181044183171"`).

Guild config is merged as: `default` + `<guild_id>` + optional channel overrides.

## Core Keys

- `enabled` (bool, default: `false`)
  - Enables/disables automod for the guild.
  - Example: `true`

- `log_channel_id` (int|null, default: `null`)
  - Channel ID for automod log embeds.
  - Example: `1386804720953331844`

- `whitelist` (object)
  - `roles` (list[int], default: `[]`) role IDs ignored by automod.
  - `channels` (list[int], default: `[]`) channel IDs ignored by automod.

- `protected_roles` (list[int], default: `[]`)
  - Members with any of these roles are never moderated.

- `channel_overrides` (object, default: `{}`)
  - Per-channel rule overrides.
  - Format:
    - `channel_overrides.<channel_id>.<rule_name>.<setting> = value`
  - Example:
    ```json
    {
      "channel_overrides": {
        "1386804720953331844": {
          "caps": {
            "enabled": true,
            "caps_percent": 60
          }
        }
      }
    }
    ```

## Rule Objects

Each rule usually supports:
- `enabled` (bool)
- `action` (`delete|warn|timeout|kick|ban|log_only`)
- `delete_message` (bool, optional)
- `escalation` (list, optional)

### `bad_words`
- `words` (list[str], default: `[]`)
- `action` (default: `warn`)
- `delete_message` (default: `true`)

### `spam`
- `max_messages` (int, default: `5`)
- `per_seconds` (int, default: `6`)
- `action` (default: `timeout`)
- `timeout_seconds` (int, default: `60`)

### `duplicate_messages`
- `window_seconds` (int, default: `30`)
- `min_duplicates` (int, default: `3`)
- `action` (default: `delete`)

### `links`
- `block_invites` (bool, default: `true`)
- `allowed_domains` (list[str], default: `[]`)
- `allowed_invite_codes` (list[str], default: `[]`)
- `action` (default: `delete`)

### `mentions`
- `max_mentions` (int, default: `5`)
- `action` (default: `warn`)

### `caps`
- `min_length` (int, default: `10`)
- `caps_percent` (float, default: `70`)
- `action` (default: `delete`)

### `attachments`
- `max_attachments` (int, default: `6`)
- `max_embeds` (int, default: `3`)
- `action` (default: `delete`)

### `custom_regex`
- `rules` (list[object], default: `[]`)
  - Rule item:
    - `name` (str)
    - `pattern` (str, regex)
    - `action` (`delete|warn|timeout|kick|ban|log_only`)
- Example:
  ```json
  {
    "custom_regex": {
      "enabled": true,
      "rules": [
        { "name": "Nitro Scam", "pattern": "free\\s+nitro", "action": "delete" }
      ]
    }
  }
  ```

### `anti_selfbot`
- `use_builtin_patterns` (bool, default: `true`)
- `builtin_patterns` (list[str], default: token-leak regex set)
- `extra_patterns` (list[str], default: `[]`)
- `action` (default: `delete`)

### `new_user`
- `max_account_age_days` (int, default: `7`)
- `channels_only` (list[int], default: `[]`)
- `action` (default: `warn`)

### `anti_raid`
- `window_seconds` (int, default: `10`)
- `join_threshold` (int, default: `10`)
- `cooldown_seconds` (int, default: `60`)
- `action` (default: `timeout`)
- `timeout_seconds` (int, default: `300`)

## Escalation and Thresholds

- `warn_thresholds` (object)
  - Key = warn count as string.
  - Value = action object.
  - Example:
    ```json
    {
      "warn_thresholds": {
        "3": { "action": "timeout", "seconds": 300 },
        "5": { "action": "kick" }
      }
    }
    ```

- `escalation` (per rule, list[object])
  - Example:
    ```json
    {
      "spam": {
        "escalation": [
          { "after": 1, "action": "warn" },
          { "after": 2, "action": "timeout", "seconds": 120 }
        ]
      }
    }
    ```

## Runtime Slash Commands (Automod)

- Existing:
  - `/automod`, `/automod_on`, `/automod_off`, `/automod_status`, `/automod_reload`
- Rule and config:
  - `/automod_toggle_rule`
  - `/automod_set_action`
  - `/automod_set_value`
  - `/automod_set_delete_message`
- Bad words:
  - `/automod_badword_add`
  - `/automod_badword_remove`
  - `/automod_badword_list`
- Whitelist/logging:
  - `/automod_set_log`
  - `/automod_whitelist_channel`
  - `/automod_whitelist_role`
- Channel overrides:
  - `/automod_channel_override_set`
  - `/automod_channel_override_clear`
- Warns:
  - `/automod_warns`
