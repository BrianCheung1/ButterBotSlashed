import discord
from discord import app_commands
from discord.ext import commands
import os
from dotenv import load_dotenv
import requests
import json
from datetime import datetime


load_dotenv()
IP = os.getenv('IP')
list_of_guilds = os.getenv("GUILDS").split(",")
MY_GUILDS = [discord.Object(id=int(guild)) for guild in list_of_guilds]


class Minecraft(commands.Cog):
    """Basic Features"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="mc", description="Show status of minecraft server")
    async def minecraft(self, interaction: discord.Interaction):
        """Show status of minecraft server"""
        url = requests.get(f'https://api.mcsrvstat.us/2/{IP}')
        text = url.text
        data = json.loads(text)
        server_status = data['online']

        if server_status:
            num_of_players = data['players']['online']
            if (num_of_players == 0):
                all_players = "` None `"
                all_players_list = "` None `"
            else:
                all_players = data['players']['uuid']
                all_players_list = ""
                for player, uuid in all_players.items():
                    all_players_list += f'` {player} - {uuid} `\n'

            embed = discord.Embed(title="Minecraft Server Status")
            embed.add_field(name="Players Online", value=num_of_players)
            embed.add_field(
                name="Players", value=all_players_list, inline=False)
            embed.timestamp = datetime.now()
            embed.set_footer(text=f'{interaction.user}',
                             icon_url=interaction.user.avatar)
            embed.set_image(url="https://external-content.duckduckgo.com/iu/?u=https%3A%2F%2Fvignette.wikia.nocookie.net%2Fstevethetrooper%2Fimages%2F2%2F25%2FThumbnail_minecraft_zps277f5003.png%2Frevision%2Flatest%3Fcb%3D20140102163508&f=1&nofb=1")

            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("Server is offline")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(
        Minecraft(bot),
        guilds=MY_GUILDS
    )
    print("Minecraft is Loaded")
