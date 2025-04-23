from typing import Optional

import discord


def create_embed(
    title: str,
    description: str,
    color: discord.Color = discord.Color.blue(),
    fields: Optional[list[tuple[str, str, bool]]] = None,
    footer: Optional[str] = None,
    thumbnail: Optional[str] = None,
    image: Optional[str] = None,
) -> discord.Embed:
    """
    Helper function to create a Discord embed.

    :param title: The title of the embed.
    :param description: The main description.
    :param color: The color of the embed.
    :param fields: A list of tuples (name, value, inline).
    :param footer: Footer text.
    :param thumbnail: URL for the thumbnail image.
    :param image: URL for the embed image.
    :return: A discord.Embed object.
    """
    embed = discord.Embed(title=title, description=description, color=color)

    if fields:
        for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=inline)

    if footer:
        embed.set_footer(text=footer)

    if thumbnail:
        embed.set_thumbnail(url=thumbnail)

    if image:
        embed.set_image(url=image)

    return embed
