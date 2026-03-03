import asyncio
import json
from io import BytesIO
from pathlib import Path
from typing import Any, Optional

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont, ImageSequence

from .module_registry import is_module_enabled

BASE_DIR = Path(__file__).resolve().parent.parent
XP_FILE = BASE_DIR / "Main" / "xp.json"
CONFIG_FILE = BASE_DIR / "Main" / "leveling.json"
BACKGROUND_FILE = BASE_DIR / "Main" / "backgrounds.json"
LEVEL_REWARDS_FILE = BASE_DIR / "Main" / "level_rewards.json"
SUPPORTERS_FILE = BASE_DIR / "Storage" / "Data" / "supporters.json"
FONT_PATH = BASE_DIR / "Main" / "Roboto-Regular.ttf"
BOLD_FONT_PATH = BASE_DIR / "Main" / "Roboto-Bold.ttf"
CACHE_DIR = BASE_DIR / "Storage" / "Temp" / "level_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        with path.open("r", encoding="utf-8") as fp:
            return json.load(fp)
    except (OSError, json.JSONDecodeError):
        return default


def _save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fp:
        json.dump(data, fp, indent=2, ensure_ascii=True)


def _supporter_active(user_id: int) -> bool:
    data = _load_json(SUPPORTERS_FILE, {"supporters": {}})
    supporters = data.get("supporters", {})
    if not isinstance(supporters, dict):
        return False
    record = supporters.get(str(user_id))
    if not isinstance(record, dict):
        return False
    return bool(record.get("active", False))


async def _dispatch_module_event(
    bot: commands.Bot,
    guild: Optional[discord.Guild],
    module_name: str,
    action: str,
    actor: Optional[discord.abc.User] = None,
    details: str = "",
    channel_id: Optional[int] = None,
) -> None:
    if guild is None:
        return
    try:
        bot.dispatch("coffeecord_module_event", guild, module_name, action, actor, details, channel_id)
    except Exception:
        return


async def _check_level_up(bot: commands.Bot, guild_id: str, user_id: str, channel: Optional[discord.abc.Messageable]) -> None:
    xp_data = _load_json(XP_FILE, {})
    config = _load_json(CONFIG_FILE, {})
    rewards_data = _load_json(LEVEL_REWARDS_FILE, {})

    user_data = xp_data.get(guild_id, {}).get(user_id, {"xp": 0, "level": 1, "next_level_xp": 10})
    guild_cfg = config.get(guild_id, {})
    guild_rewards = rewards_data.get(guild_id, {})
    rewards = guild_rewards.get("rewards", {})
    replace_old = bool(guild_rewards.get("replace_old_roles", False))

    xp = int(user_data.get("xp", 0))
    level = int(user_data.get("level", 1))
    next_level_xp = int(user_data.get("next_level_xp", guild_cfg.get("base_xp", 10)))
    if xp < next_level_xp:
        return

    old_level = level
    user_data["level"] = level + 1
    user_data["xp"] = 0
    base = int(guild_cfg.get("base_xp", 10))
    scale = float(guild_cfg.get("xp_scale", 1.1))
    user_data["next_level_xp"] = int(base * (scale ** user_data["level"]))

    xp_data.setdefault(guild_id, {})
    xp_data[guild_id][user_id] = user_data
    _save_json(XP_FILE, xp_data)

    guild: Optional[discord.Guild] = None
    if isinstance(channel, discord.TextChannel):
        guild = channel.guild
        try:
            await channel.send(f"🎉 <@{user_id}> has leveled up to **Level {user_data['level']}**!")
        except discord.HTTPException:
            pass
        await _dispatch_module_event(
            bot,
            guild,
            "leveling",
            "level_up",
            actor=guild.get_member(int(user_id)) if guild else None,
            details=f"user_id={user_id}; old_level={old_level}; new_level={user_data['level']}",
            channel_id=channel.id if hasattr(channel, "id") else None,
        )

    if guild is None:
        return
    member = guild.get_member(int(user_id))
    if member is None:
        return
    reward = rewards.get(str(user_data["level"]))
    if not isinstance(reward, dict):
        return
    role = guild.get_role(int(reward.get("role_id", 0)))
    if role is None:
        return

    try:
        await member.add_roles(role)
    except discord.HTTPException:
        return

    if replace_old:
        for lvl, info in rewards.items():
            if lvl == str(user_data["level"]) or not isinstance(info, dict):
                continue
            old_role = guild.get_role(int(info.get("role_id", 0)))
            if old_role and old_role in member.roles:
                try:
                    await member.remove_roles(old_role)
                except discord.HTTPException:
                    pass

    message_tpl = str(reward.get("message", "🎉 {user} reached level {level} and earned {role}!"))
    content = (
        message_tpl.replace("{user}", member.mention)
        .replace("{role}", role.mention)
        .replace("{level}", str(user_data["level"]))
        .replace("{server}", guild.name)
    )
    try:
        await channel.send(content)  # type: ignore[arg-type]
    except Exception:
        pass

    await _dispatch_module_event(
        bot,
        guild,
        "leveling",
        "reward_granted",
        actor=member,
        details=f"level={user_data['level']}; role_id={role.id}",
        channel_id=channel.id if hasattr(channel, "id") else None,
    )


async def award_message_xp(bot: commands.Bot, message: discord.Message) -> None:
    if message.guild is None or message.author.bot:
        return
    if not await is_module_enabled(message.guild.id, "leveling"):
        return
    guild_id = str(message.guild.id)
    user_id = str(message.author.id)
    xp_data = _load_json(XP_FILE, {})
    config = _load_json(CONFIG_FILE, {})
    xp_data.setdefault(guild_id, {})
    xp_data[guild_id].setdefault(user_id, {"xp": 0, "level": 0})
    xp_data[guild_id][user_id]["xp"] += int(config.get(guild_id, {}).get("message_xp", 0))
    _save_json(XP_FILE, xp_data)
    await _check_level_up(bot, guild_id, user_id, message.channel)


async def award_reaction_xp(bot: commands.Bot, reaction: discord.Reaction, user: discord.abc.User) -> None:
    if user.bot or reaction.message.guild is None:
        return
    if not await is_module_enabled(reaction.message.guild.id, "leveling"):
        return
    guild_id = str(reaction.message.guild.id)
    user_id = str(user.id)
    xp_data = _load_json(XP_FILE, {})
    config = _load_json(CONFIG_FILE, {})
    xp_data.setdefault(guild_id, {})
    xp_data[guild_id].setdefault(user_id, {"xp": 0, "level": 0})
    xp_data[guild_id][user_id]["xp"] += int(config.get(guild_id, {}).get("reaction_xp", 0))
    _save_json(XP_FILE, xp_data)
    await _check_level_up(bot, guild_id, user_id, reaction.message.channel)


async def award_voice_xp(
    bot: commands.Bot,
    member: discord.Member,
    active_vc_members: dict[str, dict[str, float]],
) -> None:
    guild_id = str(member.guild.id)
    user_id = str(member.id)
    if not await is_module_enabled(member.guild.id, "leveling"):
        return
    if guild_id not in active_vc_members or user_id not in active_vc_members[guild_id]:
        return
    join_time = active_vc_members[guild_id].pop(user_id)
    duration = asyncio.get_event_loop().time() - join_time
    minutes = int(duration / 60)
    if minutes <= 0:
        return
    xp_data = _load_json(XP_FILE, {})
    config = _load_json(CONFIG_FILE, {})
    xp_data.setdefault(guild_id, {})
    xp_data[guild_id].setdefault(user_id, {"xp": 0, "level": 0})
    gained_xp = int(config.get(guild_id, {}).get("vc_minute_xp", 0)) * minutes
    xp_data[guild_id][user_id]["xp"] += gained_xp
    _save_json(XP_FILE, xp_data)
    channel = discord.utils.get(member.guild.text_channels, name="general")
    if channel is not None:
        await _check_level_up(bot, guild_id, user_id, channel)


class LevelingCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    xp_group = app_commands.Group(name="xp", description="XP and leveling configuration commands")
    levelreward_group = app_commands.Group(name="levelreward", description="Level reward role commands")

    @app_commands.command(name="levelbackground", description="Set your level card background (GIF for supporters)")
    @app_commands.describe(url="Link to the background image or GIF")
    async def levelbackground(self, interaction: discord.Interaction, url: str) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("This command can only be used in servers.", ephemeral=True)
            return
        if not await is_module_enabled(interaction.guild.id, "leveling"):
            await interaction.response.send_message(
                "This module is currently disabled. An admin can enable it with /modules.",
                ephemeral=True,
            )
            return
        try:
            async with aiohttp.ClientSession() as session:
                async with session.head(url, allow_redirects=True) as resp:
                    if resp.status != 200 or not str(resp.headers.get("Content-Type", "")).startswith("image/"):
                        await interaction.response.send_message("❌ Invalid image URL.", ephemeral=True)
                        return
        except Exception:
            await interaction.response.send_message("❌ Invalid image URL.", ephemeral=True)
            return

        if url.lower().endswith(".gif") and not _supporter_active(interaction.user.id):
            await interaction.response.send_message("🚫 Only supporters can use GIF backgrounds.", ephemeral=True)
            return

        data = _load_json(BACKGROUND_FILE, {})
        data[str(interaction.user.id)] = url
        _save_json(BACKGROUND_FILE, data)
        await _dispatch_module_event(
            self.bot,
            interaction.guild,
            "leveling",
            "background_update",
            actor=interaction.user,
            details=f"gif={url.lower().endswith('.gif')}",
            channel_id=interaction.channel.id if interaction.channel else None,
        )
        await interaction.response.send_message("✅ Background updated successfully!", ephemeral=True)

    @app_commands.command(name="level", description="Show your or another user's level card.")
    async def level(self, interaction: discord.Interaction, user: Optional[discord.Member] = None) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("This command can only be used in servers.", ephemeral=True)
            return
        if not await is_module_enabled(interaction.guild.id, "leveling"):
            await interaction.response.send_message(
                "This module is currently disabled. An admin can enable it with /modules.",
                ephemeral=True,
            )
            return
        target = user or interaction.user
        guild_id = str(interaction.guild.id)
        user_id = str(target.id)
        xp_data = _load_json(XP_FILE, {})
        backgrounds = _load_json(BACKGROUND_FILE, {})
        user_data = xp_data.get(guild_id, {}).get(user_id, {"xp": 0, "level": 1})
        xp = int(user_data.get("xp", 0))
        level = int(user_data.get("level", 1))
        xp_for_next_level = max(int(user_data.get("next_level_xp", (level * 100) + 100)), 1)
        progress = max(0.0, min(xp / xp_for_next_level, 1.0))
        bg_url = str(backgrounds.get(user_id, "https://i.imgur.com/6z6kKlg.png"))
        supporter = _supporter_active(target.id)

        await interaction.response.defer()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(bg_url) as resp:
                    if resp.status != 200:
                        await interaction.followup.send("❌ Failed to download background.", ephemeral=True)
                        return
                    bg_bytes = await resp.read()
        except Exception as e:
            await interaction.followup.send(f"❌ Error loading background: {e}", ephemeral=True)
            return

        try:
            if bg_url.lower().endswith(".gif") and supporter:
                bg = Image.open(BytesIO(bg_bytes))
                frames = [f.convert("RGBA").resize((800, 240)) for f in ImageSequence.Iterator(bg)]
                duration = int(bg.info.get("duration", 100))
            else:
                bg = Image.open(BytesIO(bg_bytes)).convert("RGBA").resize((800, 240))
                frames = [bg]
                duration = 100
        except Exception as e:
            await interaction.followup.send(f"❌ Could not open background: {e}", ephemeral=True)
            return

        avatar = None
        try:
            avatar_bytes = await target.display_avatar.replace(size=128).read()
            avatar = Image.open(BytesIO(avatar_bytes)).convert("RGBA").resize((128, 128))
            mask = Image.new("L", avatar.size, 0)
            draw_mask = ImageDraw.Draw(mask)
            draw_mask.ellipse((0, 0, 128, 128), fill=255)
            avatar.putalpha(mask)
        except Exception:
            avatar = None

        guild_xp = xp_data.get(guild_id, {})
        sorted_users = sorted(guild_xp.items(), key=lambda x: x[1].get("xp", 0), reverse=True)
        rank = next((i + 1 for i, (uid, _) in enumerate(sorted_users) if uid == user_id), 0)

        try:
            name_font = ImageFont.truetype(str(BOLD_FONT_PATH), 30)
            level_font = ImageFont.truetype(str(BOLD_FONT_PATH), 28)
            rank_font = ImageFont.truetype(str(BOLD_FONT_PATH), 30)
            xp_font = ImageFont.truetype(str(BOLD_FONT_PATH), 32)
        except Exception:
            try:
                name_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 30)
                level_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 28)
                rank_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 30)
                xp_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 32)
            except Exception:
                name_font = ImageFont.load_default()
                level_font = ImageFont.load_default()
                rank_font = ImageFont.load_default()
                xp_font = ImageFont.load_default()

        output_frames = []
        for frame in frames:
            draw = ImageDraw.Draw(frame)
            avatar_x, avatar_y = 24, 56
            avatar_size = 128
            content_left = 180
            content_right = 760
            top_y = 50
            separator_y = 118
            xp_text_y = 132
            bar_top = 168
            bar_bottom = 198
            bar_radius = 50

            draw.rounded_rectangle((content_left, bar_top, content_right, bar_bottom), radius=bar_radius, fill=(50, 50, 50, 170))
            fill_width = int((content_right - content_left) * progress)
            if fill_width > 0:
                draw.rounded_rectangle(
                    (content_left, bar_top, content_left + fill_width, bar_bottom),
                    radius=bar_radius,
                    fill=(0, 200, 255, 255),
                )

            if avatar:
                frame.paste(avatar, (avatar_x, avatar_y), avatar)
                status_source = interaction.guild.get_member(target.id) or target
                status_key = str(getattr(status_source, "raw_status", getattr(status_source, "status", "offline"))).lower()
                status_color = {
                    "online": (67, 181, 129, 255),
                    "idle": (250, 166, 26, 255),
                    "dnd": (240, 71, 71, 255),
                    "offline": (116, 127, 141, 255),
                    "invisible": (116, 127, 141, 255),
                }.get(status_key, (116, 127, 141, 255))
                dot_center_x = avatar_x + avatar_size - 8
                dot_center_y = avatar_y + avatar_size - 8
                draw.ellipse((dot_center_x - 13, dot_center_y - 13, dot_center_x + 13, dot_center_y + 13), fill=(32, 34, 37, 255))
                draw.ellipse((dot_center_x - 10, dot_center_y - 10, dot_center_x + 10, dot_center_y + 10), fill=status_color)

            display_name = str(target.display_name)
            level_text = f"Level {level}"
            rank_text = f"Rank #{rank}"
            xp_display = max(0, min(int(xp), xp_for_next_level))
            xp_text = f"XP: {xp_display:,} / {xp_for_next_level:,}"

            draw.text((content_left, top_y), display_name, font=name_font, fill=(80, 255, 120, 255), stroke_width=2, stroke_fill=(20, 20, 20, 255))
            level_bbox = draw.textbbox((0, 0), level_text, font=level_font)
            rank_bbox = draw.textbbox((0, 0), rank_text, font=rank_font)
            draw.text((content_right - (level_bbox[2] - level_bbox[0]), top_y), level_text, font=level_font, fill=(80, 255, 120, 255), stroke_width=2, stroke_fill=(20, 20, 20, 255))
            draw.text((content_right - (rank_bbox[2] - rank_bbox[0]), top_y + 38), rank_text, font=rank_font, fill=(130, 255, 160, 255), stroke_width=2, stroke_fill=(20, 20, 20, 255))
            draw.line((content_left, separator_y, content_right, separator_y), fill=(255, 255, 255, 130), width=2)
            draw.text((content_left, xp_text_y), xp_text, font=xp_font, fill=(130, 255, 160, 255), stroke_width=2, stroke_fill=(20, 20, 20, 255))
            output_frames.append(frame)

        temp_path = CACHE_DIR / (f"{user_id}_level.gif" if bg_url.lower().endswith(".gif") and supporter else f"{user_id}_level.png")
        if bg_url.lower().endswith(".gif") and supporter:
            output_frames[0].save(str(temp_path), save_all=True, append_images=output_frames[1:], duration=duration, loop=0, disposal=2)
        else:
            output_frames[0].save(str(temp_path))
        try:
            await interaction.followup.send(file=discord.File(str(temp_path)))
        finally:
            if temp_path.exists():
                temp_path.unlink()

    @app_commands.command(name="xpset", description="Set a user's XP and level (Admin only)")
    @app_commands.describe(user="User", xp="XP value", level="Level value")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def xpset(self, interaction: discord.Interaction, user: discord.Member, xp: int, level: int) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("This command can only be used in servers.", ephemeral=True)
            return
        if not await is_module_enabled(interaction.guild.id, "leveling"):
            await interaction.response.send_message(
                "This module is currently disabled. An admin can enable it with /modules.",
                ephemeral=True,
            )
            return
        guild_id = str(interaction.guild.id)
        user_id = str(user.id)
        xp_data = _load_json(XP_FILE, {})
        xp_data.setdefault(guild_id, {})
        xp_data[guild_id][user_id] = {"xp": xp, "level": level}
        _save_json(XP_FILE, xp_data)
        await _dispatch_module_event(
            self.bot,
            interaction.guild,
            "leveling",
            "xp_set",
            actor=interaction.user,
            details=f"target={user.id}; xp={xp}; level={level}",
            channel_id=interaction.channel.id if interaction.channel else None,
        )
        await interaction.response.send_message(f"✅ Set {user.display_name}'s XP to {xp} and Level to {level}.", ephemeral=True)

    @xp_group.command(name="config", description="Configure XP gain and leveling settings for your server (Admin only)")
    @app_commands.describe(
        message_xp="XP gained per message",
        reaction_xp="XP gained per reaction",
        vc_minute_xp="XP gained per minute in VC",
        poll_vote_xp="XP gained per poll vote",
        base_xp="XP required for Level 1",
        xp_scale="XP scaling factor (how much more XP per level)",
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def xp_config(
        self,
        interaction: discord.Interaction,
        message_xp: int,
        reaction_xp: int,
        vc_minute_xp: int,
        poll_vote_xp: int,
        base_xp: int,
        xp_scale: float,
    ) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("This command can only be used in servers.", ephemeral=True)
            return
        if not await is_module_enabled(interaction.guild.id, "leveling"):
            await interaction.response.send_message(
                "This module is currently disabled. An admin can enable it with /modules.",
                ephemeral=True,
            )
            return
        cfg = _load_json(CONFIG_FILE, {})
        guild_id = str(interaction.guild.id)
        cfg[guild_id] = {
            "message_xp": message_xp,
            "reaction_xp": reaction_xp,
            "vc_minute_xp": vc_minute_xp,
            "poll_vote_xp": poll_vote_xp,
            "base_xp": base_xp,
            "xp_scale": xp_scale,
        }
        _save_json(CONFIG_FILE, cfg)
        await _dispatch_module_event(
            self.bot,
            interaction.guild,
            "leveling",
            "xp_config_update",
            actor=interaction.user,
            details=(
                f"message_xp={message_xp}; reaction_xp={reaction_xp}; vc_minute_xp={vc_minute_xp}; "
                f"poll_vote_xp={poll_vote_xp}; base_xp={base_xp}; xp_scale={xp_scale}"
            ),
            channel_id=interaction.channel.id if interaction.channel else None,
        )
        preview = "\n".join(
            f"Level {lvl}: {int(sum(base_xp * (xp_scale ** (i - 1)) for i in range(1, lvl + 1)))} XP total"
            for lvl in [1, 2, 3, 5, 10]
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
            color=discord.Color.green(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @levelreward_group.command(name="add", description="Add a level reward role.")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def levelreward_add(
        self,
        interaction: discord.Interaction,
        level: int,
        role: discord.Role,
        message: str = "🎉 Congrats {user}, you reached level {level} and earned {role}!",
    ) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("This command can only be used in servers.", ephemeral=True)
            return
        if not await is_module_enabled(interaction.guild.id, "leveling"):
            await interaction.response.send_message(
                "This module is currently disabled. An admin can enable it with /modules.",
                ephemeral=True,
            )
            return
        guild_id = str(interaction.guild.id)
        data = _load_json(LEVEL_REWARDS_FILE, {})
        guild_data = data.get(guild_id, {"rewards": {}, "replace_old_roles": False})
        guild_data["rewards"][str(level)] = {"role_id": role.id, "message": message}
        data[guild_id] = guild_data
        _save_json(LEVEL_REWARDS_FILE, data)
        await _dispatch_module_event(
            self.bot,
            interaction.guild,
            "leveling",
            "levelreward_add",
            actor=interaction.user,
            details=f"level={level}; role_id={role.id}",
            channel_id=interaction.channel.id if interaction.channel else None,
        )
        await interaction.response.send_message(f"✅ Added reward for level **{level}** -> {role.mention}", ephemeral=True)

    @levelreward_group.command(name="remove", description="Remove a level reward role.")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def levelreward_remove(self, interaction: discord.Interaction, level: int) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("This command can only be used in servers.", ephemeral=True)
            return
        if not await is_module_enabled(interaction.guild.id, "leveling"):
            await interaction.response.send_message(
                "This module is currently disabled. An admin can enable it with /modules.",
                ephemeral=True,
            )
            return
        guild_id = str(interaction.guild.id)
        data = _load_json(LEVEL_REWARDS_FILE, {})
        if guild_id not in data or str(level) not in data[guild_id].get("rewards", {}):
            await interaction.response.send_message("❌ No reward found for that level.", ephemeral=True)
            return
        del data[guild_id]["rewards"][str(level)]
        _save_json(LEVEL_REWARDS_FILE, data)
        await _dispatch_module_event(
            self.bot,
            interaction.guild,
            "leveling",
            "levelreward_remove",
            actor=interaction.user,
            details=f"level={level}",
            channel_id=interaction.channel.id if interaction.channel else None,
        )
        await interaction.response.send_message(f"🗑️ Removed reward for level **{level}**.", ephemeral=True)

    @levelreward_group.command(name="list", description="List all level reward roles.")
    async def levelreward_list(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("This command can only be used in servers.", ephemeral=True)
            return
        if not await is_module_enabled(interaction.guild.id, "leveling"):
            await interaction.response.send_message(
                "This module is currently disabled. An admin can enable it with /modules.",
                ephemeral=True,
            )
            return
        guild_id = str(interaction.guild.id)
        data = _load_json(LEVEL_REWARDS_FILE, {})
        guild_data = data.get(guild_id, {}).get("rewards", {})
        if not guild_data:
            await interaction.response.send_message("ℹ️ No rewards configured yet.", ephemeral=True)
            return
        desc = ""
        for lvl, info in sorted(guild_data.items(), key=lambda x: int(x[0])):
            role = interaction.guild.get_role(int(info["role_id"]))
            desc += f"**Level {lvl}** -> {role.mention if role else '❓ Missing Role'}\n"
        await interaction.response.send_message(
            embed=discord.Embed(title="🎁 Level Rewards", description=desc, color=discord.Color.gold()),
            ephemeral=True,
        )

    @levelreward_group.command(name="mode", description="Choose whether to replace old reward roles.")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def levelreward_mode(self, interaction: discord.Interaction, replace_old_roles: bool) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("This command can only be used in servers.", ephemeral=True)
            return
        if not await is_module_enabled(interaction.guild.id, "leveling"):
            await interaction.response.send_message(
                "This module is currently disabled. An admin can enable it with /modules.",
                ephemeral=True,
            )
            return
        guild_id = str(interaction.guild.id)
        data = _load_json(LEVEL_REWARDS_FILE, {})
        guild_data = data.get(guild_id, {"rewards": {}, "replace_old_roles": False})
        guild_data["replace_old_roles"] = replace_old_roles
        data[guild_id] = guild_data
        _save_json(LEVEL_REWARDS_FILE, data)
        await _dispatch_module_event(
            self.bot,
            interaction.guild,
            "leveling",
            "levelreward_mode",
            actor=interaction.user,
            details=f"replace_old_roles={replace_old_roles}",
            channel_id=interaction.channel.id if interaction.channel else None,
        )
        await interaction.response.send_message(
            "✅ Now removing old reward roles." if replace_old_roles else "⚙️ Now keeping old reward roles.",
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    cog = LevelingCog(bot)
    # add_cog() automatically registers any app_commands.Group class attributes,
    # so we must NOT call bot.tree.add_command() for xp_group / levelreward_group here.
    await bot.add_cog(cog)
