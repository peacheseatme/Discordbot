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

COMMAND_CATEGORIES = {
    "General": [
        "/help", "/support-us", "/date", "/say", "/dm", "/poll"
    ],
    "Yaps / Stats": [
        "/yaps"
    ],
    "Tickets": [
        "/ticket_setup", "/close"
    ],
    "Logging": [
        "/logging_on", "/logging_off", "/logging_channel", "/logging_config"
    ],
    "Moderation": [
        "/ban", "/unban", "/mute", "/unmute", "/hardmute",
        "/muterole_create", "/muterole_update",
        "/giverole", "/removerole", "/languagefilter"
    ],
    "Fun": [
        "/8ball", "/bet", "/flipcoin", "/marry", "/breakup", "/hug", "/kiss",
        "/lovecalc", "/truth", "/dare", "/uwuify", "/nuke", "/roast",
        "/ak47", "/petpet", "/dog", "/cat", "/abracadaberamotherafu"
    ],
    "Timers / Reminders": [
        "/remindme", "/starttimer", "/checktimers", "/endtimer"
    ],
    "Verification": [
        "/verify", "/sendverifyreaction"
    ],
    "Leveling": [
        "/level", "/levelbackground", "/xpset", "/xp_config",
        "/levelreward_add", "/levelreward_remove",
        "/levelreward_list", "/levelreward_mode"
    ],
    "Autorole": [
        "/autorole", "/setautorole"
    ],
    "Applications": [
        "/application"
    ],
    "Calls": [
        "/call", "/call_add", "/call_remove", "/call_end", "/call_promote"
    ],
    "Dev / Owner": [
        "/synccommands", "/debugcommands", "/clearchache",
    ]
}

class HelpMenu(discord.ui.View):
    def __init__(self, pages, index):
        super().__init__(timeout=120)
        self.pages = pages
        self.index = index

    @discord.ui.button(label="◀️", style=discord.ButtonStyle.secondary)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index = (self.index - 1) % len(self.pages)
        await interaction.response.edit_message(embed=self.pages[self.index], view=self)

    @discord.ui.button(label="▶️", style=discord.ButtonStyle.secondary)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index = (self.index + 1) % len(self.pages)
        await interaction.response.edit_message(embed=self.pages[self.index], view=self)


def build_help_pages():
    pages = []
    for category, cmds in COMMAND_CATEGORIES.items():
        embed = discord.Embed(
            title=f"📖 Help — {category}",
            description="\n".join(f"`{cmd}`" for cmd in cmds),
            color=discord.Color.blurple()
        )
        pages.append(embed)
    return pages


@bot.tree.command(name="help", description="View bot commands or search for a specific one")
@app_commands.describe(search="Search for a command name")
async def help_cmd(interaction: discord.Interaction, search: str = None):
    pages = build_help_pages()

    if search:
        search = search.lower()
        found = [cmd for cmds in COMMAND_CATEGORIES.values() for cmd in cmds if search in cmd.lower()]
        if not found:
            await interaction.response.send_message(f"❌ No commands found for `{search}`")
            return

        embed = discord.Embed(
            title=f"🔍 Search Results for: {search}",
            description="\n".join(f"`{cmd}`" for cmd in found),
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)
        return

    view = HelpMenu(pages, 0)
    await interaction.response.send_message(embed=pages[0], view=view)

class DonateView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(
            label="Support us via Ko-fi",
            url=DONATION_URL,
            style=discord.ButtonStyle.link
        ))

@tree.command(name="support-us", description="Support Coffeecord and get acces to exclusive features!")  # Optional: Only register in test server)
async def donate(interaction: discord.Interaction):
    if interaction.guild is None or interaction.guild.id != GALAXY_BOT_SERVER_ID:
        await interaction.response.send_message(
            f"❌ Please use this command in the **Coffeecord Support Server**: {PERMANENT_INVITE}",
            ephemeral=False
        )
        return

    embed = discord.Embed(
        title="Support Coffeecord! 💙",
        description=(
            "Click the button below to support us via Ko-fi.\n\n"
            "✅ Link your Discord account to Kofi and buy us a coffee or membership to support us!\n"
            "**Perks:**\n"
            "- `Supporter` role!\n"
            "- Access to a private channel!\n"
            "- Early access to new features!\n"
            "- Play Gifs in your leveling card!"
        ),
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed, view=DonateView(), ephemeral=True)

YAP_FILE = "yaps.json"

if not os.path.exists(YAP_FILE):
    with open(YAP_FILE, "w") as f:
        json.dump({"guilds": {}, "stats": {}}, f, indent=4)

def load_yaps():
    with open(YAP_FILE, "r") as f:
        return json.load(f)

def save_yaps(data):
    with open(YAP_FILE, "w") as f:
        json.dump(data, f, indent=4)


# ------------------------ COMMAND: /yaps ------------------------
@bot.tree.command(name="yaps", description="Configure auto yaps (leaderboard message)")
@app_commands.describe(channel="Where leaderboard messages will be sent", interval="Minutes between leaderboards")
async def yaps(interaction: discord.Interaction, channel: discord.TextChannel, interval: int):
    data = load_yaps()
    guild_id = str(interaction.guild.id)

    if "guilds" not in data:
        data["guilds"] = {}

    data["guilds"][guild_id] = {
        "channel": channel.id,
        "enabled": True,
        "interval_minutes": interval,
        "timer": interval
    }

    save_yaps(data)
    await interaction.response.send_message(
        f"✅ Yap leaderboard enabled in {channel.mention} every **{interval} minutes**."
    )

# ------------------------ AUTO YAP LOOP ------------------------
@tasks.loop(minutes=1)
async def auto_yap():
    data = load_yaps()
    guilds_config = data.get("guilds", {})

    for guild_id_str, config in guilds_config.items():
        if not config.get("enabled"):
            continue

        try:
            guild_id = int(guild_id_str)
        except ValueError:
            continue

        guild = bot.get_guild(guild_id)
        if guild is None:
            continue

        channel = guild.get_channel(config["channel"])
        if channel is None:
            continue

        # countdown
        config["timer"] = config.get("timer", config.get("interval_minutes", 60)) - 1
        if config["timer"] > 0:
            continue

        # reset timer
        config["timer"] = config.get("interval_minutes", 60)

        # leaderboard
        stats = data.get("stats", {}).get(guild_id_str, {})
        if not stats:
            await channel.send("Nobody has yapped yet ☕")
            continue

        # pick which leaderboard to show (rotating through daily, weekly, monthly)
        if "last_period" not in config:
            config["last_period"] = "daily"
        elif config["last_period"] == "daily":
            config["last_period"] = "weekly"
        elif config["last_period"] == "weekly":
            config["last_period"] = "monthly"
        else:
            config["last_period"] = "daily"

        period = config["last_period"]

        # sort by message count
        sorted_users = sorted(stats.items(), key=lambda x: x[1][period], reverse=True)
        top_15 = sorted_users[:15]

        leaderboard = []
        for i, (uid, counts) in enumerate(top_15, start=1):
            member = guild.get_member(int(uid))
            name = member.display_name if member else f"User {uid}"
            leaderboard.append(f"**{i}.** {name} — `{counts[period]} messages`")

        embed = discord.Embed(
            title=f"🏆 Top Yappers ({period.capitalize()})",
            description="\n".join(leaderboard) or "No messages yet!",
            color=discord.Color.orange()
        )
        embed.set_footer(text="☕ Coffeecord auto-yaps leaderboard")

        try:
            await channel.send(embed=embed)
        except Exception as e:
            print(f"[YAP] Error sending in {guild.name}: {e}")

    save_yaps(data)

# ------------------------ RESET TASKS ------------------------
@tasks.loop(hours=24)
async def reset_daily():
    data = load_yaps()
    for g in data.get("stats", {}).values():
        for u in g.values():
            u["daily"] = 0
    save_yaps(data)

@tasks.loop(hours=24*7)
async def reset_weekly():
    data = load_yaps()
    for g in data.get("stats", {}).values():
        for u in g.values():
            u["weekly"] = 0
    save_yaps(data)

@tasks.loop(hours=24*30)
async def reset_monthly():
    data = load_yaps()
    for g in data.get("stats", {}).values():
        for u in g.values():
            u["monthly"] = 0
    save_yaps(data)


from discord import app_commands, ui, Interaction

@bot.tree.command(name="purge", description="Bulk delete messages in a channel")
@app_commands.describe(
    amount="Number of messages to delete",
    channel="Channel to purge messages from",
    msg_type="Type of messages to delete (human/bot/all)"
)
async def purge(interaction: discord.Interaction, amount: int, channel: discord.TextChannel, msg_type: str):
    await interaction.response.defer(ephemeral=True)  # Give the bot more time

    def check(msg):
        if msg_type.lower() == "bot":
            return msg.author.bot
        elif msg_type.lower() == "human":
            return not msg.author.bot
        else:  # all
            return True

    deleted = await channel.purge(limit=amount, check=check)
    await interaction.followup.send(f"✅ Deleted {len(deleted)} messages from {channel.mention} ({msg_type})", ephemeral=True)
    
@bot.tree.command(name="specific_purge", description="Delete messages from a specific user")
@app_commands.describe(
    user="The user to delete messages from",
    amount="Number of messages to delete (or leave empty to delete all found)",
    channel="Channel to purge messages from"
)
async def specific_purge(interaction: discord.Interaction, user: discord.Member, channel: discord.TextChannel, amount: int = 1000):
    await interaction.response.defer(ephemeral=True)  # Let the user know the bot is processing

    warning_sent = False

    async def delete_messages():
        nonlocal warning_sent
        deleted_count = 0

        def check(msg):
            return msg.author.id == user.id

        # Fetch messages in small batches to avoid rate limits
        async for msg in channel.history(limit=amount):
            if check(msg):
                await msg.delete()
                deleted_count += 1

            # Check if 30 seconds have passed
            if not warning_sent and delete_messages.start_time and (asyncio.get_running_loop().time() - delete_messages.start_time > 30):
                await interaction.followup.send(
                    f"⏳ Sorry, this is taking a while. {user.display_name} has a lot of messages!",
                    ephemeral=True
                )
                warning_sent = True

        return deleted_count

    delete_messages.start_time = asyncio.get_running_loop().time()
    deleted_count = await delete_messages()

    await interaction.followup.send(
        f"✅ Deleted {deleted_count} messages from {user.mention} in {channel.mention}",
        ephemeral=True
    )
    
TICKETS_FILE = "tickets.json"
os.makedirs("ticket_transcripts", exist_ok=True)

# Helper functions
def load_json(path, default=None):
    if not os.path.exists(path):
        return default or {}
    with open(path, "r") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=4)


# ---------- /ticket_setup ----------
@tree.command(name="ticket_setup", description="Set up the ticket system with types")
@app_commands.describe(
    channel="Channel where the ticket panel will appear",
    support_roles="Roles that can claim tickets (comma-separated IDs or mentions)",
    ticket_type1="First ticket type name",
    ticket_type2="Second ticket type name (optional)",
    ticket_type3="Third ticket type name (optional)",
    message="Message for the ticket embed"
)
async def ticket_setup(
    interaction: Interaction,
    channel: discord.TextChannel,
    support_roles: str,
    ticket_type1: str,
    ticket_type2: str = None,
    ticket_type3: str = None,
    message: str = "Click below to create a ticket."
):
    guild_id = str(interaction.guild.id)

    # Parse roles
    roles = []
    for r in support_roles.split(","):
        r = r.strip()
        if r.startswith("<@&") and r.endswith(">"):
            rid = int(r[3:-1])
        else:
            try:
                rid = int(r)
            except ValueError:
                continue
        role = interaction.guild.get_role(rid)
        if role:
            roles.append(role)

    if not roles:
        await interaction.response.send_message("No valid roles provided!", ephemeral=True)
        return

    # Save configuration
    ticket_types = [ticket_type1]
    if ticket_type2:
        ticket_types.append(ticket_type2)
    if ticket_type3:
        ticket_types.append(ticket_type3)

    data = load_json(TICKETS_FILE, {})
    data[guild_id] = {
        "ticket_channel": channel.id,
        "support_roles": [r.id for r in roles],
        "ticket_types": ticket_types,
        "ticket_message": message,
        "tickets": {}
    }
    save_json(TICKETS_FILE, data)

    # Create the embed for the panel
    embed = discord.Embed(
        title="🎫 Support Tickets",
        description=message,
        color=discord.Color.blue()
    )

    # Create the view dynamically based on ticket types
    view = TicketPanel(guild_id)
    await channel.send(embed=embed, view=view)
    await interaction.response.send_message("✅ Ticket system set up!", ephemeral=True)


# ---------- Ticket Panel ----------
class TicketPanel(ui.View):
    def __init__(self, guild_id):
        super().__init__(timeout=None)
        self.guild_id = guild_id
        data = load_json(TICKETS_FILE, {})
        guild_data = data.get(str(guild_id), {})
        ticket_types = guild_data.get("ticket_types", [])

        # If multiple types, create dropdown; else single button
        if len(ticket_types) > 1:
            self.add_item(TicketTypeSelect(ticket_types, guild_id))
        else:
            self.add_item(CreateTicketButton(ticket_types[0], guild_id))


class TicketTypeSelect(ui.Select):
    def __init__(self, ticket_types, guild_id):
        options = [discord.SelectOption(label=t, description=f"Create a {t} ticket") for t in ticket_types]
        super().__init__(
            placeholder="Select ticket type",
            min_values=1,
            max_values=1,
            options=options,
            custom_id=f"ticket_type_select_{guild_id}"
        )
        self.guild_id = guild_id

    async def callback(self, interaction: Interaction):
        ticket_type = self.values[0]
        await create_ticket(interaction, ticket_type, str(self.guild_id))

class CreateTicketButton(ui.Button):
    def __init__(self, ticket_type, guild_id):
        super().__init__(
            style=discord.ButtonStyle.success,
            label=f"Create {ticket_type}",
            custom_id=f"create_ticket_{guild_id}_{ticket_type}"
        )
        self.ticket_type = ticket_type
        self.guild_id = guild_id

    async def callback(self, interaction: Interaction):
        await create_ticket(interaction, self.ticket_type, str(self.guild_id))

async def create_ticket(interaction: Interaction, ticket_type: str, guild_id: str):
    guild = interaction.guild
    member = interaction.user

    print(f"[Ticket] Starting create_ticket for {member} ({member.id}) in guild {guild_id}")
    if not guild:
        await interaction.response.send_message("This can only be used in a server.", ephemeral=True)
        return

    data = load_json(TICKETS_FILE, {})
    guild_data = data.get(guild_id)
    if not guild_data:
        print("[Ticket] No guild data found in JSON!")
        await interaction.response.send_message("❌ Ticket system not configured for this server.", ephemeral=True)
        return

    support_roles = guild_data.get("support_roles", [])
    ticket_message = guild_data.get("ticket_message", "A support agent will help you shortly.")
    print(f"[Ticket] Found {len(support_roles)} support roles.")

    # --- Permissions ---
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        member: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
    }

    for rid in support_roles:
        role = guild.get_role(rid)
        if role:
            overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
            print(f"[Ticket] Added role overwrite for {role.name}")
        else:
            print(f"[Ticket] Could not find role ID {rid}")

    try:
        channel_name = f"{ticket_type.lower()}-{member.name}".replace(" ", "-")[:90]
        channel = await guild.create_text_channel(
            name=channel_name,
            overwrites=overwrites,
            reason=f"{ticket_type} ticket for {member.name}"
        )
        print(f"[Ticket] Channel created: {channel.name}")
    except Exception as e:
        print(f"[Ticket ERROR] Failed to create channel: {e}")
        await interaction.response.send_message("❌ Failed to create ticket channel (check bot permissions).", ephemeral=True)
        return

    # --- Save JSON ---
    tickets = guild_data.get("tickets", {})
    tickets[str(channel.id)] = {
        "user": member.id,
        "type": ticket_type,
        "status": "open",
        "claimed_by": None
    }
    data[guild_id]["tickets"] = tickets
    save_json(TICKETS_FILE, data)
    print(f"[Ticket] Saved ticket data for {channel.id}")

    # --- Mentions ---
    role_mentions = " ".join(f"<@&{rid}>" for rid in support_roles if guild.get_role(rid))
    mention_text = f"{role_mentions} New ticket from {member.mention}!" if role_mentions else f"New ticket from {member.mention}!"
    print(f"[Ticket] Mention text ready.")

    # --- Send embed ---
    try:
        embed = discord.Embed(
            title=f"{ticket_type} Ticket",
            description=ticket_message,
            color=discord.Color.green()
        )
        embed.add_field(name="🎟️ Status", value="Open", inline=True)
        embed.add_field(name="👤 Created by", value=member.mention, inline=True)

        view = TicketControlPanel(guild_id, channel.id)
        await channel.send(content=mention_text, embed=embed, view=view)
        await interaction.response.send_message(f"✅ {ticket_type} ticket created: {channel.mention}", ephemeral=True)
        print("[Ticket] Ticket created successfully.")
    except Exception as e:
        print(f"[Ticket ERROR] Failed to send embed or message: {e}")


# ---------- Ticket Control Panel ----------
class TicketControlPanel(ui.View):
    def __init__(self, guild_id, channel_id):
        super().__init__(timeout=None)
        self.guild_id = guild_id
        self.channel_id = channel_id

        self.add_item(ClaimButton(guild_id, channel_id))
        self.add_item(LockButton(guild_id, channel_id))
        self.add_item(UnlockButton(guild_id, channel_id))
        self.add_item(CloseButton(guild_id, channel_id))
        self.add_item(DeleteButton(guild_id, channel_id))


# ---------- Buttons ----------
class ClaimButton(ui.Button):
    def __init__(self, guild_id, channel_id):
        super().__init__(label="Claim", style=discord.ButtonStyle.primary)
        self.guild_id = guild_id
        self.channel_id = channel_id

    async def callback(self, interaction: Interaction):
        data = load_json(TICKETS_FILE, {})
        ticket = data.get(self.guild_id, {}).get("tickets", {}).get(str(self.channel_id))
        if not ticket:
            await interaction.response.send_message("Ticket not found.", ephemeral=True)
            return

        if ticket.get("claimed_by"):
            await interaction.response.send_message("This ticket is already claimed.", ephemeral=True)
            return

        ticket["claimed_by"] = interaction.user.id
        save_json(TICKETS_FILE, data)
        await interaction.channel.send(f"🎟️ Ticket claimed by {interaction.user.mention}")
        await interaction.response.defer()


class LockButton(ui.Button):
    def __init__(self, guild_id, channel_id):
        super().__init__(label="Lock", style=discord.ButtonStyle.secondary)
        self.guild_id = guild_id
        self.channel_id = channel_id

    async def callback(self, interaction: Interaction):
        channel = interaction.channel
        data = load_json(TICKETS_FILE, {})
        ticket = data.get(self.guild_id, {}).get("tickets", {}).get(str(channel.id))
        if not ticket:
            await interaction.response.send_message("Ticket not found.", ephemeral=True)
            return

        user = channel.guild.get_member(ticket["user"])
        await channel.set_permissions(user, send_messages=False)
        ticket["status"] = "locked"
        save_json(TICKETS_FILE, data)
        await interaction.response.send_message("🔒 Ticket locked.", ephemeral=True)


class UnlockButton(ui.Button):
    def __init__(self, guild_id, channel_id):
        super().__init__(label="Unlock", style=discord.ButtonStyle.success)
        self.guild_id = guild_id
        self.channel_id = channel_id

    async def callback(self, interaction: Interaction):
        channel = interaction.channel
        data = load_json(TICKETS_FILE, {})
        ticket = data.get(self.guild_id, {}).get("tickets", {}).get(str(channel.id))
        if not ticket:
            await interaction.response.send_message("Ticket not found.", ephemeral=True)
            return

        user = channel.guild.get_member(ticket["user"])
        await channel.set_permissions(user, send_messages=True)
        ticket["status"] = "open"
        save_json(TICKETS_FILE, data)
        await interaction.response.send_message("🔓 Ticket unlocked.", ephemeral=True)


class CloseButton(ui.Button):
    def __init__(self, guild_id, channel_id):
        super().__init__(label="Close", style=discord.ButtonStyle.danger)
        self.guild_id = guild_id
        self.channel_id = channel_id

    async def callback(self, interaction: Interaction):
        data = load_json(TICKETS_FILE, {})
        ticket = data.get(self.guild_id, {}).get("tickets", {}).get(str(self.channel_id))
        if ticket:
            ticket["status"] = "closed"
            save_json(TICKETS_FILE, data)
        await interaction.channel.send("✅ Ticket closed.")
        await interaction.response.defer()


class DeleteButton(ui.Button):
    def __init__(self, guild_id, channel_id):
        super().__init__(label="Delete", style=discord.ButtonStyle.danger)
        self.guild_id = guild_id
        self.channel_id = channel_id

    async def callback(self, interaction: Interaction):
        await interaction.response.send_message("🗑️ Deleting channel in 5 seconds...", ephemeral=True)
        await asyncio.sleep(5)
        await interaction.channel.delete(reason="Ticket deleted by staff")

@bot.command()
async def loading(ctx):
    """Example command with a loading animation."""
    # Send initial message
    msg = await ctx.send("Processing: -")
    
    # Frames for animation
    frames = ["-", "\\", "|", "/"]
    idx = 0

    # Simulate some processing time (replace this with your actual task)
    for _ in range(20):  # number of updates
        await asyncio.sleep(0.2)  # time between frames
        await msg.edit(content=f"Processing: {frames[idx % len(frames)]}")
        idx += 1

    # Done processing
    await msg.edit(content="✅ Done!")
    await asyncio.sleep(1)
    await msg.delete()  # Remove the message after showing it's done
    
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

@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.data.get("custom_id") == "open_setup_menu":
        await interaction.response.send_message(
            "**Setup Menu**\n\n"
            "1. Run `/logging config` to choose what to track.\n"
            "2. Run `/verifyconfig` to set your verification method.\n"
            "3. Run `/autorole` if you want automatic roles.\n"
            "4. Use `/help` for the full command list.\n\n"
            "You're all set ☕",
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

# --- Load or create warns.json ---
if os.path.exists(WARNS_FILE):
    with open(WARNS_FILE, "r") as f:
        warns_data = json.load(f)
else:
    warns_data = {}

def save_warns():
    with open(WARNS_FILE, "w") as f:
        json.dump(warns_data, f, indent=4)


# ✅ /warn
@tree.command(name="warn", description="Warn a user")
@app_commands.describe(user="User to warn", reason="Reason for the warning")
async def warn(interaction: discord.Interaction, user: discord.User, reason: str):
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


# ✅ /listwarns
@tree.command(name="listwarns", description="List all warnings for a user")
@app_commands.describe(user="User to check warnings for")
async def listwarns(interaction: discord.Interaction, user: discord.User):
    guild_id = str(interaction.guild_id)
    user_id = str(user.id)

    guild_warns = warns_data.get(guild_id, {})
    user_warns = guild_warns.get(user_id, [])

    if not user_warns:
        await interaction.response.send_message(f"✅ {user.mention} has no warnings.", ephemeral=False)
        return

    warn_list = "\n".join(
    [
        f"**{i+1}.** {w['reason']} "
        f"(by {'<@'+str(w['warned_by'])+'>' if str(w.get('warned_by', 'AutoMod')).isdigit() else w.get('warned_by', w.get('moderator', 'Unknown'))})"
        for i, w in enumerate(user_warns)
    ]
    )


    embed = discord.Embed(
        title=f"Warnings for {user}",
        description=warn_list,
        color=discord.Color.orange()
    )
    await interaction.response.send_message(embed=embed, ephemeral=False)


# ✅ /removewarns
@tree.command(name="removewarns", description="Remove warnings from a user")
@app_commands.describe(
    user="User to remove warnings from",
    index="Warning number (leave blank to clear all)"
)
async def removewarns(interaction: discord.Interaction, user: discord.User, index: int | None = None):
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

def load_warnings():
    if os.path.exists(WARNS_FILE):
        with open(WARNS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_warnings(data):
    with open(WARNS_FILE, "w") as f:
        json.dump(data, f, indent=4)

def add_warning(user_id: int, guild_id: int, reason: str, moderator: str):
    """Adds a warning entry to warns.json compatible with /listwarns"""
    data = load_warnings()
    gid = str(guild_id)
    uid = str(user_id)

    if gid not in data:
        data[gid] = {}
    if uid not in data[gid]:
        data[gid][uid] = []

    # Store using same key names used by /warn command
    warning_entry = {
        "reason": reason,
        "warned_by": moderator,  # Matches /listwarns
        "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    }

    data[gid][uid].append(warning_entry)
    save_warnings(warning_entry)

VERIFY_FILE = "verify_config.json"

# ----------------------------------------
# UTILITIES
# ----------------------------------------
def load_verify_config():
    try:
        with open(VERIFY_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_verify_config(data):
    with open(VERIFY_FILE, "w") as f:
        json.dump(data, f, indent=4)


# ----------------------------------------
# 1️⃣ SIMPLE BUTTON VERIFY
# ----------------------------------------
class SimpleButtonView(discord.ui.View):
    def __init__(self, user, role, log_channel):
        super().__init__(timeout=60)
        self.user = user
        self.role = role
        self.log_channel = log_channel

    @discord.ui.button(label="Verify Me ✅", style=discord.ButtonStyle.success)
    async def verify_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user:
            return await interaction.response.send_message("❌ This isn’t for you.", ephemeral=True)
        await self.user.add_roles(self.role)
        await interaction.response.edit_message(content="✅ You’ve been verified!", view=None)
        if self.log_channel:
            await self.log_channel.send(f"✅ {self.user.mention} verified via **Simple Button**.")


async def run_button_verify(interaction, user, role, log_channel):
    await interaction.response.send_message(
        "Press the button below to verify yourself:",
        view=SimpleButtonView(user, role, log_channel),
        ephemeral=True
    )


# ----------------------------------------
# 2️⃣ KEYPAD CODE VERIFY
# ----------------------------------------
class CodeVerifyModal(discord.ui.Modal, title="Enter Verification Code"):
    def __init__(self, user, correct_code, role, log_channel):
        super().__init__(timeout=120)
        self.user = user
        self.correct_code = correct_code
        self.role = role
        self.log_channel = log_channel

        self.code_input = discord.ui.TextInput(label="Verification Code", placeholder="Enter your 4-digit code")
        self.add_item(self.code_input)

    async def on_submit(self, interaction: discord.Interaction):
        if self.code_input.value.strip() == self.correct_code:
            await self.user.add_roles(self.role)
            await interaction.response.send_message("✅ Verification successful!", ephemeral=True)
            if self.log_channel:
                await self.log_channel.send(f"✅ {self.user.mention} verified via **Code Method**.")
        else:
            await interaction.response.send_message("❌ Incorrect code. Try again later.", ephemeral=True)


class CodeVerifyView(discord.ui.View):
    def __init__(self, user, code, role, log_channel):
        super().__init__(timeout=120)
        self.user = user
        self.code = code
        self.role = role
        self.log_channel = log_channel

    @discord.ui.button(label="Enter Code 🔢", style=discord.ButtonStyle.primary)
    async def enter_code(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user:
            return await interaction.response.send_message("❌ Not your session.", ephemeral=True)
        await interaction.response.send_modal(CodeVerifyModal(self.user, self.code, self.role, self.log_channel))


async def run_code_verify(interaction, user, role, log_channel):
    code = "".join(random.choices("0123456789", k=4))
    try:
        await user.send(f"🔢 Your verification code for **{interaction.guild.name}**: `{code}`")
    except discord.Forbidden:
        return await interaction.response.send_message(
            "❌ I can’t DM you the code. Please enable DMs and try again.", ephemeral=True
        )

    await interaction.response.send_message(
        "📩 Check your DMs for the 4-digit code, then press below:",
        view=CodeVerifyView(user, code, role, log_channel),
        ephemeral=True
    )


# ------------------------------------------------
# 3️⃣ COLOR VERIFY
# ------------------------------------------------
class ColorVerifyButtons(discord.ui.View):
    def __init__(self, user, correct_color, role, log_channel):
        super().__init__(timeout=60)
        self.user = user
        self.correct_color = correct_color
        self.role = role
        self.log_channel = log_channel

        colors = ["Red", "Blue", "Green", "Yellow"]
        random.shuffle(colors)

        for color in colors:
            self.add_item(ColorButton(color, self))

class ColorButton(discord.ui.Button):
    def __init__(self, color, parent):
        super().__init__(label=color, style=discord.ButtonStyle.primary)
        self.color = color
        self.parent = parent

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.parent.user:
            return await interaction.response.send_message("❌ This isn't your verification session.", ephemeral=True)

        if self.color == self.parent.correct_color:
            await self.parent.user.add_roles(self.parent.role)
            await interaction.response.send_message(f"✅ Correct! You’ve been verified.", ephemeral=True)
            if self.parent.log_channel:
                await self.parent.log_channel.send(
                    f"✅ {self.parent.user.mention} was verified via **Color Method**."
                )
        else:
            await interaction.response.send_message("❌ Incorrect color. Try again!", ephemeral=True)


async def run_color_verify(interaction, user, role, log_channel):
    colors = ["Red", "Blue", "Green", "Yellow"]
    correct_color = random.choice(colors)

    try:
        await user.send(
            f"🎨 Your verification color for **{interaction.guild.name}** is **{correct_color}**.\n"
            f"Go back and click the **{correct_color}** button in the server!"
        )
        await interaction.response.send_message(
            "📩 I’ve sent you a DM with the color you need to click!", ephemeral=True
        )
    except discord.Forbidden:
        return await interaction.response.send_message(
            "❌ I couldn’t DM you! Please enable DMs from server members and try again.",
            ephemeral=True
        )

    view = ColorVerifyButtons(user, correct_color, role, log_channel)
    await interaction.followup.send(
        "🎨 Click the button with your assigned color to verify!", view=view, ephemeral=True
    )

# ----------------------------------------
# VERIFY START VIEW (MAIN ENTRY)
# ----------------------------------------
class VerifyStartView(discord.ui.View):
    def __init__(self, guild_id):
        super().__init__(timeout=None)
        self.guild_id = str(guild_id)

    @discord.ui.button(label="Verify Me ☕", style=discord.ButtonStyle.success, custom_id="verify_start_button")
    async def verify_me(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = load_verify_config()
        config = data.get(self.guild_id)
        if not config:
            return await interaction.response.send_message("⚙️ Verification not set up.", ephemeral=True)

        user = interaction.user
        guild = interaction.guild
        role = guild.get_role(config["verified_role"])
        log_channel = guild.get_channel(config["log_channel"])
        method = config["method"]

        if role in user.roles:
            return await interaction.response.send_message("✅ You’re already verified!", ephemeral=True)

        # Dispatch to correct method
        if method == "button":
            await run_button_verify(interaction, user, role, log_channel)
        elif method == "code":
            await run_code_verify(interaction, user, role, log_channel)
        elif method == "color":
            await run_color_verify(interaction, user, role, log_channel)
        else:
            await interaction.response.send_message("❌ Invalid verification method.", ephemeral=True)


# ----------------------------------------
# CONFIGURE VERIFICATION COMMAND
# ----------------------------------------
@tree.command(name="verifyconfig", description="Configure Coffeecord’s verification system")
@app_commands.describe(
    method="Verification method",
    verified_role="Role to give after verification",
    verify_channel="Channel to post the verification message",
    log_channel="Channel where verification events are logged"
)
@app_commands.choices(method=[
    app_commands.Choice(name="Simple Button", value="button"),
    app_commands.Choice(name="Keypad Code", value="code"),
    app_commands.Choice(name="Color Buttons", value="color"),
])
async def verifyconfig(interaction: discord.Interaction,
    method: app_commands.Choice[str],
    verified_role: discord.Role,
    verify_channel: discord.TextChannel,
    log_channel: discord.TextChannel
):
    guild_id = str(interaction.guild.id)
    data = load_verify_config()
    data[guild_id] = {
        "method": method.value,
        "verified_role": verified_role.id,
        "verify_channel": verify_channel.id,
        "log_channel": log_channel.id
    }
    save_verify_config(data)

    embed = discord.Embed(
        title="✅ Verification Configured",
        description=f"**Method:** {method.name}\n**Verified Role:** {verified_role.mention}\n"
                    f"**Verify Channel:** {verify_channel.mention}\n**Log Channel:** {log_channel.mention}",
        color=discord.Color.green()
    )
    embed.set_footer(text="Coffeecord Verification System - T.R.O.N")

    await interaction.response.send_message(embed=embed)

    try:
        await verify_channel.send(
            f"☕ Welcome to **{interaction.guild.name}**! Click below to verify:",
            view=VerifyStartView(interaction.guild.id)
        )
    except Exception as e:
        await interaction.followup.send(
            f"⚠️ I couldn’t send the message in {verify_channel.mention}.\n`{e}`",
            ephemeral=True
        )

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
    """Triggered when the bot joins a guild."""

    # --- NSFW SERVER CHECK ----
    if guild_has_nsfw(guild):
        try:
            if guild.system_channel and guild.system_channel.permissions_for(guild.me).send_messages:
                await guild.system_channel.send(
                    "⚠️ Coffeecord cannot operate in servers containing NSFW channels.\nLeaving this server."
                )
        except Exception:
            pass
        await guild.leave()
        print(f"[NSFW-LEAVE] Left guild {guild.name} ({guild.id}) due to NSFW channels")
        return

    # --- WELCOME BUTTONS CLASS ---
    class WelcomeButtons(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=None)
            # Proper way to add link buttons
            self.add_item(discord.ui.Button(
                label="Support Server",
                style=discord.ButtonStyle.link,
                url="https://discord.gg/zBpyzhNcVy"
            ))
            self.add_item(discord.ui.Button(
                label="Invite Me",
                style=discord.ButtonStyle.link,
                url="https://discord.com/oauth2/authorize?client_id=1390501770437984377&response_type=code&redirect_uri=https%3A%2F%2Fdiscord.com%2Foauth2%2Fauthorize%3Fclient_id%3D1390501770437984377&integration_type=0&scope=applications.commands+email"
            ))

        @discord.ui.button(label="Getting Started", style=discord.ButtonStyle.primary)
        async def setup_info(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.send_message(
                "**Getting Started with Coffeecord:**\n"
                "• `/logging config` — enable logging\n"
                "• `/autorole` — set automatic roles\n"
                "• `/verifyconfig` — configure verification\n"
                "• Need help? Join the support server!",
                ephemeral=True
            )

    # --- CHOOSE TARGET CHANNEL ---
    target = None

    # system channel first
    if guild.system_channel and guild.system_channel.permissions_for(guild.me).send_messages:
        target = guild.system_channel

    # fallback: first writable text channel
    if not target:
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                target = channel
                break

    if not target:
        print(f"[JOIN] Could not send welcome message in {guild.name}")
        return

    # --- SEND WELCOME MESSAGE ---
    try:
        await target.send(
            f"☕ **Thanks for inviting Coffeecord to `{guild.name}`!**\n"
            "I'm here to help with moderation, verification, leveling, applications, logging, and more.\n\n"
            "**Press a button below to get started.**",
            view=WelcomeButtons()
        )
        print(f"[JOIN] Sent welcome message in {guild.name}")
    except Exception as e:
        print(f"[JOIN ERROR] Failed to send welcome in {guild.name}: {e}")

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

LEVEL_REWARDS_FILE = "level_rewards.json"

# ---------- Helper Functions ----------
def load_json(path, default=None):
    if not os.path.exists(path):
        return default or {}
    with open(path, "r") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=4)

# ---------- /levelreward add ----------
@tree.command(name="levelreward_add", description="Add a level reward role.")
async def levelreward_add(
    interaction: discord.Interaction,
    level: int,                 # Discord will show "level" as the parameter
    role: discord.Role,          # Discord shows "role"
    message: str = "🎉 Congrats {user}, you reached level {level} and earned {role}!"  # optional
):
    guild_id = str(interaction.guild.id)
    data = load_json(LEVEL_REWARDS_FILE, {})
    guild_data = data.get(guild_id, {"rewards": {}, "replace_old_roles": False})
    guild_data["rewards"][str(level)] = {"role_id": role.id, "message": message}
    data[guild_id] = guild_data
    save_json(LEVEL_REWARDS_FILE, data)
    await interaction.response.send_message(f"✅ Added reward for level **{level}** → {role.mention}", ephemeral=True)


# ---------- /levelreward remove ----------
@tree.command(name="levelreward_remove", description="Remove a level reward role.")
async def levelreward_remove(interaction: discord.Interaction, level: int):
    guild_id = str(interaction.guild.id)
    data = load_json(LEVEL_REWARDS_FILE, {})
    if guild_id not in data or str(level) not in data[guild_id].get("rewards", {}):
        await interaction.response.send_message("❌ No reward found for that level.", ephemeral=True)
        return
    del data[guild_id]["rewards"][str(level)]
    save_json(LEVEL_REWARDS_FILE, data)
    await interaction.response.send_message(f"🗑️ Removed reward for level **{level}**.", ephemeral=True)


# ---------- /levelreward list ----------
@tree.command(name="levelreward_list", description="List all level reward roles.")
async def levelreward_list(interaction: discord.Interaction):
    guild_id = str(interaction.guild.id)
    data = load_json(LEVEL_REWARDS_FILE, {})
    guild_data = data.get(guild_id, {}).get("rewards", {})
    if not guild_data:
        await interaction.response.send_message("ℹ️ No rewards configured yet.", ephemeral=True)
        return

    desc = ""
    for lvl, info in sorted(guild_data.items(), key=lambda x: int(x[0])):
        role = interaction.guild.get_role(info["role_id"])
        desc += f"**Level {lvl}** → {role.mention if role else '❓ Missing Role'}\n"

    embed = discord.Embed(title="🎁 Level Rewards", description=desc, color=discord.Color.gold())
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ---------- /levelreward mode ----------
@tree.command(name="levelreward_mode", description="Choose whether to replace old reward roles.")
async def levelreward_mode(interaction: discord.Interaction, replace_old_roles: bool):
    guild_id = str(interaction.guild.id)
    data = load_json(LEVEL_REWARDS_FILE, {})
    guild_data = data.get(guild_id, {"rewards": {}, "replace_old_roles": False})
    guild_data["replace_old_roles"] = replace_old_roles
    data[guild_id] = guild_data
    save_json(LEVEL_REWARDS_FILE, data)

    mode_text = "✅ Now removing old reward roles." if replace_old_roles else "⚙️ Now keeping old reward roles."
    await interaction.response.send_message(mode_text, ephemeral=True)

# ---------- Integration: Grant Rewards On Level Up ----------
async def handle_level_up(member: discord.Member, new_level: int, channel: discord.TextChannel):
    data = load_json(LEVEL_REWARDS_FILE, {})
    guild_data = data.get(str(member.guild.id), {})
    rewards = guild_data.get("rewards", {})
    replace_old = guild_data.get("replace_old_roles", False)

    if str(new_level) not in rewards:
        return

    reward = rewards[str(new_level)]
    role = member.guild.get_role(reward["role_id"])
    if not role:
        return

    await member.add_roles(role)

    if replace_old:
        for lvl, info in rewards.items():
            if lvl != str(new_level):
                old_role = member.guild.get_role(info["role_id"])
                if old_role and old_role in member.roles:
                    await member.remove_roles(old_role)

    msg = reward["message"].replace("{user}", member.mention)\
                           .replace("{role}", role.mention)\
                           .replace("{level}", str(new_level))\
                           .replace("{server}", member.guild.name)

    await channel.send(msg)

# ------------------- LEVEL UP CHECK -------------------
async def check_level_up(guild_id, user_id, channel):
    xp_data = load_json(XP_FILE, {})
    leveling_config = load_json(CONFIG_FILE, {})
    rewards_data = load_json(LEVEL_REWARDS_FILE, {})  # <— added

    user_data = xp_data.get(guild_id, {}).get(user_id, {"xp": 0, "level": 1, "next_level_xp": 10})
    guild_config = leveling_config.get(guild_id, {})
    guild_rewards = rewards_data.get(guild_id, {})
    rewards = guild_rewards.get("rewards", {})
    replace_old = guild_rewards.get("replace_old_roles", False)

    xp = user_data.get("xp", 0)
    level = user_data.get("level", 1)
    next_level_xp = user_data.get("next_level_xp", guild_config.get("base_xp", 10))

    # --- Level up check ---
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

        # --- Announce level up ---
        if channel:
            await channel.send(f"🎉 <@{user_id}> has leveled up to **Level {user_data['level']}**!")

        # --- Handle Role Rewards ---
        try:
            member = channel.guild.get_member(int(user_id))
            if not member:
                return

            new_level = user_data["level"]
            if str(new_level) in rewards:
                reward = rewards[str(new_level)]
                role = channel.guild.get_role(reward["role_id"])
                if role:
                    await member.add_roles(role)

                    # Remove old reward roles if enabled
                    if replace_old:
                        for lvl, info in rewards.items():
                            if lvl != str(new_level):
                                old_role = channel.guild.get_role(info["role_id"])
                                if old_role and old_role in member.roles:
                                    await member.remove_roles(old_role)

                    # Send custom message
                    msg = reward["message"]\
                        .replace("{user}", member.mention)\
                        .replace("{role}", role.mention)\
                        .replace("{level}", str(new_level))\
                        .replace("{server}", member.guild.name)
                    await channel.send(msg)

        except Exception as e:
            print(f"[LevelRewardError] {e}")

import discord, json, os, time
from discord import app_commands
from discord.ext import commands

AUTOMOD_FILE = "automod.json"

def load_automod():
    if os.path.exists(AUTOMOD_FILE):
        with open(AUTOMOD_FILE, "r") as f:
            return json.load(f)
    return {}

def save_automod(data):
    with open(AUTOMOD_FILE, "w") as f:
        json.dump(data, f, indent=4)

automod_data = load_automod()
user_message_log = {}

# ------------------------- MODAL -------------------------
class AutoModSetup(discord.ui.Modal, title="⚙️ AutoMod Setup"):
    blocked_words = discord.ui.TextInput(
        label="Blocked Words (comma separated)",
        placeholder="badword1, badword2",
        required=False,
        style=discord.TextStyle.paragraph
    )
    max_mentions = discord.ui.TextInput(
        label="Max Mentions Allowed",
        placeholder="Example: 5",
        required=False
    )
    punish_action = discord.ui.TextInput(
        label="Punishment (warn/mute/kick/ban)",
        placeholder="warn",
        required=False
    )
    enable_spam = discord.ui.TextInput(
        label="Enable Spam Filter? (yes/no)",
        placeholder="yes or no",
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild_id)
        automod_data[guild_id] = {
            "blocked_words": [w.strip() for w in self.blocked_words.value.split(",") if w.strip()],
            "max_mentions": int(self.max_mentions.value) if self.max_mentions.value.isdigit() else 5,
            "punishment": (self.punish_action.value or "warn").lower(),
            "spam_filter": self.enable_spam.value.lower() == "yes",
            "invite_block": True,
            "enabled": True
        }
        save_automod(automod_data)

        await interaction.response.send_message(
            f"✅ AutoMod configured for **{interaction.guild.name}**!\n\n"
            f"**Blocked Words:** {', '.join(automod_data[guild_id]['blocked_words']) or 'None'}\n"
            f"**Max Mentions:** {automod_data[guild_id]['max_mentions']}\n"
            f"**Spam Filter:** {'Enabled' if automod_data[guild_id]['spam_filter'] else 'Disabled'}\n"
            f"**Punishment:** {automod_data[guild_id]['punishment'].capitalize()}",
            ephemeral=True
        )

# ------------------------- COMMAND -------------------------
@tree.command(name="automodconfig", description="Configure Coffeecord AutoMod settings for your server")
async def automod_config(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message("❌ You need **Manage Server** permissions to use this.", ephemeral=True)
        return
    await interaction.response.send_modal(AutoModSetup())

# ------------------------- PUNISHMENTS -------------------------
async def punish(message: discord.Message, reason: str, config: dict):
    action = config.get("punishment", "warn")
    guild_id = message.guild.id
    user_id = message.author.id
    moderator = "AutoMod"

    # Log the warning for the user (even if the punishment is kick/ban/mute)
    add_warning(user_id, guild_id, f"AutoMod: {reason}", moderator)

    embed = discord.Embed(
        title="🚨 AutoMod Violation",
        description=f"**User:** {message.author.mention}\n"
                    f"**Reason:** {reason}\n"
                    f"**Action:** {action.capitalize()}",
        color=discord.Color.red()
    )
    embed.set_footer(text=f"Detected by AutoMod • {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")

    await message.channel.send(embed=embed, delete_after=8)

    try:
        # DM the user if possible
        try:
            dm_embed = discord.Embed(
                title="⚠️ You have been punished",
                description=f"**Server:** {message.guild.name}\n**Reason:** {reason}\n**Action:** {action.capitalize()}",
                color=discord.Color.orange()
            )
            await message.author.send(embed=dm_embed)
        except:
            pass  # ignore DM errors (user may have DMs off)

        # Execute the configured punishment
        if action == "kick":
            await message.guild.kick(message.author, reason=reason)

        elif action == "ban":
            await message.guild.ban(message.author, reason=reason)

        elif action == "mute":
            role = discord.utils.get(message.guild.roles, name="Muted")
            if not role:
                # Try to create one if it doesn’t exist
                role = await message.guild.create_role(name="Muted", reason="AutoMod mute role")
                for channel in message.guild.channels:
                    await channel.set_permissions(role, send_messages=False, speak=False)
            await message.author.add_roles(role, reason=reason)

        elif action == "warn":
            # Already logged as a warning — no extra action
            pass

        else:
            print(f"[AutoMod] Unknown punishment type: {action}")

    except Exception as e:
        print(f"[AutoMod Error] Failed to punish {message.author}: {e}")

# ------------------------ ON_MESSAGE HANDLER ------------------------
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or not message.guild:
        return

    guild_id = str(message.guild.id)
    user_id = str(message.author.id)

    # ------------------------ MESSAGE XP SYSTEM ------------------------
    XP_FILE = "xp.json"
    CONFIG_FILE = "config.json"
    xp_data = load_json(XP_FILE, {})
    config = load_json(CONFIG_FILE, {})

    xp_data.setdefault(guild_id, {})
    xp_data[guild_id].setdefault(user_id, {"xp": 0, "level": 0})

    message_xp = config.get(guild_id, {}).get("message_xp", 5)
    xp_data[guild_id][user_id]["xp"] += message_xp

    save_json(XP_FILE, xp_data)
    await check_level_up(guild_id, user_id, message.channel)

    # ------------------------ YAPS (MESSAGE TRACKING) ------------------------
    data = load_yaps()
    if "stats" not in data:
        data["stats"] = {}

    if guild_id not in data["stats"]:
        data["stats"][guild_id] = {}

    if user_id not in data["stats"][guild_id]:
        data["stats"][guild_id][user_id] = {"daily": 0, "weekly": 0, "monthly": 0}

    # Increment counts
    for period in ["daily", "weekly", "monthly"]:
        data["stats"][guild_id][user_id][period] += 1

    save_yaps(data)

    # ------------------------ TICKET LOGGING ------------------------
    TICKETS_FILE = "tickets.json"
    tickets_data = load_json(TICKETS_FILE, {})
    guild_tickets = tickets_data.get(guild_id, {}).get("tickets", {})

    if str(message.channel.id) in guild_tickets:
        guild_tickets[str(message.channel.id)]["messages"].append({
            "author": str(message.author),
            "content": message.content,
            "timestamp": str(datetime.utcnow())
        })
        save_json(TICKETS_FILE, tickets_data)

    # ------------------------ AUTOMOD ------------------------
    automod_data = load_automod()
    config = automod_data.get(guild_id)

    if config and config.get("enabled", True):
        # Blocked words
        for word in config.get("blocked_words", []):
            if word.lower() in message.content.lower():
                await punish(message, f"Blocked word: {word}", config)
                return

        # Max mentions
        if message.mentions and len(message.mentions) > config.get("max_mentions", 5):
            await punish(message, f"Too many mentions ({len(message.mentions)})", config)
            return

        # Spam detection
        if config.get("spam_limit"):
            now = datetime.utcnow().timestamp()
            if not hasattr(bot, "recent_messages"):
                bot.recent_messages = {}
            user_msgs = bot.recent_messages.get(user_id, [])
            user_msgs = [t for t in user_msgs if now - t < 5]  # messages in last 5s
            user_msgs.append(now)
            bot.recent_messages[user_id] = user_msgs
            if len(user_msgs) > config["spam_limit"]:
                await punish(message, "Spam detected", config)
                bot.recent_messages[user_id] = []
                return

    # ------------------------ PROCESS COMMANDS ------------------------
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

import glob

active_uninstalls = {}  # guild_id -> "running"/"cancel"
MAX_CONSOLE_LINES = 20
SPINNER_FRAMES = ["-", "\\", "|", "/"]
INVITE_LINK = "https://discord.com/oauth2/authorize?client_id=1390501770437984377&scope=bot+applications.commands&permissions=8"

# Helper: ensure backups folder
os.makedirs("backups", exist_ok=True)


# ---------------- SMOOTH PROGRESS + CONSOLE ---------------- #
async def safe_msg_edit(msg, embed, view=None, console=None):
    """Try to edit message; if it fails append to console (if provided)."""
    try:
        await msg.edit(embed=embed, view=view)
    except discord.NotFound:
        if console is not None:
            console.append("[FAIL] embed edit failed: NotFound")
    except discord.Forbidden:
        if console is not None:
            console.append("[FAIL] embed edit failed: Forbidden")
    except discord.HTTPException as e:
        if console is not None:
            console.append(f"[FAIL] embed edit failed: HTTPException {type(e).__name__}")


async def smooth_progress(embed, msg, start, end, wheel_index, console, guild_id):
    """Animate progress bar and spinner between start..end. Returns updated wheel_index."""
    percent = float(start)
    step = max((end - start) / 20.0, 0.5)
    delay = 0.10

    # ensure wheel_index is an int
    if wheel_index is None:
        wheel_index = 0

    while percent < end:
        if active_uninstalls.get(guild_id) == "cancel":
            return wheel_index
        percent += step
        if percent > end:
            percent = end

        filled = int(percent // 5)
        bar = "█" * filled + "░" * (20 - filled)
        spinner = SPINNER_FRAMES[wheel_index % len(SPINNER_FRAMES)]
        wheel_index += 1

        # Build safe console text
        console_text = "\n".join(console[-MAX_CONSOLE_LINES:])
        safe_console = console_text.replace("`", "'").replace("\\", "/")

        embed.description = (
            "```\n"
            f"[{bar}] {int(percent):>3}%  {spinner}\n"
            f"{safe_console}\n"
            "```"
        )

        # attempt to edit and record failure if any
        await safe_msg_edit(msg, embed, view=None, console=console)
        await asyncio.sleep(delay)
    return wheel_index


# ---------------- BACKUP ---------------- #
def backup_guild_data(guild_id):
    backup = {}
    for file in glob.glob("*.json"):
        try:
            with open(file, "r") as f:
                data = json.load(f)
            if str(guild_id) in data:
                backup[file] = {str(guild_id): data[str(guild_id)]}
        except Exception:
            continue
    return backup


def save_backup_to_disk(guild_id, backup):
    if not backup:
        return None
    path = f"backups/{guild_id}.json"
    try:
        with open(path, "w") as f:
            json.dump(backup, f, indent=4)
        return path
    except Exception:
        return None


# ---------------- DELETE BOT MESSAGES ---------------- #
async def delete_bot_messages(guild, embed, msg, wheel, console, progress_weight):
    wheel = 0 if wheel is None else wheel
    # estimate total by sampling up to 500 messages per channel
    total = 0
    for channel in guild.text_channels:
        if active_uninstalls.get(guild.id) == "cancel":
            return wheel
        try:
            async for m in channel.history(limit=500):
                if m.author == guild.me:
                    total += 1
        except discord.Forbidden:
            console.append(f"[FAIL] message_bot_purge_guild: cannot read #{channel.name}")
        except discord.HTTPException:
            console.append(f"[FAIL] message_bot_purge_guild: read error #{channel.name}")

    total = max(total, 1)
    deleted = 0

    for channel in guild.text_channels:
        if active_uninstalls.get(guild.id) == "cancel":
            return wheel
        start_t = time.perf_counter()
        channel_deleted = 0
        try:
            async for m in channel.history(limit=None):
                if active_uninstalls.get(guild.id) == "cancel":
                    return wheel
                if m.author == guild.me:
                    try:
                        await m.delete()
                        channel_deleted += 1
                        deleted += 1
                        # update a little each delete
                        progress = (deleted / total) * progress_weight
                        wheel = await smooth_progress(embed, msg, progress, min(progress + 0.6, progress_weight), wheel, console, guild.id)
                        await asyncio.sleep(0.05)
                    except discord.Forbidden:
                        console.append(f"[FAIL] message_bot_purge_guild #{channel.name}: delete permission error")
                        break
                    except discord.HTTPException:
                        console.append(f"[FAIL] message_bot_purge_guild #{channel.name}: HTTPException deleting")
                        break
        except discord.Forbidden:
            console.append(f"[FAIL] message_bot_purge_guild: cannot read #{channel.name}")
        except discord.HTTPException:
            console.append(f"[FAIL] message_bot_purge_guild: read error #{channel.name}")
        elapsed_ms = int((time.perf_counter() - start_t) * 1000)
        console.append(f"[OK] message_bot_purge_guild {channel.name}: {channel_deleted} deleted ({elapsed_ms}ms)")

    console.append(f"[OK] message_bot_purge_guild: total deleted ~{deleted}")
    return wheel


# ---------------- DELETE BOT CHANNELS / CATEGORIES / VCs ---------------- #
async def delete_bot_channels(guild, embed, msg, wheel, console, progress_weight):
    wheel = 0 if wheel is None else wheel
    prefixes = ("coffeecord", "cc-", "coffee-")
    candidates = []
    for ch in guild.channels:
        name = getattr(ch, "name", "") or ""
        topic = getattr(ch, "topic", "") or ""
        if (isinstance(name, str) and name.lower().startswith(prefixes)) or ("coffeecord" in topic.lower() or "coffeecord" in name.lower()):
            candidates.append(ch)

    total = max(len(candidates), 1)
    per_item = progress_weight / total
    current = 0

    for ch in candidates:
        if active_uninstalls.get(guild.id) == "cancel":
            return wheel
        start_t = time.perf_counter()
        try:
            await ch.delete(reason="Coffeecord uninstall cleanup")
            elapsed = int((time.perf_counter() - start_t) * 1000)
            console.append(f"[OK] Deleted channel/category: {ch.name} ({elapsed}ms)")
        except discord.Forbidden:
            console.append(f"[FAIL] Cannot delete {ch.name} (permission error)")
        except discord.HTTPException:
            console.append(f"[FAIL] HTTPException deleting {ch.name}")
        prev = current
        current += per_item
        wheel = await smooth_progress(embed, msg, prev, current, wheel, console, guild.id)
        await asyncio.sleep(0.05)

    return wheel


# ---------------- CLEAN JSON ---------------- #
async def cleanup_json(guild, embed, msg, wheel, console, progress_weight):
    wheel = 0 if wheel is None else wheel
    files = glob.glob("*.json")
    per_file = progress_weight / max(len(files), 1)
    current = 0

    for file in files:
        if active_uninstalls.get(guild.id) == "cancel":
            return wheel
        start_t = time.perf_counter()
        try:
            with open(file, "r") as f:
                data = json.load(f)
            if str(guild.id) in data:
                del data[str(guild.id)]
                with open(file, "w") as f:
                    json.dump(data, f, indent=4)
                elapsed = int((time.perf_counter() - start_t) * 1000)
                console.append(f"[OK] {file}: guild_json.data_prune {elapsed}ms")
            else:
                console.append(f"[OK] {file}: no data (0ms)")
        except Exception as e:
            console.append(f"[FAIL] {file}: guild_json.data_prune failed ({type(e).__name__})")
        prev = current
        current += per_file
        wheel = await smooth_progress(embed, msg, prev, current, wheel, console, guild.id)
        await asyncio.sleep(0)
    return wheel


# ---------------- CLEAN PERMISSIONS ---------------- #
async def cleanup_permissions(guild, embed, msg, wheel, console, progress_weight):
    wheel = 0 if wheel is None else wheel
    bot_member = guild.me
    bot_role = bot_member.top_role if bot_member else None

    items = list(guild.channels) + list(guild.roles)
    per_item = progress_weight / max(len(items), 1)
    current = 0

    for item in items:
        if active_uninstalls.get(guild.id) == "cancel":
            return wheel
        start_t = time.perf_counter()
        try:
            if isinstance(item, discord.abc.GuildChannel) and bot_role:
                try:
                    await item.set_permissions(bot_role, overwrite=None)
                except Exception:
                    pass
            if isinstance(item, discord.Role) and bot_role and item == bot_role:
                try:
                    if item.is_bot_managed() or item.name.lower().startswith(("coffeecord", "cc-", "coffee")):
                        await item.delete(reason="Coffeecord uninstall cleanup")
                        elapsed = int((time.perf_counter() - start_t) * 1000)
                        console.append(f"[OK] bot_delete_own_perms {item.name} {elapsed}ms")
                    else:
                        console.append(f"[OK] bot_delete_own_perms {item.name} 0ms")
                except Exception as e:
                    console.append(f"[FAIL] bot_delete_own_perms {item.name}: {type(e).__name__}")
            else:
                elapsed = int((time.perf_counter() - start_t) * 1000)
                console.append(f"[OK] bot_delete_own_perms {getattr(item,'name',str(item))} {elapsed}ms")
        except Exception as e:
            console.append(f"[FAIL] bot_delete_own_perms {getattr(item,'name',str(item))}: {type(e).__name__}")
        prev = current
        current += per_item
        wheel = await smooth_progress(embed, msg, prev, current, wheel, console, guild.id)
        await asyncio.sleep(0)
    return wheel


# ---------------- CANCEL BUTTON ---------------- #
class UninstallButtons(discord.ui.View):
    def __init__(self, guild_id):
        super().__init__(timeout=None)
        self.guild_id = guild_id

    @discord.ui.button(label="Cancel Uninstall", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        active_uninstalls[self.guild_id] = "cancel"
        await interaction.response.send_message("❌ Uninstall cancelled.", ephemeral=True)


# ---------------- MAIN COMMAND ---------------- #
@bot.tree.command(name="uninstall", description="Safely removes Coffeecord from this server.")
@app_commands.checks.has_permissions(administrator=True)
async def uninstall(interaction: discord.Interaction, save_data: bool = False):
    guild = interaction.guild
    guild_id = guild.id
    active_uninstalls[guild_id] = "running"

    # optional backup
    backup = backup_guild_data(guild_id) if save_data else None
    saved_path = save_backup_to_disk(guild_id, backup) if (save_data and backup) else None

    embed = discord.Embed(
        title="☕ Coffeecord Uninstall",
        description="```\nPreparing uninstall...\n```",
        color=discord.Color.red()
    )
    view = UninstallButtons(guild_id)

    # send initial message (non-ephemeral so a normal message exists to edit)
    await interaction.response.send_message(embed=embed, view=view)
    await asyncio.sleep(0.12)
    msg = await interaction.original_response()

    wheel = 0
    console = [f"[..] Starting uninstall for {guild.name} (ID {guild.id})"]

    # Step 1: Delete bot messages (35%)
    wheel = await delete_bot_messages(guild, embed, msg, wheel, console, 35)
    if active_uninstalls.get(guild_id) == "cancel":
        console.append("[FAIL] Uninstall cancelled by user")
        console_text = "\n".join(console[-MAX_CONSOLE_LINES:])
        safe_console = console_text.replace("`", "'").replace("\\", "/")
        embed.description = "```\n" + safe_console + "\nUninstall cancelled.\n```"
        try:
            await safe_msg_edit(msg, embed, view=None, console=console)
        except:
            pass
        del active_uninstalls[guild_id]
        return

    # Step 2: Delete bot channels/categories/VCs (20%)
    wheel = await delete_bot_channels(guild, embed, msg, wheel, console, 20)
    if active_uninstalls.get(guild_id) == "cancel":
        console.append("[FAIL] Uninstall cancelled by user")
        console_text = "\n".join(console[-MAX_CONSOLE_LINES:])
        safe_console = console_text.replace("`", "'").replace("\\", "/")
        embed.description = "```\n" + safe_console + "\nUninstall cancelled.\n```"
        try:
            await safe_msg_edit(msg, embed, view=None, console=console)
        except:
            pass
        del active_uninstalls[guild_id]
        return

    # Step 3: Cleanup JSON (35%)
    wheel = await cleanup_json(guild, embed, msg, wheel, console, 35)
    if active_uninstalls.get(guild_id) == "cancel":
        console.append("[FAIL] Uninstall cancelled by user")
        console_text = "\n".join(console[-MAX_CONSOLE_LINES:])
        safe_console = console_text.replace("`", "'").replace("\\", "/")
        embed.description = "```\n" + safe_console + "\nUninstall cancelled.\n```"
        try:
            await safe_msg_edit(msg, embed, view=None, console=console)
        except:
            pass
        del active_uninstalls[guild_id]
        return

    # Step 4: Cleanup permissions (10%)
    wheel = await cleanup_permissions(guild, embed, msg, wheel, console, 10)
    if active_uninstalls.get(guild_id) == "cancel":
        console.append("[FAIL] Uninstall cancelled by user")
        console_text = "\n".join(console[-MAX_CONSOLE_LINES:])
        safe_console = console_text.replace("`", "'").replace("\\", "/")
        embed.description = "```\n" + safe_console + "\nUninstall cancelled.\n```"
        try:
            await safe_msg_edit(msg, embed, view=None, console=console)
        except:
            pass
        del active_uninstalls[guild_id]
        return

    # Final animation → ensure we reach 100%
    wheel = await smooth_progress(embed, msg, 95, 100, wheel, console, guild_id)
    console.append("[OK] Uninstall complete — preparing to leave server...")

    # DM owner
    try:
        owner = guild.owner
        dm_text = (
            f"☕ Coffeecord Uninstalled from {guild.name}\n\n"
            "Thanks for having me around! If you ever need me again, here’s my invite link:\n"
            f"{INVITE_LINK}\n\n"
        )
        if save_data and saved_path:
            dm_text += f"Your server data was saved to: `{saved_path}`"
        if owner:
            await owner.send(dm_text)
    except Exception:
        console.append("[FAIL] Could not DM server owner")

    # Final embed update (safe)
    console_text = "\n".join(console[-MAX_CONSOLE_LINES:])
    safe_console = console_text.replace("`", "'").replace("\\", "/")
    final_bar = "█" * 20
    final_line = f"[{final_bar}] 100%  {SPINNER_FRAMES[0]}"
    embed.description = "```\n" + final_line + "\n" + safe_console + "\nGoodbye! 👋\n```"
    try:
        await safe_msg_edit(msg, embed, view=None, console=console)
    except:
        pass

    # small pause so users can read
    await asyncio.sleep(2.0)

    # cleanup state and leave
    try:
        await guild.leave()
    except Exception:
        console.append("[FAIL] Could not leave guild (maybe missing perms)")
        try:
            # update embed with failure line (best-effort)
            console_text = "\n".join(console[-MAX_CONSOLE_LINES:])
            safe_console = console_text.replace("`", "'").replace("\\", "/")
            embed.description = "```\n" + final_line + "\n" + safe_console + "\nGoodbye! 👋\n```"
            await safe_msg_edit(msg, embed, view=None, console=console)
        except:
            pass

    active_uninstalls.pop(guild_id, None)
    
@bot.event
async def on_ready():
    print(f"✅ Global slash commands synced.")
    print(f"🤖 Logged in as {bot.user} (ID: {bot.user.id})")
    auto_yap.start()
    reset_daily.start()
    reset_weekly.start()
    reset_monthly.start()
    bot.add_view(VerifyStartView("placeholder"))
    data = load_json(TICKETS_FILE, {})
    for guild_id in data.keys():
        bot.add_view(TicketPanel(guild_id))
    await tree.sync()
bot.run(token, log_handler=handler, log_level=logging.DEBUG)
