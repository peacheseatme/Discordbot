import discord
from discord.ext import commands
import logging
from discord.ext import commands, tasks
import os
from dotenv import load_dotenv
import asyncio
from datetime import timedelta
from discord.ext import commands
from discord.ui import View, Button
from discord import ButtonStyle
import random
from discord import ButtonStyle, Interaction
from datetime import datetime, timedelta


load_dotenv()
token = os.getenv('DISCORD_TOKEN')

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.guilds = True
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

MOD_ROLES = ["Trial mod", "Mod", "Trial admin", "Admin"]
ADMIN_ROLES = ["Admin","Trial admin"]
OWNER_ROLES = ["Founder", "Server Dev"]

warnings = {}

logging_enabled = True  # Toggle to enable/disable logs
log_channel_id = None   # Will be set with !log start

async def log_action(ctx, message: str):
    if not logging_enabled:
        return

    log_channel = discord.utils.get(ctx.guild.text_channels, name="staff-logs")
    if log_channel:
        await log_channel.send(message)


@bot.event
async def on_ready():
    print(f"We are ready to go in, {bot.user.name}")

@bot.event
async def on_member_join(member):
    await member.send(f"Welcome to the server {member.name}")

log_channel_id = None  # Stores the ID of the logging channel


@bot.command()
async def help(ctx):
    help_text = """```txt
🤖 Bot Commands Help Menu

🤖 BOT COMMANDS HELP MENU
────────────────────────────────────────────

🎮 FUN 
🎱 8ball        – Ask the magic 8-ball a question
🔫 ak47         – ...uh oh
🐱 cat         – Sends a random cat pic
🐶 dog         – Sends a random dog pic
🐾 petpet      – Animated petpet gif
☢️ nuke        – Give a “present”
🫶 roast       – Roast a user

SOCIAL
💔 breakup     – Break up with someone
❤️ hug         – Hug someone
💋 kiss        – Kiss someone
💘 lovecalc    – Love calculator
💍 marry       – Propose to someone
🧵 date      – Create a private date thread with someone
🔒 close       – Close the current date

🎤 TRUTH OR DARE
🤔 truth       – Ask a truth question
🔥 dare        – Get a dare

🎲 GAMES & BETTING
🪙 flipcoin    – Flip a coin
🎰 bet         – Place a bet

🕑 TIMERS & REMINDERS
⏳ starttimer  – Start a countdown
⏱️ endtimer    – End your active timer
⏰ checktimers – See your active timers

📝 MODERATION TOOLS
🔇 mute        – Mute a user
🔊 unmute      – Unmute a user
🚫 ban         – Ban a user
🕒 tempban     – Temporarily ban a user
⚠️ warn        – Warn a user
📜 checkwarn   – See user warnings
❌ removewarn  – Remove a warning
🧹 purge       – Clear messages

🧩 ROLES & VERIFICATION
🛡️ verify      – Verify
🔧 verifyconfig – Configure the !verify command by changing given role, and verification channel (OWNER ONLY!)
🎭 autorole    – Set automatic roles (OWNER ONLY!)
➕ giverole     – Give a role to a user
➖ removerole   – Remove a role from a user 

📌 APPLICATIONS & FORMS
📨 application        – Start a staff application
✅ applicationapprove – Approve an applicant (OWNER ONLY!)
🚫 applyoff           – Disable applications (OWNER ONLY!)
🟢 applyon            – Enable applications (OWNER ONLY!)

📊 POLLS & CHAT TOOLS
✉️ dm          – Send a direct message (OWNER ONLY)
✉️ dmfoward    – Foward a direct message (OWNER ONLY)
📊 poll        – Create a poll (OWNER ONLY!)
🗣️ say         – Make the bot say something (OWNER ONLY!)
   log         – Start and stop logging bot actions (!log (start or stop)) (OWNER ONLY!)

❓ UTILITY & MISC
❓ help        – Show this command list
```"""
    await ctx.send(help_text)


@bot.command()
async def date(ctx, member: discord.Member = None):
    if not member:
        await ctx.send("❌ You must mention someone. Usage: `!date @user`")
        return

    # Create a private thread in the current channel
    thread = await ctx.channel.create_thread(
        name=f"Askout - {ctx.author.display_name} & {member.display_name}",
        type=discord.ChannelType.private_thread,
        invitable=False
    )

    # Add both the command user and the mentioned user
    await thread.add_user(ctx.author)
    await thread.add_user(member)

    await thread.send(f"👋 {ctx.author.mention} wants to go on a date with {member.mention}! Use the !close command to exit.")
    await ctx.message.add_reaction("✅")

@bot.command()
async def close(ctx):
    if isinstance(ctx.channel, discord.Thread):
        await ctx.send("🔒 This thread is now being closed.")
        await ctx.channel.edit(archived=True, locked=True)
    else:
        await ctx.send("❌ This command can only be used inside a thread.")

@bot.command()
@commands.has_permissions(ban_members=True)
async def tempban(ctx, member: discord.Member, duration: int, unit: str, *, reason=None):
    if not any(role.name in MOD_ROLES for role in ctx.author.roles):
        await ctx.send("❌ You do not have permission to use this command.")
        return

    # Convert time unit
    time_seconds = 0
    unit = unit.lower()
    if unit == "m":
        time_seconds = duration * 60
    elif unit == "h":
        time_seconds = duration * 3600
    elif unit == "d":
        time_seconds = duration * 86400
    else:
        await ctx.send("❌ Invalid time unit. Use 'm' for minutes, 'h' for hours, or 'd' for days.")
        return

    try:
        await member.send(f"You have been temporarily banned from {ctx.guild.name} for {duration} {unit}. Reason: {reason or 'No reason provided'}")
    except discord.Forbidden:
        pass  # DMs closed or blocked

    try:
        await member.ban(reason=reason or "No reason provided")
        await ctx.send(f"⛔ {member.mention} has been temporarily banned for {duration} {unit}.")
        await log_action(ctx, f"⛔ **Temp Banned** {member.mention} by {ctx.author.mention} for {duration}{unit} - Reason: {reason or 'No reason provided'}")
    except discord.Forbidden:
        await ctx.send("❌ I do not have permission to ban this user.")
        return

    await asyncio.sleep(time_seconds)

    try:
        await ctx.guild.unban(discord.Object(id=member.id))
        await log_action(ctx, f"✅ **Unbanned** {member} after tempban expired.")
    except discord.NotFound:
        pass  # User already unbanned
    except discord.Forbidden:
        await ctx.send(f"⚠️ I couldn't unban {member} due to permission issues.")

autoroles = set()  # Store roles IDs for auto-assigning

@bot.command()
@commands.has_permissions(manage_roles=True)
async def giverole(ctx, member: discord.Member, role: discord.Role):
    if not any(r.name in MOD_ROLES for r in ctx.author.roles):
        await ctx.send("❌ You do not have permission to use this command.")
        return
    
    if role in member.roles:
        await ctx.send(f"❌ {member.mention} already has the role {role.name}.")
        return
    
    try:
        await member.add_roles(role)
        await ctx.send(f"✅ Added role {role.name} to {member.mention}.")
        await log_action(ctx, f"✅ Role {role.name} given to {member.mention} by {ctx.author.mention}")
    except discord.Forbidden:
        await ctx.send("❌ I do not have permission to add that role.")
    except Exception as e:
        await ctx.send(f"❌ Error: {e}")

from discord.ui import Button, View
from discord import Interaction

# Store verification config
verify_config = {}

@bot.command()
@commands.has_any_role(*OWNER_ROLES)
async def verifyconfig(ctx, role: discord.Role, channel: discord.TextChannel):
    verify_config[ctx.guild.id] = {
        "role_id": role.id,
        "channel_id": channel.id
    }
    await ctx.send(f"✅ Verification configured: role set to {role.mention}, channel set to {channel.mention}.")

@bot.command()
async def verify(ctx):
    config = verify_config.get(ctx.guild.id)
    if not config:
        await ctx.send("❌ Verification has not been configured yet.")
        return

    if ctx.channel.id != config["channel_id"]:
        await ctx.send("❌ You can only use this command in the configured verification channel.")
        return

    class StartVerificationView(discord.ui.View):
        @discord.ui.button(label="Start Verification", style=discord.ButtonStyle.success)
        async def start(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user != ctx.author:
                await interaction.response.send_message("❌ This is not your verification session.", ephemeral=True)
                return

            code = ''.join(random.choices('0123456789', k=6))
            user_input = ""

            class KeypadView(discord.ui.View):
                def __init__(self):
                    super().__init__(timeout=120)

                async def update_message(self, interaction):
                    content = f"**🔐 Code:** `{code}`\n**🔢 Your input:** `{user_input}`"
                    await interaction.response.edit_message(content=content, view=self)

                async def submit(self, interaction):
                    nonlocal user_input
                    if user_input == code:
                        role = ctx.guild.get_role(config["role_id"])
                        if role:
                            await interaction.user.add_roles(role)
                            await interaction.response.edit_message(content="✅ You are now verified!", view=None)
                        else:
                            await interaction.response.edit_message(content="❌ Verified role not found.", view=None)
                    else:
                        await interaction.response.edit_message(content="❌ Incorrect code. Try again with !verify.", view=None)

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
                    nonlocal user_input
                    user_input = ""
                    await self.update_message(interaction)
                @discord.ui.button(label="Submit", style=discord.ButtonStyle.success, row=3)
                async def submit_btn(self, interaction, _):
                    await self.submit(interaction)

            await interaction.response.send_message(
                content=f"**🔐 Code:** `{code}`\n**🔢 Your input:** ``,",
                view=KeypadView(),
                ephemeral=True
            )

    await ctx.send("Please click the button to start verification:", view=StartVerificationView())

@bot.command(name="8ball")
async def eight_ball(ctx, *, question: str):
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
    await ctx.send(f"🎱 Question: {question}\nAnswer: {answer}")

@bot.command()
async def bet(ctx, member: discord.Member, *, bet: str):
    await ctx.send(f"{ctx.author.mention} has bet {member.mention} {bet}!")

@bot.command()
async def flipcoin(ctx, *, prize: str = None):
    result = random.choice(["Heads", "Tails"])
    if prize:
        await ctx.send(f"🪙 The coin landed on **{result}**! {ctx.author.mention} wins {prize}!")
    else:
        await ctx.send(f"🪙 The coin landed on **{result}**!")

# Store marriages in memory (you'll want persistence for real use)
marriages = {}  # user_id -> partner_id
marriage_requests = {}  # user_id -> requester_id (pending requests)

@bot.command()
async def marry(ctx, member: discord.Member):
    married_role = discord.utils.get(ctx.guild.roles, name="Married")

    if ctx.author.id in marriages:
        await ctx.send("❌ You are already married.")
        return
    if member.id in marriages:
        await ctx.send(f"❌ {member.mention} is already married.")
        return
    if member.id in marriage_requests and marriage_requests[member.id] == ctx.author.id:
        # Accept marriage request
        marriages[ctx.author.id] = member.id
        marriages[member.id] = ctx.author.id
        del marriage_requests[member.id]

        # Add "Married" role
        if married_role:
            await ctx.author.add_roles(married_role)
            await member.add_roles(married_role)

        await ctx.send(f"💍 {ctx.author.mention} and {member.mention} are now married! Congratulations! 🎉")
    else:
        marriage_requests[ctx.author.id] = member.id
        await ctx.send(f"💌 {ctx.author.mention} has proposed to {member.mention}! {member.mention}, type `!marry {ctx.author.display_name}` to accept.")

@bot.command()
async def breakup(ctx, member: discord.Member):
    married_role = discord.utils.get(ctx.guild.roles, name="Married")

    user_id = ctx.author.id
    partner_id = marriages.get(user_id)
    if partner_id == member.id:
        del marriages[user_id]
        del marriages[partner_id]

        # Remove "Married" role
        if married_role:
            await ctx.author.remove_roles(married_role)
            await member.remove_roles(married_role)

        await ctx.send(f"💔 {ctx.author.mention} and {member.mention} have broken up.")
    else:
        await ctx.send(f"❌ You are not married to {member.mention}.")

@bot.command()
async def hug(ctx, member: discord.Member):
    await ctx.send(f"🤗 {ctx.author.mention} gives {member.mention} a big hug!")

@bot.command()
async def kiss(ctx, member: discord.Member):
    await ctx.send(f"{ctx.author.mention} kissed {member.mention}!")

@bot.command()
async def lovecalc(ctx, member1: discord.Member, member2: discord.Member):
    score = random.randint(0, 100)
    hearts = "❤️" * (score // 10)
    await ctx.send(f"💖 Love compatibility between {member1.mention} and {member2.mention} is {score}% {hearts}")

@bot.command()
async def truth(ctx, member: discord.Member, *, question: str):
    await ctx.send(f"🧠 {member.mention}, **Truth:** {question}")

@bot.command()
async def dare(ctx, member: discord.Member, *, challenge: str):
    await ctx.send(f"🔥 {member.mention}, **Dare:** {challenge}")

warnings = {}
timers = {}
reminders = []    

@tasks.loop(seconds=60)
async def reminder_checker():
    now = datetime.now()
    for reminder in reminders[:]:
        if reminder['time'] <= now:
            try:
                await reminder['user'].send(f"⏰ Reminder: {reminder['message']}")
            except:
                pass
            reminders.remove(reminder)

@bot.command()
async def remindme(ctx, message: str, date: str, time: str):
    try:
        remind_time = datetime.strptime(f"{date} {time}", "%m/%d/%y %H:%M")
        reminders.append({"user": ctx.author, "message": message, "time": remind_time})
        await ctx.send(f"✅ Reminder set for {remind_time.strftime('%m/%d/%y %H:%M')}.")
    except ValueError:
        await ctx.send("❌ Invalid date or time format. Use MM/DD/YY HH:MM.")

# Make sure this is defined at the top if not already
timers = {}

@bot.command()
async def starttimer(ctx, duration: str):
    try:
        unit = duration[-1]
        value = int(duration[:-1])

        if unit == 's':
            seconds = value
        elif unit == 'm':
            seconds = value * 60
        elif unit == 'h':
            seconds = value * 3600
        else:
            raise ValueError("Invalid unit")

        timer_id = len(timers) + 1
        end_time = datetime.now() + timedelta(seconds=seconds)
        timers[timer_id] = {"user": ctx.author, "end": end_time}
        await ctx.send(f"⏳ Timer #{timer_id} started for {value}{unit}.")

        await asyncio.sleep(seconds)

        if timer_id in timers:
            await ctx.author.send(f"⏰ Timer #{timer_id} is up!")
            del timers[timer_id]

    except ValueError:
        await ctx.send("❌ Invalid format. Use like `10s`, `5m`, or `2h` (s=seconds, m=minutes, h=hours).")
    except Exception as e:
        await ctx.send(f"❌ An error occurred: {e}")

@bot.command()
async def checktimers(ctx):
    user_timers = [
        f"⏳ Timer #{tid} ends at <t:{int(timer['end'].timestamp())}:R>"
        for tid, timer in timers.items()
        if timer["user"].id == ctx.author.id
    ]

    if user_timers:
        await ctx.send("\n".join(user_timers))
    else:
        await ctx.send("❌ You have no active timers.")

@bot.command()
async def endtimer(ctx, timer_id: int):
    timer = timers.get(timer_id)
    if not timer:
        await ctx.send("❌ Timer not found.")
        return

    if timer["user"].id != ctx.author.id:
        await ctx.send("🚫 You can only end your own timers.")
        return

    del timers[timer_id]
    await ctx.send(f"🛑 Timer #{timer_id} has been cancelled.")

@bot.command()
@commands.has_permissions(manage_roles=True)
async def removerole(ctx, member: discord.Member, role: discord.Role):
    if not any(r.name in MOD_ROLES for r in ctx.author.roles):
        await ctx.send("❌ You do not have permission to use this command.")
        return

    if role not in member.roles:
        await ctx.send(f"❌ {member.mention} does not have the role {role.name}.")
        return
    
    try:
        await member.remove_roles(role)
        await ctx.send(f"✅ Removed role {role.name} from {member.mention}.")
        await log_action(ctx, f"✅ Role {role.name} removed from {member.mention} by {ctx.author.mention}")
    except discord.Forbidden:
        await ctx.send("❌ I do not have permission to remove that role.")
    except Exception as e:
        await ctx.send(f"❌ Error: {e}")

import json

AUTOROLE_FILE = "autorole.json"

def load_autoroles():
    if not os.path.exists(AUTOROLE_FILE):
        return {}
    with open(AUTOROLE_FILE, "r") as f:
        return json.load(f)

def save_autoroles(data):
    with open(AUTOROLE_FILE, "w") as f:
        json.dump(data, f, indent=4)

@bot.command()
@commands.has_permissions(manage_roles=True)
async def autorole(ctx, action: str, role: discord.Role):
    data = load_autoroles()
    guild_id = str(ctx.guild.id)

    if action.lower() == "add":
        if guild_id not in data:
            data[guild_id] = []
        if role.id not in data[guild_id]:
            data[guild_id].append(role.id)
            save_autoroles(data)
            await ctx.send(f"✅ Added {role.name} to auto-role list.")
        else:
            await ctx.send("❗ That role is already in the auto-role list.")
    elif action.lower() == "remove":
        if guild_id in data and role.id in data[guild_id]:
            data[guild_id].remove(role.id)
            save_autoroles(data)
            await ctx.send(f"🗑 Removed {role.name} from auto-role list.")
        else:
            await ctx.send("❌ That role wasn't in the list.")
    else:
        await ctx.send("❌ Usage: `!autorole add @role` or `!autorole remove @role`")

@bot.event
async def on_member_join(member):
    data = load_autoroles()
    guild_id = str(member.guild.id)
    if guild_id in data:
        for role_id in data[guild_id]:
            role = discord.utils.get(member.guild.roles, id=role_id)
            if role:
                try:
                    await member.add_roles(role)
                except discord.Forbidden:
                    pass  # Bot doesn't have permission

@bot.command()
@commands.has_permissions(manage_roles=True)
async def mute(ctx, member: discord.Member, duration: int, unit: str, *, reason=None):
    if not any(role.name in MOD_ROLES for role in ctx.author.roles):
        await ctx.send("❌ You do not have permission to use this command.")
        return

    unit = unit.lower()
    if unit not in ("m", "h"):
        await ctx.send("❌ Invalid time unit. Use 'm' for minutes or 'h' for hours.")
        return

    # Convert duration to seconds
    duration_seconds = duration * 60 if unit == "m" else duration * 3600

    # Create or find the 'Muted' role
    mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if mute_role is None:
        try:
            mute_role = await ctx.guild.create_role(name="Muted", reason="Needed a mute role")
            for channel in ctx.guild.channels:
                await channel.set_permissions(mute_role, send_messages=False, speak=False, add_reactions=False)
        except discord.Forbidden:
            await ctx.send("❌ I do not have permission to create or manage roles.")
            return

    if mute_role in member.roles:
        await ctx.send(f"❌ {member.mention} is already muted.")
        return

    try:
        await member.add_roles(mute_role, reason=reason)
        await ctx.send(f"🔇 {member.mention} has been muted for {duration}{unit}. Reason: {reason or 'No reason provided'}")
        await log_action(ctx, f"🔇 **Muted** {member.mention} by {ctx.author.mention} for {duration}{unit} - Reason: {reason or 'No reason provided'}")

        # Wait for the duration and then unmute
        await asyncio.sleep(duration_seconds)
        await member.remove_roles(mute_role, reason="Mute duration expired")
        await log_action(ctx, f"🔊 **Auto-unmuted** {member.mention} after {duration}{unit}")
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to mute this user.")
    
@bot.command()
async def say(ctx, *, arg):
    if not any(role.name in OWNER_ROLES for role in ctx.author.roles):
        await ctx.send("❌ You do not have permission to use this command.")
        return

    
    message, channel_part = map(str.strip, arg.split('#', 1))

    channel = None

    # Try to parse channel mention: <#123456789012345678>
    if channel_part.startswith('<#') and channel_part.endswith('>'):
        channel_id = int(channel_part[2:-1])
        channel = ctx.guild.get_channel(channel_id)
    
    # Try to parse channel ID directly if not mention
    elif channel_part.isdigit():
        channel = ctx.guild.get_channel(int(channel_part))

    # Otherwise try to find by name (case insensitive)
    else:
        channel = discord.utils.find(lambda c: c.name.lower() == channel_part.lower(), ctx.guild.channels)
    
    if channel is None:
        await ctx.send(f"❌ Could not find a channel matching `{channel_part}`.")
        return

    await ctx.message.delete()
    await channel.send(message)
    await log_action(ctx, f"💬 **Message said by {ctx.author.mention}** in {channel.mention}: {message}")

@bot.command()
async def dm(ctx, member: discord.Member, *, message):
    if not any(role.name in OWNER_ROLES for role in ctx.author.roles):
        await ctx.send("❌ You do not have permission to use this command.")
        return
    


    try:
        await member.send(f"📬 **Message from the staff:**\n{message}")
        await ctx.send(f"✅ Message sent to {member.mention}.")
        await log_action(ctx, f"📨 **DM sent** to {member.mention} by {ctx.author.mention} - Content: {message}")
    except discord.Forbidden:
        await ctx.send("❌ Could not send the DM. The user's DMs may be closed.")

    mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if mute_role is None:
        try:
            mute_role = await ctx.guild.create_role(name="Muted")
            for channel in ctx.guild.channels:
                await channel.set_permissions(mute_role, send_messages=False, speak=False)
        except discord.Forbidden:
            await ctx.send("❌ I do not have permission to create the Muted role.")
            return

    if mute_role in member.roles:
        await ctx.send(f"⚠️ {member.mention} is already muted.")
        return

    await member.add_roles(mute_role, reason=reason)
    await ctx.send(f"🔇 {member.mention} has been muted. Reason: {reason if reason else 'No reason provided'}")
    await log_action(ctx, f"🔇 **Muted** {member.mention} by {ctx.author.mention} - Reason: {reason if reason else 'No reason provided'}")

@bot.command()
async def unmute(ctx, member: discord.Member):
    if not any(role.name in MOD_ROLES for role in ctx.author.roles):
        await ctx.send("❌ You do not have permission to use this command.")
        return

    mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if mute_role:
        if mute_role in member.roles:
            await member.remove_roles(mute_role)
            await ctx.send(f"🔊 {member.mention} has been unmuted.")
            await log_action(ctx, f"🔊 **Unmuted** {member.mention} by {ctx.author.mention}")
        else:
            await ctx.send(f"⚠️ {member.mention} is not muted.")
    else:
        await ctx.send("❌ 'Muted' role does not exist.")

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


warnings = {}  # somewhere global

from discord.ext import commands, tasks
import discord
import asyncio
from discord.ext import commands


@bot.command()
async def poll(ctx, *, args):
    if not any(role.name in OWNER_ROLES for role in ctx.author.roles):
        await ctx.send("❌ You do not have permission to use this command.")
        return

    # Expecting format: Question # channel-name # time_in_minutes
    if '#' not in args:
        await ctx.send("❌ Please separate the question, channel, and time with `#`.\nExample: `!poll What is your favorite color? # general # 5`")
        return

    parts = [part.strip() for part in args.split('#')]
    if len(parts) != 3:
        await ctx.send("❌ Incorrect format. Use: `!poll Question # channel # time_in_minutes`")
        return

    question, channel_name, time_str = parts

    # Get the channel object by name
    channel = discord.utils.get(ctx.guild.channels, name=channel_name)
    if not channel:
        await ctx.send(f"❌ Could not find a channel named `{channel_name}`.")
        return

    # Parse time in minutes and convert to seconds
    try:
        duration_minutes = int(time_str)
        if duration_minutes <= 0:
            raise ValueError()
        duration_seconds = duration_minutes * 60
    except ValueError:
        await ctx.send("❌ Time must be a positive integer representing minutes.")
        return

    # Create and send the poll embed
    embed = discord.Embed(title="📊 Poll", description=question, color=discord.Color.blue())
    embed.set_footer(text=f"Poll ends in {duration_minutes} minute(s).")
    poll_message = await channel.send(embed=embed)

    # Add reactions for upvote and downvote
    await poll_message.add_reaction("👍")
    await poll_message.add_reaction("👎")

    await log_action(ctx, f"📊 **Poll created by {ctx.author.mention} in {channel.mention}**: {question}")

    # Wait for the duration then remove reactions
    await asyncio.sleep(duration_seconds)
    try:
        await poll_message.clear_reactions()
        await channel.send(f"🛑 Poll ended! Thanks for voting.")
    except discord.Forbidden:
        await channel.send("⚠️ I do not have permission to clear reactions.")

@bot.command()
async def warn(ctx, member: discord.Member, *, reason):
    if not any(role.name in MOD_ROLES for role in ctx.author.roles):
        await ctx.send("❌ You do not have permission to use this command.")
        return

    user_warnings = warnings.get(member.id, [])
    user_warnings.append(f"{reason} (issued by {ctx.author.display_name})")
    warnings[member.id] = user_warnings

    await ctx.send(f"⚠️ {member.mention} has been warned. Reason: {reason}")
    await log_action(ctx, f"⚠️ **Warned** {member.mention} by {ctx.author.mention} - Reason: {reason}")

@bot.command()
async def checkwarn(ctx, member: discord.Member):
    if not any(role.name in MOD_ROLES for role in ctx.author.roles):
        await ctx.send("❌ You do not have permission to use this command.")
        return

    user_warns = warnings.get(member.id, [])
    if user_warns:
        formatted_warnings = "\n".join(f"{i+1}. {warn}" for i, warn in enumerate(user_warns))
        await ctx.send(f"{member.mention} has warnings:\n{formatted_warnings}")
    else:
        await ctx.send(f"{member.mention} has no warnings.")

@bot.command()
async def removewarn(ctx, member: discord.Member):
    if not any(role.name in MOD_ROLES for role in ctx.author.roles):
        await ctx.send("❌ You do not have permission to use this command.")
        return

    if member.id in warnings:
        warnings.pop(member.id)
        await ctx.send(f"❌ Warnings removed for {member.mention}.")
        await log_action(ctx, f"❌ Removed all warnings for {member.mention} by {ctx.author.mention}")
    else:
        await ctx.send(f"{member.mention} has no warnings to remove.")

@bot.command()
async def purge(ctx, amount: int):
    if not any(role.name in MOD_ROLES for role in ctx.author.roles):
        await ctx.send("❌ You do not have permission to use this command.")
        return

    if amount <= 0:
        await ctx.send("❌ Please specify a positive number of messages to delete.")
        return

    # Limit the maximum number to avoid abuse (optional)
    if amount > 10000:
        await ctx.send("❌ You can only delete up to 10000 messages at once.")
        return

    deleted = await ctx.channel.purge(limit=amount + 1)  # +1 to include the purge command message itself
    await ctx.send(f"🧹 Deleted {len(deleted)-1} messages.", delete_after=5)
    await log_action(ctx, f"🧹 **Purged** {len(deleted)-1} messages in {ctx.channel.mention} by {ctx.author.mention}")

@bot.command()
@commands.has_permissions(manage_messages=True)
async def purgebot(ctx, botname: str, amount: int):
    """Purges messages from a specific bot by name."""
    botname = botname.lower()

    def is_target_bot(msg):
        return msg.author.bot and msg.author.name.lower() == botname

    deleted = await ctx.channel.purge(limit=amount * 5, check=is_target_bot)
    await ctx.send(f"🧹 Deleted {len(deleted)} messages from bot `{botname}`.", delete_after=5)


@bot.command()
@commands.has_permissions(manage_messages=True)
async def purgehuman(ctx, username: str, amount: int):
    """Purges messages from a specific human user by name."""
    username = username.lower()

    def is_target_user(msg):
        return not msg.author.bot and msg.author.name.lower() == username

    deleted = await ctx.channel.purge(limit=amount * 5, check=is_target_user)
    await ctx.send(f"🧹 Deleted {len(deleted)} messages from human `{username}`.", delete_after=5)

@bot.command()
async def ban(ctx, member: discord.Member, *, reason=None):
    if not any(role.name in MOD_ROLES for role in ctx.author.roles):
        await ctx.send("❌ You do not have permission to use this command.")
        return

    try:
        await member.ban(reason=reason)
        await ctx.send(f"⛔ {member.mention} has been banned. Reason: {reason if reason else 'No reason provided'}")
        await log_action(ctx, f"⛔ **Banned** {member.mention} by {ctx.author.mention} - Reason: {reason if reason else 'No reason provided'}")
    except discord.Forbidden:
        await ctx.send("❌ I do not have permission to ban this user.")
    except Exception as e:
        await ctx.send(f"❌ Failed to ban user: {e}")

@bot.command()
@commands.has_any_role(*MOD_ROLES)
async def unban(ctx, user_id: int):
    try:
        user = await bot.fetch_user(user_id)  # Fetch user object by ID
        await ctx.guild.unban(user)
        await ctx.send(f"✅ {user.mention} has been unbanned.")
        await log_action(ctx, f"✅ **Unbanned** {user} by {ctx.author}")
    except discord.NotFound:
        await ctx.send("❌ This user is not banned or does not exist.")
    except discord.Forbidden:
        await ctx.send("❌ I do not have permission to unban this user.")
    except discord.HTTPException as e:
        await ctx.send(f"❌ Failed to unban user: {e}")

@bot.command()
@commands.has_any_role(*ADMIN_ROLES)
async def applyon(ctx):
    channel = discord.utils.get(ctx.guild.text_channels, name="staff-applications")
    if channel is None:
        await ctx.send("❌ The 'staff-applications' channel was not found.")
        return

    overwrite = channel.overwrites_for(ctx.guild.default_role)
    overwrite.view_channel = True
    await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
    await ctx.send("✅ Staff applications are now **open**.")
    await log_action(ctx, f"✅ **Opened** staff applications by {ctx.author.mention}")

@bot.command()
@commands.has_any_role(*ADMIN_ROLES)
async def applyoff(ctx):
    channel = discord.utils.get(ctx.guild.text_channels, name="staff-applications")
    if channel is None:
        await ctx.send("❌ The 'staff-applications' channel was not found.")
        return

    overwrite = channel.overwrites_for(ctx.guild.default_role)
    overwrite.view_channel = False
    await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
    await ctx.send("❌ Staff applications are now **closed**.")
    await log_action(ctx, f"❌ **Closed** staff applications by {ctx.author.mention}")

@bot.command()
async def application(ctx):
    if ctx.channel.name != "staff-applications":
        await ctx.send("You can only use this command in #staff-application.")
        return

    questions = [
        "What is your real name?",
        "How old are you?",
        "Why do you want to join the staff team?",
        "What experience do you have with moderation?",
        "Are you willing to follow the server rules?",
        "What game[s] are you applying for? Or just the discord server? [Stormworks, SCP:SL or Minecraft]",
        "If someone were to harrass another player, what would you do?",
        "If an admin was abusing, what would you do?",
        "On a scale of 1-10, how would you rate BlackBox Servers?"
    ]

    answers = []
    try:
        await ctx.author.send("Starting your staff application. Please answer the following questions:")
        for q in questions:
            await ctx.author.send(q)
            msg = await bot.wait_for('message', check=lambda m: m.author == ctx.author and isinstance(m.channel, discord.DMChannel), timeout=300)
            answers.append(f"**{q}**\n{msg.content}\n")

        founder_member = discord.utils.find(lambda m: any(r.name == "Founder" for r in m.roles), ctx.guild.members)
        transcript = "\n".join(answers)
        if founder_member:
            await founder_member.send(f"📬 New staff application from {ctx.author} (ID: {ctx.author.id}):\n\n{transcript}")
            await ctx.author.send("✅ Your application has been sent to the server owner. Thank you!")
        else:
            await ctx.send("❌ Could not find a member with the 'Founder' role.")
    except Exception as e:
        await ctx.send("❌ Unable to complete application. Make sure your DMs are open.")

@bot.command()
@commands.has_any_role(*OWNER_ROLES)
async def applicationapprove(ctx, member: discord.Member):
    trial_mod_role = discord.utils.get(ctx.guild.roles, name="Trial Moderator")
    if trial_mod_role is None:
        await ctx.send("❌ The role 'Trial Moderator' does not exist on this server.")
        return
    
    try:
        await member.add_roles(trial_mod_role)
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to assign roles.")
        return
    except discord.HTTPException as e:
        await ctx.send(f"❌ Failed to assign role: {e}")
        return

    try:
        await member.send("🎉 You have been approved as a staff member! You will start as a 'Trial Mod'. Welcome aboard!")
    except discord.Forbidden:
        await ctx.send(f"⚠️ Could not send DM to {member.mention}, but the role was assigned.")
    
    await ctx.send(f"✅ Approved {member.mention} for staff.")
    await log_action(ctx, f"✅ **Approved staff application** for {member.mention} by {ctx.author.mention}")

@bot.command()
@commands.has_any_role(*OWNER_ROLES)
async def applicationdeny(ctx, member: discord.Member, *, reason: str = "No specific reason provided."):
    try:
        await member.send(f"❌ Your staff application has been denied.\n**Reason:** {reason}\nYou are welcome to reapply in the future.")
    except discord.Forbidden:
        await ctx.send(f"⚠️ Could not send DM to {member.mention}, but they were denied.")

    await ctx.send(f"❌ Denied staff application for {member.mention}.")
    await log_action(ctx, f"❌ **Denied staff application** for {member.mention} by {ctx.author.mention}\n**Reason:** {reason}")

import aiohttp

# Dog image by breed (using Dog CEO API)
@bot.command()
async def dog(ctx, breed: str = None):
    url = "https://dog.ceo/api/breeds/image/random"
    if breed:
        url = f"https://dog.ceo/api/breed/{breed.lower()}/images/random"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
            if data["status"] == "success":
                await ctx.send(data["message"])
            else:
                await ctx.send("❌ Breed not found or error getting dog image.")

# Random cat image (TheCatAPI)
@bot.command()
async def cat(ctx):
    url = "https://api.thecatapi.com/v1/images/search"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
            if data:
                await ctx.send(data[0]["url"])
            else:
                await ctx.send("❌ Could not get a cat image.")

# Petpet GIF for a user's avatar (using petpet API)
@bot.command()
async def petpet(ctx, member: discord.Member = None):
    member = member or ctx.author
    avatar_url = member.avatar.url if member.avatar else member.default_avatar.url
    api_url = f"https://some-petpet-api.com/api/petpet?image={avatar_url}"  # Replace with real API if available
    await ctx.send(f"Here's the petpet gif for {member.mention}: {api_url}")

# AK-47 GIF (static URL or from Giphy)
@bot.command()
async def ak47(ctx):
    url = "https://giphy.com/gifs/cat-gun-thug-GaqnjVbSLs2uA"  # Example
    await ctx.send(url)

# Nuke “present” gift (fun gif)
@bot.command()
async def nuke(ctx, member: discord.Member):
    url = "https://giphy.com/gifs/explosion-bomb-mushroom-X92pmIty2ZJp6"
    await ctx.send(f"{ctx.author.mention} gave a 🎁 to {member.mention}!\n{url}")

# Uwuify message (simple text transform)
import re

# Roast (random roast from list)
@bot.command()
async def roast(ctx):
    roasts = [
        "You're as bright as a black hole, and twice as dense.",
        "You have something on your chin… no, the third one down.",
        "You're the reason the gene pool needs a lifeguard.",
        "You bring everyone so much joy… when you leave the room.",
        "You have the perfect face for radio."
    ]
    await ctx.send(random.choice(roasts))

# DM forward to owner (use owner id)
@bot.command()
@commands.has_any_role(*OWNER_ROLES)
async def dmfoward(ctx, *, message: str):
    owner_id = 1272383035269976067  # Replace with your actual owner ID if needed
    owner = bot.get_user(owner_id)
    
    if owner:
        await owner.send(f"📨 DM forward from {ctx.author} ({ctx.author.id}):\n{message}")
        await ctx.send("✅ Message forwarded to the owner.")
    else:
        await ctx.send("❌ Owner not found.")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingAnyRole):
        await ctx.send("🚫 You don’t have permission to use that command.")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("🚫 You’re missing required permissions to run this command.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❗ Missing argument: `{error.param.name}`")
    elif isinstance(error, commands.CommandNotFound):
        pass  # You can respond here if you want to let users know they used a wrong command
    else:
        # For debugging other unexpected errors
        await ctx.send("⚠️ An error occurred while processing the command.")
        raise error  # Optional: for logging in console

bot.run(token, log_handler=handler, log_level=logging.DEBUG)
