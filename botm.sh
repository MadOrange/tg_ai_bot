#!/bin/bash
# AI Bot Manager Script
# Usage: ./bot_manager.sh [start|stop|restart|status|log]

# ==============================
# CONFIGURATION Конфигурация 
# ==============================
BOT_DIR="/home/ior4nge/tg_ai_bot"      # Directory with bot files
SCRIPT="start_bot.sh"                   # Main bot script
PID_FILE="$BOT_DIR/monitor.pid"         # File to store monitor PID
LOG_FILE="$BOT_DIR/start_bot.log"       # Log file for monitor
BOT_PROCESS="tg_bot_v1.5.0.py"          # Bot process name to find

# ==============================
# COLOR CODES (for better output)
# ==============================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'  # No Color

# ==============================
# FUNCTIONS
# ==============================

# Print colored message
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Start the bot
start_bot() {
    print_info "Starting AI Bot..."
    
    # Check if already running
    if [ -f "$PID_FILE" ] && ps -p $(cat "$PID_FILE") > /dev/null 2>&1; then
        print_warning "Bot is already running (Monitor PID: $(cat "$PID_FILE"))"
        return 1
    fi
    
    # Change to bot directory
    if ! cd "$BOT_DIR" 2>/dev/null; then
        print_error "Cannot access bot directory: $BOT_DIR"
        return 1
    fi
    
    print_info "Launching bot with nohup..."
    
    # Start bot with nohup (background, survives terminal close)
    nohup setsid "./$SCRIPT" > "$LOG_FILE" 2>&1 < /dev/null &
    
    # Save monitor PID
    MONITOR_PID=$!
    echo $MONITOR_PID > "$PID_FILE"
    
    # Wait a bit for bot to initialize
    sleep 3
    
    # Verify monitor is running
    if ps -p $MONITOR_PID > /dev/null 2>&1; then
        print_success "Bot monitor started successfully"
        print_info "  Monitor PID: $MONITOR_PID"
        print_info "  Log file: $LOG_FILE"
        print_info "  View logs: tail -f $LOG_FILE"
    else
        print_error "Failed to start bot monitor"
        rm -f "$PID_FILE"
        return 1
    fi
    
    return 0
}

# Stop the bot
stop_bot() {
    print_info "Stopping AI Bot..."
    
    local stopped_something=false
    
    # Stop monitor if PID file exists
    if [ -f "$PID_FILE" ]; then
        MONITOR_PID=$(cat "$PID_FILE")
        
        if ps -p "$MONITOR_PID" > /dev/null 2>&1; then
            print_info "Stopping monitor process (PID: $MONITOR_PID)..."
            
            # Try graceful shutdown first
            kill "$MONITOR_PID" 2>/dev/null
            sleep 2
            
            # Force kill if still running
            if ps -p "$MONITOR_PID" > /dev/null 2>&1; then
                print_warning "Monitor not responding, forcing kill..."
                kill -9 "$MONITOR_PID" 2>/dev/null
            fi
            
            stopped_something=true
        fi
        
        # Remove PID file
        rm -f "$PID_FILE"
        print_info "PID file removed: $PID_FILE"
    fi
    
    # Stop all bot python processes
    local bot_processes=$(pgrep -f "$BOT_PROCESS" 2>/dev/null)
    if [ -n "$bot_processes" ]; then
        print_info "Stopping bot processes..."
        pkill -f "$BOT_PROCESS" 2>/dev/null
        
        # Force kill any remaining
        sleep 1
        local remaining=$(pgrep -f "$BOT_PROCESS" 2>/dev/null)
        if [ -n "$remaining" ]; then
            print_warning "Some processes still running, forcing kill..."
            pkill -9 -f "$BOT_PROCESS" 2>/dev/null
        fi
        
        stopped_something=true
    fi
    
    # Stop any remaining start_bot.sh processes
    local script_processes=$(pgrep -f "$SCRIPT" 2>/dev/null)
    if [ -n "$script_processes" ]; then
        print_info "Stopping script processes..."
        pkill -f "$SCRIPT" 2>/dev/null
        stopped_something=true
    fi
    
    if [ "$stopped_something" = true ]; then
        print_success "All bot processes stopped"
    else
        print_info "No running bot processes found"
    fi
}

# Show bot status
status_bot() {
    echo "================================"
    echo "AI BOT STATUS"
    echo "================================"
    
    # Check monitor
    if [ -f "$PID_FILE" ]; then
        MONITOR_PID=$(cat "$PID_FILE")
        if ps -p "$MONITOR_PID" > /dev/null 2>&1; then
            print_success "[MONITOR] Running (PID: $MONITOR_PID)"
            
            # Get monitor uptime
            local uptime=$(ps -p "$MONITOR_PID" -o etime= 2>/dev/null | xargs)
            print_info "  Uptime: ${uptime:-unknown}"
        else
            print_error "[MONITOR] PID file exists but process not found"
            print_warning "  Clean up with: rm $PID_FILE"
        fi
    else
        print_warning "[MONITOR] Not running (no PID file)"
    fi
    
    echo "--------------------------------"
    
    # Check bot processes
    local bot_processes=$(pgrep -f "$BOT_PROCESS" 2>/dev/null)
    if [ -n "$bot_processes" ]; then
        local count=$(echo "$bot_processes" | wc -l)
        print_success "[BOT] $count process(es) running"
        
        # Show each process
        echo "$bot_processes" | while read pid; do
            local info=$(ps -p "$pid" -o pid,etime,cmd --no-headers 2>/dev/null)
            if [ -n "$info" ]; then
                print_info "  PID $info"
            fi
        done
    else
        print_warning "[BOT] No processes running"
    fi
    
    echo "--------------------------------"
    
    # Check log file
    if [ -f "$LOG_FILE" ]; then
        local log_size=$(du -h "$LOG_FILE" 2>/dev/null | cut -f1)
        local log_lines=$(wc -l < "$LOG_FILE" 2>/dev/null)
        print_info "[LOGS] File: $LOG_FILE"
        print_info "       Size: ${log_size:-unknown}, Lines: ${log_lines:-unknown}"
    else
        print_warning "[LOGS] Log file not found"
    fi
    
    echo "================================"
}

# Show recent logs
show_log() {
    print_info "Bot Logs: $LOG_FILE"
    echo "--------------------------------"
    
    if [ -f "$LOG_FILE" ]; then
        # Show last 30 lines with line numbers
        tail -30 "$LOG_FILE" | nl -ba | sed 's/^/    /'
        
        echo "--------------------------------"
        print_info "Total lines: $(wc -l < "$LOG_FILE")"
        print_info "View live: tail -f $LOG_FILE"
        print_info "Clear logs: > $LOG_FILE"
    else
        print_error "Log file not found: $LOG_FILE"
        # Check if directory exists
        if [ ! -d "$BOT_DIR" ]; then
            print_error "Bot directory not found: $BOT_DIR"
        fi
    fi
}

# Restart bot
restart_bot() {
    print_info "Restarting AI Bot..."
    stop_bot
    sleep 3
    start_bot
}

# Clear old logs
clean_logs() {
    print_info "Cleaning old log files..."
    
    if [ -f "$LOG_FILE" ] && [ -s "$LOG_FILE" ]; then
        local old_size=$(du -h "$LOG_FILE" | cut -f1)
        echo -n "" > "$LOG_FILE"
        print_success "Cleared log file (was $old_size)"
    else
        print_info "Log file is empty or doesn't exist"
    fi
    
    # Clean other log files in bot directory
    local other_logs=$(find "$BOT_DIR" -name "*.log" -type f ! -name "$(basename "$LOG_FILE")" 2>/dev/null)
    if [ -n "$other_logs" ]; then
        print_info "Found additional log files:"
        echo "$other_logs" | while read log; do
            local size=$(du -h "$log" 2>/dev/null | cut -f1)
            echo "  $log ($size)"
        done
    fi
}

# ==============================
# MAIN SCRIPT
# ==============================

# Check for command line argument
if [ $# -eq 0 ]; then
    echo "=========================================="
    echo "AI BOT MANAGER"
    echo "=========================================="
    echo "Usage: $0 {start|stop|restart|status|log|clean}"
    echo ""
    echo "Commands:"
    echo "  start   - Start the bot"
    echo "  stop    - Stop the bot"
    echo "  restart - Restart the bot"
    echo "  status  - Show bot status"
    echo "  log     - Show recent logs"
    echo "  clean   - Clear log files"
    echo ""
    echo "Configuration:"
    echo "  Bot directory: $BOT_DIR"
    echo "  Main script: $SCRIPT"
    echo "  PID file: $PID_FILE"
    echo "  Log file: $LOG_FILE"
    echo "=========================================="
    exit 1
fi

# Handle commands
case "$1" in
    start)
        start_bot
        ;;
    stop)
        stop_bot
        ;;
    restart)
        restart_bot
        ;;
    status)
        status_bot
        ;;
    log)
        show_log
        ;;
    clean)
        clean_logs
        ;;
    *)
        print_error "Unknown command: $1"
        echo "Available commands: start, stop, restart, status, log, clean"
        exit 1
        ;;
esac

exit 0