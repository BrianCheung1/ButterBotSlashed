from datetime import datetime, timezone
from discord import ButtonStyle, app_commands
from discord.ext import commands
from discord.ui import Button, View
from dotenv import load_dotenv
from pymongo import MongoClient
from typing import Literal, Union, NamedTuple, Optional
import discord
import os

load_dotenv()
list_of_guilds = os.getenv("GUILDS").split(",")
MY_GUILDS = [discord.Object(id=int(guild)) for guild in list_of_guilds]
GAMES = os.getenv("GAMES")
MONGO_URL = os.getenv("ATLAS_URI")
cluster = MongoClient(MONGO_URL)
db = cluster["Users"]
collection = db["UserData"]


class Profile(commands.Cog):
    """Information about Users"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="profile", description="Shows basic info of a member")
    @app_commands.describe(member="The profile of a user")
    # @app_commands.checks.cooldown(1, 10, key=lambda i: (i.guild_id, i.user.id))
    async def profile(
        self, interaction: discord.Interaction, member: Optional[discord.Member]
    ):
        """Shows basic info of a member"""
        if not member:
            member = interaction.user
        # .roles gives id and name
        # list compression for only role names
        # convert list to more readable text
        role_names = [role.mention for role in member.roles[1:]]
        count = len(role_names)
        all_roles = " ".join(role_names)
        if len(all_roles) >= 1000:
            all_roles = all_roles[:1000].rsplit("<@&", 1)[0] + "..."
        if (len(all_roles)) == 0:
            all_roles = "`None ` "

        # member joined date - today date to measure total days in server
        days_in_server = abs(
            (
                datetime.now().replace(tzinfo=None)
                - member.joined_at.replace(tzinfo=None)
            ).days
        )

        embed = discord.Embed(
            title=f"Profile of {member.name}", color=member.accent_color
        )
        embed.add_field(name="Username", value=member.name, inline=True)
        embed.add_field(name="Tag", value=member.discriminator, inline=True)
        if member.display_name != member.name:
            embed.add_field(name="Nickname", value=member.display_name, inline=True)
        embed.add_field(name="ID", value=member.id, inline=False)
        embed.add_field(
            name="Creation Date of Account",
            value=f"{discord.utils.format_dt(member.created_at)}",
            inline=False,
        )
        embed.add_field(
            name="Joined Date",
            value=f"{discord.utils.format_dt(member.joined_at)}",
            inline=False,
        )
        embed.add_field(name="Days in Server", value=f"{days_in_server}", inline=True)
        embed.add_field(name="Activity", value=f"{member.activity}", inline=True)

        search = {"_id": member.id}
        if collection.count_documents(search) == 0:
            post = {"_id": member.id, "balance": 1000}
            collection.insert_one(post)
        user = collection.find(search)
        for result in user:
            balance = result["balance"]

        embed.add_field(name="Balance", value=f"${float(balance):,.2f}", inline=True)
        embed.add_field(name=f"Roles - {count}", value=f"{all_roles}", inline=False)
        embed.set_image(url=member.display_avatar)
        embed.timestamp = datetime.now()
        embed.set_footer(text=f"{member}", icon_url=member.avatar)

        view = View()
        button = Button(
            label="Download avatar",
            url=str(member.display_avatar.url),
            style=ButtonStyle.url,
        )
        view.add_item(button)

        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(
        name="server-info", description="Shows information about the server"
    )
    async def server_info(self, interaction: discord.Interaction):
        """test"""
        server = interaction.user.guild
        embed = discord.Embed(title=f"Information about {server.name}")
        embed.add_field(name="Owner 👑", value=server.owner, inline=True)
        embed.add_field(name="Server ID", value=server.id, inline=True)
        embed.add_field(
            name="Server Creation Date",
            value=f"{discord.utils.format_dt(server.created_at)}",
            inline=False,
        )
        embed.add_field(
            name="Voice Channels", value=f"{len(server.voice_channels)}", inline=True
        )
        embed.add_field(
            name="Text Channels", value=f"{len(server.text_channels)}", inline=True
        )
        embed.add_field(name="Members", value=server.member_count, inline=True)

        role_names = [role.mention for role in server.roles[1:]]
        count = len(role_names)
        all_roles = " ".join(role_names)
        if len(all_roles) >= 1000:
            all_roles = all_roles[:1000].rsplit("<@&", 1)[0] + "..."
        elif (len(all_roles)) == 0:
            all_roles = "`None ` "

        embed.add_field(name=f"Roles - {count}", value=f"{all_roles}", inline=False)

        embed.set_thumbnail(url=server.icon)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="balance", description="Shows balance of user")
    async def balance(
        self, interaction: discord.Interaction, member: Optional[discord.Member]
    ):
        if not member:
            member = interaction.user

        search = {"_id": member.id}
        if collection.count_documents(search) == 0:
            post = {"_id": member.id, "balance": 1000}
            collection.insert_one(post)
        user = collection.find(search)
        for result in user:
            balance = result["balance"]
        await interaction.response.defer()
        await interaction.followup.send(f"💳{member.mention} has ${balance:,.2f}")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Profile(bot), guilds=MY_GUILDS)
    print("Profile is Loaded")
