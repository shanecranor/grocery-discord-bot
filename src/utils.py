import discord
from typing import Dict, List, Tuple

from constants import LOG_CHANNEL_NAME


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


def create_section_view(
    section: str,
    items: List[str],
    name_to_msgs: Dict[str, List[discord.Message]],
    grocery_channel: discord.TextChannel,
) -> Tuple[str, discord.ui.View]:
    """Build the header text and a discord.ui.View of buttons for a section.
    - Truncation to 25 items (adds '(truncated)' to header)
    - Duplicate numbering suffix ' (n)'
    - Stable ordering of provided items
    - Button callback that deletes original message if unchanged and disables itself
    """
    view = discord.ui.View(timeout=600)
    truncated = False
    if len(items) > 25:
        items = items[:25]
        truncated = True
    dup_counts: Dict[str, int] = {}
    for item_name in items:
        base = item_name
        dup_counts[base] = dup_counts.get(base, 0) + 1
        shown = f"{base} ({dup_counts[base]})" if dup_counts[base] > 1 else base
        safe_label = (shown[:80] + "…") if len(shown) > 81 else shown
        source_list = name_to_msgs.get(base, [])
        if not source_list:
            continue
        src_msg = source_list.pop(0)

        btn = discord.ui.Button(  # type: ignore
            label=safe_label,
            style=discord.ButtonStyle.secondary,
            custom_id=f"groce:{src_msg.id}",
        )  # type: ignore[call-arg]

        async def button_callback(
            interaction: discord.Interaction,
            *,
            _src_msg: discord.Message = src_msg,
            _shown: str = shown,
            _btn: discord.ui.Button = btn,  # type: ignore[type-arg]
        ) -> None:  # pragma: no cover - network interaction
            channel = grocery_channel
            if not channel:
                await interaction.response.send_message(
                    "Channel missing.", ephemeral=True
                )
                return
            try:
                target = await channel.fetch_message(_src_msg.id)
                if target.content == _src_msg.content:
                    await target.delete()
                    try:
                        _btn.disabled = True
                        if interaction.message:
                            await interaction.message.edit(view=view)  # type: ignore[arg-type]
                    except Exception:
                        pass
                    await interaction.response.send_message(
                        f"Removed: {_shown}", ephemeral=True
                    )
                    try:  # pragma: no cover - network interaction
                        if interaction.guild:
                            log_channel = next(
                                (
                                    c
                                    for c in interaction.guild.text_channels
                                    if c.name == LOG_CHANNEL_NAME
                                ),
                                None,
                            )
                            if log_channel:
                                await log_channel.send(
                                    f"Item removed via button: '{_src_msg.content}' (shown as '{_shown}') by <@{interaction.user.id}>",
                                    allowed_mentions=discord.AllowedMentions.none(),
                                )
                    except Exception:
                        pass
                else:
                    await interaction.response.send_message(
                        "Item changed; not removed.", ephemeral=True
                    )
            except Exception:
                await interaction.response.send_message(
                    "Original not found.", ephemeral=True
                )

        btn.callback = button_callback  # type: ignore
        view.add_item(btn)  # type: ignore[arg-type]

    header = f"**{section}**" + (" (truncated)" if truncated else "")
    return header, view
