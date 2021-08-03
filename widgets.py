from PyQt5          import QtCore, QtGui, QtWidgets
from PyQt5.QtGui    import QPixmap
from database_stuff import DB, sqlite
from pathlib        import Path
from tricks         import tech as t
import math
import os
import pathlib
import random
import shutil

class GOD(QtWidgets.QFrame):
    def __init__(self, place, main, type=None, show=True):
        super().__init__(place)
        self.main = main
        self.parent = place

        if type:
            self.type = type

        if show:
            self.show()

class DevLabel(QtWidgets.QLabel):
    def __init__(self, place, main):
        super().__init__(place)
        self.main = main
        self.setGeometry(0,0,place.width(),place.height())
        self.setStyleSheet('background-color: rgba(0,0,0,0)')
    def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
        if ev.button() == 1:
            self.main.dev_mode = False
            self.main.setStyleSheet('background-color: rgb(20,20,20) ; color: rgb(255,255,255)')
            self.main.setWindowTitle('Back to normal')
        elif ev.button() == 2:
            self.main.dev_mode = True
            self.main.setStyleSheet('background-color: rgb(80,10,10) ; color: white')
            self.main.setWindowTitle('DEV MODE!')


class VerticalLabel(QtWidgets.QWidget):
    def __init__(self, place, main, text):
        super().__init__(place)
        self.main = main
        self.parent = place
        self.text = text
        self.setStyleSheet('font: 14pt')
        self.setGeometry(0, 0, place.width(), place.height())
        self.show()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setPen(QtCore.Qt.white)
        painter.rotate(-90)
        half_width = int(self.parent.width() / 2) + 7
        painter.drawText(half_width - self.parent.height() - 5, half_width, self.text)
        painter.end()

class PDFWidget(GOD):
    def make_labels(self):
        """
        visual labels showing filename, filesize, extension (vertical)
        and status label
        """
        SIZE = math.ceil(self.height() * 0.08)
        SIZE = int(SIZE)

        # SIZE LABEL
        self.size_label = QtWidgets.QLabel(self)
        y = self.height() - SIZE - 3
        x = int(self.width() * 0.1)
        self.size_label.setGeometry(x, y, self.width(), SIZE)
        self.size_label.setStyleSheet('background-color: rgb(20,20,170)')
        self.size_label.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
        filesize = os.path.getsize(self.data['path'])
        filesize = filesize / 1000000
        filesize = round(filesize, 2)
        self.size_label.setText(str(filesize) + 'MB')
        self.size_label.show()

        # NAME LABEL
        self.name_label = QtWidgets.QLabel(self)
        y = self.size_label.geometry().top() - SIZE - 3
        x = int(self.width() * 0.1)
        self.name_label.setGeometry(x, y, self.width() - x, SIZE)
        self.name_label.setStyleSheet('background-color: blue')
        self.name_label.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
        self.name_label.setToolTip(self.data['path'])
        self.name_label.show()

        filename = self.data['filename']
        for c in range(len(self.data['filename'])-1,0,-1):

            if c == len(self.data['filename'])-1:
                text = filename
            else:
                text = filename[0:c] + '...'

            label = QtWidgets.QLabel(self, text=text)
            label.show()
            lw = label.width()
            label.close()
            if lw <= self.name_label.width():
                self.name_label.setText(text)
                break

        # EXTENSION LABEL
        self.pdf_label = QtWidgets.QLabel(self)
        h = self.height() - self.name_label.geometry().top() - 3
        w = self.name_label.geometry().left()
        self.pdf_label.setGeometry(0, self.name_label.geometry().top(), w, h)
        self.pdf_label.setStyleSheet('background-color: black ; color: white')
        self.pdf_label.show()

        # VERTICAL LABEL
        self.vetical_label = VerticalLabel(self.pdf_label, self.main, self.data['extension'])

        # STATUS LABEL
        self.status_label = QtWidgets.QLabel(self)
        self.status_label.setStyleSheet('background-color: black ; color: white ; font: 8pt')
        self.status_label.setText(self.data['status'].upper())
        self.status_label.show()
        h = self.status_label.height()
        y = self.name_label.geometry().top() - 3 - h
        self.status_label.setGeometry(0, y, self.width(), h)
        self.status_label.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)

    def set_position(self):
        """
        self.setGeometry()
        """
        if self.main.pdf_wt + self.main.figure_width > self.main.canvas.width():
            self.main.pdf_wt = 3
            self.main.pdf_ht += self.main.figure_height + 3

        self.setGeometry(self.main.pdf_wt, self.main.pdf_ht, self.main.figure_width, self.main.figure_height)
        self.main.pdf_wt += self.width() + 3

    def post_init(self):
        """
        what happens directly after widget is born
        """
        self.set_position()
        self.make_labels()
        self.setStyleSheet('background-color: rgb(180,180,180)')

    def set_pixmap(self, tmp_folder):
        """
        pixmap is set first AFTER the file has been completly processed
        :param tmp_folder: string
        """
        if not os.path.exists(tmp_folder):
            return False

        label = QtWidgets.QLabel(self)
        label.setGeometry(1, 1, self.width() - 2, self.status_label.geometry().top() - 2)
        label.show()

        for walk in os.walk(tmp_folder):
            files = [walk[0] + '/' + x for x in walk[2]]

            if not files:
                return False

            files.sort()

            pixmap = QPixmap(
                files[0]).scaled(label.width(), label.height(), transformMode=QtCore.Qt.SmoothTransformation
            )

            label.setPixmap(pixmap)
            break

    def process_file(self):
        """
        alot of checks is beeing made before the file is beeing
        processed and once its done pixmap will be set and tmp_folders
        will be deleted and self.data['processed'] will be set to True
        :return: bool
        """
        self.data['processed'] = True

        def error(self, text, stylesheet='background-color: red ; color: white'):
            self.status_label.setText(text)
            self.status_label.setStyleSheet(stylesheet)
            self.load_next_job()

        md5 = t.md5_hash_file(self.data['path'])
        data = sqlite.ro('select * from files where md5 = (?)', md5)
        if data:
            error(self, 'FILE ALREADY PROCESSED')
            return False

        to_dir = self.main.to_dir.toPlainText()
        filename = self.data['filename']

        if not to_dir:
            error(self, 'IMPOSSIBLE OUTPUT FOLDER')
            return False

        if to_dir and not os.path.exists(to_dir):
            pathlib.Path(to_dir).mkdir(parents=True)

        if not os.path.exists(to_dir):
            error(self, 'ERROR CREATING FOLDER')
            return False

        if filename.find('/') > -1 or filename.find('\\') > -1:
            error(self, 'SHITTY OS')
            return False

        outputpath = to_dir + '/' + filename + '.cbz'
        outputpath = os.path.abspath(os.path.expanduser(outputpath))

        if os.path.exists(outputpath) and os.path.getsize(outputpath) > 0:
            error(self, 'DESTINATION EXISTS', 'background-color: green ; color: white')
            return False

        elif os.path.exists(outputpath) and os.path.getsize(outputpath) == 0:
            try: os.remove(outputpath)
            except:
                error(self, 'PERMISSION ERROR')
                return False

        try:
            Path(outputpath).touch()
            if os.path.exists(outputpath):
                try: os.remove(outputpath)
                except:
                    error(self, 'PERMISSION ERROR')
                    return False
        except:
            error(self, 'PERMISSION ERROR')
            return False

        rv = self.main.convert_pdf_to_images(inputpath=self.data['path'], outputpath=outputpath)

        if rv['status']:
            self.set_pixmap(rv['tmp_webp_folder'])

            if os.path.exists(rv['tmp_webp_folder']):
                shutil.rmtree(rv['tmp_webp_folder'])

            if os.path.exists(rv['tmp_jpeg_folder']):
                shutil.rmtree(rv['tmp_jpeg_folder'])

            self.status_label.setText('PROCESSED')
            self.status_label.setStyleSheet('background-color: green ; color: white')

            self.vetical_label.close()
            self.vetical_label = VerticalLabel(self.pdf_label, self.main, 'CBZ')

            self.name_label.setToolTip(rv['outputpath'])

            filesize = os.path.getsize(rv['outputpath'])
            filesize = filesize / 1000000
            filesize = round(filesize, 2)
            self.size_label.setText(str(self.size_label.text()) + ' to ' + str(filesize) + 'MB')

            query, values = sqlite.empty_insert_query(table='files')
            values[DB.files.md5] = md5
            values[DB.files.local_path] = self.data['path']
            sqlite.w(query, values)

            if self.main.delete_source_pdf.isChecked():
                os.remove(self.data['path'])

        if not self.load_next_job() and self.main.continous_convertion.isChecked():
            self.main.draw_more_pdf_files()
            self.load_next_job()

    def load_next_job(self):
        """
        if self.main.continous_convertion is checked another
        job is added as long as there are files to job from
        """
        random.shuffle(self.main.widgets['main'])
        if self.main.continous_convertion.isChecked():
            for i in self.main.widgets['main']:
                if not i.data['processed']:
                    i.status_label.setText('PROCESSING')
                    i.status_label.setStyleSheet('background-color: magenta ; color: white')
                    t.start_thread(self.main.dummy, finished_function=i.process_file)
                    return True

    def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
        if self.main.dev_mode:
            return

        if ev.button() == 1:

            self.status_label.setText('PROCESSING')
            self.status_label.setStyleSheet('background-color: magenta ; color: white')

            t.start_thread(self.main.dummy, finished_function=self.process_file)

        elif ev.button() == 2:
            self.data['processed'] = False
            print(self.data['path'] + ' removed from blocklist!')