import sqlite3
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QComboBox, QCheckBox, QMessageBox
)
from PyQt5.QtCore import Qt, QDate
from modules.config import DB_PATH
from modules.lang.translator import translator as _

class UserPreferencesWindow(QDialog):
    def __init__(self, user_id):
        super().__init__()
        self.setWindowTitle(_("user_pref.title"))
        self.setFixedSize(400, 300)
        self.user_id = user_id

        layout = QVBoxLayout()

        self.theme_label = QLabel(_("user_pref.theme_label"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems([
            _("user_pref.theme.default"),
            _("user_pref.theme.dark"),
            _("user_pref.theme.lightblue"),
            _("user_pref.theme.green")
        ])

        self.only_self_checkbox = QCheckBox(_("user_pref.only_self"))

        self.daily_label = QLabel(_("user_pref.daily_sales") + "...")
        self.monthly_label = QLabel(_("user_pref.monthly_sales") + "...")

        self.save_btn = QPushButton(_("user_pref.save"))
        self.save_btn.clicked.connect(self.save_preferences)

        layout.addWidget(self.theme_label)
        layout.addWidget(self.theme_combo)
        layout.addWidget(self.only_self_checkbox)
        layout.addWidget(self.daily_label)
        layout.addWidget(self.monthly_label)
        layout.addWidget(self.save_btn)
        layout.setAlignment(Qt.AlignTop)
        self.setLayout(layout)

        self.load_preferences()
        self.load_sales_summary()

    def load_preferences(self):
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT theme, only_self_sales FROM users WHERE id = ?", (self.user_id,))
            row = cursor.fetchone()
            conn.close()

            if row:
                theme, only_self = row
                index = self.theme_combo.findText(_(f"user_pref.theme.{theme.lower()}")) if theme else 0
                self.theme_combo.setCurrentIndex(index if index >= 0 else 0)
                self.only_self_checkbox.setChecked(bool(only_self))
        except Exception as e:
            QMessageBox.warning(self, _("error.title"), _("user_pref.load_error").format(error=str(e)))

    def load_sales_summary(self):
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

            today = QDate.currentDate().toString("yyyy-MM-dd")
            month_start = QDate.currentDate().addDays(-QDate.currentDate().day() + 1).toString("yyyy-MM-dd")

            cursor.execute("SELECT SUM(quantity_sold) FROM sales WHERE user_id = ? AND date = ?", (self.user_id, today))
            daily = cursor.fetchone()[0] or 0

            cursor.execute("SELECT SUM(quantity_sold) FROM sales WHERE user_id = ? AND date >= ?", (self.user_id, month_start))
            monthly = cursor.fetchone()[0] or 0

            self.daily_label.setText(f"{_('user_pref.daily_sales')}: {daily}")
            self.monthly_label.setText(f"{_('user_pref.monthly_sales')}: {monthly}")
            conn.close()
        except Exception as e:
            self.daily_label.setText(f"{_('user_pref.daily_sales')}: {_('error.title')}")
            self.monthly_label.setText(f"{_('user_pref.monthly_sales')}: {_('error.title')}")
            QMessageBox.critical(self, _("error.title"), _("user_pref.sales_load_error").format(error=str(e)))

    def save_preferences(self):
        theme = self.theme_combo.currentText()
        theme_raw = {
            _("user_pref.theme.default"): "Varsayılan",
            _("user_pref.theme.dark"): "Koyu",
            _("user_pref.theme.lightblue"): "Açık Mavi",
            _("user_pref.theme.green"): "Yeşil"
        }.get(theme, "Varsayılan")

        only_self = int(self.only_self_checkbox.isChecked())

        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users SET theme = ?, only_self_sales = ? WHERE id = ?
            """, (theme_raw, only_self, self.user_id))
            conn.commit()
            conn.close()

            QMessageBox.information(self, _("success.title"), _("user_pref.saved"))
            self.close()
        except Exception as e:
            QMessageBox.critical(self, _("error.title"), _("user_pref.save_error").format(error=str(e)))
