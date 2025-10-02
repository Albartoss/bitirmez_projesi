import sqlite3
import pandas as pd
import os
from modules.config import DB_PATH

PRODUCTS_CSV = "data/products.csv"
SALES_CSV = "data/sales.csv"
DB_FILE = "database/inventory.db"

conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS products (
    product_id INTEGER PRIMARY KEY,
    product_name TEXT NOT NULL,
    brand TEXT,
    category TEXT,
    cost_price REAL,
    selling_price REAL,
    expiry_date TEXT,
    discount_price REAL,         -- ✅ kampanya fiyatı
    discount_until TEXT          -- ✅ kampanya bitiş tarihi
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    product_id INTEGER,
    quantity_sold INTEGER,
    FOREIGN KEY (product_id) REFERENCES products (product_id)
)
""")

cursor.execute("DROP TABLE IF EXISTS stock_transactions")
cursor.execute("""
CREATE TABLE stock_transactions (
    transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER,
    date TEXT,
    quantity INTEGER,
    note TEXT,
    expiry_date TEXT,
    FOREIGN KEY (product_id) REFERENCES products(product_id)
)
""")

if os.path.exists(PRODUCTS_CSV):
    df_products = pd.read_csv(PRODUCTS_CSV)
    expected_cols = [
        "product_id", "product_name", "brand", "category",
        "cost_price", "selling_price", "expiry_date", "discount_price", "discount_until"
    ]
    for col in expected_cols:
        if col not in df_products.columns:
            df_products[col] = None
    df_products = df_products[expected_cols]
    df_products.to_sql("products", conn, if_exists="replace", index=False)

if os.path.exists(SALES_CSV):
    df_sales = pd.read_csv(SALES_CSV)
    df_sales.to_sql("sales", conn, if_exists="replace", index=False)

print("Veritabanı başarıyla oluşturuldu veya güncellendi.")
conn.commit()
conn.close()
