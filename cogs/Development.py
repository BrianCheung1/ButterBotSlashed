from pydoc import describe
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv
list_of_guilds = os.getenv("GUILDS").split(",")
MY_GUILDS = [discord.Object(id=int(guild)) for guild in list_of_guilds]


class Development(commands.Cog):
    """Development Commands"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="reload", description="Reload cogs")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def reload(self, interaction: discord.Interaction) -> None:
        """Reload Cogs"""
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                await self.bot.reload_extension(f'cogs.{filename[:-3]}')
        await interaction.response.send_message("Cogs Reloaded", ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message):
        # if the author of a message is a bot stop
        if message.author.bot:
            return
        print(
            f'[{str(message.channel).title()}][{datetime.now().strftime("%I:%M:%S:%p")}] {message.author}: {message.content}')

    @commands.Cog.listener()
    async def on_application_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        print("test")

    @app_commands.command(name="ping", description="Shows Bot Latency")
    async def ping(self, interaction: discord.Interaction):
        """Shows Bot Latency"""
        await interaction.response.send_message(f'**Pong**: *{round(self.bot.latency*1000)}ms*')

    @app_commands.command(name="sync", description="Syncs commands to all servers")
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.checks.cooldown(1, 30, key=lambda i: (i.guild_id, i.user.id))
    async def sync(self, interaction: discord.Interaction):
        """Syncs commands to all servers"""
        count = 0
        # loops through the servers of the bot
        # reloading the cogs for each server
        # sync the commands for each guild
        for guild in self.bot.guilds:
            for filename in os.listdir(f'./cogs'):
                if filename.endswith('.py'):
                    await self.bot.reload_extension(f'cogs.{filename[:-3]}')
            await self.bot.tree.sync(guild=discord.Object(int(guild.id)))
            count += 1
        await interaction.response.send_message(f'{count} servers synced')


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(
        Development(bot),
        guilds=MY_GUILDS
    )
    print("Development is Loaded")
