import streamlit as st
import var_dump as var_dump
import json


global spinner_container
 
from yookassa_common import handle_exceptions_soap  
from yookassa_common import generate_uuid
from yookassa_common import yookassa_config
from yookassa_common import ЗаполнитьЗначенияСвойств


st.set_page_config(
    page_title="Оплата ЮКасса",
    page_icon="🧊",
    layout="wide",
    initial_sidebar_state="collapsed",
    )      

from yookassa_common import RerouteIfMAIN
import os
RerouteIfMAIN(__name__,os.path.basename(__file__))

def НайтиЛСПоКодуДоступа():
    if  not st.session_state.get('КодДоступаЛС',None):
        #del st.session_state.yookassa_config
        return
    if  not st.session_state.get('LsВвод',None):  
        #del st.session_state.yookassa_config
        return
    
    if  st.session_state.КодДоступаЛС.strip()=='' or st.session_state.LsВвод.strip()=='':
        del st.session_state.yookassa_config
        return

    LsВвод = st.session_state.LsВвод   
    st.session_state.yookassa_config['LsВвод'] = st.session_state.LsВвод
    yookassa_config['LsВвод'] = st.session_state.LsВвод  

    КодДоступаЛС = st.session_state.КодДоступаЛС 
    st.session_state.yookassa_config['КодДоступаЛС'] = st.session_state.КодДоступаЛС  
    yookassa_config['КодДоступаЛС'] = st.session_state.КодДоступаЛС  

    st.session_state.КОплатеИзменено = False

    response = handle_exceptions_soap("getByAccessCodeLs",
                                       accessCodeLs=КодДоступаЛС,
                                       Ls = LsВвод)
    if st.session_state.get("soap_error",None):
       return   
    
    if json.loads(response)['Реквизиты'] == None or json.loads(response)['Реквизиты']['Ls'] == '':
        КодДоступаЛС = st.session_state.get('КодДоступаЛС',None)
        LsВвод = st.session_state.get('LsВвод',None)
        del st.session_state.yookassa_config
        st.session_state.КодДоступаЛС = КодДоступаЛС
        st.session_state.LsВвод = LsВвод
        st.session_state.soap_error="Некорректный код доступа ЛС или ему не соответствует ни один ЛС."
        return    
    
    ls_json = json.loads(response) # Преобразование JSON-ответа в словарь

    yookassa_config['urlLS']       = ls_json['Реквизиты']['ivcBaseWdsl'] #.replace('Сервис', '')
    yookassa_config['ivcBaseCode'] = ls_json['Реквизиты']['ivcBaseCode']
    yookassa_config['Ls']          = ls_json['Реквизиты']['Ls']
    yookassa_config['codeSB']      = st.session_state.get("КодСБ","") 

    response = handle_exceptions_soap("getLsData",
                                        ivcBaseCode = yookassa_config["ivcBaseCode"],
                                        Ls = yookassa_config["Ls"] ,
                                        codeSB = yookassa_config["codeSB"])
    
    if st.session_state.get("soap_error",None):
       return   
    
    ls_data_json = json.loads(response) # Преобразование JSON-ответа в словарь

    ЗаполнитьЗначенияСвойств(yookassa_config,ls_data_json['ДанныеЛС'])
    st.session_state.yookassa_config = yookassa_config

def НайтиЛСПоКодуДоступаСпиннер():
    global spinner_container 
    with spinner_container:
        st.markdown("")
        st.markdown("") 
        with st.spinner('Запрос выполняется...'): 
            НайтиЛСПоКодуДоступа() 

def on_change_Приборы():
    import json
    if "edited_rows" not in st.session_state.Приборы_editor:
        return
    edited_rows = st.session_state.Приборы_editor["edited_rows"]  
    for row_id, row in edited_rows.items():
        st.session_state.yookassa_config["Приборы"][row_id]["ТекущееПоказание"] =  edited_rows[row_id]["ТекущееПоказание"]
        Прибор = st.session_state.yookassa_config["Приборы"][row_id]
        response = handle_exceptions_soap("WritePok",ivcBaseCode=st.session_state.yookassa_config["ivcBaseCode"],
                                                    КодПУ = Прибор["КодПрибора"],
                                                    ПредыдущееПоказание = Прибор["ПредыдущееПоказание"], 
                                                    Показание = Прибор["ТекущееПоказание"],
                                                    сТарифныйПлан = "1")
        if st.session_state.get("soap_error",None):
            return   
        st.session_state.СообщениеЗаписатьПоказание = response     

def on_change_ПолучателиСБ():
    if "edited_rows" not in st.session_state.ПолучателиСБ_editor:
        return
    edited_rows = st.session_state.ПолучателиСБ_editor["edited_rows"]
    for row_id, row in edited_rows.items():
        st.session_state.yookassa_config["ПолучателиСБ"][row_id]["Остаток"] =  edited_rows[row_id]["Остаток"] 
        st.session_state.yookassa_config = st.session_state.yookassa_config
        st.session_state.КОплатеИзменено = True 

def ЗаписатьОплату():
    import json
    import yookassa
    from yookassa import Configuration
    from yookassa import Payment

    st.session_state.yookassa_config['codeSB'] = st.session_state.КодСБ
    ПолучателиСБ = st.session_state.yookassa_config["ПолучателиСБ"]
    ОберткаПолучателиСБ = {}
    ОберткаПолучателиСБ["Получатели"] = ПолучателиСБ  

    #Получить рачетный счет,ид магазина, ключ магазина    
    response = handle_exceptions_soap("GetRSYooKassa0925",
                                       ivcBaseCode = st.session_state.yookassa_config['ivcBaseCode'] ,
                                       КодСБ = st.session_state.yookassa_config['codeSB'], 
                                       ЛС = st.session_state.yookassa_config['Ls'] 
                                      )           
    if st.session_state.get("soap_error",None):
        return   
    st.session_state.rs_json = json.loads(response) # Преобразование JSON-ответа в словарь
    st.session_state.yookassa_config['ИДМагазинаYK'] = st.session_state.rs_json["metadata"]['ИДМагазинаYK']
    st.session_state.yookassa_config['КлючМагазинаYK'] = st.session_state.rs_json["metadata"]['КлючМагазинаYK']
    del st.session_state.rs_json["metadata"]['ИДМагазинаYK']
    del st.session_state.rs_json["metadata"]['КлючМагазинаYK']
    #st.session_state.yookassa_config['ИДМагазинаYK']="994463"
    #st.session_state.yookassa_config['КлючМагазинаYK']="test_Eo6SZA8D2c0Hj9Y5kmD38cM3GiWwO7yDVTAqkFuCh3I"

    st.session_state.yookassa_config["IdTran"] = generate_uuid()
    DPayment ={}
    DPayment["amount"] = {}
    DPayment["amount"]["value"] = st.session_state.КОплате
    DPayment["amount"]["currency"] = "RUB"
    DPayment["capture"] = True
    DPayment["payment_order"]={}
    DPayment["payment_order"]["type"] = "utilities"
    DPayment["payment_order"]["amount"] = {}
    DPayment["payment_order"]["amount"]["value"] = st.session_state.КОплате
    DPayment["payment_order"]["amount"]["currency"] = "RUB"
      
    DPayment["payment_order"]["recipient"] = st.session_state.rs_json["recipient"]
    DPayment["payment_order"]["payment_period"] = st.session_state.rs_json["payment_period"]
    DPayment["payment_order"]["payment_purpose"] = st.session_state.rs_json["payment_purpose"]
    
    DPayment["payment_order"]["account_number"] = st.session_state.yookassa_config['Ls']

    DPayment["metadata"] = st.session_state.rs_json["metadata"]
    st.session_state.yookassa_config['ФИО'] = st.session_state.yookassa_config['ФИО'].replace('.', '')
    DPayment["metadata"]["payerName"] = st.session_state.yookassa_config['ФИО']
    DPayment["metadata"]["payNumber"] = st.session_state.yookassa_config['Ls']
    DPayment["metadata"]["payerAddress"] = st.session_state.yookassa_config['АдресЛС']
    DPayment["confirmation"] = {}
    DPayment["confirmation"]["type"] = "redirect"
    
    myurl = st.streamlit.context.headers._headers['Origin'][0]
    
    #DPayment["confirmation"]["return_url"] = myurl+"http://176.213.140.14:8501/yookassa_return_url/?IdTran="+st.session_state.yookassa_config["IdTran"]
    #DPayment["confirmation"]["return_url"] = myurl+"/?active_page=yookassa_return_url&IdTran="+st.session_state.yookassa_config["IdTran"]
    DPayment["confirmation"]["return_url"] = myurl+"/?active_page=yookassa&IdTran="+st.session_state.yookassa_config["IdTran"]
    #DPayment
    Configuration.configure(st.session_state.yookassa_config['ИДМагазинаYK'],
                            st.session_state.yookassa_config['КлючМагазинаYK']) 
    res = Payment.create(DPayment)
    #st.write(var_dump.var_dump(res))
    ИДКвитанции = res.id 
    st.session_state.yookassa_config["ИДКвитанции"] = ИДКвитанции
    response = handle_exceptions_soap("WriteTranYKConfig",                                                                                
                                            ivcBaseCode = st.session_state.yookassa_config["ivcBaseCode"],
                                            ИДМагазинаYK = st.session_state.yookassa_config["ИДМагазинаYK"],
                                            КлючМагазинаYK= st.session_state.yookassa_config["КлючМагазинаYK"],
                                            IdTran = st.session_state.yookassa_config["IdTran"], 
                                            ИДКвитанции = st.session_state.yookassa_config["ИДКвитанции"],
                                            Config = json.dumps(st.session_state.yookassa_config,ensure_ascii=False).encode('utf-8') 
                                            )
    if st.session_state.get("soap_error",None):
        return
    
    response = handle_exceptions_soap("WritePaymentYooKassa",ivcBaseCode = st.session_state.yookassa_config['ivcBaseCode'] ,
                                                    ЛС = st.session_state.yookassa_config['Ls'], 
                                                    ФИО = st.session_state.yookassa_config['ФИО'],
                                                    Адрес = st.session_state.yookassa_config['АдресЛС'] ,
                                                    КодСБ = st.session_state.yookassa_config['codeSB'], 
                                                    ИДКвитанции = ИДКвитанции,
                                                    ДетализацияОплаты = ОберткаПолучателиСБ )

    if st.session_state.get("soap_error",None):
        return
                                         
    st.markdown(f'<a href="{res["confirmation"]["confirmation_url"]}" target="_blank">Перейти на страницу подтверждения платежа</a>', unsafe_allow_html=True)
    nav_script = """
        <meta http-equiv="refresh" content="0; url='%s'">
    """ % (res["confirmation"]["confirmation_url"])
    st.write(nav_script, unsafe_allow_html=True) #Перенаправление на страницу оплаты

#главная программа---------------------------------------------------

st.header("Оплата через ЮКassa")
st.subheader("Поиск лицевого счета")
if "yookassa_config" not in st.session_state:
    myurl = st.streamlit.context.headers._headers['Origin'][0]+"/?active_page=yookassa"
    nav_script = """
        <meta http-equiv="refresh" content="0; url='%s'">
    """ % (myurl)
    st.write(nav_script, unsafe_allow_html=True) #Корректное перенаправление на оплату
    st.rerun()
if "LsВвод" in st.session_state.yookassa_config:
    LsВвод = st.session_state.yookassa_config["LsВвод"]
st.text_input(label="Лицевой счет",key ="LsВвод",value = LsВвод, on_change = НайтиЛСПоКодуДоступаСпиннер)
spinner_container =st.container()

if "КодДоступаЛС" in st.session_state.yookassa_config:
    КодДоступаЛС = st.session_state.yookassa_config["КодДоступаЛС"]
st.text_input(label="Код доступа ЛС",key ="КодДоступаЛС",value = КодДоступаЛС, on_change = НайтиЛСПоКодуДоступаСпиннер)


if "IdTran" in st.query_params:
    IdTran = st.query_params["IdTran"]
    del st.query_params["IdTran"]  
    
    from yookassa import Configuration
    from yookassa import Payment
    import var_dump as var_dump

    Configuration.configure(st.session_state.yookassa_config['ИДМагазинаYK'],
                            st.session_state.yookassa_config['КлючМагазинаYK'])
    st.info("ИД Квитанции:"+st.session_state.yookassa_config['ИДКвитанции']+" "+"ИД Транзакции:"+IdTran) 
    try: 
      res = Payment.find_one(st.session_state.yookassa_config['ИДКвитанции'])
      res_status = res.status
    except Exception as e:
       st.error("Оплата не произведена") 
       res_status ="failed"
    if res_status =="succeeded":
        st.success("Оплата произведена успешно.")
        try:
            response = handle_exceptions_soap("AcceptPaymentYK",ivcBaseCode = st.session_state.yookassa_config['ivcBaseCode'] ,
                                                    ИДКвитанции = st.session_state.yookassa_config['ИДКвитанции'])
            st.info('Оплата зафиксирована в БД АО "ИВЦ ЖКХ"')
        except Exception as e:
            st.session_state.soap_error = str(e)
    elif res_status == "failed":
         st.error("Оплата не произведена.") 
    elif res_status == "pending":
         st.error("Оплата обрабатывается в ЮКassa.") 
    if st.session_state.get("soap_error",None):
        st.error(st.session_state.soap_error)            
    if  st.session_state.yookassa_config.get("КодДоступаЛС",None):
        НайтиЛСПоКодуДоступаСпиннер()
    pass

if "soap_error" in st.session_state: 
    st.error(body = st.session_state.soap_error, icon=":material/error:")       
    del st.session_state.soap_error
    if "IdTran" in st.query_params:
        del st.query_params["IdTran"]         
st.divider()

if st.session_state.yookassa_config['Ls']: 
    st.subheader("Данные абонента")   
    if st.session_state.yookassa_config['КодыСБ']:
        КодCБ = st.selectbox(label="Отбор по Коду услуги СБ",options=yookassa_config['КодыСБ'],key="КодСБ",on_change = НайтиЛСПоКодуДоступаСпиннер) 
    st.markdown("**Лицевой счет** "+st.session_state.yookassa_config['Ls'])    
if st.session_state.yookassa_config['АдресЛС']:    
    st.markdown("**Адрес** "+st.session_state.yookassa_config['АдресЛС'])
if st.session_state.yookassa_config['ПолучателиСБ']:
    st.subheader("К оплате задолженности с учетом начисления за текущий период")
    if not st.session_state.get("КОплатеИзменено",False):
      st.info(body="Откорректируйте сумму в столбце :red[К оплате], указав желаемый размер оплаты и нажмите :material/payments: :green[Оплатить]", icon=":material/info:")   
    else:  
      st.warning(body="Откорректирована сумма :red[К оплате].Для оплаты нажмите :material/payments: :green[Оплатить]", icon=":material/info:")   
    column_config = {
    "КодПолучателя": st.column_config.Column(label="Код",width="medium", disabled=True),
    "Получатель": st.column_config.Column(width="medium", disabled=True),
    "Остаток": st.column_config.NumberColumn(label="К оплате",width="large",min_value=0.00, format="%.2f", required=False,step=0.01,default = 0.00)
    }
    ПолучателиСБ_df=st.data_editor(st.session_state.yookassa_config['ПолучателиСБ'],
                                   key='ПолучателиСБ_editor',
                                   on_change = on_change_ПолучателиСБ,
                                   column_config=column_config,
                                   column_order=("КодПолучателя", "Получатель","Остаток"))
    Всего_остаток = sum(item['Остаток'] for item in ПолучателиСБ_df)
    st.session_state.КОплате =  Всего_остаток
    c1,c2 = st.columns([4,6])
    with c1:
        formatted_str = "{:,.2f}".format(Всего_остаток)
        if not st.session_state.get("КОплатеИзменено",False):
            st.markdown("##### Всего к оплате задолженности с учетом начислений :green["+formatted_str+'] руб.')    
        else:                
            st.markdown("##### Всего к оплате (изменено) :green["+formatted_str+'] руб.')    
    with c2:
        Оплатить_button = st.button(label=":green[Оплатить]", key="Оплатить",icon=":material/payments:")    
        if Оплатить_button:
            ЗаписатьОплату()

if st.session_state.yookassa_config['Приборы']:
    st.subheader("Приборы учета")    
    column_config = {
    "КодПрибора": st.column_config.Column(label="Код",width="medium", disabled=True),
    "Прибор": st.column_config.Column(label="Код",width="medium", disabled=True),
    "ЗаводскойНомер": st.column_config.Column(label="Заводской Номер",width="medium", disabled=True),
    "ПредыдущееПоказание": st.column_config.NumberColumn(label="Предыдущее Показание",width="medium",min_value=0.00, format="%.6f",disabled=True),
    "ТекущееПоказание": st.column_config.NumberColumn(label="Текущее Показание",width="medium",min_value=0.00, format="%.6f", required=False)
    } 
    st.info(body="Внесите значение в столбец :red[Текущее Показание].Показания будут приняты к учету в базе данных, даже если не производилась оплата", icon=":material/info:")   
    if "soap_error" in st.session_state: 
        st.error(body = st.session_state.soap_error, icon=":material/error:")       
        del st.session_state.soap_error
    if "СообщениеЗаписатьПоказание" in st.session_state:          
        st.info(body = st.session_state.СообщениеЗаписатьПоказание, icon=":material/info:")       
        del st.session_state.СообщениеЗаписатьПоказание
    st.data_editor(st.session_state.yookassa_config['Приборы'],
                                   key="Приборы_editor",
                                   on_change = on_change_Приборы,
                                   column_config=column_config,                                    
                                   column_order=("КодПрибора", "Прибор","ЗаводскойНомер","ПредыдущееПоказание","ТекущееПоказание"))

#if st.session_state.get("ls_json",None):
#    for key, value in st.session_state.ls_json.items():
#        st.write(f"**{key}**")
#        for subkey, subvalue in value.items():
#            st.write(f"  {subkey}: {subvalue}")
            
#if st.session_state.get("ls_data_json",None):
#    for key, value in st.session_state.ls_data_json.items():
#        st.write(f"**{key}**")
#        for subkey, subvalue in value.items():
#            st.write(f"  {subkey}: {subvalue}")





       