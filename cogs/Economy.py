import discord
from discord import app_commands
from discord.ext import commands
import os
from dotenv import load_dotenv
from typing import Literal, Union, NamedTuple, Optional, List
from datetime import datetime
from discord.ui import Button, View
from discord import ButtonStyle
import random
from pymongo import MongoClient


load_dotenv()
list_of_guilds = os.getenv("GUILDS").split(",")
MY_GUILDS = [discord.Object(id=int(guild)) for guild in list_of_guilds]
MONGO_URL = os.getenv('ATLAS_URI')
cluster = MongoClient(MONGO_URL)
db = cluster["Users"]
collection = db["UserData"]


class Economy(commands.Cog):
    """Economy Features"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="give", description="Give users money")
    @app_commands.describe(member="The member you want to give money to", amount="The amount you want to give")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def give(self, interaction: discord.Interaction, member: Optional[discord.Member], amount: Optional[int] = 1000):
        if not member:
            member = interaction.user

        search = {"_id": member.id}
        if (collection.count_documents(search) == 0):
            await interaction.response.send_message("User does not exist")
        else:
            user = collection.find(search)
            for result in user:
                balance = result["balance"]
            balance += amount
            collection.update_one({"_id": interaction.user.id}, {
                                  "$set": {"balance": balance}})
            await interaction.response.send_message(f'{member.mention} now has ${balance:,}')


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(
        Economy(bot),
        guilds=MY_GUILDS
    )
    print("Economy is Loaded")
