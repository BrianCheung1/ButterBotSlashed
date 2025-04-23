import os
from datetime import datetime, timedelta
from typing import Optional

import aiosqlite
import discord
import requests
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import commands
from dotenv import load_dotenv

from utils.datetime import convert_to_datetime
from utils.embeds import create_embed
from utils.logging import logger

load_dotenv()
VAL_KEY = os.getenv("VAL")


class Valorant2(commands.Cog):
    """Valorant2 stats"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

        self.db_folder = "database/valorant"
        # Ensure the 'database' folder exists
        if not os.path.exists(self.db_folder):
            os.makedirs(self.db_folder)

        # Specify the full path for the database
        self.db_path = os.path.join(self.db_folder, "valorant_stats2.db")

        # Initialize the database asynchronously
        self.bot.loop.create_task(self._initialize_db())

    async def _initialize_db(self) -> None:
        """Initialize the SQLite database and create the necessary table."""
        try:
            self.db = await aiosqlite.connect(self.db_path)
            await self.db.execute(
                """
                CREATE TABLE IF NOT EXISTS players (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    tag TEXT NOT NULL,
                    region TEXT NOT NULL
                )
                """
            )
            await self.db.commit()
        except Exception as e:
            logger.error(f"Error initializing database: {e}")

    async def save_player(self, name: str, tag: str, region: str) -> None:
        """Store player information in the database."""

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT 1 FROM players WHERE name = ? AND tag = ? AND region = ?",
                (name.lower(), tag.lower(), region.lower()),
            )
            exists = await cursor.fetchone()

        if exists:
            logger.info(f"Player {name}#{tag} already exists in the database.")
            return  # Skip inserting if player already exists
        try:
            await self.db.execute(
                """
                INSERT OR REPLACE INTO players (name, tag, region)
                VALUES (?, ?, ?)
            """,
                (name.lower(), tag.lower(), region.lower()),
            )
            await self.db.commit()
        except Exception as e:
            logger.error(f"Error storing player lookup: {e}")

    async def cog_unload(self) -> None:
        """Close the database connection when the cog is unloaded."""
        await self.db.close()

    async def player_name_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ):
        """Autocomplete function for player's username."""
        try:
            # Fetch player names from the database that start with the current input
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "SELECT DISTINCT name FROM players WHERE name LIKE ? LIMIT 25",
                    (f"{current.lower()}%",),
                )
                players = await cursor.fetchall()

            # Return the top 5 unique suggestions as choices
            return [Choice(name=player[0], value=player[0]) for player in set(players)]

        except Exception as e:
            logger.error(f"Error during player name autocomplete: {e}")
            return []

    async def player_tag_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ):
        """Autocomplete function for player's tag based on selected name."""
        try:
            # Get the currently selected player name from the interaction
            selected_name = interaction.namespace.name  # Extracts the selected name

            if not selected_name:
                return []

            # Fetch tags associated with the selected player name
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "SELECT DISTINCT tag FROM players WHERE name = ? AND tag LIKE ? LIMIT 25",
                    (
                        selected_name,
                        f"{current.lower()}%",
                    ),
                )
                tags = await cursor.fetchall()

            # Return the corresponding tags as choices
            return [Choice(name=tag[0], value=tag[0]) for tag in tags]

        except Exception as e:
            logger.error(f"Error during player tag autocomplete: {e}")
            return []

    async def get_player_mmr_history(
        self, name: str, tag: str, region: str
    ) -> Optional[dict]:
        """
        Helper function to retrieve a player's current MMR.
        :param name: Player's username
        :param tag: Player's tag
        :param region: Player's region
        :return: JSON response from the API or None if an error occurs
        """
        if not VAL_KEY:
            logger.error("VAL_KEY is not set in the environment variables.")
            return None

        try:
            response = requests.get(
                f"https://api.henrikdev.xyz/valorant/v2/mmr-history/{region}/pc/{name}/{tag}",
                headers={"Authorization": f"{VAL_KEY}"},
            )
            logger.info(
                f"https://api.henrikdev.xyz/valorant/v2/mmr-history/{region}/pc/{name}/{tag}"
            )
            if response.status_code == 200:
                logger.info(f"Successfully fetched MMR-History for {name}#{tag}")
                return response.json()
            else:
                logger.error(
                    f"Failed to fetch MMR-History for {name}#{tag}. Status code: {response.status_code}"
                )
                return None
        except Exception as e:
            logger.error(
                f"Exception occurred while fetching MMR-History for {name}#{tag}: {e}"
            )
            return None

    async def get_player_mmr(self, name: str, tag: str, region: str) -> Optional[dict]:
        """
        Helper function to retrieve a player's current MMR.
        :param name: Player's username
        :param tag: Player's tag
        :param region: Player's region
        :return: JSON response from the API or None if an error occurs
        """
        if not VAL_KEY:
            logger.error("VAL_KEY is not set in the environment variables.")
            return None

        try:
            response = requests.get(
                f"https://api.henrikdev.xyz/valorant/v3/mmr/{region}/pc/{name}/{tag}",
                headers={"Authorization": f"{VAL_KEY}"},
            )
            if response.status_code == 200:
                logger.info(f"Successfully fetched MMR for {name}#{tag}")
                return response.json()
            else:
                logger.error(
                    f"Failed to fetch MMR for {name}#{tag}. Status code: {response.status_code}"
                )
                return None
        except Exception as e:
            logger.error(f"Exception occurred while fetching MMR for {name}#{tag}: {e}")
            return None

    @app_commands.command(name="valorantmmr2")
    @app_commands.describe(
        name="Player's username",
        tag="Player's Tag",
        region="Player's Region",
        time="How long to look back for MMR history (in hours)",
    )
    @app_commands.autocomplete(name=player_name_autocomplete)
    @app_commands.autocomplete(tag=player_tag_autocomplete)
    async def valorant_mmr_history(
        self,
        interaction: discord.Interaction,
        name: str,
        tag: str,
        time: Optional[int] = 12,
        region: Optional[str] = "na",
    ):
        """Returns the stats of a Valorant player's MMR history."""
        await interaction.response.defer()

        # Convert input to lowercase
        name, tag, region = name.lower(), tag.lower(), region.lower()

        # Fetch player data
        player_mmr_history = await self.get_player_mmr_history(name, tag, region)
        player_mmr = await self.get_player_mmr(name, tag, region)

        if not player_mmr_history or "data" not in player_mmr_history:
            return await interaction.followup.send(
                f"Error fetching MMR history for {name}#{tag}. Please try again later."
            )

        if not player_mmr or "data" not in player_mmr:
            return await interaction.followup.send(
                f"Error fetching MMR for {name}#{tag}. Please try again later."
            )

        # Save player info if data exists
        await self.save_player(name, tag, region)

        # Extract match history
        history = player_mmr_history["data"].get("history", [])
        if not history:
            return await interaction.followup.send(
                f"No match history found for {name}#{tag}."
            )

        # Define time limit for filtering matches
        time_limit = datetime.utcnow() - timedelta(hours=time)

        # Filter matches in the last 'time' hours
        filtered_history = [
            match
            for match in history
            if convert_to_datetime(match["date"]) >= time_limit
        ]

        # Get starting rank/elo by finding the last match before the time limit
        starting_match = next(
            (
                match
                for match in history
                if convert_to_datetime(match["date"]) < time_limit
            ),
            None,
        )
        starting_elo = (
            starting_match["elo"]
            if starting_match
            else (filtered_history[-1]["elo"] if filtered_history else None)
        )
        starting_rank = starting_match["tier"]["name"] if starting_match else "Unknown"

        if not filtered_history:
            return await interaction.followup.send(
                f"No matches found for {name}#{tag} in the last {time} hours."
            )

        # Calculate RR changes
        ending_elo = filtered_history[0]["elo"]
        total_rr_change = ending_elo - starting_elo

        # Calculate win/loss record
        wins = sum(1 for match in filtered_history if match["last_change"] > 0)
        losses = sum(1 for match in filtered_history if match["last_change"] < 0)
        draws = sum(1 for match in filtered_history if match["last_change"] == 0)
        total_matches = len(filtered_history)
        win_loss_ratio = wins / total_matches if total_matches > 0 else 0
        match_display = []
        for match in filtered_history:
            change = match["last_change"]
            if change > 0:
                emoji = "✅"
            elif change < 0:
                emoji = "❌"
            else:
                emoji = "➖"

            # Format with sign and spacing
            sign = "+" if change > 0 else ""
            match_display.append(f"{emoji} ({sign}{change})")

        # Group into rows of 5 for readability
        rows = [
            "  ".join(match_display[i : i + 5]) for i in range(0, len(match_display), 5)
        ]
        match_results_display = "\n".join(rows)

        # Fetch current rank info
        current_mmr = player_mmr["data"].get("current", {})
        current_rank = current_mmr.get("tier", {}).get("name", "Unknown")
        current_rr = current_mmr.get("rr", 0)
        shields = current_mmr.get("rank_protection_shields", 0)

        rr_change_display = (
            f"+{total_rr_change}" if total_rr_change > 0 else f"{total_rr_change}"
        )

        embed = create_embed(
            title=f"MMR history for {name}#{tag} (last {time} hours)",
            description="Here is a summary of your recent matches.",
            fields=[
                ("Total Matches", str(total_matches), True),
                ("Wins", str(wins), True),
                ("Losses/Draws", f"{losses}/{draws}", True),
                ("Win/Loss Ratio", f"{win_loss_ratio:.2f}", True),
                ("Total RR Change", f"{rr_change_display} RR", True),
                ("\u200b", "\u200b", True),  # Invisible placeholder
                ("Starting Rank", starting_rank or "Unknown", True),
                ("Starting RR", str(starting_elo % 100), True),
                ("\u200b", "\u200b", True),  # Invisible placeholder
                ("Current Rank", current_rank, True),
                ("Current RR", str(current_rr), True),
                ("\u200b", "\u200b", True),  # Invisible placeholder
                ("Match History (Latest → Oldest)", match_results_display, False),
                ("Total Shields", str(shields), True),
            ],
            color=discord.Color.blue(),
        )

        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Valorant2(bot))
    logger.info("Valorant2 is Loaded")
