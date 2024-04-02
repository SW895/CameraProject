from djbackend.celery import app
from .models import CustomUser
import socket
import os
import json
import logging


@app.task
def aprove_user(user):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    msg = {'request_type':'aprove_user_request', 
               'username':user.username, 
               'email':user.email}
    try:
        sock.connect((os.environ.get('INTERNAL_HOST', '127.0.0.1'),
                      int(os.environ.get('INTERNAL_PORT', '20900'))))
    except socket.error as error:
        logging.info('%s', error)
    else: 
        sock.send(json.dumps(msg).encode())
    sock.close()
    

@app.task
def clean_denied():
    denied_users = CustomUser.objects.filter(is_active=False, admin_checked=True)
    for user in denied_users:
        user.delete()


@app.task
def check_nonactive():
    nonactive = CustomUser.objects.filter(is_active=False, admin_checked=False)
    for user in nonactive:
        aprove_user(user)
