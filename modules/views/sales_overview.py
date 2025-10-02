import sqlite3
import os
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QHeaderView, QComboBox, QDateEdit, QPushButton, QHBoxLayout, QWidget
)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, QDate
from modules.config import DB_PATH
from modules.lang.translator import Translator

t = Translator()

class SalesOverviewWindow(QDialog):
    def __init__(self, user_role, user_id):
        super().__init__()
        self.setWindowTitle(t.tr("sales_overview.title"))
        self.setMinimumSize(850, 600)

        self.user_role = user_role
        self.user_id = user_id
        self.only_self = False

        self.layout = QVBoxLayout()
        filter_layout = QHBoxLayout()

        self.product_filter = QComboBox()
        self.product_filter.addItem(t.tr("common.all_products"))
        self.populate_product_filter()

        self.date_filter = QDateEdit()
        self.date_filter.setCalendarPopup(True)
        self.date_filter.setDate(QDate.currentDate())

        self.refresh_btn = QPushButton(t.tr("sales_overview.refresh"))
        self.refresh_btn.clicked.connect(self.load_sales)

        filter_layout.addWidget(QLabel(t.tr("form.product")))
        filter_layout.addWidget(self.product_filter)
        filter_layout.addWidget(QLabel(t.tr("form.date")))
        filter_layout.addWidget(self.date_filter)
        filter_layout.addWidget(self.refresh_btn)

        if self.user_role == "worker":
            self.self_toggle_btn = QPushButton("🔘 " + t.tr("sales_overview.show_all"))
            self.self_toggle_btn.clicked.connect(self.toggle_self_sales)
            filter_layout.addWidget(self.self_toggle_btn)

        self.layout.addLayout(filter_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            t.tr("form.user"),
            t.tr("form.product_id"),
            t.tr("form.quantity"),
            t.tr("form.date"),
            t.tr("form.image")
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.layout.addWidget(self.table)

        self.total_label = QLabel(t.tr("sales_overview.total_sales").format(count=0))
        self.total_label.setAlignment(Qt.AlignRight)
        self.layout.addWidget(self.total_label)

        self.setLayout(self.layout)
        self.load_sales()

    def populate_product_filter(self):
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT product_id FROM sales")
            product_ids = cursor.fetchall()
            for pid_tuple in product_ids:
                self.product_filter.addItem(str(pid_tuple[0]))
            conn.close()
        except:
            pass

    def toggle_self_sales(self):
        self.only_self = not self.only_self
        text = "✅ " + t.tr("sales_overview.only_self") if self.only_self else "🔘 " + t.tr("sales_overview.show_all")
        self.self_toggle_btn.setText(text)
        self.load_sales()

    def load_sales(self):
        date_str = self.date_filter.date().toString("yyyy-MM-dd")
        selected_product = self.product_filter.currentText()

        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

            base_query = """
                SELECT u.nickname, s.product_id, s.quantity_sold, s.date, p.image_path
                FROM sales s
                JOIN users u ON s.user_id = u.id
                JOIN products p ON s.product_id = p.product_id
                WHERE s.date = ? AND s.quantity_sold > 0
            """
            params = [date_str]

            if self.user_role == "owner":
                base_query += " AND (u.owner_id = ? OR u.id = ?)"
                params += [self.user_id, self.user_id]

            elif self.user_role == "worker":
                if self.only_self:
                    base_query += " AND s.user_id = ?"
                    params.append(self.user_id)

            if selected_product != t.tr("common.all_products"):
                base_query += " AND s.product_id = ?"
                params.append(int(selected_product))

            cursor.execute(base_query, tuple(params))
            rows = cursor.fetchall()

            self.table.setRowCount(len(rows))
            total_sales = 0
            for row_idx, (nickname, pid, qty, date, img_path) in enumerate(rows):
                self.table.setItem(row_idx, 0, QTableWidgetItem(nickname))
                self.table.setItem(row_idx, 1, QTableWidgetItem(str(pid)))
                self.table.setItem(row_idx, 2, QTableWidgetItem(str(qty)))
                self.table.setItem(row_idx, 3, QTableWidgetItem(date))

                image_label = QLabel()
                if img_path and os.path.exists(img_path):
                    pixmap = QPixmap(img_path).scaled(60, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    image_label.setPixmap(pixmap)
                self.table.setCellWidget(row_idx, 4, image_label)
                self.table.setRowHeight(row_idx, 65)

                total_sales += int(qty)

            self.total_label.setText(t.tr("sales_overview.total_sales").format(count=total_sales))
            conn.close()

        except Exception as e:
            self.table.setRowCount(1)
            self.table.setItem(0, 0, QTableWidgetItem(f"{t.tr('error.database')}: {str(e)}"))
