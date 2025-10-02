import sqlite3
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from prophet import Prophet
from sklearn.metrics import mean_absolute_error, mean_squared_error
from statsmodels.tsa.arima.model import ARIMA 
from modules.config import DB_PATH

def get_forecast_with_arima(product_name, periods=10):
    try:
        conn = sqlite3.connect(DB_PATH)
        sales = pd.read_sql_query("SELECT * FROM sales", conn)
        products = pd.read_sql_query("SELECT * FROM products", conn)
        conn.close()

        df = pd.merge(sales, products, on="product_id")
        df = df[df["product_name"] == product_name]

        if df.empty:
            print("DEBUG: DataFrame boş, ürün bulunamadı!")
            return None, None, None, None, None

        df["date"] = pd.to_datetime(df["date"])
        df_grouped = df.groupby("date")["quantity_sold"].sum().reset_index()
        df_prophet = df_grouped.rename(columns={"date": "ds", "quantity_sold": "y"})

        # Prophet
        model = Prophet(daily_seasonality=True)
        model.fit(df_prophet)
        future = model.make_future_dataframe(periods=periods)
        forecast = model.predict(future)
        merged = pd.merge(df_prophet, forecast, on="ds", how="left")
        mae_prophet = mean_absolute_error(merged["y"], merged["yhat"])
        rmse_prophet = mean_squared_error(merged["y"], merged["yhat"]) ** 0.5
        forecast_future = forecast[forecast["ds"] > df_prophet["ds"].max()]
        forecast["yhat"] = forecast["yhat"].clip(lower=0)
        forecast["yhat_upper"] = forecast["yhat_upper"].clip(lower=0)
        forecast["yhat_lower"] = forecast["yhat_lower"].clip(lower=0)
        y = df_prophet["y"].values
        order = (1, 1, 1) if len(y) > 5 else (0, 1, 0)
        # ARIMA  
        arima_model = ARIMA(y, order=order)
        arima_fit = arima_model.fit()
        arima_forecast = arima_fit.forecast(steps=periods)
        arima_index = pd.date_range(df_prophet["ds"].max() + pd.Timedelta(days=1), periods=periods, freq="D")
        arima_series = pd.Series(arima_forecast, index=arima_index)

        arima_in_sample = arima_fit.predict(start=0, end=len(y)-1)
        mae_arima = mean_absolute_error(y, arima_in_sample)
        rmse_arima = mean_squared_error(y, arima_in_sample) ** 0.5
        arima_series = pd.Series(np.maximum(arima_forecast, 0), index=arima_index)

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=df_prophet["ds"], y=df_prophet["y"],
            mode='lines+markers',
            name='Gerçek Satış',
            line=dict(color='royalblue')
        ))
        fig.add_trace(go.Scatter(
            x=forecast_future["ds"], y=forecast_future["yhat"],
            mode='lines',
            name='Prophet Tahmini',
            line=dict(color='darkorange', dash='dash')
        ))
        fig.add_trace(go.Scatter(
            x=forecast_future["ds"].tolist() + forecast_future["ds"][::-1].tolist(),
            y=forecast_future["yhat_upper"].tolist() + forecast_future["yhat_lower"][::-1].tolist(),
            fill='toself',
            fillcolor='rgba(255,165,0,0.2)',
            line=dict(color='rgba(255,255,255,0)'),
            hoverinfo="skip",
            name='Prophet Tahmin Aralığı'
        ))
        fig.add_trace(go.Scatter(
            x=arima_series.index, y=arima_series.values,
            mode='lines',
            name='ARIMA Tahmini',
            line=dict(color='green', dash='dot')
        ))

        fig.update_layout(
            title=f"📈 {product_name} – Prophet vs ARIMA Tahmini",
            xaxis_title="Tarih",
            yaxis_title="Satış Adedi",
            legend=dict(x=0.01, y=0.99),
            template="plotly_white"
        )

        fig.add_annotation(
            text=f"Prophet - MAE: {mae_prophet:.2f} | RMSE: {rmse_prophet:.2f}",
            xref="paper", yref="paper",
            x=1, y=1.13, showarrow=False,
            bgcolor="lightblue", bordercolor="blue", borderwidth=1
        )
        fig.add_annotation(
            text=f"ARIMA - MAE: {mae_arima:.2f} | RMSE: {rmse_arima:.2f}",
            xref="paper", yref="paper",
            x=1, y=1.06, showarrow=False,
            bgcolor="lightgreen", bordercolor="green", borderwidth=1
        )

        return df_prophet, forecast, mae_prophet, rmse_prophet, mae_arima, rmse_arima, fig

    except Exception as e:
        print(f"[forecasting] Hata: {e}")
        return None, None, None, None, None, None, None
