import asyncio
import psycopg
import logging
import json
import os
from psycopg import sql
from camera_utils import ServerRequest


class BaseRecordHandling:

    DEBUG = False
    save_queue = asyncio.Queue()

    async def save(self):
        raise NotImplementedError


class NewVideoRecord(BaseRecordHandling):

    log = logging.getLogger('Save records to DB')

    @classmethod
    async def save(self):

        self.log.info('Connection to DB')
        db_conn, cur = connect_to_db(self.DEBUG)

        if db_conn:
            self.log.info('Successfully connected to db')
            while self.save_db_records_queue.qsize() > 0:
                record = self.save_db_records_queue.get()
                self.log.info('Got new record')
                columns = record.keys()
                values = [record[column] for column in columns]
                ret = sql.SQL('INSERT INTO main_archivevideo({fields}) VALUES ({values});').format(
                fields=sql.SQL(',').join([sql.Identifier(column) for column in columns]),
                values=sql.SQL(',').join(values),)
                try:
                    cur.execute(ret)
                except psycopg.Error as error:
                    self.signal_queue.put(ServerRequest(request_type='corrupted_record',
                                                        db_record=json.dumps(record)))
                    self.log.error('Error ocured: %s', error)
                else:
                    self.log.info('Record saved')
                finally:
                    db_conn.commit()

            self.log.info('No more new records')
            if self.DEBUG:
                return
            cur.close()
            db_conn.close()


class CameraRecord(BaseRecordHandling):

    log = logging.getLogger('Save camera to DB')

    @classmethod
    async def save(self):

        self.log.info('Connection to DB')
        db_conn, cur = connect_to_db(self.DEBUG)
        if db_conn:

            if self.DEBUG:
                cur.execute('DELETE FROM main_camera')
                db_conn.commit()

            try:
                cur.execute("UPDATE main_camera SET is_active=False WHERE is_active=True;")
            except (Exception, psycopg.Error):
                self.log.error('No records')
            else:
                self.log.debug('All cameras set to is_active=False')
            finally:
                db_conn.commit()

            while self.save_queue.qsize() > 0:
                record = await self.save_queue.get()
                self.log.info('Got new record %s', record)
                try:
                    cur.execute("INSERT INTO main_camera(camera_name, is_active) VALUES (%s, True);", (record['camera_name'],))
                    self.log.info('Camera %s added', record['camera_name'])
                except (Exception, psycopg.Error) as error:
                    db_conn.commit()
                    self.log.error('Failed to create new record %s: %s', record['camera_name'], error)
                    try:
                        cur.execute("UPDATE main_camera SET is_active=True WHERE camera_name=%s;", (record['camera_name'],))
                        self.log.info('Camera %s successfully activated', record['camera_name'])
                    except (Exception, psycopg.Error) as error:
                        self.log.error('Corrupted camera record %s: %s', record['camera_name'], error)
                db_conn.commit()
                self.save_queue.task_done()

            cur.close()
            db_conn.close()
            self.log.info('No more new records')


class UserRecord(BaseRecordHandling):

    log = logging.getLogger('User aprove')

    def save(self, request):
        request.connection.close()
        db_conn, cur = connect_to_db(self.DEBUG)

        if db_conn:
            if request.request_result == 'aproved':
                cur.execute("UPDATE registration_customuser SET is_active=True, admin_checked=True WHERE username=(%s);", (request.username,))
                self.log.info('User %s successfully activated', request.username)
            else:
                cur.execute("UPDATE registration_customuser SET admin_checked=True WHERE username=(%s);", (request.username,))
                self.log.info('User %s denied', request.username)

            db_conn.commit()
            cur.close()
            db_conn.close()
        else:
            self.log.error('Failed to connect to DB')


class ActiveCameras():

    log = logging.getLogger('Get active cameras')

    @classmethod
    async def get_active_camera_list(self):
        self.log.debug('connecting to db')
        db_conn, cur = connect_to_db(False)  #make async
        if db_conn:
            self.log.info('Successfully connected to db')
            cur.execute("SELECT camera_name FROM main_camera WHERE is_active=True")
            active_cameras = cur.fetchall()
        cur.close()
        db_conn.close()
        return active_cameras


def connect_to_db(DEBUG):
    if DEBUG:
        dbname = 'test_dj_test'
    else:
        dbname = os.environ.get('POSTGRES_DB', 'dj_test')

    db_user = os.environ.get('POSTGRES_USER', 'test_dj')
    db_password = os.environ.get('POSTGRES_PASSWORD', '123')
    db_host = os.environ.get('POSTGRES_HOST', 'localhost')
    db_port = os.environ.get('POSTGRES_PORT', '5432')

    try:
        db_conn = psycopg.connect(dbname=dbname,
                                  user=db_user,
                                  password=db_password,
                                  host=db_host,
                                  port=db_port)
    except Exception:
        return None, None
    else:
        cur = db_conn.cursor()
        return db_conn, cur
    

