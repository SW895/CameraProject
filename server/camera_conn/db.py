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


class BaseRecordHandling:

    save_queue = asyncio.Queue()
    cur = None
    db_conn = None

    def __init__(self, request):
        self.request = request

    async def save(self):
        raise NotImplementedError

    async def send_response(self, status):
        await self.db_conn.commit()
        builder = RequestBuilder().with_args(status=status)
        response = builder.build()
        self.request.writer.write(response.serialize().encode())
        await self.request.writer.drain()
        self.request.writer.close()
        await self.request.writer.wait_closed()
        await self.cur.close()
        await self.db_conn.close()


class NewVideoRecord(BaseRecordHandling):

    log = logging.getLogger('Video Record')

    async def save(self):
        self.log.info('Connection to DB')
        self.db_conn, self.cur = await connect_to_db()
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
                self.log.error('Error ocured: %s', error)
                await self.send_response('failed')
                return
            else:
                self.log.info('Record saved')

        await self.send_response('success')
        self.log.info('No more new records')


class CameraRecord(BaseRecordHandling):

    log = logging.getLogger('Camera Record')

    async def save(self):
        self.log.info('Connection to DB')
        self.db_conn, self.cur = await connect_to_db()
        if not self.db_conn:
            self.log.error('Failed to connect to DB')
            return
        await self.set_all_cameras_to_inactive()
        while self.save_queue.qsize() > 0:
            record = await self.save_queue.get()
            self.log.info('Got new record %s', record)
            try:
                await self.cur.execute("INSERT INTO \
                                        main_camera (camera_name, is_active) \
                                        VALUES (%s, True) \
                                        ON CONFLICT (camera_name) \
                                        DO UPDATE \
                                        SET is_active=True;",
                                       (record['camera_name'],))
                self.log.info('Camera %s activated', record['camera_name'])
            except (Exception, psycopg.Error):
                await self.send_response('failed')
                return
            self.save_queue.task_done()

        await self.send_response('success')
        self.log.info('No more new records')

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


class UserRecord(BaseRecordHandling):

    log = logging.getLogger('User Record')

    async def save(self):
        self.db_conn, self.cur = await connect_to_db()
        if not self.db_conn:
            self.log.error('Failed to connect to DB')
            return

        while self.save_queue.qsize() > 0:
            record = await self.save_queue.get()
            self.log.info('Got new record %s', record)
            if self.request.request_result == 'aproved':
                try:
                    await self.cur.execute(
                            "UPDATE registration_customuser \
                             SET is_active=True, admin_checked=True \
                             WHERE username=(%s);",
                            (self.request.username,))
                    self.log.info('User %s successfully activated',
                                  self.request.username)
                except psycopg.Error:
                    self.log.debug('Failed to aprove user:%s',
                                   self.request.username)
                    await self.send_response('failed')
                    return
            else:
                try:
                    await self.cur.execute(
                            "UPDATE registration_customuser \
                             SET admin_checked=True \
                             WHERE username=(%s);",
                            (self.request.username,))
                    self.log.info('User %s denied', self.request.username)
                except psycopg.Error:
                    self.log.debug('Failed to deny user:%s',
                                   self.request.username)
                    await self.send_response('failed')
                    return
        await self.send_response('success')


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
    except Exception:
        return None, None
    else:
        cur = db_conn.cursor()
        return db_conn, cur
