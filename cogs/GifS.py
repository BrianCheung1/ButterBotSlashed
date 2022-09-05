
from threading import stack_size
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
import random

load_dotenv()
KEY = os.getenv('TENOR_TOKEN')
list_of_guilds = os.getenv("GUILDS").split(",")
MY_GUILDS = [discord.Object(id=int(guild)) for guild in list_of_guilds]


class Gifs(commands.Cog):
    """Basic Features"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="gif", description="sends a gif of your query")
    @app_commands.describe(query="Will search tenor api for a gif of your query")
    async def gif(self, interaction: discord.Interaction, query: str):
        """Sends a gif of your query"""
        # get the top 8 GIFs for the search term
        r = requests.get(
            "https://tenor.googleapis.com/v2/search?q=%s&key=%s&client_key=butter&limit=50" % (query, KEY))

        gif_list = []

        if r.status_code == 200:
            # load the GIFs using the urls for the smaller GIF sizes
            top_20gifs = json.loads(r.content)
            gif_list.extend(media["media_formats"]["gif"]["url"]
                            for media in top_20gifs["results"])
            embed = discord.Embed()
            embed.set_image(url=random.choice(gif_list))
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("No gifs were found for your query")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(
        Gifs(bot),
        guilds=MY_GUILDS
    )
    print("Gifs is Loaded")
