import os
import pandas as pd
import json
import random
import datetime

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QLabel, QSpinBox, QHBoxLayout,
    QComboBox, QLineEdit, QCheckBox, QGroupBox, QFormLayout, QMessageBox,
    QDialog, QDialogButtonBox, QDoubleSpinBox
)
from PyQt5.QtCore import Qt

LABCORE_DRAWS_FILE_NAME = "labcore_draws.csv"
CONFIG_DIR_NAME = "config"
GENERATED_DIR_NAME = "generated"

class GenerationSettingsDialog(QDialog):
    def __init__(self, parent=None, config_core={}, config_softpool={}, config_quotas={}, pool_stats={}):
        super().__init__(parent)
        self.setWindowTitle("Настройки Генерации")
        self.setGeometry(200, 200, 600, 450)

        self.config_core = config_core
        self.config_softpool = config_softpool
        self.config_quotas = config_quotas
        self.pool_stats = pool_stats

        main_layout = QVBoxLayout(self)

        settings_group = QGroupBox("Общие Настройки Генерации")
        settings_layout = QFormLayout()

        self.boost_spinbox = QDoubleSpinBox()
        self.boost_spinbox.setRange(0.0, 5.0)
        self.boost_spinbox.setSingleStep(0.1)
        self.boost_spinbox.setValue(self.config_core.get("boost", 1.0))
        settings_layout.addRow("Усиление Glue/Anchor (Boost):", self.boost_spinbox)

        self.psw_weight_spinbox = QDoubleSpinBox()
        self.psw_weight_spinbox.setRange(0.0, 5.0)
        self.psw_weight_spinbox.setSingleStep(0.1)
        self.psw_weight_spinbox.setValue(self.config_core.get("psw_weight", 1.0))
        settings_layout.addRow("Усиление номеров по PSW:", self.psw_weight_spinbox)

        self.glue_anchor_checkbox = QCheckBox("Включить Glue/Anchor")
        self.glue_anchor_checkbox.setChecked(self.config_core.get("glue_anchor", False))
        settings_layout.addRow("", self.glue_anchor_checkbox)

        self.stabilization_method_combo = QComboBox()
        self.stabilization_method_combo.addItems(["average_last_30_draws", "dynamic_adaptive"])
        self.stabilization_method_combo.setCurrentText(self.config_core.get("stabilization_method", "average_last_30_draws"))
        settings_layout.addRow("Метод стабилизации:", self.stabilization_method_combo)
        
        settings_group.setLayout(settings_layout)
        main_layout.addWidget(settings_group)

        softpool_group = QGroupBox("SoftPool Настройки")
        softpool_layout = QFormLayout()

        self.h_zone_edit = QLineEdit(", ".join(map(str, self.config_softpool.get("H_zone", []))))
        softpool_layout.addRow("H-зона (через запятую):", self.h_zone_edit)

        self.m_zone_edit = QLineEdit(", ".join(map(str, self.config_softpool.get("M_zone", []))))
        softpool_layout.addRow("M-зона (через запятую):", self.m_zone_edit)

        self.l_zone_edit = QLineEdit(", ".join(map(str, self.config_softpool.get("L_zone", []))))
        softpool_layout.addRow("L-зона (через запятую):", self.l_zone_edit)

        self.exclude_edit = QLineEdit(", ".join(map(str, self.config_softpool.get("exclude", []))))
        softpool_layout.addRow("Исключить номера (через запятую):", self.exclude_edit)

        self.softpool_boost_spinbox = QDoubleSpinBox()
        self.softpool_boost_spinbox.setRange(0.0, 5.0)
        self.softpool_boost_spinbox.setSingleStep(0.1)
        self.softpool_boost_spinbox.setValue(self.config_softpool.get("boost", 1.0))
        softpool_layout.addRow("Усиление SoftPool:", self.softpool_boost_spinbox)
        
        softpool_group.setLayout(softpool_layout)
        main_layout.addWidget(softpool_group)

        quota_group = QGroupBox("Распределение Hot/Mid/Cold")
        quota_layout = QFormLayout()

        self.h_quota_spinbox = QSpinBox()
        self.h_quota_spinbox.setRange(0, 100)
        self.h_quota_spinbox.setValue(self.config_quotas.get("H", 0))
        quota_layout.addRow("Hot (%):", self.h_quota_spinbox)

        self.m_quota_spinbox = QSpinBox()
        self.m_quota_spinbox.setRange(0, 100)
        self.m_quota_spinbox.setValue(self.config_quotas.get("M", 0))
        quota_layout.addRow("Mid (%):", self.m_quota_spinbox)

        self.c_quota_spinbox = QSpinBox()
        self.c_quota_spinbox.setRange(0, 100)
        self.c_quota_spinbox.setValue(self.config_quotas.get("C", 0))
        quota_layout.addRow("Cold (%):", self.c_quota_spinbox)

        quota_group.setLayout(quota_layout)
        main_layout.addWidget(quota_group)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)

    def get_settings(self):
        settings = {
            "core": {
                "boost": self.boost_spinbox.value(),
                "psw_weight": self.psw_weight_spinbox.value(),
                "glue_anchor": self.glue_anchor_checkbox.isChecked(),
                "stabilization_method": self.stabilization_method_combo.currentText()
            },
            "softpool": {
                "H_zone": [int(x.strip()) for x in self.h_zone_edit.text().split(',') if x.strip()],
                "M_zone": [int(x.strip()) for x in self.m_zone_edit.text().split(',') if x.strip()],
                "L_zone": [int(x.strip()) for x in self.l_zone_edit.text().split(',') if x.strip()],
                "exclude": [int(x.strip()) for x in self.exclude_edit.text().split(',') if x.strip()],
                "boost": self.softpool_boost_spinbox.value()
            },
            "quotas": {
                "H": self.h_quota_spinbox.value(),
                "M": self.m_quota_spinbox.value(),
                "C": self.c_quota_spinbox.value()
            }
        }
        return settings

class GenerationTab(QWidget):
    def __init__(self):
        super().__init__()
        self.setLayout(QVBoxLayout())

        current_script_dir = os.path.dirname(os.path.abspath(__file__))
        self.project_root_dir = os.path.abspath(os.path.join(current_script_dir, os.pardir))
        
        self.config_core = self._load_config(os.path.join(self.project_root_dir, CONFIG_DIR_NAME, "core_settings.json"))
        self.config_softpool = self._load_config(os.path.join(self.project_root_dir, CONFIG_DIR_NAME, "softpool_config.json"))
        self.config_quotas = self._load_config(os.path.join(self.project_root_dir, CONFIG_DIR_NAME, "quota_config.json"))
        self.pool_stats = self._load_config(os.path.join(self.project_root_dir, CONFIG_DIR_NAME, "pool_stats.json"))
        
        self.draws_df = self._load_draws(os.path.join(self.project_root_dir, LABCORE_DRAWS_FILE_NAME))

        top_layout = QVBoxLayout()

        draw_num_mode_group = QGroupBox("Номер тиража для генерации")
        draw_num_mode_layout = QVBoxLayout()

        self.auto_draw_num_checkbox = QCheckBox("Автоматическое определение следующего тиража")
        self.auto_draw_num_checkbox.setChecked(True)
        self.auto_draw_num_checkbox.stateChanged.connect(self._toggle_draw_num_input)
        draw_num_mode_layout.addWidget(self.auto_draw_num_checkbox)

        self.manual_draw_num_spinbox = QSpinBox()
        self.manual_draw_num_spinbox.setRange(1, 9999)
        self.manual_draw_num_spinbox.setValue(self._get_next_draw_number())
        draw_num_mode_layout.addWidget(self.manual_draw_num_spinbox)
        
        draw_num_mode_group.setLayout(draw_num_mode_layout)
        top_layout.addWidget(draw_num_mode_group)

        basic_settings_layout = QHBoxLayout()

        basic_settings_layout.addWidget(QLabel("Количество комбинаций:"))
        self.num_combinations_spinbox = QSpinBox()
        self.num_combinations_spinbox.setRange(1, 1000)
        self.num_combinations_spinbox.setValue(100)
        basic_settings_layout.addWidget(self.num_combinations_spinbox)

        basic_settings_layout.addWidget(QLabel("Контур:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Контур A (Stable)", "Контур B (Experimental)"])
        current_mode_setting = self.config_core.get("mode", "hybrid")
        if current_mode_setting == "hybrid":
            self.mode_combo.setCurrentText("Контур A (Stable)")
        elif current_mode_setting == "experimental":
            self.mode_combo.setCurrentText("Контур B (Experimental)")
        basic_settings_layout.addWidget(self.mode_combo)

        btn_open_settings = QPushButton("Настройки генерации...")
        btn_open_settings.clicked.connect(self.open_generation_settings)
        basic_settings_layout.addWidget(btn_open_settings)

        top_layout.addLayout(basic_settings_layout)

        self.layout().addLayout(top_layout)
        
        btn_generate = QPushButton("Сгенерировать Комбинации")
        btn_generate.clicked.connect(self.generate_combinations)
        self.layout().addWidget(btn_generate)

        self.status_label = QLabel("Нажмите 'Сгенерировать' для начала.")
        self.layout().addWidget(self.status_label)

        self.layout().addStretch(1)
        
        self._toggle_draw_num_input()


    def _toggle_draw_num_input(self):
        """Переключает доступность ручного ввода номера тиража."""
        if self.auto_draw_num_checkbox.isChecked():
            self.manual_draw_num_spinbox.setReadOnly(True)
            self.manual_draw_num_spinbox.setButtonSymbols(QSpinBox.NoButtons)
            self.manual_draw_num_spinbox.setValue(self._get_next_draw_number())
        else:
            self.manual_draw_num_spinbox.setReadOnly(False)
            self.manual_draw_num_spinbox.setButtonSymbols(QSpinBox.UpDownArrows)


    def _load_config(self, filename):
        if os.path.exists(filename):
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError as e:
                QMessageBox.warning(self, "Ошибка загрузки конфигурации", f"Ошибка чтения {filename}: {e}")
                return {}
        else:
            QMessageBox.warning(self, "Отсутствует файл конфигурации", f"Файл {filename} не найден. Используются значения по умолчанию.")
            return {}

    def _load_draws(self, filename):
        if os.path.exists(filename):
            try:
                df = pd.read_csv(filename, encoding="utf-8-sig")
                for i in range(1, 7):
                    df[f'N{i}'] = pd.to_numeric(df[f'N{i}'], errors='coerce').astype('Int64')
                return df
            except Exception as e:
                QMessageBox.warning(self, "Ошибка загрузки тиражей", f"Не удалось загрузить {filename}: {e}")
                return pd.DataFrame()
        else:
            QMessageBox.warning(self, "Отсутствует файл тиражей", f"Файл {filename} не найден.")
            return pd.DataFrame()

    def _get_next_draw_number(self):
        filepath = os.path.join(self.project_root_dir, LABCORE_DRAWS_FILE_NAME)
        if os.path.exists(filepath):
            try:
                df = pd.read_csv(filepath, encoding="utf-8-sig")
                df['Тираж'] = pd.to_numeric(df['Тираж'], errors='coerce')
                if not df['Тираж'].empty and not pd.isna(df['Тираж'].max()):
                    return int(df['Тираж'].max()) + 1
            except Exception:
                pass
        return 1


    def open_generation_settings(self):
        dialog = GenerationSettingsDialog(
            parent=self,
            config_core=self.config_core,
            config_softpool=self.config_softpool,
            config_quotas=self.config_quotas,
            pool_stats=self.pool_stats
        )
        
        if dialog.exec_() == QDialog.Accepted:
            updated_settings = dialog.get_settings()
            
            self.config_core.update(updated_settings["core"])
            self.config_softpool.update(updated_settings["softpool"])
            self.config_quotas.update(updated_settings["quotas"])

            self._save_config(os.path.join(self.project_root_dir, CONFIG_DIR_NAME, "core_settings.json"), self.config_core)
            self._save_config(os.path.join(self.project_root_dir, CONFIG_DIR_NAME, "softpool_config.json"), self.config_softpool)
            self._save_config(os.path.join(self.project_root_dir, CONFIG_DIR_NAME, "quota_config.json"), self.config_quotas)
            
            if (self.config_quotas["H"] + self.config_quotas["M"] + self.config_quotas["C"]) != 100:
                QMessageBox.warning(self, "Ошибка квот", "Сумма Hot, Mid, Cold квот должна быть равна 100%. Пожалуйста, скорректируйте в настройках.")
            else:
                QMessageBox.information(self, "Настройки сохранены", "Настройки генерации успешно обновлены.")

    def _save_config(self, filename, config_data):
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            QMessageBox.warning(self, "Ошибка сохранения конфигурации", f"Не удалось сохранить {filename}: {e}")

    def generate_combinations(self):
        self.status_label.setText("Генерация...")
        
        self.pool_stats = self._load_config(os.path.join(self.project_root_dir, CONFIG_DIR_NAME, "pool_stats.json"))
        if not self.pool_stats:
            self.status_label.setText("Генерация отменена: Отсутствуют данные статистики пула.")
            return
        
        if len(self.pool_stats) < 52:
            for i in range(1, 53):
                num_str = str(i)
                if num_str not in self.pool_stats:
                    self.pool_stats[num_str] = {
                        "frequency": 0.0, "last_seen": 999, "avg_interval": 0.0,
                        "std_interval": 0.0, "psw": 0.0, "zone": "Sleepy"
                    }
                if "zone" not in self.pool_stats[num_str]:
                    self.pool_stats[num_str]["zone"] = "Sleepy"

        num_combinations = self.num_combinations_spinbox.value()
        
        selected_contour_text = self.mode_combo.currentText()
        if selected_contour_text == "Контур A (Stable)":
            self.config_core["mode"] = "hybrid"
            contour_label = "Контур_A"
        else:
            self.config_core["mode"] = "experimental"
            contour_label = "Контур_B"

        if self.auto_draw_num_checkbox.isChecked():
            generate_for_draw_number = self._get_next_draw_number()
        else:
            generate_for_draw_number = self.manual_draw_num_spinbox.value()


        if (self.config_quotas.get("H", 0) + self.config_quotas.get("M", 0) + self.config_quotas.get("C", 0)) != 100:
            QMessageBox.warning(self, "Ошибка квот", "Сумма Hot, Mid, Cold квот должна быть равна 100%. Пожалуйста, скорректируйте в настройках генерации.")
            self.status_label.setText("Генерация отменена: Ошибка квот.")
            return

        try:
            from generate.generator import LotteryGenerator
            generator = LotteryGenerator(
                draws_df=self.draws_df,
                config_core=self.config_core,
                config_softpool=self.config_softpool,
                config_quotas=self.config_quotas,
                pool_stats=self.pool_stats
            )
            
            generated_combinations = generator.generate_combinations(num_combinations)

            output_dir_path = os.path.join(self.project_root_dir, GENERATED_DIR_NAME)
            os.makedirs(output_dir_path, exist_ok=True)
            
            base_filename = f"combinations_for_draw_{generate_for_draw_number}_{contour_label}.csv"
            output_filename = os.path.join(output_dir_path, base_filename)

            if os.path.exists(output_filename):
                timestamp_suffix = datetime.datetime.now().strftime("_%Y%m%d_%H%M%S")
                output_filename = os.path.join(output_dir_path, f"combinations_for_draw_{generate_for_draw_number}_{contour_label}{timestamp_suffix}.csv")


            generated_df = pd.DataFrame(generated_combinations, columns=[f'N{i}' for i in range(1, 7)])
            generated_df.to_csv(output_filename, index=False, encoding="utf-8-sig")

            self.status_label.setText(f"Сгенерировано {len(generated_combinations)} комбинаций для тиража №{generate_for_draw_number} ({contour_label}). Сохранено в {os.path.basename(output_filename)}")
            QMessageBox.information(self, "Генерация завершена", f"Успешно сгенерировано {len(generated_combinations)} комбинаций для тиража №{generate_for_draw_number} ({contour_label}).")

        except Exception as e:
            self.status_label.setText(f"Ошибка генерации: {e}")
            QMessageBox.critical(self, "Ошибка Генерации", f"Произошла ошибка в процессе генерации: {e}")