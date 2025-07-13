import os
import json
import datetime
import sys
import pandas as pd
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QGroupBox, QFormLayout, QHBoxLayout,
    QMessageBox, QPlainTextEdit, QDialog, QListWidget, QListWidgetItem, QLineEdit,
    QDoubleSpinBox, QSpinBox, QDialogButtonBox 
)
from PyQt5.QtCore import Qt, QTimer

# Импортируем из нового вспомогательного модуля
from utils.json_utils import load_json_config, save_json_config

# Импортируем модули АКК
from akk.LABCORE_80 import LABCORE_80
from akk.AKK import AKK
from akk.module_back import ReverseAnalysis


# Пути к файлам конфигурации и отчетам
CONFIG_DIR = "config"
LABCORE_80_CONFIG_FILE = os.path.join(CONFIG_DIR, "labcore_80_config.json")
AKK_CONFIG_FILE = os.path.join(CONFIG_DIR, "akk_config.json")
REVERSE_ANALYSIS_CONFIG_FILE = os.path.join(CONFIG_DIR, "reverse_analysis_config.json")
CORE_SETTINGS_FILE = os.path.join(CONFIG_DIR, "core_settings.json")

LABCORE_SAFE_DIR = "labcore_safe"
LABCORE_STATE_FILE = os.path.join(LABCORE_SAFE_DIR, "labcore_state.json")
LABCORE_DRAWS_FILE = "labcore_draws.csv"

AKK_REPORTS_DIR = os.path.join("reports", "AKK_Reports")
REVERSE_ANALYSIS_REPORTS_DIR = os.path.join("reports", "Reverse_Analysis_Reports")
SVERKA_INF_DIR = os.path.join("reports", "Сверка_inf")


# --- Класс для перенаправления stdout в QTextEdit ---
class QTextEditLogger(object):
    def __init__(self, editor):
        self.editor = editor
        self.terminal = sys.stdout # Сохраняем оригинальный stdout

    def write(self, message):
        self.editor.appendPlainText(message)
        self.terminal.write(message) # Пишем также в консоль
        self.editor.verticalScrollBar().setValue(self.editor.verticalScrollBar().maximum()) # Прокрутка вниз
        
    def flush(self):
        self.terminal.flush() # Необходим для совместимости с sys.stdout


class AkkSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Продвинутые Настройки АКК / LABCORE-80 / Тест-Лаборатория")
        self.setGeometry(200, 200, 500, 600) # Увеличим размер для нового лога Тест-Лаборатории
        self.setLayout(QVBoxLayout())

        self.project_root_dir = os.getcwd()

        self.akk_config = load_json_config(os.path.join(self.project_root_dir, AKK_CONFIG_FILE))
        self.labcore_80_config = load_json_config(os.path.join(self.project_root_dir, LABCORE_80_CONFIG_FILE))

        main_form_layout = QFormLayout()

        # --- Настройки АКК (Целевые Пороги) ---
        akk_settings_group = QGroupBox("Настройки АКК (Целевые Пороги)")
        akk_settings_layout = QFormLayout()

        self.target_5_match_spin = QDoubleSpinBox()
        self.target_5_match_spin.setRange(0.0, 100.0)
        self.target_5_match_spin.setSingleStep(1.0)
        self.target_5_match_spin.setSuffix(" %")
        self.target_5_match_spin.setValue(self.akk_config.get("target_5_match_percentage", 0.80) * 100)
        akk_settings_layout.addRow("Цель 5 попаданий:", self.target_5_match_spin)

        self.min_5_match_spin = QDoubleSpinBox()
        self.min_5_match_spin.setRange(0.0, 100.0)
        self.min_5_match_spin.setSingleStep(1.0)
        self.min_5_match_spin.setSuffix(" %")
        self.min_5_match_spin.setValue(self.akk_config.get("min_5_match_percentage", 0.15) * 100)
        akk_settings_layout.addRow("Мин. 5 попаданий:", self.min_5_match_spin)

        self.target_6_match_spin = QDoubleSpinBox()
        self.target_6_match_spin.setRange(0.0, 100.0)
        self.target_6_match_spin.setSingleStep(1.0)
        self.target_6_match_spin.setSuffix(" %")
        self.target_6_match_spin.setValue(self.akk_config.get("target_6_match_percentage", 0.40) * 100)
        akk_settings_layout.addRow("Цель 6 попаданий:", self.target_6_match_spin)

        self.min_6_match_spin = QDoubleSpinBox()
        self.min_6_match_spin.setRange(0.0, 100.0)
        self.min_6_match_spin.setSingleStep(1.0)
        self.min_6_match_spin.setSuffix(" %")
        self.min_6_match_spin.setValue(self.akk_config.get("min_6_match_percentage", 0.02) * 100)
        akk_settings_layout.addRow("Мин. 6 попаданий:", self.min_6_match_spin)

        akk_settings_group.setLayout(akk_settings_layout)
        main_form_layout.addRow(akk_settings_group)

        # --- Настройки LABCORE-80 (Количество циклов для обычного режима) ---
        labcore_settings_group = QGroupBox("Настройки LABCORE-80 (Для обычного режима)")
        labcore_settings_layout = QFormLayout()

        self.cycles_to_run_spin = QSpinBox()
        self.cycles_to_run_spin.setRange(1, 1000)
        self.cycles_to_run_spin.setValue(self.labcore_80_config.get("cycles_to_run", 1))
        labcore_settings_layout.addRow("Количество циклов для запуска:", self.cycles_to_run_spin)

        labcore_settings_group.setLayout(labcore_settings_layout)
        main_form_layout.addRow(labcore_settings_group)

        # --- Настройки Тест-Лаборатории ---
        test_lab_group = QGroupBox("Тест-Лаборатория (Отладка на прошлых тиражах)")
        test_lab_layout = QFormLayout()

        self.test_start_draw_spin = QSpinBox()
        self.test_start_draw_spin.setRange(1, 9999)
        self.test_start_draw_spin.setValue(1) # По умолчанию с первого тиража
        test_lab_layout.addRow("Начать с тиража №:", self.test_start_draw_spin)

        self.test_num_draws_spin = QSpinBox()
        self.test_num_draws_spin.setRange(1, 1000)
        self.test_num_draws_spin.setValue(30) # По умолчанию 30 тиражей
        test_lab_layout.addRow("Количество тиражей для анализа:", self.test_num_draws_spin)

        self.btn_run_test_lab = QPushButton("Запустить Тест-Лабораторию")
        self.btn_run_test_lab.clicked.connect(self._run_test_lab_mode)
        test_lab_layout.addRow("", self.btn_run_test_lab)

        self.test_lab_log = QPlainTextEdit() # Лог для вывода внутри диалога
        self.test_lab_log.setReadOnly(True)
        self.test_lab_log.setPlaceholderText("Лог выполнения Тест-Лаборатории...")
        test_lab_layout.addRow("Лог Тест-Лаборатории:", self.test_lab_log)

        test_lab_group.setLayout(test_lab_layout)
        main_form_layout.addRow(test_lab_group)


        self.layout().addLayout(main_form_layout)

        # Кнопки сохранения и закрытия диалога
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        self.layout().addWidget(button_box)

        self.original_stdout = sys.stdout # Сохраняем оригинальный stdout
        self.test_logger = QTextEditLogger(self.test_lab_log) # Создаем логгер для диалога

    def _save_settings(self):
        try:
            self.akk_config["target_5_match_percentage"] = self.target_5_match_spin.value() / 100.0
            self.akk_config["min_5_match_percentage"] = self.min_5_match_spin.value() / 100.0
            self.akk_config["target_6_match_percentage"] = self.target_6_match_spin.value() / 100.0
            self.akk_config["min_6_match_percentage"] = self.min_6_match_spin.value() / 100.0
            save_json_config(os.path.join(self.project_root_dir, AKK_CONFIG_FILE), self.akk_config)

            self.labcore_80_config["cycles_to_run"] = self.cycles_to_run_spin.value()
            save_json_config(os.path.join(self.project_root_dir, LABCORE_80_CONFIG_FILE), self.labcore_80_config)

            QMessageBox.information(self, "Сохранение", "Настройки успешно сохранены!")
            # self.accept() # Не закрываем диалог, если пользователь хочет запустить тест
        except Exception as e:
            QMessageBox.critical(self, "Ошибка сохранения", f"Не удалось сохранить настройки: {e}")

    def _run_test_lab_mode(self):
        """Запускает LABCORE-80 в режиме Тест-Лаборатории."""
        start_draw = self.test_start_draw_spin.value()
        num_draws = self.test_num_draws_spin.value()

        # Проверяем наличие labcore_draws.csv и его содержимое
        draws_filepath = os.path.join(self.project_root_dir, LABCORE_DRAWS_FILE)
        if not os.path.exists(draws_filepath) or os.stat(draws_filepath).st_size == 0:
            QMessageBox.warning(self, "Ошибка Тест-Лаборатории", "Файл labcore_draws.csv не найден или пуст. Тест невозможен.")
            return

        try:
            draws_df = pd.read_csv(draws_filepath, encoding="utf-8-sig")
            if draws_df.empty or 'Тираж' not in draws_df.columns:
                QMessageBox.warning(self, "Ошибка Тест-Лаборатории", "Файл labcore_draws.csv пуст или не содержит колонку 'Тираж'. Тест невозможен.")
                return
            
            max_history_draw = draws_df['Тираж'].max()
            if start_draw > max_history_draw:
                QMessageBox.warning(self, "Ошибка Тест-Лаборатории", f"Начальный тираж №{start_draw} не найден в истории. Максимальный тираж в истории: №{max_history_draw}.")
                return

            parent_akk_tab = self.parent()
            if not parent_akk_tab or not parent_akk_tab.labcore_80_instance:
                QMessageBox.critical(self, "Ошибка Тест-Лаборатории", "Модуль LABCORE-80 не инициализирован в основной вкладке.")
                return

            self.test_lab_log.clear() # Очищаем лог перед новым тестом
            self.test_lab_log.appendPlainText(f"--- Запуск Тест-Лаборатории с тиража №{start_draw}, количество: {num_draws} ---")
            
            # Перенаправляем stdout в лог диалога
            sys.stdout = self.test_logger
            
            # Запускаем LABCORE-80 в режиме исторического тестирования
            parent_akk_tab.labcore_80_instance.run_historical_test_cycle(
                start_draw=start_draw, 
                num_draws=num_draws,
                log_callback=self.test_lab_log.appendPlainText # Передаем метод для логирования
            )

            # Восстанавливаем оригинальный stdout
            sys.stdout = self.original_stdout
            self.test_lab_log.appendPlainText(f"\n--- Тест-Лаборатория завершена. ---")
            QMessageBox.information(self, "Тест-Лаборатория", "Выполнение Тест-Лаборатории завершено. Смотрите лог для деталей.")

        except Exception as e:
            QMessageBox.critical(self, "Ошибка Тест-Лаборатории", f"Произошла ошибка при запуске теста: {e}")
            self.test_lab_log.appendPlainText(f"\n--- ОШИБКА Тест-Лаборатории: {e} ---")
            sys.stdout = self.original_stdout # Восстанавливаем stdout в случае ошибки


class AkkTab(QWidget):
    def __init__(self):
        super().__init__()
        self.setLayout(QVBoxLayout())

        self.project_root_dir = os.getcwd()

        self.header_label = QLabel("Управление и Мониторинг LABCORE-80 / АКК") 
        self.header_label.setStyleSheet("font-weight: bold; font-size: 16px;")
        self.layout().addWidget(self.header_label, alignment=Qt.AlignCenter)

        # --- Раздел "LABCORE-80: Управление Циклом" ---
        labcore_80_group = QGroupBox("LABCORE-80: Управление Циклом")
        labcore_80_layout = QFormLayout()

        self.current_phase_label = QLabel("Текущая фаза: Ожидание")
        labcore_80_layout.addRow("Статус:", self.current_phase_label)

        self.cycle_count_label = QLabel("Выполнено циклов: 0")
        labcore_80_layout.addRow("Циклы:", self.cycle_count_label)

        self.last_successful_draw_label = QLabel("Последний тираж: N/A")
        labcore_80_layout.addRow("Обработано тиражей:", self.last_successful_draw_label)

        self.last_generated_draw_label = QLabel("Комбинации для тиража: N/A")
        labcore_80_layout.addRow("Сгенерировано для тиража:", self.last_generated_draw_label)

        btn_run_labcore_80_cycle = QPushButton("Запустить цикл LABCORE-80")
        btn_run_labcore_80_cycle.clicked.connect(self._run_labcore_80_cycle)
        labcore_80_layout.addRow("", btn_run_labcore_80_cycle)

        labcore_80_group.setLayout(labcore_80_layout)
        self.layout().addWidget(labcore_80_group)

        # --- Раздел "Отчеты и История АКК" ---
        reports_history_group = QGroupBox("Отчеты и История Анализа")
        reports_history_layout = QHBoxLayout()

        btn_view_akk_reports = QPushButton("Просмотреть Отчеты АКК")
        btn_view_akk_reports.clicked.connect(lambda: self._view_reports_folder(AKK_REPORTS_DIR))
        reports_history_layout.addWidget(btn_view_akk_reports)

        btn_view_reverse_reports = QPushButton("Просмотреть Отчеты Обратного Анализа")
        btn_view_reverse_reports.clicked.connect(lambda: self._view_reports_folder(REVERSE_ANALYSIS_REPORTS_DIR))
        reports_history_layout.addWidget(btn_view_reverse_reports)
        
        btn_view_sverka_reports = QPushButton("Просмотреть Отчеты Сверки")
        btn_view_sverka_reports.clicked.connect(lambda: self._view_reports_folder(SVERKA_INF_DIR))
        reports_history_layout.addWidget(btn_view_sverka_reports)


        reports_history_group.setLayout(reports_history_layout)
        self.layout().addWidget(reports_history_group)

        # --- Раздел "Настройки АКК" (продвинутые) ---
        akk_settings_group = QGroupBox("Продвинутые Настройки АКК")
        akk_settings_layout = QVBoxLayout()
        akk_settings_layout.addWidget(QLabel("<i>Эти настройки влияют на логику адаптации системы. Изменяйте с осторожностью.</i>"))
        btn_open_akk_settings = QPushButton("Открыть Продвинутые Настройки АКК")
        btn_open_akk_settings.clicked.connect(self._open_advanced_akk_settings)
        akk_settings_layout.addWidget(btn_open_akk_settings)
        akk_settings_group.setLayout(akk_settings_layout)
        self.layout().addWidget(akk_settings_group)

        # --- Журнал действий АКК / LABCORE ---
        log_group = QGroupBox("Журнал LABCORE-80 / АКК")
        log_layout = QVBoxLayout()
        self.akk_log_display = QPlainTextEdit()
        self.akk_log_display.setReadOnly(True)
        self.akk_log_display.setPlaceholderText("Журнал действий LABCORE-80 и АКК.")
        log_layout.addWidget(self.akk_log_display)
        log_group.setLayout(log_layout)
        self.layout().addWidget(log_group)

        self.layout().addStretch(1)

        # Инициализация модулей LABCORE-80 и АКК
        self.labcore_80_instance = None
        self.akk_instance = None
        self._initialize_akk_modules()
        self._update_labcore_80_status_labels()

        # Таймер для имитации выполнения цикла
        self.labcore_80_timer = QTimer(self)
        self.labcore_80_timer.timeout.connect(self._simulate_labcore_80_step)
        self.current_cycle_steps = []
        self.current_step_index = 0
        self.current_mock_draw_number = 0
        self.total_cycles_to_run = 1
        self.completed_cycles_in_run = 0

        # Перенаправляем стандартный вывод в наш лог
        sys.stdout = QTextEditLogger(self.akk_log_display)

    def _load_config(self, filepath):
        return load_json_config(filepath)

    def _ensure_config_exists(self, filepath, default_content):
        if not os.path.exists(filepath):
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(default_content, f, indent=4, ensure_ascii=False)
                self.append_log(f"Создан файл конфигурации: {os.path.basename(filepath)}")
            except Exception as e:
                self.append_log(f"Ошибка создания конфига {os.path.basename(filepath)}: {e}")
                QMessageBox.critical(self, "Ошибка", f"Не удалось создать файл конфигурации: {os.path.basename(filepath)}: {e}")
        else:
            try:
                current_config = load_json_config(filepath)
                updated = False
                for key, value in default_content.items():
                    if key not in current_config:
                        current_config[key] = value
                        updated = True
                if updated:
                    with open(filepath, 'w', encoding='utf-8') as f:
                        json.dump(current_config, f, indent=4, ensure_ascii=False)
                    self.append_log(f"Обновлен файл конфигурации: {os.path.basename(filepath)} новыми полями.")
            except Exception as e:
                self.append_log(f"Ошибка обновления конфига {os.path.basename(filepath)}: {e}")


    def _initialize_akk_modules(self):
        self._ensure_config_exists(os.path.join(self.project_root_dir, AKK_CONFIG_FILE), {
            "min_5_plus_threshold": 1, "adjustment_strength": 0.05, "adjustment_history": [],
            "target_5_match_percentage": 0.80, "min_5_match_percentage": 0.15,
            "target_6_match_percentage": 0.40, "min_6_match_percentage": 0.02
        })
        self._ensure_config_exists(os.path.join(self.project_root_dir, LABCORE_80_CONFIG_FILE), {
            "current_phase": "Idle", "cycle_count": 0, "log_level": "INFO", "cycles_to_run": 1
        })
        self._ensure_config_exists(os.path.join(self.project_root_dir, REVERSE_ANALYSIS_CONFIG_FILE), {
            "top_missing_limit": 10, "top_extra_limit": 10
        })
        self._ensure_config_exists(os.path.join(self.project_root_dir, LABCORE_STATE_FILE), {
            "last_successful_draw": 0, "last_generated_draw": 0, "last_analysis_draw": 0
        })
        self._ensure_config_exists(os.path.join(self.project_root_dir, CORE_SETTINGS_FILE), {
            "version": "1.0", "mode": "hybrid", "autonomous": False, "boost": 2.6,
            "psw_weight": 1.5, "glue_anchor": True, "stabilization_method": "average_last_30_draws",
            "structure_quotas": {}
        })
        self._ensure_config_exists(os.path.join(self.project_root_dir, CONFIG_DIR, "labcore_A_settings.json"), {
            "temperature": 0.7, "diversity_factor": 1.2, "consistency_threshold": 0.95,
            "history_window": 50, "prediction_boost": 1.05
        })
        self._ensure_config_exists(os.path.join(self.project_root_dir, CONFIG_DIR, "labcore_B_settings.json"), {
            "aggressiveness": 1.5, "exploratory_factor": 0.2, "novelty_weight": 0.8,
            "re_evaluation_interval": 3, "dynamic_threshold_adjustment": True
        })


        try:
            labcore_80_config_path = os.path.join(self.project_root_dir, LABCORE_80_CONFIG_FILE)
            self.labcore_80_instance = LABCORE_80(self.project_root_dir, labcore_80_config_path)
            self.append_log("LABCORE-80 модуль инициализирован.")
        except Exception as e:
            self.append_log(f"Ошибка инициализации LABCORE-80: {e}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось инициализировать LABCORE-80: {e}")

        try:
            akk_config_path = os.path.join(self.project_root_dir, AKK_CONFIG_FILE)
            self.akk_instance = AKK(akk_config_path, self.project_root_dir)
            self.append_log("АКК модуль инициализирован.")
        except Exception as e:
            self.append_log(f"Ошибка инициализации АКК: {e}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось инициализировать АКК: {e}")


    def _update_labcore_80_status_labels(self):
        """Обновляет метки статуса LABCORE-80 из его состояния."""
        if self.labcore_80_instance:
            self.current_phase_label.setText(f"Текущая фаза: {self.labcore_80_instance.current_phase}")
            self.cycle_count_label.setText(f"Выполнено циклов: {self.labcore_80_instance.cycle_count}")
            self.last_successful_draw_label.setText(f"Обработано тиражей: №{self.labcore_80_instance.labcore_state.get('last_successful_draw', 'N/A')}")
            self.last_generated_draw_label.setText(f"Сгенерировано для тиража: №{self.labcore_80_instance.labcore_state.get('last_generated_draw', 'N/A')}")
        else:
            self.current_phase_label.setText("Текущая фаза: Модуль не инициализирован")

    def _get_next_draw_number(self):
        """Определяет следующий номер тиража из labcore_draws.csv."""
        draws_filepath = os.path.join(self.project_root_dir, LABCORE_DRAWS_FILE)
        if not os.path.exists(draws_filepath):
            QMessageBox.warning(self, "Ошибка", f"Файл {LABCORE_DRAWS_FILE} не найден. Невозможно определить следующий тираж. Используем 1.")
            return 1
        try:
            draws_df = pd.read_csv(draws_filepath, encoding="utf-8-sig")
            if draws_df.empty or 'Тираж' not in draws_df.columns:
                QMessageBox.warning(self, "Ошибка", f"Файл {LABCORE_DRAWS_FILE} пуст или не содержит колонку 'Тираж'. Используем 1.")
                return 1
            last_draw = draws_df['Тираж'].max()
            return int(last_draw) + 1
        except Exception as e:
            QMessageBox.critical(self, "Ошибка чтения тиражей", f"Не удалось прочитать {LABCORE_DRAWS_FILE}: {e}. Используем 1.")
            return 1

    def _run_labcore_80_cycle(self):
        """Запускает один или несколько циклов LABCORE-80 вручную."""
        if not self.labcore_80_instance:
            QMessageBox.warning(self, "Ошибка", "Модуль LABCORE-80 не инициализирован. Пожалуйста, перезапустите программу.")
            return
        
        labcore_80_config_path = os.path.join(self.project_root_dir, LABCORE_80_CONFIG_FILE)
        current_labcore_config = self._load_config(labcore_80_config_path) 
        self.total_cycles_to_run = current_labcore_config.get("cycles_to_run", 1)
        self.completed_cycles_in_run = 0

        self.current_mock_draw_number = self._get_next_draw_number()
        self.append_log(f"Запуск {self.total_cycles_to_run} циклов LABCORE-80, начиная с тиража №{self.current_mock_draw_number}...")
        
        self._start_single_labcore_cycle()

    def _start_single_labcore_cycle(self):
        """Начинает имитацию одного цикла LABCORE-80."""
        if self.completed_cycles_in_run >= self.total_cycles_to_run:
            self.append_log(f"Все {self.total_cycles_to_run} циклов LABCORE-80 завершены.")
            QMessageBox.information(self, "Цикл LABCORE-80", f"Все {self.total_cycles_to_run} циклов LABCORE-80 успешно завершены.")
            self._update_labcore_80_status_labels()
            return

        self.append_log(f"\n--- Запуск цикла {self.completed_cycles_in_run + 1}/{self.total_cycles_to_run} для тиража №{self.current_mock_draw_number} ---")
        self.current_step_index = 0
        self.full_cycle_phases = [
            f"Запуск цикла LABCORE-80 для тиража №{self.current_mock_draw_number}...",
            "Проверка нового тиража...",
            "Выполнение сверки...",
            "Анализ АКК и принятие решений...",
            "Выполнение корректировок / переобучения (если необходимо)...",
            "Генерация комбинаций...",
            "Формирование и отправка отчётов...",
            "Цикл завершен."
        ]
        self.labcore_80_timer.start(1000)

    def _simulate_labcore_80_step(self):
        """Имитирует один шаг цикла LABCORE-80 и обновляет UI."""
        if self.current_step_index < len(self.full_cycle_phases):
            phase_message = self.full_cycle_phases[self.current_step_index]
            self.append_log(f"Фаза: {phase_message}")
            self.current_phase_label.setText(f"Текущая фаза: {phase_message}")
            self.current_step_index += 1
        else:
            self.labcore_80_timer.stop()
            self.append_log("Текущий цикл LABCORE-80 завершен.")
            self.completed_cycles_in_run += 1
            
            if self.labcore_80_instance:
                self.labcore_80_instance.cycle_count += 1
                self.labcore_80_instance.current_phase = "Idle"
                self.labcore_80_instance.labcore_state["last_successful_draw"] = self.current_mock_draw_number
                self.labcore_80_instance.labcore_state["last_generated_draw"] = self.current_mock_draw_number + 1
                self.labcore_80_instance._save_labcore_state()
                self.labcore_80_instance._save_config() 
            
            self.current_mock_draw_number += 1
            self._update_labcore_80_status_labels()

            if self.completed_cycles_in_run < self.total_cycles_to_run:
                self._start_single_labcore_cycle()
            else:
                self.append_log(f"Все {self.total_cycles_to_run} циклов LABCORE-80 завершены.")
                QMessageBox.information(self, "Цикл LABCORE-80", f"Все {self.total_cycles_to_run} циклов LABCORE-80 успешно завершены.")


    def _open_advanced_akk_settings(self):
        dialog = AkkSettingsDialog(self)
        if dialog.exec_():
            self.append_log("Настройки АКК/LABCORE-80 обновлены через диалог.")
            self._initialize_akk_modules()
            self._update_labcore_80_status_labels()

    def _view_reports_folder(self, folder_name):
        folder_path = os.path.join(self.project_root_dir, folder_name)
        if not os.path.exists(folder_path):
            QMessageBox.information(self, "Папка не найдена", f"Папка с отчетами '{folder_name}' не существует.")
            self.append_log(f"Попытка открыть несуществующую папку: {folder_path}")
            return
        
        try:
            if sys.platform == "win32":
                os.startfile(folder_path)
            elif sys.platform == "darwin":
                os.system(f"open \"{folder_path}\"")
            else:
                os.system(f"xdg-open \"{folder_path}\"")
            self.append_log(f"Открыта папка: {folder_path}")
        except Exception as e:
            QMessageBox.warning(self, "Ошибка открытия папки", f"Не удалось открыть папку: {e}")
            self.append_log(f"Ошибка открытия папки {folder_path}: {e}")

    def append_log(self, message):
        timestamp = datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        self.akk_log_display.appendPlainText(f"{timestamp} {message}")
        self.akk_log_display.verticalScrollBar().setValue(self.akk_log_display.verticalScrollBar().maximum())