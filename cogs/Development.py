import asyncio
import os
import platform
import random
from collections import defaultdict
from datetime import datetime
from typing import Literal, Optional

import aiosqlite
import discord
from discord import app_commands
from discord.ext import commands, tasks

from utils.logging import send_error_to_support_channel
from utils.stats import get_user_data

GUILD_ID = 152954629993398272


class Development(commands.Cog):
    """Development Commands"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.my_background_task.start()

    # Custom check to allow only the bot owner
    def is_owner_check(interaction: discord.Interaction) -> bool:
        return (
            interaction.user.id == interaction.client.owner_id
            or interaction.user.id == 1047615361886982235
        )

    @app_commands.command(name="reload", description="Reload cogs")
    @app_commands.check(is_owner_check)
    @app_commands.guilds(discord.Object(id=GUILD_ID))
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

    @app_commands.command(name="ping", description="Shows Bot Latency")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def ping(self, interaction: discord.Interaction):
        """Shows Bot Latency"""

        await interaction.response.send_message(
            f"**Pong**: *{round(self.bot.latency*1000)}ms*"
        )

    @app_commands.command(name="sync", description="Syncs commands to all servers")
    @app_commands.check(is_owner_check)
    @app_commands.checks.cooldown(1, 5, key=lambda i: (i.guild_id, i.user.id))
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def sync(
        self,
        interaction: discord.Interaction,
    ):
        """Syncs commands to all servers and lists synced command names."""
        await interaction.response.defer()
        synced = await self.bot.tree.sync()
        syncedGuild = await self.bot.tree.sync(guild=discord.Object(id=GUILD_ID))

        await interaction.followup.send(
            f"Synced {len(synced)} commands globally to {len(self.bot.guilds)} guilds\n"
            f"Synced {len(syncedGuild)} commands  to {interaction.guild} guild"
        )

    @app_commands.command(
        name="list_commands", description="Lists all synced commands in this server."
    )
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def list_commands(self, interaction: discord.Interaction):
        await interaction.response.defer()

        # Get the synced commands for this guild
        guild_commands = self.bot.tree.get_commands(guild=discord.Object(id=GUILD_ID))
        global_commands = self.bot.tree.get_commands()
        # Initialize dictionaries to store commands by cog/module
        global_commands_by_cog = defaultdict(list)
        guild_commands_by_cog = defaultdict(list)

        # Organize global commands by cog/module
        for cmd in global_commands:
            cog_name = cmd.module or "No Cog"
            global_commands_by_cog[cog_name].append(cmd.name)

        # Organize guild-specific commands by cog/module
        for cmd in guild_commands:
            cog_name = cmd.module or "No Cog"
            guild_commands_by_cog[cog_name].append(cmd.name)

        # Format the output by cog/module
        global_command_list = "\n".join(
            [
                f"**{cog}**:\n" + "\n".join([f"- `{cmd}`" for cmd in cmds])
                for cog, cmds in global_commands_by_cog.items()
            ]
        )
        guild_command_list = "\n".join(
            [
                f"**{cog}**:\n" + "\n".join([f"- `{cmd}`" for cmd in cmds])
                for cog, cmds in guild_commands_by_cog.items()
            ]
        )

        # Send the organized command lists
        await interaction.followup.send(
            f"**Global Commands**: {len(global_commands)} \n{global_command_list}\n\n**Guild-Specific Commands**: {len(guild_commands)}\n{guild_command_list}"
        )

    @app_commands.command(name="stats", description="show stats of the bot")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
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

    @app_commands.command(name="error", description="raise an error")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def error_command(self, interaction: discord.Interaction):
        try:
            # Some code that could raise an error
            raise ValueError(
                "This is a test error"
            )  # Simulating an error for demonstration

        except Exception as e:
            # Error occurred, send the error details to the support channel
            error_message = str(e)
            await send_error_to_support_channel(
                bot=interaction.client,  # Pass the bot instance
                target_guild_id=152954629993398272,  # Replace with the actual target guild ID
                target_channel_id=455431053528793098,  # Replace with the actual channel ID
                error=error_message,
                interaction=interaction,
                admin_user=None,  # You can provide an admin user if needed
            )

    @app_commands.command(name="update_tables", description="Update database")
    @app_commands.check(is_owner_check)
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def update_tables(self, interaction: discord.Interaction):
        """Update the movies table for all guilds to include the added_by column."""
        await interaction.response.send_message("Starting database updates...")

        updates = []  # Collect messages for each guild
        for guild in self.bot.guilds:
            db_name = self.get_db_name(guild.id)
            try:
                await self.modify_table_to_add_added_by(db_name)
                updates.append(
                    f"✅ Updated database for guild: **{guild.name}** ({guild.id})"
                )
            except Exception as e:
                updates.append(
                    f"❌ Failed to update database for guild: **{guild.name}** ({guild.id}). Error: {e}"
                )

        # Send a final update message
        result_message = "\n".join(updates)
        await interaction.followup.send(f"Database Update Results:\n{result_message}")

    @app_commands.command(
        name="sync_all_users",
        description="Sync stats for all users across all servers.",
    )
    @app_commands.check(is_owner_check)
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def sync_all_users(self, interaction: discord.Interaction):
        """Loops through all guilds and members to sync their stats."""
        await interaction.response.send_message("⏳ Syncing all users' stats...")

        updated = 0
        failed = 0

        for guild in self.bot.guilds:
            for member in guild.members:
                if member.bot:
                    continue
                try:
                    get_user_data(member)  # This handles sync/init logic
                    updated += 1
                except Exception as e:
                    print(f"[❌] Failed to sync {member.display_name}: {e}")
                    failed += 1

        await interaction.followup.send(
            f"✅ Synced stats for **{updated}** users\n❌ Failed for **{failed}** users"
        )

    def get_db_name(self, guild_id):
        """Generate a unique database name based on the guild ID."""
        return os.path.join(self.db_folder, f"movies_{guild_id}.db")

    async def modify_table_to_add_added_by(self, db_name):
        async with aiosqlite.connect(db_name) as db:
            # Step 1: Create the new table with the added_by column
            await db.execute(
                """
                CREATE TABLE movies_new (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    link TEXT NOT NULL UNIQUE,
                    added_by TEXT
                )
                """
            )

            # Step 2: Copy data from the old table to the new table
            await db.execute(
                "INSERT INTO movies_new (id, name, link) SELECT id, name, link FROM movies"
            )

            # Step 3: Drop the old table
            await db.execute("DROP TABLE movies")

            # Step 4: Rename the new table
            await db.execute("ALTER TABLE movies_new RENAME TO movies")

            await db.commit()

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

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Ensure new member has a stat entry on join."""
        try:
            get_user_data(member)
            print(f"[✅] Synced stats for new member: {member.display_name}")
        except Exception as e:
            print(f"[❌] Failed to sync stats for {member.display_name}: {e}")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Development(bot), guild=discord.Object(id=GUILD_ID))
    print("Development is Loaded")
