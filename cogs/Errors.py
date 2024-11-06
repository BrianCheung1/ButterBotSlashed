from discord import Interaction
from discord.app_commands import (
    AppCommandError,
    MissingPermissions,
    CommandNotFound,
    CommandOnCooldown,
)
from discord.ext import commands
from dotenv import load_dotenv
import discord
import os
import logging

# Set up logging for better error tracking
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

load_dotenv()
list_of_guilds = os.getenv("GUILDS").split(",")
MY_GUILDS = [discord.Object(id=int(guild)) for guild in list_of_guilds]


class Errors(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        # -> Option 1 ---
        # setting the handler
        bot.tree.on_error = self.on_app_command_error

    # -> Option 1 ---
    # the global error handler for all app commands (slash & ctx menus)
    async def on_app_command_error(
        self, interaction: discord.Interaction, error: AppCommandError
    ):
        # Log the error for further analysis
        logger.error(f"Error running command Interaction: {interaction} Error: {error}")

        # Check if the interaction has been deferred
        if not interaction.response.is_done():
            await interaction.response.defer()

        # Handle specific error types
        if isinstance(error, CommandNotFound):
            await interaction.followup.send(
                "No Command Found - Commands may not be synced. Please try using `/sync`.",
                ephemeral=True,
            )
        elif isinstance(error, MissingPermissions):
            await interaction.followup.send(
                f"Missing Permissions - You need the following permissions: {', '.join(error.missing_permissions)}.",
                ephemeral=True,
            )
        elif isinstance(error, CommandOnCooldown):
            await interaction.followup.send(
                f"Command on cooldown. Please try again in {error.retry_after:.2f} seconds.",
                ephemeral=True,
            )
        else:
            # Generic error message
            await interaction.followup.send(
                "Something went wrong while processing your request. Please try again later.",
                ephemeral=True,
            )
            # Log the detailed error for debugging
            logger.error(f"Unexpected error: {error}")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Errors(bot), guilds=MY_GUILDS)
    print("Errors is Loaded")
