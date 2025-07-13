import pandas as pd
import json
import os
import datetime
from collections import Counter

# Импортируем из нового вспомогательного модуля
from utils.json_utils import load_json_config, save_json_config

# Предполагается, что эти пути будут относительно корневой директории LABCORE
GENERATED_DIR = "generated"
REPORTS_DIR = "reports"
REVERSE_ANALYSIS_REPORTS_DIR = os.path.join(REPORTS_DIR, "Reverse_Analysis_Reports")

class ReverseAnalysis:
    def __init__(self, config_reverse_path, project_root_dir):
        self.project_root_dir = project_root_dir
        self.config_reverse_path = config_reverse_path
        self.config = load_json_config(self.config_reverse_path) # Используем новую надежную функцию

    def _save_config(self): # Без аргумента, использует self.config_reverse_path и self.config
        save_json_config(self.config_reverse_path, self.config) # Используем save_json_config

    def analyze_failed_generation(self, draw_number, failed_combinations_filepath, winning_numbers):
        print(f"ReverseAnalysis: Starting analysis for failed generations for draw {draw_number}...")
        
        if not os.path.exists(failed_combinations_filepath):
            print(f"ReverseAnalysis: Failed combinations file not found: {failed_combinations_filepath}")
            return "File not found."

        try:
            failed_df = pd.read_csv(failed_combinations_filepath, encoding="utf-8-sig")
            winning_set = set(winning_numbers)

            analysis_results = {
                "draw_number": draw_number,
                "analysis_timestamp": datetime.datetime.now().isoformat(),
                "winning_numbers": winning_numbers,
                "total_failed_combinations": len(failed_df),
                "match_counts": {str(i): 0 for i in range(7)},
                "common_missing_numbers": {},
                "common_extra_numbers": {}
            }

            all_generated_numbers = []
            for index, row in failed_df.iterrows():
                generated_combination = [row[f'N{i}'] for i in range(1, 7) if pd.notna(row[f'N{i}'])]
                generated_set = set(generated_combination)
                
                num_matches = len(generated_set & winning_set)
                analysis_results["match_counts"][str(num_matches)] += 1

                missing_in_combination = list(winning_set - generated_set)
                extra_in_combination = list(generated_set - winning_set)

                for num in missing_in_combination:
                    analysis_results["common_missing_numbers"][str(num)] = analysis_results["common_missing_numbers"].get(str(num), 0) + 1
                for num in extra_in_combination:
                    analysis_results["common_extra_numbers"][str(num)] = analysis_results["common_extra_numbers"].get(str(num), 0) + 1
                
                all_generated_numbers.extend(generated_combination)

            generated_counter = Counter(all_generated_numbers)
            analysis_results["top_generated_unmatched"] = sorted([
                (num, count) for num, count in generated_counter.items() if num not in winning_set
            ], key=lambda x: x[1], reverse=True)[:self.config.get("top_missing_limit", 10)]

            print(f"ReverseAnalysis: Analysis complete for draw {draw_number}.")
            self._generate_reverse_analysis_report(analysis_results)
            return analysis_results

        except Exception as e:
            print(f"ReverseAnalysis: Error during analysis for draw {draw_number}: {e}")
            return f"Error: {e}"

    def _generate_reverse_analysis_report(self, analysis_results):
        report_dir_path = os.path.join(self.project_root_dir, REVERSE_ANALYSIS_REPORTS_DIR)
        os.makedirs(report_dir_path, exist_ok=True)

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = os.path.join(report_dir_path, f"Reverse_Analysis_draw_{analysis_results['draw_number']}_{timestamp}.txt")

        with open(report_filename, 'w', encoding='utf-8') as f:
            f.write(f"Отчет об обратном анализе для тиража №{analysis_results['draw_number']}\n")
            f.write(f"Дата анализа: {analysis_results['analysis_timestamp']}\n")
            f.write(f"Выпавшие номера: {', '.join(map(str, analysis_results['winning_numbers']))}\n")
            f.write(f"Всего проанализировано комбинаций: {analysis_results['total_failed_combinations']}\n\n")
            f.write("Распределение совпадений:\n")
            for matches, count in sorted(analysis_results["match_counts"].items(), key=lambda item: int(item[0]), reverse=True):
                f.write(f"  {matches} совпадений: {count} комбинаций\n")
            
            f.write("\nЧасто отсутствующие выигрышные номера в неудачных комбинациях:\n")
            top_missing_limit = self.config.get("top_missing_limit", 10)
            sorted_missing = sorted(analysis_results["common_missing_numbers"].items(), key=lambda item: item[1], reverse=True)[:top_missing_limit]
            for num, count in sorted_missing:
                f.write(f"  Номер {num}: {count} раз отсутствовал\n")

            f.write("\nЧасто генерируемые, но не выпавшие номера в неудачных комбинациях:\n")
            top_extra_limit = self.config.get("top_extra_limit", 10)
            sorted_extra = sorted(analysis_results["common_extra_numbers"].items(), key=lambda item: item[1], reverse=True)[:top_extra_limit]
            for num, count in sorted_extra:
                f.write(f"  Номер {num}: {count} раз был лишним\n")
            
            if "top_generated_unmatched" in analysis_results:
                f.write("\nТоп-10 сгенерированных, но не совпавших номеров (по частоте генерации):\n")
                for num, count in analysis_results["top_generated_unmatched"]:
                    f.write(f"  Номер {num}: {count} раз (не совпал)\n")

        print(f"ReverseAnalysis: Отчет сохранен в {report_filename}")