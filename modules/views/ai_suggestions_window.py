from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QTextEdit, QPushButton
from PyQt5.QtCore import Qt
from modules.logic.ml_assistant import InventoryForecastAssistant
from modules.logic.ai_suggestion_engine import AISuggestionEngine
from modules.lang.translator import Translator

class AISuggestionsWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.t = Translator()
        self.setWindowTitle(self.t.tr("ai.title"))
        self.setMinimumSize(700, 550)

        layout = QVBoxLayout()

        self.output_area = QTextEdit()
        self.output_area.setReadOnly(True)
        self.output_area.setStyleSheet("font-size: 11pt;")

        self.analyze_button = QPushButton(self.t.tr("button.calculate_suggestions"))
        self.analyze_button.clicked.connect(self.run_analysis)

        layout.addWidget(QLabel(self.t.tr("ai.description")))
        layout.addWidget(self.analyze_button)
        layout.addWidget(self.output_area)
        self.setLayout(layout)

    def run_analysis(self):
        self.output_area.clear()

        ml_assistant = InventoryForecastAssistant(enable_trends=False)
        forecast_report = ml_assistant.run_analysis()

        forecast_suggestions = []
        if not forecast_report:
            forecast_suggestions.append(self.t.tr("ai.no_data_prophet"))
        else:
            for item in forecast_report:
                name = item["product_name"]
                days = item["days_to_depletion"]
                is_slow = item["is_slow"]
                stock = item["stock"]

                if is_slow:
                    forecast_suggestions.append(self.t.tr("ai.slow_selling").format(name=name))
                elif 0 < days <= 7:
                    forecast_suggestions.append(self.t.tr("ai.restock_needed").format(name=name, days=days))
                elif days > 60:
                    forecast_suggestions.append(self.t.tr("ai.too_much_stock").format(name=name, days=days))

        engine = AISuggestionEngine()
        ops_report = engine.analyze()

        ops_suggestions = []
        if not ops_report:
            ops_suggestions.append(self.t.tr("ai.no_data_operational"))
        else:
            for row in ops_report:
                pname = row["product_name"]
                for suggestion in row["suggestions"]:
                    ops_suggestions.append(self.t.tr("ai.operational").format(name=pname, suggestion=suggestion))

        text = ""
        if forecast_suggestions:
            text += self.t.tr("ai.section_prophet") + "\n" + "\n".join(forecast_suggestions) + "\n\n"
        if ops_suggestions:
            text += self.t.tr("ai.section_operational") + "\n" + "\n".join(ops_suggestions)
        if not text:
            text = self.t.tr("ai.all_good")

        self.output_area.setPlainText(text)
