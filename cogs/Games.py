import asyncio
from typing import Optional
import discord
from discord import app_commands
from discord.ext import commands
from discord.app_commands import Choice
from datetime import datetime
import os
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
from pymongo import MongoClient
import random

load_dotenv()
GAMES = os.getenv('GAMES')
list_of_guilds = os.getenv("GUILDS").split(",")
MY_GUILDS = [discord.Object(id=int(guild)) for guild in list_of_guilds]
MONGO_URL = os.getenv('ATLAS_URI')
cluster = MongoClient(MONGO_URL)
db = cluster["Users"]
collection = db["UserData"]


class Games(commands.Cog):
    """Games functions"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(
        name="games",
        description="Provide the google sheet links to games"
    )
    async def games(self, interaction: discord.Interaction):
        """Provide the google sheet links to games"""
        view = GamesList()
        await interaction.response.send_message(f'Games Channel: <#629459633031086080>', view=view)

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

        title = soup.select_one('div[class="apphub_AppName"]').contents[0]
        description = soup.find("meta", property="og:description")["content"]
        image = soup.find("meta", property="og:image")["content"]
        price = soup.find("meta", itemprop="price")["content"]
        reviews = soup.find("meta", itemprop="reviewCount")["content"]
        app_id = steam_link.split("/")[4]

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
        embed.add_field(name="App Id", value=f'{app_id}', inline=True)
        embed.set_image(url=image)
        embed.timestamp = datetime.now()
        embed.set_footer(text=f'{interaction.user}',
                         icon_url=interaction.user.avatar)
        await interaction.response.send_message(embed=embed)

    @ app_commands.command(name="gamble", description="Chance to win or lose money - Default $100")
    @ app_commands.describe(amount="Amount of money you want to gamble - Default $100")
    async def gamble(self, interaction: discord.Interaction, amount: Optional[int] = 100):
        view = GamblingButton(interaction, amount)
        embed = gamble_helper(interaction, amount)
        await interaction.response.send_message(embed=embed, view=view)


class GamesList(discord.ui.View):
    def __init__(self):
        super().__init__()
        # we need to quote the query string to make a valid url. Discord will raise an error if it isn't valid.
        url = GAMES

        # Link buttons cannot be made with the decorator
        # Therefore we have to manually create one.
        # We add the quoted url to the button, and add the button to the view.
        self.add_item(discord.ui.Button(label='List Of Games', url=url))


class GamblingButton(discord.ui.View):
    def __init__(self, interaction: discord.Interaction, amount: Optional[int]):
        super().__init__(timeout=None)
        self.amount = amount
        self.interaction = interaction

    # this function must return a boolean, or to the very least a truthy/falsey value.
    async def interaction_check(self, interaction: discord.Interaction) -> bool:

        if self.interaction.user.id != interaction.user.id:
            await interaction.response.send_message("Please start your own game with /gamble", ephemeral=True)
            return False
        return True

    @ discord.ui.button(label='Play Again', style=discord.ButtonStyle.red)
    async def play_again(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = gamble_helper(interaction, self.amount)
        await interaction.response.edit_message(embed=embed, view=self)


def gamble_helper(interaction: discord.Interaction, amount: Optional[int]):
    search = {"_id": interaction.user.id}
    if (collection.count_documents(search) == 0):
        post = {"_id": interaction.user.id, "balance": 1000}
        collection.insert_one(post)
    user = collection.find(search)
    win = ""
    for result in user:
        balance = result["balance"]
        prev_balance = balance
    if amount > balance:
        embed = discord.Embed(title="Not enough balance",
                              description=f'${amount:,} bet')
        embed.add_field(name="Needed Balance",
                        value=f'${amount:,}', inline=True)
        embed.add_field(name="Balance",
                        value=f'${balance:,}', inline=True)
        return embed
    else:
        bot_number = int(random. randrange(1, 100))
        member_number = int(random.randrange(1, 100))
        if (bot_number < member_number):
            balance += amount
            collection.update_one({"_id": interaction.user.id}, {
                "$set": {"balance": balance}})
            win = f'{interaction.user.mention} rolled a higher number'
        elif (bot_number > member_number):
            balance -= amount
            collection.update_one({"_id": interaction.user.id}, {
                "$set": {"balance": balance}})
            win = f'Dealer rolled a higher number'
        elif (bot_number == member_number):
            win = 'No Winners'
        embed = discord.Embed(title="Gambling Details",
                              description=f'${amount:,} bet')
        embed.add_field(name="Dealer rolled a ",
                        value=bot_number, inline=False)
        embed.add_field(
            name=f'{interaction.user} rolled a', value=member_number, inline=False)
        embed.add_field(name="Result", value=f'{win}', inline=False)
        embed.add_field(name="Previous Balance",
                        value=f'${prev_balance:,}', inline=True)
        embed.add_field(name="New Balance",
                        value=f'${balance:,}', inline=True)
        new_balance = balance-prev_balance
        if new_balance >= 0:
            embed.add_field(name="Result",
                            value=f'+${abs(balance-prev_balance):,}', inline=True)
        else:
            embed.add_field(name="Result",
                            value=f'-${abs(balance-prev_balance):,}', inline=True)
        return embed


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(
        Games(bot),
        guilds=MY_GUILDS
    )
    print("Games is Loaded")
