import discord
from collections.abc import Callable, Awaitable
from typing import cast, TypeAlias


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
        await command(message)
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
    """List all grocery items. Placeholder implementation."""
    # This is a placeholder. In a real implementation, this would fetch items from a database or other storage.
    items = ["Apples", "Bananas", "Carrots"]
    if items:
        await message.channel.send(
            "Grocery List:\n" + "\n".join(f"- {item}" for item in items)
        )
    else:
        await message.channel.send("The grocery list is currently empty.")
    return
