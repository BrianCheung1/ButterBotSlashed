
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

    @app_commands.command(
        name="games",
        description="Provide the google sheet links to games"
    )
    async def games(self, interaction: discord.Interaction):
        """Provide the google sheet links to games"""
        await interaction.response.send_message(f'Games Channel: <#629459633031086080> \nFull List of Games: {GAMES}')

    @app_commands.command(name="test")
    async def userinfo(self, ctx: discord.Interaction, member: discord.Member = None):
        '''Check a user's profile details.'''


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(
        Test(bot),
        guilds=MY_GUILDS
    )
    print("Test is Loaded")
