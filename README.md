# Grocery Discord Bot

This bot reacts to every new message in a server with a ❌ emoji (only in channels containing the string "groce"). When a user reacts with ❌, the bot deletes the message and sends a notification to a channel named "grocery-log" in the same server if it exists.

## Setup

1. Install dependencies:

   ```bash
   uv sync
   ```

2. Create a Discord bot and copy its token.

3. Provide the token via the `DISCORD_TOKEN` environment variable:

   ```bash
   export DISCORD_TOKEN="your token"
   ```

4. Run the bot:

   ```bash
   uv run src/main.py
   ```
