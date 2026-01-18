#!/bin/bash
cd /home/ior4nge/tg_ai_bot
BOT_FILE="tg_bot_v1.5.0.py"


# Trap signal for correct ending
trap 'echo "Recived stop signal"; exit 0' TERM INT
trap '' HUP  # Ignoring HUP (bay the way)

while true; do
    echo "[$(date)] 🚀 Starting AI-bot..."
    
    # Start without NOHUP inside!
    python3 -u "$BOT_FILE" >> bot_full.log 2>&1 &
    BOT_PID=$!
    echo $BOT_PID > bot.pid
    
    echo "[$(date)] Bot is running (PID: $BOT_PID)"
    
    # Ждем завершения бота
    wait $BOT_PID
    EXIT_CODE=$?
    
    echo "[$(date)] ⚠️ Bot ending with code $EXIT_CODE"
    
    # If it was SIGTERM (15) or handing stop
    if [ $EXIT_CODE -eq 143 ] || [ $EXIT_CODE -eq 130 ]; then
        echo "[$(date)] Normal stoping, don't restart"
        exit 0
    fi
    
    echo "[$(date)] 🔄 Restart in 10 sec..."
    sleep 10
done