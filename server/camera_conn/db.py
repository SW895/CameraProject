import asyncio
import psycopg
import logging
# import json
import os
from psycopg import sql
# from .camera_utils import ServerRequest


class BaseRecordHandling:

    DEBUG = False
    save_queue = asyncio.Queue()
    cur = None
    db_conn = None

    async def save(self):
        raise NotImplementedError


class NewVideoRecord(BaseRecordHandling):

    log = logging.getLogger('Video Record')

    @classmethod
    async def save(self):
        self.log.info('Connection to DB')
        self.db_conn, self.cur = await connect_to_db(self.DEBUG)
        if not self.db_conn:
            self.log.error('Failed to connect to DB')
            return

        self.log.info('Successfully connected to db')
        while self.save_queue.qsize() > 0:
            record = await self.save_queue.get()
            self.log.info('Got new record')
            columns = record.keys()
            values = sql.SQL(',').join([record[column] for column in columns])
            fields = sql.SQL(',').join([sql.Identifier(column)
                                        for column in columns])
            ret = sql.SQL('INSERT INTO main_archivevideo({fields}) \
                           VALUES ({values});').format(fields=fields,
                                                       values=values,)
            try:
                await self.cur.execute(ret)
            except psycopg.Error as error:
                # request = ServerRequest(request_type='corrupted_record',
                # db_record=json.dumps(record))
                # self.signal_queue.put(request) ??????????????????????????????
                self.log.error('Error ocured: %s', error)
            else:
                self.log.info('Record saved')
            finally:
                await self.db_conn.commit()

        self.log.info('No more new records')
        await self.cur.close()
        await self.db_conn.close()


class CameraRecord(BaseRecordHandling):

    log = logging.getLogger('Camera Record')

    @classmethod
    async def save(self):
        self.log.info('Connection to DB')
        self.db_conn, self.cur = await connect_to_db(self.DEBUG)
        if not self.db_conn:
            self.log.error('Failed to connect to DB')
            return
        await self.set_all_cameras_to_inactive()
        while self.save_queue.qsize() > 0:
            record = await self.save_queue.get()
            self.log.info('Got new record %s', record)
            await self.process_record(record)
            self.save_queue.task_done()

        await self.cur.close()
        await self.db_conn.close()
        self.log.info('No more new records')

    @classmethod
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

    @classmethod
    async def process_record(self, record):
        try:
            await self.cur.execute("INSERT INTO \
                                   main_camera(camera_name, is_active) \
                                   VALUES (%s, True);",
                                   (record['camera_name'],))
            self.log.info('Camera %s added', record['camera_name'])
        except psycopg.Error as error:
            await self.db_conn.commit()
            self.log.error('Failed to create new record %s: %s',
                           record['camera_name'], error)
            try:
                await self.cur.execute("UPDATE main_camera \
                                       SET is_active=True \
                                       WHERE camera_name=%s;",
                                       (record['camera_name'],))
                self.log.info('Camera %s successfully activated',
                              record['camera_name'])
            except (Exception, psycopg.Error) as error:
                self.log.error('Corrupted camera record %s: %s',
                               record['camera_name'], error)
        except KeyError:
            self.log.error('Corrupted record')
            return
        await self.db_conn.commit()


class UserRecord(BaseRecordHandling):

    log = logging.getLogger('User Record')

    @classmethod
    async def save(self, request):
        self.db_conn, self.cur = await connect_to_db(self.DEBUG)
        if not self.db_conn:
            self.log.error('Failed to connect to DB')
            return

        if request.request_result == 'aproved':
            await self.cur.execute("UPDATE registration_customuser \
                              SET is_active=True, admin_checked=True \
                              WHERE username=(%s);", (request.username,))
            self.log.info('User %s successfully activated', request.username)
        else:
            await self.cur.execute("UPDATE registration_customuser \
                              SET admin_checked=True \
                              WHERE username=(%s);", (request.username,))
            self.log.info('User %s denied', request.username)

        await self.db_conn.commit()
        await self.cur.close()
        await self.db_conn.close()


class ActiveCameras(BaseRecordHandling):

    log = logging.getLogger('Get active cameras')

    @classmethod
    async def get_active_camera_list(self):
        self.log.debug('connecting to db')
        self.db_conn, self.cur = await connect_to_db(self.DEBUG)
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


async def connect_to_db(DEBUG):
    if DEBUG:
        dbname = 'test_dj_test'
    else:
        dbname = os.environ.get('POSTGRES_DB', 'dj_test')

    db_user = os.environ.get('POSTGRES_USER', 'test_dj')
    db_password = os.environ.get('POSTGRES_PASSWORD', '123')
    db_host = os.environ.get('POSTGRES_HOST', 'localhost')
    db_port = os.environ.get('POSTGRES_PORT', '5432')
    logging.debug('CONNECTION TO DB:%s', dbname)
    try:
        db_conn = await psycopg.AsyncConnection.connect(
                                            dbname=dbname,
                                            user=db_user,
                                            password=db_password,
                                            host=db_host,
                                            port=db_port)
    except Exception:
        return None, None
    else:
        cur = db_conn.cursor()
        return db_conn, cur
