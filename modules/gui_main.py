from modules.lang.translator import translator as _
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLabel, QWidget, QVBoxLayout, QMessageBox, QDialog, QAction
)
from modules.config import DB_PATH
from PyQt5.QtGui import QFont, QCursor
from PyQt5.QtCore import Qt
import sys, os, subprocess, re
import sqlite3
from modules.views.forecasting import FilteredForecastWindow
from modules.views.owner_create import OwnerCreateWindow
from modules.logic.forecasting import get_forecast_with_arima
from modules.views.user_preferences import UserPreferencesWindow
from modules.views.product_manage import AddProductWindow, ManageProductWindow
from modules.views.sales_entry import AddSaleWindow
from modules.views.reports import ReportWindow, ProfitReportWindow, ExpiryReportWindow, check_stock_levels, backup_all_data
from modules.views.date_filtered_forecast import DateFilteredForecastWindow
from modules.views.graph_analysis import GraphWindow
from modules.views.storage_unit_manage import StorageUnitManageWindow
from modules.views.stock_alert import StockAlertWindow
from modules.views.user_manage import UserManageWindow
from modules.views.sales_overview import SalesOverviewWindow
from modules.widgets.plotly_to_gui import PlotlyViewer
from modules.views.owner_assistant_window import OwnerAssistantWindow
from modules.views.ai_suggestions_window import AISuggestionsWindow
from modules.logic.ml_assistant import InventoryForecastAssistant
from modules.views.storage_settings_window import ProductStorageSettingsWindow
from modules.views.product_location_linker import ProductLocationLinker

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLabel, QWidget, QVBoxLayout, QMessageBox, QDialog, QAction
)
from modules.lang.translator import translator

class InventoryApp(QMainWindow):
    def __init__(self, user_role="owner", allowed_modules=None, nickname="", user_id=None):
        super().__init__()
        self.user_role = user_role
        self.allowed_modules = allowed_modules if allowed_modules else []
        self.nickname = nickname
        self.user_id = user_id

        self.setWindowTitle(f"Inventory Management Assistant - {self.nickname}")
        self.setGeometry(400, 150, 800, 600)
        self.apply_user_theme()

        menubar = self.menuBar()
        menubar.setStyleSheet("font-size: 12pt;")

        self.user_label = QLabel(f"<a href='#'>{translator.tr('label.logged_in_as').format(name=self.nickname)}</a>")
        self.user_label.setTextFormat(Qt.RichText)
        self.user_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.user_label.setOpenExternalLinks(False)
        self.user_label.linkActivated.connect(self.show_user_preferences)

        user_widget = QWidget()
        user_layout = QVBoxLayout(user_widget)
        user_layout.setContentsMargins(0, 0, 10, 0)
        user_layout.addWidget(self.user_label, alignment=Qt.AlignRight)
        menubar.setCornerWidget(user_widget, Qt.TopRightCorner)

        account_menu = menubar.addMenu(translator("menu.account"))
        account_menu.addAction(translator.translate("menu.change_user"), self.logout_and_restart)

        if self.user_role in ["admin", "owner"] or "product_manage" in self.allowed_modules:
            product_menu = menubar.addMenu(translator.translate("menu.product"))
            product_menu.addAction(translator.translate("menu.add_product"), self.show_add_product)
            product_menu.addAction(translator.translate("menu.add_sale"), self.show_add_sale)
            product_menu.addAction(translator.translate("menu.stock_alert"), self.show_stock_alert)

        if self.user_role == "owner":
            user_menu = menubar.addMenu(translator.translate("menu.user"))
            user_menu.addAction(translator.translate("menu.create_worker"), self.show_user_manage)
            user_menu.addAction(translator.translate("menu.manage_workers"), self.show_worker_manage)

        if self.user_role == "admin":
            user_menu = menubar.addMenu(translator.translate("menu.user"))
            user_menu.addAction(translator.translate("menu.create_worker"), self.show_user_manage)
            user_menu.addAction(translator.translate("menu.manage_users"), self.show_user_admin_manage)
            user_menu.addAction(translator.translate("menu.create_owner"), self.show_owner_create)

        if self.user_role in ["admin", "owner"]:
            report_menu = menubar.addMenu(translator.translate("menu.sales_tracking"))
            report_menu.addAction(translator.translate("menu.sales_summary"), self.show_sales_overview)
            report_menu.addAction(translator.translate("menu.manage_products"), self.show_manage_product)

        if self.user_role in ["admin", "owner"]:
            tools_menu = menubar.addMenu(translator.translate("menu.location_mapping"))
            tools_menu.addAction(translator.translate("menu.product_location_link"), self.show_product_location_linker)

        if self.user_role in ["admin", "owner"] or "sales" in self.allowed_modules:
            sale_menu = menubar.addMenu(translator.translate("menu.sales"))
            sale_menu.addAction(translator.translate("menu.sales_report"), self.show_report)
            sale_menu.addAction(translator.translate("menu.sales_summary"), self.show_sales_overview)

        if self.user_role in ["admin", "owner"] or "forecast" in self.allowed_modules:
            forecast_menu = menubar.addMenu(translator.translate("menu.forecast"))
            forecast_menu.addAction(translator.translate("menu.product_forecast"), self.show_filtered_forecast)
            forecast_menu.addAction(translator.translate("menu.date_forecast"), self.show_date_forecast)

        if self.user_role in ["admin", "owner"] or "analysis" in self.allowed_modules:
            analysis_menu = menubar.addMenu(translator.translate("menu.analysis"))
            analysis_menu.addAction(translator.translate("menu.graph_analysis"), self.show_graph)
            analysis_menu.addAction(translator.translate("menu.profit_report"), self.show_profit_report)
            analysis_menu.addAction(translator.translate("menu.expiry_report"), self.show_expiry_report)

        if self.user_role in ["admin", "owner"] or "stock" in self.allowed_modules:
            other_menu = menubar.addMenu(translator.translate("menu.stock_backup"))
            other_menu.addAction(translator.translate("menu.storage_settings"), self.show_storage_settings)
            other_menu.addAction(translator.translate("menu.manage_storage"), self.show_storage_manager)
            other_menu.addAction(translator.translate("menu.stock_alert"), self.show_stock_alert)
            other_menu.addAction(translator.translate("menu.backup_data"), backup_all_data)

        if self.user_role in ["admin", "owner"]:
            ai_menu = menubar.addMenu(translator.translate("menu.ai_support"))
            ai_menu.addAction(translator.translate("menu.ai_helper"), self.show_ai_assistant)
            ai_menu.addAction(translator.translate("menu.update_trends"), self.update_trends_from_api)
            ai_menu.addAction(translator.translate("menu.show_suggestions"), self.show_ai_suggestions)
            ai_menu.addAction(translator.translate("menu.reorder_advice"), self.show_reorder_advice)

        welcome_label = QLabel(translator.translate("app.welcome_message"))
        welcome_label.setAlignment(Qt.AlignCenter)
        welcome_label.setFont(QFont("Arial", 14))

        container = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(welcome_label)
        container.setLayout(layout)
        self.setCentralWidget(container)


    def apply_user_theme(self):
        try:
            BASE_DIR = os.path.dirname(os.path.abspath(__file__))
            DB_PATH = os.path.join(BASE_DIR, "../database/inventory.db")
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT theme FROM users WHERE id = ?", (self.user_id,))
            result = cursor.fetchone()
            conn.close()
            theme = result[0] if result and result[0] else "Açık"
            if theme == "Koyu":
                self.setStyleSheet("""
                    QMainWindow { background-color: #2c2c2c; color: white; }
                    QLabel, QMenuBar, QMenu, QPushButton, QTableWidget, QComboBox, QLineEdit {
                        background-color: #3a3a3a; color: white;
                    }
                    QMenuBar::item:selected, QMenu::item:selected {
                        background-color: #555;
                    }
                """)
            elif theme == "Yeşil":
                self.setStyleSheet("""
                    QMainWindow { background-color: #e6ffee; }
                    QLabel, QMenuBar, QMenu, QPushButton, QTableWidget, QComboBox, QLineEdit {
                        background-color: #ccffcc; color: #003300;
                    }
                    QMenuBar::item:selected, QMenu::item:selected {
                        background-color: #99ff99;
                    }
                """)
            elif theme == "Açık Mavi":
                self.setStyleSheet("""
                    QMainWindow { background-color: #e6f2ff; }
                    QLabel, QMenuBar, QMenu, QPushButton, QTableWidget, QComboBox, QLineEdit {
                        background-color: #cce6ff; color: #003366;
                    }
                    QMenuBar::item:selected, QMenu::item:selected {
                        background-color: #99ccff;
                    }
                """)
            else:
                self.setStyleSheet("")
        except Exception as e:
            print(f"Tema uygulanamadı: {e}")
            self.setStyleSheet("")

    def show_ai_assistant(self):
        self.ai_window = OwnerAssistantWindow()
        self.ai_window.exec_()

    def show_storage_settings(self):
        self.storage_window = ProductStorageSettingsWindow()
        self.storage_window.exec_()

    def show_ai_suggestions(self):
        self.suggestion_window = AISuggestionsWindow()
        self.suggestion_window.exec_()

    def update_trends_from_api(self):
        try:
            assistant = InventoryForecastAssistant(enable_trends=False)
            assistant.update_trend_scores()
            QMessageBox.information(self, "Başarılı", "Trend verileri güncellendi.")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Trend güncelleme başarısız: {e}")

    def show_storage_manager(self):
        self.storage_window = StorageUnitManageWindow()
        self.storage_window.exec_()

    def show_user_preferences(self):
        self.pref_window = UserPreferencesWindow(user_id=self.user_id)
        self.pref_window.exec_()
        self.apply_user_theme()

    def show_add_product(self): self.add_window = AddProductWindow(); self.add_window.exec_()
    def show_manage_product(self): self.manage_window = ManageProductWindow(); self.manage_window.exec_()
    def show_owner_create(self): self.owner_create_window = OwnerCreateWindow(); self.owner_create_window.exec_()
    def show_worker_manage(self): from modules.views.worker_manage import WorkerManageWindow; self.worker_manage_window = WorkerManageWindow(owner_id=self.user_id); self.worker_manage_window.exec_()
    def show_add_sale(self): self.sale_window = AddSaleWindow(user_id=self.user_id); self.sale_window.exec_()
    def show_filtered_forecast(self):
        self.filter_forecast_window = FilteredForecastWindow()
        self.filter_forecast_window.exec_()
    def show_report(self): self.report_window = ReportWindow(); self.report_window.exec_()
    def show_forecast(self):
        try:
            base_path = os.path.dirname(os.path.abspath(__file__))
            module_path = os.path.join(base_path, "ml_module.py")
            result = subprocess.run([sys.executable, module_path], capture_output=True, text=True, cwd=base_path)
            match = re.search(r"<<HTML_PATH>>(.*?)<<END>>", result.stdout)
            if match:
                html_path = match.group(1).strip()
                viewer = PlotlyViewer((html_path, "Tahmin Grafiği"))
                viewer.exec_()
            else:
                QMessageBox.warning(self, "Uyarı", "Tahmin grafiği oluşturulamadı.")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Grafik gösterimi başarısız:\n{str(e)}")

    def show_graph(self): self.graph_window = GraphWindow(); self.graph_window.exec_()
    def show_date_forecast(self): self.date_forecast_window = DateFilteredForecastWindow(); self.date_forecast_window.exec_()
    def show_profit_report(self): self.profit_window = ProfitReportWindow(); self.profit_window.exec_()
    def show_expiry_report(self): self.expiry_window = ExpiryReportWindow(); self.expiry_window.exec_()
    def show_user_manage(self): self.user_manage_window = UserManageWindow(owner_id=self.user_id); self.user_manage_window.exec_()
    def show_user_admin_manage(self): from modules.views.user_admin_manage import UserAdminManageWindow; self.admin_user_manage_window = UserAdminManageWindow(); self.admin_user_manage_window.exec_()
    def show_sales_overview(self): self.sales_window = SalesOverviewWindow(user_role=self.user_role, user_id=self.user_id); self.sales_window.exec_()
    def show_stock_alert(self): self.stock_alert_window = StockAlertWindow(); self.stock_alert_window.exec_(); check_stock_levels()
    def logout_and_restart(self):
        from modules.views.login_window import LoginRegisterWindow
        self.close()
        self.login_screen = LoginRegisterWindow()
        if self.login_screen.exec_() == QDialog.Accepted:
            role = self.login_screen.logged_in_role
            permissions = self.login_screen.logged_in_permissions
            nickname = self.login_screen.logged_in_nickname
            user_id = self.login_screen.logged_in_user_id
            self.new_app = InventoryApp(user_role=role, allowed_modules=permissions, nickname=nickname, user_id=user_id)
            self.new_app.show()
    def show_product_location_linker(self):
        self.linker_window = ProductLocationLinker()
        self.linker_window.exec_()
    def show_reorder_advice(self):
        from modules.logic.reorder_advisor import ReorderAdvisor
        advisor = ReorderAdvisor()
        suggestions = advisor.compute_reorder_advice(min_days=7)
        if not suggestions:
            QMessageBox.information(self, "Bilgi", "Tüm ürünlerde yeterli stok mevcut.")
            return

        text = ""
        for item in suggestions:
            text += f"📦 {item['product_name']} → {item['suggested_order']} adet önerilir.\n"

        QMessageBox.information(self, "Stok Yenileme Önerisi", text)

