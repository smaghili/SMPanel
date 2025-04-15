#!/bin/bash

# Print header
echo "=== Starting SMPanel Bot with Webhook ==="

# Check if localtunnel is installed
if ! command -v lt &> /dev/null; then
    echo "Localtunnel not found. Installing..."
    npm install -g localtunnel
    if [ $? -ne 0 ]; then
        echo "Failed to install localtunnel. Make sure npm is installed."
        echo "Try: sudo apt-get install npm"
        exit 1
    fi
    echo "Localtunnel installed successfully."
else
    echo "Localtunnel is already installed."
fi

# Stop any running instances
echo "Stopping previous instances..."
pkill -f "python3 src/bot/index.py" || true
pkill -f "lt --port 8443" || true
sleep 2

# Start localtunnel in background and capture output
echo "Starting localtunnel..."
lt_output=$(mktemp)
lt --port 8443 > "$lt_output" 2>&1 &
LT_PID=$!

# Wait for localtunnel to initialize and get URL
echo "Waiting for tunnel URL..."
sleep 3

# Extract the tunnel URL
max_attempts=10
attempt=1
tunnel_url=""

while [ -z "$tunnel_url" ] && [ $attempt -le $max_attempts ]; do
    echo "Attempt $attempt to get URL..."
    tunnel_url=$(grep -o "https://[^[:space:]]*\.loca\.lt" "$lt_output" | head -n 1)
    
    if [ -z "$tunnel_url" ]; then
        sleep 2
        attempt=$((attempt + 1))
    fi
done

if [ -z "$tunnel_url" ]; then
    echo "Failed to get tunnel URL after $max_attempts attempts"
    echo "Check output file: $lt_output"
    exit 1
fi

echo "Tunnel URL: $tunnel_url"

# Update .env file with new URL
echo "Updating .env with new URL..."
sed -i "s|WEBHOOK_URL=.*|WEBHOOK_URL=$tunnel_url|g" .env

# Start the bot
echo "Starting the bot..."
source venv/bin/activate
python3 src/bot/index.py

echo "✅ Bot started successfully with webhook!"
echo "Tunnel URL: $tunnel_url"
echo "Localtunnel PID: $LT_PID"
echo "To stop the bot, run: ./stop_with_webhook.sh" 