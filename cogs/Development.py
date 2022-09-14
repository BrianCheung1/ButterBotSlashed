from datetime import datetime
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
from typing import Literal, Optional
import discord
import os
import platform

load_dotenv()
list_of_guilds = os.getenv("GUILDS").split(",")
MY_GUILDS = [discord.Object(id=int(guild)) for guild in list_of_guilds]


class Development(commands.Cog):
    """Development Commands"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="reload", description="Reload cogs")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def reload(
        self,
        interaction: discord.Interaction,
        cog: Optional[
            Literal[
                "development",
                "economy",
                "errors",
                "games",
                "general",
                "gifs",
                "math",
                "minecraft",
                "moderation",
                "profile",
                "test",
            ]
        ] = None,
    ):
        """Reload Cogs"""
        await interaction.response.defer()
        if not cog:
            for filename in os.listdir("./cogs"):
                if filename.endswith(".py"):
                    await self.bot.reload_extension(f"cogs.{filename[:-3]}")
            await interaction.followup.send("Cogs Reloaded", ephemeral=True)
        else:
            await self.bot.reload_extension(f"cogs.{cog}")
            await interaction.followup.send(f"{cog.title()} Reloaded", ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message):
        # if the author of a message is a bot stop
        if message.author.bot:
            return
        print(
            f'[{str(message.channel).title()}][{datetime.now().strftime("%I:%M:%S:%p")}] {message.author}: {message.content}'
        )

    @app_commands.command(name="ping", description="Shows Bot Latency")
    async def ping(self, interaction: discord.Interaction):
        """Shows Bot Latency"""

        await interaction.response.send_message(
            f"**Pong**: *{round(self.bot.latency*1000)}ms*"
        )

    @app_commands.command(name="sync", description="Syncs commands to all servers")
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.checks.cooldown(1, 5, key=lambda i: (i.guild_id, i.user.id))
    async def sync(
        self,
        interaction: discord.Interaction,
        server: Optional[Literal["This Server", "All Servers"]] = None,
    ):
        """Syncs commands to all servers"""
        # loops through the servers of the bot
        # reloading the cogs for each server
        # sync the commands for each guild
        await interaction.response.defer()
        if not server:
            for filename in os.listdir(f"./cogs"):
                if filename.endswith(".py"):
                    await self.bot.reload_extension(f"cogs.{filename[:-3]}")
            await self.bot.tree.sync(guild=discord.Object(int(interaction.guild.id)))
            await interaction.followup.send(f"{interaction.guild.name} synced")
        elif server == "All Server":
            for filename in os.listdir(f"./cogs"):
                if filename.endswith(".py"):
                    await self.bot.reload_extension(f"cogs.{filename[:-3]}")

            await self.bot.tree.sync()
            await interaction.followup.send(f"{len(self.bot.guilds)} servers synced")

    @app_commands.command(name="stats", description="show stats of the bot")
    async def stats(self, interaction: discord.Interaction):
        guild_count = 0
        user_count = 0
        cog_count = 0
        for guild in self.bot.guilds:
            guild_count += 1
            user_count += guild.member_count

        for filename in os.listdir("cogs/"):
            if filename.endswith(".py"):
                cog_count += 1

        embed = discord.Embed(title=f"{self.bot.user.display_name} stats")
        embed.add_field(
            name="Ping", value=f"{round(self.bot.latency*1000)}ms", inline=True
        )
        embed.add_field(name="Total Servers", value=f"{guild_count}", inline=True)
        embed.add_field(name="Total Members", value=f"{user_count}", inline=True)
        # embed.add_field(name="Uptime", value=f"{start_time}", inline=False)

        embed.add_field(
            name="Discord.py Version", value=f"{discord.__version__}", inline=True
        )
        embed.add_field(
            name="Python Version", value=f"{platform.python_version()}", inline=True
        )
        embed.add_field(name="Total Cogs", value=f"{cog_count}", inline=False)
        embed.set_thumbnail(url=self.bot.user.display_avatar)
        embed.timestamp = datetime.now()
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Development(bot), guilds=MY_GUILDS)
    print("Development is Loaded")
