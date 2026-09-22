#!/bin/bash
#
# restart_ivc_track.sh — перезапуск ivc_track-debug.service с проверкой
#
set -euo pipefail

SERVICE="ivc_track-debug.service"
APP_PORT="8505"
DEBUG_PORT="5681"
HEALTH_URL="http://127.0.0.1:${APP_PORT}/_stcore/health"
APP_URL="http://127.0.0.1:${APP_PORT}/"
MAX_WAIT=30          # сколько секунд ждать готовности
CHECK_INTERVAL=1     # интервал между проверками

# Цвета
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

ok()    { echo -e "${GREEN}✅ $*${NC}"; }
fail()  { echo -e "${RED}❌ $*${NC}"; }
warn()  { echo -e "${YELLOW}⚠️  $*${NC}"; }
info()  { echo -e "${BLUE}ℹ️  $*${NC}"; }
step()  { echo -e "${CYAN}${BOLD}▶ $*${NC}"; }

# --- 0. Проверка root ---
if [ "$(id -u)" -ne 0 ]; then
    fail "Запустите с sudo: sudo $0"
    exit 1
fi

echo
echo -e "${BOLD}🔄 Перезапуск ${SERVICE}${NC}"
echo "─────────────────────────────────────────"

# --- 1. Текущее состояние ---
step "Текущее состояние"
if systemctl is-active --quiet "$SERVICE"; then
    OLD_PID=$(systemctl show -p MainPID --value "$SERVICE")
    OLD_UPTIME=$(systemctl show -p ActiveEnterTimestamp --value "$SERVICE")
    info "Сервис активен (MainPID: ${OLD_PID})"
    info "Запущен с: ${OLD_UPTIME}"
else
    warn "Сервис не активен"
fi

# --- 2. Запоминаем NRestarts до рестарта ---
RESTARTS_BEFORE=$(systemctl show -p NRestarts --value "$SERVICE")
info "NRestarts до рестарта: ${RESTARTS_BEFORE}"

# --- 3. Рестарт ---
echo
step "Перезапуск сервиса"
if ! systemctl restart "$SERVICE"; then
    fail "systemctl restart вернул ошибку"
    echo
    echo "── Последние логи ──"
    journalctl -u "$SERVICE" -n 30 --no-pager
    exit 1
fi
ok "Команда restart выполнена"

# --- 4. Ждём, пока сервис станет active ---
echo
step "Ожидание запуска сервиса"
WAITED=0
while [ "$WAITED" -lt "$MAX_WAIT" ]; do
    STATE=$(systemctl is-active "$SERVICE" 2>/dev/null || true)
    if [ "$STATE" = "active" ]; then
        ok "Сервис active (за ${WAITED}s)"
        break
    fi
    printf "\r${YELLOW}⏳ Ожидание... ${WAITED}s (состояние: ${STATE})${NC}"
    sleep "$CHECK_INTERVAL"
    WAITED=$((WAITED + CHECK_INTERVAL))
done

if [ "$STATE" != "active" ]; then
    echo
    fail "Сервис не запустился за ${MAX_WAIT}s (состояние: ${STATE})"
    echo
    echo "── Статус ──"
    systemctl status "$SERVICE" --no-pager || true
    echo
    echo "── Последние логи ──"
    journalctl -u "$SERVICE" -n 30 --no-pager || true
    exit 1
fi

# --- 5. Проверяем, что Main PID появился ---
NEW_PID=$(systemctl show -p MainPID --value "$SERVICE")
if [ -z "$NEW_PID" ] || [ "$NEW_PID" = "0" ]; then
    fail "MainPID не установлен"
    exit 1
fi
ok "Main PID: ${NEW_PID}"

# --- 6. Ждём готовности приложения (health endpoint) ---
echo
step "Ожидание готовности приложения (${HEALTH_URL})"
WAITED=0
HTTP_OK=0
while [ "$WAITED" -lt "$MAX_WAIT" ]; do
    HTTP_CODE=$(curl -sS -o /dev/null -w "%{http_code}" \
        --max-time 3 "$HEALTH_URL" 2>/dev/null || echo "000")
    if [ "$HTTP_CODE" = "200" ]; then
        HTTP_OK=1
        ok "Приложение готово (HTTP ${HTTP_CODE} за ${WAITED}s)"
        break
    fi
    printf "\r${YELLOW}⏳ Ожидание... ${WAITED}s (HTTP: ${HTTP_CODE})${NC}"
    sleep "$CHECK_INTERVAL"
    WAITED=$((WAITED + CHECK_INTERVAL))
done
echo

if [ "$HTTP_OK" -ne 1 ]; then
    fail "Приложение не ответило за ${MAX_WAIT}s"
    echo
    echo "── Порты ──"
    ss -tlnp | grep -E ":${APP_PORT}|:${DEBUG_PORT}" || echo "  (ничего не слушает)"
    echo
    echo "── Логи приложения ──"
    tail -30 /var/www/html/ivc_track/streamlit-debug.error.log 2>/dev/null || true
    exit 1
fi

# --- 7. Финальные проверки ---
echo
step "Финальные проверки"

# 7.1. Основной URL
APP_CODE=$(curl -sS -o /dev/null -w "%{http_code}" --max-time 5 "$APP_URL" 2>/dev/null || echo "000")
if [ "$APP_CODE" = "200" ]; then
    ok "Главная страница: HTTP ${APP_CODE}"
else
    warn "Главная страница: HTTP ${APP_CODE}"
fi

# 7.2. Порт приложения
if ss -tlnp 2>/dev/null | grep -q ":${APP_PORT} "; then
    ok "Порт ${APP_PORT} слушается"
else
    fail "Порт ${APP_PORT} не слушается"
fi

# 7.3. Порт отладчика
if ss -tlnp 2>/dev/null | grep -q ":${DEBUG_PORT} "; then
    ok "Порт отладчика ${DEBUG_PORT} слушается"
else
    warn "Порт отладчика ${DEBUG_PORT} не слушается (отладка недоступна)"
fi

# 7.4. NRestarts не вырос
RESTARTS_AFTER=$(systemctl show -p NRestarts --value "$SERVICE")
if [ "$RESTARTS_AFTER" = "$RESTARTS_BEFORE" ]; then
    ok "NRestarts стабилен: ${RESTARTS_AFTER}"
else
    warn "NRestarts изменился: ${RESTARTS_BEFORE} → ${RESTARTS_AFTER}"
fi

# 7.5. CPU процесса
PY_PID=$(pgrep -f "debugpy.*${DEBUG_PORT}.*streamlit run main.py" | head -1 || true)
if [ -n "$PY_PID" ]; then
    CPU=$(ps -p "$PY_PID" -o pcpu= | tr -d ' ')
    MEM=$(ps -p "$PY_PID" -o pmem= | tr -d ' ')
    ok "Python PID ${PY_PID}: CPU ${CPU}%, MEM ${MEM}%"
else
    warn "Python-процесс не найден (возможно, ещё стартует)"
fi

# --- 8. Итог ---
echo
echo "─────────────────────────────────────────"
ok "🎉 Перезапуск завершён успешно"
echo
echo -e "${CYAN}Ссылки:${NC}"
echo "  🌐 Приложение:  http://192.168.10.130:${APP_PORT}/"
echo "  🔧 Отладчик:    192.168.10.130:${DEBUG_PORT}"
echo "  📋 Логи:        journalctl -u ${SERVICE} -f"
echo "  📄 Файл логов:  tail -f /var/www/html/ivc_track/streamlit-debug.log"
echo