#src/logic/strategies.py

from abc import ABC, abstractmethod
from PySide6.QtGui import QImage, QPainter, QColor
from PySide6.QtCore import QRectF, QSize
import json

class SaveStrategy(ABC):
    @abstractmethod
    def save(self, filename: str, scene):
        """
        :param filename: Путь сохранения
        :param scene: Ссылка на QGraphicsScene (источник данных)
        """
        pass


class JsonSaveStrategy(SaveStrategy):
    def save(self, filename, scene):
        # 1. Подготовка структуры
        data = {
            "version": "1.0",
            "scene": {
                "width": scene.width(),
                "height": scene.height()
            },
            "shapes": []
        }

        # 2. Сбор объектов (от нижнего к верхнему)
        items = scene.items()[::-1]

        for item in items:
            # ПРОВЕРКА:
            # 1. Есть ли у нас метод to_dict?
            # 2. Является ли объект корневым (нет родителя)?
            if hasattr(item, "to_dict") and item.parentItem() is None:
                data["shapes"].append(item.to_dict())

        # 3. Запись
        with open(filename, 'w', encoding='utf-8') as f:
            # Добавил ensure_ascii=False на случай кириллицы в путях или именах
            json.dump(data, f, indent=4, ensure_ascii=False)


class ImageSaveStrategy(SaveStrategy):
    def __init__(self, format_name="PNG", background_color="white", crop_to_content=False):
        self.format_name = format_name
        self.bg_color = background_color
        self.crop_to_content = crop_to_content # Флаг для доп. задания

    def save(self, filename, scene):
        # 1. Определяем область для рендеринга
        if self.crop_to_content:
            # Берем только рамку, охватывающую все фигуры
            rect = scene.itemsBoundingRect()
            # Если сцена пустая, rect будет невалидным, откатываемся к размеру сцены
            if rect.isEmpty():
                rect = scene.sceneRect()
        else:
            # Берем весь размер "листа"
            rect = scene.sceneRect()

        width = int(rect.width())
        height = int(rect.height())

        # Защита от создания пустой картинки 0x0
        if width <= 0 or height <= 0:
            return

        # 2. Создаем буфер изображения
        image = QImage(width, height, QImage.Format_ARGB32)

        # 3. Заливка фона
        if self.bg_color == "transparent":
            image.fill(QColor(0, 0, 0, 0))
        else:
            image.fill(QColor(self.bg_color))

        # 4. Рендеринг
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # ВАЖНО: Мы рисуем область 'rect' со сцены в полный размер картинки
        scene.render(painter, QRectF(image.rect()), rect)

        painter.end()

        # 5. Сохранение
        image.save(filename, self.format_name)