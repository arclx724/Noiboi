#!/bin/bash
echo "Stopping Bot..."
pkill -f main.py

echo "Pulling Updates..."
git pull

echo "Starting Bot..."
nohup python3 main.py &

echo "Bot Updated & Started! Showing logs..."
tail -f nohup.out
