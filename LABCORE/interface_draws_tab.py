import os
import pandas as pd
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QFileDialog,
    QTableWidget, QTableWidgetItem, QHBoxLayout, QLineEdit, QMessageBox,
    QDialog, QDialogButtonBox, QFormLayout, QSpinBox
)
from PyQt5.QtCore import Qt
import datetime

LABCORE_DRAWS_FILE = "labcore_draws.csv"

class DrawsTab(QWidget):
    def __init__(self):
        super().__init__()
        self.setLayout(QVBoxLayout())

        self.label_last = QLabel("Последний тираж: ...")
        self.label_last.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.layout().addWidget(self.label_last)

        self.table = QTableWidget()
        self.table.setStyleSheet("font-size: 12px;")
        self.layout().addWidget(self.table)

        buttons_layout = QHBoxLayout()

        btn_load = QPushButton("Загрузить CSV")
        btn_load.clicked.connect(self.load_csv)
        buttons_layout.addWidget(btn_load)

        btn_add_new_draw = QPushButton("Ввод нового тиража")
        btn_add_new_draw.clicked.connect(self.open_add_draw_dialog)
        buttons_layout.addWidget(btn_add_new_draw)

        self.layout().addLayout(buttons_layout)

        if not os.path.exists(LABCORE_DRAWS_FILE):
            pd.DataFrame(columns=["Тираж", "Дата", "Комплект", "N1", "N2", "N3", "N4", "N5", "N6"]).to_csv(LABCORE_DRAWS_FILE, index=False, encoding="utf-8-sig")

        self.load_local_draws()

    def load_csv(self):
        path, _ = QFileDialog.getOpenFileName(self, "Выбрать CSV", "", "CSV Files (*.csv)")
        if path:
            try:
                df = pd.read_csv(path, encoding="utf-8-sig")
                df = self.clean_dataframe(df)
                df.to_csv(LABCORE_DRAWS_FILE, index=False, encoding="utf-8-sig")
                self.load_local_draws()
            except Exception as e:
                QMessageBox.warning(self, "Ошибка", f"Не удалось загрузить файл: {str(e)}")

    def clean_dataframe(self, df):
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
            df_cleaned["Тираж"] = pd.to_numeric(df_cleaned["Тираж"], errors='coerce').astype('Int64')
        
        for col in ["Дата", "Комплект"]:
            if col in df_cleaned.columns:
                df_cleaned[col] = df_cleaned[col].fillna("").astype(str)

        if "Тираж" in df_cleaned.columns:
            df_cleaned.drop_duplicates(subset=["Тираж"], keep="last", inplace=True)
            df_cleaned.sort_values(by="Тираж", ascending=False, inplace=True)

        return df_cleaned

    def load_local_draws(self):
        if os.path.exists(LABCORE_DRAWS_FILE):
            df = pd.read_csv(LABCORE_DRAWS_FILE, encoding="utf-8-sig")
            df = self.clean_dataframe(df)
            
            display_cols = ["Тираж", "N1", "N2", "N3", "N4", "N5", "N6"]
            display_df = df[[col for col in display_cols if col in df.columns]].copy()
            
            self.display_draw_table(display_df)

            if not df.empty:
                last_draw_row = df.loc[df['Тираж'].idxmax()]
                
                numbers_cols = [f'N{i}' for i in range(1, 7)]
                existing_numbers_cols = [col for col in numbers_cols if col in last_draw_row.index]
                numbers = ", ".join(str(int(x)) for x in last_draw_row[existing_numbers_cols].dropna())
                
                self.label_last.setText(f"Последний тираж №{int(last_draw_row.loc['Тираж'])} — Номера: {numbers}")
        else:
            self.display_draw_table(pd.DataFrame(columns=["Тираж", "N1", "N2", "N3", "N4", "N5", "N6"]))
            self.label_last.setText("Последний тираж: нет данных")

    def display_draw_table(self, df):
        self.table.setRowCount(len(df))
        self.table.setColumnCount(len(df.columns))
        self.table.setHorizontalHeaderLabels(df.columns)
        for i in range(len(df)):
            for j in range(len(df.columns)):
                val = str(df.iat[i, j])
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(i, j, item)
        self.table.resizeColumnsToContents()

    def get_next_draw_number(self):
        if os.path.exists(LABCORE_DRAWS_FILE):
            try:
                df = pd.read_csv(LABCORE_DRAWS_FILE, encoding="utf-8-sig")
                df['Тираж'] = pd.to_numeric(df['Тираж'], errors='coerce')
                if not df.empty and not pd.isna(df['Тираж'].max()):
                    return int(df['Тираж'].max()) + 1
            except Exception:
                return 1
        return 1

    def open_add_draw_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Добавить новый тираж")
        
        layout = QFormLayout(dialog)

        next_draw_num = self.get_next_draw_number()
        
        self.draw_number_input = QLineEdit(str(next_draw_num))
        self.draw_number_input.setReadOnly(True)
        layout.addRow("Номер тиража:", self.draw_number_input)

        self.number_inputs = []
        for i in range(1, 7):
            spin_box = QSpinBox()
            spin_box.setRange(1, 52)
            spin_box.setFixedSize(50, 25)
            self.number_inputs.append(spin_box)
            layout.addRow(f"Число N{i}:", spin_box)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, dialog)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        if dialog.exec_() == QDialog.Accepted:
            self.add_new_draw_from_dialog()

    def add_new_draw_from_dialog(self):
        draw_number = int(self.draw_number_input.text())
        numbers = []
        for spin_box in self.number_inputs:
            numbers.append(spin_box.value())
        
        if len(numbers) != 6:
            QMessageBox.warning(self, "Ошибка ввода", "Необходимо ввести ровно 6 чисел.")
            return
        
        if not all(1 <= num <= 52 for num in numbers):
            QMessageBox.warning(self, "Ошибка ввода", "Все числа должны быть в диапазоне от 1 до 52.")
            return

        if len(set(numbers)) != 6:
            QMessageBox.warning(self, "Ошибка ввода", "Все числа должны быть уникальными.")
            return

        numbers.sort()

        try:
            if os.path.exists(LABCORE_DRAWS_FILE):
                df = pd.read_csv(LABCORE_DRAWS_FILE, encoding="utf-8-sig")
            else:
                df = pd.DataFrame(columns=["Тираж", "Дата", "Комплект", "N1", "N2", "N3", "N4", "N5", "N6"])
            
            df['Тираж'] = pd.to_numeric(df['Тираж'], errors='coerce').astype('Int64')

            if draw_number in df['Тираж'].dropna().values:
                QMessageBox.warning(self, "Ошибка", f"Тираж №{draw_number} уже существует. Введите другой номер или измените существующий тираж.")
                return

            new_row_data = {
                "Тираж": draw_number,
                "Дата": datetime.datetime.now().strftime("%Y-%m-%d"),
                "Комплект": "",
                "N1": numbers[0],
                "N2": numbers[1],
                "N3": numbers[2],
                "N4": numbers[3],
                "N5": numbers[4],
                "N6": numbers[5]
            }
            new_draw_df = pd.DataFrame([new_row_data])

            df = pd.concat([df, new_draw_df], ignore_index=True)
            
            df.to_csv(LABCORE_DRAWS_FILE, index=False, encoding="utf-8-sig")
            
            self.load_local_draws()
            QMessageBox.information(self, "Успех", f"Тираж №{draw_number} успешно добавлен и сохранен.")

        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось добавить тираж: {str(e)}")