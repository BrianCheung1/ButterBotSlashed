import os
import uuid
from datetime import datetime, timedelta
from typing import List, Optional

import aiosqlite
import discord
import requests
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import commands
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

load_dotenv()
VAL_KEY = os.getenv("VAL")


class Valorant(commands.Cog):
    """Valorant stats"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.queue_manager = QueueManager()
        self.db_folder = "valorant_database"
        self.player_names = []
        self.player_tags = []

        # Ensure the 'database' folder exists
        if not os.path.exists(self.db_folder):
            os.makedirs(self.db_folder)

        # Specify the full path for the database
        self.db_path = os.path.join(self.db_folder, "valorant_stats.db")

        # Initialize the database asynchronously
        self.bot.loop.create_task(self._initialize_db())

    async def _initialize_db(self):
        """Initialize the SQLite database and create the necessary table."""
        self.db = await aiosqlite.connect(self.db_path)
        await self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS player_lookups (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                tag TEXT NOT NULL,
                region TEXT NOT NULL
            )
            """
        )
        await self.db.commit()

    async def store_player_lookup(self, name: str, tag: str, region: str):
        """Store player lookup information in the database."""
        await self.db.execute(
            """
            INSERT INTO player_lookups (name, tag, region)
            VALUES (?, ?, ?)
        """,
            (name, tag, region),
        )
        await self.db.commit()

    @app_commands.command(name="valorantgames")
    @app_commands.describe(
        name="Player's username",
        tag="Player's Tag",
        region="Players'Region",
    )
    async def valorant_games(
        self,
        interaction: discord.Interaction,
        name: str,
        tag: str,
        region: Optional[str] = "NA",
    ):
        """Returns the stats of a valorant games"""
        await interaction.response.defer()
        stored_matches = self.get_stored_matches(region, name, tag)
        current_season = self.get_current_season()
        if isinstance(stored_matches, str):
            await self.store_player_lookup(name, tag, region)
            await interaction.followup.send(f"{stored_matches}")
            return

        select = MatchSelector(self.bot, stored_matches, current_season, name, tag)
        view = discord.ui.View()
        view.add_item(select)

        await interaction.followup.send(view=view)

    @app_commands.choices(
        time=[
            Choice(name="1 Hour", value=1),
            Choice(name="2 Hour", value=2),
            Choice(name="3 Hour", value=3),
            Choice(name="4 Hour", value=4),
            Choice(name="5 Hour", value=5),
            Choice(name="6 Hour", value=6),
            Choice(name="12 Hour", value=12),
            Choice(name="1 Day", value=24),
            Choice(name="2 Days", value=48),
            Choice(name="3 Days", value=72),
            Choice(name="1 Week", value=168),
        ]
    )
    @app_commands.command(name="valorantmmr")
    @app_commands.describe(
        name="Player's username",
        tag="Player's Tag",
        region="Players'Region",
        time="How long to look back for MMR history",
    )
    async def valorant_mmr_history(
        self,
        interaction: discord.Interaction,
        name: str,
        tag: str,
        time: Optional[int] = 24,
        region: Optional[str] = "NA",
    ):
        """Returns the stats of a valorant player's mmr history"""
        await interaction.response.defer()
        api_url = f"https://api.henrikdev.xyz/valorant/v1/mmr-history/na/{name}/{tag}?api_key={VAL_KEY}"
        api_url2 = f"https://api.henrikdev.xyz/valorant/v1/mmr/na/{name}/{tag}?api_key={VAL_KEY}"
        response = requests.get(api_url)
        response2 = requests.get(api_url2)

        if response.status_code == 200 and response2.status_code == 200:
            account_mmr = response.json()
            current_mmr = response2.json()
            mmr_data = account_mmr["data"]
            current_mmr_data = current_mmr["data"]
            mmr = 0
            wins = 0
            loses = 0
            if (
                current_mmr_data.get("name") is None
                and current_mmr_data.get("tag") is None
            ):
                await interaction.followup.send(
                    "Failed to fetch MMR history. Incorrect Name or Tag."
                )
                return
            await self.store_player_lookup(name, tag, region)
            current_rank = current_mmr_data.get("currenttierpatched", "Unknown")
            current_rr = current_mmr_data.get("elo", 0)
            current_rank_picture = current_mmr_data.get("images", {}).get(
                "small", "unknown Url"
            )
            cutoff_date = datetime.utcnow() - timedelta(hours=time)
            starting_rank = "Unknown"
            starting_rr = 0

            for i, game_data in enumerate(mmr_data):
                game_date_str = game_data.get("date", "")
                game_date = datetime.strptime(game_date_str, "%A, %B %d, %Y %I:%M %p")
                # Check if game date is less than current date and break the loop if it is
                if game_date < cutoff_date:
                    starting_rank = game_data.get("currenttierpatched", "Unknown")
                    starting_rr = game_data.get("elo", 0)
                    print("Breaking loop, game date is less than current date")
                    break
                game_mmr_change = game_data.get("mmr_change_to_last_game", 0)
                if game_mmr_change > 0:
                    wins += 1
                else:
                    loses += 1
            if starting_rank == "Unknown":
                mmr = 0
            else:
                mmr = current_rr - starting_rr

            embed = discord.Embed(
                title=f"{name}'s MMR history",
                description=f"MMR change in the last {time} hours",
            )
            embed.add_field(name="Games Won", value=wins, inline=True)
            embed.add_field(name="Games Lost", value=loses, inline=True)
            embed.add_field(name="\u200B", value="\u200B")
            embed.add_field(name="Starting Rank", value=starting_rank, inline=True)
            embed.add_field(
                name="Starting RR", value=f"{starting_rr%100}/100", inline=True
            )
            embed.add_field(name="\u200B", value="\u200B")
            embed.add_field(name="Current Rank", value=current_rank, inline=True)
            embed.add_field(
                name="Current RR", value=f"{current_rr%100}/100", inline=True
            )
            embed.add_field(name="\u200B", value="\u200B")
            mmr_display = f"+{mmr}" if mmr > 0 else f"{mmr}"
            embed.add_field(name="RR Change", value=mmr_display, inline=False)
            embed.timestamp = datetime.now()
            embed.set_thumbnail(url=current_rank_picture)

            await interaction.followup.send(embed=embed)
        else:
            # Handle error if the response was not successful
            await interaction.followup.send(
                "Failed to fetch MMR history. Please try again later."
            )

    @app_commands.command(name="valorantstats")
    @app_commands.describe(
        name="Player's username",
        tag="Player's Tag",
        region="Players'Region",
    )
    async def valorant_stats(
        self,
        interaction: discord.Interaction,
        name: str,
        tag: str,
        region: Optional[str] = "NA",
    ):
        """Returns the stats of a valorant player's"""
        await interaction.response.defer()

        account_details = self.get_account_details(name, tag)
        stored_matches = self.get_stored_matches(region, name, tag)
        current_season = self.get_current_season()
        mmr_history = self.get_mmr_history(region, name, tag)

        # Check if any of the variables is a string, indicating an error or unexpected response
        if (
            isinstance(account_details, str)
            or isinstance(stored_matches, str)
            or isinstance(mmr_history, str)
        ):
            await self.store_player_lookup(name, tag, region)
            await interaction.followup.send(
                f"{account_details} \n{stored_matches} \n{mmr_history}"
            )
            return

        account_level = account_details.get("account_level", "Unknown")
        account_last_updated = account_details.get("last_update", "Unknown")
        account_small_card = account_details.get("card", {}).get("small", "Unknown")
        account_wide_card = account_details.get("card", {}).get("wide", "Unknown")

        stats = self.calculate_stats(stored_matches, current_season, mmr_history)
        embeds = self.player_all_stats_embeds(
            name,
            account_level,
            account_last_updated,
            account_small_card,
            account_wide_card,
            stats,
        )
        view = ValorantEmbedChanger(embeds)
        await interaction.followup.send(embed=embeds[0], view=view)

    @app_commands.command(name="valoranttracker")
    @app_commands.describe(
        name="Player's username",
        tag="Player's Tag",
    )
    async def valorant_tracker(
        self, interaction: discord.Interaction, name: str, tag: str
    ):
        """Returns the stats of a valorant player's using tracker.gg api"""
        await interaction.response.defer()

        api_url = f"https://api.tracker.gg/api/v2/valorant/standard/matches/riot/{name.replace(' ', '%20')}%23{tag}"

        headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36",
            "Cookie": "cf_clearance=ARR45y2wBdWY.s7EwjJ_hLgcIh4zBr9eIACnu3xsJm0-1715057869-1.0.1.1-9J4.z0KHMC8iwTZHxEErmc5nbQYt5j1idKLMISLbI.PTynhA1_aM8DgJs6z08DqYwCYf6340ttcsepZxpVmJmQ; X-Mapping-Server=s22; cf_clearance=eDLkbZ1HnlVuCeBcNtuVJX21SNyOmilcFRCcztE.17c-1716841883-1.0.1.1-sqgpLOJD3Li048S9hDPYfdBTAKFCzy_r4j.Jl3b9aD.I7O2ML5Ja5unToc4NFMVnQhhWDoSkbqhyCKA2JJ2B7g; __cflb=02DiuFQAkRrzD1P1mdkJhfdTc9AmTWwYj1vZQQJFRZEKW; session_id=d95a6756-e253-4374-a768-ed8b3ceaf700; __cf_bm=iqiod4DFjbtTDk.0ga2cNam5uW1ND_oC7CWkQuIusEc-1716845622-1.0.1.1-I3eKaaqwDdi9GmWZt94uAlQ7fyy.prRwLiqRAe6ZiC9sCN.5kmK7.34O1tvLR1EXeW4n5lRqU8eF3Mm_5rCFzHyygREoTIRT7akS9oF2_yw",
            "Sec-Ch-Ua": 'Google Chrome";v="125", "Chromium";v="125", "Not.A/Brand";v="24',
        }
        response = requests.get(api_url, headers=headers)
        if response.status_code == 200:
            await self.store_player_lookup(name, tag, "NA")
            data = response.json()

            # Process the data to create select options
            # Store matches data
            matches = data["data"]["matches"]
            match_details = {match["attributes"]["id"]: match for match in matches}

            # Process the data to create select options
            options = []
            for match in matches:
                map_name = match.get("metadata", {}).get("mapName", "Unknown Map")
                result = match.get("metadata", {}).get("result", "Unknown Result")
                time = match.get("metadata", {}).get("timestamp")
                if time:
                    input_format = ""
                    dt = None
                    try:
                        input_format = "%Y-%m-%dT%H:%M:%S.%f%z"
                        dt = datetime.strptime(time, input_format)
                    except ValueError:
                        input_format = "%Y-%m-%dT%H:%M:%S%z"
                        dt = datetime.strptime(time, input_format)

                    dt_adjusted = dt - timedelta(hours=4)  # Adjusting time zone
                    formatted_time = dt_adjusted.strftime("%Y-%m-%d %I:%M %p")
                else:
                    formatted_time = "Unknown Time"

                label = f"{map_name} - {result} - {formatted_time}"
                options.append(
                    discord.SelectOption(label=label, value=match["attributes"]["id"])
                )

            # Create the select menu
            select = discord.ui.Select(placeholder="Choose a match", options=options)

            # Define a callback for the select menu
            async def callback(interaction: discord.Interaction):
                selected_match_id = select.values[0]
                match = match_details.get(selected_match_id)

                if match:
                    # Extract player stats
                    player_stats = next(
                        (
                            player
                            for player in match.get("segments", [])
                            if player.get("metadata", {})
                            .get("platformUserHandle", "")
                            .lower()
                            == f"{name}#{tag.lower()}"
                        ),
                        None,
                    )

                    if player_stats:
                        # Extract stats
                        stats_mapping = {
                            "kills": "Kills",
                            "deaths": "Deaths",
                            "assists": "Assists",
                            "roundsWon": "Rounds Won",
                            "roundsLost": "Rounds Lost",
                            "placement": "Placement",
                            "econRating": "Econ Rating",
                            "scorePerRound": "ACS",
                            "damagePerRound": "ADR",
                            "headshotsPercentage": "HS%",
                            "firstBloods": "First Bloods",
                            "firstDeaths": "First Deaths",
                            "kAST": "KAST",
                            "clutches": "Clutches Won",
                            "clutchesLost": "Clutches Lost",
                            "aces": "Aces",
                            "plants": "Plants",
                            "defuses": "Defuses",
                            "rank": "Rank",
                            "trnPerformanceScore": "Tracker Score",
                        }
                        agent = player_stats.get("metadata", {}).get(
                            "agentName", "Unknown Agent"
                        )
                        agent_url = player_stats.get("metadata", {}).get(
                            "agentImageUrl", "Unknown Url"
                        )
                        map_name = match.get("metadata", {}).get(
                            "mapName", "Unknown Map"
                        )
                        embed = discord.Embed(
                            title=f"{name}' stats on {map_name}",
                            description=f"Agent: {agent}",
                        )
                        embed.set_thumbnail(url=agent_url)

                        for key, label in stats_mapping.items():
                            if key == "rank":
                                value = (
                                    player_stats.get("stats", {})
                                    .get(key, {})
                                    .get("metadata", {})
                                    .get("tierName", "Unranked")
                                )
                            else:
                                value = (
                                    player_stats.get("stats", {})
                                    .get(key, {})
                                    .get("displayValue", "Unknown")
                                )
                            if key == "placement":
                                embed.add_field(
                                    name=label, value=f"{value}/10", inline=True
                                )
                            elif key == "trnPerformanceScore":
                                embed.add_field(
                                    name=label, value=f"{value}/1000", inline=True
                                )
                            else:
                                embed.add_field(name=label, value=value, inline=True)

                        splash_url = match.get("metadata", {}).get("mapImageUrl")
                        if splash_url:
                            embed.set_image(url=splash_url)

                        playtime = (
                            player_stats.get("stats", {})
                            .get("playtime", {})
                            .get("displayValue", "Unknown")
                        )
                        embed.set_footer(text=f"Match time: {playtime}")

                        await interaction.response.edit_message(embed=embed)
                    else:
                        await interaction.followup.send(
                            "Player stats not found for the selected match."
                        )
                else:

                    await interaction.followup.send("Match details not found.")

            select.callback = callback

            # Create the view with the select menu
            view = discord.ui.View()
            view.add_item(select)

            # Send the select menu to the user
            await interaction.followup.send(view=view)
        else:
            print(response.status_code)
            await interaction.followup.send("Error with API, Try again later")

    @valorant_games.autocomplete("name")
    @valorant_mmr_history.autocomplete("name")
    @valorant_stats.autocomplete("name")
    @valorant_tracker.autocomplete("name")
    async def autocomplete_name(
        self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice]:
        """Autocomplete player name based on database."""
        if current in self.player_names:
            return self.player_names

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT DISTINCT name FROM player_lookups
                WHERE name LIKE ?
                LIMIT 25
                """,
                (f"{current}%",),
            )
            results = await cursor.fetchall()
        self.player_names = [
            app_commands.Choice(name=name[0], value=name[0]) for name in results
        ]

        return self.player_names

    @valorant_games.autocomplete("tag")
    @valorant_mmr_history.autocomplete("tag")
    @valorant_stats.autocomplete("tag")
    @valorant_tracker.autocomplete("tag")
    async def autocomplete_tag(
        self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice]:
        """Autocomplete player tag based on database."""
        chosen_name = None
        for option in interaction.data.get("options", []):
            if option["name"] == "name":
                chosen_name = option.get("value", None)
                break  # Stop looping once we find the 'name'

        if not chosen_name:
            return []  # If no name is selected, return an empty list

        if current in self.player_tags:
            return self.player_tags
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT DISTINCT tag
                FROM player_lookups
                WHERE tag LIKE ?
                ORDER BY
                    CASE WHEN name = ? THEN 0 ELSE 1 END, -- Prioritize chosen name's tag
                    tag ASC -- Alphabetical order for other tags
                LIMIT 25
                """,
                (
                    f"{current}%",  # Match tags starting with the current input
                    chosen_name,  # Prioritize tags associated with the chosen name
                ),
            )
            results = await cursor.fetchall()

        if not results:
            return []  # Return an empty list if no results are found

        self.player_tags = [
            app_commands.Choice(name=tag[0], value=tag[0]) for tag in results
        ]

        return self.player_tags

    @valorant_games.autocomplete("region")
    @valorant_mmr_history.autocomplete("region")
    @valorant_stats.autocomplete("region")
    async def autocomplete_region(
        self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice]:
        """Autocomplete region from predefined list."""
        regions = ["NA", "EU", "AP", "KR", "LATAM", "BR"]
        matching_regions = [
            app_commands.Choice(name=region, value=region)
            for region in regions
            if current.lower() in region.lower()
        ]
        return matching_regions

    @app_commands.command(name="valorantqueue")
    @app_commands.describe(
        size="Number of players before queue is full",
        queue_id="Creates a queue with ID of choice or provide an existing ID to resend that queue to the channel",
        members="Members that are already in queue",
        # role = "Role to ping"
    )
    async def valorant_queue(
        self,
        interaction: discord.Interaction,
        size: Optional[int] = 5,
        queue_id: Optional[str] = None,
        members: Optional[str] = None,
    ):
        """Create a queue for valorant team of any size"""
        response = ""
        # Generate a unique queue_id using uuid
        if queue_id:
            # If queue_id is provided, fetch the existing queue
            current_queue = self.queue_manager.get_queue(queue_id)
            queue_members = "\n".join(user.mention for user in current_queue)
            if current_queue:
                response = f"\n\nCurrent Queue:\n{queue_members}"
            else:
                response = "\n\nThe queue is currently empty."
            if current_queue is None:
                await interaction.response.send_message(
                    "This queue ID does not exist", ephemeral=True
                )
                return
            # Delete the previous response
            previous_message_id = self.queue_manager.get_message_id(queue_id)
            if previous_message_id:
                try:
                    previous_message = await interaction.channel.fetch_message(
                        previous_message_id
                    )
                    await previous_message.delete()
                    self.queue_manager.delete_message_id(queue_id)
                except discord.NotFound:
                    pass  # The message was already deleted
        else:
            # Generate a unique queue_id using uuid
            unique_id = str(uuid.uuid4())
            queue_id = f"valorant_{interaction.channel_id}_{unique_id}"

            if members:
                # Split mentions and fetch members
                mentions = members.split()
                member_objects = []
                for mention in mentions:
                    member_id = int(mention.strip("<@!>"))
                    member = interaction.guild.get_member(member_id)
                    if member:
                        member_objects.append(member)
                        self.queue_manager.join_queue(queue_id, member)

                queue_members = "\n".join(user.mention for user in member_objects)
                response = f"\n\nCurrent Queue:\n{queue_members}"
                if len(member_objects) >= size:
                    for member in member_objects:
                        try:
                            await member.send(
                                f"{size} R's are ready\nCurrent Queue:\n{queue_members}\n"
                            )
                        except Exception:
                            print(f"\n{member.mention} could not be Dmed")

        # Role Mention
        role_id = 1250116396935807130  # Replace with your role ID
        role = discord.utils.get(interaction.guild.roles, id=role_id)
        role_mention = role.mention if role else ""
        # Send the new message and store its ID
        await interaction.response.send_message(
            f"R's? {role_mention}{response}",
            view=QueueButton(
                self.bot, size, self.queue_manager, queue_id, interaction.user.id
            ),
        )
        new_message = await interaction.original_response()
        self.queue_manager.set_message_id(queue_id, new_message.id)

    def calculate_stats(
        self, matches: List[dict], season: str, mmr_history: dict
    ) -> dict:
        stats = {
            "total_kills": 0,
            "total_deaths": 0,
            "total_assists": 0,
            "total_games": 0,
            "total_wins": 0,
            "total_loses": 0,
            "total_draws": 0,
            "total_headshots": 0,
            "total_bodyshots": 0,
            "total_legshots": 0,
            "total_score": 0,
            "total_damage": 0,
            "total_rounds": 0,
            "agents_played": {},
            "maps_played": {},
            "peak_rank": "Unranked",
            "current_rank": "Unranked",
            "current_season": season,
            "clusters": {},
        }

        for match in matches:
            if (
                match.get("meta", {}).get("season", {}).get("short", "Unknown")
                == season
            ):
                stats = self.update_match_stats(stats, match, mmr_history)

        return stats

    def update_match_stats(self, stats: dict, match: dict, mmr_history: dict) -> dict:
        game_stats = match.get("stats", {})
        team_color = game_stats.get("team", "Unknown")
        agent = game_stats.get("character", {}).get("name", "Unknown")
        cluster = match.get("meta", {}).get("cluster", "N/A")
        map_name = match.get("meta", {}).get("map", {}).get("name", "Unknown")
        blue_team_rounds = match.get("teams", {}).get("blue", 0)
        red_team_rounds = match.get("teams", {}).get("red", 0)

        stats["total_kills"] += game_stats.get("kills", 0)
        stats["total_deaths"] += game_stats.get("deaths", 0)
        stats["total_assists"] += game_stats.get("assists", 0)
        stats["total_games"] += 1
        stats["total_headshots"] += game_stats.get("shots", {}).get("head", 0)
        stats["total_bodyshots"] += game_stats.get("shots", {}).get("body", 0)
        stats["total_legshots"] += game_stats.get("shots", {}).get("leg", 0)
        stats["total_score"] += game_stats.get("score", 0)
        stats["total_damage"] += game_stats.get("damage", {}).get("made", 0)
        stats["total_rounds"] += blue_team_rounds + red_team_rounds

        if map_name not in stats["maps_played"]:
            stats["maps_played"][map_name] = {"wins": 0, "loses": 0, "draws": 0}

        if agent not in stats["agents_played"]:
            stats["agents_played"][agent] = {"wins": 0, "loses": 0, "draws": 0}

        if cluster not in stats["clusters"]:
            stats["clusters"][cluster] = {"wins": 0, "loses": 0, "draws": 0}

        peak = mmr_history.get("peak")
        if peak:
            stats["peak_rank"] = (
                peak.get("season", {}).get("short", "Unknown")
                + " - "
                + peak.get("tier", {}).get("name", "Unranked")
            )
        else:
            stats["peak_rank"] = "Unknown - Unranked"
        stats["current_rank"] = (
            mmr_history.get("current", {}).get("tier", {}).get("name", "Unranked")
            + " - "
            + str(mmr_history.get("current", {}).get("rr", 0))
            + " RR "
        )

        if (team_color == "Blue" and blue_team_rounds > red_team_rounds) or (
            team_color == "Red" and red_team_rounds > blue_team_rounds
        ):
            stats["total_wins"] += 1
            stats["maps_played"][map_name]["wins"] = (
                stats["maps_played"][map_name].get("wins", 0) + 1
            )
            stats["agents_played"][agent]["wins"] = (
                stats["agents_played"][agent].get("wins", 0) + 1
            )
            stats["clusters"][cluster]["wins"] = (
                stats["clusters"][cluster].get("wins", 0) + 1
            )
        elif (team_color == "Blue" and blue_team_rounds < red_team_rounds) or (
            team_color == "Red" and red_team_rounds < blue_team_rounds
        ):
            stats["total_loses"] += 1
            stats["maps_played"][map_name]["loses"] = (
                stats["maps_played"][map_name].get("loses", 0) + 1
            )
            stats["agents_played"][agent]["loses"] = (
                stats["agents_played"][agent].get("loses", 0) + 1
            )
            stats["clusters"][cluster]["loses"] = (
                stats["clusters"][cluster].get("loses", 0) + 1
            )
        else:
            stats["total_draws"] += 1
            stats["maps_played"][map_name]["draws"] = (
                stats["maps_played"][map_name].get("draws", 0) + 1
            )
            stats["agents_played"][agent]["draws"] = (
                stats["agents_played"][agent].get("draws", 0) + 1
            )
            stats["clusters"][cluster]["draws"] = (
                stats["clusters"][cluster].get("draws", 0) + 1
            )
        return stats

    def player_all_stats_embeds(
        self,
        name: str,
        level: str,
        last_updated: str,
        small_card: str,
        wide_card: str,
        stats: dict,
    ) -> List[discord.Embed]:
        current_season = stats["current_season"]
        total_games = stats["total_games"]

        if stats["total_games"] == 0:
            embed_no_games = discord.Embed(
                title=f"{name}'s Overview", description=f"Level {level}"
            )
            embed_no_games.set_image(url=wide_card)
            embed_no_games.set_thumbnail(url=small_card)
            embed_no_games.set_footer(
                text=f"Current Season: {current_season} - Total Games: {total_games}"
            )
            return [embed_no_games]
        total_shots = (
            stats["total_headshots"]
            + stats["total_bodyshots"]
            + stats["total_legshots"]
        )
        average_kills = round((stats["total_kills"] / stats["total_games"]), 2)
        average_deaths = round((stats["total_deaths"] / stats["total_games"]), 2)
        average_assists = round((stats["total_assists"] / stats["total_games"]), 2)
        average_headshots = round(((stats["total_headshots"] / total_shots) * 100), 2)
        average_bodyshots = round(((stats["total_bodyshots"] / total_shots) * 100), 2)
        average_legshots = round(((stats["total_legshots"] / total_shots) * 100), 2)
        average_score = round(stats["total_score"] / stats["total_rounds"])
        average_damage = round((stats["total_damage"] / stats["total_rounds"]), 2)
        win_rate = round(((stats["total_wins"] / stats["total_games"]) * 100), 2)

        embed1 = discord.Embed(title=f"{name}'s Overview", description=f"Level {level}")
        embed1.add_field(name="Peak Rank", value=stats["peak_rank"], inline=True)
        embed1.add_field(name="Current Rank", value=stats["current_rank"], inline=True)
        embed1.add_field(name="Last Updated", value=last_updated, inline=True)
        embed1.add_field(name="AVG Kills", value=average_kills, inline=True)
        embed1.add_field(name="AVG Deaths", value=average_deaths, inline=True)
        embed1.add_field(name="AVG Assists", value=average_assists, inline=True)
        embed1.add_field(name="Games Won", value=stats["total_wins"], inline=True)
        embed1.add_field(name="Games Lost", value=stats["total_loses"], inline=True)
        embed1.add_field(name="Games Drawed", value=stats["total_draws"], inline=True)
        embed1.add_field(name="Win Rate", value=f"{win_rate:g}%", inline=False)
        embed1.add_field(
            name="AVG Headshots", value=f"{average_headshots}%", inline=True
        )
        embed1.add_field(
            name="AVG Bodyshots", value=f"{average_bodyshots}%", inline=True
        )
        embed1.add_field(name="AVG Legshots", value=f"{average_legshots}%", inline=True)
        embed1.add_field(name="ACS", value=f"{average_score}", inline=True)
        embed1.add_field(name="ADR", value=f"{average_damage}", inline=True)
        embed1.add_field(name="", value="\u200b", inline=True)
        embed1.set_image(url=wide_card)
        embed1.set_thumbnail(url=small_card)
        embed1.set_footer(
            text=f"Current Season: {current_season} - Total Games: {total_games}"
        )

        embed2 = discord.Embed(
            title=f"{name}'s Agents Played", description=f"Level {level}"
        )
        for key, value in sorted(
            stats["agents_played"].items(),
            key=lambda item: item[1]["wins"],
            reverse=True,
        ):
            formatted_value = (
                f"W:{value.get('wins', 0)} - "
                f"L:{value.get('loses', 0)} - "
                f"D:{value.get('draws', 0)}"
            )
            embed2.add_field(name=key, value=formatted_value, inline=True)

            # embed2.add_field(name=key, value=str(value), inline=True)
        embed2.set_image(url=wide_card)
        embed2.set_thumbnail(url=small_card)
        embed2.set_footer(
            text=f"Current Season: {current_season} - Total Games: {total_games}"
        )

        embed3 = discord.Embed(
            title=f"{name}'s Maps played", description=f"Level {level}"
        )
        for key, value in sorted(
            stats["maps_played"].items(),
            key=lambda item: item[1]["wins"],
            reverse=True,
        ):
            formatted_value = (
                f"W:{value.get('wins', 0)} - "
                f"L:{value.get('loses', 0)} - "
                f"D:{value.get('draws', 0)}"
            )
            embed3.add_field(name=key, value=formatted_value, inline=True)
        embed3.set_image(url=wide_card)
        embed3.set_thumbnail(url=small_card)
        embed3.set_footer(
            text=f"Current Season: {current_season} - Total Games: {total_games}"
        )

        embed4 = discord.Embed(title=f"{name}'s Clusters played")
        for key, value in sorted(
            stats["clusters"].items(),
            key=lambda item: item[1]["wins"],
            reverse=True,
        ):
            formatted_value = (
                f"W:{value.get('wins', 0)} - "
                f"L:{value.get('loses', 0)} - "
                f"D:{value.get('draws', 0)}"
            )
            embed4.add_field(name=key, value=formatted_value, inline=True)
        embed4.set_image(url=wide_card)
        embed4.set_thumbnail(url=small_card)
        embed4.set_footer(
            text=f"Current Season: {current_season} - Total Games: {total_games}"
        )
        return [embed1, embed2, embed3, embed4]

    def get_errors(self, api_json):
        if "errors" not in api_json:
            return "No Errors"

        if "errors" in api_json:
            errors = api_json["errors"]
            if errors:
                error_info = errors[0]  # Assuming you're interested in the first error
                code = error_info.get("code", "Unknown code")
                status = error_info.get("status", "Unknown status")

        error_codes_dict = {
            0: {
                404: "Endpoint not found",
                400: "General bad user input",
                401: "Missing API Key",
                403: "Invalid API key",
                429: "Rate Limit",
            },
            1: {500: "Internal Error"},
            2: {501: "API Endpoint in this version does not exist"},
            3: {404: "File not found"},
            4: {400: "Invalid File"},
            5: {500: "Error while parsing"},
            6: {400: "Invalid Region"},
            7: {400: "Invalid Country Code"},
            8: {400: "Ivalid website category"},
            9: {500: "Error while fetching needed resource"},
            10: {400: "Unknown raw type"},
            11: {400: "JSON parsing error. Check input JSON"},
            13: {500: "Internal Redis connection error"},
            15: {500: "Premier endpoint temporary issues"},
            16: {404: "Premier team not found"},
            17: {400: "Query param division must be a number"},
            18: {400: "Query param division must be a number between 1 & 21"},
            19: {400: "Invalid premier conference"},
            20: {400: "Premier mixed querys detected (name & tag and puuid)"},
            21: {500: "Error while connecting to regular database"},
            22: {404: "Account not found"},
            23: {
                404: "Region for user not found. Please ask the user to play a deathmatch or another gamemode"
            },
            24: {
                404: "Error while fetching needed match data to retrieve users level & more"
            },
            25: {404: "No MMR data found for user"},
            26: {404: "Match not found"},
            27: {400: "Invalid mode/queue"},
            28: {400: "Invalid map"},
            29: {400: "Missing query param size"},
            30: {400: "Query param size & page must be a number"},
            31: {400: "Query param size must be greater than 0"},
            32: {400: "Query param page must be greater than 0"},
            33: {400: "Invalid season"},
            34: {400: "Query name is required"},
            35: {400: "Query tag is required"},
            36: {404: "User not found in leaderboard"},
        }

        if code in error_codes_dict and status in error_codes_dict[code]:
            return error_codes_dict[code][status]
        else:
            return "Unknown Error"

    def get_account_details(self, name, tag):
        account_api = f"https://api.henrikdev.xyz/valorant/v1/account/{name}/{tag}?force=true&api_key={VAL_KEY}"
        account_api_response = requests.get(account_api)
        account_api_json = account_api_response.json()
        error_check = self.get_errors(account_api_json)
        if error_check == "No Errors":
            return account_api_json["data"]
        else:
            return error_check + " in get_account_details"

    def get_stored_matches(self, region, name, tag):
        stored_matches_api = f"https://api.henrikdev.xyz/valorant/v1/stored-matches/{region}/{name}/{tag}?mode=competitive&api_key={VAL_KEY}"
        stored_matches_response = requests.get(stored_matches_api)
        stored_matches_json = stored_matches_response.json()
        error_check = self.get_errors(stored_matches_json)
        if error_check == "No Errors":
            return stored_matches_json["data"]
        else:
            return error_check + " in stored_matches"

    def get_current_season(self):
        current_season_api = (
            f"https://api.henrikdev.xyz/valorant/v1/content?api_key={VAL_KEY}"
        )
        current_season_response = requests.get(current_season_api)
        current_season_json = current_season_response.json()
        error_check = self.get_errors(current_season_json)
        if error_check == "No Errors":
            current_season_acts = current_season_json["acts"]
            active_episode = None
            active_act = None

            for act in current_season_acts:
                if act["isActive"]:
                    if act["type"] == "episode":
                        active_episode = (
                            act["name"].split(" ")[-1].lower()
                        )  # Extract the episode number
                    elif act["type"] == "act":
                        active_act = (
                            act["name"].split(" ")[-1].lower()
                        )  # Extract the act number

            # Combine the identifiers into the desired string format
            result = (
                f"e{active_episode}a{active_act}"
                if active_episode and active_act
                else "No active episode or act found"
            )
            return result
        else:
            return error_check + " in current_season"

    def get_mmr_history(self, region, name, tag):
        mrr_history_api = f"https://api.henrikdev.xyz/valorant/v3/mmr/{region}/pc/{name}/{tag}?api_key={VAL_KEY}"
        mrr_history_response = requests.get(mrr_history_api)
        mrr_history_json = mrr_history_response.json()
        error_check = self.get_errors(mrr_history_json)
        if error_check == "No Errors":
            return mrr_history_json["data"]
        else:
            return error_check + " in mrr_history"

    def get_match_details(self, region, match_id):
        match_details_api = f"https://api.henrikdev.xyz/valorant/v4/match/{region}/{match_id}?api_key={VAL_KEY}"
        match_details_response = requests.get(match_details_api)
        match_details_json = match_details_response.json()
        error_check = self.get_errors(match_details_json)
        if error_check == "No Errors":
            return match_details_json["data"]
        else:
            return error_check + " in match_details"


class QueueButton(discord.ui.View):
    def __init__(self, bot, size, queue_manager, queue_id, original_user_id) -> None:
        super().__init__(timeout=None)
        self.bot = bot
        self.size = size
        self.queue_manager = queue_manager
        self.queue_id = queue_id
        self.original_user_id = original_user_id

        current_queue = self.queue_manager.get_queue(self.queue_id)
        if len(current_queue) >= self.size:
            join_button = self.children[0]  # Access the "Join Queue" button
            join_button.disabled = True
            join_button.label = "Queue Full"

    @discord.ui.button(
        label="Join Queue", style=discord.ButtonStyle.primary, emoji="😎"
    )
    async def button_callback(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        # Role Mention
        role_id = 1250116396935807130  # Replace with your role ID
        role = discord.utils.get(interaction.guild.roles, id=role_id)
        role_mention = role.mention if role else ""

        response = f"R's? {role_mention}"
        user = interaction.user
        current_queue = self.queue_manager.get_queue(self.queue_id)
        current_queue_length = len(current_queue)
        if current_queue_length >= self.size:
            queue_members = "\n".join(user.mention for user in current_queue)
            response += f"\n\nCurrent Queue:\n{queue_members}"
            button.disabled = True
            button.label = "Queue Full"
            await interaction.response.edit_message(content=response, view=self)
            return

        if self.queue_manager.join_queue(self.queue_id, user):
            response += f"\n{user.mention} has joined the queue!"
        else:
            response += f"\n{user.mention}, you are already in the queue!"

        # Show current queue
        current_queue = self.queue_manager.get_queue(self.queue_id)
        if current_queue:
            queue_members = "\n".join(user.mention for user in current_queue)
            response += f"\n\nCurrent Queue:\n{queue_members}"
        else:
            response += "\n\nThe queue is currently empty."

        current_queue_length = len(current_queue)
        if current_queue_length >= self.size:
            button.disabled = True
            button.label = "Queue Full"
            for user in current_queue:
                try:
                    user_dm = await self.bot.fetch_user(user.id)
                    queue_members = "\n".join(user.mention for user in current_queue)
                    await user_dm.send(
                        f"{self.size} R's are ready\nCurrent Queue:\n{queue_members}"
                    )
                except Exception:
                    response += f"\n{user.mention} could not be Dmed"
            await interaction.response.edit_message(content=response, view=self)
        else:
            await interaction.response.edit_message(content=response)

    @discord.ui.button(
        label="Leave Queue", style=discord.ButtonStyle.danger, emoji="😢"
    )
    async def leave_queue_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        # Role Mention
        role_id = 1250116396935807130  # Replace with your role ID
        role = discord.utils.get(interaction.guild.roles, id=role_id)
        role_mention = role.mention if role else ""

        response = f"R's? {role_mention}"

        user = interaction.user
        if self.queue_manager.leave_queue(self.queue_id, user):
            response += f"\n{user.mention} has left the queue!"
        else:
            response += f"\n{user.mention}, you are not in the queue!"

        # Show current queue
        current_queue = self.queue_manager.get_queue(self.queue_id)
        if current_queue:
            queue_members = "\n".join(user.mention for user in current_queue)
            response += f"\n\nCurrent Queue:\n{queue_members}"
        else:
            response += "\n\nThe queue is currently empty."

        current_queue_length = len(current_queue)
        if current_queue_length < self.size:
            join_button = self.children[0]  # Access the "Join Queue" button
            join_button.disabled = False
            join_button.label = "Join Queue"
            await interaction.response.edit_message(content=response, view=self)
        else:
            await interaction.response.edit_message(content=response)

    @discord.ui.button(
        label="Delete Queue", style=discord.ButtonStyle.danger, emoji="❎"
    )
    async def delete_queue_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):

        if (
            interaction.user.id != self.original_user_id
            and not interaction.user.guild_permissions.manage_messages
        ):
            await interaction.response.send_message(
                "You don't have permission to delete this queue.", ephemeral=True
            )
            return

        # Check if the user has moderation permissions
        self.queue_manager.delete_queue(self.queue_id)
        previous_message_id = self.queue_manager.get_message_id(self.queue_id)
        if previous_message_id:
            try:
                previous_message = await interaction.channel.fetch_message(
                    previous_message_id
                )
                await previous_message.delete()
                self.queue_manager.delete_message_id(self.queue_id)
            except discord.NotFound:
                pass

    # @discord.ui.button(label="Show Queue ID", style=discord.ButtonStyle.danger, emoji="🆔")
    # async def show_queue_id(self, interaction: discord.Interaction, button: discord.ui.Button):
    #     if interaction.user.id != interaction.message.interaction.user.id and not interaction.user.guild_permissions.manage_messages:
    #         await interaction.response.send_message("You don't have permission to see the ID.", ephemeral=True)
    #         return

    #     response = f"The queue ID is: \n`{self.queue_id}`"
    #     await interaction.response.send_message(response, ephemeral=True)  # Send the message only to the user who clicked the button

    @discord.ui.button(
        label="Resend Queue", style=discord.ButtonStyle.danger, emoji="🔄"
    )
    async def resend_queue(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        current_queue = self.queue_manager.get_queue(self.queue_id)
        queue_members = "\n".join(user.mention for user in current_queue)
        if current_queue:
            response = f"\n\nCurrent Queue:\n{queue_members}"
        else:
            response = "\n\nThe queue is currently empty."
        if current_queue is None:
            await interaction.response.send_message(
                "This queue ID does not exist", ephemeral=True
            )
            return
        # Delete the previous response
        previous_message_id = self.queue_manager.get_message_id(self.queue_id)
        if previous_message_id:
            try:
                previous_message = await interaction.channel.fetch_message(
                    previous_message_id
                )
                await previous_message.delete()
                self.queue_manager.delete_message_id(self.queue_id)
            except discord.NotFound:
                pass  # The message was already deleted
        # Role Mention
        role_id = 1250116396935807130  # Replace with your role ID
        role = discord.utils.get(interaction.guild.roles, id=role_id)
        role_mention = role.mention if role else ""
        await interaction.response.send_message(
            f"R's? {role_mention} {response}", view=self
        )
        new_message = await interaction.original_response()
        self.queue_manager.set_message_id(self.queue_id, new_message.id)


# Queue manager class
class QueueManager:
    def __init__(self):
        self.queues = {}
        self.message_ids = {}

    def join_queue(self, queue_id, user):
        if queue_id not in self.queues:
            self.queues[queue_id] = []
        if user not in self.queues[queue_id]:
            self.queues[queue_id].append(user)
            return True
        return False

    def leave_queue(self, queue_id, user):
        if queue_id in self.queues and user in self.queues[queue_id]:
            self.queues[queue_id].remove(user)
            return True
        return False

    def delete_queue(self, queue_id):
        if queue_id in self.queues:
            del self.queues[queue_id]
        return True

    def get_queue(self, queue_id):
        return self.queues.get(queue_id, [])

    def get_all_queues(self):
        return {
            queue_id: self.queues[queue_id]
            for queue_id in self.queues
            if self.queues[queue_id]
        }

    def set_message_id(self, queue_id, message_id):
        self.message_ids[queue_id] = message_id

    def get_message_id(self, queue_id):
        return self.message_ids.get(queue_id)

    def delete_message_id(self, queue_id):
        if queue_id in self.message_ids:
            del self.message_ids[queue_id]


class ValorantEmbedChanger(discord.ui.View):
    def __init__(
        self, embeds: List[discord.Embed], match_selector: discord.ui.Select = None
    ):
        super().__init__(timeout=None)
        self.embeds = embeds
        self.current = 0
        self.update_buttons()
        self.match_selector = match_selector

    def update_buttons(self):
        self.prev_button.disabled = self.current == 0
        self.next_button.disabled = self.current == len(self.embeds) - 1

    @discord.ui.button(label="Prev", style=discord.ButtonStyle.primary, disabled=True)
    async def prev_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.current -= 1
        self.update_buttons()
        if self.match_selector:
            new_view = discord.ui.View()
            new_view.add_item(self.prev_button)
            new_view.add_item(self.next_button)
            new_view.add_item(self.match_selector)
            new_view.timeout = None
        else:
            new_view = self
        await interaction.response.edit_message(
            embed=self.embeds[self.current], view=new_view
        )

    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary)
    async def next_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.current += 1
        self.update_buttons()
        if self.match_selector:
            new_view = discord.ui.View()
            new_view.add_item(self.prev_button)
            new_view.add_item(self.next_button)
            new_view.add_item(self.match_selector)
            new_view.timeout = None
        else:
            new_view = self
        await interaction.response.edit_message(
            embed=self.embeds[self.current], view=new_view
        )


class MatchSelector(discord.ui.Select):
    def __init__(self, bot, stored_matches, current_season, name, tag):
        self.bot = bot
        self.name = name.lower()
        self.tag = tag.lower()
        options = []
        count = 0
        for match in stored_matches:
            match_season = (
                match.get("meta", {}).get("season", {}).get("short", "Unknown")
            )
            match_id = match.get("meta", {}).get("id", "Unknown")
            match_time = match.get("meta", {}).get("started_at", "Unknown")
            match_map = match.get("meta", {}).get("map", {}).get("name", "Unknown")

            # Parse the date string to a datetime object
            input_format = ""
            date_obj = None
            try:
                input_format = "%Y-%m-%dT%H:%M:%S.%fZ"
                date_obj = datetime.strptime(match_time, input_format)
            except ValueError:
                input_format = "%Y-%m-%dT%H:%M:%S%z"
                date_obj = datetime.strptime(match_time, input_format)

            # Convert the datetime object to the desired format
            output_format = "%A, %B %d, %Y %I:%M %p"
            formatted_date = date_obj.strftime(output_format)

            last_match_date = datetime.strptime(
                formatted_date, "%A, %B %d, %Y %I:%M %p"
            )
            adjusted_date = last_match_date - timedelta(hours=4)
            result_date_str = adjusted_date.strftime("%A, %B %d, %Y %I:%M %p")

            if isinstance(match_id, str) and match_season == current_season:
                option = discord.SelectOption(
                    label=f"{match_map} - {result_date_str}", value=str(match_id)
                )
                options.append(option)
                count += 1

            if count >= 25:
                break

        super().__init__(placeholder="Select a match", options=options)

    async def callback(self, interaction: discord.Interaction):
        selected_value = self.values[0]  # Get the selected match ID
        match_details = self.bot.get_cog("Valorant").get_match_details(
            "na", selected_value
        )
        stats = self.calculate_stats(match_details)
        embed = self.player_match_stats_embeds(stats)

        embeds = self.get_team_stats(match_details, self.name, self.tag)
        all_embeds = embed + embeds

        new_view = discord.ui.View()
        embed_changer = ValorantEmbedChanger(all_embeds, self)
        new_view.add_item(embed_changer.prev_button)
        new_view.add_item(embed_changer.next_button)
        new_view.add_item(self)
        new_view.timeout = None

        # Step 2: Get the Absolute Path (Optional)
        image_path = "public/output_image.png"
        absolute_image_path = os.path.abspath(image_path)
        with open(absolute_image_path, "rb") as f:
            picture = discord.File(f)

        await interaction.response.edit_message(
            embed=all_embeds[0], view=new_view, attachments=[picture]
        )

    def get_agent_abilities(self):
        agent_abilities_api = "https://valorant-api.com/v1/agents"
        agent_abilities_response = requests.get(agent_abilities_api)
        agent_abilities_json = agent_abilities_response.json()
        return agent_abilities_json["data"]

    def get_maps(self):
        maps_api = "https://valorant-api.com/v1/maps"
        maps_response = requests.get(maps_api)
        maps_json = maps_response.json()
        return maps_json["data"]

    def calculate_stats(self, match: dict) -> dict:
        stats = {
            "total_kills": 0,
            "total_deaths": 0,
            "total_assists": 0,
            "total_headshots": 0,
            "total_bodyshots": 0,
            "total_legshots": 0,
            "total_score": 0,
            "total_damage": 0,
            "total_rounds": 0,
            "ability_casts": {
                "Ability1": 0,
                "Ability2": 0,
                "Grenade": 0,
                "Ultimate": 0,
            },
            "current_rank": "Unranked",
            "first_bloods": 0,
            "first_deaths": 0,
            "bomb_plants": 0,
            "bomb_defuses": 0,
            "account_level": 0,
            "agent_played": "Unknown",
            "map_played": "Unknown",
            "team": "Unknown",
            "rounds_won": 0,
            "rounds_lost": 0,
            "game_time": 0,
            "game_version": 0,
            "game_date": 0,
            "game_server": "Unknown",
            "placement": "N/A",
            "duels": {},
            "weapons": {},
        }

        stats = self.update_match_stats(stats, match)

        return stats

    def update_match_stats(self, stats: dict, match: dict) -> dict:
        players = match.get("players", [])
        player_stats = next(
            player
            for player in players
            if player["name"].lower() == self.name and player["tag"].lower() == self.tag
        )
        map_stats = match.get("metadata", {})
        team_stats = match.get("teams", [])
        team_color = next(
            team
            for team in team_stats
            if team["team_id"] == player_stats.get("team_id", "Unknown")
        )

        stats["total_kills"] = player_stats.get("stats", {}).get("kills", 0)
        stats["total_deaths"] = player_stats.get("stats", {}).get("deaths", 0)
        stats["total_assists"] = player_stats.get("stats", {}).get("assists", 0)

        stats["total_headshots"] = player_stats.get("stats", {}).get("headshots", 0)
        stats["total_bodyshots"] = player_stats.get("stats", {}).get("bodyshots", 0)
        stats["total_legshots"] = player_stats.get("stats", {}).get("legshots", 0)

        stats["total_score"] = player_stats.get("stats", {}).get("score", 0)
        stats["total_damage"] = (
            player_stats.get("stats", {}).get("damage", {}).get("dealt", 0)
        )

        stats["ability_casts"]["Ability1"] = player_stats.get("ability_casts", {}).get(
            "ability1", 0
        )
        stats["ability_casts"]["Ability2"] = player_stats.get("ability_casts", {}).get(
            "ability2", 0
        )
        stats["ability_casts"]["Grenade"] = player_stats.get("ability_casts", {}).get(
            "grenade", 0
        )
        stats["ability_casts"]["Ultimate"] = player_stats.get("ability_casts", {}).get(
            "ultimate", 0
        )

        stats["current_rank"] = player_stats.get("tier", {}).get("name", "Unranked")
        stats["account_level"] = player_stats.get("account_level", 0)
        stats["agent_played"] = player_stats.get("agent", {}).get("name", "Unknown")

        stats["map_played"] = map_stats.get("map", {}).get("name", "Unknown")
        stats["team"] = player_stats.get("team_id", "Unknown")
        stats["rounds_won"] = team_color.get("rounds", {}).get("won", 0)
        stats["rounds_lost"] = team_color.get("rounds", {}).get("lost", 0)

        stats["game_time"] = map_stats.get("game_length_in_ms", 0)
        stats["game_version"] = map_stats.get("game_version", "Unknown")
        stats["game_date"] = map_stats.get("started_at", "Unknown")
        stats["game_server"] = map_stats.get("cluster", "Unknown")

        players = match.get("players", [])
        total_rounds = stats["rounds_won"] + stats["rounds_lost"]

        def get_players_with_stats(team_players):
            return [
                (
                    player["name"],
                    player["tag"],
                    player["stats"]["score"],
                    player["stats"]["kills"],
                    player["stats"]["deaths"],
                    player["stats"]["assists"],
                    player["tier"]["name"],
                    player["agent"]["name"],
                )
                for player in players
            ]

        # Sort players by ACS
        players_with_stats_sorted = sorted(
            get_players_with_stats(players),
            key=lambda x: x[2] / total_rounds,
            reverse=True,
        )
        # Find the index of the player
        stats["placement"] = next(
            (
                i + 1
                for i, player in enumerate(players_with_stats_sorted)
                if player[0].lower() == self.name and player[1].lower() == self.tag
            ),
            None,
        )

        # Process round data
        round_data = match.get("rounds", [])
        earliest_kill_time = {}
        for round_number, rounds in enumerate(round_data, start=1):
            plant_events = rounds.get("plant", {})
            defuse_events = rounds.get("defuse", {})

            if plant_events:
                planted_by = plant_events.get("player", {})
                if planted_by and planted_by.get("name", "").lower() == self.name:
                    stats["bomb_plants"] += 1
            if defuse_events:
                defused_by = defuse_events.get("player", {})
                if defused_by and defused_by.get("name", "").lower() == self.name:

                    stats["bomb_defuses"] += 1

        # Check player stats for first bloods and first deaths
        for kill_event in match.get("kills", []):
            kill_time = kill_event.get("time_in_round_in_ms")
            killer = kill_event.get("killer", {})
            victim = kill_event.get("victim", {})

            killer_display_name = killer.get("name", "").lower()
            killer_display_tag = killer.get("tag", "").lower()
            victim_display_name = victim.get("name", "").lower()
            victim_display_tag = victim.get("tag", "").lower()
            weapon = kill_event.get("weapon", {}).get("name", "")
            round_number = kill_event.get("round")

            # Track the earliest kill time in the round
            if (
                round_number not in earliest_kill_time
                or kill_time < earliest_kill_time[round_number]["kill_time"]
            ):
                earliest_kill_time[round_number] = {
                    "kill_time": kill_time,
                    "killer_display_name": killer_display_name,
                    "killer_display_tag": killer_display_tag,
                    "victim_display_name": victim_display_name,
                    "victim_display_tag": victim_display_tag,
                }

            # Handle duels involving self (either as killer or victim)
            if killer_display_name == self.name and killer_display_tag == self.tag:
                duel_key = f"{victim_display_name}#{victim_display_tag}"
                stats["duels"].setdefault(duel_key, {"Kills": 0, "Deaths": 0})
                stats["duels"][duel_key]["Kills"] += 1

                # Track weapon usage
                stats["weapons"].setdefault(weapon, {"Kills": 0})
                stats["weapons"][weapon]["Kills"] += 1

            elif victim_display_name == self.name and victim_display_tag == self.tag:
                duel_key = f"{killer_display_name}#{killer_display_tag}"
                stats["duels"].setdefault(duel_key, {"Kills": 0, "Deaths": 0})
                stats["duels"][duel_key]["Deaths"] += 1

        # Count the first kills and deaths
        for round_info in earliest_kill_time.values():
            if (
                round_info["killer_display_name"] == self.name
                and round_info["killer_display_tag"] == self.tag
            ):
                stats["first_bloods"] += 1
            if (
                round_info["victim_display_name"] == self.name
                and round_info["victim_display_tag"] == self.tag
            ):
                stats["first_deaths"] += 1

        return stats

    def player_match_stats_embeds(self, stats: dict) -> discord.Embed:
        account_level = stats["account_level"]
        total_shots = (
            stats["total_headshots"]
            + stats["total_bodyshots"]
            + stats["total_legshots"]
        )
        rounds_won = stats["rounds_won"]
        rounds_lost = stats["rounds_lost"]
        total_rounds = rounds_won + rounds_lost
        score = f"{rounds_won} - {rounds_lost}"

        average_headshots = round(((stats["total_headshots"] / total_shots) * 100), 2)
        average_bodyshots = round(((stats["total_bodyshots"] / total_shots) * 100), 2)
        average_legshots = round(((stats["total_legshots"] / total_shots) * 100), 2)
        average_score = round(stats["total_score"] / total_rounds)
        average_damage = round((stats["total_damage"] / total_rounds), 2)

        average_ability1_casted = round(
            (stats["ability_casts"]["Ability1"] / total_rounds), 2
        )
        average_ability2_casted = round(
            (stats["ability_casts"]["Ability2"] / total_rounds), 2
        )
        average_grenade_casted = round(
            (stats["ability_casts"]["Grenade"] / total_rounds), 2
        )
        average_ultimate_casted = round(
            (stats["ability_casts"]["Ultimate"] / total_rounds), 2
        )

        embed = discord.Embed(
            title=f"{self.name}#{self.tag}'s stats",
            description=f"Level {account_level}",
        )
        embed.add_field(name="Current Rank", value=stats["current_rank"], inline=True)
        embed.add_field(name="Current Map", value=stats["map_played"], inline=True)
        embed.add_field(name="Current Agent", value=stats["agent_played"], inline=True)
        embed.add_field(name="Kills", value=stats["total_kills"], inline=True)
        embed.add_field(name="Deaths", value=stats["total_deaths"], inline=True)
        embed.add_field(name="Assists", value=stats["total_assists"], inline=True)
        embed.add_field(name="Headshots", value=f"{average_headshots}%", inline=True)
        embed.add_field(name="Bodyshots", value=f"{average_bodyshots}%", inline=True)
        embed.add_field(name="Legshots", value=f"{average_legshots}%", inline=True)
        embed.add_field(name="ACS", value=f"{average_score}", inline=True)
        embed.add_field(name="ADR", value=f"{average_damage}", inline=True)
        embed.add_field(name="Score", value=score, inline=True)

        agent_abilities = self.get_agent_abilities()
        agent_stats = next(
            agent
            for agent in agent_abilities
            if agent["displayName"] == stats["agent_played"]
        )
        agent_icon = agent_stats.get("displayIcon")

        maps = self.get_maps()
        map_stats = next(
            map_details
            for map_details in maps
            if map_details["displayName"] == stats["map_played"]
        )
        map_splash = map_stats.get("splash", "N/A")
        # Create a dictionary to map ability slots to their display names
        ability_display_names = {}
        for ability in agent_stats["abilities"]:
            ability_display_names[ability["slot"]] = ability.get("displayName")

        # Retrieve the display names
        ability1_display_name = ability_display_names.get("Ability1")
        ability2_display_name = ability_display_names.get("Ability2")
        grenade_display_name = ability_display_names.get("Grenade")
        ultimate_display_name = ability_display_names.get("Ultimate")

        embed.add_field(
            name=ability1_display_name,
            value=f"{average_ability1_casted} casts per round",
            inline=True,
        )
        embed.add_field(
            name=grenade_display_name,
            value=f"{average_grenade_casted} casts per round",
            inline=True,
        )
        embed.add_field(
            name=ability2_display_name,
            value=f"{average_ability2_casted} casts per round",
            inline=True,
        )
        embed.add_field(
            name=ultimate_display_name,
            value=f"{average_ultimate_casted} casts per round",
            inline=False,
        )

        embed.add_field(name="First Bloods", value=stats["first_bloods"], inline=True)
        embed.add_field(name="First Deaths", value=stats["first_deaths"], inline=True)
        embed.add_field(name="", value="\u200b", inline=True)
        embed.add_field(name="Bomb Plants", value=stats["bomb_plants"], inline=True)
        embed.add_field(name="Bomb Defuses", value=stats["bomb_defuses"], inline=True)
        embed.add_field(name="", value="\u200b", inline=True)
        embed.add_field(name="Placement", value=f'{stats["placement"]}/10', inline=True)
        embed.set_thumbnail(url=agent_icon)
        embed.set_image(url=map_splash)

        time_in_ms = stats["game_time"]

        # Convert milliseconds to seconds
        time_in_seconds = time_in_ms / 1000

        # Convert seconds to hours, minutes, and seconds
        hours = int(time_in_seconds // 3600)
        remaining_seconds = time_in_seconds % 3600
        minutes = int(remaining_seconds // 60)
        seconds = round(remaining_seconds % 60)

        time = 0
        # Print the result
        if hours > 0:
            time = f"Game Length: {hours}:{minutes:02d}:{seconds:02d}"
        else:
            time = f"Game Length: {minutes:02d}:{seconds:02d}"

        input_format = ""
        date_obj = None
        try:
            input_format = "%Y-%m-%dT%H:%M:%S.%fZ"
            date_obj = datetime.strptime(stats["game_date"], input_format)
        except ValueError:
            input_format = "%Y-%m-%dT%H:%M:%S%z"
            date_obj = datetime.strptime(stats["game_date"], input_format)

        # Convert the datetime object to the desired format
        output_format = "%A, %B %d, %Y %I:%M %p"
        formatted_date = date_obj.strftime(output_format)

        last_match_date = datetime.strptime(formatted_date, "%A, %B %d, %Y %I:%M %p")
        adjusted_date = last_match_date - timedelta(hours=4)
        result_date_str = adjusted_date.strftime("%A, %B %d, %Y %I:%M %p")
        result_date = datetime.strptime(result_date_str, "%A, %B %d, %Y %I:%M %p")

        game_version = stats["game_version"]
        game_server = stats["game_server"]
        embed.set_footer(text=f"{time} - {game_server} - {game_version}")
        embed.timestamp = result_date

        embed1 = discord.Embed(
            title=f"{self.name}#{self.tag}'s Duels",
            description=f"Level {account_level}",
        )
        for key, value in sorted(
            stats["duels"].items(),
            key=lambda item: item[1]["Kills"],
            reverse=True,
        ):
            embed1.add_field(name="Player", value=key, inline=True)
            embed1.add_field(name="Kills", value=value.get("Kills", 0), inline=True)
            embed1.add_field(name="Deaths", value=value.get("Deaths", 0), inline=True)

        embed2 = discord.Embed(
            title=f"{self.name}#{self.tag}'s Weapons",
            description=f"Level {account_level}",
        )
        for key, value in sorted(
            stats["weapons"].items(),
            key=lambda item: item[1]["Kills"],
            reverse=True,
        ):
            embed2.add_field(name="Weapon", value=key, inline=True)
            embed2.add_field(name="Kills", value=value.get("Kills", 0), inline=True)
            embed2.add_field(name="", value="\u200b", inline=True)

        return [embed, embed1, embed2]

    def get_team_stats(self, match_details, name, tag):
        players = match_details.get("players")
        total_rounds = match_details.get("teams")[0].get("rounds", {}).get(
            "won", 0
        ) + match_details.get("teams")[0].get("rounds", {}).get("lost", 0)
        map_name = match_details.get("metadata").get("map").get("name")
        team = next(
            player
            for player in players
            if player.get("name").lower() == name.lower()
            and player.get("tag").lower() == tag.lower()
        )
        name = f"{name}#{tag}".lower()
        team_color = team.get("team_id")
        red_players = [player for player in players if player.get("team_id") == "Red"]
        blue_players = [player for player in players if player.get("team_id") == "Blue"]

        def get_players_with_stats(team_players):
            return [
                (
                    player["name"],
                    player["tag"],
                    player["stats"]["score"],
                    player["stats"]["kills"],
                    player["stats"]["deaths"],
                    player["stats"]["assists"],
                    player["tier"]["name"],
                    player["stats"]["damage"]["dealt"],
                    player["agent"]["name"],
                )
                for player in team_players
            ]

        # Sort players by ACS
        red_players_with_stats_sorted = sorted(
            get_players_with_stats(red_players),
            key=lambda x: x[2] / total_rounds,
            reverse=True,
        )
        blue_players_with_stats_sorted = sorted(
            get_players_with_stats(blue_players),
            key=lambda x: x[2] / total_rounds,
            reverse=True,
        )

        # Create embeds
        embed1_title = (
            f"{name}'s team stats" if team_color == "Red" else "Enemy team stats"
        )
        embed2_title = (
            f"{name}'s team stats" if team_color == "Blue" else "Enemy team stats"
        )

        team = next(
            (
                team
                for team in match_details.get("teams")
                if team["team_id"] == team_color
            ),
            None,
        )
        rounds_won = team.get("rounds").get("won")
        rounds_lost = team.get("rounds").get("lost")

        embed1 = discord.Embed(title=embed1_title)
        embed2 = discord.Embed(title=embed2_title)

        # Example player data (fill this in with real data)
        team_a_players = [
            ["Name", "Rank", "ACS", "Kills", "Deaths", "Assists", "ADR", "Agent"],
        ]
        team_b_players = [
            ["Name", "Rank", "ACS", "Kills", "Deaths", "Assists", "ADR", "Agent"],
        ]

        for (
            player_name,
            tag,
            score,
            kills,
            deaths,
            assists,
            rank,
            damage,
            agent,
        ) in red_players_with_stats_sorted:
            embed1.add_field(
                name="Player",
                value=f"{player_name}#{tag} - {rank} - {agent}",
                inline=True,
            )
            embed1.add_field(name="ACS", value=round(score / total_rounds), inline=True)
            embed1.add_field(
                name="KDA", value=f"{kills}/{deaths}/{assists}", inline=True
            )
            team_a_players.append(
                [
                    f"{player_name}#{tag}",
                    f"{rank}",
                    f"{round(score / total_rounds)}",
                    f"{kills}",
                    f"{deaths}",
                    f"{assists}",
                    f"{round(damage/total_rounds, 2)}",
                    f"{agent}",
                ]
            )

        for (
            player_name,
            tag,
            score,
            kills,
            deaths,
            assists,
            rank,
            damage,
            agent,
        ) in blue_players_with_stats_sorted:
            embed2.add_field(
                name="Player",
                value=f"{player_name}#{tag} - {rank} - {agent}",
                inline=True,
            )
            embed2.add_field(name="ACS", value=round(score / total_rounds), inline=True)
            embed2.add_field(
                name="KDA", value=f"{kills}/{deaths}/{assists}", inline=True
            )
            team_b_players.append(
                [
                    f"{player_name}#{tag}",
                    f"{rank}",
                    f"{round(score / total_rounds)}",
                    f"{kills}",
                    f"{deaths}",
                    f"{assists}",
                    f"{round(damage/total_rounds, 2)}",
                    f"{agent}",
                ]
            )
        # Create a new blank image with a white background
        width, height = 1400, 600
        image = Image.new("RGB", (width, height), "white")
        draw = ImageDraw.Draw(image)

        # Define fonts
        font_path = (
            "./public/fonts/Roboto-Bold.ttf"  # Replace with the path to your font file
        )
        font_large = ImageFont.truetype(font_path, 20)
        font_small = ImageFont.truetype(font_path, 16)

        # Define some colors
        team_a_color = (24, 100, 79)  # Dark Green
        team_b_color = (91, 22, 22)  # Dark Red
        text_color_white = (255, 255, 255)

        draw.rectangle([(0, 0), (width, 50)], fill=team_a_color)
        draw.text(
            (10, 10),
            f"{embed1.title}",
            font=font_large,
            fill=text_color_white,
        )

        draw.text(
            (310, 10),
            f"Rounds: {rounds_won if name in embed1.title else rounds_lost}",
            font=font_large,
            fill=text_color_white,
        )
        draw.text(
            (560, 10),
            f"Map: {map_name}",
            font=font_large,
            fill=text_color_white,
        )

        draw.rectangle([(0, 300), (width, 350)], fill=team_b_color)
        draw.text(
            (10, 310),
            f"{embed2.title}",
            font=font_large,
            fill=text_color_white,
        )

        draw.text(
            (310, 310),
            f"Rounds: {rounds_won if name in embed2.title else rounds_lost}",
            font=font_large,
            fill=text_color_white,
        )

        # Function to draw player data rows
        def draw_player_row(y_offset, player_data, team_color):
            x_offset = 10
            draw.rectangle([(0, y_offset), (width, y_offset + 60)], fill=team_color)
            draw.line(
                [(0, y_offset + 10), (width, y_offset + 10)], fill=(0, 0, 0), width=2
            )
            for index, item in enumerate(player_data):
                draw.text(
                    (x_offset, y_offset + 20),
                    str(item),
                    font=font_small,
                    fill=text_color_white,
                )
                # Increment x_offset only after the first items
                if index < 1:
                    x_offset += 300
                else:
                    x_offset += 125

        # Draw team A rows
        y_offset = 40
        for player in team_a_players:
            draw_player_row(y_offset, player, team_a_color)
            y_offset += 40

        # Draw team B rows
        y_offset = 340
        for player in team_b_players:
            draw_player_row(y_offset, player, team_b_color)
            y_offset += 40

        # Specify the image path to save the file
        image_path = "./public/output_image.png"

        # Save the image
        image.save(image_path)
        return [embed1, embed2]


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Valorant(bot))
    print("Valorant is Loaded")
