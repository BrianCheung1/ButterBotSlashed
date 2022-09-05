import discord
from discord import app_commands
from discord.ext import commands
import os
from dotenv import load_dotenv
import requests
import json
from datetime import datetime
from discord.ext import tasks


load_dotenv()
IP = os.getenv('IP')
list_of_guilds = os.getenv("GUILDS").split(",")
MY_GUILDS = [discord.Object(id=int(guild)) for guild in list_of_guilds]


class Minecraft(commands.Cog):
    """Basic Features"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.minecraft_status = "Offline - Nobody online 🥲"
        self.my_background_task.start()

    @app_commands.command(name="mc", description="Show status of minecraft server")
    async def minecraft(self, interaction: discord.Interaction):
        """Show status of minecraft server"""
        url = requests.get(
            f'https://minecraft-api.com/api/ping/{IP}/25565/json')
        if not url.text.__contains__("players"):
            await interaction.response.send_message("Server is offline")
        text = json.loads(url.text)

        modpack_name = text['modpackData']['name']
        minecraft_version = text['version']['name']
        players_online = text['players']['online']
        all_players = ""
        if (players_online != 0):
            for player in text['players']['sample']:
                all_players += f'`{player["name"]} - {player["id"]} `\n'
        if (len(all_players) == 0):
            all_players = "Nobody online 🥲"
        embed = discord.Embed(title="Minecraft Server Status")
        embed.add_field(
            name="Modpack Name", value=modpack_name, inline=True)
        embed.add_field(
            name="Minecraft Version", value=minecraft_version, inline=True)
        embed.add_field(
            name=f'Players Online - {players_online}', value=all_players, inline=False)
        embed.timestamp = datetime.now()
        embed.set_footer(text=f'{interaction.user}',
                         icon_url=interaction.user.avatar)
        embed.set_image(url="https://external-content.duckduckgo.com/iu/?u=https%3A%2F%2Fvignette.wikia.nocookie.net%2Fstevethetrooper%2Fimages%2F2%2F25%2FThumbnail_minecraft_zps277f5003.png%2Frevision%2Flatest%3Fcb%3D20140102163508&f=1&nofb=1")

        await interaction.response.send_message(embed=embed)

    @tasks.loop(seconds=300)  # task runs every 60 seconds
    async def my_background_task(self):
        url = requests.get(
            f'https://minecraft-api.com/api/ping/{IP}/25565/json')
        if not url.text.__contains__("players"):
            self.minecraft_status = "Minecraft Server - Offline 🥲"
        else:
            text = json.loads(url.text)
            players_online = text['players']['online']
            if (players_online != 1):
                self.minecraft_status = f'Minecraft Server - {players_online} players online'
            self.minecraft_status = f'Minecraft Server - {players_online} player online'
        await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=self.minecraft_status))

    @my_background_task.before_loop
    async def before_my_task(self):
        await self.bot.wait_until_ready()  # wait until the bot logs in


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(
        Minecraft(bot),
        guilds=MY_GUILDS

    )
    print("Minecraft is Loaded")
