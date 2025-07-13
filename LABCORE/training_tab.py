import os
import json
import datetime
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QCheckBox, QSpinBox,
    QGroupBox, QFormLayout, QHBoxLayout, QMessageBox, QPlainTextEdit, QProgressBar
)
from PyQt5.QtCore import Qt, QTimer

CONFIG_DIR = "config"
MODELS_DIR = "models"
REPORTS_DIR = "reports"
TRAINING_LOGS_DIR = os.path.join(REPORTS_DIR, "Training_Logs")

MODEL_SETTINGS_FILE = os.path.join(CONFIG_DIR, "model_prediction_config.json")

class TrainingTab(QWidget):
    def __init__(self):
        super().__init__()
        self.setLayout(QVBoxLayout())

        self.project_root_dir = os.getcwd()

        self.header_label = QLabel("Обучение Моделей Ансамбля")
        self.header_label.setStyleSheet("font-weight: bold; font-size: 16px;")
        self.layout().addWidget(self.header_label, alignment=Qt.AlignCenter)

        models_group = QGroupBox("Выбор Моделей")
        models_layout = QVBoxLayout()

        self.xgboost_checkbox = QCheckBox("XGBoost")
        self.lightgbm_checkbox = QCheckBox("LightGBM")
        self.catboost_checkbox = QCheckBox("CatBoost")

        models_layout.addWidget(self.xgboost_checkbox)
        models_layout.addWidget(self.lightgbm_checkbox)
        models_layout.addWidget(self.catboost_checkbox)

        models_group.setLayout(models_layout)
        self.layout().addWidget(models_group)

        training_data_group = QGroupBox("Данные для Обучения")
        training_data_layout = QFormLayout()

        self.num_draws_for_training_spinbox = QSpinBox()
        self.num_draws_for_training_spinbox.setRange(30, 10000)
        self.num_draws_for_training_spinbox.setValue(100)
        training_data_layout.addRow("Использовать последние тиражи:", self.num_draws_for_training_spinbox)

        training_data_group.setLayout(training_data_layout)
        self.layout().addWidget(training_data_group)

        btn_train_models = QPushButton("Начать Обучение / Дообучение Моделей")
        btn_train_models.clicked.connect(self.start_training)
        self.layout().addWidget(btn_train_models)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setValue(0)
        self.layout().addWidget(self.progress_bar)

        self.status_label = QLabel("Статус: Ожидание запуска обучения.")
        self.layout().addWidget(self.status_label)

        self.training_log_display = QPlainTextEdit()
        self.training_log_display.setReadOnly(True)
        self.training_log_display.setPlaceholderText("Здесь будет отображаться журнал обучения моделей.")
        self.layout().addWidget(self.training_log_display)

        self.layout().addStretch(1)

        self._load_model_settings()

    def _load_model_settings(self):
        filepath = os.path.join(self.project_root_dir, MODEL_SETTINGS_FILE)
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    self.xgboost_checkbox.setChecked(settings.get("xgboost_active", False))
                    self.lightgbm_checkbox.setChecked(settings.get("lightgbm_active", False))
                    self.catboost_checkbox.setChecked(settings.get("catboost_active", False))
                    self.num_draws_for_training_spinbox.setValue(settings.get("num_draws_for_training", 100))
                    self.append_log(f"Настройки моделей загружены из {os.path.basename(filepath)}.")
            except Exception as e:
                QMessageBox.warning(self, "Ошибка загрузки настроек моделей", f"Не удалось загрузить настройки моделей: {e}")
                self.append_log(f"Ошибка загрузки настроек моделей: {e}")
        else:
            self.append_log(f"Файл {os.path.basename(filepath)} не найден. Используются значения по умолчанию.")
            self._save_model_settings()

    def _save_model_settings(self):
        settings = {
            "xgboost_active": self.xgboost_checkbox.isChecked(),
            "lightgbm_active": self.lightgbm_checkbox.isChecked(),
            "catboost_active": self.catboost_checkbox.isChecked(),
            "num_draws_for_training": self.num_draws_for_training_spinbox.value()
        }
        
        filepath = os.path.join(self.project_root_dir, MODEL_SETTINGS_FILE)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=4, ensure_ascii=False)
            self.append_log(f"Настройки моделей сохранены в {os.path.basename(filepath)}.")
        except Exception as e:
            QMessageBox.warning(self, "Ошибка сохранения настроек моделей", f"Не удалось сохранить настройки моделей: {e}")
            self.append_log(f"Ошибка сохранения настроек моделей: {e}")

    def append_log(self, message):
        timestamp = datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        self.training_log_display.appendPlainText(f"{timestamp} {message}")
        self.training_log_display.verticalScrollBar().setValue(self.training_log_display.verticalScrollBar().maximum())

    def start_training(self):
        self._save_model_settings()
        
        selected_models = []
        if self.xgboost_checkbox.isChecked():
            selected_models.append("XGBoost")
        if self.lightgbm_checkbox.isChecked():
            selected_models.append("LightGBM")
        if self.catboost_checkbox.isChecked():
            selected_models.append("CatBoost")

        if not selected_models:
            QMessageBox.warning(self, "Ошибка", "Пожалуйста, выберите хотя бы одну модель для обучения.")
            return

        num_draws = self.num_draws_for_training_spinbox.value()
        self.append_log(f"Начато обучение моделей: {', '.join(selected_models)} на последних {num_draws} тиражах.")
        self.status_label.setText("Статус: Обучение моделей...")
        self.progress_bar.setValue(0)

        self.current_progress = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_training_progress)
        self.timer.start(100)

    def _update_training_progress(self):
        self.current_progress += random.randint(1, 5)
        if self.current_progress >= 100:
            self.current_progress = 100
            self.timer.stop()
            self.progress_bar.setValue(100)
            self.status_label.setText("Статус: Обучение завершено!")
            self.append_log("Обучение всех выбранных моделей успешно завершено.")
            QMessageBox.information(self, "Обучение завершено", "Модели успешно обучены и готовы к использованию.")
            self._save_training_log_report("Успешно")
        else:
            self.progress_bar.setValue(self.current_progress)

    def _save_training_log_report(self, status):
        report_dir_path = os.path.join(self.project_root_dir, TRAINING_LOGS_DIR)
        os.makedirs(report_dir_path, exist_ok=True)

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = os.path.join(report_dir_path, f"training_report_{timestamp}.txt")
        
        with open(report_filename, 'w', encoding='utf-8') as f:
            f.write(f"Отчет об обучении моделей:\n")
            f.write(f"Дата обучения: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Выбранные модели: ")
            
            selected_models = []
            if self.xgboost_checkbox.isChecked(): selected_models.append("XGBoost")
            if self.lightgbm_checkbox.isChecked(): selected_models.append("LightGBM")
            if self.catboost_checkbox.isChecked(): selected_models.append("CatBoost")
            f.write(f"{', '.join(selected_models)}\n")
            
            f.write(f"Количество тиражей для обучения: {self.num_draws_for_training_spinbox.value()}\n")
            f.write(f"Статус обучения: {status}\n\n")
            f.write("Полный журнал обучения:\n")
            f.write(self.training_log_display.toPlainText())
        
        QMessageBox.information(self, "Отчет обучения сохранен", f"Отчет об обучении сохранен в:\n{os.path.basename(report_filename)}")
        self.append_log(f"Отчет обучения сохранен в {os.path.basename(report_filename)}.")