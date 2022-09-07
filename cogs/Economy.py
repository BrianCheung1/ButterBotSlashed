from datetime import datetime
from discord import ButtonStyle, app_commands
from discord.ext import commands
from discord.ui import Button, View
from dotenv import load_dotenv
from pymongo import MongoClient
from typing import Literal, Union, NamedTuple, Optional, List
import discord
import os
import random


load_dotenv()
list_of_guilds = os.getenv("GUILDS").split(",")
MY_GUILDS = [discord.Object(id=int(guild)) for guild in list_of_guilds]
MONGO_URL = os.getenv("ATLAS_URI")
cluster = MongoClient(MONGO_URL)
db = cluster["Users"]
collection = db["UserData"]


class Economy(commands.Cog):
    """Economy Features"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="give", description="Give users money")
    @app_commands.describe(
        member="The member you want to give money to",
        amount="The amount you want to give",
    )
    @app_commands.checks.has_permissions(moderate_members=True)
    async def give(
        self,
        interaction: discord.Interaction,
        member: Optional[discord.Member],
        amount: Optional[int] = 1000,
    ):
        if not member:
            member = interaction.user

        search = {"_id": member.id}
        if collection.count_documents(search) == 0:
            await interaction.response.send_message("User does not exist")
        else:
            user = collection.find(search)
            for result in user:
                balance = result["balance"]
            balance += amount
            collection.update_one(
                {"_id": interaction.user.id}, {"$set": {"balance": balance}}
            )
            await interaction.response.send_message(
                f"{member.mention} now has ${balance:,}"
            )

    @app_commands.command(
        name="leaderboard", description="Richest members of your server"
    )
    async def leaderboard(self, interaction: discord.Interaction):
        top_members = {}
        count = 1
        for member in interaction.guild.members:
            print(member)
            search = {"_id": member.id}
            if collection.count_documents(search) != 0:
                user = collection.find(search)
                for result in user:
                    balance = result["balance"]
                if not member.nick:
                    top_members[member.name] = balance
                else:
                    top_members[member.nick] = balance
        sorted_top_members = dict(
            sorted(top_members.items(), key=lambda item: item[1], reverse=True)
        )
        embed = discord.Embed(title=f"{interaction.guild.name} Leaderboard")
        for member, balance in sorted_top_members.items():
            embed.add_field(
                name=f"{count}. {member}", value=f"${balance}", inline=False
            )
            count += 1
            if count > 10:
                break
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Economy(bot), guilds=MY_GUILDS)
    print("Economy is Loaded")
