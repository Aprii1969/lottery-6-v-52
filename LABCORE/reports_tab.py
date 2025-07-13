import os
import json
import datetime
import sys

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QLineEdit, QGroupBox, QFormLayout,
    QMessageBox, QTimeEdit, QPlainTextEdit, QHBoxLayout, QDialog, QListWidget,
    QListWidgetItem, QDialogButtonBox, QCheckBox
)
from PyQt5.QtCore import Qt, QTime, QTimer

CONFIG_DIR = "config"
REPORTS_DIR_PATH = os.path.join("reports", "Сверка_inf")

REPORT_SETTINGS_FILE = os.path.join(CONFIG_DIR, "report_settings.json")

class ReportsTab(QWidget):
    def __init__(self):
        super().__init__()
        self.setLayout(QVBoxLayout())

        self.project_root_dir = os.getcwd()

        self.header_label = QLabel("Настройки и Журнал Отчётов")
        self.header_label.setStyleSheet("font-weight: bold; font-size: 16px;")
        self.layout().addWidget(self.header_label, alignment=Qt.AlignCenter)

        email_group = QGroupBox("Настройки Email Отчётов")
        email_layout = QFormLayout()

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Введите email адрес")
        email_layout.addRow("Email для отчётов:", self.email_input)

        email_group.setLayout(email_layout)
        self.layout().addWidget(email_group)

        auto_mode_group = QGroupBox("Настройки Автоматической Загрузки Тиражей")
        auto_mode_layout = QFormLayout()

        self.draw_site_url_input = QLineEdit()
        self.draw_site_url_input.setPlaceholderText("Например: http://www.lottery.com/results")
        auto_mode_layout.addRow("URL сайта лотереи:", self.draw_site_url_input)

        self.check_time_label = QLabel("Время проверки тиража (ЧЧ:ММ):")
        self.check_time_input = QTimeEdit(QTime(23, 30))
        self.check_time_input.setDisplayFormat("HH:mm")
        auto_mode_layout.addRow(self.check_time_label, self.check_time_input)

        self.days_of_week_label = QLabel("Дни недели для проверки:")
        self.days_of_week_layout = QHBoxLayout()
        self.day_checkboxes = {}
        days = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
        for day in days:
            checkbox = QCheckBox(day)
            self.days_of_week_layout.addWidget(checkbox)
            self.day_checkboxes[day] = checkbox
        self.day_checkboxes["Среда"].setChecked(True)
        self.day_checkboxes["Суббота"].setChecked(True)

        auto_mode_layout.addRow(self.days_of_week_label, self.days_of_week_layout)

        auto_mode_group.setLayout(auto_mode_layout)
        self.layout().addWidget(auto_mode_group)

        buttons_layout = QHBoxLayout()
        btn_save_settings = QPushButton("Сохранить Настройки Отчётов")
        btn_save_settings.clicked.connect(self.save_report_settings)
        buttons_layout.addWidget(btn_save_settings)
        
        btn_view_reports = QPushButton("Просмотреть Сохранённые Отчёты")
        btn_view_reports.clicked.connect(self.view_saved_reports)
        buttons_layout.addWidget(btn_view_reports)

        btn_send_test_report = QPushButton("Отправить тестовый отчёт")
        btn_send_test_report.clicked.connect(self._send_test_report)
        buttons_layout.addWidget(btn_send_test_report)

        self.layout().addLayout(buttons_layout)

        log_group = QGroupBox("Журнал Отчётов / Статус")
        log_layout = QVBoxLayout()

        self.report_log_display = QPlainTextEdit()
        self.report_log_display.setReadOnly(True)
        self.report_log_display.setPlaceholderText("Здесь будет отображаться статус отправки отчетов и действий автономного режима.")
        log_layout.addWidget(self.report_log_display)

        log_group.setLayout(log_layout)
        self.layout().addWidget(log_group)

        self.layout().addStretch(1)

        self._load_report_settings()

    def _load_report_settings(self):
        filepath = os.path.join(self.project_root_dir, REPORT_SETTINGS_FILE)
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    self.email_input.setText(settings.get("email", ""))
                    self.draw_site_url_input.setText(settings.get("draw_site_url", ""))
                    
                    time_str = settings.get("check_time", "23:30")
                    hour, minute = map(int, time_str.split(':'))
                    self.check_time_input.setTime(QTime(hour, minute))

                    selected_days = settings.get("check_days_of_week", ["Среда", "Суббота"])
                    for day, checkbox in self.day_checkboxes.items():
                        checkbox.setChecked(day in selected_days)
                    
                    self.append_log(f"Настройки отчетов загружены из {os.path.basename(filepath)}.")
            except Exception as e:
                QMessageBox.warning(self, "Ошибка загрузки настроек", f"Не удалось загрузить настройки отчетов: {e}")
                self.append_log(f"Ошибка загрузки настроек отчетов: {e}")
        else:
            self.append_log(f"Файл {os.path.basename(filepath)} не найден. Используются значения по умолчанию.")
            self.save_report_settings()

    def save_report_settings(self):
        selected_days = [day for day, checkbox in self.day_checkboxes.items() if checkbox.isChecked()]

        settings = {
            "email": self.email_input.text(),
            "draw_site_url": self.draw_site_url_input.text(),
            "check_time": self.check_time_input.time().toString("HH:mm"),
            "check_days_of_week": selected_days
        }
        
        filepath = os.path.join(self.project_root_dir, REPORT_SETTINGS_FILE)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=4, ensure_ascii=False)
            QMessageBox.information(self, "Настройки сохранены", "Настройки отчетов успешно сохранены.")
            self.append_log(f"Настройки отчетов сохранены в {os.path.basename(filepath)}.")
        except Exception as e:
            QMessageBox.warning(self, "Ошибка сохранения", f"Не удалось сохранить настройки отчетов: {e}")
            self.append_log(f"Ошибка сохранения настроек отчетов: {e}")

    def append_log(self, message):
        timestamp = datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        self.report_log_display.appendPlainText(f"{timestamp} {message}")
        self.report_log_display.verticalScrollBar().setValue(self.report_log_display.verticalScrollBar().maximum())

    def _send_test_report(self):
        email_address = self.email_input.text().strip()
        if not email_address:
            QMessageBox.warning(self, "Ошибка отправки", "Пожалуйста, укажите email адрес для отправки отчёта.")
            self.append_log("Ошибка: Email адрес для тестового отчёта не указан.")
            return
        
        if "@" not in email_address or "." not in email_address:
            QMessageBox.warning(self, "Ошибка отправки", "Пожалуйста, введите корректный email адрес.")
            self.append_log(f"Ошибка: Некорректный email адрес: {email_address}")
            return

        self.append_log(f"Начата имитация отправки тестового отчёта на {email_address}...")
        self.send_timer_counter = 0
        self.send_timer = QTimer(self)
        self.send_timer.timeout.connect(self._update_send_progress)
        self.send_timer.start(500)
        self.send_timer_max = 3


    def _update_send_progress(self):
        self.send_timer_counter += 1
        if self.send_timer_counter <= self.send_timer_max:
            self.append_log(f"   Имитация отправки... ({self.send_timer_counter}/{self.send_timer_max})")
        else:
            self.send_timer.stop()
            self.append_log(f"Тестовый отчёт успешно отправлен (имитация) на {self.email_input.text().strip()}.")
            QMessageBox.information(self, "Отправка завершена", f"Имитация отправки тестового отчёта на {self.email_input.text().strip()} завершена успешно.")


    def view_saved_reports(self):
        reports_path = os.path.join(self.project_root_dir, REPORTS_DIR_PATH)
        
        if not os.path.exists(reports_path) or not os.listdir(reports_path):
            QMessageBox.information(self, "Нет отчётов", f"Папка с отчётами ({reports_path}) не найдена или пуста.")
            return
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Просмотр Отчётов Сверки")
        dialog_layout = QVBoxLayout(dialog)

        list_widget = QListWidget()
        report_files = [f for f in os.listdir(reports_path) if f.endswith(('.csv', '.txt')) and f.startswith('sverka_report_draw_')]
        
        if not report_files:
            dialog_layout.addWidget(QLabel("Нет сохранённых отчётов сверки."))
        else:
            for f_name in sorted(report_files, reverse=True): 
                item = QListWidgetItem(f_name)
                item.setData(Qt.UserRole, os.path.join(reports_path, f_name))
                list_widget.addItem(item)
            
            list_widget.itemDoubleClicked.connect(self._open_report_file)
            dialog_layout.addWidget(list_widget)

        button_box = QDialogButtonBox(QDialogButtonBox.Close, dialog)
        button_box.accepted.connect(dialog.accept)
        dialog_layout.addWidget(button_box)
        
        dialog.exec_()

    def _open_report_file(self, item):
        filepath = item.data(Qt.UserRole)
        if os.path.exists(filepath):
            try:
                if sys.platform == "win32":
                    os.startfile(filepath)
                elif sys.platform == "darwin":
                    os.system(f"open \"{filepath}\"")
                else:
                    os.system(f"xdg-open \"{filepath}\"")
            except Exception as e:
                QMessageBox.warning(self, "Ошибка открытия файла", f"Не удалось открыть файл: {e}")
        else:
            QMessageBox.warning(self, "Файл не найден", f"Файл отчета не существует: {filepath}")