import streamlit as st
from yookassa import Configuration
from yookassa import Payment
import var_dump as var_dump
import json
from yookassa_common import handle_exceptions_soap  

st.set_page_config(
    page_title="Отлеживание оплат ЮКасса",
    page_icon="🧊",
    layout="wide",
    initial_sidebar_state="collapsed",
    )    

from yookassa_common import RerouteIfMAIN
import os
RerouteIfMAIN(__name__,os.path.basename(__file__))

if "IdTran" in st.query_params:
    IdTran = st.query_params["IdTran"]  
    
    Tran =json.loads(handle_exceptions_soap("GetTranByIdTran", IdTran = IdTran))
    #st.session_state.yookassa_config["ivcBaseCode"] =Tran["ivcBaseCode"]      #"04"
    #st.session_state.yookassa_config['ИДМагазинаYK'] = Tran["ИДМагазинаYK"]   #994463"
    #st.session_state.yookassa_config['КлючМагазинаYK'] =Tran["КлючМагазинаYK"]#"test_Eo6SZA8D2c0Hj9Y5kmD38cM3GiWwO7yDVTAqkFuCh3I"
    #st.session_state.yookassa_config['ИДКвитанции'] = Tran["ИДКвитанции"]

    Configuration.configure(Tran['ИДМагазинаYK'],
                            Tran['КлючМагазинаYK'])
    try: 
      res = Payment.find_one(Tran['ИДКвитанции'])
    except Exception as e:
        st.markdown("Оплата не произведена. ИД Квитанции:"+Tran['ИДКвитанции'])  
        st.stop()
    #st.write(var_dump.var_dump(res))
    if res.status =="succeeded":
        st.markdown("Оплата произведена успешно.ИД Квитанции:"+Tran['ИДКвитанции'])
        response = handle_exceptions_soap("AcceptPaymentYK",
                                            ivcBaseCode = Tran['ivcBaseCode'] ,
                                            ИДКвитанции = Tran['ИДКвитанции']
                                        )
        if st.session_state.get("soap_error",None):
            st.stop()
        st.markdown(f'Оплата зафиксирована в БД АО "ИВЦ ЖКХ". ИД Квитанции:{Tran["ИДКвитанции"]}')
    else:
        st.markdown(f"Оплата не завершена. Статус:[{res.status}]. ИД Квитанции:{Tran['ИДКвитанции']}")        
else:
    try:
        st.markdown("## Журнал обработки ")
        st.markdown('<span style="font-size: 12px;">[последние 300 строк]</span>', unsafe_allow_html=True)
        st.divider()
        with open("update_payments.log", "r", encoding='utf-8', errors='replace') as file:
            lines = file.readlines()
            last_100_lines = lines[-300:]
            for line in last_100_lines:
                st.write(line)
    except FileNotFoundError:
        st.error("Файл не найден.")
    except Exception as e:
        st.error(f"Произошла ошибка: {e}")
    st.stop()
    st.markdown("#### Обработка незавершенных платежей")
    response = handle_exceptions_soap("GetNotAcceptedTranYK")
    if st.session_state.get("soap_error",None):
        st.stop()
    if not json.loads(response)['NotAcceptedTrans']:
        st.stop()    
    else:
        NotAcceptedTrans = json.loads(response)['NotAcceptedTrans']    
        try:
            Mags_json = handle_exceptions_soap("GetMagsYK")
            if st.session_state.get("soap_error",None):
                st.stop()
            Mags = json.loads(Mags_json)
        except Exception as e:
            st.session_state.soap_error = str(e)
            st.stop()
        trans_to_del = []    
        for Mag in Mags['Mags']:    
            #st.session_state.yookassa_config["ivcBaseCode"] = Mag["ivcBaseCode"]      #"04"
            #st.session_state.yookassa_config['ИДМагазинаYK'] = Mag["ИДМагазинаYK"]   #994463"
            #st.session_state.yookassa_config['КлючМагазинаYK'] = Mag["КлючМагазинаYK"]#"test_Eo6SZA8D2c0Hj9Y5kmD38cM3GiWwO7yDVTAqkFuCh3I"
            Configuration.configure(Mag["ИДМагазинаYK"],Mag['КлючМагазинаYK']) 
            
            selected_trans = [Tran for Tran in NotAcceptedTrans if Tran.get('ИДМагазинаYK') == st.session_state.yookassa_config['ИДМагазинаYK']]
            for Tran in selected_trans:
                res = Payment.find_one(Tran['ИДКвитанции'])
                #st.write(var_dump.var_dump(res))
                if res.status =="succeeded":
                    st.markdown("Оплата произведена успешно.ИД Квитанции:"+Tran['ИДКвитанции'])
                    handle_exceptions_soap("AcceptPaymentYK",
                                            ivcBaseCode = Mag['ivcBaseCode'],
                                            ИДКвитанции = Tran['ИДКвитанции'])
                    if st.session_state.get("soap_error",None):
                        st.stop()    

                    st.markdown('Оплата зафиксирована в БД АО "ИВЦ ЖКХ".ИД Квитанции:'+Tran['ИДКвитанции'])
                    trans_to_del.append(Tran['ИДКвитанции'])
                else:
                    if res.status=="canceled":
                        st.markdown("Оплата отменена.Статус:["+res.status+"].ИД Квитанции:"+Tran['ИДКвитанции'])
                        #собираем ИДКвитанций в массив для удаления
                        trans_to_del.append(Tran['ИДКвитанции'])
                        pass
                    else:
                        st.markdown("Оплата не завершена.Статус:["+res.status+"].ИД Квитанции:"+Tran['ИДКвитанции'])
        #чистим базу от ненужных транзакций
        trans_to_del_json = json.dumps(trans_to_del)
        response = handle_exceptions_soap("DeleteTransYK",
                                            trans_to_del_json=trans_to_del_json)
        if st.session_state.get("soap_error",None):
            st.stop()    
