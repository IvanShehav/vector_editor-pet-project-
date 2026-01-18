# vector_editor/main.py
import sys
from PySide6.QtWidgets import QApplication
from src.app import VectorEditorWindow

def main():
    app = QApplication(sys.argv)

    # Инициализация и настройка темы оформления (опционально)
    app.setStyle("Fusion")

    window = VectorEditorWindow()
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()