from modules.logic.finance import get_profit_report
from modules.widgets.plotly_to_gui import PlotlyViewer
from modules.config import DB_PATH
from modules.lang.translator import Translator

import os
import sqlite3
import pandas as pd
from datetime import datetime
from PyQt5.QtWidgets import (
    QDialog, QLabel, QPushButton, QVBoxLayout, QFileDialog,
    QMessageBox, QScrollArea, QWidget, QHBoxLayout,
    QComboBox, QDateEdit
)
from PyQt5.QtCore import QDate
import plotly.express as px

class ReportWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.t = Translator()
        self.setWindowTitle(self.t.tr("report.sales_title"))
        self.setFixedSize(800, 600)

        layout = QVBoxLayout()
        self.report_data = []
        filter_layout = QHBoxLayout()
        self.start_date = QDateEdit(QDate.currentDate().addMonths(-1))
        self.end_date = QDateEdit(QDate.currentDate())
        self.start_date.setCalendarPopup(True)
        self.end_date.setCalendarPopup(True)

        self.category_filter = QComboBox()
        self.brand_filter = QComboBox()
        self.category_filter.addItem(self.t.tr("filter.all"))
        self.brand_filter.addItem(self.t.tr("filter.all"))

        refresh_btn = QPushButton(self.t.tr("filter.apply"))
        refresh_btn.clicked.connect(self.load_data)

        filter_layout.addWidget(QLabel(self.t.tr("filter.start")))
        filter_layout.addWidget(self.start_date)
        filter_layout.addWidget(QLabel(self.t.tr("filter.end")))
        filter_layout.addWidget(self.end_date)
        filter_layout.addWidget(QLabel(self.t.tr("filter.brand")))
        filter_layout.addWidget(self.brand_filter)
        filter_layout.addWidget(QLabel(self.t.tr("filter.category")))
        filter_layout.addWidget(self.category_filter)
        filter_layout.addWidget(refresh_btn)
        layout.addLayout(filter_layout)

        self.scroll = QScrollArea()
        self.content = QWidget()
        self.content_layout = QVBoxLayout()
        self.content.setLayout(self.content_layout)
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(self.content)
        layout.addWidget(self.scroll)

        self.summary_label = QLabel()
        self.summary_label.setStyleSheet("font-weight: bold; font-size: 12pt; margin: 8px 0;")
        layout.addWidget(self.summary_label)

        export_btn = QPushButton(self.t.tr("report.export_excel"))
        export_btn.clicked.connect(self.export_to_excel)
        layout.addWidget(export_btn)

        graph_btn = QPushButton(self.t.tr("report.show_graph"))
        graph_btn.clicked.connect(self.show_graph)
        layout.addWidget(graph_btn)

        self.setLayout(layout)
        self.load_filters()
        self.load_data()

    def load_filters(self):
        try:
            conn = sqlite3.connect(DB_PATH)
            df = pd.read_sql_query("SELECT DISTINCT brand, category FROM products", conn)
            conn.close()
            for brand in sorted(df["brand"].dropna().unique()):
                self.brand_filter.addItem(brand)
            for cat in sorted(df["category"].dropna().unique()):
                self.category_filter.addItem(cat)
        except:
            pass

    def load_data(self):
        for i in reversed(range(self.content_layout.count())):
            widget_to_remove = self.content_layout.itemAt(i).widget()
            if widget_to_remove:
                widget_to_remove.setParent(None)

        try:
            conn = sqlite3.connect(DB_PATH)
            df = pd.read_sql_query("""
                SELECT s.date, p.product_name, p.brand, p.category, s.quantity_sold
                FROM sales s
                JOIN products p ON s.product_id = p.product_id
            """, conn)
            conn.close()

            df["date"] = pd.to_datetime(df["date"])
            start = self.start_date.date().toPyDate()
            end = self.end_date.date().toPyDate()
            df = df[(df["date"] >= pd.Timestamp(start)) & (df["date"] <= pd.Timestamp(end))]

            brand_val = self.brand_filter.currentText()
            cat_val = self.category_filter.currentText()

            if brand_val != self.t.tr("filter.all"):
                df = df[df["brand"] == brand_val]
            if cat_val != self.t.tr("filter.all"):
                df = df[df["category"] == cat_val]

            if df.empty:
                self.content_layout.addWidget(QLabel(self.t.tr("report.no_data")))
                self.summary_label.setText("")
                return

            total_sold = df["quantity_sold"].sum()
            top_seller = df.groupby("product_name")["quantity_sold"].sum().idxmax()
            self.summary_label.setText(self.t.tr("report.top_seller").format(name=top_seller, qty=total_sold))

            self.df_current = df.copy()

            for _, row in df.iterrows():
                label = QLabel(f"📅 {row['date'].strftime('%d.%m.%Y')} – {row['product_name']} → {row['quantity_sold']} {self.t.tr('unit.piece')}")
                label.setStyleSheet("font-size: 11pt;")
                self.content_layout.addWidget(label)

        except Exception as e:
            self.content_layout.addWidget(QLabel(self.t.tr("error.general").format(error=str(e))))

    def export_to_excel(self):
        if not hasattr(self, "df_current") or self.df_current.empty:
            QMessageBox.information(self, self.t.tr("info.title"), self.t.tr("report.no_data"))
            return
        path, _ = QFileDialog.getSaveFileName(self, self.t.tr("report.save_excel"), "", "Excel (*.xlsx)")
        if not path:
            return
        try:
            self.df_current.to_excel(path, index=False)
            QMessageBox.information(self, self.t.tr("success.title"), self.t.tr("report.saved").format(path=path))
        except Exception as e:
            QMessageBox.critical(self, self.t.tr("error.title"), self.t.tr("report.export_failed").format(error=str(e)))

    def show_graph(self):
        if not hasattr(self, "df_current") or self.df_current.empty:
            QMessageBox.information(self, self.t.tr("info.title"), self.t.tr("report.no_data"))
            return
        try:
            df_plot = self.df_current.groupby("product_name")["quantity_sold"].sum().reset_index()
            fig = px.bar(
                df_plot,
                x="product_name",
                y="quantity_sold",
                title=self.t.tr("report.graph_title"),
                labels={"quantity_sold": self.t.tr("unit.piece"), "product_name": self.t.tr("product.name")}
            )
            fig.update_layout(xaxis_tickangle=-45)
            html_path = "temp_sales_plot.html"
            fig.write_html(html_path)
            viewer = PlotlyViewer((html_path, self.t.tr("report.graph_title")))
            viewer.exec_()
        except Exception as e:
            QMessageBox.critical(self, self.t.tr("error.title"), self.t.tr("report.graph_failed").format(error=str(e)))

class ProfitReportWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.t = Translator()
        self.setWindowTitle(self.t.tr("profit.title"))
        self.setFixedSize(800, 600)

        layout = QVBoxLayout()
        self.report_data = []
        filter_layout = QHBoxLayout()
        self.start_date = QDateEdit(QDate.currentDate().addMonths(-1))
        self.end_date = QDateEdit(QDate.currentDate())
        self.start_date.setCalendarPopup(True)
        self.end_date.setCalendarPopup(True)

        refresh_btn = QPushButton(self.t.tr("filter.apply"))
        refresh_btn.clicked.connect(self.load_data)

        filter_layout.addWidget(QLabel(self.t.tr("filter.start")))
        filter_layout.addWidget(self.start_date)
        filter_layout.addWidget(QLabel(self.t.tr("filter.end")))
        filter_layout.addWidget(self.end_date)
        filter_layout.addWidget(refresh_btn)
        layout.addLayout(filter_layout)

        self.summary_label = QLabel()
        self.summary_label.setStyleSheet("font-weight: bold; font-size: 12pt; margin: 8px 0;")
        layout.addWidget(self.summary_label)

        self.scroll = QScrollArea()
        self.content = QWidget()
        self.content_layout = QVBoxLayout()
        self.content.setLayout(self.content_layout)
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(self.content)
        layout.addWidget(self.scroll)

        export_btn = QPushButton(self.t.tr("profit.export_excel"))
        export_btn.clicked.connect(self.export_csv)
        layout.addWidget(export_btn)

        graph_btn = QPushButton(self.t.tr("profit.show_graph"))
        graph_btn.clicked.connect(self.show_graph)
        layout.addWidget(graph_btn)

        self.setLayout(layout)
        self.load_data()

    def load_data(self):
        for i in reversed(range(self.content_layout.count())):
            widget_to_remove = self.content_layout.itemAt(i).widget()
            if widget_to_remove:
                widget_to_remove.setParent(None)

        try:
            conn = sqlite3.connect(DB_PATH)
            df_sales = pd.read_sql_query("SELECT * FROM sales", conn)
            df_products = pd.read_sql_query("SELECT * FROM products", conn)
            conn.close()

            df_sales["date"] = pd.to_datetime(df_sales["date"])
            start = self.start_date.date().toPyDate()
            end = self.end_date.date().toPyDate()
            df_sales = df_sales[(df_sales["date"] >= pd.Timestamp(start)) & (df_sales["date"] <= pd.Timestamp(end))]

            df_merged = pd.merge(df_sales, df_products, on="product_id")
            grouped = df_merged.groupby("product_name")

            total_revenue = 0
            total_cost = 0
            self.report_data.clear()

            for name, group in grouped:
                total_qty = group["quantity_sold"].sum()
                revenue = (group["quantity_sold"] * group["selling_price"]).sum()
                cost = (group["quantity_sold"] * group["cost_price"]).sum()
                profit = revenue - cost
                profit_margin = (profit / revenue * 100) if revenue != 0 else 0

                total_revenue += revenue
                total_cost += cost

                msg = self.t.tr("profit.line").format(
                    name=name, qty=total_qty, revenue=revenue, cost=cost, profit=profit, margin=profit_margin
                )
                label = QLabel(msg)
                label.setStyleSheet("font-size: 11pt;")
                self.content_layout.addWidget(label)

                self.report_data.append({
                    "Product": name,
                    "Quantity Sold": total_qty,
                    "Revenue": revenue,
                    "Cost": cost,
                    "Profit": profit,
                    "Profit Margin (%)": profit_margin
                })

            if self.report_data:
                df_rep = pd.DataFrame(self.report_data)
                best_profit = df_rep.sort_values("Profit", ascending=False).iloc[0]
                worst_profit = df_rep.sort_values("Profit").iloc[0]

                net_profit = total_revenue - total_cost
                self.summary_label.setText(
                    self.t.tr("profit.summary").format(
                        net=net_profit, revenue=total_revenue, cost=total_cost,
                        best=best_profit["Product"], best_val=best_profit["Profit"],
                        worst=worst_profit["Product"], worst_val=worst_profit["Profit"]
                    )
                )
            else:
                self.summary_label.setText(self.t.tr("profit.no_data"))

        except Exception as e:
            self.content_layout.addWidget(QLabel(self.t.tr("error.general").format(error=str(e))))

    def export_csv(self):
        if not self.report_data:
            QMessageBox.information(self, self.t.tr("info.title"), self.t.tr("profit.no_data"))
            return

        path, _ = QFileDialog.getSaveFileName(self, self.t.tr("profit.export_title"), "", "Excel (*.xlsx)")
        if not path:
            return

        try:
            df = pd.DataFrame(self.report_data)
            df.to_excel(path, index=False)
            QMessageBox.information(self, self.t.tr("success.title"), self.t.tr("profit.saved").format(path=path))
        except Exception as e:
            QMessageBox.critical(self, self.t.tr("error.title"), self.t.tr("profit.export_failed").format(error=str(e)))

    def show_graph(self):
        if not self.report_data:
            QMessageBox.information(self, self.t.tr("info.title"), self.t.tr("profit.no_data"))
            return
        try:
            df = pd.DataFrame(self.report_data)
            fig = px.bar(df, x="Product", y="Profit", title=self.t.tr("profit.graph_title"), labels={"Profit": self.t.tr("unit.profit")})
            fig.update_layout(xaxis_tickangle=-45)
            html_path = "temp_profit_plot.html"
            fig.write_html(html_path)
            viewer = PlotlyViewer((html_path, self.t.tr("profit.graph_title")))
            viewer.exec_()
        except Exception as e:
            QMessageBox.critical(self, self.t.tr("error.title"), self.t.tr("profit.graph_failed").format(error=str(e)))

class ExpiryReportWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.t = Translator()
        self.setWindowTitle(self.t.tr("expiry.title"))
        self.setFixedSize(800, 600)

        layout = QVBoxLayout()
        self.report_data = []

        filter_layout = QHBoxLayout()
        self.only_critical_checkbox = QComboBox()
        self.only_critical_checkbox.addItems([
            self.t.tr("expiry.all"),
            self.t.tr("expiry.critical_only")
        ])

        refresh_btn = QPushButton(self.t.tr("filter.apply"))
        refresh_btn.clicked.connect(self.load_data)

        filter_layout.addWidget(QLabel(self.t.tr("expiry.mode")))
        filter_layout.addWidget(self.only_critical_checkbox)
        filter_layout.addWidget(refresh_btn)
        layout.addLayout(filter_layout)

        self.summary_label = QLabel()
        self.summary_label.setStyleSheet("font-weight: bold; font-size: 12pt; margin: 8px 0;")
        layout.addWidget(self.summary_label)

        self.scroll = QScrollArea()
        self.content = QWidget()
        self.content_layout = QVBoxLayout()
        self.content.setLayout(self.content_layout)
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(self.content)
        layout.addWidget(self.scroll)

        export_btn = QPushButton(self.t.tr("expiry.export_excel"))
        export_btn.clicked.connect(self.export_to_csv)
        layout.addWidget(export_btn)

        graph_btn = QPushButton(self.t.tr("expiry.show_graph"))
        graph_btn.clicked.connect(self.show_graph)
        layout.addWidget(graph_btn)

        self.setLayout(layout)
        self.load_data()

    def load_data(self):
        for i in reversed(range(self.content_layout.count())):
            widget_to_remove = self.content_layout.itemAt(i).widget()
            if widget_to_remove:
                widget_to_remove.setParent(None)

        try:
            conn = sqlite3.connect(DB_PATH)
            df = pd.read_sql_query("""
                SELECT p.product_name, p.brand, p.category, st.date as stock_date,
                       st.expiry_date, st.quantity
                FROM stock_transactions st
                JOIN products p ON st.product_id = p.product_id
                WHERE st.expiry_date IS NOT NULL
            """, conn)
            conn.close()

            df["expiry_date"] = pd.to_datetime(df["expiry_date"], errors="coerce")
            df["stock_date"] = pd.to_datetime(df["stock_date"], errors="coerce")
            df["days_left"] = (df["expiry_date"] - pd.Timestamp.today()).dt.days
            df = df.sort_values("expiry_date")

            if self.only_critical_checkbox.currentText() == self.t.tr("expiry.critical_only"):
                df = df[df["days_left"] <= 30]

            total_critical = 0
            total_quantity = 0

            self.report_data.clear()

            for _, row in df.iterrows():
                name = row["product_name"]
                brand = row["brand"]
                category = row["category"]
                expiry = row["expiry_date"].strftime("%d.%m.%Y")
                stock_date = row["stock_date"].strftime("%d.%m.%Y") if pd.notna(row["stock_date"]) else self.t.tr("expiry.unknown")
                quantity = int(row["quantity"])
                days_left = int(row["days_left"])

                if days_left <= 3:
                    icon = "🔴"
                elif days_left <= 10:
                    icon = "🟡"
                else:
                    icon = "🟢"

                msg = self.t.tr("expiry.line").format(
                    icon=icon, name=name, brand=brand, cat=category,
                    date=stock_date, qty=quantity, expiry=expiry, left=days_left
                )

                label = QLabel(msg)
                label.setStyleSheet("font-size: 11pt;")
                self.content_layout.addWidget(label)

                self.report_data.append({
                    "Product": name,
                    "Brand": brand,
                    "Category": category,
                    "Purchase Date": stock_date,
                    "Expiry Date": expiry,
                    "Quantity": quantity,
                    "Days Left": days_left
                })

                if days_left <= 10:
                    total_critical += 1
                    total_quantity += quantity

            if self.report_data:
                self.summary_label.setText(self.t.tr("expiry.summary").format(
                    count=total_critical, qty=total_quantity
                ))
            else:
                self.summary_label.setText(self.t.tr("expiry.no_data"))

        except Exception as e:
            self.content_layout.addWidget(QLabel(self.t.tr("error.general").format(error=str(e))))

    def export_to_csv(self):
        if not self.report_data:
            QMessageBox.information(self, self.t.tr("info.title"), self.t.tr("expiry.no_data"))
            return

        path, _ = QFileDialog.getSaveFileName(self, self.t.tr("expiry.export_title"), "", "Excel (*.xlsx)")
        if not path:
            return

        try:
            df = pd.DataFrame(self.report_data)
            df.to_excel(path, index=False)
            QMessageBox.information(self, self.t.tr("success.title"), self.t.tr("expiry.saved").format(path=path))
        except Exception as e:
            QMessageBox.critical(self, self.t.tr("error.title"), self.t.tr("expiry.export_failed").format(error=str(e)))

    def show_graph(self):
        if not self.report_data:
            QMessageBox.information(self, self.t.tr("info.title"), self.t.tr("expiry.no_data"))
            return

        try:
            df = pd.DataFrame(self.report_data)
            df["Days Left"] = df["Days Left"].astype(int)
            df_plot = df.groupby("Days Left")["Quantity"].sum().reset_index()
            fig = px.bar(
                df_plot, x="Days Left", y="Quantity",
                title=self.t.tr("expiry.graph_title"),
                labels={"Days Left": self.t.tr("expiry.days_left"), "Quantity": self.t.tr("unit.piece")}
            )
            fig.update_layout(xaxis_title=self.t.tr("expiry.days_left"), yaxis_title=self.t.tr("unit.piece"), xaxis_tickmode="linear")
            html_path = "temp_expiry_plot.html"
            fig.write_html(html_path)
            viewer = PlotlyViewer((html_path, self.t.tr("expiry.graph_title")))
            viewer.exec_()
        except Exception as e:
            QMessageBox.critical(self, self.t.tr("error.title"), self.t.tr("expiry.graph_failed").format(error=str(e)))

def check_stock_levels():
    from modules.lang.translator import Translator
    t = Translator()

    try:
        conn = sqlite3.connect(DB_PATH)

        df_products = pd.read_sql_query("SELECT * FROM products", conn)
        df_sales = pd.read_sql_query("SELECT product_id, quantity_sold FROM sales", conn)
        df_stock = pd.read_sql_query("SELECT product_id, quantity FROM stock_transactions", conn)

        conn.close()

        if df_products.empty:
            QMessageBox.information(None, t.tr("info.title"), t.tr("stock.no_products"))
            return

        df_sales_sum = df_sales.groupby("product_id")["quantity_sold"].sum().reset_index() if not df_sales.empty else pd.DataFrame(columns=["product_id", "quantity_sold"])
        df_stock_sum = df_stock.groupby("product_id")["quantity"].sum().reset_index() if not df_stock.empty else pd.DataFrame(columns=["product_id", "quantity"])

        df_stock_sum.columns = ["product_id", "total_stock"]
        df_sales_sum.columns = ["product_id", "total_sold"]

        df = pd.merge(df_products, df_sales_sum, on="product_id", how="left")
        df = pd.merge(df, df_stock_sum, on="product_id", how="left")
        df = df.fillna(0)

        df["current_stock"] = (df["total_stock"] - df["total_sold"]).clip(lower=0)

        threshold = 3
        low_stock_items = df[df["current_stock"] < threshold]

        if low_stock_items.empty:
            QMessageBox.information(None, t.tr("stock.status"), t.tr("stock.all_good"))
        else:
            message = t.tr("stock.critical_header") + "\n\n"
            for _, row in low_stock_items.iterrows():
                message += f"- {row['product_name']} → {int(row['current_stock'])} {t.tr('unit.piece')}\n"

            QMessageBox.warning(None, t.tr("stock.alert"), message)

    except Exception as e:
        QMessageBox.critical(None, t.tr("error.title"), t.tr("stock.error").format(error=str(e)))

def backup_all_data():
    from modules.lang.translator import Translator
    t = Translator()

    try:
        conn = sqlite3.connect(DB_PATH)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        folder = QFileDialog.getExistingDirectory(None, t.tr("backup.select_folder"))
        if not folder:
            return

        for table in ["products", "sales", "stock_transactions"]:
            if table == "sales":
                df = pd.read_sql_query("""
                    SELECT s.date, s.product_id, p.product_name, s.quantity_sold
                    FROM sales s
                    JOIN products p ON s.product_id = p.product_id
                """, conn)

            elif table == "stock_transactions":
                df = pd.read_sql_query("""
                    SELECT st.date, st.product_id, p.product_name, st.quantity, st.note
                    FROM stock_transactions st
                    JOIN products p ON st.product_id = p.product_id
                """, conn)

            elif table == "products":
                df = pd.read_sql_query("SELECT * FROM products", conn)

            else:
                continue

            csv_path = os.path.join(folder, f"{table}_{timestamp}.csv")
            df.to_csv(csv_path, index=False, encoding="utf-8-sig", sep=";")

            excel_path = os.path.join(folder, f"{table}_{timestamp}.xlsx")
            df.to_excel(excel_path, index=False)

        QMessageBox.information(None, t.tr("success.title"), t.tr("backup.success").format(path=folder))

    except Exception as e:
        QMessageBox.critical(None, t.tr("error.title"), t.tr("backup.failed").format(error=str(e)))
