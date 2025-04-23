import os
import random
import re
from datetime import datetime

import aiosqlite
import discord
import kitsu
import tmdbsimple as tmdb
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
tmdb.API_KEY = os.getenv("TMDB")
# PLEX_URL = os.getenv("PLEX_URL")
# PLEX_TOKEN = os.getenv("PLEX_TOKEN")
# plex = PlexServer(PLEX_URL, PLEX_TOKEN)


class Streaming(commands.Cog):
    """Tv Shows and Movies Database"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.db_folder = "database"
        self.movies = {}

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
        for guild in self.bot.guilds:
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

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        """Delete the database file when the bot leaves a guild."""
        db_name = self.get_db_name(guild.id)
        if os.path.exists(db_name):
            os.remove(db_name)
            print(f"Deleted database for guild {guild.id}")

    @app_commands.command(name="movie", description="Shows information about a movie")
    @app_commands.describe(query="Movie you want to search")
    async def movie(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer()

        response = tmdb.Search()
        search = response.movie(query=query)
        results = search.get("results", [])  # Get the list of results from the response

        if not results:
            await interaction.followup.send("No results for your query")
            return

        view = discord.ui.View()
        embed = discord.Embed()
        result_text = ""

        for index, result in enumerate(results):
            title = result.get("title", "Unknown Title")
            release_date = result.get("release_date", "Unknown Date")
            view.add_item(
                MovieButton(index + 1, result)
            )  # Use the result object directly
            result_text += f"{index + 1}. **{title}** ({release_date})\n"

            if index >= 4:  # Show only the top 5 results
                break

        view.add_item(MovieMenuButton(query, results))
        embed.add_field(name=f"Results for '{query.title()}'", value=result_text)
        embed.timestamp = datetime.now()
        embed.set_footer(
            text=f"Requested by {interaction.user.display_name}",
            icon_url=interaction.user.display_avatar.url,
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
        name="tv_show", description="Shows information about a TV show"
    )
    @app_commands.describe(query="TV show you want to search")
    async def tv_show(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer()

        response = tmdb.Search()
        search = response.tv(query=query)  # Use `tv` method for TV show search
        results = search.get(
            "results", []
        )  # Get the list of results or empty list if none

        if not results:
            await interaction.followup.send("No results for your query")
            return

        view = discord.ui.View()
        embed = discord.Embed()
        result_text = ""

        for index, result in enumerate(results):
            original_name = result.get("original_name", "Unknown Name")
            first_air_date = result.get("first_air_date", "Unknown Date")
            view.add_item(TVButton(index + 1, result))  # Use the result object directly
            result_text += f"{index + 1}. **{original_name}** ({first_air_date})\n"

            if index >= 4:  # Show only the top 5 results
                break

        view.add_item(TVMenuButton(query, results))
        embed.add_field(name=f"Results for '{query.title()}'", value=result_text)
        embed.timestamp = datetime.now()
        embed.set_footer(
            text=f"Requested by {interaction.user.display_name}",
            icon_url=interaction.user.display_avatar.url,
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

        if not interaction.user:
            interaction.user = None

        db_name = self.get_db_name(guild_id)
        async with aiosqlite.connect(db_name) as db:
            added_movies = []
            duplicate_movies = []

            for entry in link_list:
                # Check if entry is an IMDb link
                if re.match(r"^https?://(www\.)?(m\.)?imdb\.com/title/tt\d+/", entry):
                    movie_name = await self.get_movie_name_from_imdb(entry)
                    movie_link = entry
                # Check if entry is a TMDb link
                elif re.match(r"^https?://(www\.)?themoviedb\.org/movie/\d+", entry):
                    tmdb_id_match = re.search(r"movie/(\d+)", entry)
                    if tmdb_id_match:
                        tmdb_id = tmdb_id_match.group(1)
                        movie = tmdb.Movies(tmdb_id)
                        response = movie.info()
                        if "title" in response:
                            movie_name = response["title"]
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
                        return

                # Attempt to add the movie to the database
                try:
                    await db.execute(
                        "INSERT INTO movies (name, link, added_by) VALUES (?, ?, ?)",
                        (movie_name, movie_link, interaction.user.name),
                    )
                    added_movies.append(
                        (movie_name, movie_link)
                    )  # Store both name and link
                except aiosqlite.IntegrityError:
                    duplicate_movies.append(movie_name)

            await db.commit()

        # Send feedback to the user
        added_message = (
            "Added movies:\n"
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
        try:
            async with aiosqlite.connect(db_name) as db:
                async with db.execute(
                    "SELECT name, link, added_by FROM movies"
                ) as cursor:
                    movies = await cursor.fetchall()
                    total_movies = len(movies)
                    if not movies:
                        await interaction.response.send_message(
                            f"No movies found in the database for guild ID {guild_id}."
                        )
                        return

                    # Divide movies into chunks of 10 and add index numbers
                    chunks = [movies[i : i + 10] for i in range(0, len(movies), 10)]
                    await interaction.response.send_message(
                        f"List of movies in guild {interaction.guild.name} (Total: {total_movies} movies):"
                    )

                    movie_index = 1  # Start the index counter
                    for chunk in chunks:
                        # Format each movie with its index number
                        movie_list = "\n".join(
                            f"{movie_index + i}. [{name}](<{link}>) - Added By {added_by}"
                            for i, (name, link, added_by) in enumerate(chunk)
                        )
                        movie_index += len(chunk)  # Update the index for the next chunk
                        await interaction.channel.send(movie_list)
        except Exception:
            await interaction.response.send_message(
                f"No movies found in the database for guild ID {guild_id}."
            )

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
                "SELECT id, link, name, added_by FROM movies WHERE LOWER(name) = ?",
                (lower_identifier,),
            )
            movie = await cursor.fetchone()

            # If not found by title, try to find by link (case-insensitive)
            if not movie:
                cursor = await db.execute(
                    "SELECT id, link, name, added_by FROM movies WHERE LOWER(link) = ?",
                    (lower_identifier,),
                )
                movie = await cursor.fetchone()

            # If a movie was found, remove it
            if movie:
                movie_id, movie_link, name, added_by = movie
                await db.execute("DELETE FROM movies WHERE id = ?", (movie_id,))
                await db.commit()

                # Format movie identifier as a hyperlink if link is available
                link_text = f"[{name}](<{movie_link}>)"

                await interaction.response.send_message(
                    f"Removed movie: {link_text} added by {added_by}"
                )
            else:
                await interaction.response.send_message(
                    f"Movie not found: {movie_identifier}"
                )

    @remove_movie.autocomplete("movie_identifier")
    async def movie_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice]:
        """Autocomplete function for movie_identifier."""
        guild_id = interaction.guild.id
        db_name = self.get_db_name(guild_id)

        # Check if results are cached for the current input
        if guild_id in self.movies and current in self.movies[guild_id]:
            return self.movies[guild_id][current]

        async with aiosqlite.connect(db_name) as db:
            # Fetch movies that match the current input (case-insensitive)
            cursor = await db.execute(
                """
                SELECT name FROM movies
                WHERE LOWER(name) LIKE ?
                LIMIT 25
                """,
                (f"%{current.lower()}%",),
            )
            movies = await cursor.fetchall()

        # Cache the results for this guild and input
        if guild_id not in self.movies:
            self.movies[guild_id] = {}
        self.movies[guild_id][current] = [
            app_commands.Choice(name=movie[0], value=movie[0]) for movie in movies
        ]

        # Return a list of app_commands.Choice objects for autocomplete
        return self.movies[guild_id][current]

    @app_commands.command(name="random_movie")
    async def random_movie(self, interaction: discord.Interaction):
        """Choose a random movie from the database for the server and delete it."""
        guild_id = interaction.guild.id
        db_name = self.get_db_name(guild_id)

        async with aiosqlite.connect(db_name) as db:
            # Retrieve both `id`, `name`, and `link` of all movies
            async with db.execute(
                "SELECT id, name, link, added_by FROM movies"
            ) as cursor:
                movies = await cursor.fetchall()
                if not movies:
                    await interaction.response.send_message(
                        "No movies found in the database. Use /add_movie to add some!"
                    )
                    return

                # Choose a random movie
                chosen_movie = random.choice(movies)
                movie_id, movie_name, movie_link, added_by = chosen_movie

                # Delete the chosen movie from the database
                await db.execute("DELETE FROM movies WHERE id = ?", (movie_id,))
                await db.commit()

                # Prepare the response with a hyperlink and suppress preview
                movie_message = f"Random movie: [{movie_name}](<{movie_link}>) added by {added_by} (Deleted from database)"
                await interaction.response.send_message(movie_message)

    @app_commands.command(name="list_databases")
    async def list_databases(self, interaction: discord.Interaction):
        """List all available movie databases and allow the user to select one, with the total movie count for each guild."""
        await interaction.response.defer()
        guild_list = []
        for guild in self.bot.guilds:
            if guild:
                db_name = self.get_db_name(guild.id)
                total_movies = 0

                try:
                    # Fetch the count of movies in the current guild's database
                    async with aiosqlite.connect(db_name) as db:
                        async with db.execute("SELECT COUNT(*) FROM movies") as cursor:
                            total_movies = await cursor.fetchone()
                            total_movies = total_movies[0] if total_movies else 0
                except Exception as e:
                    print(f"Error fetching movie count for guild {guild.id}: {e}")

                guild_list.append(
                    f"{guild.name} (`{guild.id}`) - Total Movies: {total_movies}"
                )
            else:
                guild_list.append(f"(Unknown Guild) (`{guild.id}`) - Total Movies: 0")

        guild_list_text = "\n".join(guild_list)

        # Send the list to the user
        await interaction.followup.send(
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
    await bot.add_cog(Streaming(bot))
    print("Streaming is Loaded")
