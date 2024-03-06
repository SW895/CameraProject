import json
import datetime
from datetime import datetime
import socket



date1 = '2024_01_20T14_25_34'
date2 = '2024_02_12T09_23_12'
date3 = '2024_05_24T23_23_12'
date4 = '2024_09_09T17_09_01'
date1 = datetime.strptime(date1,'%Y_%m_%dT%H_%M_%S')
date2 = datetime.strptime(date2,'%Y_%m_%dT%H_%M_%S')
date3 = datetime.strptime(date3,'%Y_%m_%dT%H_%M_%S')
date4 = datetime.strptime(date4,'%Y_%m_%dT%H_%M_%S')

new_item_1 = {"date_created":date1.isoformat(), 
              "human_det":True, 
              "cat_det":False, 
              "chiken_det":False, 
              "car_det":False 
}
new_item_2 = {"date_created":date2.isoformat(), 
              "human_det":True, 
              "cat_det":True, 
              "chiken_det":False, 
              "car_det":False 
}
new_item_3 = {"date_created":date3.isoformat(), 
              "human_det":True, 
              "cat_det":False, 
              "chiken_det":True, 
              "car_det":False 
}
new_item_4 = {"date_created":date4.isoformat(), 
              "human_det":True, 
              "cat_det":False, 
              "chiken_det":False, 
              "car_det":True 
}

json1 = json.dumps(new_item_1)
json2 = json.dumps(new_item_2)
json3 = json.dumps(new_item_3)
json4 = json.dumps(new_item_4)

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(('127.0.0.1', 10900))
#sock.connect(('213.183.51.61', 10900))

"""
with open('db.json', 'a') as outfile:
    outfile.write(json1 + "\n")
    outfile.write(json2 + "\n")


result = []
with open('db.json', 'r') as outfile2:
    for json_obj in outfile2:
        json_objz = json.loads(json_obj)
        result.append(json_objz)
"""

reply = 'SaveDB'
sock.send(reply.encode())
answer = sock.recv(1024)

i = 0
#records = [json1, json2, json3, json4]
records = json1 + '|' + json2 + '|' +json3 + '|' +json4 + '|'
if answer.decode() == 'accepted': 
    sock.sendall(records.encode())
sock.close()
