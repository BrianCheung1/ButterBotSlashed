from datetime import datetime
from discord.ext import commands
from dotenv import load_dotenv
from pyfiglet import figlet_format
import discord
import os
import asyncio

# Load environment variables from .env file
load_dotenv()
TOKEN = os.getenv("TOKEN")
CLIENT_ID = os.getenv("ID")

# Ensure TOKEN and CLIENT_ID are loaded properly
if not TOKEN or not CLIENT_ID:
    raise ValueError("Bot token or client ID not found in environment variables.")


class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="`",
            intents=discord.Intents.all(),
            application_id=CLIENT_ID,
            help_command=None,
        )

    async def setup_hook(self) -> None:
        excluded_cogs = []  # Add cog names to exclude if needed
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py"):
                cog_name = filename[:-3]
                if cog_name not in excluded_cogs:
                    await self.load_extension(f"cogs.{cog_name}")
                else:
                    print(f"Skipping {cog_name}...")

    async def on_ready(self):
        print("------")
        print(f'\n{figlet_format("ButterBot", "standard")}')
        print(f"Date: {datetime.now().strftime('%Y-%m-%d')}")
        print(f"Time: {datetime.now().strftime('%H:%M:%S')}")
        print(f"Logged in as {self.user} (ID: {self.user.id})")
        print(f"Ping: {round(self.latency * 1000)} ms")
        print("------")


# Initialize and run the bot with error handling
try:
    bot = MyBot()
    bot.start_time = datetime.now()
    bot.run(TOKEN)
except discord.LoginFailure:
    print("Invalid token provided. Please check your .env file.")
except Exception as e:
    print(f"An error occurred: {e}")
