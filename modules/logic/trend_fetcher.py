import requests
import pandas as pd
import time
import random
import json
import os
from datetime import datetime, timedelta

class GoogleTrendsFetcher:
    def __init__(self, geo='TR', gprop='froogle', cache_path='trend_cache.json', ttl_hours=24, serpapi_key=None):
        self.geo = geo
        self.gprop = gprop
        self.cache_path = cache_path
        self.ttl = timedelta(hours=ttl_hours)
        self.cache = self._load_cache()
        self.api_key = serpapi_key or os.getenv("SERPAPI_KEY")

    def _load_cache(self):
        if os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, 'r', encoding='utf-8') as f:
                    raw = json.load(f)
                    return {
                        k: {
                            'score': v['score'],
                            'timestamp': datetime.fromisoformat(v['timestamp'])
                        } for k, v in raw.items()
                    }
            except Exception as e:
                print(f"Önbellek okunamadı: {e}")
        return {}

    def _save_cache(self):
        try:
            with open(self.cache_path, 'w', encoding='utf-8') as f:
                json.dump({
                    k: {
                        'score': v['score'],
                        'timestamp': v['timestamp'].isoformat()
                    } for k, v in self.cache.items()
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Önbellek kaydedilemedi: {e}")

    def get_trend_score(self, keyword):
        if keyword in self.cache:
            cached = self.cache[keyword]
            if cached['score'] > 0 and datetime.now() - cached['timestamp'] < self.ttl:
                return cached['score']

        if not self.api_key:
            print("SerpAPI anahtarı bulunamadı.")
            return 0.0

        try:
            params = {
                "engine": "google_trends",
                "q": keyword,
                "geo": self.geo,
                "gprop": self.gprop,
                "api_key": self.api_key
            }
            response = requests.get("https://serpapi.com/search", params=params)
            data = response.json()

            points = data.get("interest_over_time", [])
            if not points:
                print(f"Trend verisi yok: {keyword}")
                return 0.0

            avg = sum(p.get("value", 0) for p in points) / len(points)
            score = round(avg, 2)
            self.cache[keyword] = {
                'score': score,
                'timestamp': datetime.now()
            }
            self._save_cache()
            return score

        except Exception as e:
            print(f"Trend alınamadı: {keyword} | Hata: {e}")
            return 0.0

    def get_trend_scores_bulk(self, keywords):
        trend_scores = {}
        for word in keywords:
            score = self.get_trend_score(word)
            trend_scores[word] = score
            time.sleep(random.uniform(6, 12))
        return trend_scores

if __name__ == "__main__":
    fetcher = GoogleTrendsFetcher(serpapi_key="YOUR_API_KEY")
    keywords = ["kola", "fanta", "ayran", "enerji içeceği"]
    results = fetcher.get_trend_scores_bulk(keywords)
    for k, v in results.items():
        print(f"{k}: {v}")
