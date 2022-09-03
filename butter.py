from typing import Optional, Literal

import discord
from discord import app_commands
from discord.ext import commands
import os
from dotenv import load_dotenv
from datetime import datetime
from discord.ext import tasks
import requests
import json
from pyfiglet import figlet_format


# will first look for a .env file and if it finds one, it will load the environment variables from the file and make them accessible to your project
load_dotenv()
TOKEN = os.getenv('TOKEN')
CLIENT_ID = os.getenv('ID')
# list_of_guilds = os.getenv("GUILDS").split(",")
# MY_GUILDS = [discord.Object(id=int(guild)) for guild in list_of_guilds]


class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(
            activity=discord.Activity(
                type=discord.ActivityType.watching, name="You"),
            command_prefix="`",
            intents=discord.Intents.all(),
            application_id=CLIENT_ID
        )

    async def setup_hook(self) -> None:
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                await self.load_extension(f'cogs.{filename[:-3]}')
        # await self.tree.sync(guild=discord.Object(int(os.getenv("GUILDS").split(",")[0])))
        # self.my_background_task.start()

    async def on_ready(self):
        print('------')
        print(f'\n{figlet_format("ButterBot", "standard")}')
        print(f'{datetime.now().strftime("Date: %D")}')
        print(f'{datetime.now().strftime("Time: %I:%M:%S:%p")}')
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        print(f'Ping {round(self.latency*1000)}ms')
        print('------')

    @ tasks.loop(seconds = 60)  # task runs every 60 seconds
    async def my_background_task(self):
        print("test")

    @ my_background_task.before_loop
    async def before_my_task(self):
        await self.wait_until_ready()  # wait until the bot logs in


bot=MyBot()
bot.run(TOKEN)
