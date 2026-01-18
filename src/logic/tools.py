# src/logic/tools.py
from abc import ABC, abstractmethod
from PySide6.QtWidgets import QGraphicsView
from PySide6.QtCore import Qt, QPointF
from src.logic.factory import ShapeFactory
from src.logic.commands import AddShapeCommand, MoveCommand, DeleteShapeCommand

class Tool(ABC):
    def __init__(self, view):
        self.view = view # Ссылка на Canvas (View)
        self.scene = view.scene # Ссылка на сцену

    @abstractmethod
    def mouse_press(self, event): pass

    @abstractmethod
    def mouse_move(self, event): pass

    @abstractmethod
    def mouse_release(self, event): pass


class SelectionTool(Tool):
    """Инструмент для выделения и перемещения фигур"""

    def __init__(self, view, undo_stack):
        super().__init__(view)
        self.undo_stack = undo_stack

        # Хранилище для начальных позиций
        # Словарь: {item: QPointF(x, y)}
        self.item_positions = {}

    def mouse_press(self, event):
        self.view.viewport().setCursor(Qt.ClosedHandCursor)
        # 1. Сначала даем Qt обработать клик (выделить объекты)
        super(type(self.view), self.view).mousePressEvent(event)

        # 2. Запоминаем позиции ВСЕХ выделенных объектов
        self.item_positions.clear()
        for item in self.scene.selectedItems():
            self.item_positions[item] = item.pos()

    def mouse_move(self, event):
        # Даем Qt визуально двигать объекты
        super(type(self.view), self.view).mouseMoveEvent(event)

    def mouse_release(self, event):
        self.view.viewport().setCursor(Qt.OpenHandCursor)
        # 1. Даем Qt завершить процесс перетаскивания
        super(type(self.view), self.view).mouseReleaseEvent(event)

        # 2. Проверяем, кто реально сдвинулся
        moved_items = []
        for item, old_pos in self.item_positions.items():
            new_pos = item.pos()
            if new_pos != old_pos: # Проверка: сдвинулся ли объект хотя бы на пиксель
                moved_items.append((item, old_pos, new_pos))

        # 3. Если движение было, создаем команды
        if moved_items:
            # Используем МАКРОС: все движения считаются ОДНИМ действием в истории
            self.undo_stack.beginMacro("Move Items")
            for item, old_pos, new_pos in moved_items:
                cmd = MoveCommand(item, old_pos, new_pos)
                self.undo_stack.push(cmd)
            self.undo_stack.endMacro()

        self.item_positions.clear()


class CreationTool(Tool):
    """Инструмент для создания фигур (Резиновая нить)"""

    def __init__(self, view, shape_type, undo_stack):
        super().__init__(view)
        self.shape_type = shape_type
        self.undo_stack = undo_stack
        self.start_pos = None
        self.temp_shape = None # Временная фигура для предпросмотра

    def mouse_press(self, event):
        if event.button() == Qt.LeftButton:
            self.start_pos = self.view.mapToScene(event.pos())

            # 1. Создаем фигуру сразу в точке клика
            # Цвет берем из View (Canvas), так как мы его там храним
            try:
                self.temp_shape = ShapeFactory.create_shape(
                    self.shape_type,
                    self.start_pos,
                    self.start_pos, # Пока начало и конец совпадают
                    self.view.current_color # <--- Передаем цвет!
                )
                self.scene.addItem(self.temp_shape)
            except ValueError:
                pass

    def mouse_move(self, event):
        # 2. Если мы тащим мышь и фигура создана - обновляем её форму
        if self.temp_shape and self.start_pos:
            current_pos = self.view.mapToScene(event.pos())
            # Вызываем метод set_geometry у фигуры (см. shapes.py)
            self.temp_shape.set_geometry(self.start_pos, current_pos)

    def mouse_release(self, event):
        if event.button() == Qt.LeftButton and self.temp_shape:
            # 1. Запоминаем финальную точку
            end_pos = self.view.mapToScene(event.pos())
            color = self.view.current_color

            # 2. УДАЛЯЕМ временную фигуру (превью)
            self.scene.removeItem(self.temp_shape)
            self.temp_shape = None

            # 3. Создаем "финальную" фигуру для команды
            try:
                final_shape = ShapeFactory.create_shape(
                    self.shape_type, self.start_pos, end_pos, color
                )

                # 4. СОЗДАЕМ КОМАНДУ И КЛАДЕМ В СТЕК
                # Метод push() сам вызовет redo(), и фигура появится
                command = AddShapeCommand(self.scene, final_shape)
                self.undo_stack.push(command)

            except ValueError: pass

            self.start_pos = None

class PolygonTool(Tool):
    def __init__(self, view):
        super().__init__(view)
        self.nodes = []      # Список зафиксированных точек
        self.temp_item = None # Превью (нить)

    def mouse_press(self, event):
        if event.button() == Qt.LeftButton:
            pos = self.view.mapToScene(event.pos())

            # Если кликнули близко к первой точке (радиус 15 пикселей) — замыкаем
            if self.nodes and (pos - self.nodes[0]).manhattanLength() < 15:
                self.finish_polygon(closed=True)
                return

            self.nodes.append(pos)
            self._update_preview(pos)

    def mouse_move(self, event):
        if self.nodes:
            current_pos = self.view.mapToScene(event.pos())
            self._update_preview(current_pos)

    def _update_preview(self, cursor_pos):
        if self.temp_item:
            self.scene.removeItem(self.temp_item)

        display_points = list(self.nodes)
        if cursor_pos not in display_points:
            display_points.append(cursor_pos)

        if len(display_points) >= 2:
            from src.logic.shapes import Polygon
            # Нить всегда незамкнута и полупрозрачна
            self.temp_item = Polygon(display_points, self.view.current_color, is_closed=False)
            self.temp_item.setOpacity(0.5)
            self.scene.addItem(self.temp_item)

    def finish_polygon(self, closed=True):
        if len(self.nodes) < 2:
            self._clear_temp()
            return

        from src.logic.shapes import Polygon
        from src.logic.commands import AddShapeCommand

        final_poly = Polygon(self.nodes, self.view.current_color, is_closed=closed)
        self._clear_temp()
        self.nodes = []

        # Добавляем в историю
        self.view.undo_stack.push(AddShapeCommand(self.scene, final_poly))

    def _clear_temp(self):
        if self.temp_item:
            self.scene.removeItem(self.temp_item)
            self.temp_item = None

    def mouse_release(self, event): pass