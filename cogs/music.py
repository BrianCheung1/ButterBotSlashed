from bs4 import BeautifulSoup
from datetime import datetime
from discord import app_commands
from discord.ext import commands, tasks
from dotenv import load_dotenv
from typing import Optional
import discord
import os
import asyncio
import youtube_dl

load_dotenv()
list_of_guilds = os.getenv("GUILDS").split(",")
MY_GUILDS = [discord.Object(id=int(guild)) for guild in list_of_guilds]


youtube_dl.utils.bug_reports_message = lambda: ""

ytdl_format_options = {
    "format": "bestaudio/best",
    "outtmpl": "%(extractor)s-%(id)s-%(title)s.%(ext)s",
    "restrictfilenames": True,
    "noplaylist": True,
    "nocheckcertificate": True,
    "ignoreerrors": False,
    "logtostderr": False,
    "quiet": True,
    "no_warnings": True,
    "default_search": "auto",
    "source_address": "0.0.0.0",  # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    "options": "-vn",
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.05):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get("title")
        self.url = data.get("url")
        self.webpage_url = data.get("webpage_url")
        self.duration = data.get("duration")

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(
            None, lambda: ytdl.extract_info(url, download=not stream)
        )

        if "entries" in data:
            # take first item from a playlist
            data = data["entries"][0]
        filename = data["url"] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)


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
    async def play(
        self,
        interaction: discord.Interaction,
        query: str,
    ):
        await interaction.response.defer()
        if interaction.guild.voice_client is None:
            if interaction.user.voice:
                await interaction.user.voice.channel.connect()
            else:
                await interaction.response.send_message(
                    "You are not connected to a voice channel."
                )
        else:
            await interaction.guild.voice_client.move_to(interaction.user.voice.channel)

        player = await YTDLSource.from_url(query, loop=self.bot.loop, stream=True)
        if interaction.guild.voice_client.is_playing():
            await interaction.followup.send(f"{player.webpage_url} was added to queue")
            self.playlist[interaction.guild.id].append(player)
        else:
            interaction.guild.voice_client.play(
                player,
                after=lambda x=None: asyncio.run_coroutine_threadsafe(
                    self.check_queue(interaction), self.bot.loop
                ),
            )
            self.playlist[interaction.guild.id] = []
            self.current[interaction.guild.id] = player
            await interaction.followup.send(f"Now playing: {player.webpage_url}")

    @app_commands.command(name="volume", description="Change volume of bot")
    @app_commands.describe(volume="1-100% volume")
    async def volume(
        self, interaction: discord.Interaction, volume: app_commands.Range[int, 0, 100]
    ):
        if interaction.guild.voice_client is None:
            return await interaction.response.send_message(
                "Not connected to a voice channel."
            )
        interaction.guild.voice_client.source.volume = volume / 100
        await interaction.response.send_message(f"Changed volume to {volume}%")

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

    @app_commands.command(name="stop", description="disconnect the bot from the server")
    async def stop(self, interaction: discord.Interaction):
        if interaction.guild.voice_client:
            self.playlist.clear()
            self.current.clear()
            await interaction.guild.voice_client.disconnect()
            await interaction.response.send_message("Music stopped")
        else:
            await interaction.response.send_message("Not connected to a voice channel")

    @app_commands.command(name="queue", description="shows the queue of songs")
    async def queue(self, interaction: discord.Interaction):
        songs = []
        embed = discord.Embed(title="Queue")
        if interaction.guild.id in self.playlist:
            if self.current[interaction.guild.id]:
                minutes = self.current[interaction.guild.id].duration // 60
                seconds = self.current[interaction.guild.id].duration % 60
                duration = "%.2d:%.2d" % (minutes, seconds)
                embed.add_field(
                    name="Currently Playing",
                    value=f"[{self.current[interaction.guild.id].title}]({self.current[interaction.guild.id].webpage_url}) - Duration: {duration}",
                    inline=False,
                )
            if self.playlist[interaction.guild.id]:
                for song in self.playlist[interaction.guild.id]:
                    minutes = song.duration // 60
                    seconds = song.duration % 60
                    duration = "%.2d:%.2d" % (minutes, seconds)
                    songs.append(
                        f"[{song.title}]({song.webpage_url}) - Duration: {duration}"
                    )
                if songs:
                    embed.add_field(name="Upcoming", value="\n".join(songs))
        if not songs and not self.current:
            return await interaction.response.send_message("No Songs in Queue")
        await interaction.response.send_message(embed=embed)

    async def check_queue(self, interaction):
        if interaction.guild_id in self.playlist:
            if len(self.playlist[interaction.guild_id]) != 0:
                song = self.playlist[interaction.guild_id].pop(0)
                self.current[interaction.guild.id] = song
                interaction.guild.voice_client.play(
                    song,
                    after=lambda x=None: asyncio.run_coroutine_threadsafe(
                        self.check_queue(interaction), self.bot.loop
                    ),
                )

                await interaction.followup.send(f"{song.title} is now playing")
            else:
                await interaction.followup.send("All songs have finished")
                await interaction.guild.voice_client.disconnect()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Music(bot), guilds=MY_GUILDS)
    print("Music is Loaded")
