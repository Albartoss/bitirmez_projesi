from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QTabWidget,
    QWidget, QFormLayout, QLineEdit, QComboBox, QHBoxLayout, QMessageBox, QListWidget, QTableWidgetItem
)
import sqlite3
from modules.config import DB_PATH
from modules.lang.translator import translator as _

class StorageUnitManageWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(_("storage_manage.title"))
        self.setMinimumSize(600, 400)

        self.tabs = QTabWidget()
        self.fridge_tab = QWidget()
        self.shelf_tab = QWidget()

        self.tabs.addTab(self.fridge_tab, _("storage_manage.tab_fridges"))
        self.tabs.addTab(self.shelf_tab, _("storage_manage.tab_shelves"))

        self.setup_fridge_tab()
        self.setup_shelf_tab()

        layout = QVBoxLayout()
        layout.addWidget(self.tabs)
        self.setLayout(layout)

        self.load_units()

    def setup_fridge_tab(self):
        layout = QVBoxLayout()
        self.fridge_list = QListWidget()
        self.fridge_list.itemClicked.connect(self.fill_fridge_form)

        form = QFormLayout()
        self.fridge_name = QLineEdit()
        self.fridge_type = QComboBox()
        self.fridge_type.addItems([
            _("storage_manage.fridge_type.standard"),
            _("storage_manage.fridge_type.industrial"),
            _("storage_manage.fridge_type.mini")
        ])
        self.fridge_capacity = QLineEdit()
        self.fridge_location = QLineEdit()

        form.addRow(_("storage_manage.name") + ":", self.fridge_name)
        form.addRow(_("storage_manage.type") + ":", self.fridge_type)
        form.addRow(_("storage_manage.capacity") + ":", self.fridge_capacity)
        form.addRow(_("storage_manage.location") + ":", self.fridge_location)

        btn_layout = QHBoxLayout()
        add_btn = QPushButton(_("storage_manage.add"))
        update_btn = QPushButton(_("storage_manage.update"))
        del_btn = QPushButton(_("storage_manage.delete"))
        add_btn.clicked.connect(self.add_fridge)
        update_btn.clicked.connect(self.update_fridge)
        del_btn.clicked.connect(self.delete_fridge)
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(update_btn)
        btn_layout.addWidget(del_btn)

        layout.addWidget(QLabel(_("storage_manage.list_fridges")))
        layout.addWidget(self.fridge_list)
        layout.addLayout(form)
        layout.addLayout(btn_layout)
        self.fridge_tab.setLayout(layout)

    def setup_shelf_tab(self):
        layout = QVBoxLayout()
        self.shelf_list = QListWidget()
        self.shelf_list.itemClicked.connect(self.fill_shelf_form)

        form = QFormLayout()
        self.shelf_name = QLineEdit()
        self.shelf_type = QComboBox()
        self.shelf_type.addItems([
            _("storage_manage.shelf_type.wall"),
            _("storage_manage.shelf_type.center"),
            _("storage_manage.shelf_type.under_counter")
        ])
        self.shelf_capacity = QLineEdit()
        self.shelf_location = QLineEdit()

        form.addRow(_("storage_manage.name") + ":", self.shelf_name)
        form.addRow(_("storage_manage.type") + ":", self.shelf_type)
        form.addRow(_("storage_manage.capacity") + ":", self.shelf_capacity)
        form.addRow(_("storage_manage.location") + ":", self.shelf_location)

        btn_layout = QHBoxLayout()
        add_btn = QPushButton(_("storage_manage.add"))
        update_btn = QPushButton(_("storage_manage.update"))
        del_btn = QPushButton(_("storage_manage.delete"))
        add_btn.clicked.connect(self.add_shelf)
        update_btn.clicked.connect(self.update_shelf)
        del_btn.clicked.connect(self.delete_shelf)
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(update_btn)
        btn_layout.addWidget(del_btn)

        layout.addWidget(QLabel(_("storage_manage.list_shelves")))
        layout.addWidget(self.shelf_list)
        layout.addLayout(form)
        layout.addLayout(btn_layout)
        self.shelf_tab.setLayout(layout)

    def load_units(self):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fridges (
                id INTEGER PRIMARY KEY,
                name TEXT,
                type TEXT,
                max_capacity INTEGER,
                location TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS shelves (
                id INTEGER PRIMARY KEY,
                name TEXT,
                type TEXT,
                max_capacity INTEGER,
                location TEXT
            )
        """)
        conn.commit()

        self.fridge_list.clear()
        cursor.execute("SELECT id, name, type, max_capacity, location FROM fridges")
        for row in cursor.fetchall():
            self.fridge_list.addItem(f"[# {row[0]}] {row[1]} ({row[2]} - {row[3]} ürün) [{row[4]}]")

        self.shelf_list.clear()
        cursor.execute("SELECT id, name, type, max_capacity, location FROM shelves")
        for row in cursor.fetchall():
            self.shelf_list.addItem(f"[# {row[0]}] {row[1]} ({row[2]} - {row[3]} ürün) [{row[4]}]")

        conn.close()

    def fill_fridge_form(self, item):
        try:
            id_ = int(item.text().split("[# ")[1].split("]")[0])
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT name, type, max_capacity, location FROM fridges WHERE id = ?", (id_,))
            result = cursor.fetchone()
            conn.close()
            if result:
                self.fridge_name.setText(result[0])
                self.fridge_type.setCurrentText(result[1])
                self.fridge_capacity.setText(str(result[2]))
                self.fridge_location.setText(result[3])
        except:
            pass

    def update_fridge(self):
        selected = self.fridge_list.currentRow()
        if selected >= 0:
            try:
                text = self.fridge_list.item(selected).text()
                id_ = int(text.split("[# ")[1].split("]")[0])
                name = self.fridge_name.text()
                t = self.fridge_type.currentText()
                cap = int(self.fridge_capacity.text())
                loc = self.fridge_location.text()

                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE fridges SET name=?, type=?, max_capacity=?, location=? WHERE id=?
                """, (name, t, cap, loc, id_))
                conn.commit()
                conn.close()
                self.load_units()
            except Exception as e:
                QMessageBox.warning(self, _("error.title"), _("error.general").format(error=str(e)))

    def add_fridge(self):
        try:
            name = self.fridge_name.text()
            t = self.fridge_type.currentText()
            cap = int(self.fridge_capacity.text())
            loc = self.fridge_location.text()

            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO fridges (name, type, max_capacity, location) VALUES (?, ?, ?, ?)", (name, t, cap, loc))
            conn.commit()
            conn.close()
            self.load_units()
        except:
            QMessageBox.warning(self, _("error.title"), _("storage_manage.invalid_input"))

    def delete_fridge(self):
        selected = self.fridge_list.currentRow()
        if selected >= 0:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM fridges")
            ids = cursor.fetchall()
            conn.execute("DELETE FROM fridges WHERE id = ?", (ids[selected][0],))
            conn.commit()
            conn.close()
            self.load_units()

    def fill_shelf_form(self, item):
        try:
            id_ = int(item.text().split("[# ")[1].split("]")[0])
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT name, type, max_capacity, location FROM shelves WHERE id = ?", (id_,))
            result = cursor.fetchone()
            conn.close()
            if result:
                self.shelf_name.setText(result[0])
                self.shelf_type.setCurrentText(result[1])
                self.shelf_capacity.setText(str(result[2]))
                self.shelf_location.setText(result[3])
        except:
            pass

    def update_shelf(self):
        selected = self.shelf_list.currentRow()
        if selected >= 0:
            try:
                text = self.shelf_list.item(selected).text()
                id_ = int(text.split("[# ")[1].split("]")[0])
                name = self.shelf_name.text()
                t = self.shelf_type.currentText()
                cap = int(self.shelf_capacity.text())
                loc = self.shelf_location.text()

                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE shelves SET name=?, type=?, max_capacity=?, location=? WHERE id=?
                """, (name, t, cap, loc, id_))
                conn.commit()
                conn.close()
                self.load_units()
            except Exception as e:
                QMessageBox.warning(self, _("error.title"), _("error.general").format(error=str(e)))

    def add_shelf(self):
        try:
            name = self.shelf_name.text()
            t = self.shelf_type.currentText()
            cap = int(self.shelf_capacity.text())
            loc = self.shelf_location.text()

            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO shelves (name, type, max_capacity, location) VALUES (?, ?, ?, ?)", (name, t, cap, loc))
            conn.commit()
            conn.close()
            self.load_units()
        except:
            QMessageBox.warning(self, _("error.title"), _("storage_manage.invalid_input"))

    def delete_shelf(self):
        selected = self.shelf_list.currentRow()
        if selected >= 0:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM shelves")
            ids = cursor.fetchall()
            conn.execute("DELETE FROM shelves WHERE id = ?", (ids[selected][0],))
            conn.commit()
            conn.close()
            self.load_units()
