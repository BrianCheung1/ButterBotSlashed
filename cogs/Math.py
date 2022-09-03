import discord
from discord import app_commands
from discord.ext import commands

import os
from dotenv import load_dotenv

load_dotenv
list_of_guilds = os.getenv("GUILDS").split(",")
MY_GUILDS = [discord.Object(id=int(guild)) for guild in list_of_guilds]


class Math(commands.Cog):
    """Math functions"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(
        name="add",
        description="Adds two numbers together."
    )
    @app_commands.describe(
        first_value='The first value you want to add something to',
        second_value='The value you want to add to the first value',
    )
    async def add(self, interaction: discord.Interaction, first_value: int, second_value: int):
        """Adds two numbers together."""
        await interaction.response.send_message(f'{first_value} + {second_value} = {first_value + second_value}')

    @app_commands.command(
        name="subtract",
        description="Subtract one number from another."
    )
    @app_commands.describe(
        first_value='The first value you want to be subtracted',
        second_value='The value you want to subtract from the first value',
    )
    async def subtract(self, interaction: discord.Interaction, first_value: int, second_value: int):
        """Subtract one number from another."""
        await interaction.response.send_message(f'{first_value} - {second_value} = {first_value-second_value}')


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(
        Math(bot),
        guilds=MY_GUILDS
    )
    print("Math is Loaded")
