"""Discord bot that reacts to new messages with ❌ and deletes them on reaction."""

from __future__ import annotations

import os
from dotenv import load_dotenv

import discord

load_dotenv()


intents = discord.Intents.default()
intents.message_content = True

bot = discord.Client(intents=intents)


@bot.event
async def on_message(message: discord.Message) -> None:
    """Add a ❌ reaction to every new message from users."""
    if message.author.bot:
        return
    channel = message.channel
    if not isinstance(channel, discord.TextChannel):
        print("Message not in a text channel, ignoring.")
        return
    if "groce" not in channel.name.lower():
        print("Channel name does not contain 'groce', ignoring.")
        return
    await message.add_reaction("❌")


@bot.event
async def on_raw_reaction_add(reaction: discord.RawReactionActionEvent) -> None:
    print(
        "Reaction added:",
        reaction.emoji,
        reaction.type,
        "by",
        reaction.user_id,
    )
    """Delete athe message when a different user reacts with ❌."""
    if reaction.member and reaction.member.bot:
        print("Reaction by bot, ignoring.")
        return
    if str(reaction.emoji) == "❌":
        # delete the message that was reacted to
        channel = bot.get_channel(reaction.channel_id)
        if not isinstance(channel, discord.TextChannel):
            print("Channel not found or not a text channel.")
            return
        message = await channel.fetch_message(reaction.message_id)
        await message.delete()

        # log the deletion in a specific channel
        if not message.guild:
            print("Message not from a guild.")
            return
        log_channel = None
        for channel_item in message.guild.text_channels:
            if channel_item.name == "grocery-log":
                log_channel = channel_item
                break
        if not log_channel:
            print("Log channel not found.")
            return
        await log_channel.send(
            f"Item deleted: '{message.content}' in <#{channel.id}> by <@{reaction.user_id}>",
            allowed_mentions=discord.AllowedMentions.none(),
        )


def main() -> None:
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_TOKEN environment variable not set")
    bot.run(token)


if __name__ == "__main__":
    main()
