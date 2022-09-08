from datetime import datetime
from discord.ext import commands
from dotenv import load_dotenv
from pyfiglet import figlet_format
import discord
import os

# will first look for a .env file and if it finds one, it will load the environment variables from the file
# and make them accessible to your project
load_dotenv()
TOKEN = os.getenv("TOKEN")
CLIENT_ID = os.getenv("ID")


class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="`", intents=discord.Intents.all(), application_id=CLIENT_ID
        )

    async def setup_hook(self) -> None:
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py"):
                await self.load_extension(f"cogs.{filename[:-3]}")
        for guild in self.guilds:
            await self.tree.sync(guild=discord.Object(int(guild.id)))

    async def on_ready(self):
        print("------")
        print(f'\n{figlet_format("ButterBot", "standard")}')
        print(f'{datetime.now().strftime("Date: %D")}')
        print(f'{datetime.now().strftime("Time: %I:%M:%S:%p")}')
        print(f"Logged in as {self.user} (ID: {self.user.id})")
        print(f"Ping {round(self.latency*1000)}ms")
        print("------")


bot = MyBot()


# @bot.tree.error
# async def on_app_command_error(
#     interaction: Interaction,
#     error: AppCommandError
# ):
#     await interaction.response.send_message(error)

bot.run(TOKEN)
