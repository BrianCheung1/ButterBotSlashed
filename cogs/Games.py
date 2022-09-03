import discord
from discord import app_commands
from discord.ext import commands
from discord.app_commands import Choice
from datetime import datetime
import os
from dotenv import load_dotenv
import requests
import json
from bs4 import BeautifulSoup

load_dotenv()
GAMES = os.getenv('GAMES')
list_of_guilds = os.getenv("GUILDS").split(",")
MY_GUILDS = [discord.Object(id=int(guild)) for guild in list_of_guilds]


class Games(commands.Cog):
    """Games functions"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(
        name="add_game",
        description="add a game to games channel"
    )
    @app_commands.describe(
        add='Adding or Updating a game',
        download_link='The google drive download link',
        steam_link='The steam link to the game',
    )
    @app_commands.choices(add=[Choice(name="Added", value="Added "), Choice(name="Updated", value="Updated")])
    @app_commands.checks.has_permissions(moderate_members=True)
    async def add(self, interaction: discord.Interaction, add: str, download_link: str, steam_link: str):
        """Adds two numbers together."""

        # bs4 to parse through steam link for data
        url = steam_link
        response = requests.get(url)
        soup = BeautifulSoup(response.text, features="html.parser")

        title = soup.find("meta", property="og:title")[
            "content"].replace("on Steam", "")
        description = soup.find("meta", property="og:description")["content"]
        image = soup.find("meta", property="og:image")["content"]
        price = soup.find("meta", itemprop="price")["content"]
        reviews = soup.find("meta", itemprop="reviewCount")["content"]

        embed = discord.Embed(
            title=f'{add} - {title}', color=0x336EFF, url=steam_link)
        embed.add_field(name="Direct Download Link",
                        value=f'[Click Here]({download_link})', inline=False)
        embed.add_field(name="Full Games List",
                        value=f'[Click Here]({GAMES})', inline=False)
        embed.add_field(name="Steam Link", value=f'{steam_link}', inline=False)
        embed.add_field(name="Description",
                        value=f'{description}', inline=False)
        embed.add_field(name="Price", value=f'{price}', inline=True)
        embed.add_field(name="Reviews", value=f'{reviews}', inline=True)
        embed.set_image(url=image)
        embed.timestamp = datetime.now()
        embed.set_footer(text=f'{interaction.user}',
                         icon_url=interaction.user.avatar)
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(
        Games(bot),
        guilds=MY_GUILDS
    )
    print("Games is Loaded")
