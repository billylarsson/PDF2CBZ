from PyQt5.Qt     import QObject, QRunnable, QThreadPool
from PyQt5.QtCore import pyqtSignal, pyqtSlot
from functools    import partial
from sqlite3      import Error
import os
import pathlib
import platform
import sqlite3
import sys
import time
import traceback

class SQLite:
    def __init__(self, INI_FILE_NAME, INI_FILE_DIR, DATABASE_FILENAME, DATABASE_FOLDER, DATABASE_SUBFOLDER):
        """
        this is trying to get all sqlite reads and writes into a single
        class with a single thread, columns are stored in self.techdict
        :param INI_FILE_NAME: filename only (not full path)
        :param INI_FILE_DIR: direct string or __file__ from folder where ini will be
                        loaded/created (__file__ is user friendly, therefore used)
        :param DATABASE_FOLDER: ie /home/user/Documents (ignored if not exists)
        :param DATABASE_SUBFOLDER: ie COOLPROGRAM (ignored if not PARENT_DIRECTORY not exists)
        :param DATABASE_FILENAME: my_program.sqlite
        """
        # ------------------------------------ #
        self.INI_FILE          = INI_FILE_NAME
        self.INI_DIR           = INI_FILE_DIR
        self.NEW_APP_DIR       = DATABASE_SUBFOLDER
        self.PARENT_DIRECTORY  = DATABASE_FOLDER
        self.DATABASE_FILENAME = DATABASE_FILENAME
        self.INI_FULL_PATH     = os.path.abspath(os.path.expanduser(self.INI_DIR + self.INI_FILE))
        # ------------------------------------ #
        self.techdict = {}
        self.sqliteconnection = None
        self.sqlitecursor = None
        self.release_grip = False
        self.threadpool = QThreadPool(maxThreadCount=1, expiryTimeout=-1)
        thread = self.Worker(partial(self.init_connection_and_cursor))
        self.threadpool.start(thread)
        while not self.release_grip:
            time.sleep(0.01)

    def init_connection_and_cursor(self):
        """
        changes the directory to the same as the file is run and looks for settings.ini
        such will be created if non exists and a row will be created with the path to the sqlite file
        a settings table will be created i use row 1 for that, so only one should ever be created
        if something isnt working, hard exit will be make sys.exit()
        """
        def get_db_folder_and_filename(local_path):
            """
            :param local_path must be full path including filename
            :return: object.string: full_path, db_folder, file_name
            """
            class LOCATIONS:
                full_path = local_path
                if platform.system() != "Windows":
                    tmp_full_path = local_path.split('/')
                    file_name = tmp_full_path[-1]
                    tmp_full_path.pop(-1)
                    db_folder = '/'.join(tmp_full_path)
                else:
                    tmp_full_path = local_path.split('\\')
                    file_name = tmp_full_path[-1]
                    tmp_full_path.pop(-1)
                    db_folder = '\\'.join(tmp_full_path)

            return LOCATIONS

        def make_nessesary_folders(local_path):
            """
            makes proper subfolders
            :param local_path must be full path including filename
            """
            if not os.path.exists(local_path):
                loc = get_db_folder_and_filename(local_path)
                if loc.db_folder and not os.path.exists(loc.db_folder):
                    pathlib.Path(loc.db_folder).mkdir(parents=True)

        def ini_file_creation(self, force=False):
            """
            :param force: bool, if True INI_FILE will be overwritten
            """
            if not os.path.exists(self.INI_FULL_PATH) or force:
                with open(self.INI_FULL_PATH, 'w') as f:
                    db_file = self.DATABASE_FILENAME

                    if os.path.exists(self.PARENT_DIRECTORY):
                        if self.NEW_APP_DIR:
                            full_db_path = f'{self.PARENT_DIRECTORY}/{self.NEW_APP_DIR}/{db_file}'
                        else:
                            full_db_path = f'{self.PARENT_DIRECTORY}/{db_file}'
                    else:
                        full_db_path = db_file

                    full_db_path = os.path.abspath(os.path.expanduser(full_db_path))
                    f.write(f'local_database = "{full_db_path}"\n')
                    make_nessesary_folders(full_db_path)

                    f.close()

        def load_database(self):
            """
            iter each row from INI_FILE until it find both: 'local_database'
            AND 'sqlite' then loads the database and checks if table settings
            is preset or creates an empty settings-table
            :return: bool
            """
            with open(self.INI_FULL_PATH, 'r') as f:
                database_location = list(f)

                for row in database_location:
                    for database, dbdict in databases.items():

                        if len(row) < len(database):
                            continue

                        if database != 'local_database' or row[0:len(database)] != database:
                            continue

                        path_split = row.split('"')
                        local_path = [x for x in path_split if x.find('sqlite') > -1]

                        if not local_path:
                            return False

                        loc = get_db_folder_and_filename(local_path[0])

                        if not os.path.exists(loc.db_folder):
                            return False

                        if not os.path.exists(loc.full_path):
                            try:
                                pathlib.Path(loc.full_path).touch()
                                if os.path.exists(loc.full_path):
                                    try:
                                        os.remove(loc.full_path)
                                    except:
                                        print('Failed to modify:', loc.full_path)
                                        sys.exit()
                            except:
                                print('Failed to write:', loc.full_path)
                                sys.exit()

                        if platform.system() == 'Windows':
                            self.sqliteconnection = sqlite3.connect(loc.full_path, timeout=30, check_same_thread=False)
                        else:
                            self.sqliteconnection = sqlite3.connect(loc.full_path)

                        self.sqlitecursor = self.sqliteconnection.cursor()

                        try:
                            self.sqlitecursor.execute('select * from settings where id is 1')

                        except Error:
                            query_one = 'create table settings (id INTEGER PRIMARY KEY AUTOINCREMENT)'
                            query_two = 'insert into settings values(?)'

                            try:
                                self.sqlitecursor.execute(query_one)
                                self.sqlitecursor.execute(query_two, (None,))
                                self.sqliteconnection.commit()
                            except Error:
                                print('SQLite table creation error!')
                                sys.exit()
                        finally:
                            return True

        databases = dict(
            local_database=dict(
                connection=self.sqliteconnection, cursor=self.sqlitecursor),
        )

        ini_file_creation(self)
        if not load_database(self):
            ini_file_creation(self, force=True)
            if not load_database(self):
                print('HARD QUIT!')
                sys.exit()

        self.release_grip = True

    def sqlite_superfunction(self, connection, table, column, type):
        """
        if table isnt found one will be created for you, same is true for columns
        :param connection: sqlite3 connection (can be a string, this is for techdict key)
        :param table: string
        :param column: string
        :param type: string, integer, float
        :return: integer
        """
        if connection not in self.techdict:
            self.techdict.update({connection: { }})
        if table not in self.techdict[connection]:
            self.techdict[connection].update({table : { }})

        query_one = 'select * from ' + table
        if not self.ro(query_one, fetch='pointer'):
            query_two = 'create table ' + table + ' (id INTEGER PRIMARY KEY AUTOINCREMENT)'
            self.w(query_two)
            self.ro(query_one)

        col_names = self.get_description()

        for count, row in enumerate(col_names):
            if row[0] not in self.techdict[connection][table]:
                self.techdict[connection][table].update({row[0] : count})

        if column in self.techdict[connection][table]:
            return self.techdict[connection][table][column]
        else:
            query = 'alter table ' + table + ' add column ' + column + ' ' + type.upper()
            self.w(query)
            return len(col_names)

    def db_sqlite(self, table, column, type='text'):
        """
        close to unnessesary, but when you have a ton of DB.things it actually helps
        """
        return self.sqlite_superfunction(self.sqliteconnection, table, column, type)

    def empty_insert_query(self, table):
        rv = self.road(empty_query_table=table)
        return rv['query'], rv['values']

    def get_description(self):
        rv = self.road(description=True)
        return rv

    def ra(self, query=None, values=None, fetch='all'):
        rv = self.road(query, values, fetch)
        return rv

    def read_master(self, return_dict, query=None, values=None, fetch="one, all or pointer"):
        """
        this reads from the database in many ways or just points the correct entry
        :param return_dict: dictionary, program is frozen untill RV or False takes its place
        :param query: string
        :param values: string or tuple (or none)
        :param fetch: string
        :return: data or bool
        """
        if query and values:

            if type(values) == tuple:
                self.sqlitecursor.execute(query, values)
            elif type(values) == str:
                self.sqlitecursor.execute(query, (values,))

        elif query:
            try:
                self.sqlitecursor.execute(query)
            except Error:
                return_dict['return_value'] = [False]
                return False

        if fetch == 'one':
            data = self.sqlitecursor.fetchone()
            return_dict['return_value'] = [data]

        elif fetch == 'all':
            data = self.sqlitecursor.fetchall()
            return_dict['return_value'] = [data]

        elif fetch == 'pointer':
            return_dict['return_value'] = [True]

    def ro(self, query=None, values=None, fetch='one'):
        rv = self.road(query, values, fetch)
        return rv

    def road(self, query=None, values=None, fetch=None, description=False, empty_query_table=False):
        """
        all reads uses the same function, this is just an optimization
        :param query: string
        :param values: string, tuple or none
        :param fetch: string
        :param description: bool
        :return: data or bool
        """
        rd = dict(return_value=[])

        if description:
            def thread_description(self, rd):
                rd['return_value'] = [self.sqlitecursor.description]

            thread = self.Worker(partial(thread_description, self, rd))

        elif empty_query_table:
            def empty_insert_query(self, rd, empty_query_table):
                self.sqlitecursor.execute('PRAGMA table_info("{}")'.format(empty_query_table, ))
                tables = self.sqlitecursor.fetchall()
                query_part1 = "insert into " + empty_query_table + " values"
                query_part2 = "(" + ','.join(['?'] * len(tables)) + ")"
                values = [None] * len(tables)
                rd['return_value'] = [dict(query=query_part1 + query_part2, values=values)]

            thread = self.Worker(partial(empty_insert_query, self, rd, empty_query_table))

        else:
            thread = self.Worker(partial(self.read_master, rd, query, values, fetch))

        self.threadpool.start(thread)

        counter = -1
        while rd['return_value'] == []:
            if counter < 1:
                time.sleep(0.01)
            elif counter < 2:
                time.sleep(0.05)
            elif counter < 5:
                time.sleep(0.10)
            else:
                time.sleep(0.20)

        return rd['return_value'][0]

    def w(self, query, values=None, blob=None):
        """
        decides if write is executemany or just execute
        :param query: string
        :param values: list, tuple, string or none
        """
        if blob:
            self.write_one_master(query, values, blob)
        elif type(values) == list and type(values[0]) != tuple:
            self.write_one_master(query, values)
        elif type(values) == list:
            self.write_many_master(query, values)
        else:
            self.write_one_master(query, values)

    def commit_and_regenerate(self):
        try:
            self.sqliteconnection.commit()

        except sqlite3.OperationalError:
            self.sqlitecursor.close()
            self.sqliteconnection.close()
            self.init_connection_and_cursor()
            self.sqliteconnection.commit()

        time.sleep(0.05)

    def write_many_master(self, query, values):
        """
        Write Many (executemany instead of execute)
        :param query: string
        :param values: list
        """
        def write_to_database(self, query, values):
            self.sqlitecursor.executemany(query, values)
            self.commit_and_regenerate()

        if query and values:
            thread = self.Worker(partial(write_to_database, self, query, values))
            self.threadpool.start(thread)

    def write_one_master(self, query=None, values=None, blob=None):
        """
        Write One (execute instead of execute many)
        :param query: string
        :param values: string or tuple (or even none)
        """
        def write_to_database(self, query, values, blob):
            if blob:
                if values:
                    self.sqlitecursor.execute(query, (sqlite3.Binary(blob), values,))
                else:
                    self.sqlitecursor.execute(query, [sqlite3.Binary(blob)])

            elif values == None:
                self.sqlitecursor.execute(query)

            elif type(values) == list:
                self.sqlitecursor.execute(query, tuple(values))

            elif type(values) == tuple:
                self.sqlitecursor.execute(query, values)

            else:
                self.sqlitecursor.execute(query, (values,))

            self.commit_and_regenerate()

        if query:
            thread = self.Worker(partial(write_to_database, self, query, values, blob))
            self.threadpool.start(thread)

    class Worker(QRunnable):
        def __init__(self, function):
            super().__init__()
            self.fn = function
            self.signals = self.WorkerSignals()

        class WorkerSignals(QObject):
            finished = pyqtSignal()
            error = pyqtSignal(tuple)
            result = pyqtSignal(object)
            progress = pyqtSignal(int)

        @pyqtSlot()
        def run(self):
            try:
                result = self.fn()
            except:
                traceback.print_exc()
                exctype, value = sys.exc_info()[:2]
                self.signals.error.emit((exctype, value, traceback.format_exc()))
            else:
                self.signals.result.emit(result)  # Return the result of the processing
            finally:
                self.signals.finished.emit()  # Done