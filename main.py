#!/usr/bin/env python3

from PIL            import Image
from PyPDF2         import PdfFileReader
from PyQt5          import QtWidgets
from database_stuff import DB, sqlite
from pdf2image      import convert_from_path
from tricks         import tech as t
from widgets        import PDFWidget
from zipfile        import BadZipFile, ZipFile
import PyPDF2
import concurrent.futures
import math
import os
import psutil
import shutil
import string
import sys
import time

FIGURE_HEIGHT = 300


def pdf_to_jpeg(job):
    """
    thread job that requires a starting and ending index
    :param job: tuple
    :return: list with paths as strings
    """
    image_list = convert_from_path(
        job[0], output_folder=job[1], first_page=job[2], last_page=job[3], output_file=job[4],
        jpegopt=dict(quality=100), fmt='jpeg', paths_only=True,
    )
    return image_list
def convert_files_to_jpeg(joblist, inputpath, tmp_jpeg_folder):
    """
    :param joblist: dictionary with letters as keys containing list indexes (int)
    :param inputpath: string to pdf file-path
    :param tmp_jpeg_folder: string
    :return: list with image paths
    """
    image_list = []
    threadlist = []
    for letter in joblist:
        threadlist.append((inputpath, tmp_jpeg_folder, joblist[letter][0], joblist[letter][-1], letter,))

    with concurrent.futures.ProcessPoolExecutor() as executor:
        for _, rv in zip(joblist, executor.map(pdf_to_jpeg, threadlist)):
            for path in rv:
                image_list.append(path)

    image_list.sort()
    return image_list

def jpeg_to_webp(job):
    """
    jpeg to webp
    :param job: tuple -> 0:jpeg_file_path, 1:save_webp_file_path
    :return: string -> webp_file_location
    """
    image = Image.open(job[0])
    image.save(job[1], 'webp', method=6, quality=70)
    return job[1]
def convert_files_to_webp(joblist):
    """
    :param joblist: list with jpeg_files
    :return:
    """
    with concurrent.futures.ProcessPoolExecutor() as executor:
        for _, rv in zip(joblist, executor.map(jpeg_to_webp, joblist)):
            pass

def recompress_fucntion(destination_file, tmp_folder):
    """
    compresses the files from tmp_folder into file.cbz
    :param destination_file: string new file.zip
    :param tmp_folder: string
    :return: bool
    """
    def confirm_new_files(ziplocation):
        """
        test if the file.zip/cbz has the same
        amount of files as tmp_folder
        :param ziplocation: string
        :return: bool
        """
        try:
            zf = ZipFile(ziplocation)
            filecontents = list(zf.namelist())
        except BadZipFile:
            os.remove(ziplocation)
            print('OUTPUT FILE BROKEN')
            return False

        for walk in os.walk(tmp_folder):
            files = [walk[0] + '/' + x for x in walk[2]]
            if len(filecontents) < len(files):
                os.remove(ziplocation)
                shutil.rmtree(tmp_folder)
                print('FILES MISSING')
                return False
            break

        return True

    zipfile = destination_file[0:-(len('.cbz'))]

    os.sync()
    shutil.make_archive(zipfile, 'zip', tmp_folder)
    zipfile += '.zip'
    os.sync()

    if not confirm_new_files(zipfile):
        return False

    if not os.path.exists(zipfile) or os.path.getsize(zipfile) == 0:
        print('WRITE OUTPUT ERROR')
        if os.path.exists(zipfile):
            os.remove(zipfile)

        return False

    shutil.move(zipfile, destination_file)

    return True

class main(QtWidgets.QMainWindow):
    def __init__(self):
        super(main, self).__init__()
        self.setWindowTitle('STRANGLE THE FUCKING DUCK v0.1 build:666')
        self.setStyleSheet('background-color: rgb(20,20,20) ; color: rgb(255,255,255)')
        self.setFixedSize(1920, 1080)
        self.widgets = dict(main=[], pdf=[], cbz=[])

        self.wt = 5
        self.ht = 5

        self.reset_ht_wt()

        self.from_dir = QtWidgets.QPlainTextEdit(self, toolTip='SOURCE FOLDER')
        self.from_dir.setStyleSheet('background-color: rgb(30,30,30) ; color: rgb(235,235,235)')
        self.from_dir.setGeometry(self.wt, self.ht, int(self.width() * 0.5), 30)
        self.from_dir.show()
        self.ht += self.from_dir.height() + 3
        self.from_dir.textChanged.connect(self.from_dir_changed)

        self.to_dir = QtWidgets.QPlainTextEdit(self, toolTip='DESTINATION FOLDER')
        self.to_dir.setStyleSheet('background-color: rgb(30,30,30) ; color: rgb(235,235,235)')
        self.to_dir.setGeometry(self.wt, self.ht, int(self.width() * 0.5), 30)
        self.to_dir.show()
        self.ht += self.to_dir.height() + 3
        self.to_dir.textChanged.connect(self.to_dir_changed)

        self.canvas = QtWidgets.QFrame(self)
        self.canvas.setStyleSheet('background-color: rgb(25,25,25)')
        self.canvas.setGeometry(self.wt, self.ht, self.width() - self.wt * 2, self.height() - self.ht - 5)
        self.canvas.show()
        self.ht += self.canvas.height() + 3

        self.btn_more = QtWidgets.QPushButton(self, text='MORE')
        self.btn_more.move(self.from_dir.geometry().right() + 5, 5)
        self.btn_more.clicked.connect(self.draw_more_pdf_files)

        self.continous_convertion = QtWidgets.QCheckBox(self, text='CONTINOUS')
        self.continous_convertion.setToolTip('Continous conversions, start another once current is completed!')
        self.continous_convertion.move(self.from_dir.geometry().right() + 5, self.btn_more.geometry().bottom() + 5)

        self.deside_figure_size()

        self.show()

        setting_plaintext_label = {
            DB.settings.source_path: self.from_dir,
            DB.settings.destination_path: self.to_dir,
         }

        for key, label in setting_plaintext_label.items():
            rv = t.retrieve_setting(key)
            if rv:
                label.setPlainText(rv)


    def deside_figure_size(self):
        """
        calculates how large widgets should be to fill the self.canvas (frame)
        """
        # HEIGHT >
        self.figure_height = FIGURE_HEIGHT

        av = self.canvas.height() / FIGURE_HEIGHT
        left_over = self.canvas.height() - (FIGURE_HEIGHT * math.floor(av))

        if left_over > av:
            self.figure_height += math.floor(left_over / math.floor(av))
            self.figure_height = int(self.figure_height)

        self.figure_height -= 3 # gives geometry.height() breathing room

        # WIDTH >
        self.figure_width = self.figure_height * 0.6
        av = math.floor(self.canvas.width() / self.figure_width)
        left_over = self.canvas.width() - (self.figure_width * math.floor(av))
        if left_over > av:
            self.figure_width += math.floor(left_over / math.floor(av))
            self.figure_width = int(self.figure_width)

        self.figure_width -= 3 # gives geometry.width() breathing room


    def reset_widgets(self, widgets=None, all=False):
        def close_and_pop(self, key):
            for count in range(len(self.widgets[key]) - 1, -1, -1):
                self.widgets[key][count].close()
                self.widgets[key].pop(count)
        if all:
            for key in self.widgets:
                close_and_pop(self, key)

        if widgets and widgets in self.widgets:
            close_and_pop(self, widgets)

        self.reset_ht_wt()

    def reset_ht_wt(self):
        self.pdf_wt = 3
        self.pdf_ht = 3

        self.cbz_wt = 3
        self.cbz_ht = 3

    def get_all_files_from_path(self, path, extension=None):
        """
        :param path: string
        :param extension: string -> pdf
        :return: list
        """
        all_files = []

        if not os.path.exists(path):
            return all_files

        for this in os.walk(path):
            for f in this[2]:
                path = this[0] + '/' + f
                if extension and type(extension) == str:

                    ext = path.split('.')
                    if len(ext) == 1:
                        continue

                    if ext[-1].lower() != extension.lower():
                        continue

                if path not in all_files:
                    all_files.append(path)

        return all_files

    def make_all_files_dictionary(self, all_files, append_to_this=False):
        """
        makes a working dictionary
        :param all_files: list with file paths
        :param append_to_this: (not used)
        :return: dictionary
        """
        if append_to_this:
            rdict = append_to_this
        else:
            rdict = {}

        for i in all_files:
            count = len(rdict)+1

            filename = i.split('/')
            filename = filename[-1].split('.')

            if len(filename[-1]) < 5:
                extension = filename[-1].upper()
            else:
                extension = 'EXT'

            if len(filename) > 1:
                filename = filename[-2]
            else:
                filename = i

            rdict[i] = dict(
                path=i,
                processed=False,
                drawn=False,
                count=count,
                filename=filename,
                extension=extension,
                status='UNPROCESSED',
            )

        return rdict

    def draw_more_pdf_files(self):
        self.reset_widgets(all=True)
        self.draw_pdf_files()

    def draw_pdf_files(self):
        """
        draws widgets from self.pdf_files, if present
        """
        if 'pdf_files' not in dir(self):
            return

        for path in self.pdf_files:
            if self.figure_height + self.pdf_ht > self.canvas.height():
                break

            if self.pdf_files[path]['drawn']:
                continue

            data = sqlite.ro('select * from files where local_path = (?)', path)
            if data:
                continue

            self.pdf_files[path]['drawn'] = True
            widget = PDFWidget(self.canvas, self, type='PDF')
            self.widgets['main'].append(widget)
            widget.data = self.pdf_files[path]
            widget.post_init()


    def from_dir_changed(self):
        """
        triggers if the texts in the plaintextedit is an actuall path
        """
        text = self.from_dir.toPlainText().strip()
        if os.path.exists(text):
            sqlite.w('update settings set source_path = (?) where id is 1', text)
            all_files = self.get_all_files_from_path(text, extension='PDF')
            self.pdf_files = self.make_all_files_dictionary(all_files)

            if not self.pdf_files:
                return

            self.reset_widgets(all=True)
            self.draw_pdf_files()

    def to_dir_changed(self):
        """
        not used
        """
        text = self.to_dir.toPlainText().strip()
        if os.path.exists(text):
            sqlite.w('update settings set destination_path = (?) where id is 1', text)

    def get_page_count_for_pdf(self, path):
        """
        :param path: string
        :return: integer
        """
        with open(path, "rb") as pdf_file:
            try: pdf_reader = PdfFileReader(pdf_file)
            except:
                PyPDF2.utils.PdfReadError
                return False
            return pdf_reader.numPages

    def decide_pages_per_cpu(self, inputpath):
        """
        counts physical cores and calculates a fair amount of images per core, a
        dictionary is created with letter (key) that will be used to save the temporary
        jpeg files. If the pdf has to less files, then job ignores multiple cpu's
        :param inputpath: string
        :return: dictionary or bool
        """
        def correct_rvdict(rv):
            """
            rv['a'] cannot be less than 2 (begin and end)
            this investegates, interfers and corrects that
            """
            if rv['a'] == []:
                rv.pop('a')

            elif rv['a'] == [0]:
                rv['b'].append(0)
                rv.pop('a')

            for i in rv:
                rv[i].sort()

        page_count = self.get_page_count_for_pdf(inputpath)
        cpu_count = psutil.cpu_count(logical=False)
        alphabet = list(string.ascii_lowercase)

        if page_count and page_count / 3 > cpu_count:
            rv = {}
            pages_per_cpu = math.ceil(page_count/cpu_count)
            pages_per_cpu = int(pages_per_cpu)
            for c in range(cpu_count-1, -1, -1):
                letter = alphabet[c]
                rv[letter] = []
                for cc in range(pages_per_cpu):
                    if page_count < 0:
                        break
                    rv[letter].append(page_count)
                    page_count -= 1

            correct_rvdict(rv)
            return rv

        return False

    def dummy(self):
        time.sleep(1)

    def convert_pdf_to_images(self, inputpath, outputpath):
        """
        if large pdf job is spread across cpu's else just one cpu-job
        extract jpeg files into a tmp_folder and then convert them to webp
        :param inputpath: string
        :param outputpath: string
        :return: dictionary
        """
        tmp_jpeg_folder = t.tmp_folder(inputpath, hash=True, delete=True)
        tmp_folder = t.tmp_folder(outputpath, hash=True, delete=True)

        rv = self.decide_pages_per_cpu(inputpath)
        if rv:
            image_list = convert_files_to_jpeg(rv, inputpath, tmp_jpeg_folder)
        else:
            image_list = convert_from_path(
                inputpath, output_folder=tmp_jpeg_folder, fmt='jpeg', paths_only=True, jpegopt=dict(quality=100)
            )

        if not image_list:
            return False

        jobs = []

        for count, jpeg_image_path in enumerate(image_list):
            filename = t.zero_prefiller(count, lenght=5)
            webp_save_path = f'{tmp_folder}/{filename}.webp'
            jobs.append((jpeg_image_path, webp_save_path, outputpath,))

        convert_files_to_webp(jobs)
        rv = recompress_fucntion(outputpath, tmp_folder)

        return dict(status=rv, tmp_webp_folder=tmp_folder, tmp_jpeg_folder=tmp_jpeg_folder, outputpath=outputpath)

app = QtWidgets.QApplication(sys.argv)
window = main()
app.exec_()