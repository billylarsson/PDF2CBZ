from PyQt5.Qt     import QObject, QRunnable, QThreadPool
from PyQt5.QtCore import pyqtSignal, pyqtSlot
from functools    import partial
from sqlite3      import Error
import os
import pathlib
import platform
import sqlite3
import sys
import traceback

NEW_APP_DIR = 'PDF2CBZ'
INI_FILE = 'settings.ini'

class WorkerSignals(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(object)
    progress = pyqtSignal(int)

class Worker(QRunnable):
    def __init__(self, function):
        super(Worker, self).__init__()
        self.fn = function
        self.signals = WorkerSignals()

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

class SQLite:
    def __init__(self):
        """
        this is trying to get all sqlite reads and writes into a single
        class with a single thread, columns are stored in self.techdict
        """
        self.techdict = {}
        self.sqliteconnection = None
        self.sqlitecursor = None
        self.release_grip = False
        self.threadpool = QThreadPool(maxThreadCount=1, expiryTimeout=-1)
        thread = Worker(partial(self.init_connection_and_cursor))
        self.threadpool.start(thread)
        while not self.release_grip:
            continue

    def init_connection_and_cursor(self):
        """
        changes the directory to the same as the file is run and looks for settings.ini
        such will be created if non exists and a row will be created with the path to the sqlite file
        a settings table will be created i use row 1 for that, so only one should ever be created
        if something isnt working, hard exit will be make sys.exit()
        """
        def make_nessesary_folders(local_path):
            if not os.path.exists(local_path):
                part = local_path.split('/')
                part.pop(-1)
                if part:
                    path = '/'.join(part)
                    if not os.path.exists(path):
                        pathlib.Path(path).mkdir(parents=True)

        if platform.system() == "Windows":
            os.chdir(os.path.realpath(__file__)[0:os.path.realpath(__file__).rfind('\\')])
        else:
            os.chdir(os.path.realpath(__file__)[0:os.path.realpath(__file__).rfind('/')])

        databases = dict(
            local_database=dict(
                connection=self.sqliteconnection, cursor=self.sqlitecursor),
        )

        if not os.path.exists(INI_FILE):
            with open(INI_FILE, 'w') as f:
                devpath = '/home/plutonergy/Documents/'
                if os.path.exists(devpath):
                    devpath = f'{devpath}{NEW_APP_DIR}/'
                else:
                    devpath = ""

                sqlite_file = f'{devpath}/{NEW_APP_DIR.lower()}_database.sqlite'
                sqlite_file = os.path.abspath(os.path.expanduser(sqlite_file))

                f.write(f'local_database = "{sqlite_file}"\n')
                f.close()

        with open(INI_FILE, 'r') as f:
            database_location = list(f)

            for row in database_location:
                for database, dbdict in databases.items():
                    if len(row) > len(database):
                        if row[0:len(database)] == database:
                            local_path = row[row.find('"') + 1:row.rfind('"')]

                            if database == 'local_database':
                                make_nessesary_folders(local_path)
                                self.sqliteconnection = sqlite3.connect(local_path)
                                self.sqlitecursor = self.sqliteconnection.cursor()
                                dbdict['cursor'] = True

                                try:
                                    self.sqlitecursor.execute('select * from settings where id is 1')

                                except Error:
                                    query_one = 'create table settings (id INTEGER PRIMARY KEY AUTOINCREMENT)'
                                    query_two = 'insert into settings values(?)'

                                    with self.sqliteconnection:
                                        self.sqlitecursor.execute(query_one)
                                        self.sqlitecursor.execute(query_two, (None,))

            for database, dbdict in databases.items():
                if dbdict['cursor'] == None:
                    print("SQLiteconnection failed: hard quit!")
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

    def write_one_master(self, query=None, values=None):
        """
        Write One (execute instead of execute many)
        :param query: string
        :param values: string or tuple (or even none)
        """
        def write_to_database(self, query, values):
            with self.sqliteconnection:
                if values == None:
                    self.sqlitecursor.execute(query)
                elif type(values) == list:
                    self.sqlitecursor.execute(query, tuple(values))
                elif type(values) == tuple:
                    self.sqlitecursor.execute(query, values)
                else:
                    self.sqlitecursor.execute(query, (values,))

        if query:
            thread = Worker(partial(write_to_database, self, query, values))
            self.threadpool.start(thread)

    def write_many_master(self, query, values):
        """
        Write Many (executemany instead of execute)
        :param query: string
        :param values: list
        """
        def write_to_database(self, query, values):
            with self.sqliteconnection:
                self.sqlitecursor.executemany(query, values)

        if query and values:
            thread = Worker(partial(write_to_database, self, query, values))
            self.threadpool.start(thread)

    def w(self, query, values=None):
        """
        decides if write is executemany or just execute
        :param query: string
        :param values: list, tuple, string or none
        """
        if type(values) == list and type(values[0]) != tuple:
            self.write_one_master(query, values)
        elif type(values) == list:
            self.write_many_master(query, values)
        else:
            self.write_one_master(query, values)

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
            try: self.sqlitecursor.execute(query)
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

            thread = Worker(partial(thread_description, self, rd))

        elif empty_query_table:
            def empty_insert_query(self, rd, empty_query_table):
                self.sqlitecursor.execute('PRAGMA table_info("{}")'.format(empty_query_table, ))
                tables = self.sqlitecursor.fetchall()
                query_part1 = "insert into " + empty_query_table + " values"
                query_part2 = "(" + ','.join(['?'] * len(tables)) + ")"
                values = [None] * len(tables)
                rd['return_value'] = [dict(query=query_part1 + query_part2, values=values)]

            thread = Worker(partial(empty_insert_query, self, rd, empty_query_table))

        else:
            thread = Worker(partial(self.read_master, rd, query, values, fetch))

        self.threadpool.start(thread)

        while rd['return_value'] == []:
            continue

        return rd['return_value'][0]


    def ra(self, query=None, values=None, fetch='all'):
        rv = self.road(query, values, fetch)
        return rv

    def ro(self, query=None, values=None, fetch='one'):
        rv = self.road(query, values, fetch)
        return rv

    def get_description(self):
        rv = self.road(description=True)
        return rv

    def empty_insert_query(self, table):
        rv = self.road(empty_query_table=table)
        return rv['query'], rv['values']

sqlite = SQLite()

class DB:
    class settings:
        theme = sqlite.db_sqlite('settings', 'theme')
        geometry = sqlite.db_sqlite('settings', 'geometry')
        source_path = sqlite.db_sqlite('settings', 'source_path')
        destination_path = sqlite.db_sqlite('settings', 'destination_path')
        webp_slider = sqlite.db_sqlite('settings', 'webp_slider', 'integer')
        del_source = sqlite.db_sqlite('settings', 'del_source', 'integer')
        continous = sqlite.db_sqlite('settings', 'continous', 'integer')
        poppler_path = sqlite.db_sqlite('settings', 'poppler_path')

    class files:
        local_path = sqlite.db_sqlite('files', 'local_path')
        md5 = sqlite.db_sqlite('files', 'md5')
