import json
import os
import random

import discord
import requests
from discord import Interaction, Member, app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
KEY = os.getenv("TENOR_TOKEN")


class Gifs(commands.Cog):
    """Basic Features"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="gif", description="sends a gif of your query")
    @app_commands.describe(query="Will search tenor api for a gif of your query")
    async def gif(self, interaction: discord.Interaction, query: str):
        """Sends a gif of your query"""
        r = requests.get(
            f"https://tenor.googleapis.com/v2/search?q={query}&key={KEY}&client_key=butter&limit=50",
            timeout=100,
        )
        if r.status_code == 200:
            # load the GIFs using the urls for the smaller GIF sizes
            found_gifs = json.loads(r.content)
            gif_list = []
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
        guild_emojis = list(interaction.guild.emojis)

        if fixed_emoji in guild_emojis:
            await interaction.response.send_message(fixed_emoji.url)
        else:
            await interaction.response.send_message("Emoji not in server")

    # Command to roast a member
    @app_commands.command(
        name="roast", description="Roast someone with text and a GIF!"
    )
    @app_commands.describe(
        member="The member you want to roast",
    )
    async def roast(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
    ):
        # Get the roast text and GIF
        roast_text = get_random_roast()
        roast_gif_url = get_random_roast_gif()

        # Create embed message
        embed = discord.Embed(
            description=roast_text,
            color=discord.Color.red(),
        )
        embed.set_thumbnail(url=member.avatar.url)

        if roast_gif_url:
            embed.set_image(url=roast_gif_url)

        # Send the embed with roast message
        await interaction.response.send_message(
            content=f"{member.mention} Got Roasted!", embed=embed
        )


def get_random_roast():
    response = requests.get(
        "https://evilinsult.com/generate_insult.php?lang=en&type=json"
    )
    if response.status_code == 200:
        return response.json().get(
            "insult", "You are the reason we have instructions on shampoo bottles."
        )
    return "You are so slow, it took you 3 hours to watch '60 Minutes'."


# Fetch a random roast GIF from Tenor
def get_random_roast_gif():
    url = f"https://tenor.googleapis.com/v2/search?q=roasted&key={KEY}&client_key=butter&limit=20"  # Get multiple results
    response = requests.get(url).json()

    if response.get("results"):
        # Randomly select a GIF from the search results
        random_gif = random.choice(response["results"])
        return random_gif["media_formats"]["gif"]["url"]

    return None


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Gifs(bot))
    print("Gifs is Loaded")
