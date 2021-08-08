from script_pack.sqlite_handler import SQLite
import os

sqlite = SQLite(
    DATABASE_FILENAME=os.environ['DATABASE_FILENAME'],
    DATABASE_FOLDER=os.environ['DATABASE_FOLDER'],
    DATABASE_SUBFOLDER=os.environ['DATABASE_SUBFOLDER'],
    INI_FILE_NAME=os.environ['INI_FILE_NAME'],
    INI_FILE_DIR=os.environ['INI_FILE_DIR'],
)

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
        resize_4k = sqlite.db_sqlite('settings', 'resize_4k', 'integer')
        store_covers = sqlite.db_sqlite('settings', 'store_covers', 'integer')

    class files:
        md5 = sqlite.db_sqlite('files', 'md5')
        cover = sqlite.db_sqlite('files', 'cover', 'blob')
        converted = sqlite.db_sqlite('files', 'converted', 'integer')
        cover_data = sqlite.db_sqlite('files', 'cover_data')

