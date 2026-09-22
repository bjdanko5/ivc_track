import streamlit as st
from yookassa_common import yookassa_Настройки
from yookassa_common import yookassa_config
import os
import subprocess
import psutil  # нужно установить: pip install psutil
import time 

spinner_container = None
yookassa_config = yookassa_Настройки()

def is_process_running(process_name):
    """Проверяет, запущен ли процесс с указанным именем"""
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if process_name in ' '.join(proc.info['cmdline'] or []):
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return False
def is_default_page(current_page):
    if "active_page" in  st.query_params:   
        active_page  = st.query_params["active_page"] 
        if active_page == current_page:
           return True 
    else: 
        if current_page == "ivc_track" :
            return True
        else: 
            return False
    return False    
def Роутинг():
    pages = {
    'Сервисы АО "ИВЦ ЖКХ"': [
        st.Page("pages/ivc_track.py", title="Отслеживание уведомлений", icon = ":material/login:" ,default = is_default_page("ivc_track")),   
        st.Page("pages/yookassa.py", title="Оплата через ЮKassa", icon = ":material/login:" , default = is_default_page("yookassa")), 
        st.Page("pages/yookassa_return_url.py", title="Отслеживание ЮKassa", icon = ":material/login:" ,default = is_default_page("yookassa_return_url")),   
    ],
   
    }
    pg = st.navigation(pages)  
    pg.run() 


# # Проверяем, был ли уже запущен процесс update_payments.py
# if not os.path.exists('/var/www/html/ivc_track/update_payments_done.txt'):
#     # Запускаем update_payments.py как подпроцесс
#     subprocess.Popen(["python", "update_payments.py"])
#     # Создаем файл-флаг, указывающий, что update_payments.py был запущен
#     open('/var/www/html/ivc_track/update_payments_done.txt', 'w').close()
# Проверяем, нужно ли запускать update_payments.py
flag_file = '/var/www/html/ivc_track/update_payments_done.txt'
script_name = 'update_payments.py'

project_dir = '/var/www/html/ivc_track'
flag_file = os.path.join(project_dir, 'update_payments_done.txt')
log_file = os.path.join(project_dir, 'update_payments.log')
script_path = os.path.join(project_dir, 'update_payments.py')

#if not os.path.exists(flag_file) and not is_process_running(script_name):
if not is_process_running(script_name):    
    try:
        # Запускаем скрипт в фоновом режиме
        # process = subprocess.Popen(
            # ["python", script_name],
            # stdout=subprocess.PIPE,
            # stderr=subprocess.PIPE,
            # start_new_session=True  # Отвязываем от родительского процесса
        # )
       with open(log_file, 'w') as log:
        # Запускаем процесс с перенаправлением вывода в лог-файл
        process = subprocess.Popen(
            ["python","-Xfrozen_modules=off", script_path],
            stdout=log,        # stdout пишем в лог
            stderr=log,        # stderr пишем в лог
            start_new_session=True,
            stdin=subprocess.DEVNULL,
            cwd=project_dir,   # Устанавливаем рабочую директорию
            env=os.environ.copy()
        )
        # Создаем файл-флаг
        with open(flag_file, 'w') as f:
            f.write(f"Started at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"PID: {process.pid}\n")
        
        #st.success("✅ Процесс обновления платежей запущен!")
        
    except Exception as e:
        pass
        #st.error(f"❌ Ошибка запуска: {e}")
else:
    if os.path.exists(flag_file):
        pass
        #st.info("ℹ️ Процесс обновления платежей уже был запущен ранее")
    else:
        pass
        #st.info("ℹ️ Процесс обновления платежей уже выполняется")   
Роутинг()        
