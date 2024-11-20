import asyncio

import discord
import yt_dlp as youtube_dl
from discord import app_commands
from discord.ext import commands


class YTDLSource:
    search_cache = {}

    @staticmethod
    async def from_url(url: str, *, loop=None, stream=False):
        # Check if the search term is already cached
        if url in YTDLSource.search_cache:
            return YTDLSource.search_cache[url]

        ydl_opts = {
            "format": "bestaudio/best",
            "extractaudio": True,
            "audioquality": 1,
            "outtmpl": "downloads/%(id)s.%(ext)s",
            "restrictfilenames": True,
            "quiet": True,
            "logtostderr": False,
            "nocheckcertificate": True,
            "default_search": "ytsearch3",
            "source_address": None,
            "noplaylist": True,
            "geo_bypass": True,  # Try bypassing regional restrictions
            "sleep_interval": 1,  # Reduce sleep time between requests
        }

        if stream:
            ydl_opts["force_generic_extractor"] = True
            ydl_opts["quiet"] = False

        # Perform the search asynchronously
        loop = asyncio.get_event_loop()
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = await loop.run_in_executor(
                None, lambda: ydl.extract_info(url, download=False)
            )
            # Check if 'entries' exists and return the list of results
            if "entries" in info:
                results = info["entries"]
            elif "url" in info:
                results = [info]
            else:
                results = []  # No results found

        # Cache the results for later use
        YTDLSource.search_cache[url] = results
        return results


class Music(commands.Cog):
    """Music Features"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.playlist = {}
        self.current = {}

    @app_commands.command(
        name="play", description="Plays a youtube url depending on user query"
    )
    @app_commands.describe(
        query="link to song you want played or general term to search for"
    )
    async def play(self, interaction: discord.Interaction, query: str):

        # Connect to voice channel if not already connected
        if interaction.guild.voice_client is None:
            if interaction.user.voice:
                await interaction.user.voice.channel.connect()
            else:
                return await interaction.response.send_message(
                    "You are not connected to a voice channel."
                )

        await interaction.response.defer()
        # Search for the top 5 results in the background
        search_task = asyncio.create_task(
            YTDLSource.from_url(query, loop=self.bot.loop, stream=True)
        )

        # While waiting for the search task to complete, let the bot process other commands
        player_results = await search_task

        if not player_results:
            return await interaction.followup.send("No results found for your query.")

        # Create an embed with the top 5 songs for the user to choose from
        # Create an embed with the top 5 songs
        embed = discord.Embed(
            title="Top 5 Songs for Your Search", color=discord.Color.blue()
        )
        reactions = ["1️⃣", "2️⃣", "3️⃣"]
        for idx, player in enumerate(player_results[:3], 1):
            embed.add_field(
                name=f"{reactions[idx - 1]} {player['title']}",
                value=f"[{player['webpage_url']}]",
                inline=False,
            )

        await interaction.followup.send(
            content="Please choose a song using the reactions", embed=embed
        )
        message = await interaction.original_response()
        # Add reactions for user selection
        for reaction in reactions[: len(player_results)]:
            await message.add_reaction(reaction)

        # Define a check function to ensure only the user who invoked the command can react
        def check(reaction, user):
            return user == interaction.user and str(reaction.emoji) in reactions

        # Wait for user response
        try:
            # msg = await self.bot.wait_for("message", check=check, timeout=30.0)
            # idx = int(msg.content) - 1
            # player = player_results[idx]

            reaction, user = await self.bot.wait_for(
                "reaction_add", timeout=60, check=check
            )
            selected_index = reactions.index(str(reaction.emoji))
            player = player_results[selected_index]  # Get the song dictionary

            # Create an FFmpegPCMAudio source from the selected video URL
            audio_source = discord.FFmpegPCMAudio(
                player["url"],
                **{
                    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
                    "options": "-vn",
                },
            )
            audio_source = discord.PCMVolumeTransformer(audio_source)
            audio_source.volume = 0.05  # Default volume set to 5%

            song_info = {
                "source": audio_source,
                "title": player["title"],
                "duration": player["duration"],
                "webpage_url": player["webpage_url"],
            }

            if interaction.guild.voice_client.is_playing():
                await interaction.followup.send(
                    f"{song_info['webpage_url']} was added to queue"
                )
                self.playlist[interaction.guild.id].append(song_info)
            else:
                try:
                    # If audio is already playing, add the song to the playlist instead of playing immediately
                    if interaction.guild.voice_client.is_playing():
                        await interaction.followup.send(
                            f"{song_info['webpage_url']} was added to queue"
                        )
                        self.playlist[interaction.guild.id].append(song_info)
                    else:
                        # Play the song immediately if nothing is playing
                        interaction.guild.voice_client.play(
                            song_info["source"],
                            after=lambda x=None: asyncio.run_coroutine_threadsafe(
                                self.check_queue(interaction), self.bot.loop
                            ),
                        )
                        self.playlist[interaction.guild.id] = []
                        self.current[interaction.guild.id] = song_info
                        await interaction.followup.send(
                            f"Now playing: {song_info['webpage_url']}"
                        )
                except Exception as e:
                    print(f"Error occurred during playback: {e}")
                    await interaction.followup.send(
                        "There was an error while playing the song."
                    )

        except asyncio.TimeoutError:
            await message.edit(
                content="You took too long to respond. Cancelling the song selection.",
                embed=None,
            )
            await self.check_queue(interaction)

    @app_commands.command(name="stop", description="disconnect the bot from the server")
    async def stop(self, interaction: discord.Interaction):
        if interaction.guild.voice_client:
            self.playlist.clear()
            self.current.clear()
            await interaction.guild.voice_client.disconnect()
            await interaction.response.send_message("Music stopped")
        else:
            await interaction.response.send_message("Not connected to a voice channel")

    @app_commands.command(name="volume", description="Change volume of bot")
    @app_commands.describe(volume="1-100% volume")
    async def volume(
        self, interaction: discord.Interaction, volume: app_commands.Range[int, 0, 100]
    ):
        if interaction.guild.voice_client is None:
            return await interaction.response.send_message(
                "Not connected to a voice channel."
            )
        # Adjust volume using PCMVolumeTransformer
        voice_client = interaction.guild.voice_client
        if voice_client.source:
            voice_client.source.volume = volume / 100
            await interaction.response.send_message(f"Changed volume to {volume}%")
        else:
            await interaction.response.send_message("No audio source playing")

    @app_commands.command(name="skip", description="Skips current song")
    async def skip(self, interaction: discord.Interaction):
        if interaction.guild.voice_client:
            if interaction.guild.voice_client.is_playing():
                await interaction.response.send_message("Song has been skipped")
                interaction.guild.voice_client.stop()
            else:
                await interaction.response.send_message("No songs playing")
        else:
            await interaction.response.send_message("Not connected to a voice channel")

    async def check_queue(self, interaction):
        # Check if there are songs left in the playlist
        if (
            interaction.guild.id in self.playlist
            and len(self.playlist[interaction.guild.id]) > 0
        ):
            # Pop the next song from the queue
            next_song = self.playlist[interaction.guild.id].pop(0)

            # Play the next song
            interaction.guild.voice_client.play(
                next_song["source"],
                after=lambda x=None: asyncio.run_coroutine_threadsafe(
                    self.check_queue(interaction), self.bot.loop
                ),
            )
            self.current[interaction.guild.id] = next_song
            await interaction.followup.send(
                f"Now playing next song: {next_song['title']}"
            )
        else:
            # If the playlist is empty, check if the bot is playing
            if not interaction.guild.voice_client.is_playing():
                await interaction.followup.send("No more songs in the queue.")
                # Only disconnect if not playing anything and no songs are left
                await interaction.guild.voice_client.disconnect()

    @app_commands.command(name="queue", description="shows the queue of songs")
    async def queue(self, interaction: discord.Interaction):
        songs = []
        embed = discord.Embed(title="Queue")
        if interaction.guild.id in self.playlist:
            if self.current.get(interaction.guild.id):
                minutes = self.current[interaction.guild.id]["duration"] // 60
                seconds = self.current[interaction.guild.id]["duration"] % 60
                duration = "%.2d:%.2d" % (minutes, seconds)
                embed.add_field(
                    name="Currently Playing",
                    value=f"[{self.current[interaction.guild.id]['title']}]({self.current[interaction.guild.id]['webpage_url']}) - Duration: {duration}",
                    inline=False,
                )
            if self.playlist[interaction.guild.id]:
                for song in self.playlist[interaction.guild.id]:
                    minutes = song["duration"] // 60
                    seconds = song["duration"] % 60
                    duration = "%.2d:%.2d" % (minutes, seconds)
                    songs.append(
                        f"[{song['title']}]({song['webpage_url']}) - Duration: {duration}"
                    )
                if songs:
                    embed.add_field(name="Upcoming", value="\n".join(songs))
        if not songs and not self.current:
            return await interaction.response.send_message("No Songs in Queue")
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Music(bot))
    print("Music is Loaded")
