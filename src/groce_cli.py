import discord
from collections.abc import Callable, Awaitable
from typing import cast, TypeAlias, Dict, List

from constants import GROCE_CHANNEL_NAME, AISLES
from filter_and_group import filter_and_group_items


CommandFunc: TypeAlias = Callable[[discord.Message], Awaitable[None]]


def get_commands() -> dict[str, CommandFunc]:
    """Return a dictionary of command names to functions.
    Scans globals for coroutine functions whose names start with cmd_.
    """
    commands = {
        func.__name__[4:]: cast(CommandFunc, func)
        for func in globals().values()
        if callable(func) and func.__name__.startswith("cmd_")
    }
    return commands


async def handle_cli_message(message: discord.Message) -> None:
    """Handle a message in a groce-cli channel."""
    print("Handling groce-cli message:", message.content)
    commands = get_commands()
    print("Available commands:", commands.keys())
    user_cmd = message.content.split()[0].lower()
    command = commands.get(user_cmd)
    if command:
        try:
            await command(message)
        except Exception as e:
            print("Error occurred while executing command:", e)
            await message.channel.send(f"Error executing command '{user_cmd}': {e}")
    else:
        await message.channel.send(
            "Unknown command. Type 'help' for a list of commands."
        )


async def cmd_ping(message: discord.Message) -> None:
    await message.channel.send("Pong!")
    return


async def cmd_help(message: discord.Message) -> None:
    """Respond with a list of available commands. find out by looping through functions that start with cmd_"""
    commands = get_commands()
    command_names = sorted(commands.keys())
    await message.channel.send(f"Available commands: {', '.join(command_names)}")
    return


async def cmd_man(message: discord.Message) -> None:
    """return the docstring of a given command"""
    commands = get_commands()
    parts = message.content.split()
    if len(parts) < 2:
        await message.channel.send("Usage: man <command>")
        return
    user_cmd = parts[1].lower()
    command = commands.get(user_cmd)
    if not command:
        await message.channel.send(f"Command '{user_cmd}' not found.")
        return
    if not command.__doc__:
        await message.channel.send(f"No documentation available for '{user_cmd}'.")
        return
    await message.channel.send(command.__doc__)


async def cmd_clear(message: discord.Message) -> None:
    """
    clear all items in the CLI channel
    """
    # Restrict to text channels for type safety
    if isinstance(message.channel, discord.TextChannel):
        await message.channel.purge()
    else:
        await message.channel.send("Cannot purge messages in this channel type.")
    await message.channel.send("Cleared all messages in this channel.")
    return


async def cmd_list(message: discord.Message) -> None:
    """List grocery items.

    Default: ungrouped plain text list.
    Add 'group' argument to render grouped interactive buttons (one message per aisle).
    Optionally specify store before 'group'. Examples:
      list
      list joes
      list joes group
      list group
    """
    if not message.guild:
        await message.channel.send("Command must be used in a guild.")
        return
    grocery_channel: discord.TextChannel | None = None
    for ch in message.guild.text_channels:
        if ch.name == GROCE_CHANNEL_NAME:
            grocery_channel = ch
            break
    if not grocery_channel:
        await message.channel.send(f"Channel '{GROCE_CHANNEL_NAME}' not found.")
        return
    original_msgs: List[discord.Message] = [
        m
        async for m in grocery_channel.history(limit=400, oldest_first=True)
        if m.content.strip()
    ]
    if not original_msgs:
        await message.channel.send("No grocery items found.")
        return
    args = message.content.split()[1:]
    is_grouped = False
    if any(a.lower() == "group" for a in args):
        is_grouped = True
        args = [a for a in args if a.lower() != "group"]
    store_filter = args[0].lower() if args else None

    item_texts = [m.content for m in original_msgs]
    if not is_grouped:
        text = await filter_and_group_items(
            item_texts, store_filter, False, enable_llm=False
        )
        await message.channel.send(text or "(empty)")
        return

    grouped_text, raw_mapping = await filter_and_group_items(  # type: ignore
        item_texts, store_filter, True, enable_llm=True, return_mapping=True
    )
    from typing import cast as _cast

    mapping = _cast(Dict[str, List[str]], raw_mapping)

    # Build display-name -> list of original messages for duplicate handling
    def strip_store_prefix(raw: str) -> str:
        if store_filter and raw.lower().startswith(store_filter + ":"):
            return raw[len(store_filter) + 1 :].strip()
        return raw

    def base_display(raw: str) -> str:
        txt = strip_store_prefix(raw)
        if "(" in txt and txt.endswith(")"):
            return txt[: txt.rfind("(")].strip()
        return txt

    name_to_msgs: Dict[str, List[discord.Message]] = {}
    for m in original_msgs:
        key = base_display(m.content)
        name_to_msgs.setdefault(key, []).append(m)

    aisle_order = list(AISLES.keys())
    ordered_sections: List[str] = sorted(
        mapping.keys(),
        key=lambda s: aisle_order.index(s) if s in AISLES else len(AISLES),
    )

    for section in ordered_sections:
        items = mapping[section]
        if not items:
            continue
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

            def make_cb(msg_id: int, msg_content: str, shown_label: str):
                async def _cb(interaction: discord.Interaction) -> None:
                    channel = grocery_channel
                    if not channel:
                        await interaction.response.send_message(
                            "Channel missing.", ephemeral=True
                        )
                        return
                    try:
                        target = await channel.fetch_message(msg_id)
                        if target.content == msg_content:
                            await target.delete()
                            await interaction.response.send_message(
                                f"Removed: {shown_label}", ephemeral=True
                            )
                        else:
                            await interaction.response.send_message(
                                "Item changed; not removed.", ephemeral=True
                            )
                    except Exception:
                        await interaction.response.send_message(
                            "Original not found.", ephemeral=True
                        )

                return _cb

            btn = discord.ui.Button(  # type: ignore
                label=safe_label,
                style=discord.ButtonStyle.secondary,
                custom_id=f"groce:{src_msg.id}",
            )  # type: ignore[call-arg]
            btn.callback = make_cb(
                msg_id=src_msg.id,
                msg_content=src_msg.content,
                shown_label=shown,
            )  # type: ignore
            view.add_item(btn)  # type: ignore[arg-type]

        header = f"**{section}**" + (" (truncated)" if truncated else "")
        await message.channel.send(header, view=view)
    return
