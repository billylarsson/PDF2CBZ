#!/usr/bin/env python3
from PIL            import Image
from PyQt5          import QtCore, QtWidgets
from PyQt5.QtGui    import QPixmap
from database_stuff import DB, sqlite
from functools      import partial
from pdf2image      import convert_from_path, pdfinfo_from_path
from tricks         import tech as t
from widgets        import DevLabel, PDFWidget
from zipfile        import BadZipFile, ZipFile
import concurrent.futures
import math
import os
import platform
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

    source_file, output_folder, first_page, last_page, output_file, poppler_path = job

    image_list = convert_from_path(
        source_file,
        dpi=200,
        first_page=first_page,
        last_page=last_page,
        fmt='jpeg',
        output_file=output_file,
        output_folder=output_folder,
        paths_only=True,
        jpegopt=dict(quality=100, optimize=True),
        poppler_path=poppler_path,
    )
    return image_list
def convert_files_to_jpeg(joblist, inputpath, tmp_jpeg_folder, poppler_path=None, show_hdd_space=None):
    """
    if tmp_folder goes below 100mb False is returned
    :param joblist: dictionary with letters as keys containing list indexes (int)
    :param inputpath: string to pdf file-path
    :param tmp_jpeg_folder: string
    :return: list with image paths, or False if hdd full
    """
    image_list = []
    threadlist = []
    for letter in joblist:
        threadlist.append((inputpath, tmp_jpeg_folder, joblist[letter][0], joblist[letter][-1], letter, poppler_path,))

    with concurrent.futures.ProcessPoolExecutor() as executor:
        for _, rv in zip(joblist, executor.map(pdf_to_jpeg, threadlist)):
            for path in rv:
                image_list.append(path)

            if show_hdd_space:
                show_hdd_space()

            _, _, tmp_free = shutil.disk_usage(tmp_jpeg_folder)
            if (tmp_free/1000000) < 100:
                return False

    image_list.sort()
    return image_list

def jpeg_to_webp(job):
    """
    jpeg to webp
    :param job: tuple -> 0:jpeg_file_path, 1:save_webp_file_path, 2:webp_quality
    :return: string -> webp_file_location
    """
    source_path, destination_path, _, webp_quality = job
    image = Image.open(source_path)
    image.save(destination_path, 'webp', method=6, quality=webp_quality)
    return dict(source=source_path, destination=destination_path)
def convert_files_to_webp(joblist, show_hdd_space=None):
    """
    :param joblist: list with jpeg_files
    :return:
    """
    with concurrent.futures.ProcessPoolExecutor() as executor:
        for _, rv in zip(joblist, executor.map(jpeg_to_webp, joblist)):

            if rv and os.path.getsize(rv['destination']) > 0:
                os.remove(rv['source'])

            if show_hdd_space:
                show_hdd_space()

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

    if platform.system() != "Windows":
        os.sync()

    shutil.make_archive(zipfile, 'zip', tmp_folder)
    zipfile += '.zip'

    if platform.system() != "Windows":
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

class PDF2CBZmain(QtWidgets.QMainWindow):
    def __init__(self):
        super(PDF2CBZmain, self).__init__()

        self.setWindowTitle('PDF to WEBP-compressed CBZ v0.2 build:667')
        self.setStyleSheet('background-color: rgb(20,20,20) ; color: rgb(255,255,255)')

        if 'devmode' in sys.argv:
            self.dev_mode = True
        else:
            self.dev_mode = False

        self.setFixedSize(1800, 1000)
        self.widgets = dict(main=[], pdf=[], cbz=[])

        self.wt = 3
        self.ht = 3

        self.reset_ht_wt()

        self.from_dir = QtWidgets.QPlainTextEdit(self, toolTip='SOURCE FOLDER')
        self.from_dir.setStyleSheet('background-color: rgb(30,30,30) ; color: rgb(235,235,235)')
        self.from_dir.setGeometry(self.wt, self.ht, int(self.width() * 0.4), 30)
        self.ht += self.from_dir.height() + 3
        self.from_dir.textChanged.connect(self.from_dir_changed)

        self.to_dir = QtWidgets.QPlainTextEdit(self, toolTip='DESTINATION FOLDER')
        self.to_dir.setStyleSheet('background-color: rgb(30,30,30) ; color: rgb(235,235,235)')
        self.to_dir.setGeometry(self.wt, self.ht, int(self.width() * 0.4), 30)
        self.ht += self.to_dir.height() + 3
        self.to_dir.textChanged.connect(self.to_dir_changed)

        self.canvas = QtWidgets.QFrame(self)
        self.canvas.setStyleSheet('background-color: rgb(25,25,25)')
        self.canvas.setGeometry(self.wt, self.ht, self.width() - self.wt * 2, self.height() - self.ht - 5)

        self.webp_label = QtWidgets.QLabel(self)
        self.webp_label.setStyleSheet('background-color: rgb(30,30,30) ; color: rgb(235,235,235) ; font: 14pt')
        self.webp_label.move(self.from_dir.geometry().right() + 3, self.from_dir.geometry().top())
        self.webp_label.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
        self.webp_label.setFixedWidth(200)
        DevLabel(self.webp_label, self)

        webp_value = t.retrieve_setting(DB.settings.webp_slider)
        if not webp_value:
            webp_value = 70

        self.webp_slider = QtWidgets.QSlider(self, minimum=0, maximum=100, value=webp_value)
        self.webp_slider.setFixedWidth(self.webp_label.width())
        self.webp_slider.move(self.webp_label.geometry().left(), self.webp_label.geometry().bottom() + 3)
        self.webp_slider.setOrientation(1)
        self.webp_slider.valueChanged.connect(self.slider_changed)
        self.slider_changed()

        self.continous_convertion = QtWidgets.QCheckBox(self, text='CONTINOUS')
        self.continous_convertion.setToolTip('Continous conversions, start another once current is completed!')
        self.continous_convertion.move(self.webp_label.geometry().right() + 3, 3)
        self.continous_convertion.setStyleSheet('background-color: rgb(30,30,30) ; color: rgb(235,235,235)')

        rv = t.retrieve_setting(DB.settings.continous)
        if rv:
            self.continous_convertion.setChecked(rv)

        self.continous_convertion.stateChanged.connect(partial(
            self.save_setting, self.continous_convertion, 'continous'))

        self.delete_source_pdf = QtWidgets.QCheckBox(self, text='DELETE PDF')
        self.delete_source_pdf.move(self.continous_convertion.geometry().right() + 3, 3)
        self.delete_source_pdf.setToolTip('When jobs complete, the PDF source will be permanently deleted!')
        self.delete_source_pdf.setStyleSheet('background-color: rgb(30,30,30) ; color: rgb(235,235,235)')

        rv = t.retrieve_setting(DB.settings.del_source)
        if rv:
            self.delete_source_pdf.setChecked(rv)

        self.delete_source_pdf.stateChanged.connect(partial(
            self.save_setting, self.delete_source_pdf, 'del_source'))

        self.pdf_threads = QtWidgets.QCheckBox(self, text='PDF THREADS', checked=True)
        self.pdf_threads.setFixedWidth(self.pdf_threads.width() + 10)
        self.pdf_threads.move(self.delete_source_pdf.geometry().right() + 3, 3)
        self.pdf_threads.setToolTip('Checked == FASTER')
        self.pdf_threads.setStyleSheet('background-color: rgb(30,30,30) ; color: rgb(235,235,235)')

        self.wepb_threads = QtWidgets.QCheckBox(self, text='WEBP THREADS', checked=True)
        self.wepb_threads.setFixedWidth(self.wepb_threads.width() + 20)
        self.wepb_threads.move(self.pdf_threads.geometry().right() + 3, 3)
        self.wepb_threads.setToolTip('Checked == FASTER')
        self.wepb_threads.setStyleSheet('background-color: rgb(30,30,30) ; color: rgb(235,235,235)')

        self.btn_more = QtWidgets.QPushButton(self, text='NEXT')
        self.btn_more.move(self.wepb_threads.geometry().right() + 3, 3)
        self.btn_more.setFixedWidth(int(self.btn_more.width() * 0.7))
        self.btn_more.clicked.connect(self.draw_more_pdf_files)

        self.btn_refresh = QtWidgets.QPushButton(self, text='REFRESH')
        self.btn_refresh.move(self.btn_more.geometry().right() + 3, 3)
        self.btn_refresh.setFixedWidth(int(self.btn_refresh.width() * 0.7))
        self.btn_refresh.clicked.connect(self.from_dir_changed)

        tt = 'example -> /home/user/poppler-0.68.0/bin\n\nWindows download: http://blog.alivate.com.au/poppler-windows/'
        self.poppler_path = QtWidgets.QPlainTextEdit(self, toolTip=tt)
        self.poppler_path.setStyleSheet('background-color: rgb(30,30,30) ; color: rgb(235,235,235)')
        x = self.webp_slider.geometry().right() + 3
        y = self.webp_slider.geometry().top()
        w = self.btn_refresh.geometry().right() - self.continous_convertion.geometry().left()
        h = self.webp_label.height()
        self.poppler_path.setGeometry(x, y, w, h)
        self.poppler_path.textChanged.connect(self.poppler_path_changed)

        cyd = {
            'PDF SOURCE FOLDER': self.from_dir,
            'CBZ DESTINATION FOLDER': self.to_dir,
            'POPPLER PATH': self.poppler_path,
        }

        for i,j in cyd.items():
            label = QtWidgets.QLabel(j, text=i, alignment=QtCore.Qt.AlignRight|QtCore.Qt.AlignVCenter)
            label.setStyleSheet('background-color: rgba(0,0,0,0) ; color: gray ; font: 10pt')
            label.setGeometry(0,0,j.width() - 20,j.height())
            label.lower()

        self.deside_figure_size()

        if os.path.exists('background.webp'):
            bg = QtWidgets.QLabel(self)
            bg.setGeometry(0,0,self.width(),self.height())
            pixmap = QPixmap('background.webp').scaled(bg.width(), bg.height())
            bg.setPixmap(pixmap)
            bg.lower()

        self.show()

        setting_plaintext_label = {
            DB.settings.source_path: self.from_dir,
            DB.settings.destination_path: self.to_dir,
            DB.settings.poppler_path: self.poppler_path,
         }

        for key, label in setting_plaintext_label.items():
            rv = t.retrieve_setting(key)
            if rv:
                label.setPlainText(rv)

        self.show_hdd_spaces()

    def show_hdd_spaces(self):
        title = 'PDF to WEBP-compressed CBZ v0.2 build:667'

        base_dir = t.tmp_folder(create_dir=False, return_base=True)
        if os.path.exists(base_dir):
            tmp_total, tmp_used, tmp_free = shutil.disk_usage(base_dir)
            title += f" | Working dir: TOTAL: {int(tmp_total/1000000)}mb "
            title += f"USED: {int(tmp_used/1000000)}mb FREE: {int(tmp_free/1000000)}mb"

        to_dir = self.to_dir.toPlainText().strip()
        if os.path.exists(to_dir):
            to_total, to_used, to_free = shutil.disk_usage(to_dir)
            title += f" | Destination dir: TOTAL: {int(to_total/1000000)}mb "
            title += f"USED: {int(to_used/1000000)}mb FREE: {int(to_free/1000000)}mb"

        self.setWindowTitle(title)

    def get_poppler_path(self):
        poppler_path = self.poppler_path.toPlainText().strip()
        if not os.path.exists(poppler_path):
            poppler_path = None
        return poppler_path

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

        image_list = None

        poppler_path = self.get_poppler_path()

        if self.pdf_threads.isChecked():
            rv = self.decide_pages_per_cpu(inputpath)
            if rv:
                image_list = convert_files_to_jpeg(rv, inputpath, tmp_jpeg_folder, poppler_path, self.show_hdd_spaces)

        if not image_list:
            image_list = pdf_to_jpeg((inputpath, tmp_jpeg_folder, None, None, None, poppler_path,))

        if not image_list:
            return False

        jobs = []

        for count, jpeg_image_path in enumerate(image_list):
            filename = t.zero_prefiller(count, lenght=5)
            webp_save_path = f'{tmp_folder}/{filename}.webp'
            webp_save_path = os.path.abspath(os.path.expanduser(webp_save_path))

            jobs.append((jpeg_image_path, webp_save_path, outputpath, self.webp_slider.value()))

        if not self.wepb_threads.isChecked():
            for i in jobs:
                convert_files_to_webp(i)
        else:
            convert_files_to_webp(jobs, self.show_hdd_spaces)

        rv = recompress_fucntion(outputpath, tmp_folder)

        return dict(status=rv, tmp_webp_folder=tmp_folder, tmp_jpeg_folder=tmp_jpeg_folder, outputpath=outputpath)

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

        if cpu_count >= len(alphabet):
            cpu_count = len(alphabet) - 1

        if page_count and page_count / 3 > cpu_count:
            rv = {}
            pages_per_cpu = math.ceil(page_count / cpu_count)
            pages_per_cpu = int(pages_per_cpu)
            for c in range(cpu_count - 1, -1, -1):
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

        self.figure_height -= 3  # gives geometry.height() breathing room

        # WIDTH >
        self.figure_width = self.figure_height * 0.6
        av = math.floor(self.canvas.width() / self.figure_width)
        left_over = self.canvas.width() - (self.figure_width * math.floor(av))
        if left_over > av:
            self.figure_width += math.floor(left_over / math.floor(av))
            self.figure_width = int(self.figure_width)

        self.figure_width -= 3  # gives geometry.width() breathing room

    def draw_more_pdf_files(self):
        self.reset_widgets(all=True)
        self.draw_pdf_files()

    def draw_pdf_files(self):
        """
        draws widgets from self.pdf_files, if present
        """
        def thread_extract_image(widget, tmp_folder):
            pdf_to_jpeg((widget.data['path'], tmp_folder, 0, 1, 'Cover', self.get_poppler_path()))

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

            tmp_folder = t.tmp_folder()
            t.start_thread(
                thread_extract_image, worker_arguments=(widget, tmp_folder,),
                finished_function=widget.set_pixmap, finished_arguments=(tmp_folder, True,),
                threads=4, name='refresh'
            )

            if self.dev_mode:
                return

    def dummy(self, sleep=1):
        time.sleep(sleep)

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

    def get_page_count_for_pdf(self, path):
        """
        :param path: string
        :return: integer or False
        """
        poppler_path = self.get_poppler_path()

        rv = pdfinfo_from_path(path, poppler_path=poppler_path)

        if rv and rv['Pages']:
            return rv['Pages']
        else:
            return False

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
            count = len(rdict) + 1
            i = os.path.abspath(os.path.expanduser(i))

            if platform.system() == "Windows":
                filename = i.split('\\')
            else:
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

    def poppler_path_changed(self):
        """
        triggers if the texts in the plaintextedit is an actuall path
        """
        text = self.poppler_path.toPlainText().strip()
        if os.path.exists(text):
            sqlite.w('update settings set poppler_path = (?) where id is 1', text)

    def reset_ht_wt(self):
        self.pdf_wt = 3
        self.pdf_ht = 3

        self.cbz_wt = 3
        self.cbz_ht = 3

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

    def save_setting(self, widget, setting_var):
        widget_type = widget.metaObject().className()
        if widget_type == 'QSlider':
            value = widget.value()
        elif widget_type == 'QCheckBox':
            value = widget.isChecked()
        else:
            print('You need to spank your monkey harder!')
            return

        sqlite.w(f'update settings set {setting_var} = (?) where id is 1', value)

    def slider_changed(self):
        self.webp_label.setText('WEBP QUALITY: ' + str(self.webp_slider.value()))
        self.save_setting(self.webp_slider, 'webp_slider')

    def to_dir_changed(self):
        """
        triggers if the texts in the plaintextedit is an actuall path
        """
        text = self.to_dir.toPlainText().strip()
        if os.path.exists(text):
            sqlite.w('update settings set destination_path = (?) where id is 1', text)

app = QtWidgets.QApplication(sys.argv)
window = PDF2CBZmain()
app.exec_()
