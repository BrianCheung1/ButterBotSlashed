import asyncio
import os
from datetime import datetime
from typing import Optional

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from transformers import pipeline


class Moderation(commands.Cog):
    """Moderation Features"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        # Load the DialoGPT model from Hugging Face
        self.generator = pipeline("text-generation", model="gpt2")

    @app_commands.command(
        name="purge",
        description="Deletes messages - 100 messages max, less than 14 day old messages",
    )
    @app_commands.describe(
        amount="amount of messages to purge default 5, min - 1, max - 100"
    )
    @app_commands.checks.has_permissions(moderate_members=True)
    async def purge(
        self,
        interaction: discord.Interaction,
        amount: Optional[app_commands.Range[int, 1, 100]] = 5,
    ):
        await interaction.response.defer()
        messages = [
            message async for message in interaction.channel.history(limit=amount + 1)
        ]
        if len(messages) >= 1:
            messages.pop(0)
        await interaction.channel.delete_messages(messages)
        await interaction.followup.send(f"{amount} messages deleted")

    @app_commands.command(
        name="role",
        description="Give a member a role or delete the role if they have it",
    )
    @app_commands.describe(
        member="member you want to give a role to",
        role="role you want to give to a member",
    )
    @app_commands.checks.has_permissions(moderate_members=True)
    async def role(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        role: discord.Role,
    ):
        if role in member.roles:
            await member.remove_roles(role)
            await interaction.response.send_message(
                f"{role.mention} role removed from {member.mention}"
            )
        else:
            await member.add_roles(role)
            await interaction.response.send_message(
                f"{role.mention} role given to {member.mention}"
            )

    @app_commands.command(
        name="mute", description="Mutes a member in the voice channel"
    )
    @app_commands.checks.has_permissions(moderate_members=True)
    async def mute(self, interaction: discord.Interaction, member: discord.Member):
        await member.edit(mute=True)
        await interaction.response.send_message(f"{member.mention} has been muted")

    @app_commands.command(
        name="unmute", description="Unmutes a member in the voice channel"
    )
    @app_commands.checks.has_permissions(moderate_members=True)
    async def unmute(self, interaction: discord.Interaction, member: discord.Member):
        await member.edit(mute=False)
        await interaction.response.send_message(f"{member.mention} has been unmuted")

    @app_commands.command(
        name="self_role",
        description="Creates an embed that allows other use to self-role",
    )
    @app_commands.describe(role="Role for other users to give themselves")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def self_role(self, interaction: discord.Interaction, role: discord.Role):
        embed = discord.Embed()
        embed.add_field(name="Role", value=f"{role.mention}")
        view = SelfRoleButton(role)
        await interaction.response.send_message(embed=embed, view=view)

    @commands.Cog.listener()
    async def on_message(self, message):
        # if the author of a message is a bot stop
        if message.author.bot:
            return

        # Check if the bot was mentioned
        if self.bot.user in message.mentions:
            # Remove mention from the message content
            user_input = message.content.replace(f"<@{self.bot.user.id}>", "").strip()
            if user_input:
                # Generate an AI response
                generating_message = await message.reply("Generating response...")
                response = await self.generate_ai_response(user_input)
                await generating_message.edit(content=response)
            else:
                await message.reply(
                    "Hello! Mention me with a message, and I'll respond!"
                )
        print(
            f'[{str(message.guild).title()}][{str(message.channel).title()}][{datetime.now().strftime("%I:%M:%S:%p")}] {message.author}: {message.content}'
        )

    # Generate an AI response using Cloudflare Worker AI API asynchronously
    async def generate_ai_response(self, user_input: str) -> str:
        WORKERS_ACCOUNT_ID = os.getenv("WORKERS_ACCOUNT_ID")
        API_BASE_URL = f"https://api.cloudflare.com/client/v4/accounts/{WORKERS_ACCOUNT_ID}/ai/run/"
        WORKERS_API_KEY = os.getenv("WORKERS_API_KEY")
        headers = {"Authorization": f"Bearer {WORKERS_API_KEY}"}

        async with aiohttp.ClientSession() as session:
            input_data = {
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a passive-aggressive discord bot that tries to answer questions or prompts",
                    },
                    {"role": "user", "content": user_input},
                ]
            }
            retries = 3
            for attempt in range(retries):
                try:
                    async with session.post(
                        f"{API_BASE_URL}@cf/meta/llama-3-8b-instruct",
                        json=input_data,
                        headers=headers,
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            return data.get("result", {}).get(
                                "response", "Sorry, I couldn't generate a response."
                            )
                        else:
                            return "Sorry, there was an error with the AI request."
                except asyncio.TimeoutError:
                    if attempt < retries - 1:
                        await asyncio.sleep(2)  # Wait before retrying
                    else:
                        return "Sorry, the request timed out after multiple attempts."
                except Exception as e:
                    return f"An error occurred: {str(e)}"


class SelfRoleButton(discord.ui.View):
    def __init__(self, role: discord.Role):
        super().__init__(timeout=None)
        self.role = role

    @discord.ui.button(label="Add Role", style=discord.ButtonStyle.red)
    async def add_role(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.user.add_roles(self.role)
        await interaction.response.send_message(
            content=f"{self.role.mention} added", ephemeral=True
        )

    @discord.ui.button(label="Remove Role", style=discord.ButtonStyle.red)
    async def remove_role(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.user.remove_roles(self.role)
        await interaction.response.send_message(
            content=f"{self.role.mention} Removed", ephemeral=True
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Moderation(bot))
    print("Moderation is Loaded")
