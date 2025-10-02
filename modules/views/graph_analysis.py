import sqlite3
import pandas as pd
import plotly.graph_objects as go
import tempfile
from PyQt5.QtWidgets import QDialog, QFormLayout, QComboBox, QPushButton, QMessageBox
from modules.widgets.plotly_to_gui import PlotlyViewer
from modules.config import DB_PATH
from modules.lang.translator import Translator

class GraphWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.t = Translator()
        self.setWindowTitle(self.t.tr("graph.title"))
        self.setFixedSize(440, 300)

        self.layout = QFormLayout()

        self.filter_type = QComboBox()
        self.filter_type.addItems([
            self.t.tr("graph.by_product"),
            self.t.tr("graph.by_brand"),
            self.t.tr("graph.by_category"),
            self.t.tr("graph.by_storage"),
            self.t.tr("graph.overall")
        ])

        self.target_selector = QComboBox()
        self.update_target_list(self.filter_type.currentText())
        self.filter_type.currentTextChanged.connect(self.update_target_list)

        self.display_mode = QComboBox()
        self.display_mode.addItems([
            self.t.tr("graph.sales_qty"),
            self.t.tr("graph.revenue"),
            self.t.tr("graph.profit"),
            self.t.tr("graph.usage"),
            self.t.tr("graph.all")
        ])

        self.plot_btn = QPushButton(self.t.tr("graph.show_button"))
        self.plot_btn.clicked.connect(self.plot_graph)

        self.layout.addRow(self.t.tr("graph.filter_type"), self.filter_type)
        self.layout.addRow(self.t.tr("graph.selection"), self.target_selector)
        self.layout.addRow(self.t.tr("graph.display_mode"), self.display_mode)
        self.layout.addRow(self.plot_btn)

        self.setLayout(self.layout)

    def update_target_list(self, filter_type):
        self.target_selector.clear()
        conn = sqlite3.connect(DB_PATH)
        products = pd.read_sql_query("SELECT * FROM products", conn)
        shelves = pd.read_sql_query("SELECT * FROM shelves", conn)
        fridges = pd.read_sql_query("SELECT * FROM fridges", conn)
        conn.close()

        t = self.t
        mapping = {
            t.tr("graph.by_product"): "product_name",
            t.tr("graph.by_brand"): "brand",
            t.tr("graph.by_category"): "category"
        }

        if filter_type in mapping:
            values = products[mapping[filter_type]].dropna().unique()
        elif filter_type == t.tr("graph.by_storage"):
            values = list(shelves["name"]) + list(fridges["name"])
        else:
            values = [t.tr("graph.overall_value")]

        self.target_selector.addItems(sorted(str(v) for v in values))

    def plot_graph(self):
        t = self.t
        filter_type = self.filter_type.currentText()
        target = self.target_selector.currentText()
        display_mode = self.display_mode.currentText()

        conn = sqlite3.connect(DB_PATH)
        sales = pd.read_sql_query("SELECT * FROM sales WHERE quantity_sold > 0", conn)
        products = pd.read_sql_query("SELECT * FROM products", conn)
        links = pd.read_sql_query("SELECT * FROM product_storage_links", conn)
        fridges = pd.read_sql_query("SELECT * FROM fridges", conn)
        shelves = pd.read_sql_query("SELECT * FROM shelves", conn)
        ai_log = pd.read_sql_query("SELECT * FROM ai_suggestions_log", conn) if "ai_suggestions_log" in pd.read_sql("SELECT name FROM sqlite_master WHERE type='table'", conn)["name"].values else pd.DataFrame()
        conn.close()

        sales["date"] = pd.to_datetime(sales["date"])
        df = pd.merge(sales, products, on="product_id")
        df = pd.merge(df, links, on="product_id", how="left")

        if filter_type == t.tr("graph.by_product"):
            df = df[df["product_name"] == target]
        elif filter_type == t.tr("graph.by_brand"):
            df = df[df["brand"] == target]
        elif filter_type == t.tr("graph.by_category"):
            df = df[df["category"] == target]
        elif filter_type == t.tr("graph.by_storage"):
            sid = None
            if target in shelves["name"].values:
                sid = shelves[shelves["name"] == target]["id"].values[0]
                df = df[(df["storage_type"] == "shelf") & (df["storage_id"] == sid)]
            elif target in fridges["name"].values:
                sid = fridges[fridges["name"] == target]["id"].values[0]
                df = df[(df["storage_type"] == "fridge") & (df["storage_id"] == sid)]

        if df.empty:
            QMessageBox.information(self, t.tr("info.title"), t.tr("graph.no_data"))
            return

        df["effective_price"] = df.apply(
            lambda row: float(row["discount_price"]) if (
                pd.notna(row.get("discount_price")) and
                pd.notna(row.get("discount_until")) and
                row["date"] <= pd.to_datetime(row["discount_until"])
            ) else float(row["selling_price"]), axis=1
        )

        df["revenue"] = df["quantity_sold"] * df["effective_price"]
        df["cost"] = df["quantity_sold"] * df["cost_price"]
        df["profit"] = df["revenue"] - df["cost"]
        df["used_volume"] = df["quantity_sold"] * df["unit_volume"].fillna(1)

        df_grouped = df.groupby("date").agg({
            "quantity_sold": "sum",
            "revenue": "sum",
            "profit": "sum",
            "used_volume": "sum"
        }).reset_index()

        full_range = pd.date_range(start=df_grouped["date"].min(), end=df_grouped["date"].max())
        df_grouped = df_grouped.set_index("date").reindex(full_range, fill_value=0).rename_axis("date").reset_index()

        fig = go.Figure()

        if display_mode in [t.tr("graph.sales_qty"), t.tr("graph.all")]:
            fig.add_trace(go.Scatter(x=df_grouped["date"], y=df_grouped["quantity_sold"], mode="lines+markers", name=t.tr("graph.sales_qty")))

        if display_mode in [t.tr("graph.revenue"), t.tr("graph.all")]:
            fig.add_trace(go.Scatter(x=df_grouped["date"], y=df_grouped["revenue"], mode="lines+markers", name=t.tr("graph.revenue")))

        if display_mode in [t.tr("graph.profit"), t.tr("graph.all")]:
            fig.add_trace(go.Scatter(x=df_grouped["date"], y=df_grouped["profit"], mode="lines+markers", name=t.tr("graph.profit")))

        if display_mode in [t.tr("graph.usage"), t.tr("graph.all")]:
            capacity = 1
            if filter_type == t.tr("graph.by_storage"):
                if target in shelves["name"].values:
                    capacity = shelves[shelves["name"] == target]["max_capacity"].values[0]
                elif target in fridges["name"].values:
                    capacity = fridges[fridges["name"] == target]["max_capacity"].values[0]

            df_grouped["usage_percent"] = (df_grouped["used_volume"] / capacity) * 100
            fig.add_trace(go.Scatter(x=df_grouped["date"], y=df_grouped["usage_percent"], mode="lines+markers", name=t.tr("graph.usage")))

        if not ai_log.empty and filter_type == t.tr("graph.by_product"):
            ai_log["timestamp"] = pd.to_datetime(ai_log["timestamp"])
            ai_log = ai_log[ai_log["product_name"] == target]
            for _, row in ai_log.iterrows():
                fig.add_vline(x=row["timestamp"], line=dict(color="purple", dash="dot"),
                              annotation_text=f"🧠 {row['suggestion_type']}", annotation_position="top right")

        fig.update_layout(
            title=f"{target} – {display_mode}",
            xaxis_title=t.tr("forecast.date"),
            yaxis_title=t.tr("graph.y_label"),
            template="plotly_white",
            height=500
        )

        with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp:
            fig.write_html(tmp.name)
            html_path = tmp.name

        viewer = PlotlyViewer((html_path, f"{target} – {display_mode}"))
        viewer.exec_()
