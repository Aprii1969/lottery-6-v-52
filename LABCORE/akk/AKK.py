import pandas as pd
import json
import os
import datetime
import numpy as np # Добавляем импорт numpy для np.mean

# Импортируем из нового вспомогательного модуля
from utils.json_utils import load_json_config, save_json_config

# Используем относительный импорт, так как module_back.py находится в той же папке 'akk'
from .module_back import ReverseAnalysis

# Предполагается, что эти пути будут относительно корневой директории LABCORE
CONFIG_DIR = "config"
REPORTS_DIR = "reports"
AKK_REPORTS_DIR = os.path.join(REPORTS_DIR, "AKK_Reports")
CORE_SETTINGS_FILE = os.path.join(CONFIG_DIR, "core_settings.json")

# Файлы настроек для контуров A и B
LABCORE_A_SETTINGS_FILE = os.path.join(CONFIG_DIR, "labcore_A_settings.json")
LABCORE_B_SETTINGS_FILE = os.path.join(CONFIG_DIR, "labcore_B_settings.json")

class AKK:
    def __init__(self, config_path, project_root_dir):
        self.config_path = config_path
        self.project_root_dir = project_root_dir
        self.config = load_json_config(self.config_path) # Используем новую надежную функцию
        self.adjustment_history = self.config.get("adjustment_history", [])
        
        self.min_5_plus_threshold = self.config.get("min_5_plus_threshold", 1)
        self.adjustment_strength = self.config.get("adjustment_strength", 0.05)
        
        self.target_5_match_percentage = self.config.get("target_5_match_percentage", 0.80)
        self.min_5_match_percentage = self.config.get("min_5_match_percentage", 0.15)
        self.target_6_match_percentage = self.config.get("target_6_match_percentage", 0.40)
        self.min_6_match_percentage = self.config.get("min_6_match_percentage", 0.02)

        self.reports_dir = os.path.join(self.project_root_dir, AKK_REPORTS_DIR)
        os.makedirs(self.reports_dir, exist_ok=True)

    def _save_config(self): # Без аргумента, использует self.config_path и self.config
        save_json_config(self.config_path, self.config) # Используем save_json_config

    def _load_core_settings(self):
        return load_json_config(os.path.join(self.project_root_dir, CORE_SETTINGS_FILE))

    def _save_core_settings(self, settings):
        save_json_config(os.path.join(self.project_root_dir, CORE_SETTINGS_FILE), settings)

    def _load_a_settings(self):
        return load_json_config(os.path.join(self.project_root_dir, LABCORE_A_SETTINGS_FILE))

    def _save_a_settings(self, settings):
        save_json_config(os.path.join(self.project_root_dir, LABCORE_A_SETTINGS_FILE), settings)

    def _load_b_settings(self):
        return load_json_config(os.path.join(self.project_root_dir, LABCORE_B_SETTINGS_FILE))

    def _save_b_settings(self, settings):
        save_json_config(os.path.join(self.project_root_dir, LABCORE_B_SETTINGS_FILE), settings)

    def analyze_performance_and_adjust(self, draw_number, performance_metrics, history_performance_metrics=None):
        """
        Анализирует производительность и принимает решение о корректировке.
        history_performance_metrics: Список словарей метрик за последние тиражи для Контура A.
        """
        print(f"АКК: Анализ производительности для тиража №{draw_number} (АКК проверяет).")
        
        match_5_plus_count = performance_metrics.get("match_5_plus_count", 0)
        total_combinations = performance_metrics.get("total_combinations", 1)
        match_6_count = performance_metrics.get("match_6_count", 0)

        current_5_match_percentage = (match_5_plus_count / total_combinations) if total_combinations > 0 else 0
        current_6_match_percentage = (match_6_count / total_combinations) if total_combinations > 0 else 0

        adjustment_made = False
        recommendation = "Нет необходимости в корректировке."
        report_lines = []
        report_lines.append(f"АКК Отчет для тиража №{draw_number}")
        report_lines.append(f"Дата анализа: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"Общее количество сгенерированных комбинаций: {total_combinations}")
        report_lines.append(f"Количество 5+ совпадений: {match_5_plus_count} ({current_5_match_percentage:.2%})") 
        report_lines.append(f"Количество 6 совпадений: {match_6_count} ({current_6_match_percentage:.2%})")
        report_lines.append("-" * 30)
        report_lines.append(f"Целевой % для 5+ совпадений: {self.target_5_match_percentage:.2%}")
        report_lines.append(f"Минимальный % для 5+ совпадений: {self.min_5_match_percentage:.2%}")
        report_lines.append(f"Целевой % для 6 совпадений: {self.target_6_match_percentage:.2%}")
        report_lines.append(f"Минимальный % для 6 совпадений: {self.min_6_match_percentage:.2%}")
        report_lines.append("-" * 30)

        core_settings = self._load_core_settings()
        current_boost = core_settings.get("boost", 2.6)
        report_lines.append(f"Текущий Core Boost: {current_boost}")

        a_settings = self._load_a_settings()
        b_settings = self._load_b_settings()
        
        # --- Логика корректировки для Контура A (Stable) - по средним за 30 тиражей ---
        if history_performance_metrics:
            history_5_plus_percentages = [
                (m.get('match_5_plus_count', 0) / m.get('total_combinations', 1)) 
                for m in history_performance_metrics if m.get('total_combinations', 0) > 0
            ]
            avg_history_5_plus_percent = np.mean(history_5_plus_percentages) if history_5_plus_percentages else 0

            report_lines.append(f"Средний % 5+ за последние {len(history_performance_metrics)} тиражей: {avg_history_5_plus_percent:.2%}")

            if avg_history_5_plus_percent < self.min_5_match_percentage:
                old_temp_A = a_settings.get("temperature", 0.7)
                a_settings["temperature"] = round(min(1.0, old_temp_A + 0.1), 2)
                self._save_a_settings(a_settings)
                recommendation_A = f"Stable (Контур A): Средний % 5+ ({avg_history_5_plus_percent:.2%}) ниже минимума ({self.min_5_match_percentage:.2%}). Увеличена Temperature Контура A до {a_settings['temperature']}."
                report_lines.append(f"АКК (Stable): {recommendation_A}")
                adjustment_made = True
            elif avg_history_5_plus_percent < self.target_5_match_percentage:
                new_boost_A = current_boost + (self.adjustment_strength / 4)
                core_settings["boost"] = round(new_boost_A, 2)
                self._save_core_settings(core_settings)
                recommendation_A = f"Stable (Контур A): Средний % 5+ ({avg_history_5_plus_percent:.2%}) ниже цели ({self.target_5_match_percentage:.2%}). Core Boost скорректирован до {new_boost_A:.2f}."
                report_lines.append(f"АКК (Stable): {recommendation_A}")
                adjustment_made = True
        
        if current_6_match_percentage < self.min_6_match_percentage:
            old_aggr_B = b_settings.get("aggressiveness", 1.5)
            b_settings["aggressiveness"] = round(old_aggr_B + 0.2, 2)
            self._save_b_settings(b_settings)
            recommendation_B = f"Experimental (Контур B): % 6 попаданий ({current_6_match_percentage:.2%}) НИЖЕ МИНИМУМА ({self.min_6_match_percentage:.2%}). Увеличена Aggressiveness Контура B до {b_settings['aggressiveness']}."
            report_lines.append(f"АКК (Experimental): {recommendation_B}")
            adjustment_made = True
        elif current_6_match_percentage < self.target_6_match_percentage and current_5_match_percentage >= self.min_5_match_percentage:
            old_expl_B = b_settings.get("exploratory_factor", 0.2)
            b_settings["exploratory_factor"] = round(min(0.5, old_expl_B + 0.05), 2)
            self._save_b_settings(b_settings)
            recommendation_B = f"Experimental (Контур B): % 6 попаданий ({current_6_match_percentage:.2%}) НИЖЕ ЦЕЛИ ({self.target_6_match_percentage:.2%}). Увеличен Exploratory Factor Контура B до {b_settings['exploratory_factor']}."
            report_lines.append(f"АКК (Experimental): {recommendation_B}")
            adjustment_made = True
        elif current_5_match_percentage >= self.target_5_match_percentage and current_6_match_percentage >= self.target_6_match_percentage:
            recommendation = "Все целевые показатели достигнуты. Корректировка не требуется."
            report_lines.append(f"АКК: {recommendation}")
            adjustment_made = False

        if adjustment_made:
            self.adjustment_history.append({
                "draw_number": draw_number,
                "timestamp": datetime.datetime.now().isoformat(),
                "old_boost": round(current_boost, 2),
                "new_boost": core_settings.get("boost"),
                "reason": recommendation,
                "performance_5_plus_percent": f"{current_5_match_percentage:.2%}",
                "performance_6_percent": f"{current_6_match_percentage:.2%}"
            })
            self.config["adjustment_history"] = self.adjustment_history
            self._save_config()

        print(f"АКК: Анализ завершен. Рекомендация: {recommendation}")
        
        report_filename = os.path.join(self.reports_dir, f"AKK_report_draw_{draw_number}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
        with open(report_filename, 'w', encoding='utf-8') as f:
            f.write("\n".join(report_lines))
        print(f"АКК: Отчет сохранен в {report_filename}")

        return recommendation, adjustment_made