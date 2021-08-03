from PyQt5.Qt       import QObject, QRunnable, QThreadPool
from PyQt5.QtCore   import pyqtSignal, pyqtSlot
from database_stuff import sqlite
from functools      import partial
import hashlib
import os
import pathlib
import shutil
import sys
import tempfile
import time
import traceback

PROGRAM_NAME = 'PDF2CBZ'

class ViktorinoxTechClass:
    def __init__(self):
        self.techdict = {}

    @staticmethod
    def md5_hash_string(string):
        hash_object = hashlib.md5(string.encode())
        rv = hash_object.hexdigest()
        return rv

    @staticmethod
    def md5_hash_file(local_path):
        hash_md5 = hashlib.md5()
        with open(local_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    @staticmethod
    def zero_prefiller(value, lenght=5):
        string = str(value)
        string = ('0' * (lenght - len(string))) + string
        return string

    def threadpool(self, threads=1, name='threadpool', timeout=30000):
        if 'threadpools' not in self.techdict:
            self.techdict['threadpools'] = {}

        if name not in self.techdict['threadpools']:
            threadpool = QThreadPool(maxThreadCount=threads, expiryTimeout=timeout)
            self.techdict['threadpools'][name] = threadpool

        return self.techdict['threadpools'][name]

    def start_thread(self,
                     worker_function,
                     worker_arguments=None,
                     finished_function=None,
                     finished_arguments=None,
                     threads=1,
                     name='threadpool'
                     ):

        if worker_arguments:
            thread = Worker(partial(worker_function, *worker_arguments))
        else:
            thread = Worker(partial(worker_function))

        if finished_function:
            if finished_arguments:
                thread.signals.finished.connect(partial(finished_function, *finished_arguments))
            else:
                thread.signals.finished.connect(partial(finished_function))

        threadpool = tech.threadpool(name=name, threads=threads)
        threadpool.start(thread)

    @staticmethod
    def retrieve_setting(index):
        """
        :param index: integer
        :return: column
        """
        data = sqlite.ro('select * from settings where id is 1')
        if data:
            return data[index]

    @staticmethod
    def tmp_folder(folder_of_interest=None, reuse=False, delete=False, hash=False):
        """
        generates a temporary folder for user
        i prefer to keep my trash inside /mnt/ramdisk
        if conflict, 0,1,2,3 + _ can be added to the END of the file
        :param folder_of_interest: string or none
        :param reuse: bool -> doesnt delete folder if its present, uses cache
        :param delete: bool -> will rmtree the folder before treating
        :param hash: bool -> md5 hashing folder_or_interest for clean dirs
        :return: full path (string)
        """
        if not folder_of_interest:
            md5 = tech.md5_hash_string(str(time.time()) + PROGRAM_NAME)
            folder_of_interest = md5.upper()

        elif folder_of_interest and hash:
            md5 = tech.md5_hash_string(folder_of_interest)
            folder_of_interest = md5.upper()

        if os.path.exists('/mnt/ramdisk'):
            base_dir = '/mnt/ramdisk'
        else:
            base_dir = tempfile.gettempdir()

        complete_dir = base_dir + '/' + PROGRAM_NAME + '/' + folder_of_interest
        complete_dir = os.path.abspath(os.path.expanduser(complete_dir))

        if os.path.exists(complete_dir) and not reuse:
            try:
                if delete:
                    shutil.rmtree(complete_dir)
            except PermissionError:
                pass
            except NotADirectoryError:
                pass
            finally:
                counter = 0
                while os.path.exists(complete_dir):
                    counter += 1
                    tmp = complete_dir + '_' + str(counter)
                    if not os.path.exists(tmp):
                        complete_dir = tmp

        if not os.path.exists(complete_dir):
            pathlib.Path(complete_dir).mkdir(parents=True)

        return complete_dir

tech = ViktorinoxTechClass()

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