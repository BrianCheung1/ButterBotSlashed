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
import kitsu
import asyncio
import aiosqlite
import random
import re

tmdb.API_KEY = os.getenv("TMDB")

load_dotenv()
list_of_guilds = os.getenv("GUILDS").split(",")
MY_GUILDS = [discord.Object(id=int(guild)) for guild in list_of_guilds]


class General(commands.Cog):
    """Basic Features"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.db_folder = "database"

        # Ensure the 'database' folder exists
        if not os.path.exists(self.db_folder):
            os.makedirs(self.db_folder)

        # Initialize the table in the background
        self.bot.loop.create_task(self.create_table())

    def get_db_name(self, guild_id):
        """Generate a unique database name based on the guild ID."""
        return os.path.join(self.db_folder, f"movies_{guild_id}.db")

    async def create_table(self):
        """Ensure the movies table exists for the specified guild."""
        for guild in MY_GUILDS:
            db_name = self.get_db_name(guild.id)
            async with aiosqlite.connect(db_name) as db:
                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS movies (
                        id INTEGER PRIMARY KEY,
                        name TEXT NOT NULL UNIQUE,
                        link TEXT NOT NULL UNIQUE
                    )
                """
                )
                await db.commit()

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
        embed = discord.Embed()
        results = ""
        for index, result in enumerate(search.results):
            view.add_item(MovieButton(index + 1, search.results[index]))
            results += f'{index+1}. **{result["title"]}** {result["release_date"]}\n'
            if index >= 4:
                break
        view.add_item(MovieMenuButton(query, search.results))
        embed.add_field(name=f"Results for {query.title()}", value=results)
        embed.timestamp = datetime.now()
        embed.set_footer(
            text=f"{interaction.user.display_name}",
            icon_url=interaction.user.display_avatar,
        )
        await interaction.followup.send(embed=embed, view=view)

    @app_commands.command(
        name="popular_movies", description="Shows the top 10 popular movies"
    )
    async def popular_movies(self, interaction: discord.Interaction):
        await interaction.response.defer()
        search = tmdb.Movies()
        embed = discord.Embed(title="Popular Movies")
        result = ""
        for index, movie in enumerate(search.popular()["results"][0:10]):

            # movie_info = tmdb.Movies(movie["id"])
            # response = movie_info.info()
            result += f'{index+1}. [{movie["title"]}](https://www.themoviedb.org/movie/{movie["id"]}) - Rating: {movie["vote_average"]} - {movie["release_date"]}\n'
        embed.add_field(name="Movies", value=f"{result}")
        await interaction.followup.send(embed=embed)

    @app_commands.command(
        name="trending_movies", description="Shows the top 10 trending movies this week"
    )
    async def trending_movies(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            # Fetch the trending movies for the week using tmdbsimple
            trending = tmdb.Trending()
            results = trending.info()

            if not results["results"]:
                await interaction.followup.send("No trending movies found.")
                return

            # Prepare the embed message
            embed = discord.Embed(title="Trending Movies This Week")
            result = ""
            for index, movie in enumerate(results["results"][:10]):
                result += f'{index+1}. [{movie["title"]}](https://www.themoviedb.org/movie/{movie["id"]}) - Rating: {movie["vote_average"]} - {movie["release_date"]}\n'

            embed.add_field(name="Movies", value=f"{result}")
            await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(
                f"An error occurred while fetching the trending movies: {e}"
            )

    @app_commands.command(
        name="popular_shows", description="Shows the top 10 popular shows"
    )
    async def popular_shows(self, interaction: discord.Interaction):
        await interaction.response.defer()
        search = tmdb.TV()
        embed = discord.Embed(title="Popular Movies")
        result = ""
        for index, show in enumerate(search.popular()["results"][0:10]):
            result += f'{index+1}. [{show["name"]}](https://www.themoviedb.org/tv/{show["id"]}) - Rating: {show["vote_average"]} - {show["first_air_date"]}\n'
        embed.add_field(name="Movies", value=f"{result}")
        await interaction.followup.send(embed=embed)

    @app_commands.command(
        name="trending_tv_shows",
        description="Shows the top 10 trending TV shows this week",
    )
    async def trending_tv_shows(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            # Fetch the trending TV shows for the week using tmdbsimple
            trending = tmdb.Trending(media_type="tv")
            results = trending.info()

            if not results["results"]:
                await interaction.followup.send("No trending TV shows found.")
                return

            # Prepare the embed message
            embed = discord.Embed(title="Trending TV Shows This Week")
            result = ""
            for index, tv_show in enumerate(results["results"][:10]):
                result += f'{index+1}. [{tv_show["name"]}](https://www.themoviedb.org/tv/{tv_show["id"]}) - Rating: {tv_show["vote_average"]} - {tv_show["first_air_date"]}\n'

            embed.add_field(name="TV Shows", value=f"{result}")
            await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(
                f"An error occurred while fetching the trending TV shows: {e}"
            )

    @app_commands.command(
        name="tv_show", description="Shows information about a tv show"
    )
    @app_commands.describe(query="TV show you want to search")
    async def tv_show(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer()
        search = tmdb.Search()
        response = search.tv(query=query)
        if not search.results:
            await interaction.followup.send("No results for your query")
        view = discord.ui.View()
        embed = discord.Embed()
        results = ""
        for index, result in enumerate(search.results):
            view.add_item(TVButton(index + 1, search.results[index]))
            results += f'{index+1}. **{result["original_name"]}**\n'
            if index >= 4:
                break
        view.add_item(TVMenuButton(query, search.results))
        embed.add_field(name=f"Results for {query.title()}", value=results)
        embed.timestamp = datetime.now()
        embed.set_footer(
            text=f"{interaction.user.display_name}",
            icon_url=interaction.user.display_avatar,
        )
        await interaction.followup.send(embed=embed, view=view)

    @app_commands.command(name="popular_animes", description="Shows popular anime")
    async def popular_animes(self, interaction: discord.Interaction):
        client = kitsu.Client()
        await interaction.response.defer()
        animes = await client.trending_anime()
        embed = discord.Embed()
        results = ""
        for index, anime in enumerate(animes):
            results += (
                f"{index+1}. **[{anime.title}](https://kitsu.io/anime/{anime.id})**\n"
            )
        embed.add_field(name="Trending Animes", value=results)
        await client.close()
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="anime", description="Shows information about a anime")
    @app_commands.describe(query="Anime you want to search")
    async def anime(self, interaction: discord.Interaction, query: str):
        client = kitsu.Client()
        await interaction.response.defer()
        animes = await client.search_anime(query, limit=5)
        embed = discord.Embed()
        results = ""
        view = discord.ui.View()
        if not animes:
            await interaction.followup.send("No results for your query")
        if not isinstance(animes, list):
            view.add_item(AnimeButton(1, animes))
            results += f"{1}. **[{animes.canonical_title}](https://kitsu.io/anime/{animes.id})** - Rating: {animes.average_rating}\n"
        else:
            for index, anime in enumerate(animes):
                view.add_item(AnimeButton(index + 1, animes[index]))
                results += f"{index+1}. **[{anime.canonical_title}](https://kitsu.io/anime/{anime.id})** - Rating: {anime.average_rating}\n"

        view.add_item(AnimeMenuButton(query, animes))
        embed.add_field(name=f"Results for {query.title()}", value=results)
        embed.timestamp = datetime.now()
        embed.set_footer(
            text=f"{interaction.user.display_name}",
            icon_url=interaction.user.display_avatar,
        )
        await interaction.followup.send(embed=embed, view=view)

    @app_commands.command(
        name="time", description="Convert from one time zone to another"
    )
    @app_commands.describe(timezones="Timezone you want current time to convert to")
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
            value=f'{datetime.now().strftime("%I:%M:%p")}',
            inline=False,
        )
        embed.add_field(
            name=f"{timezones}",
            value=f'{datetime.now(timezone(timezones)).strftime("%I:%M:%p")}',
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="add_movies")
    @app_commands.describe(
        movie_links="Enter one or more IMDb movie links or movie names, separated by commas. Example: https://www.imdb.com/title/tt0111161/, The Godfather"
    )
    async def add_movies(self, interaction: discord.Interaction, movie_links: str):
        """
        Add one or multiple movies to the database using IMDb links or TMDb movie names.
        Use commas to separate multiple movie links or names.
        """
        guild_id = interaction.guild.id
        await self.create_table()  # Ensure the table exists for the guild

        # Split the input by commas and strip whitespace
        link_list = [link.strip() for link in movie_links.split(",")]

        db_name = self.get_db_name(guild_id)
        async with aiosqlite.connect(db_name) as db:
            added_movies = []
            duplicate_movies = []

            for entry in link_list:
                # Check if entry is an IMDb link
                if re.match(r"^https?://(www\.)?imdb\.com/title/tt\d+/", entry):
                    movie_name = await self.get_movie_name_from_imdb(entry)
                    movie_link = entry
                else:
                    # Use tmdbsimple to search for the movie by name
                    search = tmdb.Search()
                    response = search.movie(query=entry)
                    if response["results"]:
                        movie = response["results"][0]  # Take the first result
                        movie_name = movie["title"]
                        movie_link = f"https://www.themoviedb.org/movie/{movie['id']}"
                    else:
                        await interaction.response.send_message(
                            f"Movie not found: {entry}"
                        )
                        continue  # Skip if movie couldn't be found

                # Attempt to add the movie to the database
                try:
                    await db.execute(
                        "INSERT INTO movies (name, link) VALUES (?, ?)",
                        (movie_name, movie_link),
                    )
                    added_movies.append(
                        (movie_name, movie_link)
                    )  # Store both name and link
                except aiosqlite.IntegrityError:
                    duplicate_movies.append(movie_name)

            await db.commit()

        # Send feedback to the user
        added_message = (
            f"Added movies:\n"
            + "\n".join(f"[{name}](<{link}>)" for name, link in added_movies)
            if added_movies
            else "No new movies were added."
        )
        duplicate_message = (
            f"Duplicates not added: \n{', '.join(duplicate_movies)}"
            if duplicate_movies
            else ""
        )
        await interaction.response.send_message(f"{added_message}\n{duplicate_message}")

    @app_commands.command(name="list_movies")
    @app_commands.describe(
        guild_id="Optional guild ID to list movies from a specific guild."
    )
    async def list_movies(self, interaction: discord.Interaction, guild_id: str = None):
        """List all movies in the database for the server or a specific guild."""

        # If no guild_id is provided, use the current guild's ID
        if guild_id is None:
            guild_id = interaction.guild.id

        db_name = self.get_db_name(guild_id)

        async with aiosqlite.connect(db_name) as db:
            async with db.execute("SELECT name, link FROM movies") as cursor:
                movies = await cursor.fetchall()
                if not movies:
                    await interaction.response.send_message(
                        f"No movies found in the database for guild ID {guild_id}."
                    )
                    return

                # Divide movies into chunks of 10 and add index numbers
                chunks = [movies[i : i + 10] for i in range(0, len(movies), 10)]
                await interaction.response.send_message(
                    f"List of movies in guild {guild_id}:"
                )

                movie_index = 1  # Start the index counter
                for chunk in chunks:
                    # Format each movie with its index number
                    movie_list = "\n".join(
                        f"{movie_index + i}. [{name}](<{link}>)"
                        for i, (name, link) in enumerate(chunk)
                    )
                    movie_index += len(chunk)  # Update the index for the next chunk

                    await interaction.channel.send(movie_list)

    @app_commands.command(name="remove_movie")
    @app_commands.describe(
        movie_identifier="Enter movie link or name of movie,Example: https://www.imdb.com/title/tt0111161/ or The Shawshank Redemption"
    )
    async def remove_movie(
        self, interaction: discord.Interaction, movie_identifier: str
    ):
        """Remove a movie from the database for the server by title or link."""
        guild_id = interaction.guild.id
        db_name = self.get_db_name(guild_id)

        async with aiosqlite.connect(db_name) as db:
            # Convert the identifier to lower case for case-insensitive comparison
            lower_identifier = movie_identifier.lower()

            # Try to find the movie by title (case-insensitive)
            cursor = await db.execute(
                "SELECT id, link, name FROM movies WHERE LOWER(name) = ?",
                (lower_identifier,),
            )
            movie = await cursor.fetchone()

            # If not found by title, try to find by link (case-insensitive)
            if not movie:
                cursor = await db.execute(
                    "SELECT id, link, name FROM movies WHERE LOWER(link) = ?",
                    (lower_identifier,),
                )
                movie = await cursor.fetchone()

            # If a movie was found, remove it
            if movie:
                movie_id, movie_link, name = movie
                await db.execute("DELETE FROM movies WHERE id = ?", (movie_id,))
                await db.commit()

                # Format movie identifier as a hyperlink if link is available
                link_text = f"[{name}](<{movie_link}>)"

                await interaction.response.send_message(f"Removed movie: {link_text}")
            else:
                await interaction.response.send_message(
                    f"Movie not found: {movie_identifier}"
                )

    @app_commands.command(name="random_movie")
    async def random_movie(self, interaction: discord.Interaction):
        """Choose a random movie from the database for the server and delete it."""
        guild_id = interaction.guild.id
        db_name = self.get_db_name(guild_id)

        async with aiosqlite.connect(db_name) as db:
            # Retrieve both `id`, `name`, and `link` of all movies
            async with db.execute("SELECT id, name, link FROM movies") as cursor:
                movies = await cursor.fetchall()
                if not movies:
                    await interaction.response.send_message(
                        "No movies found in the database. Use /add_movie to add some!"
                    )
                    return

                # Choose a random movie
                chosen_movie = random.choice(movies)
                movie_id, movie_name, movie_link = chosen_movie

                # Delete the chosen movie from the database
                await db.execute("DELETE FROM movies WHERE id = ?", (movie_id,))
                await db.commit()

                # Prepare the response with a hyperlink and suppress preview
                movie_message = f"Random movie: [{movie_name}](<{movie_link}>) (Deleted from database)"
                await interaction.response.send_message(movie_message)

    @app_commands.command(name="list_databases")
    async def list_databases(self, interaction: discord.Interaction):
        """List all available movie databases and allow the user to select one."""
        # Fetch full guild objects for each guild ID in MY_GUILDS
        guild_list = []
        for guild_id in list_of_guilds:
            guild = self.bot.get_guild(int(guild_id))
            if guild:
                guild_list.append(f"{guild.name}\n`{guild.id}`")
            else:
                guild_list.append(f"(Unknown Guild)\n`{guild_id}`")

        guild_list_text = "\n".join(guild_list)

        # Send the list to the user
        await interaction.response.send_message(
            f"Available movie databases:\n{guild_list_text}\n\n"
            "Please use `/list_movies <guild_id>` to list movies for a specific database."
        )

    async def get_movie_name_from_imdb(self, imdb_url):
        """Retrieve movie title from IMDb link using tmdbsimple."""
        # Extract IMDb ID from URL using regex
        imdb_id_match = re.search(r"tt\d+", imdb_url)
        if not imdb_id_match:
            return None  # IMDb ID not found in URL

        imdb_id = imdb_id_match.group()
        search = tmdb.Find(imdb_id)
        response = search.info(external_source="imdb_id")

        if response["movie_results"]:
            return response["movie_results"][0]["title"]
        return None


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
            results += f'{index+1}. **{result["title"]}** {result["release_date"]}\n'
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
            url=f"https://www.themoviedb.org/movie/{movie.id}",
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
            if len(movie.overview) > 1024:
                movie.overview = movie.overview[0:1021] + "..."
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


class TVMenuButton(discord.ui.Button):
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
            results += f'{index+1}. **{result["original_name"]}** {result["first_release_date"]}\n'
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


class TVButton(discord.ui.Button):
    def __init__(self, label, results):
        super().__init__()
        self.results = results
        self.label = label
        self.style = discord.ButtonStyle.primary

    async def callback(self, interaction: discord.Interaction):

        await interaction.response.defer()
        first_result = self.results
        show = tmdb.TV(first_result["id"])
        genres = []
        for genre in show.info()["genres"]:
            genres.append(genre["name"])
        genres = ", ".join(genres)
        embed = discord.Embed(
            title=f"{show.name}",
            description=f"{show.tagline}",
            url=f"https://www.themoviedb.org/tv/{show.id}",
        )
        embed.add_field(name="Release Date", value=f"{show.first_air_date}")
        embed.add_field(name="Rating", value=f"{show.vote_average:.2f}")
        embed.add_field(name="Original Language", value=f"{show.original_language}")

        embed.add_field(name="Seasons", value=f"{show.number_of_seasons}")
        embed.add_field(name="Episodes", value=f"{show.number_of_episodes}")
        if show.next_episode_to_air:
            show.next_episode_to_air = f'{show.next_episode_to_air["air_date"]}'
        embed.add_field(name="Next Eps", value=f"{show.next_episode_to_air}")
        if genres:
            embed.add_field(name="Genres", value=f"{genres}")
        if show.overview:
            if len(show.overview) > 1024:
                show.overview = show.overview[0:1021] + "..."
            embed.add_field(name="Overview", value=f"{show.overview}", inline=False)
        embed.set_image(url=f"https://image.tmdb.org/t/p/original/{show.backdrop_path}")
        embed.set_thumbnail(
            url=f"https://image.tmdb.org/t/p/original/{show.poster_path}"
        )
        embed.set_footer(text="Data from TMDB")
        await interaction.followup.edit_message(
            message_id=interaction.message.id, embed=embed, view=self.view
        )


class AnimeMenuButton(discord.ui.Button):
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
        if not isinstance(self.results, list):
            results += f"{1}. **[{self.results.canonical_title}](https://kitsu.io/anime/{self.results.id})** - Rating: {self.results.average_rating}\n"
        else:
            for index, anime in enumerate(self.results):
                results += f"{index+1}. **[{anime.canonical_title}](https://kitsu.io/anime/{anime.id})** - Rating: {anime.average_rating}\n"

        embed.add_field(name=f"Results for {self.query.title()}", value=results)
        embed.timestamp = datetime.now()
        embed.set_footer(
            text=f"{interaction.user.display_name}",
            icon_url=interaction.user.display_avatar,
        )
        await interaction.followup.edit_message(
            message_id=interaction.message.id, embed=embed, view=self.view
        )


class AnimeButton(discord.ui.Button):
    def __init__(self, label, results):
        super().__init__()
        self.results = results
        self.label = label
        self.style = discord.ButtonStyle.primary

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        anime = self.results
        embed = discord.Embed(
            title=f"{anime.canonical_title}",
            description=f"{anime.title}",
            url=f"https://kitsu.io/anime/{anime.slug}",
        )
        embed.add_field(
            name="Release Date", value=f"{anime.start_date.strftime('%Y-%m-%d')}"
        )
        embed.add_field(name="Rating", value=f"{anime.average_rating}")
        embed.add_field(name="Episodes", value=f"{anime.episode_count}")

        embed.add_field(name="Ranking", value=f"{anime.rating_rank}")
        embed.add_field(name="Popularity", value=anime.popularity_rank)
        embed.add_field(name="Status", value=f"{anime.status}")

        genres = ", ".join(c.title for c in await anime.categories)
        if not genres:
            genres = "None"
        embed.add_field(name="Genre", value=genres)
        if len(anime.synopsis) > 1024:
            anime.synopsis = anime.synopsis[0:1021] + "..."
        embed.add_field(name="Overview", value=f"{anime.synopsis}", inline=False)
        embed.set_image(url=anime.cover_image())
        embed.set_thumbnail(url=anime.poster_image())
        embed.set_footer(text="Data from Kitsu")
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
