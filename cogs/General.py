from urllib.parse import quote_plus

import discord
from discord import ButtonStyle, app_commands
from discord.ext import commands
from discord.ui import Button, View
import random


class General(commands.Cog):
    """Basic Features"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="invite", description="Invite me to your discord server")
    async def invite(self, interaction: discord.Interaction):
        """Invite me to your discord server"""
        button = Button(
            label="Invite",
            url="https://discord.com/oauth2/authorize?client_id=734971561878093844",
            style=ButtonStyle.url,
        )
        view = View()
        view.add_item(button)

        embed = discord.Embed()
        embed.title = "Click the button below to invite me to your server! \U0001f389"
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="google")
    async def google(self, interaction: discord.Interaction, query: str):
        """Returns a google link for a query"""
        await interaction.response.send_message(
            f"Google Result for: `{query}`", view=Google(query)
        )

    @app_commands.command(name="8ball")
    async def eight_ball(self, interaction: discord.Interaction, question: str):
        """Returns a random 8ball response"""
        responses = [
            # Yes-style responses
            "Absolutely yes!",
            "You bet!",
            "Without a doubt!",
            "Heck yes!",
            "Yes, unless the world ends first.",
            "Sure, why not?",
            "Yup, it's in the cards.",
            "As certain as taxes.",
            "Affirmative, captain!",
            "Yes, and you didn't even need to shake me.",
            # No-style responses
            "Nope. Not today, not tomorrow.",
            "Absolutely not!",
            "No, and I'm judging you for asking.",
            "Negative, ghost rider.",
            "Nah, not a chance.",
            "Not in this universe.",
            "No, unless pigs start flying.",
            "Denied. Try again later.",
            "Hard no.",
            "Ask someone else... preferably not me.",
            # Maybe / unsure
            "Ask again later.",
            "I don't know, maybe?",
            "Could be... but I'm not confident.",
            "The answer is fuzzy. Try cleaning your screen.",
            "That's above my pay grade.",
        ]

        response = random.choice(responses)
        await interaction.response.send_message(response)


# Define a simple View that gives us a google link button.
# We take in `query` as the query that the command author requests for
class Google(discord.ui.View):
    def __init__(self, query: str):
        super().__init__()
        # we need to quote the query string to make a valid url. Discord will raise an error if it isn't valid.
        query = quote_plus(query)
        url = f"https://www.google.com/search?q={query}"

        # Link buttons cannot be made with the decorator
        # Therefore we have to manually create one.
        # We add the quoted url to the button, and add the button to the view.
        self.add_item(discord.ui.Button(label="Click Here", url=url))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(General(bot))
    print("General is Loaded")
