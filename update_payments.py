import time
import requests
from yookassa import Configuration
from yookassa import Payment
import var_dump as var_dump
import json
import datetime
import sys
from yookassa_common import get_soap_service

def handle_exceptions_soap(method_name, max_retries=3, retry_delay=1, **kwargs):
    url ="http://192.168.10.128/zkh_lk1/ws/WebLK?wsdl"
    username="Администратор"
    password=""
    soap_service,soap_error = get_soap_service(url,
                                    username,
                                    password) 
    if not soap_service:
        return soap_error
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
def update_payments():
    trans_to_del = []
    file_path = "update_payments.log"
    content=""
    current_datetime = datetime.datetime.now()
    
    content+=current_datetime.strftime("%d.%m.%Y %H:%M:%S")+":Обработка незавершенных платежей"+"\n"
    try:
        response = handle_exceptions_soap("GetNotAcceptedTranYK")
    except Exception as e:
        content+=str(e)+"\n"
        content+="Нет подключения к серверу ЛК"+"\n"
        NotAcceptedTrans = False
    try:    
        NotAcceptedTrans = json.loads(response)
    except Exception as e:
        content+=str(e)+"\n"
        content+="Проверьте лицензии на сервере ЛК"+"\n"
        NotAcceptedTrans = False
    if not NotAcceptedTrans:
        content+="Нет транзакций"+"\n"
        pass    
    else:
        NotAcceptedTrans = json.loads(response)['NotAcceptedTrans']    
        try:
            Mags_json = handle_exceptions_soap("GetMagsYK")
            Mags = json.loads(Mags_json)
        except Exception as e:
            content+="Нет транзакций"+"\n"
            pass
        for Mag in Mags['Mags']:    
            Configuration.configure(Mag["ИДМагазинаYK"],Mag["КлючМагазинаYK"]) 
            selected_trans = [Tran for Tran in NotAcceptedTrans if Tran.get('ИДМагазинаYK') == Mag["ИДМагазинаYK"]]
            for Tran in selected_trans:
                res = Payment.find_one(Tran['ИДКвитанции'])
                #st.write(var_dump.var_dump(res))
                if res.status =="succeeded":
                    content+="Оплата произведена успешно.ИД Квитанции:"+Tran['ИДКвитанции']+"\n"
                    try:
                        response = handle_exceptions_soap("AcceptPaymentYK",
                                                          ivcBaseCode = Mag['ivcBaseCode'],
                                                          ИДКвитанции = Tran['ИДКвитанции'])
                        content+='Оплата зафиксирована в БД АО "ИВЦ ЖКХ".ИД Квитанции:'+Tran['ИДКвитанции']+"\n"
                        trans_to_del.append(Tran['ИДКвитанции'])
                    except Exception as e:
                        content+="Нет транзакций"+"\n"
                        pass    
                else:
                    if res.status=="canceled":
                        content += f"Оплата отменена. Статус:[{res.status}]. ИД Квитанции:{Tran['ИДКвитанции']}\n"
                        #собираем ИДКвитанций в массив для удаления
                        trans_to_del.append(Tran['ИДКвитанции'])
                        pass
                    else:
                        content += f"Оплата не завершена. Статус:[{res.status}]. ИД Квитанции:{Tran['ИДКвитанции']}\n"
            #чистим базу от ненужных транзакций
 
    try:    
        #with open(file_path, 'a') as file:
        #    file.write(content)
        import os    
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path)  # размер файла в байтах
            if file_size > 1024 * 1024:  # 1 МБ = 1024 КБ = 1024 * 1024 байт
                with open(file_path, 'w') as file:
                    file.write(content)
                    file.flush() 
            else:
                with open(file_path, 'a') as file:
                    file.write(content)
                    file.flush() 
        else:
            with open(file_path, 'w') as file:
                file.write(content)
                file.flush() 

    except Exception as ex:
        # В случае других исключений, записываем ошибку в файл
        with open("update_payments_error.log", "a") as error_file:
            error_file.write(f"Ошибка записи в основной журнал: {ex}\n")
    return trans_to_del
while True:
    current_datetime = datetime.datetime.now()
    #print("Обработка платежей:", current_datetime, file=sys.stdout)
    file_path = "update_payments.log"
    log_line = "Обработка платежей: " + str(current_datetime) + "\n"
    try:
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write(log_line)
            f.flush()
    except:
        pass
    trans_to_del = update_payments()
    try:
        trans_to_del_json = json.dumps(trans_to_del)
        response = handle_exceptions_soap("DeleteTransYK",trans_to_del_json = trans_to_del_json)
    except Exception as e:
        pass
    time.sleep(60)  # 300 секунд = 5 минут