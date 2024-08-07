import asyncio
import psycopg
import logging
from psycopg import sql
from cam_server import RequestBuilder
from settings import (DB_HOST,
                      DB_NAME,
                      DB_PASSWORD,
                      DB_PORT,
                      DB_USER)


class BaseRecordHandler:

    log = logging.getLogger('Base Record Handler')
    save_queue = asyncio.Queue()
    cur = None
    db_conn = None

    def __init__(self, request):
        self.request = request

    async def save(self):
        await self.get_db_connection()
        if self.db_conn:
            return await self.process_records()
        return 'Failed to connect to DB'

    async def get_db_connection(self):
        self.log.info('Connection to DB')
        self.db_conn, self.cur = await connect_to_db()

    async def process_records(self):
        self.log.info('Successfully connected to db')
        while self.save_queue.qsize() > 0:
            record = await self.save_queue.get()
            self.save_queue.task_done()
            self.log.info('Got new record')
            try:
                await self.save_record(record)
            except (Exception, psycopg.Error) as error:
                self.log.error('Error ocured: %s', error)
                await self.send_response('failed')
                return 'Transaction failed'
            else:
                self.log.info('Record saved')

        await self.db_conn.commit()
        await self.send_response('success')
        self.log.info('No more new records')
        return 'Transaction succseed'

    async def save_record(self, record):
        raise NotImplementedError

    async def send_response(self, status):
        builder = RequestBuilder().with_args(status=status)
        response = builder.build()
        self.request.writer.write(response.serialize().encode())
        await self.request.writer.drain()
        self.request.writer.close()
        await self.request.writer.wait_closed()
        await self.cur.close()
        await self.db_conn.close()


class NewVideoRecord(BaseRecordHandler):

    log = logging.getLogger('Video Record')

    async def save_record(self, record):
        columns = record.keys()
        values = sql.SQL(',').join([record[column] for column in columns])
        fields = sql.SQL(',').join([sql.Identifier(column)
                                    for column in columns])
        ret = sql.SQL('INSERT INTO main_archivevideo({fields}) \
                       VALUES ({values});').format(fields=fields,
                                                   values=values,)
        await self.cur.execute(ret)


class CameraRecord(BaseRecordHandler):

    log = logging.getLogger('Camera Record')

    async def save(self):
        await self.get_db_connection()
        if self.db_conn:
            await self.set_all_cameras_to_inactive()
            await self.process_records()
        return 'Failed to connect to DB'

    async def save_record(self, record):
        await self.cur.execute("INSERT INTO \
                                main_camera (camera_name, is_active) \
                                VALUES (%s, True) \
                                ON CONFLICT (camera_name) \
                                DO UPDATE \
                                SET is_active=True;",
                               (record['camera_name'],))
        self.log.info('Camera %s activated', record['camera_name'])

    async def set_all_cameras_to_inactive(self):
        try:
            await self.cur.execute("UPDATE main_camera \
                                   SET is_active=False \
                                   WHERE is_active=True;")
        except (Exception, psycopg.Error):
            self.log.error('No records')
        else:
            self.log.debug('All cameras set to is_active=False')
        finally:
            await self.db_conn.commit()


class UserRecord(BaseRecordHandler):

    log = logging.getLogger('User Record')

    async def save_record(self, record):
        if record['request_result'] == 'aproved':
            await self.cur.execute("UPDATE registration_customuser \
                                    SET is_active=True, admin_checked=True \
                                    WHERE username=(%s);",
                                   (record['username'],))
            self.log.info('User %s successfully activated',
                          record['username'])
        else:
            await self.cur.execute("UPDATE registration_customuser \
                                    SET admin_checked=True \
                                    WHERE username=(%s);",
                                   (record['username'],))
            self.log.info('User %s denied', record['username'])


class ActiveCameras:

    log = logging.getLogger('Get active cameras')

    @classmethod
    async def get_active_camera_list(self):
        self.log.debug('connecting to db')
        self.db_conn, self.cur = await connect_to_db()
        if not self.db_conn:
            self.log.error('Failed to connect to DB')
            return []

        self.log.info('Successfully connected to db')
        await self.cur.execute("SELECT camera_name \
                          FROM main_camera \
                          WHERE is_active=True")
        active_cameras = await self.cur.fetchall()
        await self.cur.close()
        await self.db_conn.close()
        return active_cameras


async def connect_to_db():
    dbname = DB_NAME
    db_user = DB_USER
    db_password = DB_PASSWORD
    db_host = DB_HOST
    db_port = DB_PORT
    logging.debug('CONNECTION TO DB:%s', dbname)
    try:
        db_conn = await psycopg.AsyncConnection.connect(
                                            dbname=dbname,
                                            user=db_user,
                                            password=db_password,
                                            host=db_host,
                                            port=db_port)
    except Exception as error:
        logging.error('FAILED TO CONNECT TO DB: %s', error)
        return None, None
    else:
        cur = db_conn.cursor()
        return db_conn, cur


async def connect_to_db22():
    dbname = 'test_base'
    db_user = 'test_user'
    db_password = 'test_password'
    db_host = '0.0.0.0'
    db_port = '10000'
    logging.debug('CONNECTION TO DB:%s', dbname)
    try:
        db_conn = await psycopg.AsyncConnection.connect(
                                            dbname=dbname,
                                            user=db_user,
                                            password=db_password,
                                            host=db_host,
                                            port=db_port)
    except Exception as error:
        logging.error('FAILED TO CONNECT TO DB: %s', error)
        return None, None
    else:
        cur = db_conn.cursor()
        return db_conn, cur



async def main():
    db_conn, cur = await connect_to_db22()
    if db_conn:
        print('AAAAAAAAAAAAAAA')
    else:
        print('DDDDD')

import docker

client = docker.from_env()
cont = client.containers.list()

logging.critical('%s', cont)
logging.critical('Stopping container')
cont[0].stop()
#loop = asyncio.new_event_loop()
#task = loop.create_task(main())
#loop.run_until_complete(task)