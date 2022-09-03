import discord
from discord import app_commands
from discord.ext import commands
import os
from dotenv import load_dotenv
from typing import Literal, Union, NamedTuple, Optional
from datetime import datetime, timezone

load_dotenv()
GAMES = os.getenv('GAMES')
list_of_guilds = os.getenv("GUILDS").split(",")
MY_GUILDS = [discord.Object(id=int(guild)) for guild in list_of_guilds]


class Profile(commands.Cog):
    """Information about Users"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="profile")
    @app_commands.describe(member='The profile of a user')
    # @app_commands.checks.cooldown(1, 10, key=lambda i: (i.guild_id, i.user.id))
    async def profile(self, interaction: discord.Interaction, member: Optional[discord.Member]):
        """Shows basic info of a member"""
        if not member:
            mentionedUser = interaction.user
        else:
            mentionedUser = member

        # .roles gives id and name
        # list compression for only role names
        # convert list to more readable text
        role_names = [role.name for role in mentionedUser.roles]
        all_roles = ""
        count = 0
        for role in role_names:
            if role != "@everyone":
                all_roles += f'`{role} ` '
                count += 1
        if (len(all_roles)) == 0:
            all_roles = "`None ` "

        # member joined date - today date to measure total days in server
        days_in_server = abs((datetime.now().replace(
            tzinfo=None) - mentionedUser.joined_at.replace(tzinfo=None)).days)

        embed = discord.Embed(
            title=f'Profile of {mentionedUser.name}', color=mentionedUser.accent_color, description=f'ID: {mentionedUser.id}\n#: {mentionedUser.discriminator}')
        embed.add_field(name="Creation Date of Account",
                        value=f'{discord.utils.format_dt(mentionedUser.created_at)}', inline=False)
        embed.add_field(name="Joined Date",
                        value=f'{discord.utils.format_dt(mentionedUser.joined_at)}', inline=False)
        embed.add_field(name="Days in Server",
                        value=f'{days_in_server}', inline=True)
        embed.add_field(name="Activity",
                        value=f'{mentionedUser.activity}', inline=True)
        embed.add_field(name=f'Roles - {count}',
                        value=f'{all_roles}', inline=False)
        embed.set_image(url=mentionedUser.display_avatar)
        embed.timestamp = datetime.now()
        embed.set_footer(text=f'{mentionedUser}',
                         icon_url=mentionedUser.avatar)
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(
        Profile(bot),
        guilds=MY_GUILDS
    )
    print("Profile is Loaded")
