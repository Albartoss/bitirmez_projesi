import json
import os

class Translator:
    _instance = None  

    def __new__(cls, lang_code="tr"):
        if cls._instance is None:
            cls._instance = super(Translator, cls).__new__(cls)
            cls._instance.lang_code = lang_code
            cls._instance.translations = {}
            cls._instance.load_language()
            cls._instance.currency_symbol = "₺"
        return cls._instance

    def load_language(self):
        file_path = os.path.join(os.path.dirname(__file__), f"{self.lang_code}.json")
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                self.translations = json.load(f)
        except FileNotFoundError:
            print(f"[Dil] {self.lang_code}.json bulunamadı.")
            self.translations = {}

    def set_language(self, lang_code):
        self.lang_code = lang_code
        self.load_language()
        if lang_code == "tr":
            self.currency_symbol = "₺"
        elif lang_code == "en":
            self.currency_symbol = "€"
        elif lang_code == "uk":
            self.currency_symbol = "₴"
        else:
            self.currency_symbol = "¤"  # Bilinmeyen para birimi

    def tr(self, key):
        return self.translations.get(key, key)

    def __call__(self, key: str, **kwargs):
        text = self.tr(key)
        return text.format(**kwargs) if kwargs else text

    def translate(self, key, **kwargs): 
        text = self.tr(key)
        return text.format(**kwargs) if kwargs else text

translator = Translator()
