"""
Test module for verifying module refresh_registry functionality.
This module adds a simple /test command to verify it was loaded.
"""

import discord
from discord import app_commands
from discord.ext import commands

# Optional metadata for module discovery
__module_display_name__ = "Test Module"
__module_description__ = "Simple test module for verifying module refresh_registry works."
__module_category__ = "utilities"


class TestModuleCog(commands.Cog):
    """Test cog that adds a /test command."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="test", description="Test command to verify module loading.")
    async def test_command(self, interaction: discord.Interaction) -> None:
        """Simple test command that responds with a confirmation."""
        await interaction.response.send_message(
            "✅ Test module loaded successfully! Module refresh_registry is working.",
            ephemeral=True
        )


async def setup(bot: commands.Bot) -> None:
    """Setup function required for discord.py extension loading."""
    await bot.add_cog(TestModuleCog(bot))
