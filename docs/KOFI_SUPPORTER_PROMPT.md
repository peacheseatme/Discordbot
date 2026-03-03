# Prompt: Migrate Coffeecord Supporter System to Ko-fi API + Persistent Database

## Context

Coffeecord is a discord.py (v2) bot. The main bot file is `Main/Bot.py`.
The project root is `/home/gavin/Downloads/Coffeecord/`.

### Current supporter system (what to REMOVE/REPLACE)

Supporter status is currently checked by looking for a specific Discord role on the
user in the bot's home guild (the "Galaxy Bot" server, `GALAXY_BOT_SERVER_ID =
1384771470860746753`). The role ID is:

```python
SUPPORTER_ROLE_ID = 1386795218195578930   # line 1768
```

Every supporter-gated feature currently runs a check like:

```python
supporter = any(r.id == SUPPORTER_ROLE_ID for r in interaction.user.roles)
```

There are exactly **two places** in `Main/Bot.py` that do this:

1. `/levelbackground` command (line 1804) — GIF backgrounds gated by supporter status.
2. `/level` command (line 1837) — GIF animated level card rendering also uses the flag.

A file constant `SUPPORTERS_FILE = "supporters.json"` (line 96) already exists
but is currently unused.

---

## Goal

Replace the role-check with a **Ko-fi webhook + persistent JSON database** system.
When someone donates or subscribes on Ko-fi, Ko-fi sends an HTTPS POST webhook to
a URL you configure. Parse that payload, identify the donor's Discord user ID, and
store them permanently in `Storage/Data/supporters.json`.

All existing supporter gates in the bot must then query this JSON file instead of
checking Discord roles.

---

## Required Implementation

### 1. Ko-fi Webhook Receiver (`Modules/kofi_webhook.py`)

Create a new file `Modules/kofi_webhook.py` that runs an `aiohttp.web` server
alongside the Discord bot.

**Webhook endpoint:** `POST /kofi-webhook`

Ko-fi sends webhook payloads as a form-encoded body with a single field `data`
whose value is a JSON string. Parse it like this:

```python
form = await request.post()
payload = json.loads(form["data"])
```

**Ko-fi payload structure** (relevant fields):

```json
{
  "verification_token": "YOUR_TOKEN_HERE",
  "type": "Donation" | "Subscription" | "Shop Order",
  "from_name": "display name on Ko-fi",
  "email": "donor@example.com",
  "amount": "5.00",
  "currency": "USD",
  "is_subscription_payment": true | false,
  "is_first_subscription_payment": true | false,
  "kofi_transaction_id": "uuid string",
  "message": "optional message from donor",
  "timestamp": "ISO 8601 datetime string"
}
```

Ko-fi does **not** send the Discord user ID in the webhook. To link a Ko-fi
donation to a Discord account, implement the following **two-step link flow**:

#### Link Flow

1. A Discord user runs `/kofi link <email>` where `<email>` is the email address
   they used on Ko-fi.
2. The bot records a **pending link** in memory:
   `pending_links: dict[str, int] = {}  # email.lower() -> discord_user_id`
3. When a webhook arrives with a matching `email`, the bot resolves the
   `discord_user_id`, writes the supporter record to `supporters.json`, and
   DMs the user a confirmation.
4. If no pending link is found for an email, store the donation in an
   **unlinked queue** (`unlinked_donations` list in the JSON) so it can be
   claimed later via `/kofi claim <email>`.

#### Verification

Verify every incoming webhook using a secret token set in `.env`:

```
KOFI_VERIFICATION_TOKEN=your_token_here
```

Reject (return HTTP 403) any request where `payload["verification_token"]` does
not match the env var. Log a warning to the console on mismatch.

#### Server

Run the aiohttp web server on port `5000` (configurable via env var
`KOFI_PORT`, default `5000`). Start it as an `asyncio` task alongside the
Discord bot's `bot.start()` call in `Main/Bot.py`'s `if __name__ == "__main__":`
block.

---

### 2. Supporter Database (`Storage/Data/supporters.json`)

Use the existing constant:

```python
SUPPORTERS_FILE = "supporters.json"
```

but point it to the correct path `Storage/Data/supporters.json` (not the root).
Update the constant in `Main/Bot.py` accordingly.

**Schema:**

```json
{
  "supporters": {
    "<discord_user_id_str>": {
      "discord_id": 123456789,
      "email": "donor@example.com",
      "tier": "donation" | "subscription",
      "active": true,
      "first_seen": "2025-01-01T00:00:00",
      "last_payment": "2025-06-01T00:00:00",
      "total_usd": 15.00,
      "kofi_transaction_ids": ["uuid1", "uuid2"]
    }
  },
  "unlinked_donations": [
    {
      "email": "unknown@example.com",
      "amount": "5.00",
      "timestamp": "2025-06-01T00:00:00",
      "kofi_transaction_id": "uuid"
    }
  ]
}
```

`active` should be set to `false` automatically for subscriptions if
`is_subscription_payment` is `true` but the payment is more than 35 days old
(grace period). Re-set to `true` on any new payment.

---

### 3. Helper Function `is_supporter(user_id: int) -> bool`

Add this function to `Main/Bot.py` (near the top, after constants):

```python
def is_supporter(user_id: int) -> bool:
    """Return True if the Discord user has an active supporter record."""
    data = load_json(SUPPORTERS_FILE, {})
    record = data.get("supporters", {}).get(str(user_id))
    if not record:
        return False
    return record.get("active", False)
```

---

### 4. Update All Supporter Gates in `Main/Bot.py`

Replace **every** occurrence of:

```python
supporter = any(r.id == SUPPORTER_ROLE_ID for r in <member>.roles)
```

with:

```python
supporter = is_supporter(<member>.id)
```

There are two locations:

| Line | Command | Variable | Object |
|------|---------|----------|--------|
| 1804 | `/levelbackground` | `supporter` | `interaction.user` |
| 1837 | `/level` | `supporter` | `user` (the target member) |

Do **not** change any other logic in those commands — only replace the supporter
check.

---

### 5. New Slash Commands

Add these slash commands to `Main/Bot.py`:

#### `/kofi link <email>`

- Accessible to all users.
- Records `pending_links[email.lower()] = interaction.user.id`.
- Responds ephemerally: `"✅ Pending — your next Ko-fi donation/subscription from
  <email> will automatically link your Discord account."`
- Also checks the `unlinked_donations` list in `supporters.json`. If a matching
  email is found there, immediately grant supporter status and remove from the
  unlinked queue.

#### `/kofi claim <email>`

- Same as `/kofi link` but explicitly searches unlinked donations first.
- Use this when someone donated before linking.

#### `/kofi status`

- Accessible to all users. Ephemeral.
- Shows the calling user's current supporter record if it exists, or a message
  saying they are not a supporter.
- Fields to display: `active`, `tier`, `last_payment`, `total_usd`.

#### `/kofi add <user> <email>`

- Requires `administrator` permission.
- Manually adds or updates a supporter record.
- Sets `active: true`, `tier: "donation"`, timestamps to now.
- Useful for manual Ko-fi purchases that didn't trigger the webhook.

#### `/kofi remove <user>`

- Requires `administrator` permission.
- Sets `active: false` in the supporter record (does not delete).

---

### 6. `.env` Variables to Add

Document in a comment at the top of `Modules/kofi_webhook.py`:

```
KOFI_VERIFICATION_TOKEN=   # from Ko-fi Settings > API
KOFI_PORT=5000             # port to listen on (optional, defaults to 5000)
```

Load them with `os.getenv(...)` — do not hardcode values.

---

### 7. Dependency

Add `aiohttp` to `requirements.txt` if not already present. It is already used
elsewhere in the bot so it should already be installed.

---

## What NOT to change

- Do not remove `SUPPORTER_ROLE_ID` from the code in case it is needed for
  backwards compatibility — just stop reading it for access control.
- Do not modify `GALAXY_BOT_SERVER_ID` or any guild join/leave logic.
- Do not modify the `/support-us` command or the Ko-fi link button in `DonateView`.
- Do not change how `levelbackground` saves/loads background URLs — only change
  the `supporter` boolean derivation.
- Do not change any ticket, automod, or moderation logic.

---

## File Summary

| File | Action |
|------|--------|
| `Modules/kofi_webhook.py` | **Create** — aiohttp webhook receiver |
| `Storage/Data/supporters.json` | **Create** (empty schema) — persistent supporter DB |
| `Main/Bot.py` | **Modify** — update `SUPPORTERS_FILE` path, add `is_supporter()`, update supporter gates, add `/kofi` command group, start webhook server |
| `requirements.txt` | **Verify** `aiohttp` is listed |
