# src/widgets/canvas.py
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QBrush, QColor, QUndoStack
from src.logic.commands import DeleteShapeCommand, MoveCommand

#импорт класса для создания групп
from src.logic.shapes import Group

# Импортируем наши инструменты
from src.logic.tools import SelectionTool, CreationTool

class EditorCanvas(QGraphicsView):
    def __init__(self):
        super().__init__()

        # --- СЦЕНА ---
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.scene.setSceneRect(0, 0, 800, 600)

        #Создаем стек истории
        self.undo_stack = QUndoStack(self)
        # Опционально: ограничим историю 50 шагами, чтобы экономить память
        self.undo_stack.setUndoLimit(50)

        # --- ДИЗАЙН (Белый лист на сером фоне) ---
        self.setStyleSheet("background-color: #555555; border: none;")
        self.setBackgroundBrush(QBrush(QColor("white")))

        # --- НАСТРОЙКИ ---
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setAlignment(Qt.AlignCenter)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        # Включаем отслеживание мыши для эффектов наведения (Hover)
        self.setMouseTracking(True)

        # --- СОСТОЯНИЕ ---
        self.current_color = "#000000" # Цвет по умолчанию

        # --- ИНИЦИАЛИЗАЦИЯ ИНСТРУМЕНТОВ ---
        self.tools = {
            "select": SelectionTool(self, self.undo_stack),

            "line": CreationTool(self, "line", self.undo_stack),
            "rect": CreationTool(self, "rect", self.undo_stack),
            "ellipse": CreationTool(self, "ellipse", self.undo_stack)
        }

        # По умолчанию выбран Select
        self.current_tool = self.tools["select"]

        self.key_move_positions = {}

        self.setRubberBandSelectionMode(Qt.ItemSelectionMode.ContainsItemShape)

    def set_tool(self, tool_name: str):
        self.scene.clearSelection()
        self.setDragMode(QGraphicsView.DragMode.NoDrag)

        if tool_name == "select":
            self.current_tool = self.tools["select"]
            self.viewport().setCursor(Qt.OpenHandCursor)
            # Включаем ладошку только для селекта, если тебе нужно выделение рамкой
            # self.setDragMode(QGraphicsView.RubberBandDrag)
        elif tool_name in self.tools:
            self.current_tool = self.tools[tool_name]
            self.viewport().setCursor(Qt.CrossCursor)

    def set_active_color(self, color_hex):
        """Сохраняем цвет, выбранный в палитре"""
        self.current_color = color_hex
        print(f"Цвет изменен на: {color_hex}")

        selected_items = self.scene.selectedItems()
        for item in selected_items:
            # Проверяем, есть ли у предмета наш метод (он есть и у фигур, и у Групп!)
            if hasattr(item, "set_active_color"):
                item.set_active_color(color_hex)

    # --- ДЕЛЕГИРОВАНИЕ СОБЫТИЙ (Паттерн State) ---
    # Мы просто передаем управление активному инструменту

    def mousePressEvent(self, event):
        # Импортируем инструмент внутри для проверки типа
        from src.logic.tools import SelectionTool

        # Если зажат Shift И выбран инструмент выделения
        if (event.modifiers() & Qt.ShiftModifier) and isinstance(self.current_tool, SelectionTool):
            # Включаем режим прямоугольной рамки
            self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
            # Передаем событие в базовый класс QGraphicsView (он сам отрисует рамку)
            super().mousePressEvent(event)
        else:
            # Иначе — обычная работа инструмента (рисование, клик по фигуре)
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            self.current_tool.mouse_press(event)

    def mouseMoveEvent(self, event):
        # 1. Сначала даем инструменту порисовать или подвигать объект
        if self.current_tool:
            self.current_tool.mouse_move(event)

        # 2. А теперь, ЕСЛИ мы в режиме выделения (SelectionTool) и тянем объект, обновляем панель
        from src.logic.tools import SelectionTool # Импорт внутри, чтобы не было круговой зависимости

        if isinstance(self.current_tool, SelectionTool):
            if event.buttons() & Qt.LeftButton and self.scene.selectedItems():
                self.scene.selectionChanged.emit()

    def mouseReleaseEvent(self, event):
        # 1. Сначала даем базовому классу завершить выделение рамкой (если оно было)
        super().mouseReleaseEvent(event)

        # 2. Передаем событие инструменту
        self.current_tool.mouse_release(event)

        # 3. ВСЕГДА выключаем режим рамки после отпускания кнопки,
        # чтобы он не мешал работать инструменту дальше
        self.setDragMode(QGraphicsView.DragMode.NoDrag)

    def group_selection(self):
        """Создает группу из выделенных элементов"""
        selected_items = self.scene.selectedItems()

        # Защита от дурака: не группируем пустоту
        if not selected_items:
            return

        # 1. Создаем группу
        group = Group()

        # 2. Сначала добавляем пустую группу на сцену!
        # Это важно для корректной инициализации координат.
        self.scene.addItem(group)

        # 3. Переносим элементы
        for item in selected_items:
            # Снимаем выделение с ребенка (теперь он часть целого)
            item.setSelected(False)

            # ВАЖНО: addToGroup делает "reparenting".
            # Она сама удаляет item со сцены и добавляет его в дети группы.
            # Она сама пересчитывает координаты item.pos(), чтобы он визуально остался на месте.
            group.addToGroup(item)

        # 4. Выделяем новую группу, чтобы пользователь видел результат
        group.setSelected(True)
        print("Группа создана")

    def ungroup_selection(self):
        """Разбивает выделенные группы на отдельные элементы"""
        selected_items = self.scene.selectedItems()

        for item in selected_items:
            # Проверяем, является ли элемент группой.
            if isinstance(item, Group):
                # ИСПРАВЛЕНО: Правильное название метода - destroyItemGroup
                self.scene.destroyItemGroup(item)
                print("Группа расформирована")

    def keyPressEvent(self, event):
        # 1. Быстрое переключение на инструмент выделения по ПРОБЕЛУ
        if event.key() == Qt.Key_Space:
            # Находим окно, чтобы вызвать смену инструмента (как если бы нажали кнопку)
            window = self.window()
            if hasattr(window, "on_change_tool"):
                window.on_change_tool("select")
            return

        # 2. Обработка Enter для многоугольника
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            from src.logic.tools import PolygonTool
            if isinstance(self.current_tool, PolygonTool):
                self.current_tool.finish_polygon(closed=False)
                return

        # 3. Если жмем Delete — удаляем через макрос
        if event.key() == Qt.Key_Delete:
            self.delete_selected()
            return

        selected_items = self.scene.selectedItems()
        if not selected_items:
            super().keyPressEvent(event)
            return


        super().keyPressEvent(event)

        # 2. Если это первое нажатие стрелки — запоминаем, где всё стояло
        if not self.key_move_positions:
            for item in selected_items:
                self.key_move_positions[item] = item.pos()

        # 3. Считаем шаг
        step = 10 if event.modifiers() & Qt.ShiftModifier else 1
        dx, dy = 0, 0

        if event.key() == Qt.Key_Left: dx = -step
        elif event.key() == Qt.Key_Right: dx = step
        elif event.key() == Qt.Key_Up: dy = -step
        elif event.key() == Qt.Key_Down: dy = step

        # 4. ДВИГАЕМ (просто меняем координаты, в Undo пока ничего не пишем)
        if dx != 0 or dy != 0:
            for item in selected_items:
                item.setPos(item.x() + dx, item.y() + dy)
            self.scene.selectionChanged.emit()
        else:
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        # 5. Когда стрелку ОТПУСТИЛИ — один раз записываем результат в историю
        if event.key() in [Qt.Key_Left, Qt.Key_Right, Qt.Key_Up, Qt.Key_Down]:
            selected_items = self.scene.selectedItems()

            if selected_items and self.key_move_positions:
                self.undo_stack.beginMacro("Move with Keys")
                for item in selected_items:
                    old_pos = self.key_move_positions.get(item)
                    new_pos = item.pos()
                    if old_pos and old_pos != new_pos:
                        # Создаем команду только по факту итогового сдвига
                        cmd = MoveCommand(item, old_pos, new_pos)
                        self.undo_stack.push(cmd)
                self.undo_stack.endMacro()

            # Сбрасываем позиции для следующего раза
            self.key_move_positions.clear()

        super().keyReleaseEvent(event)


    def delete_selected(self):
        selected = self.scene.selectedItems()
        if not selected:
            return

        # 1. Открываем группировку (Макрос)
        self.undo_stack.beginMacro("Delete Selection")

        # 2. Проходим по каждой фигуре и создаем отдельную команду
        for item in selected:
            # Важно: если в твоем commands.py класс называется DeleteShapeCommand,
            # пиши его. Если в модуле просят DeleteCommand — пиши так.
            # Главное, чтобы здесь был ОДИН item, а не список [item]
            cmd = DeleteShapeCommand(self.scene, item)
            self.undo_stack.push(cmd)

        # 3. Закрываем группировку
        self.undo_stack.endMacro()