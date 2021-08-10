from PyQt5                  import QtCore, QtGui, QtWidgets
from PyQt5.QtGui            import QPixmap
from pathlib                import Path
from scripts.database_stuff import DB, sqlite
from scripts.tricks         import tech as t
import math
import os
import pathlib
import random
import shutil
import time

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
            self.main.show_hdd_spaces()
        elif ev.button() == 2:
            menu = QtWidgets.QMenu()
            yes_store_covers = menu.addAction('Store covers in database (quicker browsing, larger database)')
            no_store_covers = menu.addAction('Dont store covers in database (default)')
            action = menu.exec_(self.mapToGlobal(ev.pos()))
            if action == yes_store_covers:
                sqlite.w('update settings set store_covers = (?)', True)
            elif action == no_store_covers:
                sqlite.w('update settings set store_covers = (?)', False)


class VerticalLabel(QtWidgets.QWidget):
    def __init__(self, place, main, text):
        super().__init__(place)
        self.main = main
        self.parent = place
        self.text = text
        self.setStyleSheet('font: 14pt')
        self.setGeometry(0, 0, place.width(), place.height())
        self.show()

    def draw(self):
        painter = QtGui.QPainter(self)
        if self.text == 'PDF':
            painter.setPen(QtCore.Qt.gray)
        else:
            painter.setPen(QtCore.Qt.lightGray)
        painter.rotate(-90)
        half_width = int(self.parent.width() / 2) + 7
        painter.drawText(half_width - self.parent.height() - 5, half_width, self.text)
        painter.end()

    def paintEvent(self, event):
        self.draw()

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
        y = self.height() - SIZE - 1
        x = int(self.width() * 0.1)
        self.size_label.setGeometry(x, y, self.width() - x - 1, SIZE)
        self.size_label.setStyleSheet('background-color: rgb(20,20,170)')
        self.size_label.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
        filesize = os.path.getsize(self.data['path'])
        filesize = filesize / 1000000
        filesize = int(filesize)

        page_count = self.main.get_page_count_for_pdf(self.data['path'])
        if page_count:
            self.size_label.setText(f"{page_count} PAGES / {filesize} MB")
        else:
            self.size_label.setText(str(filesize) + 'MB')

        self.size_label.show()

        # NAME LABEL
        self.name_label = QtWidgets.QLabel(self)
        y = self.size_label.geometry().top() - SIZE - 1
        x = int(self.width() * 0.1)
        self.name_label.setGeometry(x, y, self.size_label.width(), SIZE)
        self.name_label.setStyleSheet('background-color: blue')
        self.name_label.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
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
        h = self.height() - self.name_label.geometry().top() - 1
        w = self.name_label.geometry().left()
        self.pdf_label.setGeometry(1, self.name_label.geometry().top(), w - 2, h)
        self.pdf_label.setStyleSheet('background-color: rgb(30,30,130) ; color: white')
        self.pdf_label.show()

        # VERTICAL LABEL
        self.set_vertical_label(self.data['extension'])

        # STATUS LABEL
        self.status_label = QtWidgets.QLabel(self)
        self.status_label.setStyleSheet('background-color: black ; color: white ; font: 8pt')
        self.status_label.setText(self.data['status'].upper())
        self.status_label.show()
        h = self.status_label.height() + 2
        y = self.name_label.geometry().top() - 1 - h
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
        frame_style = 'QFrame {background-color: rgb(180,180,180)}'
        tooltip_style = 'QToolTip {background-color: white ; color: black ; border: black}'
        self.setStyleSheet(frame_style + tooltip_style)
        self.setToolTip(self.data['path'])

    def set_cover_details_instead(self, file):
        rv = sqlite.ro('select * from files where md5 = (?)', self.data['md5'])
        if rv and rv[DB.files.cover_data]:
            self.name_label.setText(rv[DB.files.cover_data])
        else:
            _pixmap = QPixmap(file)
            pixels_size = f"{_pixmap.width()} x {_pixmap.height()}"
            fsize = os.path.getsize(file) / 1000000
            fsize = round(fsize, 2)
            text = f"COVER: {fsize}MB {pixels_size}"
            self.name_label.setText(text)
            sqlite.w('update files set cover_data = (?) where md5 = (?)', (text, self.data['md5'],))

    def set_pixmap(self, tmp_folder, delete=False):
        """
        pixmap is set first AFTER the file has been completly processed
        :param tmp_folder: string
        """
        if not os.path.exists(tmp_folder):
            return False

        if 'pixmap_label' in dir(self):
            return False

        self.pixmap_label = QtWidgets.QLabel(self)
        self.pixmap_label.setGeometry(1, 1, self.width() - 2, self.status_label.geometry().top() - 2)

        for walk in os.walk(tmp_folder):
            files = [walk[0] + '/' + x for x in walk[2]]

            if not files:
                return False

            files.sort()
            w = self.pixmap_label.width()
            h = self.pixmap_label.height()
            pixmap = QPixmap(
                files[0]).scaled(w, h, transformMode=QtCore.Qt.SmoothTransformation
            )
            self.pixmap_label.setPixmap(pixmap)
            self.set_cover_details_instead(files[0])

            self.pixmap_label.show()
            break

        if delete:
            shutil.rmtree(tmp_folder)

    def set_vertical_label(self, ext='CBZ'):
        if 'vetical_label' in dir(self):
            self.vetical_label.close()

        self.vetical_label = VerticalLabel(self.pdf_label, self.main, ext)

    def change_process_label(self, label, label_bck, current, total):
        max = self.width() - 4

        if 'process_ticker' not in dir(self):
            self.process_ticker = {}

        if label not in self.process_ticker:
            self.process_ticker.update({label: time.time() - 2})

        if current == total:
            value = max
        elif  current == total - 1:
            return
        elif time.time() - 0.5 > self.process_ticker[label]:
            self.process_ticker[label] = time.time()
            value = current / total
            value = int(max * value)
            if value > max:
                value = max
        else:
            return

        if label.geometry().right() >= max:
            return

        label.setGeometry(label.geometry().left(), label.geometry().top(), value, label.height())
        label_bck.setGeometry(label.geometry().left()-1, label.geometry().top()-1, label.width()+2, label.height()+2)

    def change_process_label_one(self, current, total):
        self.change_process_label(self.progress_label_one, self.backlabel_one, current=current, total=total)

    def change_process_label_two(self, current, total):
        self.change_process_label(self.progress_label_two, self.backlabel_two, current=current, total=total)

    def preprocess_file(self):
        if self.data['processed']:
            return

        self.data['processed'] = True
        self.data['work'] = True
        self.status_label.setText('QUEUED')
        self.status_label.setStyleSheet('background-color: darkMagenta ; color: white')
        y = self.status_label.geometry().top()
        self.status_label.setGeometry(1,y+1, self.width() - 2, self.status_label.height()-1)

        self.backlabel_one = QtWidgets.QLabel(self, styleSheet='background-color: black')
        self.backlabel_two = QtWidgets.QLabel(self, styleSheet='background-color: black')

        self.progress_label_one = QtWidgets.QLabel(self)
        y = self.status_label.geometry().top() - 7
        self.progress_label_one.setGeometry(2, y, 0, 5)
        self.progress_label_one.setStyleSheet('background-color: darkCyan')

        self.progress_label_two = QtWidgets.QLabel(self)
        y = self.progress_label_one.geometry().top() - 6
        self.progress_label_two.setGeometry(2, y, 0, 5)
        self.progress_label_two.setStyleSheet('background-color: lightBlue')

        c = {self.backlabel_one: self.progress_label_one, self.backlabel_two: self.progress_label_two}
        for i,j in c.items():
            i.setGeometry(i.geometry().left() - 1, i.geometry().top() - 1, 0 ,j.height() + 2)
            i.show()
            j.show()

        t.start_thread(self.main.dummy, worker_arguments=0.1)
        t.start_thread(self.process_file, finished_function=[self.set_vertical_label, self.load_next_job])

    def process_file(self):
        """
        alot of checks is beeing made before the file is beeing
        processed and once its done pixmap will be set and tmp_folders
        will be deleted and self.data['processed'] will be set to True
        :return: bool
        """
        def error(self, text, stylesheet='background-color: red ; color: white'):
            self.status_label.setText(text)
            self.status_label.setStyleSheet(stylesheet)

        self.status_label.setText('PROCESSING')
        self.status_label.setStyleSheet('background-color: magenta ; color: white')

        to_dir = self.main.to_dir.toPlainText()
        filename = self.data['filename']

        if not to_dir:
            error(self, 'IMPOSSIBLE OUTPUT FOLDER')
            return False

        elif not os.path.exists(self.data['path']):
            error(self, 'INPUT FILE MISSING')
            return False

        elif filename.find('/') > -1 or filename.find('\\') > -1:
            error(self, 'SHITTY OS')
            return False

        if len(to_dir) > 0 and not os.path.exists(to_dir):
            pathlib.Path(to_dir).mkdir(parents=True)

        if not os.path.exists(to_dir):
            error(self, 'ERROR CREATING FOLDER')
            return False

        outputpath = to_dir + '/' + filename + '.cbz'
        outputpath = os.path.abspath(os.path.expanduser(outputpath))

        data = sqlite.ro('select * from files where md5 = (?) and converted = (?)', (self.data['md5'], True,))
        if data and os.path.exists(outputpath) and os.path.getsize(outputpath) > 0:
            error(self, 'FILE ALREADY PROCESSED')
            return False

        elif os.path.exists(outputpath) and os.path.getsize(outputpath) > 0:
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

        rv = self.main.convert_pdf_to_images(inputpath=self.data['path'], outputpath=outputpath, widget=self)
        self.data['work'] = False

        if rv['status']:
            self.set_pixmap(rv['tmp_webp_folder'])

            if os.path.exists(rv['tmp_webp_folder']):
                shutil.rmtree(rv['tmp_webp_folder'])

            if os.path.exists(rv['tmp_jpeg_folder']):
                shutil.rmtree(rv['tmp_jpeg_folder'])

            self.status_label.setText('PROCESSED')
            self.status_label.setStyleSheet('background-color: green ; color: white')

            self.name_label.setToolTip(rv['outputpath'])

            filesize = os.path.getsize(rv['outputpath'])
            filesize = filesize / 1000000
            filesize = int(filesize)
            self.size_label.setText(str(self.size_label.text()) + ' to ' + str(filesize) + 'MB')

            sqlite.w('update files set converted = (?) where md5 = (?)', (True, self.data['md5'],))

            if self.main.delete_source_pdf.isChecked():
                os.remove(self.data['path'])

        elif not rv['status']:
            self.status_label.setText('HDD FULL')
            self.status_label.setStyleSheet('background-color: red ; color: black')

    def load_next_job(self):
        """
        if self.main.continous_convertion is checked another
        job is added as long as there are files to job from
        """
        for count in range(3):
            random.shuffle(self.main.widgets['main'])
            if self.main.continous_convertion.isChecked():
                for i in self.main.widgets['main']:
                    if count == 0 and i.status_label.text() == 'QUEUED':
                        return

                    if count > 0 and not i.data['processed']:
                        i.preprocess_file()
                        return True

                if count == 1:
                    self.main.draw_more_pdf_files()

    def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
        class ShadeLabel(QtWidgets.QLabel):
            def __init__(self, place):
                super().__init__(place)
                place.status_label.setText('DELETED FROM HDD')
                place.status_label.setStyleSheet('background-color: red ; color: white')
                self.setGeometry(0,0,place.width(),place.height())
                self.setStyleSheet('background-color: rgba(30,30,30,180)')
                self.show()
            def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
                pass

        if ev.button() == 1:
            self.preprocess_file()

        elif ev.button() == 2:
            menu = QtWidgets.QMenu()
            process_file = False

            if self.data['processed'] and os.path.exists(self.data['path']):
                process_file = menu.addAction('RE-PROCESS FILE (may fail)')
            elif os.path.exists(self.data['path']):
                process_file = menu.addAction('PROCESS FILE')
            else:
                menu.addAction('FILE GONE!')

            menu.addSeparator()

            delete_file = menu.addAction('DELETE FILE (WITHOUT CONFIRMATION!)')

            action = menu.exec_(self.mapToGlobal(ev.pos()))

            if action == process_file:
                self.data['processed'] = False
                self.preprocess_file()

            elif action == delete_file:
                if os.path.exists(self.data['path']):
                    os.remove(self.data['path'])

                ShadeLabel(self)