from datetime import datetime, timedelta
from discord import ButtonStyle, app_commands
from discord.ext import commands
from discord.ui import Button, View
from dotenv import load_dotenv
from typing import Literal, Union, NamedTuple, Optional, List
from urllib.parse import quote_plus
import discord
import os
import asyncio
import requests
from discord.app_commands import Choice
import uuid

load_dotenv()
list_of_guilds = os.getenv("GUILDS").split(",")
MY_GUILDS = [discord.Object(id=int(guild)) for guild in list_of_guilds]
VAL_KEY = os.getenv("VAL")


class Valorant(commands.Cog):
    """Valorant stats """
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.queue_manager = QueueManager()

    @app_commands.command(name="valorantlast")
    @app_commands.describe(
        name="Player's username",
        tag="Player's Tag",
        region="Players'Region",
    )
    async def valorant_last_game(self, interaction: discord.Interaction, name: str, tag: str, region: Optional[str] = "NA"):
        """Returns the stats of a valorant player's last game"""
    
        # Define the URL of the API endpoint
        account_api = f"https://api.henrikdev.xyz/valorant/v1/account/{name}/{tag}?api_key={VAL_KEY}"
        # account_matches = f"https://api.henrikdev.xyz/valorant/v1/lifetime/matches/{region}/{name}/{tag}?mode=competitive&?api_key={VAL_KEY}"
        account_matches = f"https://api.henrikdev.xyz/valorant/v3/matches/{region}/{name}/{tag}?api_key={VAL_KEY}"
        await interaction.response.defer() 
        # Make a GET request to the API
        response = requests.get(account_api)
        matches = requests.get(account_matches)

        # Check if the request was successful (status code 200)
        if response.status_code == 200 and matches.status_code == 200:
            
            data = response.json()
            last_match_data = matches.json()

            # Find the last competitive match
            last_comp_match = next((comp for comp in last_match_data["data"] if comp["metadata"]["mode"].lower() == "competitive"), None)
            last_comp_match = next((match for match in last_match_data.get("data", []) if match.get("metadata", {}).get("mode", "").lower() == "competitive"), None)
            if not last_comp_match:
                await interaction.followup.send("Error: No competitive match found, try again. Can happen if other modes were played.")
                return

            account_level = data.get("data", {}).get("account_level", "Unknown")
            card_data = data.get("data", {}).get("card", {})
            small_player_card = card_data.get("small", "URL not available")
            wide_player_card = card_data.get("wide", "URL not available")
            full_name = f"{name}#{tag}".lower()

            # Find the stats for the specified player in the last competitive match
            last_match_stats = next((player for player in last_comp_match["players"]["all_players"] if player["name"].lower() == name.lower()), None)
            
            if not last_match_stats:
                await interaction.followup.send("Error: Player stats not found in the last competitive match, try again.")
                return

            # Extract necessary stats
            stats = last_match_stats.get("stats", {})
            last_match_kills = stats.get("kills", 0)
            last_match_deaths = stats.get("deaths", 0)
            last_match_assists = stats.get("assists", 0)
            last_match_map = last_comp_match["metadata"].get("map", "Unknown")
            last_match_date_str = last_comp_match["metadata"].get("game_start_patched", "")

            try:
                last_match_date = datetime.strptime(last_match_date_str, "%A, %B %d, %Y %I:%M %p")
                adjusted_date = last_match_date - timedelta(hours=6)
                result_date_str = adjusted_date.strftime("%A, %B %d, %Y %I:%M %p")
                result_date = datetime.strptime(result_date_str, "%A, %B %d, %Y %I:%M %p")
            except ValueError:
                await interaction.followup.send("Error: Invalid date format for the last match date.")
                return

            last_match_agent = last_match_stats.get("character", "Unknown")
            last_match_combat_score = stats.get("score", 0)
            last_match_damage = last_match_stats.get("damage_made", 0)
            last_match_red = last_comp_match["teams"]["red"].get("rounds_won", 0)
            last_match_blue = last_comp_match["teams"]["blue"].get("rounds_won", 0)
            last_match_total_rounds = last_match_red + last_match_blue
            last_match_team = last_match_stats.get("team", "Unknown")
            last_match_total_shots = stats.get("headshots", 0) + stats.get("bodyshots", 0) + stats.get("legshots", 0)
            last_match_headshots = stats.get("headshots", 0)
            last_match_ability_casts = last_match_stats.get("ability_casts", {})
            last_match_ability_c = last_match_ability_casts.get("c_cast", 0)
            last_match_ability_q = last_match_ability_casts.get("q_cast", 0)
            last_match_ability_e = last_match_ability_casts.get("e_cast", 0)
            last_match_ability_x = last_match_ability_casts.get("x_cast", 0)
            last_match_server = last_comp_match["metadata"].get("cluster", "Unknown")
            last_match_game_version = last_comp_match["metadata"].get("game_version", "Unknown")
            last_match_game_length = last_comp_match["metadata"].get("game_length", 0)
            # Convert game length to minutes and seconds
            last_match_minutes, last_match_seconds = divmod(last_match_game_length, 60)

            # Process round data
            round_data = last_comp_match["rounds"]
            earliest_kill_time = {}
            plants = 0
            defuses = 0
            first_kill = 0
            first_death = 0

            for round_number, rounds in enumerate(round_data, start=1):
                plant_events = rounds.get("plant_events", {})
                defuse_events = rounds.get("defuse_events", {})

                planted_by = plant_events.get("planted_by", {})
                defused_by = defuse_events.get("defused_by", {})

                # Check plant events
                if planted_by and planted_by.get("display_name", "").lower() == full_name:
                    plants += 1

                # Check defuse events
                if defused_by and defused_by.get("display_name", "").lower() == full_name:
                    defuses += 1

                # Check player stats for kill events
                for player in rounds.get("player_stats", []):
                    for kill_event in player.get('kill_events', []):
                        kill_time = kill_event.get('kill_time_in_round')
                        killer_display_name = kill_event.get('killer_display_name', '').lower()
                        victim_display_name = kill_event.get('victim_display_name', '').lower()

                        if round_number not in earliest_kill_time or kill_time < earliest_kill_time[round_number]['kill_time']:
                            earliest_kill_time[round_number] = {
                                'kill_time': kill_time,
                                'killer_display_name': killer_display_name,
                                'victim_display_name': victim_display_name
                            }

            # Count the first kills and deaths
            for round_info in earliest_kill_time.values():
                if round_info['killer_display_name'] == full_name:
                    first_kill += 1
                if round_info['victim_display_name'] == full_name:
                    first_death += 1

            # Create and send the embed
            embed = discord.Embed(
                title=f"{name}'s Last Game Stats",
                description=f"Level {account_level}"
            )
            embed.add_field(name="Agent", value=last_match_agent, inline=True)
            embed.add_field(name="Map", value=last_match_map, inline=True)
            embed.add_field(name="\u200B", value="\u200B")
            embed.add_field(name="Kills", value=last_match_kills, inline=True)
            embed.add_field(name="Deaths", value=last_match_deaths, inline=True)
            embed.add_field(name="Assists", value=last_match_assists, inline=True)
            embed.add_field(name="Headshot %", value=round((last_match_headshots / last_match_total_shots) * 100), inline=True)
            embed.add_field(name="First Kills", value=first_kill, inline=True)
            embed.add_field(name="First Deaths", value=first_death, inline=True)
            embed.add_field(name="AVG C Ability Casted", value=round(last_match_ability_c / last_match_total_rounds, 1), inline=True)
            embed.add_field(name="AVG Q Ability Casted", value=round(last_match_ability_q / last_match_total_rounds, 1), inline=True)
            embed.add_field(name="AVG E Ability Casted", value=round(last_match_ability_e / last_match_total_rounds, 1), inline=True)
            embed.add_field(name="AVG X Ability Casted", value=round(last_match_ability_x / last_match_total_rounds, 1), inline=True)
            embed.add_field(name="Plants", value=plants, inline=True)
            embed.add_field(name="Defuses", value=defuses, inline=True)
            embed.add_field(name="ACS", value=round(last_match_combat_score / last_match_total_rounds), inline=True)
            embed.add_field(name="ADR", value=round(last_match_damage / last_match_total_rounds), inline=True)
            embed.add_field(name="Score", value=f"{last_match_blue} - {last_match_red}" if last_match_team == "Blue" else f"{last_match_red} - {last_match_blue}", inline=True)
            embed.add_field(name="Game Length", value=f"{last_match_minutes}:{last_match_seconds:02d}", inline=True)
            embed.set_footer(text=f"{last_match_server} - {last_match_game_version}")
            embed.set_image(url=wide_player_card)
            embed.set_thumbnail(url=small_player_card)
            embed.timestamp = result_date

            await interaction.followup.send(embed=embed)
            
        else:
            # Handle errors
            print(f"Failed to retrieve data: {response.status_code}")
            await interaction.followup.send("User does not exist or API Error Please try again")
            
            
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
        time="How long to look back for MMR history"
    )
    async def valorant_mmr_history(
        self, interaction: discord.Interaction, 
        name: str, tag: str, 
        time: Optional[int] = 24, 
        region: Optional[str] = "NA"
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
            current_rank = current_mmr_data.get("currenttierpatched", "Unknown")
            current_rr = current_mmr_data.get("elo", 0) % 100
            current_rank_picture = current_mmr_data.get("images", {}).get("small", "unknown Url")
            cutoff_date = datetime.utcnow() - timedelta(hours=time)
            starting_rank = "Unknown"
            starting_rr = 0

            for i, game_data in enumerate(mmr_data):
                game_date_str = game_data.get("date", "")
                game_date = datetime.strptime(game_date_str, "%A, %B %d, %Y %I:%M %p")
                # Check if game date is less than current date and break the loop if it is
                if game_date < cutoff_date:
                    starting_rank = game_data.get("currenttierpatched", "Unknown")
                    starting_rr = game_data.get("elo", 0) % 100
                    print("Breaking loop, game date is less than current date")
                    break
                game_mmr_change = game_data.get("mmr_change_to_last_game", 0)
                if game_mmr_change > 0:
                    wins += 1
                else:
                    loses += 1
                mmr += game_mmr_change
            embed = discord.Embed(
                title=f"{name}'s MMR history", description=f"MMR change in the last {time} hours")
            embed.add_field(name="Games Won", value=wins, inline=True)
            embed.add_field(name="Games Lost", value=loses, inline=True)
            embed.add_field(name="\u200B", value="\u200B")
            embed.add_field(name="Starting Rank", value=starting_rank, inline=True)
            embed.add_field(name="Starting RR", value=f"{starting_rr}/100", inline=True)
            embed.add_field(name="\u200B", value="\u200B")
            embed.add_field(name="Current Rank", value=current_rank, inline=True)
            embed.add_field(name="Current RR", value=f"{current_rr}/100", inline=True)
            embed.add_field(name="\u200B", value="\u200B")
            mmr_display = f"+{mmr}" if mmr > 0 else f"{mmr}"
            embed.add_field(name="RR Change", value=mmr_display, inline=False)
            embed.timestamp = datetime.now()
            embed.set_thumbnail (url = current_rank_picture)


            await interaction.followup.send(embed=embed)
        else:
            # Handle error if the response was not successful
            await interaction.followup.send("Failed to fetch MMR history. Please try again later.")
    
        
    @app_commands.command(name="valorantstats")
    @app_commands.describe(
        name="Player's username",
        tag="Player's Tag",
        region="Players'Region",
    )
    async def valorant_stats(self, interaction: discord.Interaction, name: str, tag: str, region: Optional[str] = "NA"):
        """Returns the stats of a valorant player's"""
        await interaction.response.defer()
        api_url = f"https://api.henrikdev.xyz/valorant/v1/lifetime/matches/na/{name}/{tag}?mode=competitive&api_key={VAL_KEY}"
        api_url2 = f"https://api.henrikdev.xyz/valorant/v1/mmr/na/{name}/{tag}?api_key={VAL_KEY}"
        api_url3 = f"https://api.henrikdev.xyz/valorant/v1/account/{name}/{tag}?api_key={VAL_KEY}"
        api_url4 = f"https://api.henrikdev.xyz/valorant/v2/mmr/na/{name}/{tag}?api_key={VAL_KEY}"
        response = requests.get(api_url)
        response2 = requests.get(api_url2)
        response3 = requests.get(api_url3)
        response4 = requests.get(api_url4)
        print(response)
        print(response2)
        print(response3)
        print(response4)
        
        
        if response.status_code == 200 and response2.status_code == 200 and response3.status_code == 200 and response4.status_code == 200:
            match_history = response.json()
            mmr = response2.json()
            account = response3.json()
            mmr_history = response4.json()
            kills = 0
            deaths = 0
            assists = 0
            total_shots = 0
            headshots = 0
            bodyshots = 0
            legshots = 0
            wins = 0
            loses = 0
            acs = 0
            adr = 0
            current_act = match_history["data"][0]["meta"]["season"]["short"]
            total_games = 0
            total_rounds = 0

            for games in match_history["data"]:
                if games["meta"]["season"]["short"] != current_act:
                    continue
                team = games["stats"]["team"]
                kills += games["stats"]["kills"]
                deaths += games["stats"]["deaths"]
                assists += games["stats"]["assists"]
                total_shots += sum(games["stats"]["shots"].values())
                headshots += games["stats"]["shots"]["head"]
                bodyshots += games["stats"]["shots"]["body"]
                legshots += games["stats"]["shots"]["leg"]
                
                if team == "Blue" and games["teams"]["blue"] > games["teams"]["red"]:
                    wins +=1
                elif team == "Blue" and games["teams"]["blue"] < games["teams"]["red"]:
                    loses += 1
                elif team == "Red" and games["teams"]["blue"] < games["teams"]["red"]:
                    wins +=1
                elif team == "Red" and games["teams"]["blue"] > games["teams"]["red"]:
                    loses +=1
                
                acs += games["stats"]["score"]
                adr += games["stats"]["damage"]["made"]
                total_games+=1
                total_rounds += games["teams"]["blue"] + games["teams"]["red"]
            embed = discord.Embed(
            title=f"{name}'s stats", description=f"Taken from {total_games} games - {current_act}")
            elo = mmr['data']['elo']
            # Use a default value of 0 if elo is None
            elo_rr = elo % 100 if elo is not None else 0
            embed.set_author(name=f"{mmr['data']['currenttierpatched']} - {elo_rr%100}RR", icon_url=account["data"]["card"]["small"], url=account["data"]["card"]["large"])
            embed.add_field(name="Highest Rank Ever", value=f'{mmr_history["data"]["highest_rank"]["patched_tier"]} - {mmr_history["data"]["highest_rank"]["season"]}', inline=True)
            # Access the current act data
            data = mmr_history.get("data", {})
            by_season = data.get("by_season", {})
            current_act_data = by_season.get("current_act", {})
            act_rank_wins = current_act_data.get("act_rank_wins", [])
            if act_rank_wins:
                highest_act_rank = act_rank_wins[0].get("patched_tier", "N/A")
            else:
                highest_act_rank = "N/A"
            embed.add_field(name="Highest Rank This Act", value=f'{highest_act_rank}', inline=True)
        
            embed.add_field(name="Games Won", value=wins, inline=True)
            embed.add_field(name="Games Lost", value=loses, inline=True)
            embed.add_field(name="Win Rate", value=round(wins/total_games, 2), inline=True)
            
            embed.add_field(name="Average Kills", value=round(kills/total_games), inline=True)
            embed.add_field(name="Average Deaths", value=round(deaths/total_games), inline=True)
            embed.add_field(name="Average Assists", value=round(assists/total_games), inline=True)
        
            embed.add_field(name="Average HS%", value=round((headshots/total_shots)*100, 1), inline=True)
            embed.add_field(name="Average Bodyshot%", value=round((bodyshots/total_shots)*100, 1), inline=True)
            embed.add_field(name="Average Legshot%", value=round((legshots/total_shots)*100, 1), inline=True)
            
            embed.add_field(name="Average ACS", value=round(acs/total_rounds), inline=True)
            embed.add_field(name="Average ADR", value=round(adr/total_rounds, 1), inline=True)
            embed.set_image(url=account["data"]["card"]["wide"])
            embed.timestamp = datetime.now()
            
                
            await interaction.followup.send(embed=embed)
        else:
            # Handle errors
            print(f"Failed to retrieve data: {response.status_code}")
            await interaction.followup.send("User does not exist or API Error Please try again")
    
    @app_commands.command(name="valorantteam")
    @app_commands.describe(
        name="Player's username",
        tag="Player's Tag",
        region="Players'Region",
    )
    async def valorant_team(self, interaction: discord.Interaction, name: str, tag: str, region: Optional[str] = "NA"):
        """Returns the stats of last games team"""
        await interaction.response.defer()
        api_url = f"https://api.henrikdev.xyz/valorant/v3/matches/na/{name}/{tag}?api_key={VAL_KEY}"
        api_url2 = "https://valorant-api.com/v1/maps"
        response = requests.get(api_url)
        response2 = requests.get(api_url2)
        
        if response.status_code == 200:
            def get_players_with_stats(team_players):
                return [(player["name"], player["stats"]["score"], player["stats"]["kills"], player["stats"]["deaths"], player["stats"]["assists"], player["currenttier_patched"], player["character"]) for player in team_players]
            def get_map_splash_url(maps_data, map_name):
                for map_data in maps_data["data"]:
                    if map_data.get("displayName") == map_name:
                        return map_data.get("splash")
                return None

            data = response.json()
            maps = response2.json()
            # Extract player data
            red_players = data["data"][0]["players"]["red"]
            blue_players = data["data"][0]["players"]["blue"]

            # Get all players
            all_players = red_players + blue_players

            # Determine user's team
            team = ""
            for player in all_players:
                if player["name"].lower() == name:
                    team = player['team'].lower()
                    break

            # Get team stats
            team_won = data["data"][0]["teams"][team]["has_won"]
            rounds_won = data["data"][0]["teams"][team]["rounds_won"]
            rounds_lost = data["data"][0]["teams"][team]["rounds_lost"]
            total_rounds = rounds_won + rounds_lost
            splash_url = get_map_splash_url(maps, data["data"][0]["metadata"]["map"])
            game_version = data["data"][0]["metadata"]["game_version"]
            game_length_min, game_length_sec = divmod(data["data"][0]["metadata"]["game_length"], 60)
            game_server = data["data"][0]["metadata"]["cluster"]

            # Sort players by ACS
            red_players_with_stats_sorted = sorted(get_players_with_stats(red_players), key=lambda x: x[1] / total_rounds, reverse=True)
            blue_players_with_stats_sorted = sorted(get_players_with_stats(blue_players), key=lambda x: x[1] / total_rounds, reverse=True)
            
            # Create embeds
            embed1_title = f"{name}'s team stats" if team == "red" else "Enemy team stats"
            embed2_title = f"{name}'s team stats" if team == "blue" else "Enemy team stats"
            embed1_description = f"Rounds: {rounds_won}-{rounds_lost}" if team == "red" else f"Rounds {rounds_lost}-{rounds_won}"
            embed2_description = f"Rounds {rounds_won}-{rounds_lost}" if team == "blue" else f"Rounds {rounds_lost}-{rounds_won}"
            
            embed1 = discord.Embed(title=embed1_title, description = embed1_description)
            for player_name, score, kills, deaths, assists, rank, agent in red_players_with_stats_sorted:
                embed1.add_field(name="Player", value=f"{player_name} - {rank} - {agent}", inline=True)
                embed1.add_field(name="ACS", value=round(score / total_rounds), inline=True)
                embed1.add_field(name="KDA", value=f"{kills}/{deaths}/{assists}", inline=True)

            embed2 = discord.Embed(title=embed2_title, description = embed2_description)
            for player_name, score, kills, deaths, assists, rank, agent in blue_players_with_stats_sorted:
                embed2.add_field(name="Player", value=f"{player_name} - {rank} - {agent}", inline=True)
                embed2.add_field(name="ACS", value=round(score / total_rounds), inline=True)
                embed2.add_field(name="KDA", value=f"{kills}/{deaths}/{assists}", inline=True)

            embed1.set_image(url=splash_url)
            embed1.set_footer(text=f"{game_length_min}:{game_length_sec:02d} - {game_server} - {game_version} ")
            embed2.set_image(url=splash_url)
            embed2.set_footer(text=f"{game_length_min}:{game_length_sec:02d} - {game_server} - {game_version} ")
            # Send embeds
            await interaction.followup.send(embeds=[embed1, embed2])
        else:
            # Handle errors
            print(f"Failed to retrieve data: {response.status_code}")
            await interaction.followup.send("User does not exist or API Error Please try again")


    @app_commands.command(name="valoranttracker")
    @app_commands.describe(
        name="Player's username",
        tag="Player's Tag",
    )
    async def valorant_tracker(self, interaction: discord.Interaction, name: str, tag: str):
        """Returns the stats of a valorant player's using tracker.gg api"""
        await interaction.response.defer()
        api_url = f"https://api.tracker.gg/api/v2/valorant/standard/matches/riot/{name.replace(' ', '%20')}%23{tag}"
        
        headers = {'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36',
                   'Cookie': 'cf_clearance=ARR45y2wBdWY.s7EwjJ_hLgcIh4zBr9eIACnu3xsJm0-1715057869-1.0.1.1-9J4.z0KHMC8iwTZHxEErmc5nbQYt5j1idKLMISLbI.PTynhA1_aM8DgJs6z08DqYwCYf6340ttcsepZxpVmJmQ; X-Mapping-Server=s22; cf_clearance=eDLkbZ1HnlVuCeBcNtuVJX21SNyOmilcFRCcztE.17c-1716841883-1.0.1.1-sqgpLOJD3Li048S9hDPYfdBTAKFCzy_r4j.Jl3b9aD.I7O2ML5Ja5unToc4NFMVnQhhWDoSkbqhyCKA2JJ2B7g; __cflb=02DiuFQAkRrzD1P1mdkJhfdTc9AmTWwYj1vZQQJFRZEKW; session_id=d95a6756-e253-4374-a768-ed8b3ceaf700; __cf_bm=iqiod4DFjbtTDk.0ga2cNam5uW1ND_oC7CWkQuIusEc-1716845622-1.0.1.1-I3eKaaqwDdi9GmWZt94uAlQ7fyy.prRwLiqRAe6ZiC9sCN.5kmK7.34O1tvLR1EXeW4n5lRqU8eF3Mm_5rCFzHyygREoTIRT7akS9oF2_yw',
                   'Sec-Ch-Ua': 'Google Chrome";v="125", "Chromium";v="125", "Not.A/Brand";v="24'}
        response = requests.get(api_url, headers=headers)
        if response.status_code == 200:
            data = response.json()

            # Process the data to create select options
            # Store matches data
            matches = data['data']['matches']
            match_details = {match['attributes']['id']: match for match in matches}

            # Process the data to create select options
            options = []
            for match in matches:
                map_name = match.get('metadata', {}).get('mapName', 'Unknown Map')
                result = match.get('metadata', {}).get('result', 'Unknown Result')
                time = match.get('metadata', {}).get('timestamp')
                if time:
                    dt = datetime.strptime(time, '%Y-%m-%dT%H:%M:%S.%f%z')
                    dt_adjusted = dt - timedelta(hours=4)  # Adjusting time zone
                    formatted_time = dt_adjusted.strftime('%Y-%m-%d %I:%M %p')
                else:
                    formatted_time = 'Unknown Time'
                    
                label = f"{map_name} - {result} - {formatted_time}"
                options.append(discord.SelectOption(label=label, value=match['attributes']['id']))
                
            # Create the select menu
            select = discord.ui.Select(placeholder="Choose a match", options=options)

            # Define a callback for the select menu
            async def callback(interaction: discord.Interaction):
                selected_match_id = select.values[0]
                match = match_details.get(selected_match_id)

                if match:
                # Extract player stats
                    player_stats = next((player for player in match.get('segments', []) if player.get('metadata', {}).get('platformUserHandle', '').lower() == f"{name}#{tag.lower()}"), None)

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
                        agent = player_stats.get('metadata', {}).get('agentName', "Unknown Agent")
                        agent_url = player_stats.get('metadata', {}).get('agentImageUrl', "Unknown Url")
                        map_name = match.get('metadata', {}).get('mapName', 'Unknown Map')
                        embed = discord.Embed(title=f"{name}' stats on {map_name}", description=f"Agent: {agent}")
                        embed.set_thumbnail(url = agent_url)

                        for key, label in stats_mapping.items():
                            if key == "rank":
                                value = player_stats.get('stats', {}).get(key, {}).get('metadata', {}).get('tierName', "Unranked")
                            else:
                                value = player_stats.get('stats', {}).get(key, {}).get('displayValue', 'Unknown')
                            if key == "placement":
                                embed.add_field(name=label, value=f"{value}/10", inline=True)
                            elif key == "trnPerformanceScore":
                                embed.add_field(name=label, value=f"{value}/1000", inline=True)
                            else:
                                embed.add_field(name=label, value=value, inline=True)

                        splash_url = match.get("metadata", {}).get("mapImageUrl")
                        if splash_url:
                            embed.set_image(url=splash_url)

                        playtime = player_stats.get('stats', {}).get('playtime', {}).get('displayValue', 'Unknown')
                        embed.set_footer(text=f"Match time: {playtime}")

                        await interaction.response.edit_message(embed=embed)
                    else:
                        await interaction.followup.send("Player stats not found for the selected match.")
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
            
    @app_commands.command(name="valorantqueue")
    @app_commands.describe(
        size="Number of players before queue is full",
    )
    async def valorant_queue(self, interaction: discord.Interaction, size: Optional[int] = 5, queue_id: Optional[str] = None):
        
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
                response = f"\n\nThe queue is currently empty."
            if current_queue is None:
                await interaction.response.send_message("This queue ID does not exist", ephemeral=True)
                return
            # Delete the previous response
            previous_message_id = self.queue_manager.get_message_id(queue_id)
            if previous_message_id:
                try:
                    previous_message = await interaction.channel.fetch_message(previous_message_id)
                    await previous_message.delete()
                    self.queue_manager.delete_message_id(queue_id)
                except discord.NotFound:
                    pass  # The message was already deleted
        else:
            # Generate a unique queue_id using uuid
            unique_id = str(uuid.uuid4())
            queue_id = f"valorant_{interaction.channel_id}_{unique_id}"
            
        # Send the new message and store its ID
        await interaction.response.send_message(f"R's? <@179124824109481984> will join{response}", view=QueueButton(self.bot, size, self.queue_manager, queue_id))
        new_message = await interaction.original_response()
        self.queue_manager.set_message_id(queue_id, new_message.id)
        
        
class QueueButton(discord.ui.View):
    def __init__(self, bot, size, queue_manager, queue_id) -> None:
        super().__init__(timeout=None)
        self.bot = bot
        self.size = size
        self.queue_manager = queue_manager
        self.queue_id = queue_id
        
    @discord.ui.button(label="Join Queue", style=discord.ButtonStyle.primary, emoji="😎")
    async def button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        response = "R's?"
        user = interaction.user
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
                user_dm = await self.bot.fetch_user(user.id)
                queue_members = "\n".join(user.mention for user in current_queue)
                await user_dm.send(f"{self.size} R's are ready\nCurrent Queue:\n{queue_members}")
            await interaction.response.edit_message(content=response, view=self)
        else:
            await interaction.response.edit_message(content=response)
            
    @discord.ui.button(label="Leave Queue", style=discord.ButtonStyle.danger, emoji="😢")
    async def leave_queue_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = interaction.user
        response = "R's?"
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
            
    @discord.ui.button(label="Delete Queue", style=discord.ButtonStyle.danger, emoji="❎")
    async def delete_queue_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        
        if interaction.user.id != interaction.message.interaction.user.id and not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("You don't have permission to delete this queue.", ephemeral=True)
            return
            
        # Check if the user has moderation permissions
        self.queue_manager.delete_queue(self.queue_id)
        previous_message_id = self.queue_manager.get_message_id(self.queue_id)
        if previous_message_id:
            try:
                previous_message = await interaction.channel.fetch_message(previous_message_id)
                await previous_message.delete()
                self.queue_manager.delete_message_id(self.queue_id)
            except discord.NotFound:
                pass
            
    @discord.ui.button(label="Show Queue ID", style=discord.ButtonStyle.danger, emoji="🆔")
    async def show_queue_id(self, interaction: discord.Interaction, button: discord.ui.Button):
        response = f"The queue ID is: `{self.queue_id}`"
        await interaction.response.send_message(response, ephemeral=True)  # Send the message only to the user who clicked the button
        
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
        return {queue_id: self.queues[queue_id] for queue_id in self.queues if self.queues[queue_id]}
    
    def set_message_id(self, queue_id, message_id):
        self.message_ids[queue_id] = message_id

    def get_message_id(self, queue_id):
        return self.message_ids.get(queue_id)

    def delete_message_id(self, queue_id):
        if queue_id in self.message_ids:
            del self.message_ids[queue_id]


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Valorant(bot), guilds=MY_GUILDS)
    print("Valorant is Loaded")
