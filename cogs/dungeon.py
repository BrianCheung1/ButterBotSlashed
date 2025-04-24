import os
from datetime import datetime, timedelta
from typing import Optional

import aiosqlite
import discord
import requests
import random
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import commands
from dotenv import load_dotenv

from utils.datetime import convert_to_datetime
from utils.embeds import create_embed
from utils.logging import logger
from utils.stats import get_user_data, update_user_player_stats, update_balance

load_dotenv()
VAL_KEY = os.getenv("VAL")


class Dungeon(commands.Cog):
    """Dungeon stats"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="player_stats", description="Player Stats")
    async def player_stats(self, interaction: discord.Interaction):
        """Command to display player stats in an embed."""
        user_data = get_user_data(interaction.user)

        # Get the cap for each stat based on level
        max_hp = max_hp_cap(user_data["player_level"])
        max_attack = max_stat_cap(user_data["player_level"])
        max_defense = max_stat_cap(user_data["player_level"])
        max_speed = max_stat_cap(user_data["player_level"])

        # Create an embed to display the player's stats
        embed = discord.Embed(
            title=f"Player Stats - {interaction.user.display_name}",
            color=discord.Color.blurple(),
        )
        embed.add_field(name="Level", value=user_data["player_level"], inline=True)
        embed.add_field(
            name="XP",
            value=f"{user_data['player_xp']}/{user_data['player_next_level_xp']}",
            inline=True,
        )
        embed.add_field(
            name="HP", value=f"{user_data['player_hp']} (Cap: {max_hp})", inline=True
        )
        embed.add_field(
            name="Attack",
            value=f"{user_data['player_attack']} (Cap: {max_attack})",
            inline=True,
        )
        embed.add_field(
            name="Defense",
            value=f"{user_data['player_defense']} (Cap: {max_defense})",
            inline=True,
        )
        embed.add_field(
            name="Speed",
            value=f"{user_data['player_speed']} (Cap: {max_speed})",
            inline=True,
        )

        # Send the embed message
        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="dungeon", description="Enter the dungeon and fight monsters!"
    )
    @app_commands.describe(floor="Choose the dungeon floor you want to challenge")
    async def dungeon(self, interaction: discord.Interaction, floor: int):
        user = interaction.user
        user_data = get_user_data(user)

        if floor < 1:
            await interaction.response.send_message(
                "Floor must be 1 or higher.", ephemeral=True
            )
            return

        cost = 50000 * floor
        balance = user_data.get("balance", 0)

        if balance < cost:
            await interaction.response.send_message(
                f"You need {cost} gold to enter floor {floor}.", ephemeral=True
            )
            return

        # Display the cost of entering
        result_embed = discord.Embed(
            title=f"Dungeon Floor {floor}", color=discord.Color.blurple()
        )
        result_embed.add_field(name="Cost to Enter", value=f"{cost} gold", inline=False)

        # Calculate win chance
        chance = calculate_win_chance(user_data, floor)
        win = random.random() <= chance

        result_embed.add_field(
            name="Win Chance", value=f"{int(chance * 100)}%", inline=True
        )

        xp_gain = 0
        xp_loss = 0

        if win:
            base_xp = 20 * floor
            player_level = user_data["player_level"]

            # If player level is higher than floor, reduce XP gain
            if player_level > floor:
                level_diff = player_level - floor
                # 10% less XP per level difference, min 10% of original XP
                xp_multiplier = max(0.1, 1 - 0.1 * level_diff)
            else:
                xp_multiplier = 1

            xp_gain = int(base_xp * xp_multiplier)
            result_embed.description = (
                f"You defeated the monsters! You earned {xp_gain} XP."
            )
        else:
            # Damage scales with floor level
            damage = 10 + (floor * 5)
            current_hp = user_data["player_hp"]
            user_data["player_hp"] = max(
                0, user_data["player_hp"] - damage
            )  # Subtract the damage from HP

            if user_data["player_hp"] <= 0:
                # Reset HP to max HP cap on death
                new_hp = max_hp_cap(user_data["player_level"])

                # Update the player stats with the new HP value
                update_user_player_stats(user=user, hp_change=new_hp - current_hp)

                # Calculate XP loss (25% of current XP)
                xp_loss = int(user_data["player_xp"] * 0.25)
                result_embed.description = (
                    f"You were defeated and lost {damage} HP... You have fainted! "
                    f"You lost {xp_loss} XP."
                )
            else:
                result_embed.description = (
                    f"You were defeated and lost {damage} HP... "
                    f"You now have {user_data['player_hp']} HP remaining."
                )

                # Update the player stats to reflect the HP loss
                update_user_player_stats(user=user, hp_change=-damage)

        # Deduct gold and update XP via the stat update function
        update_data = get_user_data(user)
        update_data["balance"] -= cost
        update_balance(user, update_data["balance"])

        # Apply XP change and auto level-up
        update_user_player_stats(
            user=user,
            xp_change=(xp_gain if win else -xp_loss),
        )

        # Reload user data to show updated level
        updated_data = get_user_data(user)
        if updated_data["player_level"] > user_data["player_level"]:
            result_embed.add_field(
                name="Level Up!",
                value=f"You reached level {updated_data['player_level']}!",
                inline=False,
            )

        await interaction.response.send_message(embed=result_embed)


def calculate_win_chance(player_stats, floor):
    base_difficulty = 100  # Difficulty of floor 1 at level 1 with stat caps
    floor_difficulty = base_difficulty * (1 + 0.25 * (floor - 1))

    # Adjust the weights to account for missing HP stat
    # Increased the weights of attack, defense, and speed to compensate for HP removal
    player_power = (
        player_stats["player_attack"] * 4  # Increased weight for attack
        + player_stats["player_defense"] * 4  # Increased weight for defense
        + player_stats["player_speed"] * 4  # Increased weight for speed
    )

    # Apply a strict threshold: If player power is less than a small fraction of floor difficulty, set chance to 0
    if (
        player_power < floor_difficulty * 0.3
    ):  # For example, if player's power is below 30% of the floor's difficulty
        chance = 0
    else:
        chance = min(
            0.95, max(0.05, player_power / floor_difficulty)
        )  # Clamp between 5% and 95%

    return chance


def max_stat_cap(level):
    """Calculates the max cap for each stat (except HP) at a given level."""
    return 5 + (level - 1) * 3


def max_hp_cap(level):
    """Calculates the max cap for HP stat at a given level."""
    if level == 1:
        return 100
    else:
        return 100 + (level - 1) * 25


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Dungeon(bot))
    logger.info("Dungeon is Loaded")
