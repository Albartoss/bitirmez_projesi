import sqlite3
import json
import hashlib
from PyQt5.QtWidgets import (
    QDialog, QLabel, QLineEdit, QPushButton, QVBoxLayout,
    QFormLayout, QCheckBox, QMessageBox, QGroupBox
)
from PyQt5.QtCore import Qt
from modules.config import DB_PATH
from modules.lang.translator import translator as _

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

class UserManageWindow(QDialog):
    def __init__(self, owner_id=None):
        super().__init__()
        self.setWindowTitle(_("user_manage.title"))
        self.setFixedSize(400, 350)
        self.owner_id = owner_id

        layout = QVBoxLayout()
        form = QFormLayout()

        self.username_input = QLineEdit()
        self.nickname_input = QLineEdit()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)

        self.permissions = {
            _("user_manage.perm_product"): QCheckBox(_("user_manage.perm_product")),
            _("user_manage.perm_sales"): QCheckBox(_("user_manage.perm_sales")),
            _("user_manage.perm_forecast"): QCheckBox(_("user_manage.perm_forecast")),
            _("user_manage.perm_analysis"): QCheckBox(_("user_manage.perm_analysis")),
            _("user_manage.perm_stock"): QCheckBox(_("user_manage.perm_stock"))
        }

        perm_box = QGroupBox(_("user_manage.perms_group"))
        perm_layout = QVBoxLayout()
        for box in self.permissions.values():
            perm_layout.addWidget(box)
        perm_box.setLayout(perm_layout)

        self.create_btn = QPushButton(_("user_manage.create_button"))
        self.create_btn.clicked.connect(self.create_user)

        form.addRow(_("user_manage.username") + ":", self.username_input)
        form.addRow(_("user_manage.nickname") + ":", self.nickname_input)
        form.addRow(_("user_manage.password") + ":", self.password_input)

        layout.addLayout(form)
        layout.addWidget(perm_box)
        layout.addWidget(self.create_btn)
        self.setLayout(layout)

    def create_user(self):
        username = self.username_input.text().strip()
        nickname = self.nickname_input.text().strip() or username
        password = self.password_input.text().strip()

        if not username or not password:
            QMessageBox.warning(self, _("warning.title"), _("user_manage.fill_all"))
            return

        selected_perms = []
        for key, box in self.permissions.items():
            if box.isChecked():
                if key == _("user_manage.perm_product"):
                    selected_perms.append("product_manage")
                elif key == _("user_manage.perm_sales"):
                    selected_perms.append("sales")
                elif key == _("user_manage.perm_forecast"):
                    selected_perms.append("forecast")
                elif key == _("user_manage.perm_analysis"):
                    selected_perms.append("analysis")
                elif key == _("user_manage.perm_stock"):
                    selected_perms.append("stock")

        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (username, password_hash, role, permissions, nickname, owner_id)
                VALUES (?, ?, 'worker', ?, ?, ?)
            """, (
                username,
                hash_password(password),
                json.dumps(selected_perms),
                nickname,
                self.owner_id
            ))
            conn.commit()
            conn.close()
            QMessageBox.information(self, _("success.title"), _("user_manage.created").format(name=nickname))
            self.close()
        except sqlite3.IntegrityError:
            QMessageBox.critical(self, _("error.title"), _("user_manage.username_exists"))
