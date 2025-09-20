import discord
from collections.abc import Callable, Awaitable
from typing import cast, TypeAlias

from filter_and_group import filter_and_group_items
from utils import fetch_channel_messages


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
    user_cmd = message.content.split()[1].lower()
    command = commands.get(user_cmd)
    if not command:
        await message.channel.send(f"Command '{user_cmd}' not found.")
        return
    if not command.__doc__:
        await message.channel.send(f"No documentation available for '{user_cmd}'.")
        return
    await message.channel.send(command.__doc__)


async def cmd_list(message: discord.Message) -> None:
    """
    List all grocery items.
    Accepts an optional 'store' argument to filter by store name.
    Accepts an optional 'group' argument to group items by section in the store.
    Example:
        `list` lists all items
        `list joes` lists items from store 'joes'
        `list joes group` lists items from store 'joes' grouped by section
    You must have a channel named 'grocery-list' and prefix items with the store name.
    Example item in grocery-list: "joes: joes O's"
    An LLM will be used to determine the section if 'group' is specified, unless the section is explicitly provided.
    You can provide the section explicitly in your item like so:
    > "joes: joes O's (cereal)"
    > "woodmans: milk (dairy)"
    In most cases the LLM should be able to figure it out on its own, but it is useful for niche items and stores with strange layouts.
    """
    try:
        items = await fetch_channel_messages(message, "grocery-list")
    except ValueError as e:
        await message.channel.send(str(e))
        return
    user_args = message.content.lower().split()[1:]
    is_grouped = False
    store_filter = None
    if "group" in user_args:
        # remove 'group' from args so order doesn't matter
        user_args.remove("group")
        is_grouped = True
    if len(user_args) and user_args[0]:
        store_filter = user_args[0]
    msg = await filter_and_group_items(items, store_filter, is_grouped)
    await message.channel.send(msg)
    return
