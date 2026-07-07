#!/bin/bash

# Define the path to the Python script and the log file
APP_DIR="/home/sepenet/AlbumsAventuresBE"
APP_SCRIPT="AlbumsAventures-BE.py"
LOG_FILE="AlbumsAventures-BE.log"

# Navigate to the application directory
cd "$APP_DIR" || exit 1

# Find and kill the running process of the Python script, it is expected to be automatically restarted by the systemctl service setup
sudo systemctl restart AlbumsPhotos-BE.service
# pkill -f "$APP_SCRIPT"

# Wait for a moment to ensure the process is terminated
# sleep 2

# # Restart the Python script and redirect output to the log file
# nohup python3 "$APP_SCRIPT" > "$LOG_FILE" 2>&1 &

# echo "Service restarted successfully."