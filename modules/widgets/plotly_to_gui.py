import os
import sys
from PyQt5.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QPushButton, QMessageBox,
    QFileDialog, QHBoxLayout, QTabWidget, QWidget
)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl
from modules.lang.translator import translator as translate

class PlotlyViewer(QDialog):
    def __init__(self, *html_paths_titles):
        super().__init__()
        self.setWindowTitle(translate("plotly.title"))
        self.setMinimumSize(1000, 700)
        self.is_fullscreen = False
        self.html_views = []

        self.tabs = QTabWidget()
        for html_path, title in html_paths_titles:
            abs_path = os.path.abspath(html_path)
            if not os.path.exists(abs_path):
                continue

            web = QWebEngineView()
            web.load(QUrl.fromLocalFile(abs_path))

            container = QWidget()
            layout = QVBoxLayout(container)
            layout.addWidget(web)
            self.tabs.addTab(container, os.path.basename(title))
            self.html_views.append((web, abs_path))

        self.save_btn = QPushButton(translate("plotly.save_html"))
        self.fullscreen_btn = QPushButton(translate("plotly.fullscreen"))
        self.save_btn.clicked.connect(self.save_as_html)
        self.fullscreen_btn.clicked.connect(self.toggle_fullscreen)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.fullscreen_btn)

        main_layout = QVBoxLayout()
        main_layout.addLayout(btn_layout)
        main_layout.addWidget(self.tabs)
        self.setLayout(main_layout)

    def save_as_html(self):
        try:
            index = self.tabs.currentIndex()
            web, html_path = self.html_views[index]

            file_dialog = QFileDialog(self)
            file_path, _ = file_dialog.getSaveFileName(
                self,
                translate("plotly.save_dialog_title"),
                "",
                "HTML Files (*.html);;All Files (*)"
            )
            if file_path:
                if not file_path.endswith(".html"):
                    file_path += ".html"
                # HTML dosyasını kopyala
                with open(html_path, "rb") as src, open(file_path, "wb") as dst:
                    dst.write(src.read())
                QMessageBox.information(self, translate("success.title"),
                                        translate("plotly.html_saved").format(path=file_path))
        except Exception as e:
            QMessageBox.critical(self, translate("error.title"),
                                 translate("plotly.html_exception").format(error=e))

    def toggle_fullscreen(self):
        if self.is_fullscreen:
            self.showNormal()
            self.fullscreen_btn.setText(translate("plotly.fullscreen"))
        else:
            self.showFullScreen()
            self.fullscreen_btn.setText(translate("plotly.windowed"))
        self.is_fullscreen = not self.is_fullscreen

if __name__ == "__main__":
    app = QApplication(sys.argv)
    viewer = PlotlyViewer(
        ("temp_forecast_plot.html", "Tahmin Grafiği"),
        ("trend_graph.html", "Trend Analizi"),
        ("summary_graph.html", "Sistem Özeti")
    )
    viewer.exec_()
