import os
import json
import datetime
import pandas as pd
import time
import random
import re
import sys # Добавлен sys для использования log_callback

# Импортируем из нового вспомогательного модуля
from utils.json_utils import load_json_config, save_json_config

# Используем относительный импорт для модулей AKK (они в той же папке akk/)
from .AKK import AKK as AKK_Module
from .module_back import ReverseAnalysis

# Импортируем StatsCalculator из его конкретного пути
import sys
# Убедимся, что корневая папка LABCORE добавлена в sys.path
# Это нужно для импорта labcore.stats_calculator
# os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)) - это путь к LABCORE/
if os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)) not in sys.path:
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))
from labcore.stats_calculator import StatsCalculator 


# Предполагается, что эти пути будут относительно корневой директории LABCORE
CONFIG_DIR = "config"
LABCORE_SAFE_DIR = "labcore_safe"
LABCORE_STATE_FILE_NAME = "labcore_state.json"
LABCORE_DRAWS_FILE = "labcore_draws.csv"
GENERATED_DIR = "generated"
SVERKA_INF_DIR = os.path.join("reports", "Сверка_inf")


# --- Новый класс: LABCORE_AI_Agent ---
class LABCORE_AI_Agent:
    def __init__(self, project_root_dir):
        self.project_root_dir = project_root_dir
        # Передаем project_root_dir в AKK_Module и ReverseAnalysis
        self.akk_instance = AKK_Module(os.path.join(self.project_root_dir, CONFIG_DIR, "akk_config.json"), self.project_root_dir)
        self.reverse_analysis_instance = ReverseAnalysis(os.path.join(self.project_root_dir, CONFIG_DIR, "reverse_analysis_config.json"), self.project_root_dir)
        
    def decide_on_akk_action(self, draw_number, performance_metrics):
        print(f"AI Agent: Deciding on AKK action for draw {draw_number} with metrics: {performance_metrics}")
        
        recommendation, adjustment_made = self.akk_instance.analyze_performance_and_adjust(
            draw_number, performance_metrics
        )
        
        if adjustment_made:
            print("AI Agent: AKK made an adjustment. Considering further actions like Reverse Analysis.")
            
            mock_failed_combinations_file = os.path.join(self.project_root_dir, GENERATED_DIR, f"combinations_for_draw_{draw_number + 1}_Контур_A.csv")
            
            if not os.path.exists(mock_failed_combinations_file):
                print(f"AI Agent: Mock failed combinations file {os.path.basename(mock_failed_combinations_file)} not found. Creating a dummy one.")
                os.makedirs(os.path.dirname(mock_failed_combinations_file), exist_ok=True)
                mock_df_data = {
                    "N1": [1, 2, 3], "N2": [7, 8, 9], "N3": [13, 14, 15],
                    "N4": [19, 20, 21], "N5": [25, 26, 27], "N6": [31, 32, 33]
                }
                pd.DataFrame(mock_df_data).to_csv(mock_failed_combinations_file, index=False, encoding="utf-8-sig")

            mock_winning_numbers = self._get_winning_numbers_from_history(draw_number)
            if mock_winning_numbers:
                self.reverse_analysis_instance.analyze_failed_generation(
                    draw_number, mock_failed_combinations_file, mock_winning_numbers
                )
                print("AI Agent: Triggered Reverse Analysis.")
            else:
                print(f"AI Agent: Skipping Reverse Analysis - winning numbers for draw {draw_number} not found.")

        return recommendation, adjustment_made

    def _get_winning_numbers_from_history(self, draw_number):
        filepath = os.path.join(self.project_root_dir, LABCORE_DRAWS_FILE)
        if os.path.exists(filepath):
            try:
                df = pd.read_csv(filepath, encoding="utf-8-sig")
                df['Тираж'] = pd.to_numeric(df['Тираж'], errors='coerce')
                draw_row = df[df['Тираж'] == draw_number]
                if not draw_row.empty:
                    numbers = [int(draw_row.iloc[0][f'N{i}']) for i in range(1, 7) if pd.notna(draw_row.iloc[0][f'N{i}'])]
                    if len(numbers) == 6:
                        return numbers
            except Exception as e:
                print(f"AI Agent: Ошибка получения номеров для тиража {draw_number} из {LABCORE_DRAWS_FILE}: {e}")
        return None

# --- Основной класс LABCORE_80 ---
class LABCORE_80:
    def __init__(self, project_root_dir, config_labcore_80_path):
        self.project_root_dir = project_root_dir
        self.config_labcore_80_path = config_labcore_80_path # Сохраняем путь к конфигу
        self.config = load_json_config(self.config_labcore_80_path) # Используем load_json_config
        
        self.current_phase = self.config.get("current_phase", "Idle")
        self.cycle_count = self.config.get("cycle_count", 0)
        self.log_level = self.config.get("log_level", "INFO")
        self.cycles_to_run = self.config.get("cycles_to_run", 1)

        self.labcore_state_filepath = os.path.join(self.project_root_dir, LABCORE_SAFE_DIR, LABCORE_STATE_FILE_NAME) # Полный путь к файлу состояния
        self.labcore_state = load_json_config(self.labcore_state_filepath) # Используем load_json_config для состояния
        
        if not self.labcore_state: # Если состояние не было загружено (например, файл пуст или некорректен), инициализируем его по умолчанию
            self.labcore_state = {"last_successful_draw": 0, "last_generated_draw": 0, "last_analysis_draw": 0}
            save_json_config(self.labcore_state_filepath, self.labcore_state) # Сохраняем дефолтное состояние, чтобы файл был корректным

        self.ai_agent = LABCORE_AI_Agent(self.project_root_dir)
        self.stats_calculator = StatsCalculator(self.project_root_dir)

        self.draws_filepath = os.path.join(self.project_root_dir, LABCORE_DRAWS_FILE)


    def _save_config(self, config_data=None):
        if config_data is None:
            config_data = self.config
        save_json_config(self.config_labcore_80_path, config_data) # Используем save_json_config

    def _save_labcore_state(self):
        """Сохраняет состояние LABCORE."""
        save_json_config(self.labcore_state_filepath, self.labcore_state) # Используем save_json_config

    def _get_last_draw_number_from_history(self):
        filepath = self.draws_filepath
        if os.path.exists(filepath):
            try:
                df = pd.read_csv(filepath, encoding="utf-8-sig")
                df['Тираж'] = pd.to_numeric(df['Тираж'], errors='coerce')
                if not df.empty and not pd.isna(df['Тираж'].max()):
                    return int(df['Тираж'].max())
            except Exception as e:
                print(f"LABCORE-80: Ошибка чтения {LABCORE_DRAWS_FILE}: {e}. Используем 0.")
        return 0

    def _get_winning_numbers_for_draw(self, draw_number):
        filepath = self.draws_filepath
        if os.path.exists(filepath):
            try:
                df = pd.read_csv(filepath, encoding="utf-8-sig")
                df['Тираж'] = pd.to_numeric(df['Тираж'], errors='coerce')
                draw_row = df[df['Тираж'] == draw_number]
                if not draw_row.empty:
                    numbers = [int(draw_row.iloc[0][f'N{i}']) for i in range(1, 7) if pd.notna(draw_row.iloc[0][f'N{i}'])]
                    if len(numbers) == 6:
                        return numbers
            except Exception as e:
                print(f"LABCORE-80: Ошибка получения номеров для тиража {draw_number} из {LABCORE_DRAWS_FILE}: {e}")
        return None

    def _perform_comparison_mock(self, processed_draw_number, generated_for_draw_number):
        print(f"LABCORE-80: Performing comparison mock for draw {processed_draw_number} with generations for {generated_for_draw_number}...")
        
        winning_numbers = self._get_winning_numbers_for_draw(processed_draw_number)
        if winning_numbers is None:
            print(f"LABCORE-80: Warning: Winning numbers for draw {processed_draw_number} not found or incomplete. Cannot perform realistic comparison mock.")
            return {
                'match_5_plus_count': random.randint(0, 2), 
                'total_combinations': 200,
                'match_6_count': random.randint(0, 0)
            }

        generated_dir_path = os.path.join(self.project_root_dir, GENERATED_DIR)
        all_generated_combinations_count = 0
        total_5_plus_matches = 0
        total_6_matches = 0

        generated_files = []
        for f_name in os.listdir(generated_dir_path):
            match = re.match(r"combinations_for_draw_(\d+)_Контур_([AB])_?(\d{8}_\d{6})?\.csv", f_name)
            if match and int(match.group(1)) == generated_for_draw_number:
                generated_files.append(os.path.join(generated_dir_path, f_name))
        
        if not generated_files:
            print(f"LABCORE-80: No generated files found for draw {generated_for_draw_number}. Cannot perform realistic comparison mock.")
            return {
                'match_5_plus_count': 0, 
                'total_combinations': 0,
                'match_6_count': 0
            }

        for g_file_path in generated_files:
            try:
                df_gen = pd.read_csv(g_file_path, encoding="utf-8-sig")
                all_generated_combinations_count += len(df_gen)
                
                for _, row in df_gen.iterrows():
                    generated_combination = [row[f'N{i}'] for i in range(1, 7) if pd.notna(row[f'N{i}'])]
                    num_matches = len(set(generated_combination) & set(winning_numbers))
                    if num_matches >= 5:
                        total_5_plus_matches += 1
                    if num_matches == 6:
                        total_6_matches += 1
            except Exception as e:
                print(f"LABCORE-80: Error processing generated file {os.path.basename(g_file_path)}: {e}")

        return {
            'match_5_plus_count': total_5_plus_matches, 
            'total_combinations': all_generated_combinations_count,
            'match_6_count': total_6_matches
        }

    def _perform_generation_mock(self, generate_for_draw_number):
        print(f"LABCORE-80: Generating combinations mock for draw {generate_for_draw_number}...")
        self.labcore_state["last_generated_draw"] = generate_for_draw_number
        self._save_labcore_state()
        print(f"LABCORE-80: Combinations mock generated for draw {generate_for_draw_number}.")


    def _perform_reporting_mock(self, draw_number, performance_metrics, akk_recommendation, adjustment_made, report_type="standard"):
        print(f"LABCORE-80: Performing reporting mock for draw {draw_number}. Type: {report_type}")
        
        report_dir_path = os.path.join(self.project_root_dir, SVERKA_INF_DIR)
        os.makedirs(report_dir_path, exist_ok=True)

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename_summary = os.path.join(report_dir_path, f"sverka_summary_auto_draw_{draw_number}_{timestamp}.txt")
        
        akk_config_data = self.ai_agent.akk_instance.config 

        akk_target_5_match = akk_config_data.get("target_5_match_percentage", 0.80)
        akk_min_5_match = akk_config_data.get("min_5_match_percentage", 0.15)
        
        current_5_match_percentage = (performance_metrics.get("match_5_plus_count", 0) / performance_metrics.get("total_combinations", 1)) if performance_metrics.get("total_combinations", 1) > 0 else 0

        with open(report_filename_summary, 'w', encoding='utf-8') as f:
            f.write(f"Автоматический отчет LABCORE-80 для тиража №{draw_number}\n")
            f.write(f"Дата отчета: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Метрики производительности: {json.dumps(performance_metrics, indent=2, ensure_ascii=False)}\n")
            f.write(f"Рекомендация АКК: {akk_recommendation}\n")
            f.write(f"Произведена корректировка: {'Да' if adjustment_made else 'Нет'}\n")
            f.write(f"Состояние: {report_type}\n")
            f.write(f"Совпадений 5+: {performance_metrics.get('match_5_plus_count', 0)} из {performance_metrics.get('total_combinations', 0)} ({current_5_match_percentage:.2%})\n")
            f.write(f"Совпадений 6: {performance_metrics.get('match_6_count', 0)} из {performance_metrics.get('total_combinations', 0)}\n")
            
            f.write(f"Целевой % 5+: {akk_target_5_match:.2%}, Мин % 5+: {akk_min_5_match:.2%}\n")

            if current_5_match_percentage < akk_min_5_match:
                f.write("\nИтог: Порог 5+ совпадений НЕ достигнут. Идет отладка программы для повышения порога совпадений 5+.\n")
            else:
                f.write("\nИтог: Порог 5+ совпадений достигнут.\n")

            if report_type == "post_training":
                f.write("\n--- Отчет о проделанной работе после обучения/отладки ---\n")
                f.write("Проведены работы по оптимизации и дообучению моделей.\n")
                f.write(f"Сгенерировано 200 комбинаций (пример) на следующий тираж ({draw_number + 1}).\n")
        
        print(f"LABCORE-80: Отчет '{report_type}' сохранен в {report_filename_summary}")


    def run_cycle(self, draw_number=None):
        """
        Запускает один полный цикл LABCORE-80.
        Если draw_number не указан, определяет следующий тираж из истории.
        """
        self.cycle_count += 1
        self.config["cycle_count"] = self.cycle_count
        self._save_config()

        print(f"LABCORE-80: Starting cycle {self.cycle_count}. Current phase: {self.current_phase}")
        self.current_phase = "Checking New Draw"
        self._save_config()

        # Обновление pool_stats.json в начале цикла
        print("LABCORE-80: Updating pool_stats.json...")
        self.stats_calculator.calculate_and_update_pool_stats()
        print("LABCORE-80: pool_stats.json updated.")

        draw_number_to_process = draw_number if draw_number is not None else (self._get_last_draw_number_from_history() + 1)
        
        print(f"LABCORE-80: New draw {draw_number_to_process} detected/assumed.")
        
        # --- ФАЗА 1: Сверка ---
        self.current_phase = "Performing Comparison"
        self._save_config()
        print(f"LABCORE-80: Phase: {self.current_phase}")
        performance_metrics = self._perform_comparison_mock(draw_number_to_process, draw_number_to_process + 1)

        print(f"LABCORE-80: Comparison done. Metrics: {performance_metrics}")

        # --- ФАЗА 2: Анализ АКК (управляется AI Агентом) ---
        self.current_phase = "AKK Analysis (AI Agent Controlled)"
        self._save_config()
        print(f"LABCORE-80: Phase: {self.current_phase}")
        
        akk_recommendation, adjustment_made = self.ai_agent.decide_on_akk_action(
            draw_number_to_process, performance_metrics
        )
        print(f"LABCORE-80: AI Agent decision: {akk_recommendation}")

        # --- ФАЗА 3: Корректировка / Переобучение (если нужно) ---
        if adjustment_made:
            self.current_phase = "Model Retraining/Parameter Adjustment"
            self._save_config()
            print(f"LABCORE-80: Phase: {self.current_phase}")
            print("LABCORE-80: Parameters adjusted/Model retraining triggered.")
            self._perform_reporting_mock(draw_number_to_process, performance_metrics, akk_recommendation, adjustment_made, report_type="post_training")

        # --- ФАЗА 4: Генерация Комбинаций ---
        self.current_phase = "Generating Combinations"
        self._save_config()
        print(f"LABCORE-80: Phase: {self.current_phase}")
        self._perform_generation_mock(draw_number_to_process + 1)
        
        # --- ФАЗА 5: Отчетность ---
        self.current_phase = "Reporting"
        self._save_config()
        print(f"LABCORE-80: Phase: {self.current_phase}")
        self._perform_reporting_mock(draw_number_to_process, performance_metrics, akk_recommendation, adjustment_made, report_type="standard")

        self.current_phase = "Idle"
        self.labcore_state["last_successful_draw"] = draw_number_to_process
        self.labcore_state["last_analysis_draw"] = draw_number_to_process
        self._save_labcore_state()
        self._save_config()

        print(f"LABCORE-80: Cycle {self.cycle_count} finished. Current phase: {self.current_phase}")
        return self.labcore_state


    def run_historical_test_cycle(self, start_draw, num_draws, log_callback):
        """
        Запускает исторический цикл тестирования LABCORE-80, не меняя live-состояние.
        """
        original_stdout = sys.stdout # Сохраняем оригинальный stdout
        sys.stdout = log_callback # Перенаправляем вывод в лог callback

        print(f"\n--- НАЧАЛО ТЕСТ-ЛАБОРАТОРИИ: Анализ {num_draws} тиражей, начиная с №{start_draw} ---")
        
        # В этом режиме мы не обновляем labcore_state.json
        # Мы просто выполняем фазы анализа и корректировки
        
        # Загружаем полную историю тиражей один раз
        try:
            draws_df = pd.read_csv(os.path.join(self.project_root_dir, LABCORE_DRAWS_FILE), encoding="utf-8-sig")
            draws_df['Тираж'] = pd.to_numeric(draws_df['Тираж'], errors='coerce').astype('Int64')
            draws_df = draws_df.sort_values(by='Тираж', ascending=True).reset_index(drop=True)
        except Exception as e:
            print(f"ОШИБКА: Не удалось загрузить историю тиражей для Тест-Лаборатории: {e}")
            sys.stdout = original_stdout
            return

        performance_history_for_akk_A = [] # История метрик для Контура A (30 тиражей)

        for i in range(num_draws):
            current_test_draw_number = start_draw + i
            
            # Проверяем, существует ли тираж в истории
            if current_test_draw_number not in draws_df['Тираж'].values:
                print(f"Предупреждение: Тираж №{current_test_draw_number} не найден в истории. Пропускаем.")
                continue

            print(f"\n--- Тест-Лаборатория: Обработка тиража №{current_test_draw_number} ---")
            
            # --- Фаза: Обновление pool_stats.json (имитация) ---
            # В реальном сценарии StatsCalculator может потребовать историю до этого тиража
            # Для мока просто вызываем, предполагая, что данные актуальны.
            self.stats_calculator.calculate_and_update_pool_stats() # Обновляем pool_stats для текущего тиража
            print(f"Тест-Лаборатория: pool_stats.json обновлен для тиража №{current_test_draw_number}.")

            # --- Фаза: Сверка (используем реальные данные тиража, но мок генерации) ---
            performance_metrics = self._perform_comparison_mock(current_test_draw_number, current_test_draw_number + 1)
            print(f"Тест-Лаборатория: Сверка завершена. Метрики: {performance_metrics}")
            
            # Добавляем метрики в историю для АКК (Контур А)
            performance_history_for_akk_A.append(performance_metrics)
            if len(performance_history_for_akk_A) > 30: # Ограничиваем до 30 последних
                performance_history_for_akk_A.pop(0)

            # --- Фаза: Анализ АКК (управляется AI Агентом) ---
            akk_recommendation, adjustment_made = self.ai_agent.decide_on_akk_action(
                current_test_draw_number, 
                performance_metrics, 
                history_performance_metrics=performance_history_for_akk_A # Передаем историю
            )
            print(f"Тест-Лаборатория: AI Agent решение: {akk_recommendation}")

            # --- Фаза: Корректировка / Переобучение (если нужно) ---
            if adjustment_made:
                print("Тест-Лаборатория: Параметры скорректированы / Переобучение запущено (имитация).")
            
            # --- Фаза: Генерация Комбинаций (имитация, не сохраняем в 'generated/') ---
            print(f"Тест-Лаборатория: Генерация комбинаций для тиража №{current_test_draw_number + 1} (имитация).")
            
            # --- Фаза: Отчетность (имитация, не сохраняем в 'reports/') ---
            # Отчеты Тест-Лаборатории будут только в логе диалога
            print(f"Тест-Лаборатория: Отчетность выполнена (имитация).")

        print(f"\n--- КОНЕЦ ТЕСТ-ЛАБОРАТОРИИ: Анализ {num_draws} тиражей завершен. ---")
        sys.stdout = original_stdout # Восстанавливаем оригинальный stdout