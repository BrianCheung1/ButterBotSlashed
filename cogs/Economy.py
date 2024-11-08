import os
import random
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
from pymongo import MongoClient

from utils.stats import balance_of_player

load_dotenv()
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
    async def give(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        amount: Optional[app_commands.Range[int, 1, None]] = 1000,
    ):
        await interaction.response.defer()
        prev_balance, balance = balance_of_player(member)
        if interaction.user.guild_permissions.administrator:
            balance += amount
            collection.update_one({"_id": member.id}, {"$set": {"balance": balance}})
            await interaction.followup.send(f"{member.mention} now has ${balance:,.2f}")
        else:
            prev_balance, user_balance = balance_of_player(interaction.user)
            if amount > user_balance:
                await interaction.followup.send(
                    f"{member.mention} is too broke to give away money - they only have {user_balance:,.2f}"
                )
            else:
                balance += amount
                collection.update_one(
                    {"_id": member.id},
                    {"$set": {"balance": balance}},
                )
                user_balance -= amount
                collection.update_one(
                    {"_id": interaction.user.id},
                    {"$set": {"balance": user_balance}},
                )
                await interaction.followup.send(
                    f"{member.mention} now has ${balance:,}"
                )

    @app_commands.command(name="mine", description="Mine ores for money")
    @app_commands.checks.cooldown(1, 60, key=lambda i: (i.guild_id, i.user.id))
    async def mine(self, interaction: discord.Interaction):
        common_blocks = ["dirt", "sand", "cobblestone", "wood"]
        common_ores = ["coal", "redstone", "lapis lazuli", "copper", "tin"]
        uncommon_ores = ["iron", "gold", "nether quartz", "platinum", "golden apple"]
        rare_ores = ["diamond", "emerald", "mythril", "sponge"]
        epic_ores = ["ancient debris", "dragon egg", "nether star"]

        prev_balance, balance = balance_of_player(interaction.user)

        await interaction.response.defer()
        choice = random.randint(0, 101)
        mining_result = ""
        if choice < 20:
            balance += random.randint(50, 100)
            mining_result = random.choice(common_blocks)
        if choice >= 20 and choice < 60:
            balance += random.randint(100, 150)
            mining_result = random.choice(common_ores)
        if choice >= 60 and choice < 80:
            balance += random.randint(150, 250)
            mining_result = random.choice(uncommon_ores)
        if choice >= 80 and choice < 95:
            balance += random.randint(250, 500)
            mining_result = random.choice(rare_ores)
        if choice >= 95 and choice <= 100:
            balance += random.randint(500, 750)
            mining_result = random.choice(epic_ores)
        if choice == 101:
            balance += random.randint(1500, 2000)
            mining_result = f"epic loot {random.choice(epic_ores)}, {random.choice(rare_ores)}, {random.choice(uncommon_ores)}, {random.choice(common_ores)}, and {random.choice(common_blocks)}"
        collection.update_one(
            {"_id": interaction.user.id}, {"$set": {"balance": balance}}
        )
        await interaction.followup.send(
            f"{interaction.user.mention} found {mining_result}, it's worth ${balance-prev_balance:,.2f}, {interaction.user.mention} has ${balance:,.2f}"
        )

    @app_commands.command(
        name="leaderboard", description="Richest members of your server"
    )
    async def leaderboard(self, interaction: discord.Interaction):
        await interaction.response.defer()
        top_members = {}
        count = 0
        page_count = 1
        pages = []
        for member in interaction.guild.members:
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
        embed_page_count = discord.Embed(title=f"{interaction.guild.name} Leaderboard")
        embed_page_count.set_footer(
            text=f"Page {page_count}", icon_url=interaction.user.display_avatar
        )
        for member, balance in sorted_top_members.items():
            embed_page_count.add_field(
                name=f"{count+1}. {member}",
                value=f"${float(balance):,.2f}",
                inline=False,
            )
            count += 1
            if count % 10 == 0:
                pages.append(embed_page_count)
                page_count += 1
                embed_page_count = discord.Embed(
                    title=f"{interaction.guild.name} Leaderboard"
                )
                embed_page_count.set_footer(
                    text=f"Page {page_count}", icon_url=interaction.user.display_avatar
                )
        pages.append(embed_page_count)
        view = LeaderboardButton(interaction, pages)
        await interaction.followup.send(embed=pages[0], view=view)


class LeaderboardButton(discord.ui.View):
    def __init__(self, interaction: discord.Interaction, pages: list):
        super().__init__(timeout=None)
        self.interaction = interaction
        self.pages = pages
        self.count = 0
        self.prev_page.disabled = True

    @discord.ui.button(label="Previous Page", style=discord.ButtonStyle.red)
    async def prev_page(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.next_page.disabled = False
        self.count -= 1
        if self.count <= 0:
            self.prev_page.disabled = True
        await interaction.response.edit_message(embed=self.pages[self.count], view=self)

    @discord.ui.button(label="Next Page", style=discord.ButtonStyle.red)
    async def next_page(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.prev_page.disabled = False
        self.count += 1
        if self.count >= len(self.pages) - 1:
            self.next_page.disabled = True
        await interaction.response.edit_message(embed=self.pages[self.count], view=self)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Economy(bot))
    print("Economy is Loaded")
