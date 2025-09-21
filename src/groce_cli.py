import discord
from collections.abc import Callable, Awaitable
from typing import cast, TypeAlias, Dict, List, Tuple

from constants import GROCE_CHANNEL_NAME, AISLES
from classifier import classify_items


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
    """Render grocery items as interactive buttons grouped by aisle.

    Usage: list [store]
    - Optionally provide a store prefix to filter (e.g. `list joes`).
    - Each aisle with at least one item becomes its own message.
    - Clicking a button deletes the original grocery list message for that item.
    - Explicit sections provided via '(Section)' suffix are used; others are classified.
    Notes:
      * Max 25 buttons per aisle message (Discord limit). Extra items are truncated.
      * Duplicate items (exact same original message content) each get their own button label with a counter suffix.
    """
    if not message.guild:
        await message.channel.send("Command must be used in a guild.")
        return
    # Fetch original message objects (need them later for deletion)
    grocery_channel = None
    for ch in message.guild.text_channels:
        if ch.name == GROCE_CHANNEL_NAME:
            grocery_channel = ch
            break
    if not grocery_channel:
        await message.channel.send(
            f"Channel '{GROCE_CHANNEL_NAME}' not found. Create it first."
        )
        return
    # Retrieve messages (oldest first) so ordering is stable
    original_msgs: List[discord.Message] = [
        m
        async for m in grocery_channel.history(limit=400, oldest_first=True)
        if m.content.strip()
    ]
    if not original_msgs:
        await message.channel.send("No grocery items found.")
        return
    user_args = message.content.split()[1:]
    store_filter = user_args[0].lower() if user_args else None

    # Filter by store prefix if provided
    filtered_msgs: List[discord.Message] = []
    if store_filter:
        prefix = store_filter + ":"
        for m in original_msgs:
            if m.content.lower().startswith(prefix):
                filtered_msgs.append(m)
        if not filtered_msgs:
            await message.channel.send(f"No items found for store '{store_filter}'.")
            return
    else:
        filtered_msgs = original_msgs

    # Parse explicit sections & collect unclassified
    section_map: Dict[str, List[Tuple[str, discord.Message]]] = {}
    to_classify: List[discord.Message] = []
    for m in filtered_msgs:
        txt = m.content.strip()
        # Remove store prefix for display
        display = txt
        if store_filter and display.lower().startswith(store_filter + ":"):
            display = display[len(store_filter) + 1 :].strip()
        if "(" in txt and txt.endswith(")"):
            section = txt[txt.rfind("(") + 1 : -1].strip()
            name = display[: display.rfind("(")].strip()
            if section:
                section_map.setdefault(section, []).append((name, m))
                continue
        to_classify.append(m)

    # Classify remaining items with LLM for sections
    if to_classify:
        classify_inputs: List[str] = []
        for m in to_classify:
            txt = m.content.strip()
            if store_filter and txt.lower().startswith(store_filter + ":"):
                txt = txt[len(store_filter) + 1 :].strip()
            classify_inputs.append(txt)
        try:
            classified = await classify_items(classify_inputs)
            items_out = classified.get("items", [])  # type: ignore
            for row, m in zip(items_out, to_classify):
                section = row.get("section", "Misc")
                item_name = row.get("item", m.content)
                section_map.setdefault(section, []).append((item_name, m))
        except Exception as e:  # Fallback: put everything into Misc
            for m in to_classify:
                section_map.setdefault("Misc", []).append((m.content, m))
            await message.channel.send(f"Classification error, fallback used: {e}")

    # Order sections by AISLES order, with unknowns last
    aisle_order = list(AISLES.keys())
    ordered_sections = sorted(
        section_map.keys(),
        key=lambda s: aisle_order.index(s) if s in AISLES else len(AISLES),
    )

    # De-duplicate labels if duplicates exist in same section
    for section, items in section_map.items():
        name_counts: Dict[str, int] = {}
        for idx, (name, m) in enumerate(items):
            c = name_counts.get(name, 0) + 1
            name_counts[name] = c
            if c > 1:
                # Append counter for display only
                items[idx] = (f"{name} ({c})", m)

    # Send one message per section with buttons
    for section in ordered_sections:
        item_pairs = section_map[section]
        if not item_pairs:
            continue
        view = discord.ui.View(timeout=600)
        truncated = False
        if len(item_pairs) > 25:
            item_pairs = item_pairs[:25]
            truncated = True

        for display_name, original_msg in item_pairs:
            safe_label = (
                (display_name[:80] + "…") if len(display_name) > 81 else display_name
            )

            # Factory to bind current values
            def make_callback(
                *,
                msg_id: int,
                msg_content: str,
                shown_name: str,
            ):
                async def _cb(interaction: discord.Interaction) -> None:
                    channel = grocery_channel
                    if not channel:
                        await interaction.response.send_message(
                            "Grocery channel missing.", ephemeral=True
                        )
                        return
                    try:
                        target = await channel.fetch_message(msg_id)
                        if target.content == msg_content:
                            await target.delete()
                            await interaction.response.send_message(
                                f"Removed: {shown_name}", ephemeral=True
                            )
                        else:
                            await interaction.response.send_message(
                                "Item content changed; not removed.",
                                ephemeral=True,
                            )
                    except Exception:
                        await interaction.response.send_message(
                            "Original message not found.", ephemeral=True
                        )

                return _cb

            btn = discord.ui.Button(
                label=safe_label,
                style=discord.ButtonStyle.secondary,
                custom_id=f"groce:{original_msg.id}",  # stable unique id per item
            )  # type: ignore[call-arg]
            btn.callback = make_callback(
                msg_id=original_msg.id,
                msg_content=original_msg.content,
                shown_name=display_name,
            )  # type: ignore
            view.add_item(btn)  # type: ignore[arg-type]

        header = f"**{section}**" + (" (truncated)" if truncated else "")
        await message.channel.send(header, view=view)
    return
