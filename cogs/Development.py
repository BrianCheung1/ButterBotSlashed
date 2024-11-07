from datetime import datetime
from discord import app_commands
from discord.ext import commands, tasks
from typing import Literal, Optional
import discord
import os
import platform
import random
import asyncio


class Development(commands.Cog):
    """Development Commands"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.my_background_task.start()

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
                "music",
                "profile",
                "test",
            ]
        ] = None,
    ):
        """Reload Cogs"""
        await interaction.response.defer()

        if cog:
            await self.bot.reload_extension(f"cogs.{cog}")
            await interaction.followup.send(f"{cog.title()} Reloaded", ephemeral=True)
        else:
            cogs = [
                filename[:-3]
                for filename in os.listdir("./cogs")
                if filename.endswith(".py")
            ]
            await asyncio.gather(
                *[self.bot.reload_extension(f"cogs.{cog}") for cog in cogs]
            )
            await interaction.followup.send("Cogs Reloaded", ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message):
        # if the author of a message is a bot stop
        if message.author.bot:
            return
        print(
            f'[{str(message.guild).title()}][{str(message.channel).title()}][{datetime.now().strftime("%I:%M:%S:%p")}] {message.author}: {message.content}'
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
        """Syncs commands to all servers and lists synced command names."""
        await interaction.response.defer()

        if server == "All Servers":
            # Re-sync the current commands globally
            synced = await self.bot.tree.sync()
            command_list = "\n".join([f"- `{cmd.name}`" for cmd in synced])
            await interaction.followup.send(
                f"Synced {len(synced)} commands globally"
            )
        else:
            # Re-sync the current commands in the guild
            synced = await self.bot.tree.sync(guild=guild)
            command_list = "\n".join([f"- `{cmd.name}`" for cmd in synced])
            await interaction.followup.send(
                f"Synced commands to {guild.name}"
            )

    @app_commands.command(name="stats", description="show stats of the bot")
    async def stats(self, interaction: discord.Interaction):

        guild_count = len(self.bot.guilds)
        user_count = sum(guild.member_count for guild in self.bot.guilds)
        cog_count = len(
            [filename for filename in os.listdir("cogs/") if filename.endswith(".py")]
        )
        slash_command_count = len(self.bot.tree.get_commands())

        # Format uptime
        uptime = datetime.now() - self.bot.start_time
        days, remainder = divmod(int(uptime.total_seconds()), 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        duration_formatted = f"{days}D:{hours}H:{minutes}M"

        embed = discord.Embed(title=f"{self.bot.user.display_name} stats")
        embed.add_field(
            name="Ping", value=f"{round(self.bot.latency*1000)}ms", inline=True
        )
        embed.add_field(name="Total Servers", value=f"{guild_count}", inline=True)
        embed.add_field(name="Total Members", value=f"{user_count}", inline=True)

        uptime = datetime.now() - self.bot.start_time
        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        days, hours = divmod(hours, 24)
        duration_formatted = f"{days}D:{hours}H:{minutes}M"

        embed = discord.Embed(title=f"{self.bot.user.display_name} stats")
        embed.add_field(
            name="Ping", value=f"{round(self.bot.latency*1000)}ms", inline=True
        )
        embed.add_field(name="Total Servers", value=f"{guild_count}", inline=True)
        embed.add_field(name="Total Members", value=f"{user_count}", inline=True)
        embed.add_field(name="Uptime", value=f"{duration_formatted}", inline=True)
        embed.add_field(
            name="Discord.py Version", value=f"{discord.__version__}", inline=True
        )
        embed.add_field(
            name="Python Version", value=f"{platform.python_version()}", inline=True
        )
        embed.add_field(name="Total Cogs", value=f"{cog_count}", inline=True)
        embed.add_field(
            name="Total Slash Commands", value=f"{slash_command_count}", inline=True
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar)
        embed.timestamp = datetime.now()
        await interaction.response.send_message(embed=embed)

    @tasks.loop(minutes=5)  # Update status every 5 minutes
    async def my_background_task(self):
        randomStatus = ["Valorant", "Apex Legends", "League Of Legends"]
        try:
            await self.bot.change_presence(
                activity=discord.Activity(
                    type=discord.ActivityType.competing,
                    name=random.choice(randomStatus),
                )
            )
        except discord.HTTPException as e:
            if e.status == 429:  # Rate limit status code
                retry_after = int(e.response.headers.get("Retry-After", 5))
                await asyncio.sleep(retry_after)
                await self.bot.change_presence(
                    activity=discord.Activity(
                        type=discord.ActivityType.competing,
                        name=random.choice(randomStatus),
                    )
                )

    @my_background_task.before_loop
    async def before_my_task(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Development(bot))
    print("Development is Loaded")
