#src/utils.py
import sys
import os

def resource_path(relative_path):
    """
    Получает абсолютный путь к ресурсу.
    Работает и для dev-режима, и для PyInstaller.
    """
    try:
        # PyInstaller создает временную папку _MEIPASS при запуске
        base_path = sys._MEIPASS
    except Exception:
        # Если переменной нет, значит мы просто запускаем скрипт
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

#команда для сборки
#pyinstaller --noconfirm --onefile --windowed --name "VectorEditor" main.py