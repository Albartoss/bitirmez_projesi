import sqlite3
import hashlib
import json
from PyQt5.QtWidgets import (
    QDialog, QLabel, QLineEdit, QPushButton, QVBoxLayout,
    QFormLayout, QMessageBox
)

from modules.config import DB_PATH
from modules.lang.translator import Translator

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

class OwnerCreateWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.t = Translator()
        self.setWindowTitle(self.t.tr("owner_create.title"))
        self.setFixedSize(350, 200)

        layout = QVBoxLayout()
        form = QFormLayout()

        self.username_input = QLineEdit()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)

        form.addRow(self.t.tr("owner_create.username"), self.username_input)
        form.addRow(self.t.tr("owner_create.password"), self.password_input)

        self.create_btn = QPushButton(self.t.tr("owner_create.button"))
        self.create_btn.clicked.connect(self.create_owner)

        layout.addLayout(form)
        layout.addWidget(self.create_btn)
        self.setLayout(layout)

    def create_owner(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        if not username or not password:
            QMessageBox.warning(self, self.t.tr("warning.title"), self.t.tr("owner_create.fill_required"))
            return

        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (username, password_hash, role, permissions)
                VALUES (?, ?, 'owner', ?)
            """, (
                username,
                hash_password(password),
                json.dumps({})
            ))
            conn.commit()
            conn.close()
            QMessageBox.information(self, self.t.tr("success.title"), self.t.tr("owner_create.created").format(username=username))
            self.close()
        except sqlite3.IntegrityError:
            QMessageBox.critical(self, self.t.tr("error.title"), self.t.tr("owner_create.username_exists"))
