# Grocery Discord Bot

This bot reacts to every new message in a server with a ❌ emoji. If anyone other than the
message author reacts with the same emoji, the bot deletes the message.

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
   python main.py
   ```

