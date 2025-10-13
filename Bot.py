from http import client
import discord
from discord.ext import commands
import logging
from discord.ext import commands, tasks
import os
from dotenv import load_dotenv
import asyncio
from datetime import timedelta
from discord.ext import commands
import sysfile_data
from discord.ui import View, Button
from discord import ButtonStyle
import random
import json
from discord import ButtonStyle, Interaction
from datetime import datetime, timedelta
from discord import app_commands
from discord.ui import Select, View, Button
import io
from discord import File
from PIL import Image, ImageDraw, ImageFont, ImageSequence
from io import BytesIO
import tempfile
from discord import Interaction, SelectOption
import yt_dlp
import hashlib
from datetime import datetime, timedelta

load_dotenv()
token = os.getenv('DISCORD_TOKEN')

# ───────── staff applications – storage helpers ─────────
STAFF_APP_FILE = "staff_applications.json"

def load_json(path: str, default: dict | list):
    """Load JSON or return *default* if file missing / corrupt."""
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default

def save_json(path: str, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

# In‑memory cache of the staff‑application config for *all* guilds
staff_app_cfg: dict[str, dict] = load_json(STAFF_APP_FILE, {})
# ─────────────────────────────────────────────────────────

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.guilds = True
intents.message_content = True
intents.members = True
OWNER_ID = 1168282467162136656

bot = commands.Bot(command_prefix="!", intents=intents)

tree = bot.tree

import sysfile_data

VERIFY_CONFIG_FILE = "verify_config.json"
REACTION_VERIFY_FILE = "reaction_verify_messages.json"

GUILD_IDS = [
    1212210181044183171,  # Replace with your guild IDs
    # Add more guild IDs for testing here
]

logging_enabled = True  # Toggle to enable/disable logs
log_channel_id = None   # Will be set with !log start

authoroles = set()
autorole_config = {}
verify_config = {}
GUILD_ID = 1212210181044183171
CONFIG_FILE = "autorole_config.json"
BOT_OWNER_ID = 1168282467162136656
GALAXY_BOT_SERVER_ID = 1384771470860746753
PERMANENT_INVITE = "https://discord.gg/wpHpe5fwuT"
DONATION_URL = "https://ko-fi.com/coffeecord"
SUPPORTERS_FILE = "supporters.json"

lockdown = False

# Lockdown command logic
import a2s

def get_staff_cfg(guild_id: str) -> dict:
    return staff_app_cfg.setdefault(guild_id, {
        "enabled": False,
        "questions": [],
        "review_channel_id": None,
        "reviewer_role_id": None
    })

DB_FILE = "servers.json"
servers = json.load(open(DB_FILE)) if os.path.exists(DB_FILE) else {}

def save():  # helper to persist to disk
    with open(DB_FILE, "w") as fp:
        json.dump(servers, fp, indent=2)

def split_addr(addr: str):
    """Return (host, port_int).  If :port missing, default 27015."""
    if ":" in addr:
        host, port = addr.rsplit(":", 1)
        return host, int(port)
    return addr, 27015

@tree.command(name="serveradd", description="Track a Steam‑based game server")
@app_commands.describe(
    alias="Nickname you’ll use later (e.g. rust‑main)",
    address="host:gamePort  – e.g. uslong3.rustafied.com:28015",
    game="rust / ark / csgo / tf2 …",
    query_port="OPTIONAL query port (defaults to gamePort)")
async def serveradd(
    inter: discord.Interaction,
    alias: str,
    address: str,
    game: str,
    query_port: int | None = None,
):
    host, game_port = split_addr(address)
    q_port = query_port or game_port            # fallback if not supplied
    servers[alias] = {
        "host": host,
        "game_port": game_port,
        "query_port": q_port,
        "game": game.lower(),
    }
    save()
    await inter.response.send_message(
        f"✅ **{alias}** saved – connect `steam://connect/{host}:{game_port}`",
        ephemeral=True
    )

@tree.command(name="serverstatus", description="Show status for a tracked server")
@app_commands.describe(alias="The nickname you set in /serveradd")
async def serverstatus(inter: discord.Interaction, alias: str):
    if alias not in servers:
        await inter.response.send_message("❌ Server alias not found.", ephemeral=True)
        return

    srv = servers[alias]
    try:
        info = a2s.info((srv["host"], srv["query_port"]))
    except Exception as e:
        await inter.response.send_message(f"⚠️ Query failed: {e}", ephemeral=True)
        return

    embed = discord.Embed(
        title=info.server_name or alias,
        description=(
            f"**Map:** {info.map_name}\n"
            f"**Players:** {info.player_count}/{info.max_players}\n"
            f"**Game:** {srv['game'].title()}"
        ),
        color=discord.Color.blurple(),
    )
    embed.set_thumbnail(url=get_icon(srv["game"]))
    embed.add_field(name="Connect",
                    value=f"`{srv['host']}:{srv['game_port']}`",
                    inline=False)
    embed.set_footer(text=f"Query port: {srv['query_port']}")
    await inter.response.send_message(embed=embed)

def get_icon(game: str) -> str:
    icons = {
        "rust": "https://cdn.cloudflare.steamstatic.com/steam/apps/252490/header.jpg",
        "ark": "https://cdn.cloudflare.steam-static.com/steam/apps/346110/header.jpg",
        "csgo": "https://cdn.cloudflare.steamstatic.com/steam/apps/730/header.jpg",
        "tf2":  "https://cdn.cloudflare.steamstatic.com/steam/apps/440/header.jpg",
    }
    return icons.get(game.lower(),
        "https://store.steampowered.com/public/shared/images/header/globalheader_logo.png")

@bot.event
async def on_interaction(interaction: discord.Interaction):
    global DISABLED

    # Allow bot owner to bypass lockdown
    if interaction.user.id == OWNER_ID:
        return await tree._call(interaction)

    # If lockdown is active, block and auto-delete bot replies
    if DISABLED and interaction.type == discord.InteractionType.application_command:
        try:
            await interaction.response.send_message(
                "🔒 Order 66 is in effect. This bot is under lockdown.",
                ephemeral=True
            )
        except discord.InteractionResponded:
            pass  # already responded, can't respond again

        # Slash commands can't be "deleted", but ephemeral responses disappear on their own
        return

    # Otherwise, process the command normally
    await tree._call(interaction)


async def lockdown_command(interaction: discord.Interaction):
    global lockdown
    lockdown = True
    await interaction.response.send_message("🔒 Lockdown enabled.")

async def unlock_command(interaction: discord.Interaction):
    global lockdown
    lockdown = False
    await interaction.response.send_message("🔓 Lockdown lifted.")

# Order to function map
ORDER_ACTIONS = {
    66: lockdown_command,
    65: unlock_command,
}

# Owner-only check
def is_owner():
    async def predicate(interaction: discord.Interaction) -> bool:
        return interaction.user.id == OWNER_ID
    return app_commands.check(predicate)

# Your executeorder command handler example:
@tree.command(name="executeorder", description="Owner-only emergency command")
@app_commands.describe(order="Order number to execute")
@app_commands.checks.has_role("Owner")  # Or your owner check
async def executeorder(interaction: discord.Interaction, order: int):
    global lockdown
    if order == 66:
        lockdown = True
        await interaction.response.send_message(
            "🔒 Order 66 has been executed, Bot is on Lockdown Till Further Notice."
        )
    elif order == 65:
        lockdown = False
        await interaction.response.send_message("🔓 Lockdown lifted.")
    else:
        await interaction.response.send_message("❌ Unknown order.", ephemeral=True)
        
def command_enable_check(command_name: str, config_db):
    async def predicate(interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)
        user_role_ids = [r.id for r in interaction.user.roles]
        config = config_db.get(guild_id, {}).get("command_config", {}).get(command_name)

        # ✅ If no config, allow by default
        if config is None:
            return True

        # ❌ Entirely disabled
        if config.get("enabled", True) is False:
            await interaction.response.send_message("❌ This command is disabled.", ephemeral=True)
            return False

        # 🔒 Handle blacklist mode
        if config.get("mode") == "blacklist":
            if any(rid in user_role_ids for rid in config.get("roles", [])):
                await interaction.response.send_message("❌ Your role is blacklisted from this command.", ephemeral=True)
                return False

        # ✅ Whitelist mode (if explicitly configured)
        if config.get("mode") == "whitelist":
            if not any(rid in user_role_ids for rid in config.get("roles", [])):
                await interaction.response.send_message("❌ You don't have access to this command.", ephemeral=True)
                return False

        return True

    return app_commands.check(predicate)

class DonateView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(
            label="Donate via Ko-fi",
            url=DONATION_URL,
            style=discord.ButtonStyle.link
        ))

@tree.command(name="donate", description="Support Coffeecord and get acces to exclusive features!")  # Optional: Only register in test server)
async def donate(interaction: discord.Interaction):
    if interaction.guild is None or interaction.guild.id != GALAXY_BOT_SERVER_ID:
        await interaction.response.send_message(
            f"❌ Please use this command in the **Offical Coffeecord Server**: {PERMANENT_INVITE}",
            ephemeral=False
        )
        return

    embed = discord.Embed(
        title="Support Coffeecord! 💙",
        description=(
            "Click the button below to donate via Ko-fi.\n\n"
            "✅ Link your Discord account to Ko-fi for auto-reward!\n"
            "**Perks:**\n"
            "- `Supporter` role!\n"
            "- Access to a private channel!\n"
            "- Early access to new features!\n"
            "- Play Gifs in your leveling card!"
        ),
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed, view=DonateView(), ephemeral=True)

if os.path.exists(VERIFY_CONFIG_FILE):
    with open(VERIFY_CONFIG_FILE, "r") as f:
        try:
            verify_config = json.load(f)
        except json.JSONDecodeError:
            print("⚠️ Warning: verify_config.json is empty or malformed.")
            verify_config = {}

sysfile_data.init_hidden_commands(bot)

# ============= CONFIG =============
TICKET_FILE = "tickets.json"
TRANSCRIPT_DIR = "transcripts"
os.makedirs(TRANSCRIPT_DIR, exist_ok=True)
# ==================================

def load_json(file):
    if not os.path.exists(file):
        return {}
    with open(file, "r") as f:
        return json.load(f)

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

# ============= ADD/REMOVE MENUS =============
class AddUserSelect(Select):
    def __init__(self, members, channel):
        options = [
            discord.SelectOption(label=m.name, value=str(m.id)) for m in members if not m.bot
        ]
        super().__init__(placeholder="Select a user to add…", options=options, min_values=1, max_values=1)
        self.channel = channel

    async def callback(self, interaction: discord.Interaction):
        user_id = int(self.values[0])
        user = interaction.guild.get_member(user_id)
        await self.channel.set_permissions(user, read_messages=True, send_messages=True)
        await interaction.response.send_message(f"✅ {user.name} added to the ticket.", ephemeral=True)

class RemoveUserSelect(Select):
    def __init__(self, members, channel):
        options = [
            discord.SelectOption(label=m.name, value=str(m.id)) for m in members if not m.bot
        ]
        super().__init__(placeholder="Select a user to remove…", options=options, min_values=1, max_values=1)
        self.channel = channel

    async def callback(self, interaction: discord.Interaction):
        user_id = int(self.values[0])
        user = interaction.guild.get_member(user_id)
        await self.channel.set_permissions(user, overwrite=None)
        await interaction.response.send_message(f"✅ {user.name} removed from the ticket.", ephemeral=True)
# ============================================


# ============= CONTROL PANEL =============
class TicketControlPanel(View):
    def __init__(self, bot, ticket_owner_id, support_roles):
        super().__init__(timeout=None)
        self.bot = bot
        self.ticket_owner_id = ticket_owner_id
        self.support_roles = support_roles
        self.claimed_by = None

    @discord.ui.button(label="Claim Ticket", style=discord.ButtonStyle.primary)
    async def claim_ticket(self, interaction: discord.Interaction, button: Button):
        if not any(r.id in self.support_roles for r in interaction.user.roles):
            return await interaction.response.send_message("❌ Only support staff can claim this ticket.", ephemeral=True)

        if self.claimed_by:
            return await interaction.response.send_message(f"⚠️ Already claimed by {self.claimed_by.mention}.", ephemeral=True)

        self.claimed_by = interaction.user
        await interaction.response.send_message(f"✅ Ticket claimed by {interaction.user.mention}.", ephemeral=False)
        button.disabled = True
        await interaction.message.edit(view=self)

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.danger)
    async def close_ticket(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.ticket_owner_id and not any(r.id in self.support_roles for r in interaction.user.roles):
            return await interaction.response.send_message("❌ Only the ticket owner or staff can close this ticket.", ephemeral=True)

        await interaction.response.send_message("🔒 Closing ticket in 5 seconds...", ephemeral=True)
        await asyncio.sleep(5)
        await self.generate_transcript(interaction.channel)
        await interaction.channel.delete()

    @discord.ui.button(label="Add User", style=discord.ButtonStyle.success)
    async def add_user(self, interaction: discord.Interaction, button: Button):
        view = View()
        members = [m for m in interaction.guild.members if m not in interaction.channel.members]
        view.add_item(AddUserSelect(members, interaction.channel))
        await interaction.response.send_message("Select a user to add:", view=view, ephemeral=True)

    @discord.ui.button(label="Remove User", style=discord.ButtonStyle.secondary)
    async def remove_user(self, interaction: discord.Interaction, button: Button):
        view = View()
        members = [m for m in interaction.channel.members if m != interaction.guild.me]
        view.add_item(RemoveUserSelect(members, interaction.channel))
        await interaction.response.send_message("Select a user to remove:", view=view, ephemeral=True)

    async def generate_transcript(self, channel: discord.TextChannel):
        messages = [msg async for msg in channel.history(limit=None, oldest_first=True)]
        transcript = [
            {
                "author": msg.author.name,
                "content": msg.content,
                "timestamp": msg.created_at.isoformat()
            }
            for msg in messages
        ]

        file_path = os.path.join(TRANSCRIPT_DIR, f"{channel.id}.json")
        with open(file_path, "w") as f:
            json.dump(transcript, f, indent=4)

        data = load_json(TICKET_FILE)
        guild_id = str(channel.guild.id)
        config = data.get(guild_id, {})
        support_roles = config.get("support_roles", [])

        # DM transcript to ticket owner
        try:
            owner = channel.guild.get_member(self.ticket_owner_id)
            if owner:
                await owner.send(file=discord.File(file_path))
        except:
            pass

        # DM transcript to support staff
        for role_id in support_roles:
            role = channel.guild.get_role(role_id)
            if role:
                for member in role.members:
                    try:
                        await member.send(file=discord.File(file_path))
                    except:
                        continue

        os.remove(file_path)
# ==========================================


# ============= MAIN TICKET VIEW =============
class TicketView(View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Open Ticket", style=discord.ButtonStyle.success)
    async def open_ticket(self, interaction: discord.Interaction, button: Button):
        data = load_json(TICKET_FILE)
        guild_id = str(interaction.guild.id)
        config = data.get(guild_id)

        if not config:
            return await interaction.response.send_message("⚠️ Ticket system not configured yet.", ephemeral=True)

        category = interaction.guild.get_channel(config["category_id"])
        support_roles = [interaction.guild.get_role(rid) for rid in config.get("support_roles", [])]

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        }
        for role in support_roles:
            overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        channel = await interaction.guild.create_text_channel(
            name=f"ticket-{interaction.user.name}",
            category=category,
            overwrites=overwrites
        )

        await channel.send(
            f"🎫 Ticket created by {interaction.user.mention}.",
            view=TicketControlPanel(self.bot, interaction.user.id, [r.id for r in support_roles])
        )

        await interaction.response.send_message(f"✅ Ticket created: {channel.mention}", ephemeral=True)
# ============================================

@tree.command(name="ticket_setup", description="Setup the ticket system")
@app_commands.describe(category="Ticket category", support_roles="Roles that can manage tickets (comma-separated)")
async def ticket_setup(interaction: discord.Interaction, category: discord.CategoryChannel, support_roles: str):
    role_ids = [int(r.strip("<@&>")) for r in support_roles.split(",") if r.strip()]
    data = load_json(TICKET_FILE)
    guild_id = str(interaction.guild.id)
    data[guild_id] = {
        "category_id": category.id,
        "support_roles": role_ids
    }
    save_json(TICKET_FILE, data)

    view = TicketView(bot)
    await interaction.channel.send("🎟️ Ticket System Setup Complete!", view=view)
    await interaction.response.send_message("✅ Ticket system configured successfully!", ephemeral=True)

@bot.event
async def on_ready():
    print(f"We are ready to go in, {bot.user.name}")

GUILD_ID = 1212210181044183171

LOGGING_FILE = "logging.json"

# --- Load & Save ---
def load_logging_config():
    if not os.path.exists(LOGGING_FILE):
        return {"guilds": {}}
    with open(LOGGING_FILE, "r") as f:
        return json.load(f)

def save_logging_config(data):
    with open(LOGGING_FILE, "w") as f:
        json.dump(data, f, indent=2)

def sanitize_logging_config(config):
    for guild_id, guild_cfg in config.get("guilds", {}).items():
        log_events = guild_cfg.setdefault("log_events", {})
        for cmd, cmd_cfg in log_events.items():
            if "enabled" not in cmd_cfg:
                cmd_cfg["enabled"] = "channel_id" in cmd_cfg
    return config

logging_config = sanitize_logging_config(load_logging_config())

# --- Logging Decision Logic ---
def should_log(guild_id: str, event: str):
    cfg = logging_config.get("guilds", {}).get(guild_id, {})
    log_events = cfg.get("log_events", {})
    is_enabled = cfg.get("enabled") and log_events.get(event, {}).get("enabled", False)
    print(f"[DEBUG] should_log → guild_id={guild_id}, event={event}, result={is_enabled}")
    return is_enabled

# --- Extract Options for Slash Commands ---
def extract_options(data):
    options = {}
    def recurse(opts):
        for opt in opts:
            if opt["type"] == 1:
                recurse(opt.get("options", []))
            else:
                options[opt["name"]] = opt["value"]
    recurse(data.get("options", []))
    return options

# --- Generate Log Message ---
async def get_log_message(interaction: discord.Interaction):
    cmd_name = interaction.command.name
    user = interaction.user
    options = extract_options(interaction.data or {})
    target_id = options.get("member") or options.get("user")
    reason = options.get("reason", "No reason provided")

    target_mention = "Unknown"
    if target_id:
        try:
            target = await interaction.guild.fetch_member(int(target_id))
            target_mention = target.mention
        except:
            target_mention = f"<@{target_id}>"

    if cmd_name == "mute":
        return f"🔇 {user.mention} muted {target_mention} — Reason: {reason}"
    if cmd_name == "unmute":
        return f"🔈 {user.mention} unmuted {target_mention}"
    if cmd_name == "ban":
        return f"🔨 {user.mention} banned {target_mention} — Reason: {reason}"
    if cmd_name == "kick":
        return f"👢 {user.mention} kicked {target_mention} — Reason: {reason}"

    return f"📘 `{cmd_name}` command used by {user.mention}"

# --- Send Log to Channel ---
async def log_action(interaction: discord.Interaction, message: str):
    guild_id = str(interaction.guild_id)
    cfg = logging_config.get("guilds", {}).get(guild_id, {})
    log_events = cfg.get("log_events", {})
    event = interaction.command.name
    channel_id = (
        log_events.get(event, {}).get("channel_id")
        or cfg.get("log_channel_id")
    )
    if not channel_id:
        print(f"[DEBUG] No channel_id set for event '{event}' in guild {guild_id}")
        return
    channel = interaction.guild.get_channel(channel_id)
    if channel:
        try:
            await channel.send(message)
            print(f"[DEBUG] Sent log message to channel {channel_id}")
        except Exception as e:
            print(f"[ERROR] Failed to send log message: {e}")
    else:
        print(f"[DEBUG] Channel ID {channel_id} not found in guild {guild_id}")

# --- Interaction Event Listener ---
@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type == discord.InteractionType.application_command:
        command_name = interaction.command.name if interaction.command else "Unknown"
        guild_id = str(interaction.guild_id) if interaction.guild_id else None

        if not guild_id:
            return

        print(f"[DEBUG] on_interaction → Guild: {guild_id}, Command: {command_name}")

        if should_log(guild_id, command_name):
            print(f"[DEBUG] should_log returned True")
            log_msg = await get_log_message(interaction)
            await log_action(interaction, log_msg)
        else:
            print(f"[DEBUG] should_log returned False")

# ----- UI Components -----

class LoggingCommandSelector(discord.ui.Select):
    def __init__(self, commands_list, guild):
        self.commands_list = commands_list
        self.guild = guild
        options = []
        for cmd in commands_list:
            # Show enabled/disabled and channel info if exists
            guild_cfg = logging_config["guilds"].get(str(guild.id), {})
            log_events = guild_cfg.get("log_events", {})
            cmd_cfg = log_events.get(cmd, {})
            enabled = cmd_cfg.get("enabled", False)
            channel_id = cmd_cfg.get("channel_id")
            channel_name = guild.get_channel(channel_id).name if channel_id and guild.get_channel(channel_id) else "None"
            label = f"{cmd} [{'ON' if enabled else 'OFF'}]"
            description = f"Logs to: #{channel_name}" if channel_id else "Not configured"
            options.append(discord.SelectOption(label=label, description=description, value=cmd))
        super().__init__(
            placeholder="Step 1: Select a command to configure ✅",
            options=options,
            custom_id="log_command_select"
        )

    async def callback(self, interaction: discord.Interaction):
        command = self.values[0]
        await interaction.response.edit_message(
            content=f"**Step 2: Choose a log channel and toggle logging for `{command}` ✅**",
            view=LogCommandView(command, self.guild, self.commands_list)
        )

class ChannelSelector(discord.ui.Select):
    def __init__(self, command_name: str, guild: discord.Guild):
        self.command_name = command_name
        self.guild = guild
        options = [
            discord.SelectOption(label=ch.name, value=str(ch.id))
            for ch in guild.text_channels if ch.permissions_for(guild.me).send_messages
        ]
        super().__init__(
            placeholder="Choose a channel to log this command",
            options=options,
            custom_id=f"channel_selector_{command_name}"
        )

    async def callback(self, interaction: discord.Interaction):
        channel_id = int(self.values[0])
        guild_id = str(self.guild.id)
        guild_cfg = logging_config["guilds"].setdefault(guild_id, {})
        event_cfg = guild_cfg.setdefault("log_events", {}).setdefault(self.command_name, {})
        event_cfg["channel_id"] = channel_id
        # Enable logging automatically when channel selected
        event_cfg["enabled"] = True
        save_logging_config(logging_config)
        await interaction.response.send_message(f"✅ `{self.command_name}` will now log to <#{channel_id}>.", ephemeral=True)

class ToggleLogging(discord.ui.Button):
    def __init__(self, command_name: str, guild_id: str):
        self.command_name = command_name
        self.guild_id = guild_id
        current = logging_config["guilds"].get(guild_id, {}).get("log_events", {}).get(command_name, {}).get("enabled", False)
        label = "✅ Enabled" if current else "❌ Disabled"
        style = discord.ButtonStyle.green if current else discord.ButtonStyle.red
        super().__init__(label=label, style=style, custom_id=f"toggle_{command_name}")

    async def callback(self, interaction: discord.Interaction):
        guild_cfg = logging_config["guilds"].setdefault(self.guild_id, {})
        event_cfg = guild_cfg.setdefault("log_events", {}).setdefault(self.command_name, {})

        event_cfg["enabled"] = not event_cfg.get("enabled", False)

        # Ensure channel_id exists, else default to guild's log_channel_id (optional)
        if "channel_id" not in event_cfg:
            event_cfg["channel_id"] = guild_cfg.get("log_channel_id", None)

        save_logging_config(logging_config)

        status = "Enabled" if event_cfg["enabled"] else "Disabled"
        label = "✅ Enabled" if event_cfg["enabled"] else "❌ Disabled"
        style = discord.ButtonStyle.green if event_cfg["enabled"] else discord.ButtonStyle.red

        # Update button label and style
        self.label = label
        self.style = style

        await interaction.response.edit_message(content=f"Logging for `{self.command_name}` is now **{status}**.", view=self.view)

class AddAnotherCommandButton(discord.ui.Button):
    def __init__(self, commands_list, guild):
        super().__init__(label="Configure Another Command", style=discord.ButtonStyle.blurple)
        self.commands_list = commands_list
        self.guild = guild

    async def callback(self, interaction: discord.Interaction):
        view = LoggingConfigView(self.commands_list, self.guild)
        await interaction.response.edit_message(content="🛠️ Choose log channels and toggle logging per command:", view=view)

class LogCommandView(discord.ui.View):
    def __init__(self, command_name, guild, commands_list):
        super().__init__(timeout=180)
        self.add_item(ChannelSelector(command_name, guild))
        self.add_item(ToggleLogging(command_name, str(guild.id)))
        self.add_item(AddAnotherCommandButton(commands_list, guild))

class LoggingConfigView(discord.ui.View):
    def __init__(self, commands_to_configure, guild):
        super().__init__(timeout=180)
        self.add_item(LoggingCommandSelector(commands_to_configure, guild))
        self.guild = guild

# ---- Commands ----

@tree.command(name="logging_on", description="Enable logging for this server.")
async def logging_on(interaction: discord.Interaction):
    guild_id = str(interaction.guild_id)
    logging_config["guilds"].setdefault(guild_id, {})
    logging_config["guilds"][guild_id]["enabled"] = True
    save_logging_config(logging_config)
    await interaction.response.send_message("✅ Logging enabled.", ephemeral=True)

@tree.command(name="logging_off", description="Disable logging for this server.")
async def logging_off(interaction: discord.Interaction):
    guild_id = str(interaction.guild_id)
    logging_config["guilds"].setdefault(guild_id, {})
    logging_config["guilds"][guild_id]["enabled"] = False
    save_logging_config(logging_config)
    await interaction.response.send_message("❌ Logging disabled.", ephemeral=True)

@tree.command(name="logging_channel", description="Set the default log channel.")
@app_commands.describe(channel="The channel to log events in")
async def logging_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    guild_id = str(interaction.guild_id)
    logging_config["guilds"].setdefault(guild_id, {})
    logging_config["guilds"][guild_id]["log_channel_id"] = channel.id
    save_logging_config(logging_config)
    await interaction.response.send_message(f"📘 Logging channel set to {channel.mention}.", ephemeral=True)

@tree.command(name="logging_config", description="Configure what commands are logged.")
async def logging_configure(interaction: discord.Interaction):
    commands_to_configure = [
        "ban", "kick", "mute", "unmute", "hardmute",
        "muterole", "muterole_create", "muterole_update",
        "xp", "xpconfig", "logging_on", "logging_off",
        "logging_channel", "logging_config"
    ]
    view = LoggingConfigView(commands_to_configure, interaction.guild)
    await interaction.response.send_message("🛠️ Choose log channels and toggle logging per command:", view=view, ephemeral=True)

from typing import Optional
from discord import app_commands, ui, Interaction
# ------------------- BAN COMMAND -------------------
@tree.command(name="ban", description="Ban or tempban a member.")
@app_commands.describe(
    member="The member to ban.",
    reason="Reason for the ban.",
    duration="Ban duration in minutes. Leave empty for permanent."
)
@app_commands.checks.has_permissions(ban_members=True)
async def ban(
    interaction: discord.Interaction,
    member: discord.Member,
    reason: Optional[str] = None,
    duration: Optional[int] = None,  # in minutes
):
    if member == interaction.user:
        return await interaction.response.send_message("❌ You cannot ban yourself.", ephemeral=True)
    if member.top_role >= interaction.user.top_role:
        return await interaction.response.send_message("❌ You cannot ban someone with an equal or higher role.", ephemeral=True)

    try:
        await member.ban(reason=reason)
        if duration:
            await interaction.response.send_message(
                f"🔨 {member} has been banned for {duration} minutes. Reason: {reason or 'No reason provided'}"
            )
            # Wait and unban later
            await asyncio.sleep(duration * 60)
            await interaction.guild.unban(member)
        else:
            await interaction.response.send_message(
                f"🔨 {member} has been permanently banned. Reason: {reason or 'No reason provided'}"
            )
    except discord.Forbidden:
        await interaction.response.send_message("❌ I don't have permission to ban this member.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Failed to ban {member}: {e}", ephemeral=True)


# ------------------- UNBAN COMMAND -------------------
@tree.command(name="unban", description="Unban a user from the server by ID (Admin only)")
@app_commands.describe(user_id="The ID of the user to unban")
@app_commands.checks.has_permissions(ban_members=True)
async def unban(interaction: discord.Interaction, user_id: str):
    guild = interaction.guild
    if not guild:
        return await interaction.response.send_message("❌ This command can only be used in a server.", ephemeral=True)

    try:
        user_id = int(user_id)
    except ValueError:
        return await interaction.response.send_message("❌ Invalid user ID.", ephemeral=True)

    try:
        # Convert async iterator to list
        bans = [b async for b in guild.bans()]
        ban_entry = next((b for b in bans if b.user.id == user_id), None)

        if not ban_entry:
            return await interaction.response.send_message(f"❌ No banned user with ID `{user_id}` found.", ephemeral=True)

        await guild.unban(ban_entry.user, reason=f"Unbanned by {interaction.user}")
        await interaction.response.send_message(f"✅ Successfully unbanned {ban_entry.user}.")
    except discord.Forbidden:
        await interaction.response.send_message("❌ I don't have permission to unban this user.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ An error occurred: {e}", ephemeral=True)
  
@tree.command(name="help", description="Show all bot commands")
async def help_command(interaction: discord.Interaction):
    try:
        embed1 = discord.Embed(
            title="🤖 BOT COMMANDS HELP MENU (1/2)",
            description="Here are the available commands:",
            color=0x00ffcc,
        )
        embed1.add_field(
            name="🎮 FUN",
            value="`/8ball`, `/ak47`, `/cat`, `/dog`, `/petpet`, `/nuke`, `/roast`, `/uwuify`",
            inline=False,
        )
        embed1.add_field(
            name="SOCIAL",
            value="`/breakup`, `/hug`, `/kiss`, `/lovecalc`, `/marry`, `/date`, `/close`",
            inline=False,
        )
        embed1.add_field(
            name="🎤 TRUTH OR DARE",
            value="`/truth`, `/dare`",
            inline=False,
        )
        embed1.add_field(
            name="🎲 GAMES & BETTING",
            value="`/flipcoin`, `/bet`",
            inline=False,
        )
        embed1.add_field(
            name="🕑 TIMERS & REMINDERS",
            value="`/starttimer`, `/endtimer`, `/checktimers`",
            inline=False,
        )

        embed2 = discord.Embed(
            title="🤖 BOT COMMANDS HELP MENU (2/2)",
            color=0x00ffcc,
        )
        embed2.add_field(
            name="📝 MODERATION",
            value="`/mute`, `/unmute`, `/ban`, `/tempban`, `/kick`, `/warn`, `/checkwarn`, `/removewarn`, `/purge`",
            inline=False,
        )
        embed2.add_field(
            name="🧩 ROLES & VERIFICATION",
            value="`/verify`, `/verifyconfig`, `/autorole`, `/giverole`, `/removerole`",
            inline=False,
        )
        embed2.add_field(
            name="📌 APPLICATIONS",
            value="`/application`, `/applicationapprove`, `/applyoff`, `/applyon`",
            inline=False,
        )
        embed2.add_field(
            name="📊 POLLS & TOOLS",
            value="`/dm`, `/dmforward`, `/poll`, `/say`, `/log`, `/donate`",
            inline=False,
        )
        embed2.add_field(
            name="📈 XP SYSTEM",
            value="`/xp`, `/xpconfig`, `/questcreate`, `/questdelete`, `/questlist`",
            inline=False,
        )

        await interaction.response.send_message(embeds=[embed1, embed2], ephemeral=True)

    except Exception as e:
        await interaction.response.send_message(
            f"❌ Error in help command: {e}", ephemeral=True
        )
        print(f"[HELP ERROR] {e}")

@tree.command(name="date", description="Ask someone on a date (creates a private thread)")
@app_commands.describe(member="The person you want to ask out")
async def date(interaction: discord.Interaction, member: discord.Member):
    thread = await interaction.channel.create_thread(
        name=f"Askout - {interaction.user.display_name} & {member.display_name}",
        type=discord.ChannelType.private_thread,
        invitable=False
    )
    await thread.add_user(interaction.user)
    await thread.add_user(member)
    await thread.send(f"👋 {interaction.user.mention} wants to go on a date with {member.mention}! Use /close to end it.")
    await interaction.response.send_message("✅ Date thread created!", ephemeral=True)

@tree.command(name="close", description="Close this private thread")
async def close(interaction: discord.Interaction):
    if isinstance(interaction.channel, discord.Thread):
        await interaction.channel.send("🔒 This thread is now being closed.")
        await interaction.channel.edit(archived=True, locked=True)
        await interaction.response.send_message("✅ Thread closed.", ephemeral=True)
    else:
        await interaction.response.send_message("❌ This command can only be used inside a thread.", ephemeral=True)

FILE_PATH = "banned_words.json"

def load_data():
    if not os.path.exists(FILE_PATH):
        with open(FILE_PATH, "w") as f:
            json.dump({}, f)
    with open(FILE_PATH, "r") as f:
        return json.load(f)

def save_data(data):
    with open(FILE_PATH, "w") as f:
        json.dump(data, f, indent=2)

def get_server_words(guild_id):
    data = load_data()
    return data.get(str(guild_id), [])

def set_server_words(guild_id, words):
    data = load_data()
    data[str(guild_id)] = words
    save_data(data)

# On message filter

# Slash command with buttons
@tree.command(name="languagefilter", description="Manage bad words for your server")
async def languagefilter(interaction: discord.Interaction):
    guild_id = str(interaction.guild.id)
    words = get_server_words(guild_id)
    word_list = "\n• " + "\n• ".join(words) if words else "No banned words set."

    view = WordManager(interaction.user, guild_id)
    await interaction.response.send_message(
        f"🚫 **Banned Words in This Server:**\n{word_list}",
        view=view,
        ephemeral=True
    )

# Button UI
class WordManager(discord.ui.View):
    def __init__(self, user, guild_id):
        super().__init__(timeout=180)
        self.user = user
        self.guild_id = guild_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user.id

    @discord.ui.button(label="➕ Add Word", style=discord.ButtonStyle.success)
    async def add(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AddWordModal(self.guild_id))

    @discord.ui.button(label="➖ Remove Word", style=discord.ButtonStyle.danger)
    async def remove(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RemoveWordModal(self.guild_id))

class AddWordModal(discord.ui.Modal, title="Add Banned Word"):
    word = discord.ui.TextInput(label="Word to ban", max_length=30)

    def __init__(self, guild_id):
        super().__init__()
        self.guild_id = guild_id

    async def on_submit(self, interaction: discord.Interaction):
        words = get_server_words(self.guild_id)
        word = self.word.value.lower()
        if word not in words:
            words.append(word)
            set_server_words(self.guild_id, words)
            await interaction.response.send_message(f"✅ Banned `{word}`", ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ That word is already banned.", ephemeral=True)

class RemoveWordModal(discord.ui.Modal, title="Remove Banned Word"):
    word = discord.ui.TextInput(label="Word to unban", max_length=30)

    def __init__(self, guild_id):
        super().__init__()
        self.guild_id = guild_id

    async def on_submit(self, interaction: discord.Interaction):
        words = get_server_words(self.guild_id)
        word = self.word.value.lower()
        if word in words:
            words.remove(word)
            set_server_words(self.guild_id, words)
            await interaction.response.send_message(f"✅ Unbanned `{word}`", ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ That word was not banned.", ephemeral=True)

async def log_action(interaction: discord.Interaction, message: str):
    guild_id = str(interaction.guild_id)
    cfg = logging_config.get("guilds", {}).get(guild_id, {})
    log_events = cfg.get("log_events", {})
    event = interaction.command.name
    channel_id = (
        log_events.get(event, {}).get("channel_id")
        or cfg.get("log_channel_id")
    )
    if not channel_id:
        print(f"[DEBUG] No channel_id set for event '{event}' in guild {guild_id}")
        return
    channel = interaction.guild.get_channel(channel_id)
    if channel:
        try:
            await channel.send(message)
            print(f"[DEBUG] Sent log message to channel {channel_id}")
        except Exception as e:
            print(f"[ERROR] Failed to send log message: {e}")
    else:
        print(f"[DEBUG] Channel ID {channel_id} not found in guild {guild_id}")

@tree.command(name="giverole", description="Give a role to a user.")
@app_commands.describe(member="User to give the role to", role="Role to give")
async def giverole(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    if role in member.roles:
        await interaction.response.send_message(
            f"❌ {member.mention} already has the role {role.name}.", ephemeral=True)
        return

    try:
        await member.add_roles(role)
        await interaction.response.send_message(
            f"✅ Added role {role.name} to {member.mention}.")
    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ I do not have permission to add that role.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(
            f"❌ Error: {e}", ephemeral=True)

@tree.command(name="removerole", description="Remove a role from a user.")
@app_commands.describe(member="User to remove the role from", role="Role to remove")
async def removerole(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    if role not in member.roles:
        await interaction.response.send_message(
            f"❌ {member.mention} does not have the role {role.name}.", ephemeral=True)
        return

    try:
        await member.remove_roles(role)
        await interaction.response.send_message(
            f"✅ Removed role {role.name} from {member.mention}.")
    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ I do not have permission to remove that role.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(
            f"❌ Error: {e}", ephemeral=True)
        

autorole_config = {}  # guild_id: {event_key: [role_ids]}

def save_autorole_config():
    with open(CONFIG_FILE, "w") as f:
        json.dump(autorole_config, f, indent=4)

def load_autorole_config():
    global autorole_config
    try:
        with open(CONFIG_FILE, "r") as f:
            autorole_config = json.load(f)
    except FileNotFoundError:
        autorole_config = {}

load_autorole_config()

class EventDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Member Join", value="member_join"),
            discord.SelectOption(label="Message Sent", value="message_sent"),
            discord.SelectOption(label="Thread Opened", value="thread_opened"),
            discord.SelectOption(label="Voice Channel Join", value="voice_join"),
            discord.SelectOption(label="Boost Server", value="boost"),
            discord.SelectOption(label="Reaction Added", value="reaction"),
            discord.SelectOption(label="Account Age Verified", value="verified"),
            discord.SelectOption(label="First Slash Command Used", value="slash"),
        ]
        super().__init__(placeholder="Choose a trigger event…", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        self.view.selected_event = self.values[0]
        await interaction.response.send_message(
            embed=discord.Embed(
                title="✅ Event Selected",
                description=f"Selected event: `{self.view.selected_event.replace('_', ' ').title()}`",
                color=discord.Color.green()
            ),
            ephemeral=True
        )

# Autorole View
class AutoRoleView(discord.ui.View):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=90)
        self.guild = guild
        self.selected_event = None
        self.selected_roles = []
        self.add_item(EventDropdown())
        self.add_item(self.RoleSelect())
        self.add_item(self.RemoveButton())
        self.add_item(self.SubmitButton())  # Submit moved to bottom

    class RoleSelect(discord.ui.RoleSelect):
        def __init__(self):
            super().__init__(placeholder="Select role(s) to give", min_values=1, max_values=5)

        async def callback(self, interaction: discord.Interaction):
            self.view.selected_roles = self.values
            role_mentions = ", ".join([role.mention for role in self.view.selected_roles])
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="✅ Roles Selected",
                    description=f"Selected role(s): {role_mentions}",
                    color=discord.Color.green()
                ),
                ephemeral=True
            )

    class SubmitButton(discord.ui.Button):
        def __init__(self):
            super().__init__(label="Submit", style=discord.ButtonStyle.green)

        async def callback(self, interaction: discord.Interaction):
            view = self.view
            if not view.selected_event or not view.selected_roles:
                await interaction.response.send_message(
                    "⚠️ Please select both an event and at least one role.",
                    ephemeral=True
                )
                return

            guild_id = str(interaction.guild.id)
            if guild_id not in autorole_config:
                autorole_config[guild_id] = {}

            autorole_config[guild_id][view.selected_event] = [role.id for role in view.selected_roles]
            save_autorole_config()

            roles_display = ", ".join(role.mention for role in view.selected_roles)
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="✅ Autoroles Saved",
                    description=f"**Event:** `{view.selected_event}`\n**Roles:** {roles_display}",
                    color=discord.Color.blurple()
                ),
                ephemeral=True
            )

    class RemoveButton(discord.ui.Button):
        def __init__(self):
            super().__init__(label="Remove Autorole", style=discord.ButtonStyle.red)

        async def callback(self, interaction: discord.Interaction):
            guild_id = str(interaction.guild.id)
            config = autorole_config.get(guild_id, {})

            if not config:
                await interaction.response.send_message("❌ No autoroles to remove.", ephemeral=True)
                return

            options = []
            for event, roles in config.items():
                for role_id in roles:
                    role = interaction.guild.get_role(role_id)
                    if role:
                        options.append(discord.SelectOption(label=f"{event} – {role.name}", value=f"{event}:{role_id}"))

            class RemoveDropdown(discord.ui.Select):
                def __init__(self):
                    super().__init__(placeholder="Select autorole to remove", options=options)

                async def callback(inner_self, interaction: discord.Interaction):
                    val = inner_self.values[0]
                    event, role_id = val.split(":")
                    role_id = int(role_id)
                    autorole_config[guild_id][event].remove(role_id)
                    if not autorole_config[guild_id][event]:
                        del autorole_config[guild_id][event]
                    save_autorole_config()
                    await interaction.response.send_message(
                        f"🗑️ Removed autorole for `{event}` (role ID: {role_id})",
                        ephemeral=True
                    )
                    self.view.stop()

            remove_view = discord.ui.View(timeout=30)
            remove_view.add_item(RemoveDropdown())
            await interaction.response.send_message("🗑️ Choose an autorole to remove:", view=remove_view, ephemeral=True)

MUTEROLE_FILE = "muterole.json"

def load_mute_config():
    try:
        with open(MUTEROLE_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_mute_config(config):
    with open(MUTEROLE_FILE, "w") as f:
        json.dump(config, f, indent=2)

mute_config = load_mute_config()

# === Mute Commands ===

@tree.command(name="mute", description="Mute a member for a specified time.")
@app_commands.describe(member="User to mute", duration="Duration (number)", unit="Time unit: m for minutes, h for hours", reason="Reason for muting")
@app_commands.checks.has_permissions(manage_roles=True)
async def mute(interaction: discord.Interaction, member: discord.Member, duration: int, unit: str, reason: str = None):
    unit = unit.lower()
    if unit not in ("m", "h"):
        await interaction.response.send_message("❌ Invalid time unit. Use 'm' for minutes or 'h' for hours.", ephemeral=True)
        return

    duration_seconds = duration * 60 if unit == "m" else duration * 3600
    guild_id = str(interaction.guild_id)
    mute_role_id = mute_config.get(guild_id)

    if not mute_role_id:
        await interaction.response.send_message("⚠️ Mute role not set. Use `/muterole_create` or `/muterole_update`.", ephemeral=True)
        return

    mute_role = interaction.guild.get_role(mute_role_id)
    if not mute_role:
        await interaction.response.send_message("⚠️ Mute role does not exist. Please update it again.", ephemeral=True)
        return

    if mute_role in member.roles:
        await interaction.response.send_message(f"❌ {member.mention} is already muted.", ephemeral=True)
        return

    await member.add_roles(mute_role, reason=reason)
    await interaction.response.send_message(f"🔇 {member.mention} has been muted for {duration}{unit}. Reason: {reason or 'No reason provided'}")

    await asyncio.sleep(duration_seconds)
    await member.remove_roles(mute_role, reason="Mute expired")


@tree.command(name="unmute", description="Unmute a member manually")
@app_commands.describe(member="User to unmute")
@app_commands.checks.has_permissions(manage_roles=True)
async def unmute(interaction: discord.Interaction, member: discord.Member):
    guild_id = str(interaction.guild_id)
    mute_role_id = mute_config.get(guild_id)
    if not mute_role_id:
        await interaction.response.send_message("⚠️ No mute role configured.", ephemeral=True)
        return

    mute_role = interaction.guild.get_role(mute_role_id)
    if mute_role in member.roles:
        await member.remove_roles(mute_role, reason="Manual unmute")
        await interaction.response.send_message(f"🔊 {member.mention} has been unmuted.")
    else:
        await interaction.response.send_message(f"❌ {member.mention} is not muted.", ephemeral=True)


@tree.command(name="muterole_create", description="Create and set a mute role")
@app_commands.checks.has_permissions(manage_roles=True)
async def muterole_create(interaction: discord.Interaction):
    guild = interaction.guild
    role = await guild.create_role(name="Muted", reason="Mute role creation")
    for channel in guild.channels:
        try:
            await channel.set_permissions(role, send_messages=False, speak=False, add_reactions=False)
        except:
            continue

    mute_config[str(guild.id)] = role.id
    save_mute_config(mute_config)
    await interaction.response.send_message(f"✅ Created and set mute role: `{role.name}`", ephemeral=True)


@tree.command(name="muterole_update", description="Update the mute role")
@app_commands.describe(role="The new mute role")
@app_commands.checks.has_permissions(manage_roles=True)
async def muterole_update(interaction: discord.Interaction, role: discord.Role):
    mute_config[str(interaction.guild_id)] = role.id
    save_mute_config(mute_config)
    await interaction.response.send_message(f"🔄 Mute role updated to `{role.name}`", ephemeral=True)


@tree.command(name="hardmute", description="Mute and remove all roles from a user")
@app_commands.describe(member="Member to hardmute", reason="Reason for hardmute")
@app_commands.checks.has_permissions(manage_roles=True)
async def hardmute(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    guild_id = str(interaction.guild_id)
    mute_role_id = mute_config.get(guild_id)
    if not mute_role_id:
        await interaction.response.send_message("⚠️ Mute role not set.", ephemeral=True)
        return

    mute_role = interaction.guild.get_role(mute_role_id)
    roles_to_remove = [r for r in member.roles if r != interaction.guild.default_role and r != mute_role]

    try:
        await member.remove_roles(*roles_to_remove, reason="Hardmute")
        await member.add_roles(mute_role, reason=reason)
        await interaction.response.send_message(f"🔇 {member.mention} has been hardmuted. Reason: {reason}")
    except discord.Forbidden:
        await interaction.response.send_message("❌ Missing permission to manage roles.", ephemeral=True)

# Event Handlers
@bot.event
async def on_member_join(member):
    config = autorole_config.get(str(member.guild.id), {})
    roles = config.get("member_join", [])
    for role_id in roles:
        role = member.guild.get_role(role_id)
        if role:
            await member.add_roles(role, reason="Autorole: Member Join")

@bot.event
async def on_thread_join(thread, member):
    config = autorole_config.get(str(member.guild.id), {})
    roles = config.get("thread_opened", [])
    for role_id in roles:
        role = member.guild.get_role(role_id)
        if role:
            await member.add_roles(role, reason="Autorole: Thread Opened")

@bot.event
async def on_voice_state_update(member, before, after):
    if not before.channel and after.channel:
        config = autorole_config.get(str(member.guild.id), {})
        roles = config.get("voice_join", [])
        for role_id in roles:
            role = member.guild.get_role(role_id)
            if role:
                await member.add_roles(role, reason="Autorole: Voice Join")

@bot.event
async def on_member_update(before, after):
    if before.premium_since is None and after.premium_since is not None:
        config = autorole_config.get(str(after.guild.id), {})
        roles = config.get("boost", [])
        for role_id in roles:
            role = after.guild.get_role(role_id)
            if role:
                await after.add_roles(role, reason="Autorole: Boost")

    # Account Age Verified - example: give role if account is older than 7 days and member just joined
    if len(before.roles) < len(after.roles):
        config = autorole_config.get(str(after.guild.id), {})
        verified_roles = config.get("verified", [])
        if (discord.utils.utcnow() - after.created_at).days >= 7:
            for role_id in verified_roles:
                role = after.guild.get_role(role_id)
                if role and role not in after.roles:
                    await after.add_roles(role, reason="Autorole: Account Age Verified")

autoroles = set()  # Store roles IDs for auto-assigning

@tree.command(name="8ball", description="Ask the magic 8-ball a question.")
@app_commands.describe(question="Your yes/no style question")
async def eight_ball(interaction: discord.Interaction, question: str):
    responses = [
        "It is certain.",
        "Without a doubt.",
        "You may rely on it.",
        "Yes, definitely.",
        "It is decidedly so.",
        "As I see it, yes.",
        "Most likely.",
        "Outlook good.",
        "Yes.",
        "Signs point to yes.",
        "Reply hazy, try again.",
        "Ask again later.",
        "Better not tell you now.",
        "Cannot predict now.",
        "Concentrate and ask again.",
        "Don't count on it.",
        "My reply is no.",
        "My sources say no.",
        "Outlook not so good.",
        "Very doubtful."
    ]
    answer = random.choice(responses)
    await interaction.response.send_message(f"🎱 **Question:** {question}\n**Answer:** {answer}")

marriages = {}  # user_id -> partner_id
marriage_requests = {}  # user_id -> requester_id (pending requests)

@tree.command(name="bet", description="Place a bet with another user.")
@app_commands.describe(member="User to bet with", bet="What you want to bet")
async def bet(interaction: discord.Interaction, member: discord.Member, bet: str):
    await interaction.response.send_message(f"{interaction.user.mention} has bet {member.mention} {bet}!")

@tree.command(name="flipcoin", description="Flip a coin, optionally with a prize.")
@app_commands.describe(prize="Prize to win")
async def flipcoin(interaction: discord.Interaction, prize: str = None):
    result = random.choice(["Heads", "Tails"])
    if prize:
        await interaction.response.send_message(f"🪙 The coin landed on **{result}**! {interaction.user.mention} wins {prize}!")
    else:
        await interaction.response.send_message(f"🪙 The coin landed on **{result}**!")

@tree.command(name="marry", description="Propose marriage to another user.")
@app_commands.describe(member="User to marry")
async def marry(interaction: discord.Interaction, member: discord.Member):
    married_role = discord.utils.get(interaction.guild.roles, name="Married")

    if interaction.user.id in marriages:
        await interaction.response.send_message("❌ You are already married.", ephemeral=True)
        return
    if member.id in marriages:
        await interaction.response.send_message(f"❌ {member.mention} is already married.", ephemeral=True)
        return
    if member.id in marriage_requests and marriage_requests[member.id] == interaction.user.id:
        # Accept marriage request
        marriages[interaction.user.id] = member.id
        marriages[member.id] = interaction.user.id
        del marriage_requests[member.id]

        # Add "Married" role
        if married_role:
            await interaction.user.add_roles(married_role)
            await member.add_roles(married_role)

        await interaction.response.send_message(f"💍 {interaction.user.mention} and {member.mention} are now married! Congratulations! 🎉")
    else:
        marriage_requests[interaction.user.id] = member.id
        await interaction.response.send_message(f"💌 {interaction.user.mention} has proposed to {member.mention}! {member.mention}, type `/marry {interaction.user.display_name}` to accept.")

@tree.command(name="breakup", description="Break up with your married partner.")
@app_commands.describe(member="Your partner")
async def breakup(interaction: discord.Interaction, member: discord.Member):
    married_role = discord.utils.get(interaction.guild.roles, name="Married")

    user_id = interaction.user.id
    partner_id = marriages.get(user_id)
    if partner_id == member.id:
        del marriages[user_id]
        del marriages[partner_id]

        # Remove "Married" role
        if married_role:
            await interaction.user.remove_roles(married_role)
            await member.remove_roles(married_role)

        await interaction.response.send_message(f"💔 {interaction.user.mention} and {member.mention} have broken up.")
    else:
        await interaction.response.send_message(f"❌ You are not married to {member.mention}.", ephemeral=True)

@tree.command(name="hug", description="Give someone a hug.")
@app_commands.describe(member="User to hug")
async def hug(interaction: discord.Interaction, member: discord.Member):
    await interaction.response.send_message(f"🤗 {interaction.user.mention} gives {member.mention} a big hug!")

@tree.command(name="kiss", description="Kiss someone.")
@app_commands.describe(member="User to kiss")
async def kiss(interaction: discord.Interaction, member: discord.Member):
    await interaction.response.send_message(f"{interaction.user.mention} kissed {member.mention}!")

@tree.command(name="lovecalc", description="Calculate love compatibility between two users.")
@app_commands.describe(member1="First user", member2="Second user")
async def lovecalc(interaction: discord.Interaction, member1: discord.Member, member2: discord.Member):
    score = random.randint(0, 100)
    hearts = "❤️" * (score // 10)
    await interaction.response.send_message(f"💖 Love compatibility between {member1.mention} and {member2.mention} is {score}% {hearts}")

@tree.command(name="truth", description="Ask someone a truth question.")
@app_commands.describe(member="User to ask", question="Truth question")
async def truth(interaction: discord.Interaction, member: discord.Member, question: str):
    await interaction.response.send_message(f"🧠 {member.mention}, **Truth:** {question}")

@tree.command(name="dare", description="Give someone a dare challenge.")
@app_commands.describe(member="User to dare", challenge="Dare challenge")
async def dare(interaction: discord.Interaction, member: discord.Member, challenge: str):
    await interaction.response.send_message(f"🔥 {member.mention}, **Dare:** {challenge}")

reminders = []
timers = {}  # timer_id -> {user, end}

@tasks.loop(seconds=60)
async def reminder_checker():
    now = datetime.now()
    for reminder in reminders[:]:
        if reminder['time'] <= now:
            try:
                await reminder['user'].send(f"\u23F0 Reminder: {reminder['message']}")
            except:
                pass
            reminders.remove(reminder)

@tree.command(name="remindme", description="Set a reminder with a message and time.")
@app_commands.describe(message="Reminder text", date="Date (MM/DD/YY)", time="Time (HH:MM 24hr)")
async def remindme(interaction: discord.Interaction, message: str, date: str, time: str):
    try:
        remind_time = datetime.strptime(f"{date} {time}", "%m/%d/%y %H:%M")
        reminders.append({"user": interaction.user, "message": message, "time": remind_time})
        await interaction.response.send_message(f"\u2705 Reminder set for {remind_time.strftime('%m/%d/%y %H:%M')}", ephemeral=True)
    except ValueError:
        await interaction.response.send_message("\u274C Invalid date or time format. Use MM/DD/YY HH:MM.", ephemeral=True)

@tree.command(name="starttimer", description="Start a timer using s, m, or h (e.g., 10s, 5m, 2h)")
@app_commands.describe(duration="Duration of the timer like 10s, 5m, or 1h")
async def starttimer(interaction: discord.Interaction, duration: str):
    try:
        unit = duration[-1]
        value = int(duration[:-1])

        if unit == 's': seconds = value
        elif unit == 'm': seconds = value * 60
        elif unit == 'h': seconds = value * 3600
        else: raise ValueError("Invalid unit")

        timer_id = len(timers) + 1
        end_time = datetime.now() + timedelta(seconds=seconds)
        timers[timer_id] = {"user": interaction.user, "end": end_time}

        await interaction.response.send_message(f"\u23F3 Timer #{timer_id} started for {value}{unit}", ephemeral=True)
        await asyncio.sleep(seconds)

        if timer_id in timers:
            await interaction.user.send(f"\u23F0 Timer #{timer_id} is up!")
            del timers[timer_id]

    except ValueError:
        await interaction.response.send_message("\u274C Invalid format. Use like `10s`, `5m`, or `2h`.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"\u274C An error occurred: {e}", ephemeral=True)

@tree.command(name="checktimers", description="Check your active timers.")
async def checktimers(interaction: discord.Interaction):
    user_timers = [
        f"\u23F3 Timer #{tid} ends at <t:{int(timer['end'].timestamp())}:R>"
        for tid, timer in timers.items()
        if timer["user"].id == interaction.user.id
    ]
    
    if user_timers:
        await interaction.response.send_message("\n".join(user_timers), ephemeral=True)
    else:
        await interaction.response.send_message("\u274C You have no active timers.", ephemeral=True)

@tree.command(name="endtimer", description="Cancel a running timer by ID.")
@app_commands.describe(timer_id="ID of the timer to cancel")
async def endtimer(interaction: discord.Interaction, timer_id: int):
    timer = timers.get(timer_id)
    if not timer:
        await interaction.response.send_message("\u274C Timer not found.", ephemeral=True)
        return

    if timer["user"].id != interaction.user.id:
        await interaction.response.send_message("\u26D4 You can only end your own timers.", ephemeral=True)
        return

    del timers[timer_id]
    await interaction.response.send_message(f"\u23F9 Timer #{timer_id} has been cancelled.", ephemeral=True)

    @app_commands.command(name="verify", description="Start verification")
    async def verify(self, interaction: discord.Interaction):
        config = verify_config.get(str(interaction.guild.id))
        if not config:
            await interaction.response.send_message("❌ Verification has not been configured.", ephemeral=True)
            return

        if interaction.channel.id != config["channel_id"]:
            await interaction.response.send_message("❌ Use this in the verification channel.", ephemeral=True)
            return

        code = ''.join(random.choices('0123456789', k=6))
        user_input = ""

        class KeypadView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=120)

            async def update_message(self, interaction):
                await interaction.response.edit_message(
                    content=f"**🔐 Code:** `{code}`\n**🔢 Your input:** `{user_input}`",
                    view=self
                )

            async def submit(self, interaction):
                if user_input == code:
                    role = interaction.guild.get_role(config["role_id"])
                    if role:
                        await interaction.user.add_roles(role)
                        await interaction.response.edit_message(content="✅ You are now verified!", view=None)
                    else:
                        await interaction.response.edit_message(content="❌ Verified role not found.", view=None)
                else:
                    await interaction.response.edit_message(content="❌ Incorrect code. Try again with /verify.", view=None)

            @discord.ui.button(label="1", style=discord.ButtonStyle.secondary, row=0)
            async def one(self, interaction, _):
                nonlocal user_input; user_input += "1"; await self.update_message(interaction)
            @discord.ui.button(label="2", style=discord.ButtonStyle.secondary, row=0)
            async def two(self, interaction, _):
                nonlocal user_input; user_input += "2"; await self.update_message(interaction)
            @discord.ui.button(label="3", style=discord.ButtonStyle.secondary, row=0)
            async def three(self, interaction, _):
                nonlocal user_input; user_input += "3"; await self.update_message(interaction)
            @discord.ui.button(label="4", style=discord.ButtonStyle.secondary, row=1)
            async def four(self, interaction, _):
                nonlocal user_input; user_input += "4"; await self.update_message(interaction)
            @discord.ui.button(label="5", style=discord.ButtonStyle.secondary, row=1)
            async def five(self, interaction, _):
                nonlocal user_input; user_input += "5"; await self.update_message(interaction)
            @discord.ui.button(label="6", style=discord.ButtonStyle.secondary, row=1)
            async def six(self, interaction, _):
                nonlocal user_input; user_input += "6"; await self.update_message(interaction)
            @discord.ui.button(label="7", style=discord.ButtonStyle.secondary, row=2)
            async def seven(self, interaction, _):
                nonlocal user_input; user_input += "7"; await self.update_message(interaction)
            @discord.ui.button(label="8", style=discord.ButtonStyle.secondary, row=2)
            async def eight(self, interaction, _):
                nonlocal user_input; user_input += "8"; await self.update_message(interaction)
            @discord.ui.button(label="9", style=discord.ButtonStyle.secondary, row=2)
            async def nine(self, interaction, _):
                nonlocal user_input; user_input += "9"; await self.update_message(interaction)
            @discord.ui.button(label="0", style=discord.ButtonStyle.secondary, row=3)
            async def zero(self, interaction, _):
                nonlocal user_input; user_input += "0"; await self.update_message(interaction)
            @discord.ui.button(label="Clear", style=discord.ButtonStyle.danger, row=3)
            async def clear(self, interaction, _):
                nonlocal user_input; user_input = ""; await self.update_message(interaction)
            @discord.ui.button(label="Submit", style=discord.ButtonStyle.success, row=3)
            async def submit_btn(self, interaction, _):
                await self.submit(interaction)

        await interaction.response.send_message(
            content=f"**🔐 Code:** `{code}`\n**🔢 Your input:** ``",
            view=KeypadView(),
            ephemeral=True
        )

class SayView(discord.ui.View):
    def __init__(self, guild):
        super().__init__(timeout=None)
        self.guild = guild
        self.channel_select = discord.ui.Select(
            placeholder="Choose a channel to send message",
            options=[
                discord.SelectOption(label=channel.name, value=str(channel.id))
                for channel in guild.text_channels if channel.permissions_for(guild.me).send_messages
            ]
        )
        self.channel_select.callback = self.select_channel
        self.add_item(self.channel_select)

        self.message_input = discord.ui.TextInput(label="Message", style=discord.TextStyle.paragraph)
        self.modal = discord.ui.Modal(title="Type your message")
        self.modal.add_item(self.message_input)
        self.modal.on_submit = self.send_message

    async def select_channel(self, interaction: discord.Interaction):
        self.selected_channel = self.guild.get_channel(int(self.channel_select.values[0]))
        await interaction.response.send_modal(self.modal)

    async def send_message(self, interaction: discord.Interaction):
        await self.selected_channel.send(self.message_input.value)
        await interaction.response.send_message("✅ Message sent!", ephemeral=True)


class DmView(discord.ui.View):
    def __init__(self, guild):
        super().__init__(timeout=None)
        self.guild = guild
        self.member_select = discord.ui.Select(
            placeholder="Choose a user to DM",
            options=[
                discord.SelectOption(label=member.display_name, value=str(member.id))
                for member in guild.members if not member.bot
            ][:25]  # Limit to 25 users
        )
        self.member_select.callback = self.select_member
        self.add_item(self.member_select)

        self.message_input = discord.ui.TextInput(label="Message", style=discord.TextStyle.paragraph)
        self.modal = discord.ui.Modal(title="Type your DM")
        self.modal.add_item(self.message_input)
        self.modal.on_submit = self.send_dm

    async def select_member(self, interaction: discord.Interaction):
        self.selected_user = self.guild.get_member(int(self.member_select.values[0]))
        await interaction.response.send_modal(self.modal)

    async def send_dm(self, interaction: discord.Interaction):
        try:
            await self.selected_user.send(f"📬 **Message from staff:**\n{self.message_input.value}")
            await interaction.response.send_message("✅ Message sent!", ephemeral=True)
            if 'log_action' in globals():
                await log_action(interaction, f"📨 **DM sent** to {self.selected_user.mention} by {interaction.user.mention} - Content: {self.message_input.value}")
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

from discord.ui import Button, View
from discord import Interaction

class Keypad(View):
    def __init__(self, code, user, ctx):
        super().__init__(timeout=300)  # 5 min timeout
        self.code = code
        self.user = user
        self.ctx = ctx
        self.input = ""
        self.message = None  # DM message object to edit

        # Create 3x4 grid of number buttons (1-9, 0, Clear, Submit)
        rows = [
            ['1', '2', '3'],
            ['4', '5', '6'],
            ['7', '8', '9'],
            ['Clear', '0', 'Submit']
        ]

        for row in rows:
            for label in row:
                style = discord.ButtonStyle.secondary
                if label == "Submit":
                    style = discord.ButtonStyle.success
                elif label == "Clear":
                    style = discord.ButtonStyle.danger

                self.add_item(NumberButton(label=label, view=self, style=style))

    async def update_message(self):
        """Update the message with the current input."""
        if self.message:
            await self.message.edit(content=f"👋 Enter the **6-digit code**:\n`{self.code}`\n🔢 Numbers Typed: `{self.input}`", view=self)


class NumberButton(Button):
    def __init__(self, label, view, style):
        super().__init__(label=label, style=style)
        self.custom_view = view

    async def callback(self, interaction: Interaction):
        if interaction.user != self.custom_view.user:
            await interaction.response.send_message("❌ This keypad isn't for you.", ephemeral=True)
            return

        if self.label == "Clear":
            self.custom_view.input = ""
        elif self.label == "Submit":
            if self.custom_view.input == self.custom_view.code:
                await interaction.response.send_message("✅ Verification successful!")
                await self.custom_view.message.delete()
                self.custom_view.stop()
            else:
                await interaction.response.send_message("❌ Incorrect code. Try again.", ephemeral=True)
                self.custom_view.input = ""
        else:
            if len(self.custom_view.input) < 6:
                self.custom_view.input += self.label

        await self.custom_view.update_message()

from discord.ext import commands, tasks

@tree.command(name="autorole", description="Configure or manage autoroles.")
async def autorole(interaction: discord.Interaction):
    guild_id = str(interaction.guild.id)
    config = autorole_config.get(guild_id, {})

    embed = discord.Embed(title="📋 Current Autorole Settings", color=discord.Color.gold())
    if config:
        for event, role_ids in config.items():
            role_mentions = [interaction.guild.get_role(rid).mention for rid in role_ids if interaction.guild.get_role(rid)]
            embed.add_field(name=event.replace('_', ' ').title(), value=", ".join(role_mentions), inline=False)
    else:
        embed.description = "No autoroles configured yet."

    await interaction.response.send_message(
        embed=embed,
        view=AutoRoleView(interaction.guild),
        ephemeral=True
    )

@tree.command(name="setautorole", description="Set a role to be added or removed automatically.")
@app_commands.describe(
    role="Role to be auto-managed",
    event="When to apply the role (on_join, on_message, on_thread)",
    action="Add or remove the role"
)
async def setautorole(interaction: discord.Interaction, role: discord.Role, event: str, action: str):
    if event not in ["on_join", "on_message", "on_thread"]:
        await interaction.response.send_message(
            "❌ Invalid event type. Choose from: on_join, on_message, on_thread.",
            ephemeral=True
        )
        return

    if action not in ["add", "remove"]:
        await interaction.response.send_message(
            "❌ Invalid action. Choose 'add' or 'remove'.",
            ephemeral=True
        )
        return

    autorole_config[str(interaction.guild.id)] = {
        "role_id": role.id,
        "event": event,
        "action": action
    }

    await interaction.response.send_message(
        f"✅ Autorole set to {action} {role.name} on {event}.",
        ephemeral=True
    )


@tree.command(name="say", description="Send a message as the bot to a specific channel")
async def say(interaction: discord.Interaction):
    await interaction.response.send_message("Select a channel to send a message:", view=SayView(interaction.guild), ephemeral=True)


@tree.command(name="dm", description="Send a DM as the bot")
async def dm(interaction: discord.Interaction):
    await interaction.response.send_message("Select a user to DM:", view=DmView(interaction.guild), ephemeral=True)


@tree.command(name="poll", description="Create a poll")
@app_commands.describe(question="The poll question", duration_minutes="How many minutes the poll will last")
async def poll(interaction: discord.Interaction, question: str, duration_minutes: int):
    class PollChannelSelect(discord.ui.Select):
        def __init__(self):
            options = [
                discord.SelectOption(label=channel.name, value=str(channel.id))
                for channel in interaction.guild.text_channels if channel.permissions_for(interaction.guild.me).send_messages
            ][:25]
            super().__init__(placeholder="Select a channel to send the poll to...", options=options)

        async def callback(self, i: discord.Interaction):
            channel = interaction.guild.get_channel(int(self.values[0]))
            embed = discord.Embed(title="📊 Poll", description=question, color=discord.Color.blue())
            embed.set_footer(text=f"Poll ends in {duration_minutes} minute(s).")
            msg = await channel.send(embed=embed)
            await msg.add_reaction("👍")
            await msg.add_reaction("👎")
            await i.response.send_message(f"✅ Poll sent to {channel.mention}", ephemeral=True)
            await asyncio.sleep(duration_minutes * 60)
            try:
                await msg.clear_reactions()
                await channel.send("🛑 Poll ended! Thanks for voting.")
            except discord.Forbidden:
                await channel.send("⚠️ I do not have permission to clear reactions.")

    class PollChannelView(discord.ui.View):
        def __init__(self):
            super().__init__()
            self.add_item(PollChannelSelect())

    await interaction.response.send_message("📊 Choose a channel to send the poll:", view=PollChannelView(), ephemeral=True)

WARNS_FILE = "warns.json"

# Load or create warns.json
if os.path.exists(WARNS_FILE):
    with open(WARNS_FILE, "r") as f:
        warns_data = json.load(f)
else:
    warns_data = {}

def save_warns():
    with open(WARNS_FILE, "w") as f:
        json.dump(warns_data, f, indent=4)

class Warns(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # /warn command
    @app_commands.command(name="warn", description="Warn a user")
    @app_commands.describe(user="User to warn", reason="Reason for the warning")
    async def warn(self, interaction: discord.Interaction, user: discord.User, reason: str):
        guild_id = str(interaction.guild_id)
        user_id = str(user.id)

        guild_warns = warns_data.setdefault(guild_id, {})
        user_warns = guild_warns.setdefault(user_id, [])
        user_warns.append({"reason": reason, "warned_by": interaction.user.id})

        save_warns()

        await interaction.response.send_message(
            f"⚠️ {user.mention} has been warned.\n**Reason:** {reason}",
            ephemeral=False
        )

    # /listwarns command
    @app_commands.command(name="listwarns", description="List all warnings for a user")
    @app_commands.describe(user="User to check warnings for")
    async def listwarns(self, interaction: discord.Interaction, user: discord.User):
        guild_id = str(interaction.guild_id)
        user_id = str(user.id)

        guild_warns = warns_data.get(guild_id, {})
        user_warns = guild_warns.get(user_id, [])

        if not user_warns:
            await interaction.response.send_message(f"✅ {user.mention} has no warnings.", ephemeral=False)
            return

        warn_list = "\n".join(
            [f"**{i+1}.** {w['reason']} (by <@{w['warned_by']}>)" for i, w in enumerate(user_warns)]
        )

        embed = discord.Embed(
            title=f"Warnings for {user}",
            description=warn_list,
            color=discord.Color.orange()
        )
        await interaction.response.send_message(embed=embed, ephemeral=False)

    # /removewarns command
    @app_commands.command(name="removewarns", description="Remove warnings from a user")
    @app_commands.describe(user="User to remove warnings from", index="Warning number (leave blank to clear all)")
    async def removewarns(self, interaction: discord.Interaction, user: discord.User, index: int | None = None):
        guild_id = str(interaction.guild_id)
        user_id = str(user.id)

        guild_warns = warns_data.get(guild_id, {})
        user_warns = guild_warns.get(user_id, [])

        if not user_warns:
            await interaction.response.send_message(f"ℹ️ {user.mention} has no warnings.", ephemeral=True)
            return

        if index is None:
            guild_warns[user_id] = []
            msg = f"🗑️ All warnings for {user.mention} have been cleared."
        else:
            if 1 <= index <= len(user_warns):
                removed = user_warns.pop(index-1)
                msg = f"🗑️ Removed warning **#{index}** from {user.mention}.\n**Reason:** {removed['reason']}"
            else:
                await interaction.response.send_message("❌ Invalid warning index.", ephemeral=True)
                return

        save_warns()
        await interaction.response.send_message(msg, ephemeral=False)

async def setup(bot: commands.Bot):
    await bot.add_cog(Warns(bot))
verify_config = {}              # guild_id -> dict with role_id, channel_id, method
reaction_verify_messages = {}  # guild_id -> verify_message_id (int)

# Load verify config from file
VERIFY_CONFIG_FILE = "verify_config.json"

# Load config
try:
    with open(VERIFY_CONFIG_FILE) as f:
        verify_config = json.load(f)
except:
    verify_config = {}
    
@tree.command(name="verify", description="Start verification")
async def verify(interaction: discord.Interaction):
    config = verify_config.get(str(interaction.guild.id))
    if not config:
        await interaction.response.send_message("❌ Verification not configured.", ephemeral=True)
        return

    if interaction.channel.id != config["channel_id"]:
        await interaction.response.send_message("❌ Use this in the verification channel.", ephemeral=True)
        return

    method = config.get("method", "keypad")

    if method == "keypad":
        await run_keypad_verify(interaction, config)
    elif method == "captcha":
        await run_captcha_verify(interaction, config)
    elif method == "button":
        await run_button_verify(interaction, config)
    elif method == "reaction":
        await interaction.response.send_message("✅ React to the verification message above.", ephemeral=True)
    else:
        await interaction.response.send_message("❌ Verification method not implemented.", ephemeral=True)

# --- Keypad Verify ---
async def run_keypad_verify(interaction, config):
    code = ''.join(random.choices('0123456789', k=6))
    user_input = ""

    class KeypadView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=120)

        async def update_message(self, interaction):
            await interaction.response.edit_message(
                content=f"**🔐 Code:** `{code}`\n**🔢 Your input:** `{user_input}`",
                view=self
            )

        async def submit(self, interaction):
            if user_input == code:
                role = interaction.guild.get_role(config["role_id"])
                await interaction.user.add_roles(role)
                await interaction.response.edit_message(content="✅ You are now verified!", view=None)
            else:
                await interaction.response.edit_message(content="❌ Incorrect code. Try again with /verify.", view=None)

        for digit in "1234567890":
            self.add_item(discord.ui.Button(label=digit, style=discord.ButtonStyle.secondary, custom_id=digit))

        @discord.ui.button(label="Clear", style=discord.ButtonStyle.danger, row=3)
        async def clear(self, interaction, _):
            nonlocal user_input
            user_input = ""
            await self.update_message(interaction)

        @discord.ui.button(label="Submit", style=discord.ButtonStyle.success, row=3)
        async def submit_btn(self, interaction, _):
            await self.submit(interaction)

    async def button_callback(interaction):
        nonlocal user_input
        user_input += interaction.data["custom_id"]
        await view.update_message(interaction)

    view = KeypadView()
    for item in view.children:
        if isinstance(item, discord.ui.Button) and item.custom_id.isdigit():
            item.callback = button_callback

    await interaction.response.send_message(
        content=f"**🔐 Code:** `{code}`\n**🔢 Your input:** ``",
        view=view,
        ephemeral=True
    )

# --- Captcha Verify ---
async def run_captcha_verify(interaction, config):
    num1 = random.randint(1, 9)
    num2 = random.randint(1, 9)
    answer = num1 + num2

    class CaptchaView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=60)

        @discord.ui.button(label="Submit", style=discord.ButtonStyle.success)
        async def submit(self, interaction_inner: discord.Interaction, _):
            if self.children[1].value and self.children[1].value.strip().isdigit():
                if int(self.children[1].value) == answer:
                    role = interaction.guild.get_role(config["role_id"])
                    await interaction.user.add_roles(role)
                    await interaction_inner.response.edit_message(content="✅ Captcha solved! You're verified!", view=None)
                else:
                    await interaction_inner.response.edit_message(content="❌ Incorrect. Try again with /verify.", view=None)

        @discord.ui.TextInput(label="What is {} + {}?".format(num1, num2), style=discord.TextStyle.short, required=True)
        async def answer_input(self, value: str):
            pass

    view = CaptchaView()
    await interaction.response.send_message("🧠 Solve the captcha below to verify:", view=view, ephemeral=True)

# --- Button Verify ---
async def run_button_verify(interaction, config):
    class ButtonView(discord.ui.View):
        @discord.ui.button(label="Click to Verify", style=discord.ButtonStyle.success)
        async def verify_button(self, interaction_inner: discord.Interaction, _):
            role = interaction.guild.get_role(config["role_id"])
            await interaction.user.add_roles(role)
            await interaction_inner.response.edit_message(content="✅ You are now verified!", view=None)

    await interaction.response.send_message("✅ Click the button below to verify:", view=ButtonView(), ephemeral=True)

# --- Reaction Role Setup ---
@tree.command(name="sendverifyreaction", description="Send verification embed with reaction")
async def sendverifyreaction(interaction: discord.Interaction):
    config = verify_config.get(str(interaction.guild.id))
    if not config:
        await interaction.response.send_message("❌ Not configured.", ephemeral=True)
        return

    embed = discord.Embed(
        title="✅ Verify Yourself",
        description="React with ✅ to get verified!",
        color=discord.Color.green()
    )
    msg = await interaction.channel.send(embed=embed)
    await msg.add_reaction("✅")

    # Save message ID to config
    config["reaction_message_id"] = msg.id
    with open(VERIFY_CONFIG_FILE, "w") as f:
        json.dump(verify_config, f, indent=4)

    await interaction.response.send_message("✅ Verification message sent.", ephemeral=True)

# --- Reaction Listener ---
@commands.Cog.listener()
async def on_raw_reaction_add(payload):
    if payload.member is None or payload.member.bot:
        return

    config = verify_config.get(str(payload.guild_id))
    if not config or config.get("method") != "reaction":
        return

    if payload.message_id != config.get("reaction_message_id"):
        return

    if str(payload.emoji) == "✅":
        guild = await bot.fetch_guild(payload.guild_id)
        member = guild.get_member(payload.user_id)
        role = guild.get_role(config["role_id"])
        if role and member:
            await member.add_roles(role)

# --- Config Command ---
class Verification(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="verifyconfig", description="Configure the verification system.")
    @app_commands.describe(method="Verification method")
    @app_commands.choices(method=[
        app_commands.Choice(name="Keypad", value="keypad"),
        app_commands.Choice(name="Captcha", value="captcha"),
        app_commands.Choice(name="Reaction", value="reaction"),
        app_commands.Choice(name="Button", value="button"),
    ])
    async def verifyconfig(self, interaction: discord.Interaction, method: app_commands.Choice[str]):
        guild_id = str(interaction.guild.id)

        # Save the chosen method to your verification config (assumes JSON dict structure)
        with open("verification_config.json", "r") as f:
            config = json.load(f)

        if guild_id not in config:
            config[guild_id] = {}

        config[guild_id]["method"] = method.value

        with open("verification_config.json", "w") as f:
            json.dump(config, f, indent=4)

        await interaction.response.send_message(f"✅ Verification method set to `{method.name}`.", ephemeral=True)

@bot.event
async def on_raw_reaction_add(payload):
    if payload.user_id == bot.user.id:
        return

    with open("verify_config.json", "r") as f:
        data = json.load(f)

    guild_id = str(payload.guild_id)
    if guild_id not in data["guilds"]:
        return

    config = data["guilds"][guild_id]
    if not config.get("enabled") or config.get("method") != "reaction":
        return

    if str(payload.message_id) != config["reaction"].get("message_id"):
        return

    if str(payload.emoji.name) != config["reaction"].get("emoji", "✅"):
        return

    guild = bot.get_guild(payload.guild_id)
    member = guild.get_member(payload.user_id)
    role = guild.get_role(int(config["verified_role"]))
    if role and member:
        await member.add_roles(role, reason="Verified via reaction")

MODQUESTIONS_FILE = "modquestions.json"

from discord import app_commands
from discord.ext import commands

class Nickname(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="nickname", description="Change Coffeecord's nickname in this server.")
    @app_commands.describe(name="The new nickname for Coffeecord.")
    async def nickname(self, interaction, name: str):
        # Check permissions
        if not interaction.guild.me.guild_permissions.manage_nicknames:
            await interaction.response.send_message("❌ I don’t have permission to change my nickname.", ephemeral=True)
            return

        try:
            await interaction.guild.me.edit(nick=name)
            await interaction.response.send_message(f"✅ Nickname changed to **{name}**")
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to change nickname: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Nickname(bot))

# leveling.py

import numpy as np

from moviepy.editor import VideoFileClip


from PIL import Image, ImageDraw, ImageFont, ImageSequence

from moviepy.editor import ImageSequenceClip

# ------------------- CONFIG -------------------
XP_FILE = "xp.json"
CONFIG_FILE = "leveling.json"
BACKGROUND_FILE = "backgrounds.json"
FONT_PATH = "Roboto-Regular.ttf"
SUPPORTER_ROLE_ID = 1386795218195578930
VIDEO_SIZE = (800, 240)
CACHE_DIR = "level_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

# ------------------- JSON HELPERS -------------------
def load_json(path, default=None):
    if not os.path.exists(path):
        return default or {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default or {}

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

# ------------------- VALIDATION -------------------
async def is_valid_image(url: str):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.head(url, allow_redirects=True) as resp:
                if resp.status != 200:
                    return False
                content_type = resp.headers.get("Content-Type", "")
                return content_type.startswith("image/")
    except:
        return False

# ------------------- LEVEL BACKGROUND -------------------
@tree.command(name="levelbackground", description="Set your level card background (GIF for supporters)")
@app_commands.describe(url="Link to the background image or GIF")
async def levelbackground(interaction: discord.Interaction, url: str):
    uid = str(interaction.user.id)
    supporter = any(r.id == SUPPORTER_ROLE_ID for r in interaction.user.roles)

    # Validate URL
    if not await is_valid_image(url):
        return await interaction.response.send_message("❌ Invalid image URL.", ephemeral=True)
    if url.lower().endswith(".gif") and not supporter:
        return await interaction.response.send_message("🚫 Only supporters can use GIF backgrounds.", ephemeral=True)

    # Save to JSON
    bg_data = load_json(BACKGROUND_FILE, {})
    bg_data[uid] = url
    save_json(BACKGROUND_FILE, bg_data)

    await interaction.response.send_message("✅ Background updated successfully!", ephemeral=True)

# ------------------- LEVEL COMMAND -------------------
@tree.command(name="level", description="Show your or another user's level card.")
async def level(interaction: discord.Interaction, user: discord.Member = None):
    user = user or interaction.user
    guild_id = str(interaction.guild.id)
    user_id = str(user.id)

    # Load XP and background data
    xp_data = load_json(XP_FILE, {})
    backgrounds = load_json(BACKGROUND_FILE, {})

    user_data = xp_data.get(guild_id, {}).get(user_id, {"xp": 0, "level": 1})
    xp = user_data.get("xp", 0)
    level = user_data.get("level", 1)
    xp_needed = user_data.get("next_level_xp", (level * 100) + 100)  # Use next_level_xp if present
    progress = min(xp / xp_needed, 1.0)

    bg_url = backgrounds.get(user_id, "https://i.imgur.com/6z6kKlg.png")
    supporter = any(r.id == SUPPORTER_ROLE_ID for r in user.roles)

    await interaction.response.defer()

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(bg_url) as resp:
                if resp.status != 200:
                    return await interaction.followup.send("❌ Failed to download background.", ephemeral=True)
                bg_bytes = await resp.read()
    except Exception as e:
        return await interaction.followup.send(f"❌ Error loading background: {e}", ephemeral=True)

    # Handle GIFs
    try:
        if bg_url.lower().endswith(".gif") and supporter:
            bg = Image.open(BytesIO(bg_bytes))
            frames = [frame.convert("RGBA").resize((800, 240)) for frame in ImageSequence.Iterator(bg)]
            duration = bg.info.get("duration", 100)
        else:
            bg = Image.open(BytesIO(bg_bytes)).convert("RGBA").resize((800, 240))
            frames = [bg]
            duration = 100
    except Exception as e:
        return await interaction.followup.send(f"❌ Could not open background: {e}", ephemeral=True)

    # Get avatar and make it round
    try:
        avatar_bytes = await user.display_avatar.replace(size=128).read()
        avatar = Image.open(BytesIO(avatar_bytes)).convert("RGBA").resize((128, 128))
        mask = Image.new("L", avatar.size, 0)
        draw_mask = ImageDraw.Draw(mask)
        draw_mask.ellipse((0, 0, 128, 128), fill=255)
        avatar.putalpha(mask)
    except Exception as e:
        avatar = None
        print(f"Avatar error: {e}")

    # Calculate server rank
    guild_xp = xp_data.get(guild_id, {})
    sorted_users = sorted(guild_xp.items(), key=lambda x: x[1]["xp"], reverse=True)
    rank = next((i + 1 for i, (uid, _) in enumerate(sorted_users) if uid == user_id), 0)

    # Draw progress and overlay
    output_frames = []
    for frame in frames:
        draw = ImageDraw.Draw(frame)
        # Progress bar
        draw.rectangle((160, 190, 750, 210), fill=(50, 50, 50, 150))
        draw.rectangle((160, 190, 160 + int(590 * progress), 210), fill=(0, 200, 255, 255))
        # Avatar on left
        if avatar:
            frame.paste(avatar, (20, 50), avatar)
            # Status dot at bottom-right of avatar
            status_color = {
                discord.Status.online: (0, 255, 0),
                discord.Status.idle: (255, 165, 0),
                discord.Status.dnd: (255, 0, 0),
                discord.Status.offline: (128, 128, 128),
                discord.Status.invisible: (128, 128, 128),
            }.get(user.status, (128, 128, 128))
            draw.ellipse((120, 130, 140, 150), fill=status_color)
        # Text
        try:
            font = ImageFont.truetype(FONT_PATH, 26)
        except:
            font = ImageFont.load_default()
        draw.text((160, 50), user.display_name, font=font, fill=(255, 255, 255))
        draw.text((160, 90), f"Level {level} | Rank #{rank}", font=font, fill=(255, 255, 255))
        draw.text((160, 130), f"XP: {xp}/{xp_needed}", font=font, fill=(220, 220, 220))
        output_frames.append(frame)

    # Save
    temp_path = os.path.join(CACHE_DIR, f"{user_id}_level.gif" if bg_url.lower().endswith(".gif") else f"{user_id}_level.png")
    if bg_url.lower().endswith(".gif") and supporter:
        output_frames[0].save(
            temp_path,
            save_all=True,
            append_images=output_frames[1:],
            duration=duration,
            loop=0,
            disposal=2
        )
    else:
        output_frames[0].save(temp_path)

    await interaction.followup.send(file=discord.File(temp_path))
    os.remove(temp_path)
# ------------------- XP SET -------------------
@tree.command(name="xpset", description="Set a user's XP and level (Admin only)")
@app_commands.describe(user="User", xp="XP value", level="Level value")
@app_commands.checks.has_permissions(manage_guild=True)
async def xpset(interaction: discord.Interaction, user: discord.Member, xp: int, level: int):
    guild_id = str(interaction.guild.id)
    user_id = str(user.id)
    xp_data = load_json(XP_FILE, {})
    if guild_id not in xp_data:
        xp_data[guild_id] = {}
    xp_data[guild_id][user_id] = {"xp": xp, "level": level}
    save_json(XP_FILE, xp_data)
    await interaction.response.send_message(f"✅ Set {user.display_name}'s XP to {xp} and Level to {level}.", ephemeral=True)

# ------------------- XP CONFIG -------------------
@tree.command(name="xp_config", description="Configure XP gain and leveling settings for your server (Admin only)")
@app_commands.describe(
    message_xp="XP gained per message",
    reaction_xp="XP gained per reaction",
    vc_minute_xp="XP gained per minute in VC",
    poll_vote_xp="XP gained per poll vote",
    base_xp="XP required for Level 1",
    xp_scale="XP scaling factor (how much more XP per level)"
)
@app_commands.checks.has_permissions(manage_guild=True)
async def xp_config(
    interaction: discord.Interaction,
    message_xp: int,
    reaction_xp: int,
    vc_minute_xp: int,
    poll_vote_xp: int,
    base_xp: int,
    xp_scale: float
):
    cfg = load_json(CONFIG_FILE, {})
    guild_id = str(interaction.guild.id)

    # Save the new settings
    cfg[guild_id] = {
        "message_xp": message_xp,
        "reaction_xp": reaction_xp,
        "vc_minute_xp": vc_minute_xp,
        "poll_vote_xp": poll_vote_xp,
        "base_xp": base_xp,
        "xp_scale": xp_scale
    }
    save_json(CONFIG_FILE, cfg)

    # --- XP Preview Function ---
    def xp_required_for_level(level, base_xp, xp_scale):
        total_xp = 0
        for i in range(1, level + 1):
            total_xp += base_xp * (xp_scale ** (i - 1))
        return int(total_xp)

    # --- Generate Preview ---
    preview_levels = [1, 2, 3, 5, 10]
    preview = "\n".join(
        [f"Level {lvl}: {xp_required_for_level(lvl, base_xp, xp_scale)} XP total" for lvl in preview_levels]
    )

    embed = discord.Embed(
        title="✅ XP Configuration Updated!",
        description=(
            f"**Message XP:** {message_xp}\n"
            f"**Reaction XP:** {reaction_xp}\n"
            f"**VC XP/min:** {vc_minute_xp}\n"
            f"**Poll Vote XP:** {poll_vote_xp}\n"
            f"**Base XP (Lvl 1):** {base_xp}\n"
            f"**XP Scale:** {xp_scale}\n\n"
            f"📊 **XP Preview:**\n{preview}"
        ),
        color=discord.Color.green()
    )

    await interaction.response.send_message(embed=embed, ephemeral=True)

@tree.command(name="abracadaberamotherafu", description="💥 Casts a mighty spell of a BIG TANK gun from Toefingers tank on a tank!")
async def abracadaberamotherafu(interaction: discord.Interaction):
    gif_url = "https://i.imgur.com/gXB0LAh.gif"  # Epic tank explosion GIF
    message = f"🪄 **ABRACADABERA MOTHERAFU—**\n{interaction.user.mention} just nuked a tank into the next dimension! 💥🚓🔥"

    await interaction.response.send_message(message)
    await interaction.followup.send(gif_url)

MODQUESTIONS_FILE = "modquestions.json"

def load_json(path, default=None):
    if not os.path.exists(path):
        return default if default is not None else {}
    try:
        with open(path, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return default if default is not None else {}

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

mod_questions = load_json(MODQUESTIONS_FILE, {})      # guild‑scoped dict

# ─── helpers --------------------------------------------------------------
def gcfg(gid: str):
    """Ensure & return this guild's config dict."""
    return mod_questions.setdefault(gid, {
        "enabled": True,
        "channel_id": None,
        "review_role": None,
        "pass_role": None,
        "questions": []
    })

def save():  save_json(MODQUESTIONS_FILE, mod_questions)

def fmt_qs(qs: list[str]) -> str:
    return "\n".join(f"`{i+1}.` {q}" for i, q in enumerate(qs)) or "*no questions yet*"

class StaffAppGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="application", description="Staff application commands")

    @app_commands.command(name="toggle", description="Toggle staff applications on or off")
    async def toggle(self, interaction: discord.Interaction):
        # Your toggle logic here
        await interaction.response.send_message("Toggled staff applications!", ephemeral=True)

    @app_commands.command(name="addquestion", description="Add a staff application question")
    async def add_question(self, interaction: discord.Interaction, question: str):
        # Add question logic here
        await interaction.response.send_message(f"Added question: {question}", ephemeral=True)

        #  /staffapp question remove -------------------------------------------
    @app_commands.command(name="question_remove", description="Remove a question")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def question_remove(self, interaction: discord.Interaction):
        qs = gcfg(str(interaction.guild_id))["questions"]
        if not qs:
            return await interaction.response.send_message(
                "ℹ️ No questions set.", ephemeral=True)

        # dropdown with questions
        class QSelect(discord.ui.Select):
            def __init__(self):
                options=[discord.SelectOption(label=f"{i+1}. {q[:90]}",
                                              value=str(i)) for i,q in enumerate(qs)]
                super().__init__(placeholder="Pick question to delete",
                                 min_values=1, max_values=1, options=options)

            async def callback(self, inter: discord.Interaction):
                idx=int(self.values[0])
                removed=qs.pop(idx); save()
                await inter.response.edit_message(
                    content=f"🗑 Removed:\n> {removed}", view=None)

        view = discord.ui.View(timeout=60)
        view.add_item(QSelect())
        await interaction.response.send_message("Select question to delete:", view=view, ephemeral=True)

          #  /staffapp question list ---------------------------------------------
    @app_commands.command(name="question_list", description="List current questions")
    async def question_list(self, interaction: discord.Interaction):
        qs = gcfg(str(interaction.guild_id))["questions"]
        await interaction.response.send_message(
            "📋 **Current questions:**\n" + fmt_qs(qs), ephemeral=True)
        
        #  /staffapp setup  -----------------------------------------------------
    @app_commands.command(name="application_setup", description="Set channel & roles")
    @app_commands.describe(
        channel="Channel where applicants will run /application",
        reviewer_role="Role notified of new applications",
        pass_role="Role granted when an application is approved")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def setup(self, interaction: discord.Interaction,
                    channel:      discord.TextChannel,
                    reviewer_role: discord.Role,
                    pass_role:     discord.Role):
        cfg = gcfg(str(interaction.guild_id))
        cfg.update(channel_id=channel.id,
                   review_role=reviewer_role.id,
                   pass_role=pass_role.id)
        save()
        await interaction.response.send_message(
            "✅ Staff‑application system configured.", ephemeral=True)    

async def setup(bot: commands.Bot):
    await bot.add_cog(StaffAppGroup())  # Required if StaffAppGroup is a cog (inheriting from commands.Cog)
    bot.tree.add_command(StaffAppGroup())  # Required if you're registering the command group manually

def get_staff_cfg(guild_id: str) -> dict:
    return staff_app_cfg.setdefault(guild_id, {
        "enabled": False,
        "questions": [],
        "review_channel_id": None,
        "reviewer_role_id": None
    })

def load_json(filename, default=None):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    return default or {}

def save_json(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)

staff_app_cfg = load_json(STAFF_APP_FILE)

# ─────────────────────────  /application  ──────────────────────────
@tree.command(
    name="application",
    description="Start a staff‑application and answer the server’s questions",
)
async def application(interaction: discord.Interaction):
    """Ask the configured questions via DM, then forward the transcript to reviewers."""
    guild_id = str(interaction.guild_id)
    cfg      = staff_app_cfg.get(guild_id)

    # ── Sanity / permission checks ─────────────────────────────────
    if not cfg or not cfg.get("enabled", False):
        return await interaction.response.send_message(
            "❌ Staff applications are not enabled on this server.", ephemeral=True)

    if cfg.get("channel_id") and interaction.channel.id != cfg["channel_id"]:
        return await interaction.response.send_message(
            f"❌ Please use this command in <#{cfg['channel_id']}>.", ephemeral=True)

    questions: list[str] = cfg.get("questions", [])
    if not questions:
        return await interaction.response.send_message(
            "❌ No application questions have been set up yet.", ephemeral=True)

    # ── Try to open DM channel ─────────────────────────────────────
    try:
        dm = await interaction.user.create_dm()
        await dm.send(
            f"📋 **{interaction.guild.name} – Staff Application**\n"
            f"You will be asked **{len(questions)}** questions.\n"
            f"Type your answer to each and send it.  *(You have 5 minutes per question – "
            f"respond with `cancel` to abort.)*")
    except discord.Forbidden:
        return await interaction.response.send_message(
            "❌ I can’t DM you. Please enable DMs from this server and try again.", ephemeral=True)

    await interaction.response.send_message("📨 Check your DMs to begin your application!", ephemeral=True)

    answers: list[str] = []
    def dm_check(m: discord.Message):
        return m.author == interaction.user and isinstance(m.channel, discord.DMChannel)

    for idx, q in enumerate(questions, 1):
        await dm.send(f"**Q{idx}.** {q}")
        try:
            reply: discord.Message = await interaction.client.wait_for(
                "message", check=dm_check, timeout=300)
        except asyncio.TimeoutError:
            await dm.send("⌛ Time‑out – application cancelled.")
            return
        if reply.content.lower().strip() == "cancel":
            await dm.send("🚫 Application cancelled.")
            return
        answers.append(f"**Q{idx}.** {q}\n{reply.content}")

    # ── Build transcript embed ─────────────────────────────────────
    transcript = "\n\n".join(answers)
    embed = discord.Embed(
        title="📬 New Staff Application",
        description=transcript,
        colour=discord.Colour.blurple(),
    ).set_author(name=str(interaction.user), icon_url=interaction.user.display_avatar)

    # ── Dispatch to review channel / reviewers ─────────────────────
    review_channel = interaction.guild.get_channel(cfg.get("review_channel_id", 0))
    reviewer_role  = interaction.guild.get_role(cfg.get("reviewer_role_id", 0))

    sent = False
    if review_channel and review_channel.permissions_for(interaction.guild.me).send_messages:
        await review_channel.send(content=reviewer_role.mention if reviewer_role else None,
                                  embed=embed)
        sent = True

    if not sent and reviewer_role:
        # Fallback – DM every reviewer (best‑effort)
        for member in reviewer_role.members:
            try:
                await member.send(embed=embed)
                sent = True
            except discord.Forbidden:
                continue

    if sent:
        await dm.send("✅ Your application has been submitted – thank you!")
    else:
        await dm.send("⚠️ Unable to deliver your application to the staff. "
                      "Please inform an administrator.")

    # (Optional) store a copy in staff_app_cfg[guild_id]["applications"] …

def load_json(filename, default=None):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    return default or {}

def save_json(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)

import aiohttp

LEAVE_MSG = (
    "❌ Coffeecord can’t operate in servers that contain NSFW channels. "
    "The bot will now leave. Have a nice day!"
)

def guild_has_nsfw(guild: discord.Guild) -> bool:
    """Return True if *any* text channel is marked NSFW."""
    return any(
        isinstance(c, discord.TextChannel) and c.is_nsfw()
        for c in guild.channels
    )

@bot.event
async def on_guild_join(guild: discord.Guild):
    """Run when the bot is invited to a guild."""
    if guild_has_nsfw(guild):
        # Try to drop a short notice in the system channel, then bail out
        try:
            if guild.system_channel and guild.system_channel.permissions_for(guild.me).send_messages:
                await guild.system_channel.send(LEAVE_MSG)
        except Exception:
            pass   # ignore “missing perms / no send rights / etc.”
        await guild.leave()
        print(f"[NSFW‑LEAVE] Left guild {guild.name} ({guild.id}) due to NSFW channels")

# ── OPTIONAL: leave later if someone *adds* an NSFW channel ─────
@bot.event
async def on_guild_channel_update(before: discord.abc.GuildChannel,
                                  after : discord.abc.GuildChannel):
    # We only care about text‑channel NSFW flag flips while we’re still inside
    if (
        isinstance(after, discord.TextChannel)
        and not before.is_nsfw()
        and     after.is_nsfw()
    ):
        guild = after.guild
        try:
            if guild.system_channel and guild.system_channel.permissions_for(guild.me).send_messages:
                await guild.system_channel.send(LEAVE_MSG)
        except Exception:
            pass
        await guild.leave()
        print(f"[NSFW‑LEAVE] Left guild {guild.name} ({guild.id}) "
              f"because channel #{after.name} was set to NSFW")

@tree.command(name="dog", description="Get a picture of a dog (optionally by breed)")
@app_commands.describe(breed="Optional dog breed (e.g., pug, husky)")
async def dog(interaction: discord.Interaction, breed: str = None):
    await interaction.response.defer()
    url = "https://dog.ceo/api/breeds/image/random"
    if breed:
        url = f"https://dog.ceo/api/breed/{breed.lower()}/images/random"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
            if data["status"] == "success":
                await interaction.followup.send(data["message"])
            else:
                await interaction.followup.send("❌ Breed not found or error getting dog image.")

@tree.command(name="cat", description="Get a picture of a random cat")
async def cat(interaction: discord.Interaction):
    await interaction.response.defer()
    url = "https://api.thecatapi.com/v1/images/search"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
            if data:
                await interaction.followup.send(data[0]["url"])
            else:
                await interaction.followup.send("❌ Could not get a cat image.")

from petpetgif import petpet

@tree.command(name="petpet", description="Generate a petpet GIF of a user's avatar")
@app_commands.describe(member="User to petpet")
async def petpet_cmd(interaction: discord.Interaction, member: discord.Member = None):
    member = member or interaction.user
    avatar_url = member.display_avatar.replace(size=256).url
    await interaction.response.defer()

    async with aiohttp.ClientSession() as s:
        async with s.get(avatar_url) as r:
            img_bytes = await r.read()

    buf_in = io.BytesIO(img_bytes)
    buf_out = io.BytesIO()
    petpet.make(buf_in, buf_out)  # from petpetgif :contentReference[oaicite:2]{index=2}
    buf_out.seek(0)

    await interaction.followup.send(file=File(buf_out, filename="petpet.gif"))

@tree.command(name="ak47", description="Send a random AK-47 gif")
async def ak47(interaction: discord.Interaction):
    await interaction.response.send_message("https://giphy.com/gifs/cat-gun-thug-GaqnjVbSLs2uA")

from uwuify import uwu
@tree.command(name="uwuify", description="Convert text to uwu-style")
@app_commands.describe(text="Text to uwuify")
async def uwuify_cmd(interaction: discord.Interaction, text: str):
    uwu_text = uwu(text)  # simple transformation :contentReference[oaicite:5]{index=5}
    await interaction.response.send_message(f"・: {uwu_text}")

@tree.command(name="nuke", description="Send a gift... surprise! 🎁")
@app_commands.describe(member="The target of your gift")
async def nuke(interaction: discord.Interaction, member: discord.Member):
    url = "https://giphy.com/gifs/explosion-bomb-mushroom-X92pmIty2ZJp6"
    await interaction.response.send_message(f"{interaction.user.mention} gave a 🎁 to {member.mention}!\n{url}")

@tree.command(name="roast", description="Send a random roast")
async def roast(interaction: discord.Interaction):
    roasts = [
        "You're as bright as a black hole, and twice as dense.",
        "You have something on your chin… no, the third one down.",
        "You're the reason the gene pool needs a lifeguard.",
        "You bring everyone so much joy… when you leave the room.",
        "You have the perfect face for radio.",
        "You're like a cloud. When you disappear, it's a beautiful day.",
        "You're not stupid; you just have bad luck thinking.",
        "You have something on your face... oh wait, it's just your face.",
        "You're the human version of a participation trophy.",
        "You're so slow, it takes you an hour to cook minute rice.",
        "You’re not lazy, you’re just in energy-saving mode... permanently."
    ]
    await interaction.response.send_message(random.choice(roasts))

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

    await bot.wait_until_ready()

    try:
        synced = await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
        print(f"Synced {len(synced)} command(s) to guild {GUILD_ID}.")
    except Exception as e:
        print(f"Sync error: {e}")

# ------------------- JSON HELPERS -------------------
def load_json(filename, default=None):
    try:
        with open(filename, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default or {}

def save_json(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f, indent=4)


# ------------------- LEVEL UP CHECK -------------------
async def check_level_up(guild_id, user_id, channel):
    xp_data = load_json(XP_FILE, {})
    leveling_config = load_json(CONFIG_FILE, {})  # <- load it here
    user_data = xp_data.get(guild_id, {}).get(user_id, {"xp": 0, "level": 1, "next_level_xp": 10})
    guild_config = leveling_config.get(guild_id, {})

    xp = user_data.get("xp", 0)
    level = user_data.get("level", 1)
    next_level_xp = user_data.get("next_level_xp", guild_config.get("base_xp", 10))

    if xp >= next_level_xp:
        # Level up
        user_data["level"] = level + 1
        user_data["xp"] = 0  # reset XP
        base = guild_config.get("base_xp", 10)
        scale = guild_config.get("xp_scale", 1.1)
        user_data["next_level_xp"] = int(base * (scale ** user_data["level"]))

        # Save updated data
        if guild_id not in xp_data:
            xp_data[guild_id] = {}
        xp_data[guild_id][user_id] = user_data
        save_json(XP_FILE, xp_data)

        # Announce level up
        if channel:
            await channel.send(f"🎉 <@{user_id}> has leveled up to **Level {user_data['level']}**!")

# ------------------- MESSAGE XP & And Ticket Logging-------------------
@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return

    # XP SYSTEM (your code stays exactly as-is)
    guild_id = str(message.guild.id)
    user_id = str(message.author.id)

    xp_data = load_json(XP_FILE, {})
    config = load_json(CONFIG_FILE, {})

    xp_data.setdefault(guild_id, {})
    xp_data[guild_id].setdefault(user_id, {"xp": 0, "level": 0})

    message_xp = config.get(guild_id, {}).get("message_xp", 0)
    xp_data[guild_id][user_id]["xp"] += message_xp

    save_json(XP_FILE, xp_data)
    await check_level_up(guild_id, user_id, message.channel)

    # TICKET MESSAGE LOGGING
    tickets_data = load_json(TICKETS_FILE, {})
    guild_tickets = tickets_data.get(guild_id, {}).get("tickets", {})
    if str(message.channel.id) in guild_tickets:
        guild_tickets[str(message.channel.id)]["messages"].append({
            "author": str(message.author),
            "content": message.content
        })
        save_json(TICKETS_FILE, tickets_data)

    await bot.process_commands(message)

# ------------------- REACTION XP -------------------
@bot.event
async def on_reaction_add(reaction, user):
    if user.bot or not reaction.message.guild:
        return

    guild_id = str(reaction.message.guild.id)
    user_id = str(user.id)

    xp_data = load_json(XP_FILE, {})
    config = load_json(CONFIG_FILE, {})

    xp_data.setdefault(guild_id, {})
    xp_data[guild_id].setdefault(user_id, {"xp": 0, "level": 0})

    reaction_xp = config.get(guild_id, {}).get("reaction_xp", 0)
    xp_data[guild_id][user_id]["xp"] += reaction_xp

    save_json(XP_FILE, xp_data)
    await check_level_up(guild_id, user_id, reaction.message.channel)


# ------------------- VOICE XP -------------------
active_vc_members = {}  # {guild_id: {user_id: join_time}}

@bot.event
async def on_voice_state_update(member, before, after):
    guild_id = str(member.guild.id)
    user_id = str(member.id)

    # Joined VC
    if before.channel is None and after.channel is not None:
        active_vc_members.setdefault(guild_id, {})[user_id] = asyncio.get_event_loop().time()

    # Left VC
    elif before.channel is not None and after.channel is None:
        if guild_id in active_vc_members and user_id in active_vc_members[guild_id]:
            join_time = active_vc_members[guild_id].pop(user_id)
            duration = asyncio.get_event_loop().time() - join_time
            minutes = int(duration / 60)

            if minutes > 0:
                xp_data = load_json(XP_FILE, {})
                config = load_json(CONFIG_FILE, {})

                xp_data.setdefault(guild_id, {})
                xp_data[guild_id].setdefault(user_id, {"xp": 0, "level": 0})

                vc_minute_xp = config.get(guild_id, {}).get("vc_minute_xp", 0)
                gained_xp = vc_minute_xp * minutes

                xp_data[guild_id][user_id]["xp"] += gained_xp
                save_json(XP_FILE, xp_data)

                channel = discord.utils.get(member.guild.text_channels, name="general")
                if channel:
                    await check_level_up(guild_id, user_id, channel)


# ------------------- XP AUTO SAVE -------------------
@tasks.loop(minutes=5)
async def autosave_xp():
    data = load_json(XP_FILE, {})
    save_json(XP_FILE, data)
    print("💾 XP autosaved.")

@bot.event
async def on_ready():
    autosave_xp.start()
    print("✅ XP gain system loaded and running!")
    
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingAnyRole):
        await ctx.send("🚫 You don’t have permission to use that command.")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("🚫 You’re missing required permissions to run this command.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❗ Missing argument: `{error.param.name}`")
    elif isinstance(error, commands.CommandNotFound):
        pass  # Optional: silently ignore unknown commands
    else:
        # Send safe message to user
        await ctx.send("⚠️ An unexpected error occurred.")

        # Optional: log error to console only
        print(f"[ERROR] {type(error).__name__}: {error}")

@tree.command(name="synccommands", description="Force sync all commands (Owner only)")
async def sync_commands(interaction: discord.Interaction):
    if interaction.user.id != 1168282467162136656:
        await interaction.response.send_message("❌ Only the owner can run this.", ephemeral=True)
        return
    try:
        synced = await tree.sync()
        await interaction.response.send_message(f"✅ Synced {len(synced)} commands!", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Failed to sync: {e}", ephemeral=True)

@tree.command(name="debugcommands", description="Print all registered commands")
async def debug_commands(interaction: discord.Interaction):
    cmds = tree.get_commands()
    output = "\n".join(f"/{cmd.name}" for cmd in cmds)
    await interaction.response.send_message(f"Registered commands:\n```\n{output}\n```", ephemeral=True)

@tree.command(name="clearchache", description="Owner-only: Clears and resyncs all slash commands")
async def clearchache(interaction: discord.Interaction):
    if interaction.user.id != BOT_OWNER_ID:
        await interaction.response.send_message("❌ You are not authorized to use this command.", ephemeral=True)
        return

    try:
        await interaction.response.send_message("🧹 Clearing and syncing commands, please wait...", ephemeral=True)

        tree.clear_commands(guild=None)  # Clear global commands
        await tree.sync()  # Sync global commands again using your original tree

        await interaction.followup.send("✅ Global commands cleared and resynced successfully!", ephemeral=True)

    except Exception as e:
        await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)
        print(f"[Sync Error] {e}")

CALLS_FILE = "active_calls.json"

if not os.path.exists(CALLS_FILE):
    with open(CALLS_FILE, "w") as f:
        json.dump({}, f)

def load_calls():
    with open(CALLS_FILE, "r") as f:
        return json.load(f)

def save_calls(data):
    with open(CALLS_FILE, "w") as f:
        json.dump(data, f, indent=4)

# -------------------------------
# Clean up empty or inactive calls
# -------------------------------
@tasks.loop(minutes=5)
async def cleanup_calls():
    calls = load_calls()
    to_remove = []
    for guild_id, sessions in calls.items():
        for call_id, info in sessions.items():
            channel = bot.get_channel(int(info["channel_id"]))
            if not channel or len(channel.members) == 0:
                try:
                    await channel.delete(reason="Inactive CoffeeCord call")
                except Exception:
                    pass
                to_remove.append((guild_id, call_id))
    for g, c in to_remove:
        del calls[g][c]
    save_calls(calls)


# ---------------------------------------------------
# /call
# ---------------------------------------------------
@tree.command(name="call", description="Start a temporary CoffeeCord call with friends.")
@discord.app_commands.describe(users="Mention the users you want to invite (space separated)")
async def call_command(interaction: discord.Interaction, users: str = ""):
    guild = interaction.guild
    author = interaction.user

    mentions = []
    if users:
        user_ids = [u.strip("<@!>") for u in users.split()]
        for uid in user_ids:
            try:
                member = await guild.fetch_member(int(uid))
                mentions.append(member)
            except:
                pass

    if not mentions:
        await interaction.response.send_message("❌ Please mention at least one valid user.", ephemeral=True)
        return

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        author: discord.PermissionOverwrite(view_channel=True, connect=True),
    }
    for user in mentions:
        overwrites[user] = discord.PermissionOverwrite(view_channel=True, connect=True)

    category = discord.utils.get(guild.categories, name="☕ CoffeeCord Calls")
    if not category:
        category = await guild.create_category("☕ CoffeeCord Calls")

    channel = await guild.create_voice_channel(f"Call - {author.name}", overwrites=overwrites, category=category)

    calls = load_calls()
    guild_calls = calls.get(str(guild.id), {})
    guild_calls[str(channel.id)] = {
        "channel_id": str(channel.id),
        "host_id": str(author.id),
        "members": [str(m.id) for m in mentions] + [str(author.id)],
        "created_at": datetime.utcnow().isoformat(),
    }
    calls[str(guild.id)] = guild_calls
    save_calls(calls)

    await interaction.response.send_message(f"✅ Created a CoffeeCord call: {channel.mention}")

    for user in mentions:
        try:
            await user.send(f"📞 **{author.name}** started a CoffeeCord call with you!\nJoin here: {channel.mention}")
        except:
            pass


# ---------------------------------------------------
# /call_add
# ---------------------------------------------------
@tree.command(name="call_add", description="Add someone to your CoffeeCord call.")
async def call_add(interaction: discord.Interaction, user: discord.Member):
    calls = load_calls()
    for guild_id, sessions in calls.items():
        for call_id, info in sessions.items():
            if info["host_id"] == str(interaction.user.id):
                channel = interaction.guild.get_channel(int(info["channel_id"]))
                if not channel:
                    continue
                await channel.set_permissions(user, view_channel=True, connect=True)
                info["members"].append(str(user.id))
                save_calls(calls)
                await interaction.response.send_message(f"✅ Added {user.mention} to the call.")
                return
    await interaction.response.send_message("❌ You aren’t the host of any active call.", ephemeral=True)


# ---------------------------------------------------
# /call_remove
# ---------------------------------------------------
@tree.command(name="call_remove", description="Remove someone from your CoffeeCord call.")
async def call_remove(interaction: discord.Interaction, user: discord.Member):
    calls = load_calls()
    for guild_id, sessions in calls.items():
        for call_id, info in sessions.items():
            if info["host_id"] == str(interaction.user.id):
                channel = interaction.guild.get_channel(int(info["channel_id"]))
                if not channel:
                    continue
                await channel.set_permissions(user, overwrite=None)
                if str(user.id) in info["members"]:
                    info["members"].remove(str(user.id))
                save_calls(calls)
                await interaction.response.send_message(f"🚫 Removed {user.mention} from the call.")
                return
    await interaction.response.send_message("❌ You aren’t the host of any active call.", ephemeral=True)


# ---------------------------------------------------
# /call_end
# ---------------------------------------------------
@tree.command(name="call_end", description="End your CoffeeCord call.")
async def call_end(interaction: discord.Interaction):
    calls = load_calls()
    for guild_id, sessions in calls.items():
        for call_id, info in list(sessions.items()):
            if info["host_id"] == str(interaction.user.id):
                channel = interaction.guild.get_channel(int(info["channel_id"]))
                if channel:
                    await channel.delete(reason="Call ended by host")
                del calls[guild_id][call_id]
                save_calls(calls)
                await interaction.response.send_message("📞 Call ended.")
                return
    await interaction.response.send_message("❌ You don’t currently host any active call.", ephemeral=True)


# ---------------------------------------------------
# /call_promote
# ---------------------------------------------------
@tree.command(name="call_promote", description="Transfer call host role to another user.")
async def call_promote(interaction: discord.Interaction, user: discord.Member):
    calls = load_calls()
    for guild_id, sessions in calls.items():
        for call_id, info in sessions.items():
            if info["host_id"] == str(interaction.user.id):
                if str(user.id) not in info["members"]:
                    await interaction.response.send_message("❌ That user isn’t in the call.", ephemeral=True)
                    return
                info["host_id"] = str(user.id)
                save_calls(calls)
                await interaction.response.send_message(f"👑 {user.mention} is now the call host!")
                return
    await interaction.response.send_message("❌ You aren’t the host of any active call.", ephemeral=True)

@bot.event
async def on_ready():
    await tree.sync() 
    print(f"✅ Global slash commands synced.")
    print(f"🤖 Logged in as {bot.user} (ID: {bot.user.id})")

bot.run(token, log_handler=handler, log_level=logging.DEBUG)
