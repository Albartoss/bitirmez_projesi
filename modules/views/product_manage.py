import sqlite3
import pandas as pd
import os
import shutil
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QComboBox, QPushButton, QLabel,
    QMessageBox, QDateEdit, QCompleter, QFileDialog
)
images_dir = os.path.abspath("images")
os.makedirs(images_dir, exist_ok=True)
from modules.config import DB_PATH
from PyQt5.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QComboBox, QPushButton, QLabel, QMessageBox, QDateEdit, QCompleter
)
from PyQt5.QtCore import QDate
from modules.config import DB_PATH
from modules.lang.translator import Translator

class AddProductWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.t = Translator()
        self.setWindowTitle(self.t.tr("product.add_title"))
        self.setFixedSize(360, 520)
        self.layout = QFormLayout()

        self.product_lookup = {}
        self.product_lookup_by_id = {}

        self.id_input = QLineEdit()
        self.name_input = QLineEdit()
        self.brand_input = QLineEdit()
        self.category_input = QLineEdit()
        self.cost_input = QLineEdit()
        self.sell_input = QLineEdit()
        self.stock_input = QLineEdit()
        self.stock_mode = QComboBox()
        self.stock_mode.addItems([self.t.tr("product.initial_entry"), self.t.tr("product.extra_stock")])
        self.image_label = QLabel(self.t.tr("product.no_image"))

        self.expiry_input = QDateEdit(QDate.currentDate())
        self.expiry_input.setCalendarPopup(True)
        self.select_image_btn = QPushButton(self.t.tr("product.select_image"))
        self.discount_input = QLineEdit()
        self.discount_until_input = QDateEdit(QDate.currentDate())
        self.discount_until_input.setCalendarPopup(True)
        self.select_image_btn.clicked.connect(self.choose_image)

        self.layout.addRow(self.t.tr("product.id"), self.id_input)
        self.layout.addRow(self.t.tr("product.name"), self.name_input)
        self.layout.addRow(self.t.tr("product.brand"), self.brand_input)
        self.layout.addRow(self.t.tr("product.category"), self.category_input)
        self.layout.addRow(self.t.tr("product.cost"), self.cost_input)
        self.layout.addRow(self.t.tr("product.sell"), self.sell_input)
        self.layout.addRow(self.t.tr("product.stock_qty"), self.stock_input)
        self.layout.addRow(self.t.tr("product.stock_mode"), self.stock_mode)
        self.layout.addRow(self.t.tr("product.expiry"), self.expiry_input)
        self.layout.addRow(self.t.tr("product.discount"), self.discount_input)
        self.layout.addRow(self.t.tr("product.discount_until"), self.discount_until_input)
        self.layout.addRow(self.t.tr("product.image"), self.image_label)
        self.layout.addRow(self.select_image_btn)
        self.selected_image_path = None

        self.submit_btn = QPushButton(self.t.tr("product.save"))
        self.submit_btn.clicked.connect(self.handle_product)
        self.layout.addRow(self.submit_btn)
        self.setLayout(self.layout)

        self.name_input.textChanged.connect(self.autofill_fields)
        self.id_input.textChanged.connect(self.autofill_by_id)

        try:
            conn = sqlite3.connect(DB_PATH)
            df = pd.read_sql_query("SELECT * FROM products", conn)
            conn.close()
            df_unique = df.drop_duplicates(subset="product_name", keep="first")
            self.product_lookup = df_unique.set_index("product_name").to_dict("index")
            self.product_lookup_by_id = df_unique.set_index("product_id").to_dict("index")

            completer = QCompleter(list(self.product_lookup.keys()))
            completer.setCaseSensitivity(False)
            self.name_input.setCompleter(completer)
        except Exception as e:
            QMessageBox.critical(self, self.t.tr("error.title"), self.t.tr("product.load_error").format(error=str(e)))

    def autofill_fields(self, text):
        match = next((p for name, p in self.product_lookup.items() if name.lower() == text.lower()), None)
        if match:
            self.id_input.setText(str(match["product_id"]))
            self.brand_input.setText(match["brand"])
            self.category_input.setText(match["category"])
            self.cost_input.setText(str(match["cost_price"]))
            self.sell_input.setText(str(match["selling_price"]))

    def autofill_by_id(self, text):
        try:
            pid = int(text)
            if pid in self.product_lookup_by_id:
                product = self.product_lookup_by_id[pid]
                self.name_input.setText(product["product_name"])
                self.brand_input.setText(product["brand"])
                self.category_input.setText(product["category"])
                self.cost_input.setText(str(product["cost_price"]))
                self.sell_input.setText(str(product["selling_price"]))
        except:
            pass

    def choose_image(self):
        file_path, _ = QFileDialog.getOpenFileName(self, self.t.tr("product.select_image"), "", "Resim Dosyaları (*.png *.jpg *.jpeg *.bmp)")
        if file_path:
            filename = os.path.basename(file_path)
            target_path = os.path.join(images_dir, filename)
            shutil.copy(file_path, target_path)
            self.selected_image_path = target_path
            self.image_label.setText(os.path.basename(file_path))

    def handle_product(self):
        try:
            name = self.name_input.text()
            if not self.stock_input.text().strip():
                QMessageBox.warning(self, self.t.tr("error.title"), self.t.tr("product.empty_stock"))
                return

            stock_value = int(self.stock_input.text())
            mode = self.stock_mode.currentText()
            mode_tr = self.t.tr("product.extra_stock")
            today = QDate.currentDate().toString("yyyy-MM-dd")
            expiry_date = self.expiry_input.date().toString("yyyy-MM-dd")

            discount_raw = self.discount_input.text().replace(",", ".").strip()
            discount_price = float(discount_raw) if discount_raw else None
            discount_until = self.discount_until_input.date().toString("yyyy-MM-dd") if discount_price is not None else None

            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM products WHERE product_name = ? OR product_id = ?", (name, self.id_input.text()))
            existing = cursor.fetchone()

            if existing and mode == mode_tr:
                product_id = existing[0]
                cursor.execute("""
                    INSERT INTO stock_transactions (product_id, date, quantity, note, expiry_date)
                    VALUES (?, ?, ?, ?, ?)
                """, (product_id, today, stock_value, "Ek Stok Girişi", expiry_date))
                QMessageBox.information(self, self.t.tr("success.title"), self.t.tr("product.stock_added").format(name=name))

            elif existing:
                QMessageBox.warning(self, self.t.tr("error.title"), self.t.tr("product.already_exists"))
                conn.close()
                return

            elif not existing and mode == mode_tr:
                QMessageBox.warning(self, self.t.tr("error.title"), self.t.tr("product.not_found"))
                conn.close()
                return

            else:
                cursor.execute("""
                    INSERT INTO products (
                        product_id, product_name, brand, category,
                        cost_price, selling_price, expiry_date,
                        discount_price, discount_until, image_path
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    int(self.id_input.text()), name, self.brand_input.text(), self.category_input.text(),
                    float(self.cost_input.text().replace(",", ".")),
                    float(self.sell_input.text().replace(",", ".")),
                    expiry_date, discount_price, discount_until,
                    self.selected_image_path if self.selected_image_path else None
                ))

                cursor.execute("""
                    INSERT INTO stock_transactions (product_id, date, quantity, note, expiry_date)
                    VALUES (?, ?, ?, ?, ?)
                """, (int(self.id_input.text()), today, stock_value, "İlk Stok Girişi", expiry_date))

                QMessageBox.information(self, self.t.tr("success.title"), self.t.tr("product.saved").format(name=name))

            conn.commit()
            conn.close()
            self.close()
        except Exception as e:
            QMessageBox.critical(self, self.t.tr("error.title"), self.t.tr("product.failed").format(error=str(e)))


class ManageProductWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.t = Translator()
        self.setWindowTitle(self.t.tr("product.manage_title"))
        self.setFixedSize(400, 540)
        self.layout = QFormLayout()

        self.product_dropdown = QComboBox()
        self.id_input = QLineEdit()
        self.brand_input = QLineEdit()
        self.category_input = QLineEdit()
        self.cost_input = QLineEdit()
        self.sell_input = QLineEdit()
        self.discount_input = QLineEdit()
        self.discount_until_input = QDateEdit(QDate.currentDate())
        self.discount_until_input.setCalendarPopup(True)

        self.image_label = QLabel(self.t.tr("product.no_image"))
        self.image_label.setFixedSize(160, 160)
        self.image_label.setStyleSheet("border: 1px solid gray")
        self.select_image_btn = QPushButton(self.t.tr("product.select_image"))
        self.select_image_btn.clicked.connect(self.select_new_image)
        self.image_path = None

        self.layout.addRow(self.t.tr("product.select"), self.product_dropdown)
        self.layout.addRow("ID:", self.id_input)
        self.layout.addRow(self.t.tr("product.brand"), self.brand_input)
        self.layout.addRow(self.t.tr("product.category"), self.category_input)
        self.layout.addRow(self.t.tr("product.cost"), self.cost_input)
        self.layout.addRow(self.t.tr("product.sell"), self.sell_input)
        self.layout.addRow(self.t.tr("product.discount"), self.discount_input)
        self.layout.addRow(self.t.tr("product.discount_until"), self.discount_until_input)
        self.layout.addRow(self.t.tr("product.image_current"), self.image_label)
        self.layout.addRow(self.select_image_btn)

        self.update_btn = QPushButton(self.t.tr("product.update"))
        self.delete_btn = QPushButton(self.t.tr("product.delete"))
        self.layout.addRow(self.update_btn, self.delete_btn)
        self.setLayout(self.layout)

        try:
            conn = sqlite3.connect(DB_PATH)
            df = pd.read_sql_query("SELECT * FROM products", conn)
            conn.close()

            self.products = df.set_index("product_name").to_dict("index")
            self.product_dropdown.addItems(self.products.keys())
            self.product_dropdown.currentTextChanged.connect(self.fill_fields)

            self.update_btn.clicked.connect(self.update_product)
            self.delete_btn.clicked.connect(self.delete_product)

            self.fill_fields(self.product_dropdown.currentText())
        except Exception as e:
            QMessageBox.critical(self, self.t.tr("error.title"), self.t.tr("product.load_error").format(error=str(e)))

    def fill_fields(self, name):
        if name in self.products:
            p = self.products[name]
            self.id_input.setText(str(p["product_id"]))
            self.brand_input.setText(p["brand"])
            self.category_input.setText(p["category"])
            self.cost_input.setText(str(p["cost_price"]))
            self.sell_input.setText(str(p["selling_price"]))
            self.image_path = p.get("image_path")

            self.discount_input.setText(str(p.get("discount_price") or ""))
            try:
                if p.get("discount_until"):
                    self.discount_until_input.setDate(QDate.fromString(p["discount_until"], "yyyy-MM-dd"))
                else:
                    self.discount_until_input.setDate(QDate.currentDate())
            except:
                self.discount_until_input.setDate(QDate.currentDate())

            if self.image_path and os.path.exists(self.image_path):
                pixmap = QPixmap(self.image_path)
                self.image_label.setPixmap(pixmap.scaled(self.image_label.size()))
            else:
                self.image_label.setText(self.t.tr("product.no_image"))
                self.image_label.setPixmap(QPixmap())

    def select_new_image(self):
        file_path, _ = QFileDialog.getOpenFileName(self, self.t.tr("product.select_image"), "", "Resim Dosyaları (*.png *.jpg *.jpeg *.bmp)")
        if file_path:
            filename = os.path.basename(file_path)
            target_path = os.path.join(images_dir, filename)
            shutil.copy(file_path, target_path)
            self.image_path = target_path
            pixmap = QPixmap(target_path)
            self.image_label.setPixmap(pixmap.scaled(self.image_label.size()))

    def update_product(self):
        try:
            name = self.product_dropdown.currentText()

            discount_raw = self.discount_input.text().replace(",", ".").strip()
            discount_price = float(discount_raw) if discount_raw else None
            discount_until = self.discount_until_input.date().toString("yyyy-MM-dd") if discount_price is not None else None

            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE products SET 
                    brand = ?, category = ?, cost_price = ?, selling_price = ?,
                    discount_price = ?, discount_until = ?, image_path = ?
                WHERE product_name = ?
            """, (
                self.brand_input.text(),
                self.category_input.text(),
                float(self.cost_input.text().replace(",", ".")),
                float(self.sell_input.text().replace(",", ".")),
                discount_price, discount_until,
                self.image_path,
                name
            ))

            conn.commit()
            conn.close()
            QMessageBox.information(self, self.t.tr("success.title"), self.t.tr("product.updated"))
            self.close()
        except Exception as e:
            QMessageBox.critical(self, self.t.tr("error.title"), self.t.tr("product.failed").format(error=str(e)))

    def delete_product(self):
        name = self.product_dropdown.currentText()
        confirm = QMessageBox.question(
            self,
            self.t.tr("confirm.title"),
            self.t.tr("product.delete_confirm").format(name=name),
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            try:
                pid = self.products[name]["product_id"]
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute("DELETE FROM stock_transactions WHERE product_id = ?", (pid,))
                cursor.execute("DELETE FROM sales WHERE product_id = ?", (pid,))
                cursor.execute("DELETE FROM products WHERE product_id = ?", (pid,))
                conn.commit()
                conn.close()
                QMessageBox.information(self, self.t.tr("success.title"), self.t.tr("product.deleted").format(name=name))
                self.close()
            except Exception as e:
                QMessageBox.critical(self, self.t.tr("error.title"), self.t.tr("product.failed").format(error=str(e)))