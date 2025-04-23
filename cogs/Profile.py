import os
from datetime import datetime
from typing import Optional

import discord
from discord import ButtonStyle, app_commands
from discord.ext import commands
from discord.ui import Button, View
from dotenv import load_dotenv
from pymongo import MongoClient

from utils.embeds import create_embed
from utils.stats import all_stats, balance_of_player, get_user_inventory

load_dotenv()
GAMES = os.getenv("GAMES")
MONGO_URL = os.getenv("ATLAS_URI")
cluster = MongoClient(MONGO_URL)
db = cluster["Users"]
collection = db["UserData"]


class Profile(commands.Cog):
    """Information about Users"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="profile", description="Shows basic info of a member")
    @app_commands.describe(member="The profile of a user")
    # @app_commands.checks.cooldown(1, 10, key=lambda i: (i.guild_id, i.user.id))
    async def profile(
        self, interaction: discord.Interaction, member: Optional[discord.Member]
    ):
        """Shows basic info of a member"""
        if not member:
            member = interaction.user
        # .roles gives id and name
        # list compression for only role names
        # convert list to more readable text
        role_names = [role.mention for role in member.roles[1:]]
        count = len(role_names)
        all_roles = " ".join(role_names)
        if len(all_roles) >= 1000:
            all_roles = all_roles[:1000].rsplit("<@&", 1)[0] + "..."
        if (len(all_roles)) == 0:
            all_roles = "`None ` "

        # member joined date - today date to measure total days in server
        days_in_server = abs(
            (
                datetime.now().replace(tzinfo=None)
                - member.joined_at.replace(tzinfo=None)
            ).days
        )

        embed = discord.Embed(
            title=f"Profile of {member.name}", color=member.accent_color
        )
        embed.add_field(name="Username", value=member.name, inline=True)
        embed.add_field(name="Tag", value=member.discriminator, inline=True)
        if member.display_name != member.name:
            embed.add_field(name="Nickname", value=member.display_name, inline=True)
        embed.add_field(name="ID", value=member.id, inline=False)
        embed.add_field(
            name="Creation Date of Account",
            value=f"{discord.utils.format_dt(member.created_at)}",
            inline=False,
        )
        embed.add_field(
            name="Joined Date",
            value=f"{discord.utils.format_dt(member.joined_at)}",
            inline=False,
        )
        embed.add_field(name="Days in Server", value=f"{days_in_server}", inline=True)
        embed.add_field(name="Activity", value=f"{member.activity}", inline=True)

        prev_balance, balance = balance_of_player(member)

        embed.add_field(name="Balance", value=f"${float(balance):,.2f}", inline=True)
        embed.add_field(name=f"Roles - {count}", value=f"{all_roles}", inline=False)
        embed.set_image(url=member.display_avatar)
        embed.timestamp = datetime.now()
        embed.set_footer(text=f"{member}", icon_url=member.avatar)

        view = View()
        button = Button(
            label="Download avatar",
            url=str(member.display_avatar.url),
            style=ButtonStyle.url,
        )
        view.add_item(button)

        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(
        name="server_info", description="Shows information about the server"
    )
    async def server_info(self, interaction: discord.Interaction):
        """Shows information about the server"""
        server = interaction.user.guild
        embed = discord.Embed(title=f"Information about {server.name}")
        embed.add_field(name="Owner 👑", value=server.owner, inline=True)
        embed.add_field(name="Server ID", value=server.id, inline=True)
        embed.add_field(
            name="Server Creation Date",
            value=f"{discord.utils.format_dt(server.created_at)}",
            inline=False,
        )

        embed.add_field(
            name="Voice Channels", value=f"{len(server.voice_channels)}", inline=True
        )

        embed.add_field(
            name="Text Channels", value=f"{len(server.text_channels)}", inline=True
        )

        embed.add_field(name="Members", value=server.member_count, inline=True)
        role_names = [role.mention for role in server.roles[1:]]
        count = len(role_names)
        all_roles = " ".join(role_names)
        if len(all_roles) >= 1000:
            all_roles = all_roles[:1000].rsplit("<@&", 1)[0] + "..."
        elif not all_roles:
            all_roles = "`None ` "
        embed.add_field(name=f"Roles - {count}", value=f"{all_roles}", inline=False)
        embed.set_thumbnail(url=server.icon)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="balance", description="Shows balance of user")
    async def balance(
        self, interaction: discord.Interaction, member: Optional[discord.Member]
    ):
        if not member:
            member = interaction.user
        prev_balance, balance = balance_of_player(member)
        await interaction.response.defer()
        await interaction.followup.send(f"💳 {member.mention} has ${balance:,.2f}")

    @app_commands.command(
        name="game_stats", description="Shows full game and heist stats of a user"
    )
    async def game_stats(
        self, interaction: discord.Interaction, member: Optional[discord.Member] = None
    ):
        member = member or interaction.user
        await interaction.response.defer()
        embed = await all_stats_embed(member)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="inventory", description="Shows inventory of user")
    async def inventory(
        self, interaction: discord.Interaction, member: Optional[discord.Member] = None
    ):
        member = member or interaction.user
        await interaction.response.defer()
        user_inventory = get_user_inventory(member)

        if not user_inventory:
            await interaction.followup.send(
                f"{member.mention} has no items in their inventory."
            )
            return

        embed = discord.Embed(
            title=f"{member.name}'s Inventory", color=discord.Color.blue()
        )
        for item in user_inventory:
            # Assuming each item is a dictionary with "name" and "quantity"
            embed.add_field(
                name=item["name"], value=f"Quantity: {item['quantity']}", inline=False
            )

        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Profile(bot))
    print("Profile is Loaded")


async def all_stats_embed(member: discord.Member) -> discord.Embed:
    stats = all_stats(member)

    fields = [
        (
            "🎡 Roulette",
            f"**Won:** {stats['roulette']['won']} | **Lost:** {stats['roulette']['lost']} | **Played:** {stats['roulette']['played']}\n"
            f"**Amount Won:** ${stats['roulette']['total_winnings']:,} | **Amount Lost:** ${stats['roulette']['total_losses']:,}",
            False,
        ),
        (
            "🎲 Gamble",
            f"**Won:** {stats['gamble']['won']} | **Lost:** {stats['gamble']['lost']} | **Played:** {stats['gamble']['played']}\n"
            f"**Amount Won:** ${stats['gamble']['total_winnings']:,} | **Amount Lost:** ${stats['gamble']['total_losses']:,}",
            False,
        ),
        (
            "🃏 Blackjack",
            f"**Won:** {stats['blackjack']['won']} | **Lost:** {stats['blackjack']['lost']} | **Played:** {stats['blackjack']['played']}\n"
            f"**Amount Won:** ${stats['blackjack']['total_winnings']:,} | **Amount Lost:** ${stats['blackjack']['total_losses']:,}",
            False,
        ),
        (
            "🎰 Slots",
            f"**Won:** {stats['slots']['won']} | **Lost:** {stats['slots']['lost']} | **Played:** {stats['slots']['played']}\n"
            f"**Amount Won:** ${stats['slots']['total_winnings']:,} | **Amount Lost:** ${stats['slots']['total_losses']:,}",
            False,
        ),
        (
            "🧠 Wordle",
            f"**Won:** {stats['wordle']['won']} | **Lost:** {stats['wordle']['lost']} | **Played:** {stats['wordle']['played']}",
            False,
        ),
        (
            "⚔️ Duel",
            f"**Won:** {stats['duel']['won']} | **Lost:** {stats['duel']['lost']} | **Played:** {stats['duel']['tied']}",
            False,
        ),
        (
            "💼 Heists",
            (
                f"**Joined:** {stats['heist']['joined']} | **Won:** {stats['heist']['won']} | **Lost:** {stats['heist']['lost']}\n"
                f"**Loot Gained:** ${stats['heist']['loot_gained']:,} | **Loot Lost:** ${stats['heist']['loot_lost']:,}\n"
                f"**Backstabs:** {stats['heist']['backstabs']} | **Betrayed:** {stats['heist']['betrayed']}"
            ),
            False,
        ),
        (
            "🕵️ Steals",
            (
                f"**Attempted:** {stats['steal']['attempted']} | **Successful:** {stats['steal']['successful']} | **Failed:** {stats['steal']['failed']}\n"
                f"**Amount Stolen:** ${stats['steal']['amount_stolen']:,} | **Lost on Fail:** ${stats['steal']['amount_lost_to_failed_steals']:,}\n"
                f"**Stolen by Others:** ${stats['steal']['amount_stolen_by_others']:,} | **Times Robbed:** {stats['steal']['times_stolen_from']}\n"
                f"**Gained from Failed Steals:** ${stats['steal']['amount_gained_from_failed_steals']:,}"
            ),
            False,
        ),
        (
            "⛏️ Mining",
            (
                f"**Level:** {stats['mining']['mining_level']}/99 | **XP:** {stats['mining']['mining_xp']:,} / {stats['mining']['next_level_xp']:,}\n"
            ),
            False,
        ),
        (
            "🎣 Fishing",
            (
                f"**Level:** {stats['fishing']['fishing_level']}/99 | **XP:** {stats['fishing']['fishing_xp']:,} / {stats['fishing']['fishing_next_level_xp']:,}\n"
            ),
            False,
        ),
    ]

    return create_embed(
        title=f"{member.display_name}'s Full Stats",
        description="📊 Here's a full breakdown of your activity!",
        color=discord.Color.gold(),
        fields=fields,
        thumbnail=member.display_avatar.url,
    )
