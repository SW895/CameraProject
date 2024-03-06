"""
obj1 = ['aaa', [1,2]]
obj2 = ['bbb', [3]]

dicti = {'aaa': [1,2], 'bbb':[3]}
if 'ccc' in dicti:
    print('True')
else:
    dicti['ccc'] = [1,2,3]
    print('False')

print(dicti)
print(dicti['ccc'][1])

for i in dicti['ccc']:
    print(i)
"""
import datetime, time

a = datetime.datetime.now()
time.sleep(10)
b = datetime.datetime.now()

print((b-a).seconds)