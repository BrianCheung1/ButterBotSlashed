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
        # bot.tree.on_error = self.on_app_command_error

    # -> Option 1 ---
    # the global error handler for all app commands (slash & ctx menus)
    async def on_app_command_error(
        self, interaction: Interaction, error: AppCommandError
    ):
        if isinstance(error, CommandNotFound):
            await interaction.response.send_message(
                "No Command Found - Commands may not be synced - Please do /sync",
                ephemeral=True,
            )
        elif isinstance(error, MissingPermissions):
            await interaction.response.send_message(
                f"Missing Permissions - Permissions need {error.missing_permissions}",
                ephemeral=True,
            )
        elif isinstance(error, CommandOnCooldown):
            await interaction.response.send_message(
                "Command on cooldown, Retry in {:.2f}s".format(error.retry_after),
                ephemeral=True,
            )
        else:
            print(error)
            await interaction.response.send_message(
                f"Error with Command - {error}", ephemeral=True
            )

    # -> Option 2 ---
    # the error handler for slash commands in this cog
    # async def cog_app_command_error(
    #     self,
    #     interaction: Interaction,
    #     error: AppCommandErro
    # ):
    #     print("This error was handled with option 2 from ?tag treeerrorcog")
    #     ...


# add and load the cog like normal


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Errors(bot), guilds=MY_GUILDS)
    print("Errors is Loaded")
