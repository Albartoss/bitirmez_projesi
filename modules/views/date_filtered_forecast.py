from PyQt5.QtWidgets import (
    QDialog, QFormLayout, QComboBox, QPushButton, QDateEdit, QMessageBox, QFileDialog
)
import sqlite3
import pandas as pd
import tempfile
import numpy as np
import plotly.graph_objects as go
from prophet import Prophet
from statsmodels.tsa.arima.model import ARIMA
from sklearn.metrics import mean_absolute_error, mean_squared_error
from PyQt5.QtCore import QDate
from modules.config import DB_PATH
from modules.widgets.plotly_to_gui import PlotlyViewer
from modules.lang.translator import Translator

class DateFilteredForecastWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.t = Translator()
        self.setWindowTitle(self.t.tr("forecast.title"))
        self.setFixedSize(400, 200)

        self.layout = QFormLayout()
        self.product_dropdown = QComboBox()
        self.start_date = QDateEdit()
        self.end_date = QDateEdit()
        self.forecast_btn = QPushButton(self.t.tr("forecast.button"))
        self.save_html_btn = QPushButton(self.t.tr("plotly.save_html"))
        self.last_fig = None

        self.start_date.setDate(QDate.currentDate().addDays(-30))
        self.end_date.setDate(QDate.currentDate())
        self.start_date.setCalendarPopup(True)
        self.end_date.setCalendarPopup(True)

        try:
            conn = sqlite3.connect(DB_PATH)
            df = pd.read_sql_query("SELECT DISTINCT product_name FROM products", conn)
            conn.close()
            for name in df["product_name"].dropna().unique():
                self.product_dropdown.addItem(name)
        except Exception as e:
            QMessageBox.critical(self, self.t.tr("error.title"), self.t.tr("forecast.load_error").format(error=str(e)))
            self.close()

        self.forecast_btn.clicked.connect(self.show_forecast)
        self.save_html_btn.clicked.connect(self.save_html)

        self.layout.addRow(self.t.tr("forecast.select_product"), self.product_dropdown)
        self.layout.addRow(self.t.tr("forecast.start_date"), self.start_date)
        self.layout.addRow(self.t.tr("forecast.end_date"), self.end_date)
        self.layout.addRow(self.forecast_btn)
        self.layout.addRow(self.save_html_btn)
        self.setLayout(self.layout)

    def show_forecast(self):
        product_name = self.product_dropdown.currentText()
        start = self.start_date.date().toPyDate()
        end = self.end_date.date().toPyDate()

        try:
            conn = sqlite3.connect(DB_PATH)
            sales = pd.read_sql_query("SELECT * FROM sales", conn)
            products = pd.read_sql_query("SELECT * FROM products", conn)
            conn.close()

            df = pd.merge(sales, products, on="product_id")
            df = df[df["product_name"] == product_name]
            df["date"] = pd.to_datetime(df["date"])
            df = df[(df["date"] >= pd.Timestamp(start)) & (df["date"] <= pd.Timestamp(end))]

            if df.empty:
                QMessageBox.warning(self, self.t.tr("info.title"), self.t.tr("forecast.no_data"))
                self.last_fig = None
                return

            df_grouped = df.groupby("date")["quantity_sold"].sum().reset_index()
            df_prophet = df_grouped.rename(columns={"date": "ds", "quantity_sold": "y"})

            # Prophet
            model = Prophet(daily_seasonality=True)
            model.fit(df_prophet)
            future = model.make_future_dataframe(periods=10)
            forecast = model.predict(future)
            merged = pd.merge(df_prophet, forecast, on="ds", how="left")
            mae_prophet = mean_absolute_error(merged["y"], merged["yhat"])
            rmse_prophet = mean_squared_error(merged["y"], merged["yhat"]) ** 0.5
            forecast_future = forecast[forecast["ds"] > df_prophet["ds"].max()]
            forecast["yhat"] = forecast["yhat"].clip(lower=0)
            forecast["yhat_upper"] = forecast["yhat_upper"].clip(lower=0)
            forecast["yhat_lower"] = forecast["yhat_lower"].clip(lower=0)

            # ARIMA
            y = df_prophet["y"].values
            order = (1, 1, 1) if len(y) > 5 else (0, 1, 0)
            arima_model = ARIMA(y, order=order)
            arima_fit = arima_model.fit()
            arima_forecast = arima_fit.forecast(steps=10)
            arima_index = pd.date_range(df_prophet["ds"].max() + pd.Timedelta(days=1), periods=10, freq="D")
            arima_series = pd.Series(np.maximum(arima_forecast, 0), index=arima_index)
            arima_in_sample = arima_fit.predict(start=0, end=len(y)-1)
            mae_arima = mean_absolute_error(y, arima_in_sample)
            rmse_arima = mean_squared_error(y, arima_in_sample) ** 0.5

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df_prophet["ds"], y=df_prophet["y"],
                mode="lines+markers", name=self.t.tr("forecast.actual_sales"), line=dict(color="royalblue")
            ))
            fig.add_trace(go.Scatter(
                x=forecast_future["ds"], y=forecast_future["yhat"],
                mode="lines", name="Prophet " + self.t.tr("forecast.prediction"), line=dict(color="darkorange", dash="dash")
            ))
            fig.add_trace(go.Scatter(
                x=forecast_future["ds"].tolist() + forecast_future["ds"][::-1].tolist(),
                y=forecast_future["yhat_upper"].tolist() + forecast_future["yhat_lower"][::-1].tolist(),
                fill="toself", fillcolor="rgba(255,165,0,0.2)",
                line=dict(color="rgba(255,255,255,0)"),
                hoverinfo="skip", name=self.t.tr("forecast.confidence_interval")
            ))
            fig.add_trace(go.Scatter(
                x=arima_series.index, y=arima_series.values,
                mode='lines', name='ARIMA Tahmini', line=dict(color='green', dash='dot')
            ))

            fig.add_annotation(
                text=f"Prophet - MAE: {mae_prophet:.2f} | RMSE: {rmse_prophet:.2f}",
                xref="paper", yref="paper",
                x=1, y=1.12, showarrow=False,
                bgcolor="lightblue", bordercolor="blue", borderwidth=1
            )
            fig.add_annotation(
                text=f"ARIMA - MAE: {mae_arima:.2f} | RMSE: {rmse_arima:.2f}",
                xref="paper", yref="paper",
                x=1, y=1.06, showarrow=False,
                bgcolor="lightgreen", bordercolor="green", borderwidth=1
            )

            fig.update_layout(
                title=f"{product_name} – {self.t.tr('forecast.title')} ({start} → {end}) + 10 {self.t.tr('forecast.days')}",
                xaxis_title=self.t.tr("forecast.date"),
                yaxis_title=self.t.tr("forecast.sales_qty"),
                template="plotly_white",
                height=500
            )

            # Geçici dosya ile gösterim için kaydet
            with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp_html:
                fig.write_html(tmp_html.name)
                html_path = tmp_html.name

            self.last_fig = fig  # Kaydet butonunda kullanılacak
            viewer = PlotlyViewer((html_path, f"{product_name} - {self.t.tr('forecast.title')}"))
            viewer.exec_()

            QMessageBox.information(
                self,
                self.t.tr("forecast.result_title"),
                f"Prophet\nMAE: {mae_prophet:.2f}  RMSE: {rmse_prophet:.2f}\n"
                f"ARIMA\nMAE: {mae_arima:.2f}  RMSE: {rmse_arima:.2f}\n"
                f"Negatif çıkan tahminler 0 olarak gösterilmiştir."
            )

        except Exception as e:
            QMessageBox.critical(self, self.t.tr("error.title"), self.t.tr("forecast.error").format(error=str(e)))

    def save_html(self):
        if self.last_fig is None:
            QMessageBox.warning(self, self.t.tr("warning.title"), self.t.tr("forecast.no_data"))
            return
        file_dialog = QFileDialog(self)
        file_path, _ = file_dialog.getSaveFileName(self, self.t.tr("plotly.save_html"), "", "HTML (*.html)")
        if file_path:
            if not file_path.endswith(".html"):
                file_path += ".html"
            try:
                self.last_fig.write_html(file_path)
                QMessageBox.information(self, self.t.tr("success.title"), self.t.tr("plotly.html_saved").format(path=file_path))
            except Exception as e:
                QMessageBox.critical(self, self.t.tr("error.title"), self.t.tr("plotly.html_exception").format(error=str(e)))
