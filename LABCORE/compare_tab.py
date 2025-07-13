import os
import pandas as pd
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QFileDialog,
    QTableWidget, QTableWidgetItem, QHBoxLayout, QComboBox, QHeaderView,
    QMessageBox, QListWidget, QListWidgetItem, QGroupBox, QDialog, QCheckBox,
    QDialogButtonBox
)
from PyQt5.QtCore import Qt
import datetime
import re

# Импортируем из нового вспомогательного модуля
from utils.json_utils import load_json_config, save_json_config

LABCORE_DRAWS_FILE = "labcore_draws.csv"
GENERATED_DIR = "generated"
REPORTS_DIR = "reports"
SVERKA_INF_DIR = os.path.join(REPORTS_DIR, "Сверка_inf")

class CompareTab(QWidget):
    def __init__(self):
        super().__init__()
        self.setLayout(QVBoxLayout())

        self.project_root_dir = os.getcwd()

        self.header_label = QLabel("Сверка сгенерированных комбинаций с тиражом")
        self.header_label.setStyleSheet("font-weight: bold; font-size: 16px;")
        self.layout().addWidget(self.header_label, alignment=Qt.AlignCenter)

        self.last_draw_info_label = QLabel("") 
        self.layout().addWidget(self.last_draw_info_label)

        auto_mode_layout = QHBoxLayout()
        self.auto_compare_checkbox = QCheckBox("Автоматическая сверка последнего тиража (для автономного режима)")
        self.auto_compare_checkbox.setChecked(False)
        self.auto_compare_checkbox.stateChanged.connect(self._toggle_manual_controls)
        auto_mode_layout.addWidget(self.auto_compare_checkbox)
        self.layout().addLayout(auto_mode_layout)

        self.manual_controls_group = QGroupBox("Ручной выбор для сверки")
        self.manual_controls_layout = QVBoxLayout()

        draw_selection_group = QGroupBox("Тираж для сверки")
        draw_selection_layout = QVBoxLayout()
        self.draw_label = QLabel("Выбранный тираж: Не выбран")
        draw_selection_layout.addWidget(self.draw_label)
        btn_select_draw = QPushButton("Выбрать тираж из истории")
        btn_select_draw.clicked.connect(self.select_draw_for_comparison)
        draw_selection_layout.addWidget(btn_select_draw)
        draw_selection_group.setLayout(draw_selection_layout)
        self.manual_controls_layout.addWidget(draw_selection_group)

        generated_selection_group = QGroupBox("Файл сгенерированных комбинаций")
        generated_selection_layout = QVBoxLayout()
        self.generated_file_label = QLabel("Выбранный файл: Не выбран")
        generated_selection_layout.addWidget(self.generated_file_label)
        btn_select_generated_file = QPushButton("Выбрать файл комбинаций")
        btn_select_generated_file.clicked.connect(self.select_generated_file)
        generated_selection_layout.addWidget(btn_select_generated_file)
        generated_selection_group.setLayout(generated_selection_layout)
        self.manual_controls_layout.addWidget(generated_selection_group)

        self.manual_controls_group.setLayout(self.manual_controls_layout)
        self.layout().addWidget(self.manual_controls_group)

        self.btn_compare = QPushButton("Начать Сверку")
        self.btn_compare.clicked.connect(self.start_comparison_logic)
        self.layout().addWidget(self.btn_compare)

        results_group = QGroupBox("Результаты Сверки")
        results_layout = QVBoxLayout()
        self.summary_label = QLabel("Сводка: Ожидание сверки...")
        results_layout.addWidget(self.summary_label)
        self.comparison_table = QTableWidget()
        self.comparison_table.setStyleSheet("font-size: 11px;")
        results_layout.addWidget(self.comparison_table)
        results_group.setLayout(results_layout)
        self.layout().addWidget(results_group)

        self.layout().addStretch(1)

        self.selected_draw_numbers = []
        self.selected_draw_info = {}
        self.selected_generated_filepath = None
        self.generated_df = pd.DataFrame()

        self.all_draws_df = self._load_draws_history() # Загружаем историю при инициализации
        self.update_last_draw_info_label()

        self._toggle_manual_controls()

    def update_last_draw_info_label(self):
        last_draw_number = self._get_last_draw_number()
        if last_draw_number is not None:
             self.last_draw_info_label.setText(f"Последний тираж в истории: №{last_draw_number}")
        else:
             self.last_draw_info_label.setText("Последний тираж в истории: Нет данных")

    def _toggle_manual_controls(self):
        is_auto_checked = self.auto_compare_checkbox.isChecked()
        self.manual_controls_group.setVisible(not is_auto_checked)
        
    def start_comparison_logic(self):
        if self.auto_compare_checkbox.isChecked():
            self.perform_auto_comparison()
        else:
            self.perform_manual_comparison()

    def _load_draws_history(self):
        filepath = os.path.join(self.project_root_dir, LABCORE_DRAWS_FILE)
        
        if not os.path.exists(filepath):
            QMessageBox.warning(self, "Ошибка загрузки истории тиражей", f"Файл {filepath} не найден.")
            return pd.DataFrame() 

        try:
            if os.stat(filepath).st_size == 0:
                QMessageBox.information(self, "История тиражей", f"Файл {filepath} пуст.")
                return pd.DataFrame(columns=["Тираж", "Дата", "Комплект", "N1", "N2", "N3", "N4", "N5", "N6"])
            
            df = pd.read_csv(filepath, encoding="utf-8-sig")
            
            if df.empty:
                QMessageBox.information(self, "История тиражей", f"Файл {filepath} содержит только заголовок или пуст после чтения.")
                return pd.DataFrame(columns=["Тираж", "Дата", "Комплект", "N1", "N2", "N3", "N4", "N5", "N6"])

            df_cleaned = self._clean_dataframe_for_comparison(df)
            
            if df_cleaned.empty:
                QMessageBox.warning(self, "История тиражей", "После очистки данных в файле тиражей не осталось валидных строк.")
                return pd.DataFrame(columns=["Тираж", "Дата", "Комплект", "N1", "N2", "N3", "N4", "N5", "N6"])

            df_cleaned['Тираж'] = pd.to_numeric(df_cleaned['Тираж'], errors='coerce').astype('Int64')
            df_cleaned.sort_values(by="Тираж", ascending=False, inplace=True)
            return df_cleaned
        except pd.errors.EmptyDataError:
            QMessageBox.information(self, "История тиражей", f"Файл {filepath} пуст или некорректен для чтения Pandas.")
            return pd.DataFrame(columns=["Тираж", "Дата", "Комплект", "N1", "N2", "N3", "N4", "N5", "N6"])
        except Exception as e:
            QMessageBox.warning(self, "Ошибка загрузки истории тиражей", f"Не удалось загрузить {filepath}: {e}")
            return pd.DataFrame()

    def _clean_dataframe_for_comparison(self, df):
        column_mapping = {
            "тираж": "Тираж", "розіграш": "Тираж",
            "дата": "Дата",
            "комплект": "Комплект",
            "n1": "N1", "кулька 1": "N1", "шар 1": "N1",
            "n2": "N2", "кулька 2": "N2", "шар 2": "N2",
            "n3": "N3", "кулька 3": "N3", "шар 3": "N3",
            "n4": "N4", "кулька 4": "N4", "шар 4": "N4",
            "n5": "N5", "кулька 5": "N5", "шар 5": "N5",
            "n6": "N6", "кулька 6": "N6", "шар 6": "N6"
        }

        df.columns = [col.lower() for col in df.columns]

        df_cleaned = pd.DataFrame()
        for target_col in ["Тираж", "Дата", "Комплект", "N1", "N2", "N3", "N4", "N5", "N6"]:
            found_col_name = None
            for original_col_name, mapped_col_name in column_mapping.items():
                if mapped_col_name == target_col:
                    if original_col_name in df.columns:
                        found_col_name = original_col_name
                        break
            
            if found_col_name:
                df_cleaned[target_col] = df[found_col_name]
            else:
                df_cleaned[target_col] = pd.NA

        if "Тираж" in df_cleaned.columns:
            df_cleaned["Тираж"] = pd.to_numeric(df_cleaned["Тираж"], errors='coerce')
            df_cleaned = df_cleaned.dropna(subset=["Тираж"])
            df_cleaned["Тираж"] = df_cleaned["Тираж"].astype('Int64')
        
        for col in ["Дата", "Комплект"]:
            if col in df_cleaned.columns:
                df_cleaned[col] = df_cleaned[col].fillna("").astype(str)

        if "Тираж" in df_cleaned.columns:
            df_cleaned.drop_duplicates(subset=["Тираж"], keep="last", inplace=True)
            df_cleaned.sort_values(by="Тираж", ascending=False, inplace=True)

        return df_cleaned


    def _get_last_draw_number(self):
        if not self.all_draws_df.empty and 'Тираж' in self.all_draws_df.columns:
            draws_series = self.all_draws_df['Тираж'].dropna()
            if not draws_series.empty:
                return int(draws_series.max())
        return None

    def select_draw_for_comparison(self):
        self.all_draws_df = self._load_draws_history() 

        if self.all_draws_df.empty:
            QMessageBox.information(self, "Нет тиражей", "В файле истории нет тиражей для выбора.")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Выбрать тираж для сверки")
        dialog_layout = QVBoxLayout(dialog)

        list_widget = QListWidget()
        for index, row in self.all_draws_df.iterrows():
            draw_num = row['Тираж']
            draw_date = row['Дата']
            numbers = ", ".join(str(int(x)) for x in row[[f'N{i}' for i in range(1, 7)]].dropna() if pd.notna(x))
            item_text = f"Тираж №{draw_num} ({draw_date}) - Номера: {numbers}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, row.to_dict())
            list_widget.addItem(item)
        
        list_widget.setMinimumWidth(400)

        dialog_layout.addWidget(list_widget)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, dialog)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        dialog_layout.addWidget(button_box)

        if dialog.exec_() == QDialog.Accepted:
            selected_item = list_widget.currentItem()
            if selected_item:
                selected_row_data = selected_item.data(Qt.UserRole)
                self.selected_draw_info = selected_row_data
                self.selected_draw_numbers = [int(selected_row_data[f'N{i}']) for i in range(1, 7) if pd.notna(selected_row_data[f'N{i}'])]
                
                draw_num = self.selected_draw_info.get('Тираж', 'N/A')
                draw_date = self.selected_draw_info.get('Дата', 'N/A')
                numbers_str = ", ".join(map(str, sorted(self.selected_draw_numbers)))
                self.draw_label.setText(f"Выбранный тираж: №{draw_num} ({draw_date}) - Номера: {numbers_str}")
            else:
                QMessageBox.warning(self, "Ошибка выбора", "Пожалуйста, выберите тираж из списка.")


    def select_generated_file(self):
        generated_dir_path = os.path.join(self.project_root_dir, GENERATED_DIR)
        
        if not os.path.exists(generated_dir_path):
            QMessageBox.information(self, "Нет файлов", f"Директория {generated_dir_path} не найдена. Сначала сгенерируйте комбинации.")
            return

        path, _ = QFileDialog.getOpenFileName(self, "Выбрать файл сгенерированных комбинаций", generated_dir_path, "CSV Files (*.csv)")
        if path:
            self.selected_generated_filepath = path
            self.generated_file_label.setText(f"Выбранный файл: {os.path.basename(path)}")
            try:
                df = pd.read_csv(path, encoding="utf-8-sig")
                for i in range(1, 7):
                    df[f'N{i}'] = pd.to_numeric(df[f'N{i}'], errors='coerce').astype('Int64')
                self.generated_df = df
            except Exception as e:
                QMessageBox.warning(self, "Ошибка загрузки файла", f"Не удалось загрузить файл комбинаций: {str(e)}")
                self.generated_df = pd.DataFrame()
        else:
            self.selected_generated_filepath = None
            self.generated_file_label.setText("Выбранный файл: Не выбран")
            self.generated_df = pd.DataFrame()

    def perform_manual_comparison(self):
        if not self.selected_draw_numbers:
            QMessageBox.warning(self, "Ошибка", "Пожалуйста, выберите тираж для сверки.")
            return
        if self.generated_df.empty:
            QMessageBox.warning(self, "Ошибка", "Пожалуйста, выберите файл сгенерированных комбинаций.")
            return
        
        self.summary_label.setText("Сводка: Выполняется ручная сверка...")
        self.comparison_table.clearContents()
        self.comparison_table.setRowCount(0)
        self.comparison_table.setColumnCount(0)

        winning_numbers_set = set(self.selected_draw_numbers)
        results_data = []
        match_counts = {i: 0 for i in range(7)}
        threshold_5_plus_met = False
        
        all_generated_combinations_count = len(self.generated_df)

        gen_for_draw_num_from_filename = 'N/A'
        file_match = re.match(r"combinations_for_draw_(\d+)_Контур_([AB])_?(\d{8}_\d{6})?\.csv", os.path.basename(self.selected_generated_filepath))
        if file_match:
            gen_for_draw_num_from_filename = file_match.group(1)
            contour_label_for_file = file_match.group(2)
        else:
            contour_label_for_file = "Неизвестный"

        for idx, row in self.generated_df.iterrows():
            generated_combination_list = [row[f'N{i}'] for i in range(1, 7) if pd.notna(row[f'N{i}'])]
            generated_combination_set = set(generated_combination_list)
            
            num_matches = len(generated_combination_set & winning_numbers_set)
            
            matching_numbers = sorted(list(generated_combination_set & winning_numbers_set))
            
            if num_matches >= 3:
                results_data.append({
                    "№": idx + 1,
                    "Номера вышедшего тиража": ", ".join(map(str, sorted(list(winning_numbers_set)))),
                    "Прогнозная комбинация": ", ".join(map(str, sorted(generated_combination_list))),
                    "Совпадающие номера": ", ".join(map(str, matching_numbers)),
                    "Количество совпадений": num_matches
                })
            
            match_counts[num_matches] += 1
            if num_matches >= 5:
                threshold_5_plus_met = True

        self.display_comparison_results(results_data)

        draw_num = self.selected_draw_info.get('Тираж', 'N/A')

        summary_text = f"<b>Сводка результатов ручной сверки для тиража №{draw_num} (сгенерировано для тиража №{gen_for_draw_num_from_filename}):</b><br>"
        summary_text += f"Всего проанализировано комбинаций: {all_generated_combinations_count}<br><br>"

        summary_text += "Совпадений (из всех сгенерированных комбинаций):<br>"
        for i in range(len(match_counts) - 1, -1, -1):
            if match_counts[i] > 0:
                summary_text += f"  {match_counts[i]} комбинаций имели {i} совпадений<br>"
        
        if not threshold_5_plus_met:
            summary_text += "<br><font color='red'><b>Внимание: Порог 5+ совпадений НЕ достигнут. Рекомендуется запуск АКК!</b></font>"
            QMessageBox.warning(self, "Сигнал АКК", "Порог 5+ совпадений не достигнут. Рекомендуется запуск модуля АКК.")
        else:
            summary_text += "<br><font color='green'><b>Порог 5+ совпадений достигнут.</b></font>"
            
        self.summary_label.setText(summary_text)

        report_actual_draw_num = draw_num if draw_num != 'N/A' else 'UNKNOWN'
        report_gen_for_draw_num = gen_for_draw_num_from_filename
        
        report_contour_label = contour_label_for_file if contour_label_for_file != "Неизвестный" else ""
        
        self._save_comparison_report(
            results_data, match_counts, report_actual_draw_num, 
            report_gen_for_draw_num, all_generated_combinations_count, 
            threshold_5_plus_met, 
            contour_label=report_contour_label,
            is_manual_mode=True
        )
        QMessageBox.information(self, "Сверка завершена", "Ручная сверка успешно завершена.")


    def perform_auto_comparison(self):
        self.summary_label.setText("Сводка: Выполняется автоматическая сверка...")
        self.comparison_table.clearContents()
        self.comparison_table.setRowCount(0)
        self.comparison_table.setColumnCount(0)

        self.all_draws_df = self._load_draws_history()
        last_draw_number = self._get_last_draw_number()
        
        if last_draw_number is None:
            QMessageBox.warning(self, "Ошибка", "Не удалось найти последний тираж в истории для сверки.")
            self.summary_label.setText("Сводка: Не удалось найти последний тираж.")
            return

        last_draw_row = self.all_draws_df[self.all_draws_df['Тираж'] == last_draw_number].iloc[0]
        winning_numbers_list = [int(last_draw_row[f'N{i}']) for i in range(1, 7) if pd.notna(last_draw_row[f'N{i}'])]
        winning_numbers_set = set(winning_numbers_list)
        
        if len(winning_numbers_list) < 6:
            QMessageBox.warning(self, "Ошибка", f"Номера для последнего тиража №{last_draw_number} неполные. Необходимы все 6 чисел.")
            self.summary_label.setText(f"Сводка: Номера тиража №{last_draw_number} неполные.")
            return

        self.last_draw_info_label.setText(f"Сверка для тиража: №{last_draw_number} - Номера: {', '.join(map(str, sorted(winning_numbers_list)))}")

        generated_dir_path = os.path.join(self.project_root_dir, GENERATED_DIR)
        if not os.path.exists(generated_dir_path):
            QMessageBox.information(self, "Нет файлов", f"Директория {generated_dir_path} не найдена. Сначала сгенерируйте комбинации.")
            self.summary_label.setText("Сводка: Нет сгенерированных файлов.")
            return
        
        expected_draw_for_gen = last_draw_number + 1
        generated_files = []
        for f_name in os.listdir(generated_dir_path):
            match = re.match(r"combinations_for_draw_(\d+)_Контур_([AB])_?(\d{8}_\d{6})?\.csv", f_name)
            if match and int(match.group(1)) == expected_draw_for_gen:
                generated_files.append(os.path.join(generated_dir_path, f_name))
        
        if not generated_files:
            QMessageBox.warning(self, "Нет файлов генерации", f"Не найдено сгенерированных файлов для тиража №{expected_draw_for_gen}. Сначала сгенерируйте комбинации для этого тиража.")
            self.summary_label.setText(f"Сводка: Нет сгенерированных файлов для тиража №{expected_draw_for_gen}.")
            return

        overall_results_data = []
        overall_match_counts = {i: 0 for i in range(7)}
        threshold_5_plus_met = False
        
        all_generated_combinations_count = 0

        winning_draw_numbers_str = ", ".join(map(str, sorted(winning_numbers_list)))

        for g_file_path in generated_files:
            try:
                df_gen = pd.read_csv(g_file_path, encoding="utf-8-sig")
                all_generated_combinations_count += len(df_gen) 
                
                for i_combo, row in df_gen.iterrows():
                    generated_combination_list = [row[f'N{i}'] for i in range(1, 7) if pd.notna(row[f'N{i}'])]
                    generated_combination_set = set(generated_combination_list)
                    
                    num_matches = len(generated_combination_set & winning_numbers_set)
                    
                    matching_numbers = sorted(list(generated_combination_set & winning_numbers_set))
                    
                    if num_matches >= 3:
                        overall_results_data.append({
                            "№": i_combo + 1,
                            "Номера вышедшего тиража": winning_draw_numbers_str,
                            "Прогнозная комбинация": ", ".join(map(str, sorted(generated_combination_list))),
                            "Совпадающие номера": ", ".join(map(str, matching_numbers)),
                            "Количество совпадений": num_matches
                        })
                    
                    overall_match_counts[num_matches] += 1

                    if num_matches >= 5:
                        threshold_5_plus_met = True

            except Exception as e:
                QMessageBox.warning(self, "Ошибка загрузки/сверки файла", f"Ошибка обработки файла {os.path.basename(g_file_path)}: {str(e)}")
                continue

        self.display_comparison_results(overall_results_data)

        summary_text = f"<b>Сводка результатов автоматической сверки для тиража №{last_draw_number} (генерации для тиража №{expected_draw_for_gen}):</b><br>"
        summary_text += f"Всего проанализировано комбинаций: {all_generated_combinations_count}<br><br>"

        summary_text += "Совпадений (из всех сгенерированных комбинаций):<br>"
        for i in range(len(overall_match_counts) - 1, -1, -1):
            if overall_match_counts[i] > 0:
                summary_text += f"  {overall_match_counts[i]} комбинаций имели {i} совпадений<br>"
        
        if not threshold_5_plus_met:
            summary_text += "<br><font color='red'><b>Внимание: Порог 5+ совпадений НЕ достигнут. Рекомендуется запуск АКК!</b></font>"
            QMessageBox.warning(self, "Сигнал АКК", "Порог 5+ совпадений не достигнут. Рекомендуется запуск модуля АКК.")
        else:
            summary_text += "<br><font color='green'><b>Порог 5+ совпадений достигнут.</b></font>"
            
        self.summary_label.setText(summary_text)

        report_actual_draw_num = last_draw_number
        report_gen_for_draw_num = expected_draw_for_gen
        
        self._save_comparison_report(overall_results_data, overall_match_counts, report_actual_draw_num, report_gen_for_draw_num, all_generated_combinations_count, threshold_5_plus_met)

        QMessageBox.information(self, "Сверка завершена", "Автоматическая сверка успешно завершена.")

    def display_comparison_results(self, results_data):
        if not results_data:
            self.comparison_table.setRowCount(0)
            self.comparison_table.setColumnCount(0)
            return

        df_results = pd.DataFrame(results_data)
        
        self.comparison_table.setRowCount(len(df_results))
        self.comparison_table.setColumnCount(len(df_results.columns))
        self.comparison_table.setHorizontalHeaderLabels(df_results.columns)

        for i in range(len(df_results)):
            for j in range(len(df_results.columns)):
                val = str(df_results.iat[i, j])
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignCenter)
                self.comparison_table.setItem(i, j, item)
        
        self.comparison_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    
    def _save_comparison_report(self, results_data, match_counts, actual_draw_num, generated_for_draw_num, total_generated_combinations, threshold_met, contour_label=None, is_manual_mode=False):
        report_dir_path = os.path.join(self.project_root_dir, SVERKA_INF_DIR)
        os.makedirs(report_dir_path, exist_ok=True)

        timestamp_suffix = datetime.datetime.now().strftime("_%Y%m%d_%H%M%S")
        
        if is_manual_mode and contour_label:
            base_filename = f"sverka_draw_{actual_draw_num}_Контур_{contour_label}"
        else:
            base_filename = f"sverka_draw_{actual_draw_num}"

        report_filename_csv = os.path.join(report_dir_path, f"{base_filename}{timestamp_suffix}.csv")
        report_filename_summary = os.path.join(report_dir_path, f"{base_filename}{timestamp_suffix}.txt")
        
        df_report = pd.DataFrame(results_data)
        df_report.to_csv(report_filename_csv, index=False, encoding="utf-8-sig")

        with open(report_filename_summary, 'w', encoding='utf-8') as f:
            f.write(f"Отчет о сверке:\n")
            f.write(f"Дата сверки: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Фактический тираж (вышедший): №{actual_draw_num}\n")
            f.write(f"Генерации были сделаны для тиража: №{generated_for_draw_num}\n")
            f.write(f"Всего проанализировано комбинаций: {total_generated_combinations}\n\n")
            f.write("Сводка результатов:\n")
            for i in range(len(match_counts) - 1, -1, -1):
                if match_counts[i] > 0:
                    f.write(f"  {match_counts[i]} комбинаций имели {i} совпадений\n")
            
            f.write("\n---\n")
            if not threshold_met:
                f.write("Внимание: Порог 5+ совпадений НЕ достигнут. Рекомендуется запуск АКК!\n")
            else:
                f.write("Порог 5+ совпадений достигнут.\n")
        
        QMessageBox.information(self, "Отчет сохранен", f"Отчет сверки сохранен в:\n{os.path.basename(report_filename_csv)}\n{os.path.basename(report_filename_summary)}")