"""Shared permission checks for app commands."""

from __future__ import annotations

import discord
from discord import app_commands


class MissingRoleOrModeratePermission(app_commands.CheckFailure):
    """Raised when user lacks Manage Roles, Moderate Members, or Manage Server."""

    pass


async def can_manage_roles_or_moderate(interaction: discord.Interaction) -> bool:
    """
    Allow Manage Roles, Moderate Members, Manage Server, or Administrator.
    Use for mute, role, and muterole commands.
    """
    if interaction.guild is None:
        raise app_commands.CheckFailure("This command can only be used in servers.")
    perms = interaction.user.guild_permissions
    if perms.manage_roles or perms.moderate_members or perms.manage_guild or perms.administrator:
        return True
    raise MissingRoleOrModeratePermission()
