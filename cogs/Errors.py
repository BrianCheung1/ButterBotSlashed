import logging

import discord
from discord import Forbidden, NotFound
from discord.app_commands import (
    AppCommandError,
    CheckFailure,
    CommandNotFound,
    CommandOnCooldown,
    MissingPermissions,
    CommandInvokeError,
)
from discord.ext import commands

# Set up logging for better error tracking
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)


class Errors(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        bot.tree.on_error = self.on_app_command_error

    # the global error handler for all app commands (slash & ctx menus)
    @commands.Cog.listener()
    async def on_app_command_error(
        self, interaction: discord.Interaction, error: AppCommandError
    ):
        # Log the error for further analysis
        logger.error(f"Error running command Interaction: {interaction} Error: {error}")

        # Get the user to ping for feedback (replace with actual user ID or username)
        admin_user_id = 1047615361886982235  # Replace with the admin's Discord user ID
        admin_user = self.bot.get_user(admin_user_id)

        # The specific server/channel ID where the error should be sent
        target_guild_id = 152954629993398272  # Replace with the target guild ID
        target_channel_id = 455431053528793098  # Replace with the target channel ID

        try:
            # Ensure the interaction response is not sent if the interaction is invalid
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
            elif isinstance(error, CommandInvokeError):
                original = getattr(error, "original", error)
                await interaction.followup.send(
                    "An error occurred while processing your command. Please try again.",
                    ephemeral=True,
                )
                logger.error(f"Original error: {original}")
            elif isinstance(error, NotFound):
                await interaction.followup.send(
                    "The command or resource was not found.",
                    ephemeral=True,
                )
            elif isinstance(error, Forbidden):
                await interaction.followup.send(
                    "I do not have permission to perform this action.",
                    ephemeral=True,
                )
            elif isinstance(error, CheckFailure):
                await interaction.followup.send(
                    "Only owner for this bot can use this command.",
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
        except NotFound as nf_error:
            # Handle the 'Unknown interaction' error explicitly here
            logger.error(
                f"Interaction not found (likely expired or invalid): {nf_error}"
            )
            return  # Don't proceed further if the interaction is invalid
        finally:
            # Send error details to a specific channel in another server
            target_guild = self.bot.get_guild(target_guild_id)
            if target_guild:
                target_channel = target_guild.get_channel(target_channel_id)
                if target_channel:
                    # Send the error details to the support channel
                    await target_channel.send(
                        f"Error occurred in {interaction.guild.name} ({interaction.guild.id}):\n"
                        f"Command: `/{interaction.command.name}` triggered by {interaction.user.name} ({interaction.user.id})\n"
                        f"Error: {error}"
                    )
                    # Ping the admin user in the support channel for feedback
                    if admin_user:
                        await target_channel.send(
                            f"<@{admin_user.id}>, Please check the error!"
                        )
                    else:
                        logger.error(f"Admin user {admin_user_id} not found.")
                else:
                    logger.error(
                        f"Channel {target_channel_id} not found in guild {target_guild_id}."
                    )
            else:
                logger.error(f"Guild {target_guild_id} not found.")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Errors(bot))
    print("Errors is Loaded")
