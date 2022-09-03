
import discord
from discord import app_commands
from discord.ext import commands
import os
from dotenv import load_dotenv
from typing import Literal, Union, NamedTuple, Optional
import requests
import json
from datetime import datetime

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

    # @app_commands.command(name="test")
    # async def test(self, interaction: discord.Interaction):
    #     url = 'https://store.steampowered.com/app/1817070/Marvels_SpiderMan_Remastered/'
    #     response = requests.get(url)
    #     soup = BeautifulSoup(response.text, features="html.parser")

    #     title = soup.find("meta", property="og:title")["content"]
    #     description = soup.find("meta", property="og:description")["content"]
    #     image = soup.find("meta", property="og:image")["content"]
    #     price = soup.find("meta", itemprop="price")["content"]
    #     reviews = soup.find("meta", itemprop="reviewCount")["content"]
    #     await interaction.response.send_message(f'{title}\n{description}\n{image}\n{price}')


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(
        Test(bot),
        guilds=MY_GUILDS
    )
    print("Test is Loaded")
