import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from modules.config import DB_PATH
from modules.lang.translator import translator

class AISuggestionEngine:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH)
        self.today = pd.Timestamp.today()

    def get_dataframes(self):
        products = pd.read_sql_query("SELECT * FROM products", self.conn)
        sales = pd.read_sql_query("SELECT * FROM sales", self.conn)
        stock = pd.read_sql_query("SELECT * FROM stock_transactions", self.conn)
        links = pd.read_sql_query("SELECT * FROM product_storage_links", self.conn)
        fridges = pd.read_sql_query("SELECT id, max_capacity FROM fridges", self.conn)
        shelves = pd.read_sql_query("SELECT id, max_capacity FROM shelves", self.conn)

        sales['date'] = pd.to_datetime(sales['date'], errors='coerce')
        stock['expiry_date'] = pd.to_datetime(stock['expiry_date'], errors='coerce')
        return products, sales, stock, links, fridges, shelves

    def detect_slow_moving(self, avg_daily):
        return avg_daily < 0.3

    def analyze(self):
        products, sales, stock, links, fridges, shelves = self.get_dataframes()
        results = []

        span = max((self.today - sales['date'].min()).days, 1)
        sale_totals = sales.groupby('product_id')['quantity_sold'].sum().reset_index()
        sale_totals['daily_avg'] = sale_totals['quantity_sold'] / span

        expiry = stock.dropna(subset=['expiry_date'])
        earliest_expiry = expiry.groupby('product_id')['expiry_date'].min().reset_index()
        earliest_expiry.columns = ['product_id', 'earliest_expiry']

        recent_sales = sales[sales["date"] >= self.today - timedelta(days=30)]
        avg_recent = recent_sales.groupby("product_id")["quantity_sold"].mean().reset_index()
        avg_recent.columns = ["product_id", "daily_avg_recent"]

        stock_total = stock.groupby('product_id')['quantity'].sum().reset_index()
        stock_total.columns = ['product_id', 'stock']

        df = pd.merge(products, sale_totals[['product_id', 'daily_avg']], on='product_id', how='left').fillna(0)
        df = pd.merge(df, avg_recent, on='product_id', how='left').fillna(0)
        df = pd.merge(df, earliest_expiry, on='product_id', how='left')
        df = pd.merge(df, stock_total, on='product_id', how='left').fillna(0)
        df = pd.merge(df, links, on='product_id', how='left')

        for _, row in df.iterrows():
            suggestions = []
            pid = row["product_id"]
            pname = row["product_name"]
            avg = row["daily_avg"]
            avg_recent = row["daily_avg_recent"]
            expiry = row["earliest_expiry"]
            stock_amt = row["stock"]
            volume = row.get("unit_volume", 1)
            storage_type = row.get("storage_type", None)
            storage_id = row.get("storage_id", None)

            if self.detect_slow_moving(avg):
                suggestions.append(translator("ai.slow_selling_general"))

            if isinstance(expiry, pd.Timestamp) and pd.notna(expiry):
                days_left = (expiry - self.today).days
                if days_left <= 10:
                    if self.detect_slow_moving(avg):
                        suggestions.append(translator("ai.expiring_and_slow"))
                    else:
                        suggestions.append(translator("ai.expiring_discount"))

            if avg == 0 and stock_amt > 0:
                suggestions.append(translator("ai.unsold_with_stock"))

            if isinstance(expiry, pd.Timestamp) and pd.notna(expiry):
                try:
                    days_to_exp = (expiry - self.today).days
                    if days_to_exp <= 7 and avg_recent < 1:
                        suggestions.append(translator("ai.front_shelf_critical"))
                    elif days_to_exp <= 7:
                        suggestions.append(translator("ai.front_shelf"))
                    elif avg_recent < 1:
                        suggestions.append(translator("ai.low_demand_shelf"))
                except Exception:
                    pass

            if pd.notna(storage_id) and pd.notna(storage_type):
                max_cap = None
                if storage_type == "fridge":
                    row_cap = fridges[fridges['id'] == storage_id]
                    if not row_cap.empty:
                        max_cap = row_cap["max_capacity"].values[0]
                elif storage_type == "shelf":
                    row_cap = shelves[shelves['id'] == storage_id]
                    if not row_cap.empty:
                        max_cap = row_cap["max_capacity"].values[0]

                if max_cap:
                    used = stock_amt * volume
                    usage_pct = (used / max_cap) * 100
                    if usage_pct >= 90:
                        suggestions.append(translator("ai.capacity_full").format(pct=round(usage_pct, 1)))
                    elif usage_pct < 30:
                        suggestions.append(translator("ai.capacity_low").format(pct=round(usage_pct, 1)))

            if suggestions:
                if isinstance(expiry, pd.Timestamp) and pd.notna(expiry):
                    expiry_str = expiry.strftime('%Y-%m-%d')
                else:
                    expiry_str = translator("common.no_expiry")

                results.append({
                    "product_id": pid,
                    "product_name": pname,
                    "daily_avg": round(avg, 2),
                    "stock": int(stock_amt),
                    "storage_type": storage_type if storage_type else translator("common.unknown"),
                    "storage_id": storage_id if storage_id else "-",
                    "earliest_expiry": expiry_str,
                    "suggestions": suggestions
                })

        return results
