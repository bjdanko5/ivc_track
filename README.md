# IVC Track

Streamlit-приложение для отслеживания квитанций через SOAP-сервис и интеграции с ЮKassa.

![Python](https://img.shields.io/badge/python-3.12-blue)
![Streamlit](https://img.shields.io/badge/streamlit-1.40-red)
![Last commit](https://img.shields.io/github/last-commit/bjdanko5/ivc_track)
![Repo size](https://img.shields.io/github/repo-size/bjdanko5/ivc_track)

---

## 📋 Содержание

- [Возможности](#-возможности)
- [Требования](#-требования)
- [Установка](#-установка)
- [Настройка](#️-настройка)
- [Запуск](#️-запуск)
- [Управление сервисом](#-управление-сервисом)
- [Работа с зависимостями](#-работа-с-зависимостями)
- [Разработка](#-разработка)
- [Структура проекта](#-структура-проекта)
- [Диагностика](#-диагностика)
- [Контрибьютинг](#-контрибьютинг)
- [Лицензия](#-лицензия)

---

## 🚀 Возможности

- 📊 Отслеживание статусов квитанций через SOAP-сервис `192.168.10.238`
- 💳 Обработка платежей через ЮKassa
- 🔄 Автоматическое обновление статусов (`update_payments.py`)
- 📝 Логирование операций
- 🤖 Интеграция с Mistral AI
- 🐛 Поддержка удалённой отладки через `debugpy` (порт `5681`)
- 📈 Мониторинг CPU/памяти через `psutil`

---

## 📦 Требования

| Компонент | Версия |
|---|---|
| Python | 3.12+ |
| pip | 22.2+ |
| systemd | любой |
| ОС | Ubuntu 22.04+ / Debian 12+ |

---

## 🔧 Установка

### 1. Клонировать репозиторий

```bash
cd /var/www/html
git clone https://github.com/bjdanko5/ivc_track.git
cd ivc_track
```

### 2. Создать виртуальное окружение

```bash
python3.12 -m venv venv
source venv/bin/activate
pip install --upgrade pip setuptools wheel
```

### 3. Установить зависимости

```bash
pip install -r requirements.txt
```

---

## ⚙️ Настройка

### Переменные окружения

Скопируйте шаблон и заполните реальными значениями:

```bash
cp .env.example .env
nano .env
```

Пример `.env`:

```ini
# SOAP-сервис IVC Track
IVC_SOAP_URL=http://192.168.10.238/ivc_track/ws/ivc_track
IVC_SOAP_USERNAME=your_username
IVC_SOAP_PASSWORD=your_password

# Лицевой счёт
IVC_PASSWORD_LS=your_password_ls

# Mistral AI
MISTRAL_API_KEY=your_mistral_api_key

# ЮKassa
YOOKASSA_SHOP_ID=your_shop_id
YOOKASSA_SECRET_KEY=your_secret_key
```

> ⚠️ **`.env` находится в `.gitignore`** — не коммитьте его в репозиторий.

### Streamlit config

```bash
mkdir -p .streamlit
cat > .streamlit/config.toml <<'EOF'
[server]
runOnSave = false
fileWatcherType = "none"
headless = true

[browser]
gatherUsageStats = false
EOF
```

---

## ▶️ Запуск

### Вручную (для разработки)

```bash
cd /var/www/html/ivc_track
source venv/bin/activate

streamlit run main.py \
    --server.port 8505 \
    --server.address 0.0.0.0 \
    --server.runOnSave false \
    --server.fileWatcherType none
```

Приложение доступно по адресу: `http://192.168.10.130:8505/`

### С отладкой (debugpy)

```bash
cd /var/www/html/ivc_track
./Manage_ivc_track.sh start-debug
```

Отладчик слушает порт `5681`. Подключение из VS Code:

```json
{
    "name": "Attach to Streamlit (Remote)",
    "type": "debugpy",
    "request": "attach",
    "connect": {
        "host": "192.168.10.130",
        "port": 5681
    },
    "pathMappings": [
        {
            "localRoot": "${workspaceFolder}",
            "remoteRoot": "/var/www/html/ivc_track"
        }
    ]
}
```

---

## 🎛️ Управление сервисом

### systemd

```bash
# Запустить
sudo systemctl start ivc_track-debug.service

# Остановить
sudo systemctl stop ivc_track-debug.service

# Перезапустить
sudo systemctl restart ivc_track-debug.service

# Статус
sudo systemctl status ivc_track-debug.service

# Логи в реальном времени
sudo journalctl -u ivc_track-debug.service -f

# Последние 50 строк логов
sudo journalctl -u ivc_track-debug.service -n 50 --no-pager
```

### Скрипт `Manage_ivc_track.sh`

```bash
cd /var/www/html/ivc_track

# Обычный запуск (без отладки, в фоне)
./Manage_ivc_track.sh start

# Запуск с отладкой (в фоне)
./Manage_ivc_track.sh start-debug

# Запуск для systemd (в foreground)
./Manage_ivc_track.sh start-debug-service

# Остановка
./Manage_ivc_track.sh stop
./Manage_ivc_track.sh stop-debug

# Перезапуск
./Manage_ivc_track.sh restart
./Manage_ivc_track.sh restart-debug

# Статус
./Manage_ivc_track.sh status
./Manage_ivc_track.sh status-debug

# Логи
./Manage_ivc_track.sh logs
./Manage_ivc_track.sh logs-debug
```

### Скрипт `restart_ivc_track.sh`

```bash
# Перезапуск с проверкой готовности
sudo /var/www/html/ivc_track/restart_ivc_track.sh
```

Скрипт:
- делает бэкап состояния;
- ждёт готовности `/_stcore/health`;
- проверяет порты `8505` и `5681`;
- проверяет `NRestarts`, CPU, память;
- показывает итоговые ссылки.

---

## 📦 Работа с зависимостями

Проект использует **`pip-tools`** для управления зависимостями и скрипт **`update_deps.sh`** для автоматизации.

### Как это устроено

| Файл | Назначение | Редактируется |
|---|---|---|
| `requirements.in` | Прямые зависимости (что вы импортируете) | ✍️ вручную |
| `requirements.txt` | Полный граф с точными версиями | 🤖 `pip-compile` |
| `.deps_backup/` | Бэкапы перед каждым обновлением | 🤖 `update_deps.sh` |

**Правило:** никогда не редактируйте `requirements.txt` вручную — он перегенерируется.

### Установка скрипта

Если `update_deps.sh` ещё не установлен:

```bash
sudo nano /usr/local/bin/update_deps.sh
# (вставить содержимое скрипта)
sudo chmod +x /usr/local/bin/update_deps.sh

# Проверить
bash -n /usr/local/bin/update_deps.sh && echo "syntax OK"
```

### Основные команды

```bash
# 1. Посмотреть, что устарело (без применения)
sudo update_deps.sh --dry-run

# 2. Обновить ВСЕ пакеты до последних совместимых версий
sudo update_deps.sh

# 3. Обновить только один пакет
sudo update_deps.sh streamlit

# 4. Обновить несколько пакетов
sudo update_deps.sh streamlit yookassa zeep

# 5. Dry-run для конкретного пакета
sudo update_deps.sh --dry-run streamlit
```

### Что делает скрипт

При запуске `update_deps.sh`:

1. **Бэкап** — сохраняет `pip freeze` в `.deps_backup/requirements_frozen_YYYYMMDD-HHMMSS.txt`
2. **Проверка** `pip-tools` — устанавливает, если нет
3. **`pip-compile`** — генерирует новый `requirements.txt`:
   - `--upgrade` — если пакеты не указаны (обновить всё)
   - `--upgrade-package <pkg>` — если указаны конкретные
4. **Показ diff** — что изменилось в версиях
5. **`pip-sync`** — синхронизирует venv:
   - удаляет пакеты, которых нет в `requirements.txt`
   - доустанавливает/обновляет нужные
6. **Восстановление** `pip-tools` (его удаляет `pip-sync`)
7. **Проверка импортов** — 9 ключевых пакетов
8. **Перезапуск** `ivc_track-debug.service`
9. **Проверка** HTTP-отклика приложения

### Пример вывода

```
📦 Обновление зависимостей ivc_track
─────────────────────────────────────────
▶ Бэкап текущего состояния
✅ Бэкап: /var/www/html/ivc_track/.deps_backup/requirements_frozen_20260922-162141.txt

▶ Проверка pip-tools
✅ pip-tools уже установлен

▶ Генерация нового requirements.txt
ℹ️  Обновление ВСЕХ пакетов
✅ requirements.txt обновлён

▶ Изменения в requirements.txt
--- /tmp/requirements_old.txt
+++ /var/www/html/ivc_track/requirements.txt
@@ -10,7 +10,7 @@
-altair==5.4.1
+altair==5.5.0
     # via streamlit
ℹ️  Строк изменено: 61

▶ Синхронизация venv (pip-sync)
✅ pip-tools восстановлен
✅ venv синхронизирован

▶ Проверка ключевых импортов
  OK   streamlit
  OK   requests
  OK   dotenv
  OK   psutil
  OK   mistralai
  OK   var_dump
  OK   zeep
  OK   yookassa
  OK   debugpy

▶ Перезапуск сервиса
✅ Сервис ivc_track-debug.service перезапущен

▶ Проверка отклика приложения
✅ Приложение отвечает: HTTP 200

─────────────────────────────────────────
🎉 Обновление завершено
```

### Фиксация версий

Чтобы **не обновлять** критичные пакеты (например, `streamlit`), зафиксируйте точную версию в `requirements.in`:

```
streamlit==1.40.1
```

Тогда `pip-compile --upgrade` **не будет** трогать этот пакет, даже если выйдет новая версия.

**Пример `requirements.in` с фиксацией:**

```
# Зафиксирован — не обновлять
streamlit==1.40.1

# Свободные — обновлять
requests
python-dotenv
psutil
mistralai
var_dump
zeep
yookassa
debugpy
pip-tools
```

Проверить, что `streamlit` не попал в diff:

```bash
sudo update_deps.sh --dry-run 2>&1 | grep -E "streamlit|altair" || echo "✅ streamlit и altair не в diff"
```

### Добавление новой зависимости

1. Добавьте пакет в `requirements.in`:

   ```bash
   echo "pandas" >> requirements.in
   ```

2. Сгенерируйте `requirements.txt`:

   ```bash
   cd /var/www/html/ivc_track
   source venv/bin/activate
   pip-compile requirements.in
   ```

3. Синхронизируйте venv:

   ```bash
   pip-sync requirements.txt
   pip install pip-tools   # восстановить
   ```

4. Или через скрипт:

   ```bash
   sudo update_deps.sh pandas
   ```

### Удаление зависимости

1. Удалите пакет из `requirements.in`:

   ```bash
   sed -i '/^pandas$/d' requirements.in
   ```

2. Перегенерируйте `requirements.txt`:

   ```bash
   cd /var/www/html/ivc_track
   source venv/bin/activate
   pip-compile requirements.in
   ```

3. Синхронизируйте venv (удалит пакет):

   ```bash
   pip-sync requirements.txt
   pip install pip-tools
   ```

### Откат обновления

Если после обновления что-то сломалось:

```bash
# 1. Список бэкапов
ls -la /var/www/html/ivc_track/.deps_backup/

# 2. Откат
cd /var/www/html/ivc_track
source venv/bin/activate
pip install -r .deps_backup/requirements_frozen_YYYYMMDD-HHMMSS.txt --force-reinstall

# 3. Перезапуск
sudo systemctl restart ivc_track-debug.service

# 4. Проверка
curl -sS --max-time 10 -o /dev/null -w "HTTP %{http_code}\n" http://127.0.0.1:8505/
```

### Ручное управление (без скрипта)

Если `update_deps.sh` недоступен:

```bash
cd /var/www/html/ivc_track
source venv/bin/activate

# Бэкап
pip freeze > .deps_backup/manual_$(date +%Y%m%d-%H%M%S).txt

# Обновить всё
pip-compile --upgrade requirements.in
pip-sync requirements.txt
pip install pip-tools

# Обновить конкретный пакет
pip-compile --upgrade-package streamlit requirements.in
pip-sync requirements.txt
pip install pip-tools
```

### Проверка актуальности

Раз в неделю:

```bash
# Что устарело
sudo update_deps.sh --dry-run

# Если только патч-версии (1.2.3 → 1.2.4) — можно обновлять
# Если мажорные (1.x → 2.x) — решать отдельно
```

### Алиасы для удобства

Добавьте в `~/.bashrc`:

```bash
alias deps-update='sudo /usr/local/bin/update_deps.sh'
alias deps-check='sudo /usr/local/bin/update_deps.sh --dry-run'
alias deps-backup='ls -la /var/www/html/ivc_track/.deps_backup/'
alias deps-list='cd /var/www/html/ivc_track && source venv/bin/activate && pip list'
```

Затем:

```bash
source ~/.bashrc

deps-check              # что устарело
deps-update             # обновить всё
deps-update streamlit   # обновить streamlit
deps-backup             # список бэкапов
deps-list               # список установленных пакетов
```

### `.gitignore`

Папка с бэкапами не должна попадать в репозиторий:

```bash
cd /var/www/html/ivc_track
echo ".deps_backup/" >> .gitignore
git add .gitignore
git commit -m "Ignore .deps_backup"
git push
```

---

## 💻 Разработка

### Прямые зависимости

| Пакет | Назначение |
|---|---|
| `streamlit` | Web UI |
| `requests` | HTTP-запросы |
| `python-dotenv` | Чтение `.env` |
| `psutil` | Мониторинг CPU/памяти |
| `mistralai` | Интеграция с Mistral AI |
| `var_dump` | Отладка (dump переменных) |
| `zeep` | SOAP-клиент |
| `yookassa` | Платёжная система |
| `debugpy` | Удалённая отладка |
| `pip-tools` | Управление зависимостями |

### Полезные команды

```bash
# Проверить синтаксис Python
python -m py_compile main.py pages/*.py

# Найти все импорты
grep -rn "^\s*import \|^\s*from " --include="*.py" --exclude-dir=venv .

# Проверить, что все пакеты установлены
python -c "
import importlib
for m in ['streamlit','requests','dotenv','psutil','mistralai','var_dump','zeep','yookassa','debugpy']:
    try:
        importlib.import_module(m)
        print(f'  OK  {m}')
    except Exception as e:
        print(f'  FAIL {m}: {e}')
"
```

---

## 📁 Структура проекта

```
ivc_track/
├── .dockerignore
├── .env                    # (не в git) реальные переменные
├── .env.example            # шаблон
├── .gitignore
├── .streamlit/
│   └── config.toml
├── .vscode/
│   └── settings.json       # настройки Pylance
├── .deps_backup/           # бэкапы зависимостей (не в git)
├── Manage_ivc_track.sh     # управление сервисом
├── restart_ivc_track.sh    # перезапуск с проверкой
├── common_soap.py          # общие SOAP-функции
├── ivc_track.png           # логотип
├── main.py                 # точка входа
├── pages/
│   ├── ivc_track.py
│   ├── yookassa.py
│   └── yookassa_return_url.py
├── requirements.in         # прямые зависимости
├── requirements.txt        # сгенерированный
├── update_payments.py      # фоновое обновление платежей
└── yookassa_common.py      # общие функции ЮKassa
```

---

## 🔍 Диагностика

### Проверить, что сервис работает

```bash
# Статус
sudo systemctl status ivc_track-debug.service --no-pager

# Порты
sudo ss -tlnp | grep -E "8505|5681"

# Отклик
curl -sS --max-time 10 -o /dev/null -w "HTTP %{http_code}, %{time_total}s\n" \
    http://127.0.0.1:8505/

# Health endpoint
curl -sS --max-time 5 http://127.0.0.1:8505/_stcore/health
```

### Если сервис перезапускается в цикле

```bash
# Счётчик рестартов
sudo systemctl show -p NRestarts --value ivc_track-debug.service

# Логи за последние 5 минут
sudo journalctl -u ivc_track-debug.service --since "5 min ago" --no-pager

# Ошибки приложения
tail -50 /var/www/html/ivc_track/streamlit-debug.error.log
```

### Если приложение тормозит

```bash
# CPU главного процесса
PY_PID=$(pgrep -f "debugpy.*5681.*streamlit run main.py" | head -1)
ps -p "$PY_PID" -o pid,pcpu,pmem,etime,args

# Профилирование Python
sudo /var/www/html/ivc_track/venv/bin/py-spy dump --pid "$PY_PID"

# Соединения
sudo ss -tnp | grep 8505
```

### Если `debugpy` не подключается

```bash
# Проверить, что порт слушается
sudo ss -tlnp | grep 5681

# Проверить, что процесс жив
pgrep -af "debugpy.*5681"

# Проверить конфликт портов
sudo ss -tlnp | grep 5680  # не занят ли другим проектом

# Перезапустить debug-сессию
./Manage_ivc_track.sh restart-debug
```

### Логи

| Файл | Назначение |
|---|---|
| `streamlit-debug.log` | stdout приложения |
| `streamlit-debug.error.log` | stderr приложения |
| `streamlit.log` | stdout продакшн-режима |
| `journalctl -u ivc_track-debug.service` | логи systemd |

### Ротация логов

`logrotate` настроен на `/etc/logrotate.d/ivc_track`:

```bash
# Проверить конфиг
sudo logrotate -d /etc/logrotate.d/ivc_track

# Принудительно прогнать
sudo logrotate -v -f /etc/logrotate.d/ivc_track
```

---

## 🤝 Контрибьютинг

1. Форкните репозиторий
2. Создайте ветку: `git checkout -b feature/my-feature`
3. Закоммитьте: `git commit -m "Add my feature"`
4. Запушьте: `git push origin feature/my-feature`
5. Откройте Pull Request

### Перед коммитом

```bash
# Проверить, что нет секретов
git diff --cached | grep -iE "password|secret|token|api_key"

# Проверить, что venv не попал
git status --short | grep venv && echo "❌ venv!" || echo "✅ ok"
```

---

## 📄 Лицензия

MIT License. См. файл `LICENSE` (если есть).

---

## 📞 Контакты

- **GitHub:** [@bjdanko5](https://github.com/bjdanko5)
- **Репозиторий:** [bjdanko5/ivc_track](https://github.com/bjdanko5/ivc_track)

---

<p align="center">
  <sub>Сделано с ❤️ для АО «ИВЦ ЖКХ»</sub>
</p>