
import discord
from discord import app_commands
from discord.ext import commands
import os
from dotenv import load_dotenv
from typing import Literal, Union, NamedTuple, Optional
from datetime import datetime
from discord.ui import Button, View
from discord import ButtonStyle
from urllib.parse import quote_plus


load_dotenv()
list_of_guilds = os.getenv("GUILDS").split(",")
MY_GUILDS = [discord.Object(id=int(guild)) for guild in list_of_guilds]


class General(commands.Cog):
    """Basic Features"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="invite", description="Invite me to your discord server")
    async def invite(self, interaction: discord.Interaction):
        """Invite me to your discord server"""
        button = Button(
            label='Invite', url=f'https://discord.com/api/oauth2/authorize?client_id={self.bot.user.id}&permissions=8&scope=bot', style=ButtonStyle.url)
        view = View()
        view.add_item(button)

        embed = discord.Embed()
        embed.title = f"Click the button below to invite me to your server! \U0001f389"
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="google")
    async def google(self, interaction: discord.Interaction, query: str):
        """Returns a google link for a query"""
        await interaction.response.send_message(f'Google Result for: `{query}`', view=Google(query))


# Define a simple View that gives us a google link button.
# We take in `query` as the query that the command author requests for
class Google(discord.ui.View):
    def __init__(self, query: str):
        super().__init__()
        # we need to quote the query string to make a valid url. Discord will raise an error if it isn't valid.
        query = quote_plus(query)
        url = f'https://www.google.com/search?q={query}'

        # Link buttons cannot be made with the decorator
        # Therefore we have to manually create one.
        # We add the quoted url to the button, and add the button to the view.
        self.add_item(discord.ui.Button(label='Click Here', url=url))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(
        General(bot),
        guilds=MY_GUILDS
    )
    print("General is Loaded")
