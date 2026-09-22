#!/bin/bash
#
# Manage_ivc_track.sh — управление Streamlit-приложением ivc_track
#
set -euo pipefail

# --- Конфигурация ---
APP_DIR="/var/www/html/ivc_track"
PORT="8505"
DEBUG_PORT="5681"
LOG_FILE="$APP_DIR/streamlit.log"
LOG_DEBUG_FILE="$APP_DIR/streamlit-debug.log"
PID_FILE="$APP_DIR/streamlit.pid"
PID_DEBUG_FILE="$APP_DIR/streamlit-debug.pid"
STREAMLIT_BIN="$APP_DIR/venv/bin/streamlit"
VENV_PYTHON="$APP_DIR/venv/bin/python"

# Цвета
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# --- Хелперы ---
is_our_streamlit() {
    local pid="$1"
    [ -n "$pid" ] || return 1
    ps -p "$pid" -o args= 2>/dev/null | grep -q "streamlit run main.py"
}

is_our_debugpy() {
    local pid="$1"
    [ -n "$pid" ] || return 1
    ps -p "$pid" -o args= 2>/dev/null | grep -q "debugpy --listen"
}

# Убить только если это наш процесс, иначе — предупредить
safe_kill() {
    local pid="$1"
    local what="$2"     # описание для логов
    local matcher="$3"  # имя функции-проверки

    [ -n "$pid" ] || return 0
    if ! ps -p "$pid" >/dev/null 2>&1; then
        return 0
    fi
    if ! "$matcher" "$pid"; then
        echo -e "${RED}❌ PID $pid ($what) — не наш процесс, не трогаем${NC}" >&2
        return 1
    fi

    echo -e "${YELLOW}⏹️  Останавливаем $what (PID: $pid)${NC}"
    kill "$pid" 2>/dev/null || true
    for _ in 1 2 3 4 5; do
        ps -p "$pid" >/dev/null 2>&1 || break
        sleep 1
    done
    if ps -p "$pid" >/dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  Принудительно завершаем PID: $pid${NC}"
        kill -9 "$pid" 2>/dev/null || true
    fi
    return 0
}

# Найти наш процесс на порту и остановить его (или предупредить о чужом)
free_port() {
    local port="$1"
    local what="$2"
    local matcher="$3"
    local pid
    pid=$(lsof -t -i:"$port" 2>/dev/null || true)
    [ -n "$pid" ] || return 0
    safe_kill "$pid" "$what на порту $port" "$matcher"
}

# --- Статус ---
status() {
    if [ -f "$PID_FILE" ]; then
        local pid
        pid=$(cat "$PID_FILE" 2>/dev/null || true)
        if [ -n "$pid" ] && ps -p "$pid" >/dev/null 2>&1 && is_our_streamlit "$pid"; then
            echo -e "${GREEN}✅ Приложение запущено (PID: $pid)${NC}"
            echo -e "🌐 http://0.0.0.0:$PORT"
            return 0
        fi
        echo -e "${RED}❌ PID-файл есть, но процесс не наш/не запущен${NC}"
        rm -f "$PID_FILE"
        return 1
    fi
    local pid
    pid=$(lsof -t -i:"$PORT" 2>/dev/null || true)
    if [ -n "$pid" ]; then
        echo -e "${YELLOW}⚠️ Процесс на порту $PORT (PID: $pid) без PID-файла${NC}"
    else
        echo -e "${RED}❌ Приложение не запущено${NC}"
    fi
    return 1
}

status-debug() {
    if [ -f "$PID_DEBUG_FILE" ]; then
        local pid
        pid=$(cat "$PID_DEBUG_FILE" 2>/dev/null || true)
        if [ -n "$pid" ] && ps -p "$pid" >/dev/null 2>&1 && is_our_debugpy "$pid"; then
            echo -e "${GREEN}✅ Отладочная сессия активна (PID: $pid)${NC}"
            echo -e "🌐 http://0.0.0.0:$PORT"
            echo -e "🔧 Порт отладчика: $DEBUG_PORT"
            return 0
        fi
        echo -e "${RED}❌ PID-файл отладки есть, но процесс не наш/не запущен${NC}"
        rm -f "$PID_DEBUG_FILE"
        return 1
    fi
    local pid
    pid=$(lsof -t -i:"$DEBUG_PORT" 2>/dev/null || true)
    if [ -n "$pid" ]; then
        echo -e "${YELLOW}⚠️ Процесс на порту $DEBUG_PORT (PID: $pid) без PID-файла${NC}"
    else
        echo -e "${RED}❌ Отладочная сессия не активна${NC}"
    fi
    return 1
}

# --- Запуск (обычный, в фоне) ---
start() {
    cd "$APP_DIR"

    if [ -f "$PID_FILE" ]; then
        local pid
        pid=$(cat "$PID_FILE" 2>/dev/null || true)
        if [ -n "$pid" ] && ps -p "$pid" >/dev/null 2>&1 && is_our_streamlit "$pid"; then
            echo -e "${YELLOW}⚠️ Приложение уже запущено (PID: $pid)${NC}"
            return 0
        fi
        rm -f "$PID_FILE"
    fi

    free_port "$PORT" "streamlit" is_our_streamlit || return 1

    if [ ! -x "$STREAMLIT_BIN" ]; then
        echo -e "${RED}❌ Не найден streamlit: $STREAMLIT_BIN${NC}" >&2
        return 1
    fi

    echo -e "${GREEN}🚀 Запускаем приложение...${NC}"
    nohup "$STREAMLIT_BIN" run main.py \
        --server.port "$PORT" \
        --server.address 0.0.0.0 \
        --server.runOnSave false \
        --server.fileWatcherType none \
        --browser.gatherUsageStats false \
        >> "$LOG_FILE" 2>&1 &

    local new_pid=$!
    echo "$new_pid" > "$PID_FILE"
    sleep 3

    if ps -p "$new_pid" >/dev/null 2>&1 && is_our_streamlit "$new_pid"; then
        echo -e "${GREEN}✅ Приложение запущено (PID: $new_pid)${NC}"
        echo -e "🌐 http://0.0.0.0:$PORT"
        echo -e "📋 Логи: $LOG_FILE"
    else
        echo -e "${RED}❌ Ошибка запуска!${NC}"
        tail -10 "$LOG_FILE" || true
        rm -f "$PID_FILE"
        return 1
    fi
}

# --- Запуск с отладкой (ручной, в фоне) ---
start-debug() {
    cd "$APP_DIR"

    if [ -f "$PID_DEBUG_FILE" ]; then
        local pid
        pid=$(cat "$PID_DEBUG_FILE" 2>/dev/null || true)
        if [ -n "$pid" ] && ps -p "$pid" >/dev/null 2>&1 && is_our_debugpy "$pid"; then
            echo -e "${YELLOW}⚠️ Отладочная сессия уже запущена (PID: $pid)${NC}"
            echo -e "${YELLOW}💡 Используйте 'stop-debug' для остановки${NC}"
            return 0
        fi
        rm -f "$PID_DEBUG_FILE"
    fi

    free_port "$PORT" "streamlit" is_our_streamlit || return 1
    free_port "$DEBUG_PORT" "debugpy" is_our_debugpy || return 1

    echo -e "${GREEN}🚀 Запускаем приложение с поддержкой отладки...${NC}"
    echo -e "${BLUE}📌 debugpy слушает порт: $DEBUG_PORT${NC}"

    nohup "$VENV_PYTHON" -m debugpy --listen "0.0.0.0:$DEBUG_PORT" \
        -m streamlit run main.py \
        --server.port "$PORT" \
        --server.address 0.0.0.0 \
        --server.runOnSave false \
        --server.fileWatcherType none \
        >> "$LOG_DEBUG_FILE" 2>&1 &

    local new_pid=$!
    echo "$new_pid" > "$PID_DEBUG_FILE"
    sleep 3

    if ps -p "$new_pid" >/dev/null 2>&1; then
        echo -e "${GREEN}✅ Приложение запущено с отладкой (PID: $new_pid)${NC}"
        echo -e "🌐 http://0.0.0.0:$PORT"
        echo -e "🔧 Порт отладчика: $DEBUG_PORT"
        echo -e "📋 Логи: $LOG_DEBUG_FILE"
        echo ""
        echo -e "${BLUE}💡 В VSCode:${NC}"
        echo -e "   1. Откройте 'Run and Debug' (Ctrl+Shift+D)"
        echo -e "   2. Выберите 'Attach to Streamlit (Remote)'"
        echo -e "   3. Нажмите F5"
    else
        echo -e "${RED}❌ Ошибка запуска!${NC}"
        tail -10 "$LOG_DEBUG_FILE" || true
        rm -f "$PID_DEBUG_FILE"
        return 1
    fi
}

# --- Запуск для systemd (foreground, без exec — PID пишет systemd) ---
start-debug-service() {
    cd "$APP_DIR"

    free_port "$PORT" "streamlit" is_our_streamlit || return 1
    free_port "$DEBUG_PORT" "debugpy" is_our_debugpy || return 1

    echo -e "${GREEN}🚀 Запускаем приложение с поддержкой отладки (для systemd)...${NC}"
    echo -e "${BLUE}📌 debugpy слушает порт: $DEBUG_PORT${NC}"

    # ВАЖНО: без exec и без &, чтобы systemd управлял процессом,
    # а PID-файл не нужен — systemd знает PID сам.
    # Но чтобы stop-debug из этого же скрипта не трогал наш процесс
    # по порту, лучше вообще не вызывать stop-debug из ExecStartPre.
    "$VENV_PYTHON" -m debugpy --listen "0.0.0.0:$DEBUG_PORT" \
        -m streamlit run main.py \
        --server.port "$PORT" \
        --server.address 0.0.0.0 \
        --server.runOnSave false \
        --server.fileWatcherType none
}

# --- Стоп ---
stop() {
    if [ -f "$PID_FILE" ]; then
        local pid
        pid=$(cat "$PID_FILE" 2>/dev/null || true)
        if [ -n "$pid" ] && ps -p "$pid" >/dev/null 2>&1; then
            safe_kill "$pid" "streamlit" is_our_streamlit || true
        else
            echo -e "${YELLOW}⚠️ PID-файл есть, но процесс не найден${NC}"
        fi
        rm -f "$PID_FILE"
        echo -e "${GREEN}✅ Приложение остановлено${NC}"
    else
        free_port "$PORT" "streamlit" is_our_streamlit || true
    fi
}

# --- Стоп отладки ---
stop-debug() {
    if [ -f "$PID_DEBUG_FILE" ]; then
        local pid
        pid=$(cat "$PID_DEBUG_FILE" 2>/dev/null || true)
        if [ -n "$pid" ] && ps -p "$pid" >/dev/null 2>&1; then
            safe_kill "$pid" "debugpy" is_our_debugpy || true
        else
            echo -e "${YELLOW}⚠️ PID-файл есть, но процесс не найден${NC}"
        fi
        rm -f "$PID_DEBUG_FILE"
    fi

    # Чистим порт отладчика, если на нём висит наш debugpy
    local dp
    dp=$(lsof -t -i:"$DEBUG_PORT" 2>/dev/null || true)
    if [ -n "$dp" ]; then
        safe_kill "$dp" "debugpy на порту $DEBUG_PORT" is_our_debugpy || true
    fi

    # ВАЖНО: НЕ трогаем порт приложения ($PORT).
    # Раньше здесь был kill -9 по $PORT — это и убивало основной сервис.
    echo -e "${GREEN}✅ Отладочная сессия остановлена${NC}"
}

# --- Перезапуск ---
restart() {
    echo -e "${BLUE}🔄 Перезапуск приложения...${NC}"
    stop
    sleep 2
    start
}

restart-debug() {
    echo -e "${BLUE}🔄 Перезапуск приложения с отладкой...${NC}"
    stop-debug
    sleep 2
    start-debug
}

# --- Логи ---
logs() {
    [ -f "$LOG_FILE" ] && tail -f "$LOG_FILE" || echo -e "${RED}❌ Файл лога не найден: $LOG_FILE${NC}"
}

logs-debug() {
    [ -f "$LOG_DEBUG_FILE" ] && tail -f "$LOG_DEBUG_FILE" || echo -e "${RED}❌ Файл лога отладки не найден: $LOG_DEBUG_FILE${NC}"
}

# --- Диспетчер ---
case "${1:-}" in
    start)               start ;;
    start-debug)         start-debug ;;
    start-debug-service) start-debug-service ;;
    stop)                stop ;;
    stop-debug)          stop-debug ;;
    restart)             restart ;;
    restart-debug)       restart-debug ;;
    status)              status ;;
    status-debug)        status-debug ;;
    logs)                logs ;;
    logs-debug)          logs-debug ;;
    *)
        cat <<EOF
Использование: $0 {команда}

Команды:
  start               - Запустить приложение
  start-debug         - Запустить приложение с отладкой (фон)
  start-debug-service - Запустить для systemd (foreground)
  stop                - Остановить приложение
  stop-debug          - Остановить отладочную сессию
  restart             - Перезапустить приложение
  restart-debug       - Перезапустить с отладкой
  status              - Статус приложения
  status-debug        - Статус отладочной сессии
  logs                - Логи приложения (tail -f)
  logs-debug          - Логи отладки (tail -f)
EOF
        exit 1
        ;;
esac

exit 0