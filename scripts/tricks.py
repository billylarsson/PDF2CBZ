from PyQt5.Qt               import QObject, QRunnable, QThreadPool
from PyQt5.QtCore           import pyqtSignal, pyqtSlot
from functools              import partial
from scripts.database_stuff import sqlite, DB
import hashlib
import os
import pathlib
import shutil
import sys
import tempfile
import time
import traceback
from PIL import Image

class ViktorinoxTechClass:
    def __init__(self):
        self.techdict = {}

    @staticmethod
    def save_image_as_blob(image_path, md5, width=None, height=None, quality=70, method=1):
        image = Image.open(image_path)

        if width:
            height = round(image.size[1] * (width / image.size[0]))
        elif height:
            width = round(image.size[0] * (height / image.size[1]))
        else:
            width = image.size[0]
            height = image.size[1]

        image_size = width, height
        image.thumbnail(image_size, Image.ANTIALIAS)

        tmp_file = tech.tmp_file(part1='webpcover_', part2='.webp', new=True)
        image.save(tmp_file, 'webp', method=method, quality=quality)

        with open(tmp_file, 'rb') as file:
            blob = file.read()
            query = 'update files set cover = (?) where md5 = (?)'
            sqlite.w(query, values=md5, blob=blob)

        os.remove(tmp_file)

    @staticmethod
    def md5_hash_string(string):
        hash_object = hashlib.md5(string.encode())
        rv = hash_object.hexdigest()
        return rv

    @staticmethod
    def md5_hash_file(local_path, partial_file=False):
        hash_md5 = hashlib.md5()
        with open(local_path, "rb") as f:
            for count, chunk in enumerate(iter(lambda: f.read(4096), b"")):
                hash_md5.update(chunk)
                if partial_file and count > partial_file:
                    break

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
            # makes sure the arguents are put into a tuple
            if type(worker_arguments) != tuple:
                worker_arguments = (worker_arguments,)
            thread = Worker(partial(worker_function, *worker_arguments))

        else:
            thread = Worker(partial(worker_function))

        if finished_function:

            if type(finished_function) != list:
                # makes finished function(s) into a list in case multiple launches are requested
                finished_function = [finished_function]

            for launcher in finished_function:

                if finished_arguments:
                    # makes sure the arguents are put into a tuple
                    if type(finished_arguments) != tuple:
                        finished_arguments = (finished_arguments,)
                    thread.signals.finished.connect(partial(launcher, *finished_arguments))

                else:
                    thread.signals.finished.connect(partial(launcher))

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
    def tmp_file(
            file_of_interest=None,
            hash=False,
            reuse=False,
            days=False,
            delete=False,
            new=False,
            part1=None, part2=None
        ):
        """
        :param file_of_interest: string can be anything fuck_a_duck.txt
        :param kwargs: reuse, doesnt delete file if its present, uses cache
        :param kwargs: days int, file is no more than x days to reuse
        :param kwargs: part1, part2 becomes part1_0004_part2.webp with new=True
        :param kwargs: new, keeps old file and puts a counter on/in new filename
        :return: full path (string)
        """
        tmp_folder = tech.tmp_folder(folder_of_interest='tmp_files', reuse=True)

        if part1 and part2:
            if file_of_interest:
                file_of_interest += part1 + part2
            else:
                file_of_interest = part1 + part2

        if not file_of_interest:
            md5 = tech.md5_hash_string(str(time.time()) + os.environ['PROGRAM_NAME'] + 'tmp_file')
            file_of_interest = md5.upper()

        if hash:
            file_of_interest = tech.md5_hash_string(file_of_interest)

        complete_path = tmp_folder + '/' + file_of_interest
        complete_path = os.path.abspath(os.path.expanduser(complete_path))

        def delete_file_checker(complete_path):
            if os.path.exists(complete_path):
                if days:
                    if os.path.getmtime(complete_path) < time.time() - (days * 86400):
                        os.remove(complete_path)
                        return

                if delete:
                    os.remove(complete_path)
                    return

        delete_file_checker(complete_path) # deletes first

        if reuse:
            return complete_path

        if os.path.exists(complete_path):
            if os.path.isfile(complete_path):
                try:
                    if not new:
                        os.remove(complete_path)
                except PermissionError:
                    pass
                except IsADirectoryError:
                    pass
                finally:

                    def zero_prefiller(value, lenght=4):
                        string = str(value)
                        string = ('0' * (lenght - len(string))) + string
                        return string

                    counter = 0
                    while os.path.exists(complete_path):
                        counter += 1
                        if part1 and part2:
                            _tmp_path = tmp_folder + '/' + part1 + zero_prefiller(counter) + part2
                            _tmp_path = os.path.abspath(os.path.expanduser(_tmp_path))
                        else:
                            _tmp_path = complete_path + '_' + zero_prefiller(counter)

                        if not os.path.exists(_tmp_path):
                            complete_path = _tmp_path

        return complete_path

    @staticmethod
    def tmp_folder(folder_of_interest=None, reuse=False, delete=False, hash=False, create_dir=True, return_base=False):
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
            md5 = tech.md5_hash_string(str(time.time()) + os.environ['PROGRAM_NAME'] + 'tmp_folder')
            folder_of_interest = md5.upper()

        elif folder_of_interest and hash:
            md5 = tech.md5_hash_string(folder_of_interest)
            folder_of_interest = md5.upper()

        if os.path.exists(os.environ['TMP_DIR']):
            base_dir = os.environ['TMP_DIR']
        else:
            base_dir = tempfile.gettempdir()

        complete_dir = base_dir + '/' + os.environ['PROGRAM_NAME'] + '/' + folder_of_interest
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

        if not os.path.exists(complete_dir) and create_dir:
            pathlib.Path(complete_dir).mkdir(parents=True)

        if return_base:
            return base_dir
        else:
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