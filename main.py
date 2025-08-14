"""Discord bot that reacts to new messages with ❌ and deletes them on reaction."""

from __future__ import annotations

import os

import discord


intents = discord.Intents.default()
intents.message_content = True

bot = discord.Client(intents=intents)


@bot.event
async def on_message(message: discord.Message) -> None:
    """Add a ❌ reaction to every new message from users."""
    if message.author.bot:
        return
    await message.add_reaction("❌")


@bot.event
async def on_reaction_add(reaction: discord.Reaction, user: discord.abc.User) -> None:
    """Delete the message when a different user reacts with ❌."""
    if user.bot:
        return

    if reaction.emoji == "❌" and reaction.message.author != user:
        await reaction.message.delete()


def main() -> None:
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_TOKEN environment variable not set")
    bot.run(token)


if __name__ == "__main__":
    main()

