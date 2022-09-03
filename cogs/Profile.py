import discord
from discord import app_commands
from discord.ext import commands
import os
from dotenv import load_dotenv
from typing import Literal, Union, NamedTuple, Optional
from datetime import datetime, timezone
from discord.ui import Button, View
from discord import ButtonStyle

load_dotenv()
GAMES = os.getenv('GAMES')
list_of_guilds = os.getenv("GUILDS").split(",")
MY_GUILDS = [discord.Object(id=int(guild)) for guild in list_of_guilds]


class Profile(commands.Cog):
    """Information about Users"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="profile", description="Shows basic info of a member")
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
        role_names = [role.mention for role in mentionedUser.roles[1:]]
        count = len(role_names)
        all_roles = " ".join(role_names)
        if (len(all_roles) >= 1000):
            all_roles = all_roles[:1000].rsplit("<@&", 1)[0] + "..."
        if (len(all_roles)) == 0:
            all_roles = "`None ` "

        # member joined date - today date to measure total days in server
        days_in_server = abs((datetime.now().replace(
            tzinfo=None) - mentionedUser.joined_at.replace(tzinfo=None)).days)

        embed = discord.Embed(
            title=f'Profile of {mentionedUser.name}', color=mentionedUser.accent_color)
        embed.add_field(name="Username",
                        value=mentionedUser.name, inline=True)
        embed.add_field(name="Tag",
                        value=mentionedUser.discriminator, inline=True)
        if (mentionedUser.display_name != mentionedUser.name):
            embed.add_field(name="Nickname",
                            value=mentionedUser.display_name, inline=True)
        embed.add_field(name="ID",
                        value=mentionedUser.id, inline=False)
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

        view = View()
        button = Button(
            label='Download avatar', url=str(mentionedUser.avatar.url), style=ButtonStyle.url)
        view.add_item(button)

        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="server-info", description="Shows information about the server")
    async def server_info(self, interaction: discord.Interaction):
        """test"""
        server = interaction.user.guild
        embed = discord.Embed(title=f'Information about {server.name}')
        embed.add_field(name="Owner 👑", value=server.owner, inline=True)
        embed.add_field(name="Server ID", value=server.id, inline=True)
        embed.add_field(name="Server Creation Date",
                        value=f'{discord.utils.format_dt(server.created_at)}', inline=False)
        embed.add_field(name="Voice Channels",
                        value=f'{len(server.voice_channels)}', inline=True)
        embed.add_field(name="Text Channels",
                        value=f'{len(server.text_channels)}', inline=True)
        embed.add_field(name="Members",
                        value=server.member_count, inline=True)

        role_names = [role.mention for role in server.roles[1:]]
        count = len(role_names)
        all_roles = " ".join(role_names)
        if (len(all_roles) >= 1000):
            all_roles = all_roles[:1000].rsplit("<@&", 1)[0] + "..."
        elif (len(all_roles)) == 0:
            all_roles = "`None ` "

        embed.add_field(name=f'Roles - {count}',
                        value=f'{all_roles}', inline=False)

        embed.set_thumbnail(url=server.icon)
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(
        Profile(bot),
        guilds=MY_GUILDS
    )
    print("Profile is Loaded")
