import json
import psycopg
import datetime
from datetime import datetime
from psycopg.types.json import Jsonb
from psycopg import sql

now = datetime.now()
new_item_1 = { "data_created":now.isoformat(), "human_det":True, "cat_det":True }
json1 = json.dumps(new_item_1)
json_encoded = json1.encode()


conn = psycopg.connect(dbname='dj_test', user='test_dj', password=123, host='localhost', port='5432')
cur = conn.cursor()

json_decoded = json_encoded.decode()
dict_in = json.loads(json_decoded)

columns = dict_in.keys()
values = [new_item_1[column] for column in columns]
print(values)
ret = sql.SQL('INSERT INTO main_archivevideo({fields}) VALUES ({values})').format(
    fields=sql.SQL(',').join([sql.Identifier(column) for column in columns]),
    values=sql.SQL(',').join(values),
)


cur.execute(ret)
conn.commit()
cur.close()

#print(qq.filter(data_created__range=(date1,date2)))
#print(qq.filter(data_created__date=date1))