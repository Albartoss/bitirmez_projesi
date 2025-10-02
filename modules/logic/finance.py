import sqlite3
import pandas as pd

from modules.config import DB_PATH

def get_profit_report():
    try:
        conn = sqlite3.connect(DB_PATH)
        df_sales = pd.read_sql_query("SELECT * FROM sales", conn)
        df_products = pd.read_sql_query("SELECT * FROM products", conn)
        conn.close()

        df_merged = pd.merge(df_sales, df_products, on="product_id")
        grouped = df_merged.groupby("product_name")

        report = []
        for name, group in grouped:
            total_qty = group["quantity_sold"].sum()
            revenue = (group["quantity_sold"] * group["selling_price"]).sum()
            cost = (group["quantity_sold"] * group["cost_price"]).sum()
            profit = revenue - cost

            report.append({
                "Product": name,
                "Quantity Sold": total_qty,
                "Revenue": revenue,
                "Cost": cost,
                "Profit": profit
            })

        return report
    except Exception as e:
        print(f"[finance] Hata: {e}")
        return []
