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


class TFT(commands.Cog):
    """TFT stats"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

        self.db_folder = "database/tft"
        # Ensure the 'database' folder exists
        if not os.path.exists(self.db_folder):
            os.makedirs(self.db_folder)

        # Specify the full path for the database
        self.db_path = os.path.join(self.db_folder, "tft.db")

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
                    tag TEXT NOT NULL
                )
                """
            )
            await self.db.commit()
        except Exception as e:
            logger.error(f"Error initializing database: {e}")

    async def save_player(self, name: str, tag: str) -> None:
        """Store player information in the database."""

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT 1 FROM players WHERE name = ? AND tag = ?",
                (name.lower(), tag.lower()),
            )
            exists = await cursor.fetchone()

        if exists:
            logger.info(f"Player {name}#{tag} already exists in the database.")
            return  # Skip inserting if player already exists
        try:
            await self.db.execute(
                """
                INSERT OR REPLACE INTO players (name, tag)
                VALUES (?, ?)
            """,
                (name.lower(), tag.lower()),
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

    async def get_player_mmr(self, name: str, tag: str) -> Optional[dict]:
        """
        Helper function to retrieve a player's current MMR.
        :param name: Player's username
        :param tag: Player's tag
        :return: JSON response from the API or None if an error occurs
        """
        if not VAL_KEY:
            logger.error("VAL_KEY is not set in the environment variables.")
            return None

        try:
            response = requests.get(
                f"https://ap.tft.tools/player/stats2/na1/{name}/{tag}/140/50",
            )
            print(response)
            print(f"https://ap.tft.tools/player/stats2/na1/{name}/{tag}/140/50")
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

    @app_commands.command(name="tftmmr")
    @app_commands.describe(
        name="Player's username",
        tag="Player's Tag",
        time="How long to look back for MMR history (in hours)",
    )
    @app_commands.autocomplete(name=player_name_autocomplete)
    @app_commands.autocomplete(tag=player_tag_autocomplete)
    async def tftmmr(
        self,
        interaction: discord.Interaction,
        name: str,
        tag: str,
        time: Optional[int] = 12,
    ):
        """Returns the stats of a TFT player's MMR history."""
        await interaction.response.defer()

        name, tag = name.lower(), tag.lower()
        player_mmr = await self.get_player_mmr(name, tag)

        if not player_mmr or "matches" not in player_mmr:
            return await interaction.followup.send(
                f"Error fetching MMR for {name}#{tag}. Please try again later."
            )

        await self.save_player(name, tag)
        matches = player_mmr.get("matches", [])

        # Filter by time
        cutoff_time = datetime.utcnow() - timedelta(hours=time)
        filtered_matches = [
            m
            for m in matches
            if datetime.utcfromtimestamp(m["dateTime"] / 1000) >= cutoff_time
        ]

        if not filtered_matches:
            return await interaction.followup.send(
                f"No games found for {name}#{tag} in the past {time} hours."
            )

        # Stats aggregation
        placements = []
        rank_before = filtered_matches[-1]["rankBefore"][0]
        lp_before = filtered_matches[-1]["rankBefore"][1]
        rank_after = filtered_matches[0]["rankAfter"][0]
        lp_after = filtered_matches[0]["rankAfter"][1]

        for match in filtered_matches:
            placements.append(match["info"]["placement"])

        avg_placement = sum(placements) / len(placements)
        total_lp_diff = sum(match.get("lpDiff", 0) for match in filtered_matches)

        # Build embed
        embed = discord.Embed(
            title=f"TFT MMR History - {name}#{tag}",
            description=f"Tracking the last {len(filtered_matches)} games over the past {time} hours",
            color=discord.Color.blue(),
        )
        embed.add_field(
            name="Starting Rank", value=f"{rank_before} {lp_before} LP", inline=True
        )
        embed.add_field(
            name="Current Rank", value=f"{rank_after} {lp_after} LP", inline=True
        )
        embed.add_field(name="LP Change", value=f"{total_lp_diff:+} LP", inline=True)
        embed.add_field(
            name="Average Placement", value=f"{avg_placement:.2f}", inline=True
        )
        embed.set_footer(
            text=f"Last updated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
        )

        # LP History (latest to oldest)
        lp_changes = []
        for match in filtered_matches:
            rb, _ = match["rankBefore"]
            ra, _ = match["rankAfter"]
            delta = match.get("lpDiff", 0)
            lp_changes.append(f"{delta:+} LP")

        lp_history_str = " | ".join(lp_changes)
        embed.add_field(
            name="LP History (Latest → Oldest)", value=lp_history_str, inline=False
        )

        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TFT(bot))
    logger.info("TFT is Loaded")
