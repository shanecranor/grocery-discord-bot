#!/bin/bash

# Kill any existing bot process when the script is terminated
trap 'kill $(jobs -p)' EXIT

while true; do
    uv run src/main.py &
    BOT_PID=$!
    
    # Wait for changes in the src directory
    fswatch -1 src/
    
    # Kill the previous bot process
    kill $BOT_PID
    wait $BOT_PID 2>/dev/null
done
