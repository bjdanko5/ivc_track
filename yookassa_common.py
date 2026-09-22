import streamlit as st
import uuid
import var_dump as var_dump
import json
import requests
import time
yookassa_config={}
def RerouteIfMAIN(prm__name__,current_script):
    import os
    def add_active_page_param(url, script_name):
        page_name = os.path.splitext(script_name)[0]  # Имя страницы соответствует имени скрипта без расширения
        if page_name in script_name and "active_page" not in url:
            if "?" in url:
                url += "&active_page=" + page_name
            else:
                url += "?active_page=" + page_name
        return url
    def create_query_string(query_params):
        if not query_params:
            return ""
        query_string = "&".join([f"{key}={value}" for key, value in query_params.items()])
        return query_string
    
    if prm__name__ == "__main__":        
        str_query_params =create_query_string(st.query_params)
        #сформировать строку параметров из st.query_params в str_query_params
        url = st.streamlit.context.headers._headers['Origin'][0]+"/?"+ str_query_params
        # Получить имя текущего исполняемого скрипта
        #current_script = os.path.basename(__file__)   
        url = add_active_page_param(url, current_script)
        nav_script = """
            <meta http-equiv="refresh" content="0; url='%s'">
        """ % (url)
        st.write(nav_script, unsafe_allow_html=True) #Перенаправление через main.py(streamlit)

def generate_uuid():
    return str(uuid.uuid4())

def yookassa_Настройки_IdTran():
    if not "IdTran" in  st.query_params:   
        return
    response = handle_exceptions_soap("GetTranByIdTranConfig",IdTran = st.query_params["IdTran"])
    if st.session_state.get("soap_error",None) or response == "":
        return           
    yookassa_config = json.loads(response)
    st.session_state.yookassa_config = yookassa_config

def yookassa_Настройки():
    global yookassa_config
    if "yookassa_config" in st.session_state:
        yookassa_config = st.session_state.yookassa_config
        yookassa_Настройки_IdTran()
        return
    yookassa_config  = {
    "КодДоступаЛС": None,   
    "url" : "http://192.168.10.128/zkh_lk1/ws/WebLK?wsdl",
    "username":'Администратор',
    "password":'',
    "urlLS"  : None,
    'АдресЛС':None,
    'ФИО':None,
    'КодыСБ' :None,
    'ПолучателиСБ' :None,
    'Приборы' :None,
    "usernameLS" :'Администратор',
    "passwordLS" : '71243339',
    "ivcBaseCode" : None,
    "LsВвод"         : None,
    "Ls"         : None,
    "LsВвод"         : None,
    "codeSB"     :"",
    "encoding":'utf-8',
    "eng_date_format":"%m/%d/%Y %I:%M:%S %p",
    "rus_date_format":'%d.%m.%Y %H:%M:%S',
    "logo_url" : "https://rostov-zkh.ru/wp-content/uploads/2024/01/%D0%91%D0%B5%D0%B7-%D0%B8%D0%BC%D0%B5%D0%BD%D0%B8-5.png",
    "logo_name": "", 
    "session_timeout":90 
    }
    st.session_state.yookassa_config = yookassa_config 
    yookassa_Настройки_IdTran()
    
def get_soap_service(url,username,password):
    from zeep import Settings, Client
    from zeep.cache import InMemoryCache
    from zeep.transports import Transport 
    from requests import Session
    from requests.auth import HTTPBasicAuth
    soap_error = ""
    try:
        session = Session()
        session.encoding = "utf-8"
        session.auth = HTTPBasicAuth(username.encode(session.encoding), password.encode(session.encoding))
        settings = Settings(strict=True)
        cache = InMemoryCache(timeout = 60)
        transport = Transport(session=session, timeout=60, operation_timeout=30,cache=cache)
        client = Client(url, settings=settings, transport=transport)
    except Exception as e:
        try:
            client = Client(url, settings=settings, transport=transport)    
        except Exception as e:
            soap_error = str(e)
            return None,soap_error
        return client.service,soap_error
    return client.service,soap_error


def handle_exceptions_soap(method_name, max_retries=3, retry_delay=1, **kwargs):
    soap_error = ""
    if "soap_service" not in st.session_state:
        soap_service,soap_error = get_soap_service(yookassa_config["url"],
                                                   yookassa_config["username"],
                                                   yookassa_config["password"]) 
        st.session_state.soap_service = soap_service 
        
    if soap_error:
        st.session_state.soap_error = soap_error
        return soap_error
    
    if "soap_error" in st.session_state:
        del st.session_state.soap_error

    soap_service = st.session_state.soap_service      

    attempts = 0
    error_message = ""
    
    while attempts < max_retries:
        try:
            response = getattr(soap_service, method_name)(**kwargs)
            return response
        except requests.exceptions.RequestException as e:
            error_message = "Ошибка при взаимодействии с SOAP-сервисом (попытка " + str(attempts+1) + "): " + str(e)
            print(error_message)
            attempts += 1
            time.sleep(retry_delay)
        except Exception as e:
            error_message = "Ошибка внутри SOAP-метода: " + str(e)
            print(error_message)
            break

    print("Не удалось выполнить вызов SOAP-сервиса после", max_retries, "попыток")
    return error_message
# Пример использования
#handle_exceptions_soap(soap_service, "getByAccessCodeLs", accessCodeLs=КодДоступаЛС)
#error = handle_exceptions_soap(soap_service, "getByAccessCodeLs", accessCodeLs=КодДоступаЛС)
def ЗаполнитьЗначенияСвойств(Приемник, Источник):
    for key, value in Источник.items():
        if key in Приемник:
            Приемник[key] = value