import sqlite3
import pandas as pd
import os
from modules.config import DB_PATH

DB_FILE = DB_PATH

conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()

cursor.execute("SELECT * FROM stock_transactions")
rows = cursor.fetchall()
print(f"Toplam {len(rows)} stok hareketi bulundu.")
for row in rows[:10]:
    print(row)

df_products = pd.read_sql_query("SELECT * FROM products", conn)

df_sales = pd.read_sql_query("SELECT product_id, quantity_sold FROM sales", conn)
df_sales_sum = df_sales.groupby("product_id")["quantity_sold"].sum().reset_index()
df_sales_sum.columns = ["product_id", "total_sold"]

df_stock = pd.read_sql_query("SELECT product_id, quantity FROM stock_transactions", conn)
df_stock_sum = df_stock.groupby("product_id")["quantity"].sum().reset_index()
df_stock_sum.columns = ["product_id", "total_stock"]

df_merged = pd.merge(df_products, df_sales_sum, on="product_id", how="left")
df_merged = pd.merge(df_merged, df_stock_sum, on="product_id", how="left")
df_merged = df_merged.fillna(0)

df_merged["current_stock"] = df_merged["total_stock"] - df_merged["total_sold"]

df_merged["profit_per_unit"] = df_merged["selling_price"] - df_merged["cost_price"]
df_merged["total_profit"] = df_merged["profit_per_unit"] * df_merged["total_sold"]

total_sales = int(df_merged["total_sold"].sum())
top_seller = df_merged.loc[df_merged["total_sold"].idxmax(), "product_name"]
most_profitable = df_merged.loc[df_merged["total_profit"].idxmax(), "product_name"]

print(f"Toplam Satış Adedi: {total_sales}")
print(f"En Çok Satan Ürün: {top_seller}")
print(f"En Kârlı Ürün: {most_profitable}")

conn.close()
