import sqlite3
import hashlib
from PyQt5.QtWidgets import (
    QDialog, QLabel, QPushButton, QVBoxLayout, QFormLayout,
    QLineEdit, QGroupBox, QScrollArea, QWidget, QMessageBox, QComboBox
)
from modules.config import DB_PATH
from modules.lang.translator import translator as _

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

class UserAdminManageWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(_("user_admin.title"))
        self.setMinimumSize(650, 550)

        layout = QVBoxLayout()
        scroll = QScrollArea()
        container = QWidget()
        self.content_layout = QVBoxLayout()

        self.load_users()

        container.setLayout(self.content_layout)
        scroll.setWidgetResizable(True)
        scroll.setWidget(container)

        layout.addWidget(scroll)
        self.setLayout(layout)

    def load_users(self):
        self.content_layout.setSpacing(15)
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT id, username, role, nickname, owner_id FROM users ORDER BY role DESC")
            users = cursor.fetchall()

            cursor.execute("SELECT id, username FROM users WHERE role = 'owner'")
            self.owners = cursor.fetchall()
            conn.close()
        except Exception as e:
            self.content_layout.addWidget(QLabel(_("error.general").format(error=str(e))))
            return

        for user_id, username, role, nickname, owner_id in users:
            box = QGroupBox(f"{username} ({role})")
            box_layout = QFormLayout()

            pw_input = QLineEdit()
            pw_input.setPlaceholderText(_("user_admin.new_password"))
            pw_input.setEchoMode(QLineEdit.Password)

            nick_input = QLineEdit()
            nick_input.setText(nickname or "")
            nick_input.setPlaceholderText(_("user_admin.nickname"))

            owner_combo = QComboBox()
            owner_combo.addItem(_("user_admin.no_owner"), None)
            for oid, oname in self.owners:
                owner_combo.addItem(oname, oid)
                if oid == owner_id:
                    owner_combo.setCurrentIndex(owner_combo.count() - 1)

            btn_update = QPushButton(_("user_admin.update"))
            btn_update.clicked.connect(
                lambda _, uid=user_id, pw=pw_input, ni=nick_input, oc=owner_combo:
                self.update_user(uid, pw, ni, oc)
            )

            box_layout.addRow(_("user_admin.password") + ":", pw_input)
            box_layout.addRow(_("user_admin.nickname_label") + ":", nick_input)
            if role == "worker":
                box_layout.addRow(_("user_admin.linked_owner") + ":", owner_combo)
            box_layout.addRow(btn_update)

            if username.lower() != "admin1" and role != "admin":
                btn_delete = QPushButton(_("user_admin.delete"))
                btn_delete.setStyleSheet("color: red;")
                btn_delete.clicked.connect(lambda _, uid=user_id, name=username: self.delete_user(uid, name))
                box_layout.addRow(btn_delete)

            box.setLayout(box_layout)
            self.content_layout.addWidget(box)

    def update_user(self, user_id, pw_field, nick_field, owner_combo):
        new_pw = pw_field.text().strip()
        new_nick = nick_field.text().strip()
        selected_owner_id = owner_combo.currentData()

        if not new_pw and not new_nick and selected_owner_id is None:
            QMessageBox.warning(self, _("warning.title"), _("user_admin.fill_at_least_one"))
            return

        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

            if new_pw:
                hashed = hash_password(new_pw)
                cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hashed, user_id))

            if new_nick:
                cursor.execute("UPDATE users SET nickname = ? WHERE id = ?", (new_nick, user_id))

            if owner_combo is not None:
                cursor.execute("UPDATE users SET owner_id = ? WHERE id = ?", (selected_owner_id, user_id))

            conn.commit()
            conn.close()
            QMessageBox.information(self, _("success.title"), _("user_admin.updated"))
            self.refresh()
        except Exception as e:
            QMessageBox.critical(self, _("error.title"), _("user_admin.update_error").format(error=str(e)))

    def delete_user(self, user_id, username):
        confirm = QMessageBox.question(
            self, _("user_admin.confirm_delete_title"),
            _("user_admin.confirm_delete_text").format(username=username),
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            try:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
                conn.commit()
                conn.close()
                QMessageBox.information(self, _("success.title"), _("user_admin.deleted").format(username=username))
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, _("error.title"), _("user_admin.delete_error").format(error=str(e)))

    def refresh(self):
        for i in reversed(range(self.content_layout.count())):
            widget = self.content_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        self.load_users()
