import sys
import os
from modules.config import DB_PATH

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "database", "inventory.db")

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from PyQt5.QtWidgets import QApplication
from modules.views.login_window import LoginRegisterWindow
from modules.gui_main import InventoryApp


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    login_dialog = LoginRegisterWindow()
    if login_dialog.exec_() == LoginRegisterWindow.Accepted:
        role = login_dialog.logged_in_role
        permissions = login_dialog.logged_in_permissions
        nickname = login_dialog.logged_in_nickname
        user_id = login_dialog.logged_in_user_id

        window = InventoryApp(
            user_role=role,
            allowed_modules=permissions,
            nickname=nickname,
            user_id=user_id
        )
        window.show()
        sys.exit(app.exec_())
