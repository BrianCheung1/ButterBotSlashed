from datetime import datetime
from discord import ButtonStyle, app_commands
from discord.ext import commands
from discord.ui import Button, View
from dotenv import load_dotenv
from typing import Literal, Union, NamedTuple, Optional, List
from urllib.parse import quote_plus
import discord
import os
import tmdbsimple as tmdb
from pytz import timezone
from AnilistPython import Anilist


anilist = Anilist()
tmdb.API_KEY = os.getenv("TMDB")

load_dotenv()
list_of_guilds = os.getenv("GUILDS").split(",")
MY_GUILDS = [discord.Object(id=int(guild)) for guild in list_of_guilds]


class General(commands.Cog):
    """Basic Features"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="invite", description="Invite me to your discord server")
    async def invite(self, interaction: discord.Interaction):
        """Invite me to your discord server"""
        button = Button(
            label="Invite",
            url=f"https://discord.com/api/oauth2/authorize?client_id={self.bot.user.id}&permissions=8&scope=bot",
            style=ButtonStyle.url,
        )
        view = View()
        view.add_item(button)

        embed = discord.Embed()
        embed.title = f"Click the button below to invite me to your server! \U0001f389"
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="google")
    async def google(self, interaction: discord.Interaction, query: str):
        """Returns a google link for a query"""
        await interaction.response.send_message(
            f"Google Result for: `{query}`", view=Google(query)
        )

    @app_commands.command(name="movie", description="Shows information about a movie")
    @app_commands.describe(query="Movie you want to search")
    async def movie(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer()
        search = tmdb.Search()
        response = search.movie(query=query)
        if not search.results:
            await interaction.followup.send("No results for your query")
        view = discord.ui.View()
        for index, result in enumerate(search.results):
            view.add_item(MovieButton(index + 1, search.results[index]))
            if index >= 4:
                break
        view.add_item(MovieMenuButton(query, search.results))
        embed = discord.Embed()
        results = ""
        for index, result in enumerate(search.results):
            results += f'{index+1}. **{result["title"]}**\n'
            if index >= 4:
                break
        embed.add_field(name=f"Results for {query.title()}", value=results)
        embed.timestamp = datetime.now()
        embed.set_footer(
            text=f"{interaction.user.display_name}",
            icon_url=interaction.user.display_avatar,
        )
        await interaction.followup.send(embed=embed, view=view)

    @app_commands.command(name="anime", description="Shows information about a anime")
    @app_commands.describe(query="Anime you want to search")
    async def anime(self, interaction: discord.Interaction, query: str):
        try:
            anime_dict = anilist.get_anime(query)
            anime_id = anilist.get_anime_id(anime_dict["name_romaji"])
        except IndexError as e:
            return await interaction.response.send_message(
                f"{e}, Please try changing your query"
            )
        embed = discord.Embed(
            title=f'{anime_dict["name_romaji"]}',
            description=anime_dict["name_english"],
            url=f"https://anilist.co/anime/{anime_id}",
        )
        embed.add_field(name="Start Date", value=anime_dict["starting_time"])
        embed.add_field(name="End Date", value=anime_dict["ending_time"])
        embed.add_field(name="Season", value=anime_dict["season"])
        embed.add_field(name="Status", value=anime_dict["airing_status"])

        if anime_dict["next_airing_ep"]:
            next_eps = anime_dict["next_airing_ep"]["airingAt"]
            converted_time = datetime.fromtimestamp(next_eps).strftime("%D")
            next_eps_air = anime_dict["next_airing_ep"]["timeUntilAiring"]
            converted_time_air = convert(next_eps_air)
            embed.add_field(name="Next Eps Date", value=f"{converted_time}")
            embed.add_field(name="Remaining Time", value=f"{converted_time_air}")
            embed.add_field(
                name="Next Eps", value=f'{anime_dict["next_airing_ep"]["episode"]}'
            )
        else:
            embed.add_field(name="Next Eps", value="None")

        embed.add_field(name="Score", value=anime_dict["average_score"])
        embed.add_field(name="Total Eps", value=anime_dict["airing_episodes"])
        if anime_dict["genres"]:
            embed.add_field(
                name="Genre", value=", ".join(anime_dict["genres"]), inline=False
            )
        if len(anime_dict["desc"]) > 1024:
            anime_dict["desc"] = anime_dict["desc"][0:1000] + "..."
        if not anime_dict["desc"]:
            anime_dict["desc"] = "None"
        embed.add_field(
            name="Description",
            value=anime_dict["desc"]
            .replace("<br>", "")
            .replace("<i>", "*")
            .replace("</i>", "*"),
            inline=False,
        )
        embed.set_image(url=anime_dict["banner_image"])
        embed.set_thumbnail(url=anime_dict["cover_image"])
        embed.set_footer(text="Data from Anilist")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="time", description="Convert from one time zone to another"
    )
    async def time(
        self,
        interaction: discord.Interaction,
        timezones: Literal[
            "US/Central", "US/Eastern", "US/Mountain", "US/Pacific", "UTC"
        ],
    ):
        embed = discord.Embed(title="Time Converter")
        embed.add_field(
            name="Local Time",
            value=f'{datetime.now().strftime("Time: %I:%M:%S:%p")}',
        )
        embed.add_field(
            name=f"{timezones}",
            value=f'{datetime.now(timezone(timezones)).strftime("Time: %I:%M:%S:%p")}',
        )
        await interaction.response.send_message(embed=embed)


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


class MovieMenuButton(discord.ui.Button):
    def __init__(self, query, results):
        super().__init__()
        self.results = results
        self.label = "Menu"
        self.query = query
        self.style = discord.ButtonStyle.primary

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        embed = discord.Embed()
        results = ""
        for index, result in enumerate(self.results):
            results += f'{index+1}. **{result["title"]}**\n'
            if index >= 4:
                break
        embed.add_field(name=f"Results for {self.query.title()}", value=results)
        embed.timestamp = datetime.now()
        embed.set_footer(
            text=f"{interaction.user.display_name}",
            icon_url=interaction.user.display_avatar,
        )
        await interaction.followup.edit_message(
            message_id=interaction.message.id, embed=embed, view=self.view
        )


class MovieButton(discord.ui.Button):
    def __init__(self, label, results):
        super().__init__()
        self.results = results
        self.label = label
        self.style = discord.ButtonStyle.primary

    async def callback(self, interaction: discord.Interaction):

        await interaction.response.defer()
        first_result = self.results
        movie = tmdb.Movies(first_result["id"])
        genres = []
        for genre in movie.info()["genres"]:
            genres.append(genre["name"])
        genres = ", ".join(genres)
        embed = discord.Embed(
            title=f"{movie.title}",
            description=f"{movie.tagline}",
            url=f"https://www.imdb.com/title/{movie.imdb_id}",
        )
        embed.add_field(name="Release Date", value=f"{movie.release_date}")
        embed.add_field(name="Rating", value=f"{movie.vote_average:.2f}")
        embed.add_field(name="Original Language", value=f"{movie.original_language}")

        hours = movie.runtime // 60
        mins = movie.runtime % 60
        converted_runtime = f"{hours}H{mins}M"
        embed.add_field(name="Budget", value=f"${movie.budget:,.2f}")
        embed.add_field(name="Revenue", value=f"${movie.revenue:,.2f}")
        embed.add_field(name="Runtime", value=f"{converted_runtime}")
        if genres:
            embed.add_field(name="Genres", value=f"{genres}")
        if movie.overview:
            embed.add_field(name="Overview", value=f"{movie.overview}", inline=False)
        embed.set_image(
            url=f"https://image.tmdb.org/t/p/original/{movie.backdrop_path}"
        )
        embed.set_thumbnail(
            url=f"https://image.tmdb.org/t/p/original/{movie.poster_path}"
        )
        embed.set_footer(text="Data from TMDB")
        await interaction.followup.edit_message(
            message_id=interaction.message.id, embed=embed, view=self.view
        )


def convert(time):

    day = time // (24 * 3600)
    time = time % (24 * 3600)
    hour = time // 3600
    time %= 3600
    minutes = time // 60
    time %= 60
    return "%dD:%dH:%dM" % (day, hour, minutes)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(General(bot), guilds=MY_GUILDS)
    print("General is Loaded")
