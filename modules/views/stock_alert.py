import os
import sqlite3
import pandas as pd
from PyQt5.QtWidgets import (
    QDialog, QLabel, QPushButton, QVBoxLayout, QFileDialog,
    QMessageBox, QScrollArea, QWidget, QHBoxLayout
)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt
from modules.config import DB_PATH
from modules.lang.translator import translator
pd.set_option('future.no_silent_downcasting', True)

class StockAlertWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(translator("stock_alert.title"))
        self.setMinimumSize(750, 550)

        self.report_data = []
        main_layout = QVBoxLayout()
        scroll = QScrollArea()
        content_widget = QWidget()
        content_layout = QVBoxLayout()

        try:
            conn = sqlite3.connect(DB_PATH)
            df_products = pd.read_sql_query("SELECT * FROM products", conn)
            df_sales = pd.read_sql_query("SELECT product_id, quantity_sold, date FROM sales", conn)
            df_stock = pd.read_sql_query("SELECT product_id, quantity, expiry_date FROM stock_transactions", conn)
            conn.close()

            df_sales["date"] = pd.to_datetime(df_sales["date"], errors="coerce")
            df_stock["expiry_date"] = pd.to_datetime(df_stock["expiry_date"], errors="coerce")

            today = pd.Timestamp.today()
            recent_sales = df_sales[df_sales["date"] >= (today - pd.Timedelta(days=30))]
            days_span = 30 if not recent_sales.empty else 1

            df_sales_sum = recent_sales.groupby("product_id")["quantity_sold"].sum().reset_index()
            df_stock_sum = df_stock.groupby("product_id")["quantity"].sum().reset_index()

            df_expiry = df_stock.dropna(subset=["expiry_date"]).copy()
            df_expiry = df_expiry.groupby("product_id")["expiry_date"].min().reset_index()
            df_expiry.columns = ["product_id", "earliest_expiry"]

            df = df_products.copy()
            df = pd.merge(df, df_sales_sum, on="product_id", how="left").fillna(0).infer_objects(copy=False)
            df = pd.merge(df, df_stock_sum, on="product_id", how="left").fillna(0).infer_objects(copy=False)
            df = pd.merge(df, df_expiry, on="product_id", how="left")

            df["current_stock"] = (df["quantity"] - df["quantity_sold"]).clip(lower=0)
            df["daily_avg"] = df["quantity_sold"] / days_span
            df["days_left"] = df.apply(
                lambda row: row["current_stock"] / row["daily_avg"] if row["daily_avg"] > 0 else float("inf"),
                axis=1
            )
            df["days_left_display"] = df["days_left"].apply(
                lambda x: f"{int(x)} " + translator("unit.days") if x != float("inf") else translator("stock_alert.slow_moving")
            )
            df["expiry_str"] = df["earliest_expiry"].apply(
                lambda x: pd.to_datetime(x).strftime("%Y-%m-%d") if pd.notna(x) else translator("common.no_expiry")
            )
            df["critical"] = df["days_left"] <= 5

            for _, row in df.iterrows():
                pname = row["product_name"]
                rem = int(row["current_stock"])
                stock_in = int(row["quantity"])
                daily = round(row["daily_avg"], 2)
                left = row["days_left_display"]
                expiry = row["expiry_str"]
                icon = "🔻" if row["critical"] else "✅"
                img_path = row.get("image_path")

                hbox = QHBoxLayout()
                image = QLabel()
                image.setFixedSize(50, 50)
                if img_path and os.path.exists(img_path):
                    pixmap = QPixmap(img_path).scaled(50, 50, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    image.setPixmap(pixmap)
                hbox.addWidget(image)

                text = QLabel(
                    f"{icon} <b>{pname}</b> — { translator('stock_alert.remaining') }: {rem} / { translator('stock_alert.in') }: {stock_in} | "
                    f"{translator('stock_alert.daily_avg')}: {daily} | {translator('stock_alert.days_left')}: <span style='color:red;'>{left}</span> | "
                    f"📅 {translator('stock_alert.expiry')}: {expiry}"
                )
                text.setTextFormat(Qt.RichText)
                text.setWordWrap(True)
                text.setStyleSheet("font-size: 11pt; padding: 6px; border-bottom: 1px solid #ccc;")
                hbox.addWidget(text)

                container = QWidget()
                container.setLayout(hbox)
                content_layout.addWidget(container)

                self.report_data.append({
                    translator("product.name"): pname,
                    translator("stock_alert.in"): stock_in,
                    translator("stock_alert.remaining"): rem,
                    translator("stock_alert.daily_avg"): daily,
                    translator("stock_alert.days_left"): left,
                    translator("stock_alert.expiry"): expiry,
                    "Critical": row["critical"]
                })

        except Exception as e:
            content_layout.addWidget(QLabel(f"{translator('error.prefix')}{str(e)}"))

        content_widget.setLayout(content_layout)
        scroll.setWidgetResizable(True)
        scroll.setWidget(content_widget)

        export_btn = QPushButton(translator("button.export_csv"))
        export_btn.clicked.connect(self.export_to_csv)

        main_layout.addWidget(scroll)
        main_layout.addWidget(export_btn)
        self.setLayout(main_layout)

    def export_to_csv(self):
        if not self.report_data:
            QMessageBox.information(self, translator("info.title"), translator("stock_alert.no_data"))
            return

        path, _ = QFileDialog.getSaveFileName(self, translator("stock_alert.save_csv"), "", translator("stock_alert.csv_filter"))
        if not path:
            return

        try:
            df_export = pd.DataFrame(self.report_data)
            df_export.to_csv(path, index=False, sep=";", encoding="utf-8-sig")
            QMessageBox.information(self, translator("success.title"), translator("stock_alert.saved").format(path=path))
        except Exception as e:
            QMessageBox.critical(self, translator("error.title"), translator("stock_alert.failed").format(error=str(e)))
