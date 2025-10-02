import sqlite3
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.io as pio
import os
from datetime import datetime
from prophet import Prophet
from modules.config import DB_PATH

conn = sqlite3.connect(DB_PATH)
df_sales = pd.read_sql_query("SELECT date, product_id, quantity_sold FROM sales", conn)
df_products = pd.read_sql_query("SELECT * FROM products", conn)
df_stock = pd.read_sql_query("SELECT product_id, quantity FROM stock_transactions", conn)
df_links = pd.read_sql_query("SELECT * FROM product_storage_links", conn)
df_shelves = pd.read_sql_query("SELECT id, max_capacity FROM shelves", conn)
df_fridges = pd.read_sql_query("SELECT id, max_capacity FROM fridges", conn)
conn.close()

today = pd.Timestamp.today()
df_sales["date"] = pd.to_datetime(df_sales["date"], errors="coerce")
df_products["discount_until"] = pd.to_datetime(df_products["discount_until"], errors="coerce")

df_daily = df_sales.groupby("date")["quantity_sold"].sum().reset_index()
df_prophet = df_daily.rename(columns={"date": "ds", "quantity_sold": "y"})

model = Prophet(daily_seasonality=True, interval_width=0.6)
model.fit(df_prophet)

future = model.make_future_dataframe(periods=30)
forecast = model.predict(future)
forecast_30 = forecast[(forecast["ds"] > df_prophet["ds"].max()) & (forecast["ds"] <= today + pd.Timedelta(days=30))]
total_forecast_qty = forecast_30["yhat"].sum()

df_sales_sum = df_sales.groupby("product_id")["quantity_sold"].sum().reset_index()
df_stock_sum = df_stock.groupby("product_id")["quantity"].sum().reset_index()

df_summary = pd.merge(df_products, df_sales_sum, on="product_id", how="left").fillna(0).infer_objects()
df_summary = pd.merge(df_summary, df_stock_sum, on="product_id", how="left").fillna(0).infer_objects()
df_summary = pd.merge(df_summary, df_links, on="product_id", how="left")
df_summary["current_stock"] = df_summary["quantity"] - df_summary["quantity_sold"]

mask = (
    pd.notna(df_summary["discount_price"]) &
    pd.notna(df_summary["discount_until"]) &
    (df_summary["discount_until"] >= today)
)
df_summary["effective_price"] = df_summary["selling_price"]
df_summary.loc[mask, "effective_price"] = df_summary.loc[mask, "discount_price"]

for col in ["effective_price", "cost_price", "quantity_sold", "quantity", "unit_volume"]:
    df_summary[col] = pd.to_numeric(df_summary[col], errors="coerce").fillna(1.0 if col == "unit_volume" else 0.0)

df_summary["weight"] = df_summary["quantity_sold"] / df_summary["quantity_sold"].sum()
df_summary["forecasted_qty"] = df_summary["weight"] * total_forecast_qty
df_summary["shortage"] = (df_summary["forecasted_qty"] - df_summary["current_stock"]).apply(lambda x: x if x > 0 else 0)

df_summary["potential_revenue"] = df_summary["forecasted_qty"] * df_summary["effective_price"]
df_summary["potential_cost"] = df_summary["forecasted_qty"] * df_summary["cost_price"]
df_summary["potential_profit"] = df_summary["potential_revenue"] - df_summary["potential_cost"]

def get_capacity(row):
    try:
        if row["storage_type"] == "shelf":
            return df_shelves[df_shelves["id"] == row["storage_id"]]["max_capacity"].values[0]
        elif row["storage_type"] == "fridge":
            return df_fridges[df_fridges["id"] == row["storage_id"]]["max_capacity"].values[0]
    except:
        return None

df_summary["storage_capacity"] = df_summary.apply(get_capacity, axis=1)
df_summary["projected_volume"] = df_summary["forecasted_qty"] * df_summary["unit_volume"]
df_summary["volume_overload"] = df_summary.apply(
    lambda row: row["projected_volume"] > row["storage_capacity"] if pd.notna(row["storage_capacity"]) else False,
    axis=1
)

total_profit = df_summary["potential_profit"].sum()
total_revenue = df_summary["potential_revenue"].sum()
total_shortage = df_summary["shortage"].sum()
critical_items = df_summary[df_summary["shortage"] > 0]
volume_issues = df_summary[df_summary["volume_overload"] == True]

fig = go.Figure()

fig.add_trace(go.Scatter(
    x=df_prophet["ds"], y=df_prophet["y"],
    mode='lines+markers',
    name='Gerçek Satış',
    line=dict(color='royalblue')
))

fig.add_trace(go.Scatter(
    x=forecast_30["ds"], y=forecast_30["yhat"],
    mode='lines',
    name='Tahmin (30 Gün)',
    line=dict(color='darkorange', dash='dash')
))

fig.add_trace(go.Scatter(
    x=forecast_30["ds"].tolist() + forecast_30["ds"][::-1].tolist(),
    y=forecast_30["yhat_upper"].tolist() + forecast_30["yhat_lower"][::-1].tolist(),
    fill='toself',
    fillcolor='rgba(255,165,0,0.2)',
    line=dict(color='rgba(255,255,255,0)'),
    hoverinfo="skip",
    name='Tahmin Aralığı'
))

if not critical_items.empty:
    warning_text = "<br>".join(
        f"{row['product_name']}: {int(row['shortage'])} eksik"
        for _, row in critical_items.iterrows()
    )
    fig.add_annotation(
        text=f"⚠️ Kritik Ürünler:<br>{warning_text}",
        xref="paper", yref="paper",
        x=1, y=0.1, showarrow=False,
        bgcolor="lightyellow", bordercolor="red", borderwidth=1
    )

if not volume_issues.empty:
    overflow_text = "<br>".join(
        f"{row['product_name']} → Kapasite aşımı"
        for _, row in volume_issues.iterrows()
    )
    fig.add_annotation(
        text=f"📦 Depo Yetersizliği:<br>{overflow_text}",
        xref="paper", yref="paper",
        x=1, y=0, showarrow=False,
        bgcolor="mistyrose", bordercolor="darkred", borderwidth=1
    )

fig.update_layout(
    title="📈 Toplam Satış Tahmini – Gelecek 30 Gün",
    xaxis_title="Tarih",
    yaxis_title="Satış Adedi",
    legend=dict(x=0.01, y=0.99),
    template="plotly_white"
)

html_path = os.path.join(os.getcwd(), "forecast_plot.html")
pio.write_html(fig, file=html_path, auto_open=False)

print("30 Günlük Tahmin:")
print(f"  • Beklenen Toplam Satış: {total_forecast_qty:.0f} adet")
print(f"  • Beklenen Gelir: {total_revenue:.2f} TL")
print(f"  • Beklenen Kâr: {total_profit:.2f} TL")
print(f"  • Stok Yetersiz Ürün Sayısı: {len(critical_items)} ürün")
print(f"  • Toplam Açık Miktar: {total_shortage:.0f} adet")
print(f"  • Kapasite Aşımı Olası Ürün Sayısı: {len(volume_issues)}")
print(f"<<HTML_PATH>>{html_path}<<END>>")
