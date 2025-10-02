import sqlite3
import pandas as pd
from prophet import Prophet
import os
from modules.config import DB_PATH
from datetime import datetime
from modules.logic.trend_fetcher import GoogleTrendsFetcher
from unidecode import unidecode
import geocoder

class InventoryForecastAssistant:
    def __init__(self, enable_trends=False):
        self.conn = sqlite3.connect(DB_PATH)
        self.today = datetime.today().date()
        self.trends_enabled = enable_trends
        self.geo_region = 'TR'

        try:
            g = geocoder.ip('me')
            if g.ok:
                city = g.city
                plaka_map = {
                    'Adana': 'TR-01', 'Adıyaman': 'TR-02', 'Afyonkarahisar': 'TR-03',
                    'Ağrı': 'TR-04', 'Amasya': 'TR-05', 'Ankara': 'TR-06', 'Antalya': 'TR-07',
                    'Artvin': 'TR-08', 'Aydın': 'TR-09', 'Balıkesir': 'TR-10', 'Bursa': 'TR-16',
                    'Denizli': 'TR-20', 'Erzurum': 'TR-25', 'Eskişehir': 'TR-26',
                    'Gaziantep': 'TR-27', 'Hatay': 'TR-31', 'Isparta': 'TR-32', 'İstanbul': 'TR-34',
                    'İzmir': 'TR-35', 'Kahramanmaraş': 'TR-46', 'Kayseri': 'TR-38', 'Kocaeli': 'TR-41',
                    'Konya': 'TR-42', 'Malatya': 'TR-44', 'Manisa': 'TR-45', 'Mersin': 'TR-33',
                    'Muğla': 'TR-48', 'Ordu': 'TR-52', 'Sakarya': 'TR-54', 'Samsun': 'TR-55',
                    'Şanlıurfa': 'TR-63', 'Tekirdağ': 'TR-59', 'Trabzon': 'TR-61', 'Van': 'TR-65'
                }
                self.geo_region = plaka_map.get(city, 'TR')
        except:
            pass

        if self.trends_enabled:
            try:
                self.trend_fetcher = GoogleTrendsFetcher(geo=self.geo_region, gprop='froogle')
            except:
                self.trends_enabled = False

    def get_sales_data(self):
        query = "SELECT product_id, date, quantity_sold FROM sales"
        df = pd.read_sql_query(query, self.conn)
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        return df.dropna()

    def get_stock_data(self):
        query = """
        SELECT product_id, SUM(quantity) AS stock
        FROM stock_transactions
        GROUP BY product_id
        """
        return pd.read_sql_query(query, self.conn)

    def get_product_names(self):
        query = "SELECT product_id, product_name, brand FROM products"
        return pd.read_sql_query(query, self.conn)

    def forecast_product(self, df_product):
        df = df_product.groupby("date")["quantity_sold"].sum().reset_index()
        df = df.rename(columns={"date": "ds", "quantity_sold": "y"})
        if len(df) < 5:
            return None
        model = Prophet()
        model.fit(df)
        future = model.make_future_dataframe(periods=7)
        forecast = model.predict(future)
        return forecast[["ds", "yhat"]].tail(7)

    def detect_slow_moving(self, avg_daily):
        return avg_daily < 0.3

    def run_analysis(self):
        df_sales = self.get_sales_data()
        df_stock = self.get_stock_data()
        df_names = self.get_product_names()

        results = []
        grouped = df_sales.groupby("product_id")

        for pid, group in grouped:
            forecast = self.forecast_product(group)
            if forecast is None:
                continue

            avg_forecast = forecast["yhat"].mean()

            product_info = df_names[df_names["product_id"] == pid].iloc[0]
            pname = product_info["product_name"]
            brand = product_info["brand"]
            search_query = unidecode(f"{brand} {pname}")

            trend_multiplier = 1.0
            if self.trends_enabled:
                try:
                    trend_score = self.trend_fetcher.get_trend_score(search_query)
                    trend_multiplier += trend_score / 100
                except Exception as e:
                    print(f"Trend alınamadı: {search_query} | Hata: {e}")
            else:
                print(f"Uyarı: Trend desteği devre dışı -> {search_query}")

            adjusted_forecast = avg_forecast * trend_multiplier

            stock_row = df_stock[df_stock["product_id"] == pid]
            stock = stock_row["stock"].values[0] if not stock_row.empty else 0
            days_left = stock / adjusted_forecast if adjusted_forecast > 0 else float("inf")

            results.append({
                "product_id": pid,
                "product_name": pname,
                "stock": stock,
                "forecast_avg": round(adjusted_forecast, 2),
                "days_to_depletion": round(days_left, 1),
                "is_slow": self.detect_slow_moving(adjusted_forecast)
            })

        return results

    def update_trend_scores(self):
        if not self.trends_enabled:
            try:
                self.trend_fetcher = GoogleTrendsFetcher(geo=self.geo_region, gprop='froogle')
                self.trends_enabled = True
                print("Trends yeniden etkinleştirildi.")
            except Exception as e:
                print(f"Trend API başlatılamadı: {e}")

        if not self.trends_enabled:
            print("Trend sistemi kullanılamıyor.")
            return

        df_names = self.get_product_names()
        for _, row in df_names.iterrows():
            search_query = unidecode(f"{row['brand']} {row['product_name']}")
            try:
                score = self.trend_fetcher.get_trend_score(search_query)
                print(f"{search_query} → Trend skoru: {score}")
            except Exception as e:
                print(f"Trend çekilemedi: {search_query} | Hata: {e}")

if __name__ == "__main__":
    assistant = InventoryForecastAssistant(enable_trends=False)
    report = assistant.run_analysis()
    for r in report:
        print(r)
    print("--- İsteğe bağlı SerpAPI trend güncellemesi başlatılıyor...")
    assistant.update_trend_scores()
