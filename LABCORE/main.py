import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget, QWidget
from interface_draws_tab import DrawsTab
from generate.generation_tab import GenerationTab
from compare_tab import CompareTab
from reports_tab import ReportsTab
from training_tab import TrainingTab
from akk_tab import AkkTab # Импортируем новую вкладку для АКК

class LabcoreApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Лото 6 из 52 — Мы идём не за чудом — мы идём за закономерностью!")
        self.setGeometry(100, 100, 1200, 700)

        tabs = QTabWidget()
        tabs.addTab(DrawsTab(), "Тиражи")
        tabs.addTab(GenerationTab(), "Генерация")
        tabs.addTab(CompareTab(), "Сверка")
        tabs.addTab(TrainingTab(), "Обучение Моделей")
        tabs.addTab(AkkTab(), "АКК / LABCORE") # Добавляем вкладку "АКК / LABCORE"
        tabs.addTab(ReportsTab(), "Отчёты")
        tabs.addTab(QWidget(), "Настройки") # Пока заглушка
        tabs.addTab(QWidget(), "Автономный режим") # Пока заглушка

        self.setCentralWidget(tabs)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = LabcoreApp()
    window.show()
    sys.exit(app.exec_())