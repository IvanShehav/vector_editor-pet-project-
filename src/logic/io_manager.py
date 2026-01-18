#src/logic/io_manager.py
import json
import os

class FileManager:
    """
    Класс отвечает ТОЛЬКО за чтение и запись данных на диск.
    Он не знает про QGraphicsScene. Он работает с Python-словарями.
    """

    @staticmethod
    def save_project(filename: str, data: dict):
        """
        :param filename: Полный путь к файлу
        :param data: Готовый словарь с данными проекта
        """
        try:
            # ensure_ascii=False позволяет сохранять кириллицу нормально
            # indent=4 делает файл читаемым (pretty print)
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)

        except OSError as e:
            # Пробрасываем ошибку выше, чтобы UI показал Alert
            raise IOError(f"Не удалось записать файл: {e}")

    @staticmethod
    def load_project(filename: str) -> dict:
        if not os.path.exists(filename):
            raise FileNotFoundError(f"Файл не найден: {filename}")

        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            raise ValueError("Файл поврежден или имеет неверный формат")
        except OSError as e:
            raise IOError(f"Ошибка чтения файла: {e}")