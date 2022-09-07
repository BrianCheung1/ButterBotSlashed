from datetime import datetime
from discord import ButtonStyle, app_commands
from discord.ext import commands
from discord.ui import Button, View
from dotenv import load_dotenv
from typing import Literal, Union, NamedTuple, Optional
import discord
import json
import os
import requests


load_dotenv()
KEY = os.getenv("TENOR_TOKEN")
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
        r = requests.get(
            "https://tenor.googleapis.com/v2/search?q=%s&key=%s&client_key=butter&limit=50"
            % (query, KEY)
        )

        gif_list = []

        if r.status_code == 200:
            # load the GIFs using the urls for the smaller GIF sizes
            found_gifs = json.loads(r.content)
            gif_list.extend(
                media["media_formats"]["gif"]["url"] for media in found_gifs["results"]
            )
            embed = discord.Embed()
            embed.set_image(url=random.choice(gif_list))
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("No gifs were found for your query")

    # limited in function as if the emoji sent isnt in any of the servers the bot is in
    # the command will fail
    @app_commands.command(
        name="enlarge", description="enlarges a gif if its in the server"
    )
    @app_commands.describe(emoji="type in the emoji you want enlarged")
    async def enlarge(self, interaction: discord.Interaction, emoji: str):
        """Enlarges an emoji"""
        emoji_id = emoji.rsplit(":", 1)[-1].replace(">", "")
        fixed_emoji = self.bot.get_emoji(int(emoji_id))
        guild_emojis = [emoji for emoji in interaction.guild.emojis]

        # if (fixed_emoji in guild_emojis):
        await interaction.response.send_message(fixed_emoji.url)
        # else:
        #     await interaction.response.send_message("Emoji not in server")

    @app_commands.command(
        name="random-emoji", description="Button to show random emojis in the server"
    )
    async def random_emoji(self, interaction: discord.Interaction):
        view = Counter()

        await interaction.response.send_message(
            "Click the button to start the process", view=view
        )
        await view.wait()


class Counter(discord.ui.View):
    # Define the actual button
    # When pressed, this displays a random emoji in the guild.
    # note: The name of the function does not matter to the library
    @discord.ui.button(label="Random Emoji", style=discord.ButtonStyle.red)
    async def emoji(self, interaction: discord.Interaction, button: discord.ui.Button):
        emoji_list = interaction.guild.emojis
        # number = int(button.label) if button.label else 0
        # if number + 1 >= 10:
        #     button.style = discord.ButtonStyle.green
        #     button.disabled = True
        # button.label = "Random Emoji"

        # Make sure to update the message with our updated selves
        await interaction.response.edit_message(content=random.choice(emoji_list))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Gifs(bot), guilds=MY_GUILDS)
    print("Gifs is Loaded")
