from discord import app_commands
from discord.ext import commands
from math import sqrt
from typing import Literal, Optional
import discord


class Math(commands.Cog):
    """Math Functions"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="math", description="math operations")
    @app_commands.describe(
        first_value="The first integer",
        second_value="The second integer",
    )
    async def math(
        self,
        interaction: discord.Interaction,
        first_value: float,
        operation: Literal["+", "-", "*", "/", "^", "√"],
        second_value: float,
    ):
        """Operations between two values"""
        answer = ""
        if operation == "+":
            answer = first_value + second_value
        elif operation == "-":
            answer = first_value - second_value
        elif operation == "*":
            answer = first_value * second_value
        elif operation == "/":
            answer = first_value / second_value
        elif operation == "^":
            answer = first_value**second_value
        elif operation == "√":
            answer = sqrt(first_value)

        answer = "{0:,.17g}".format(answer)
        first_value = "{0:,.17g}".format(first_value)
        second_value = "{0:,.17g}".format(second_value)
        answer_response = f"{first_value} {operation} {second_value} = {answer}"
        await interaction.response.send_message(answer_response)


# async def setup(bot: commands.Bot) -> None:
#     await bot.add_cog(Math(bot))
#     print("Math is Loaded")
