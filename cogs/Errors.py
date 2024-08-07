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
        print(f"Error running command Interaction: {interaction} Error: {error}")
        # Check if the interaction has been deferred
        if not interaction.response.is_done():
            await interaction.response.defer()
        if isinstance(error, CommandNotFound):
            await interaction.followup.send(
                "No Command Found - Commands may not be synced - Please do /sync",
                ephemeral=True,
            )
        elif isinstance(error, MissingPermissions):
            await interaction.followup.send(
                f"Missing Permissions - Permissions need {error.missing_permissions}",
                ephemeral=True,
            )
        elif isinstance(error, CommandOnCooldown):
            await interaction.followup.send(
                "Command on cooldown, Retry in {:.2f}s".format(error.retry_after),
                ephemeral=True,
            )
        else:
            await interaction.followup.send(
                f"Something went wrong {interaction} {error}", ephemeral=True
            )
            print(error)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Errors(bot), guilds=MY_GUILDS)
    print("Errors is Loaded")
