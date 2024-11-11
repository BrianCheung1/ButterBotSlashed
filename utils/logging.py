import logging

import discord
from discord.ext import commands

# Set up a logger (if not already done)
logger = logging.getLogger(__name__)


async def send_error_to_support_channel(
    bot: commands.Bot,
    target_guild_id: int,
    target_channel_id: int,
    error: str,
    interaction: discord.Interaction,
):
    """
    Sends error details to a support channel in the specified guild.
    If no admin user is provided, it logs an error for missing admin.
    """
    admin_user_id = 1047615361886982235
    admin_user = bot.get_user(admin_user_id)
    target_guild = bot.get_guild(target_guild_id)
    if target_guild:
        target_channel = target_guild.get_channel(target_channel_id)
        if target_channel:
            # Send the error details to the support channel
            await target_channel.send(
                f"Error occurred in {interaction.guild.name} ({interaction.guild.id}):\n"
                f"Command: `/{interaction.command.name}` triggered by {interaction.user.name} ({interaction.user.id})\n"
            )
            # Ping the admin user for feedback
            if admin_user:
                await target_channel.send(
                    f"<@{admin_user_id}>, Please check the error!"
                )
            else:
                logger.error(f"Admin user {admin_user_id} not found.")
        else:
            logger.error(
                f"Channel {target_channel_id} not found in guild {target_guild_id}."
            )
    else:
        logger.error(f"Guild {target_guild_id} not found.")


async def send_commands_to_support_channel(
    bot: commands.Bot,
    target_guild_id: int,
    target_channel_id: int,
    interaction: discord.Interaction,
):
    """
    Sends error details to a support channel in the specified guild.
    If no admin user is provided, it logs an error for missing admin.
    """
    admin_user_id = 1047615361886982235
    admin_user = bot.get_user(admin_user_id)
    target_guild = bot.get_guild(target_guild_id)
    if target_guild:
        target_channel = target_guild.get_channel(target_channel_id)
        if target_channel:
            # Send the error details to the support channel
            await target_channel.send(
                f"Error occurred in {interaction.guild.name} ({interaction.guild.id}):\n"
                f"Command: `/{interaction.command.name}` triggered by {interaction.user.name} ({interaction.user.id})\n"
            )
            # Ping the admin user for feedback
            if admin_user:
                await target_channel.send(
                    f"<@{admin_user_id}>, Please check the error!"
                )
            else:
                logger.error(f"Admin user {admin_user_id} not found.")
        else:
            logger.error(
                f"Channel {target_channel_id} not found in guild {target_guild_id}."
            )
    else:
        logger.error(f"Guild {target_guild_id} not found.")
