# src/logic/shapes.py
from abc import ABC, abstractmethod, ABCMeta
from PySide6.QtWidgets import QGraphicsPathItem, QGraphicsItemGroup, QGraphicsItem
from PySide6.QtGui import QPen, QColor, QPainterPath
from PySide6.QtCore import QPointF

# 1. Решаем конфликт метаклассов (возвращаем твой pass-класс)
class CombinedMetaclass(type(QGraphicsItem), ABCMeta):
    pass

class Shape(ABC, metaclass=CombinedMetaclass):
    def __init__(self, color: str = "black", stroke_width: int = 2):
        self.color = color
        self.stroke_width = stroke_width
        # МЫ НЕ ВЫЗЫВАЕМ методы Qt здесь, чтобы избежать RuntimeError

    def apply_initial_config(self):
        """Метод для безопасной настройки свойств Qt после инициализации всех баз"""
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)

        # Красим фигуру (кроме групп, у них своя логика)
        if not isinstance(self, QGraphicsItemGroup):
            self.set_active_color(self.color)

    def set_active_color(self, color: str):
        self.color = color
        if hasattr(self, 'setPen'):
            current_pen = self.pen()
            current_pen.setColor(QColor(self.color))
            self.setPen(current_pen)
            # Обновляем внутреннюю переменную для порядка
            self.stroke_width = current_pen.width()

    @property
    @abstractmethod
    def type_name(self) -> str:
        pass

    @abstractmethod
    def to_dict(self) -> dict:
        pass

    @abstractmethod
    def set_geometry(self, start_point: QPointF, end_point: QPointF):
        pass


class Group(QGraphicsItemGroup, Shape):
    def __init__(self):
        QGraphicsItemGroup.__init__(self)
        Shape.__init__(self)
        # Вызываем настройку только когда оба родителя готовы
        self.apply_initial_config()
        self.setHandlesChildEvents(True)

    @property
    def type_name(self) -> str:
        return "group"


    def pen(self):
        """Возвращает перо первого ребенка, чтобы панель свойств знала, какой цвет показать"""
        children = self.childItems()
        if children and hasattr(children[0], 'pen'):
            return children[0].pen()
        return QPen(QColor(self.color))

    def setPen(self, pen: QPen):
        """Принимает новое перо от панели свойств и раздает его всем детям"""
        self.color = pen.color().name()
        self.stroke_width = pen.width()
        for child in self.childItems():
            if hasattr(child, "setPen"):
                child.setPen(pen)
            # Если внутри группы есть другая группа, вызываем её метод окраски
            if isinstance(child, Shape):
                child.color = self.color
                child.stroke_width = self.stroke_width

    def set_active_color(self, color: str):
        self.color = color
        for child in self.childItems():
            if hasattr(child, "set_active_color"):
                child.set_active_color(color)
                child.stroke_width = self.stroke_width

    def set_stroke_width(self, width: int):
        self.stroke_width = width
        if hasattr(self, 'setPen'):
            current_pen = self.pen()
            current_pen.setWidth(width)
            self.setPen(current_pen)

    def set_geometry(self, s, e):
        pass

    def to_dict(self) -> dict:
        children_data = []
        for child in self.childItems():
            if isinstance(child, Shape):
                children_data.append(child.to_dict())
        return {
            "type": self.type_name,
            "pos": [self.x(), self.y()],
            "children": children_data
        }


class Rectangle(QGraphicsPathItem, Shape):
    def __init__(self, x, y, w, h, color="black", stroke_width=2):
        QGraphicsPathItem.__init__(self)
        Shape.__init__(self, color, stroke_width)
        # Настраиваем Qt-часть в последнюю очередь
        self.apply_initial_config()
        self.set_geometry_data(x, y, w, h)

    def set_geometry_data(self, x, y, w, h):
        path = QPainterPath()
        path.addRect(x, y, w, h)
        self.setPath(path)

    @property
    def type_name(self) -> str:
        return "rect"

    def set_geometry(self, start_point, end_point):
        x = min(start_point.x(), end_point.x())
        y = min(start_point.y(), end_point.y())
        w = abs(end_point.x() - start_point.x())
        h = abs(end_point.y() - start_point.y())
        self.set_geometry_data(x, y, w, h)

    def to_dict(self) -> dict:
        r = self.path().boundingRect()
        return {"type": "rect", "pos": [self.x(), self.y()],
                "props": {"x": r.x(), "y": r.y(), "w": r.width(), "h": r.height(), "color": self.color}}


class Ellipse(QGraphicsPathItem, Shape):
    def __init__(self, x, y, w, h, color="black", stroke_width=2):
        QGraphicsPathItem.__init__(self)
        Shape.__init__(self, color, stroke_width)
        self.apply_initial_config()
        self.set_geometry_data(x, y, w, h)

    def set_geometry_data(self, x, y, w, h):
        path = QPainterPath()
        path.addEllipse(x, y, w, h)
        self.setPath(path)

    @property
    def type_name(self) -> str:
        return "ellipse"

    def set_geometry(self, start_point, end_point):
        x = min(start_point.x(), end_point.x())
        y = min(start_point.y(), end_point.y())
        w = abs(end_point.x() - start_point.x())
        h = abs(end_point.y() - start_point.y())
        self.set_geometry_data(x, y, w, h)

    def to_dict(self) -> dict:
        r = self.path().boundingRect()
        return {"type": "ellipse", "pos": [self.x(), self.y()],
                "props": {"x": r.x(), "y": r.y(), "w": r.width(), "h": r.height(), "color": self.color}}


class Line(QGraphicsPathItem, Shape):
    def __init__(self, x1, y1, x2, y2, color="black", stroke_width=2):
        QGraphicsPathItem.__init__(self)
        Shape.__init__(self, color, stroke_width)
        self.apply_initial_config()
        self.x1, self.y1, self.x2, self.y2 = x1, y1, x2, y2
        self.set_geometry_data(x1, y1, x2, y2)

    def set_geometry_data(self, x1, y1, x2, y2):
        path = QPainterPath()
        path.moveTo(x1, y1)
        path.lineTo(x2, y2)
        self.setPath(path)

    @property
    def type_name(self) -> str:
        return "line"

    def set_geometry(self, start_point, end_point):
        self.x1, self.y1 = start_point.x(), start_point.y()
        self.x2, self.y2 = end_point.x(), end_point.y()
        self.set_geometry_data(self.x1, self.y1, self.x2, self.y2)

    def to_dict(self) -> dict:
        return {"type": "line", "pos": [self.x(), self.y()],
                "props": {"x1": self.x1, "y1": self.y1, "x2": self.x2, "y2": self.y2, "color": self.color}}


class Polygon(QGraphicsPathItem, Shape):
    def __init__(self, points, color="black", stroke_width=2, is_closed=True):
        # Порядок важен для PySide6!
        QGraphicsPathItem.__init__(self)
        Shape.__init__(self, color, stroke_width)

        self.points = points
        self.is_closed = is_closed

        # Используем внутреннюю переменную
        self._type_name = "Polygon"

        self.apply_initial_config()
        self.update_path()

    @property
    def type_name(self):
        return self._type_name

    def update_path(self):
        if not self.points: return
        path = QPainterPath()
        path.moveTo(self.points[0])
        for p in self.points[1:]:
            path.lineTo(p)
        if self.is_closed:
            path.closeSubpath()
        self.setPath(path)

    def to_dict(self):
        # Для сохранения нам нужны координаты всех точек
        pts = [[p.x(), p.y()] for p in self.points]
        return {
            "type": "polygon",
            "pos": [self.x(), self.y()],
            "props": {
                "points": pts,
                "color": self.color,
                "width": self.stroke_width,
                "is_closed": self.is_closed
            }
        }