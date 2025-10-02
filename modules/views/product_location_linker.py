import sqlite3
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QComboBox, QPushButton, QMessageBox, QFormLayout
)
from modules.config import DB_PATH
from modules.lang.translator import Translator

class ProductLocationLinker(QDialog):
    def __init__(self):
        super().__init__()
        self.t = Translator()
        self.setWindowTitle(self.t.tr("product_link.title"))
        self.setMinimumSize(400, 250)

        layout = QVBoxLayout()
        form = QFormLayout()

        self.product_dropdown = QComboBox()
        self.location_dropdown = QComboBox()

        self.load_products()
        self.load_locations()

        form.addRow(self.t.tr("product_link.product"), self.product_dropdown)
        form.addRow(self.t.tr("product_link.location"), self.location_dropdown)

        self.btn_save = QPushButton(self.t.tr("product_link.save_button"))
        self.btn_save.clicked.connect(self.save_link)

        layout.addLayout(form)
        layout.addWidget(self.btn_save)
        self.setLayout(layout)

    def load_products(self):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT product_id, product_name FROM products")
        self.products = cursor.fetchall()
        for pid, name in self.products:
            self.product_dropdown.addItem(f"{pid} - {name}", pid)
        conn.close()

    def load_locations(self):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, 'shelf' as type FROM shelves UNION ALL SELECT id, name, 'fridge' FROM fridges")
        self.locations = cursor.fetchall()
        for lid, name, typ in self.locations:
            label = f"{self.t.tr('product_link.type.' + typ)} #{lid} - {name}"
            self.location_dropdown.addItem(label, (lid, typ))
        conn.close()

    def save_link(self):
        product_id = self.product_dropdown.currentData()
        location_id, location_type = self.location_dropdown.currentData()

        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS product_locations (
                    product_id INTEGER,
                    location_id INTEGER,
                    location_type TEXT,
                    PRIMARY KEY (product_id)
                )
            """)
            cursor.execute("""
                INSERT OR REPLACE INTO product_locations (product_id, location_id, location_type)
                VALUES (?, ?, ?)
            """, (product_id, location_id, location_type))
            conn.commit()
            conn.close()
            QMessageBox.information(self, self.t.tr("success.title"), self.t.tr("product_link.success"))
        except Exception as e:
            QMessageBox.critical(self, self.t.tr("error.title"), self.t.tr("product_link.error").format(error=str(e)))
