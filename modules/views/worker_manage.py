import sqlite3
import hashlib
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QHBoxLayout, QMessageBox, QLineEdit, QHeaderView, QWidget
)
from PyQt5.QtCore import Qt
from modules.config import DB_PATH
from modules.lang.translator import translator as _

class WorkerManageWindow(QDialog):
    def __init__(self, owner_id):
        super().__init__()
        self.setWindowTitle(_("worker_manage.title"))
        self.setMinimumSize(720, 440)
        self.owner_id = owner_id

        layout = QVBoxLayout()
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            _("worker_manage.username"),
            _("worker_manage.current_nick"),
            _("worker_manage.new_password"),
            _("worker_manage.new_nick"),
            _("worker_manage.action")
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        layout.addWidget(self.table)
        self.setLayout(layout)
        self.load_workers()

    def load_workers(self):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, username, nickname FROM users
            WHERE role = 'worker' AND owner_id = ?
        """, (self.owner_id,))
        workers = cursor.fetchall()
        conn.close()

        self.table.setRowCount(len(workers))

        for row, (user_id, username, nickname) in enumerate(workers):
            self.table.setItem(row, 0, QTableWidgetItem(username))
            self.table.setItem(row, 1, QTableWidgetItem(nickname or "—"))

            pw_input = QLineEdit()
            pw_input.setPlaceholderText(_("worker_manage.new_password"))

            nick_input = QLineEdit()
            nick_input.setPlaceholderText(_("worker_manage.new_nick"))

            update_btn = QPushButton(_("worker_manage.update"))
            update_btn.clicked.connect(
                lambda _, uid=user_id, pw=pw_input, nn=nick_input: self.update_worker(uid, pw, nn)
            )

            delete_btn = QPushButton(_("worker_manage.delete"))
            delete_btn.clicked.connect(
                lambda _, uid=user_id, uname=username: self.delete_worker(uid, uname)
            )

            action_layout = QHBoxLayout()
            action_layout.addWidget(update_btn)
            action_layout.addWidget(delete_btn)
            wrapper = QWidget()
            wrapper.setLayout(action_layout)

            self.table.setCellWidget(row, 2, pw_input)
            self.table.setCellWidget(row, 3, nick_input)
            self.table.setCellWidget(row, 4, wrapper)

    def update_worker(self, user_id, pw_field, nick_field):
        new_pw = pw_field.text().strip()
        new_nick = nick_field.text().strip()

        if not new_pw and not new_nick:
            QMessageBox.warning(self, _("warning.title"), _("worker_manage.fill_at_least_one"))
            return

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        if new_pw:
            hashed = hashlib.sha256(new_pw.encode()).hexdigest()
            cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hashed, user_id))

        if new_nick:
            cursor.execute("UPDATE users SET nickname = ? WHERE id = ?", (new_nick, user_id))

        conn.commit()
        conn.close()
        QMessageBox.information(self, _("success.title"), _("worker_manage.updated"))
        self.load_workers()

    def delete_worker(self, user_id, username):
        confirm = QMessageBox.question(
            self,
            _("worker_manage.delete_title"),
            _("worker_manage.delete_confirm").format(username=username),
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()
            conn.close()
            QMessageBox.information(self, _("success.title"), _("worker_manage.deleted").format(username=username))
            self.load_workers()
