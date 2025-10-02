import sqlite3
import pandas as pd
from datetime import datetime
from modules.config import DB_PATH

def get_shelf_placement_suggestions():
    conn = sqlite3.connect(DB_PATH)

    products = pd.read_sql_query("SELECT product_id, product_name FROM products", conn)
    sales = pd.read_sql_query("SELECT product_id, quantity_sold, date FROM sales", conn)
    stock = pd.read_sql_query("SELECT product_id, expiry_date FROM stock_transactions WHERE expiry_date IS NOT NULL", conn)

    conn.close()

    stock["expiry_date"] = pd.to_datetime(stock["expiry_date"], errors="coerce")
    sales["date"] = pd.to_datetime(sales["date"], errors="coerce")
    today = pd.Timestamp.today()

    stock_valid = stock.dropna()
    soonest_expiry = stock_valid.groupby("product_id")["expiry_date"].min().reset_index()

    recent_sales = sales[sales["date"] >= today - pd.Timedelta(days=30)]
    avg_sales = recent_sales.groupby("product_id")["quantity_sold"].mean().reset_index()
    avg_sales.columns = ["product_id", "daily_avg"]

    df = products.copy()
    df = pd.merge(df, avg_sales, on="product_id", how="left")
    df = pd.merge(df, soonest_expiry, on="product_id", how="left")
    df["daily_avg"] = df["daily_avg"].fillna(0)
    df["days_to_expiry"] = (df["expiry_date"] - today).dt.days

    def classify(row):
        if pd.isna(row["days_to_expiry"]):
            return "Normal Raf"
        if row["days_to_expiry"] <= 7 and row["daily_avg"] < 1:
            return "⚠️ Ön Raf (SKT Yakın & Az Satıyor)"
        elif row["days_to_expiry"] <= 7:
            return "Ön Raf (SKT Yakın)"
        elif row["daily_avg"] < 1:
            return "Alt Raf (Az Satıyor)"
        else:
            return "Normal Raf"

    df["suggested_placement"] = df.apply(classify, axis=1)
    return df[["product_name", "days_to_expiry", "daily_avg", "suggested_placement"]]


if __name__ == "__main__":
    result = get_shelf_placement_suggestions()
    print(result.to_string(index=False))
