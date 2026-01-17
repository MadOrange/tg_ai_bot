#!/bin/bash
cd /home/your_user/tg_ai_bot
while true; do
    echo "$(date): Start the Telegram-AI bot"
    python3 tg_bot_v1.5.0.py
    echo "$(date): Bot is stoped, restartint in 10 seconds..."
    sleep 10
done