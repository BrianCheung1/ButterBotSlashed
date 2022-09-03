
import discord
from discord import app_commands
from discord.ext import commands
import os
from dotenv import load_dotenv
from typing import Literal, Union, NamedTuple, Optional
import requests
import json
from datetime import datetime
from discord.ui import Button, View
from discord import ButtonStyle

from bs4 import BeautifulSoup

load_dotenv()
GAMES = os.getenv('GAMES')
IP = os.getenv('IP')
list_of_guilds = os.getenv("GUILDS").split(",")
MY_GUILDS = [discord.Object(id=int(guild)) for guild in list_of_guilds]


class Test(commands.Cog):
    """Basic Features"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    # @app_commands.command(
    #     name="introduce",
    #     description="Introduce Yourself!"
    # )
    # async def introduce(self, interaction: discord.interactions, name: str, age: int) -> None:
    #     """Introduce Yourself!"""
    #     await interaction.response.send_message(f'My name is {name} and my age is {age}')

    # @app_commands.command(
    #     name="hello",
    #     description="Mentions the user"
    # )
    # async def hello(self, interaction: discord.Interaction):
    #     """Mentions the user"""
    #     await interaction.response.send_message(f'Hi, {interaction.user.mention}')

    @app_commands.command(
        name="games",
        description="Provide the google sheet links to games"
    )
    async def games(self, interaction: discord.Integration):
        """Provide the google sheet links to games"""
        await interaction.response.send_message(f'Games Channel: <#629459633031086080> \nFull List of Games: {GAMES}')

    # @app_commands.command(name="channel-info")
    # @app_commands.describe(channel='The channel to get info of')
    # async def channel_info(self, interaction: discord.Interaction, channel: Union[discord.VoiceChannel, discord.TextChannel]):
    #     """Shows basic channel info for a text or voice channel."""

    #     embed = discord.Embed(title='Channel Info')
    #     embed.add_field(name='Name', value=channel.name, inline=True)
    #     embed.add_field(name='ID', value=channel.id, inline=True)
    #     embed.add_field(
    #         name='Type',
    #         value='Voice' if isinstance(
    #             channel, discord.VoiceChannel) else 'Text',
    #         inline=True,
    #     )

    #     embed.set_footer(text='Created').timestamp = channel.created_at
    #     await interaction.response.send_message(embed=embed)

    @app_commands.command(name="test")
    async def userinfo(self, ctx: discord.Integration, member: discord.Member = None):
        '''Check a user's profile details.'''
        if member is None:
            member = ctx.user

        user = ctx.guild.get_member(member.id)

        try:
            bannerUser = await self.bot.fetch_user(member.id)
            banner = str(bannerUser.banner.url)
        except Exception:
            banner = None

        view = View()
        button3 = Button(
            label='User URL', url=f'https://discord.com/users/{user.id}', style=ButtonStyle.url)
        view.add_item(button3)

        button1 = Button(
            label='Download avatar', url=str(user.avatar.url), style=ButtonStyle.url)
        view.add_item(button1)

        if user.display_avatar.url != user.avatar.url:
            button4 = Button(
                label='Download server avatar', url=f'{user.display_avatar.url}', style=ButtonStyle.url)
            view.add_item(button4)

        if banner is not None:
            button2 = Button(
                label='Download banner', url=banner, style=ButtonStyle.url)
            view.add_item(button2)

        created = user.created_at
        created = datetime.strftime(created, "%A, %d %B %Y\n%I:%M %p")

        joined = user.joined_at
        joined = datetime.strftime(joined, "%A, %d %B %Y\n%I:%M %p")

        embed = discord.Embed()
        embed.title = f"{user.name}'s user info"
        embed.set_thumbnail(url=str(user.avatar.url))

        embed.add_field(name="Username", value=user.name, inline=True)
        embed.add_field(name="Discriminator",
                        value=f'#{user.discriminator}', inline=True)
        embed.add_field(name="Bot?", value=user.bot)
        embed.add_field(name="User ID", value=user.id, inline=False)
        embed.add_field(name="Account created",
                        value=created, inline=True)
        embed.add_field(name="Joined the server", value=joined, inline=True)

        if user.display_name != user.name:
            embed.add_field(name="Server nickname",
                            value=user.display_name, inline=True)

        perms = []
        separated_perms = []

        perms.extend(name for name, value in user.guild_permissions if value)
        if user.id == ctx.guild.owner_id:
            separated_perms = ["Server owner"]
        else:
            for perm in perms:
                separated = perm.split("_")
                reunited_lowercase = " ".join(separated)
                reunited = reunited_lowercase.capitalize()
                separated_perms.append(reunited)

        chars = list(separated_perms)

        if len(chars) > 1024:
            separated_perms = ["Too many to display"]

        embed.add_field(name="Permissions", value=", ".join(
            separated_perms), inline=False)

        roles = [role.mention for role in user.roles[1:]]
        roles.append('@everyone')

        roles_value = " | ".join(roles)
        chars = list(roles_value)

        if len(chars) > 1024:
            roles_value = ["Too many to display"]

        embed.add_field(name="Roles", value=roles_value, inline=False)

        await ctx.channel.send(embed=embed, view=view)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(
        Test(bot),
        guilds=MY_GUILDS
    )
    print("Test is Loaded")
