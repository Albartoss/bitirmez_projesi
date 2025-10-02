from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QScrollArea, QWidget, QHBoxLayout
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
import os
import sqlite3
from modules.config import DB_PATH
from modules.logic.ml_assistant import InventoryForecastAssistant
from modules.lang.translator import Translator

class OwnerAssistantWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.t = Translator()
        self.setWindowTitle(self.t.tr("ai.owner_window_title"))
        self.setMinimumSize(800, 600)

        layout = QVBoxLayout()
        scroll = QScrollArea()
        content_widget = QWidget()
        content_layout = QVBoxLayout()

        assistant = InventoryForecastAssistant()
        try:
            results = assistant.run_analysis()
            for row in results:
                pname = row['product_name']
                stock = row['stock']
                forecast = row['forecast_avg']
                days = row['days_to_depletion']
                slow = row['is_slow']

                icon = "🔻" if slow else "✅"
                color = "red" if slow else "black"

                hbox = QHBoxLayout()

                # Görsel
                image_label = QLabel()
                image_label.setFixedSize(60, 60)
                try:
                    conn = sqlite3.connect(DB_PATH)
                    c = conn.cursor()
                    c.execute("SELECT image_path FROM products WHERE product_id = ?", (row['product_id'],))
                    img_path = c.fetchone()
                    conn.close()
                    if img_path and img_path[0] and os.path.exists(img_path[0]):
                        pixmap = QPixmap(img_path[0]).scaled(60, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        image_label.setPixmap(pixmap)
                except:
                    pass
                hbox.addWidget(image_label)

                text = self.t.tr("ai.owner_line").format(
                    icon=icon,
                    product=pname,
                    stock=stock,
                    forecast=forecast,
                    days=days,
                    color=color
                )

                label = QLabel(text)
                label.setTextFormat(Qt.RichText)
                label.setStyleSheet("font-size: 11pt; margin-left: 10px;")
                label.setWordWrap(True)
                hbox.addWidget(label)

                container = QWidget()
                container.setLayout(hbox)
                content_layout.addWidget(container)
        except Exception as e:
            content_layout.addWidget(QLabel(self.t.tr("error.prefix") + str(e)))

        content_widget.setLayout(content_layout)
        scroll.setWidgetResizable(True)
        scroll.setWidget(content_widget)

        layout.addWidget(scroll)
        self.setLayout(layout)
