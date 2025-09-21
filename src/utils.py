import discord


async def fetch_channel_messages(
    message: discord.Message, channel_name: str
) -> list[str]:
    """Fetch grocery items from the specified channel."""
    target_channel = None
    if not message.guild:
        raise ValueError("Message not from a guild.")
    for channel_item in message.guild.text_channels:
        if channel_item.name == channel_name:
            target_channel = channel_item
            break
    print(f"{channel_name} channel:", target_channel)
    if not target_channel:
        raise ValueError(
            f"{channel_name} channel not found. Please create a channel with that exact name."
        )
    messages = [m async for m in target_channel.history(limit=100, oldest_first=True)]
    if not messages:
        raise ValueError(f"No messages found in {channel_name} channel.")
    return [m.content for m in messages]
