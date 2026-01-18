#src/logic/commands.py

from PySide6.QtGui import QUndoCommand, QColor

class AddShapeCommand(QUndoCommand):
    def __init__(self, scene, item):
        """
        :param scene: Сцена, куда добавляем
        :param item: Сама фигура (созданная, но еще не добавленная)
        """
        super().__init__()
        self.scene = scene
        self.item = item

        # Текст для отображения в истории (например, в меню "Undo Add Rectangle")
        # Если у фигуры есть наш метод type_name, используем его
        name = "Shape"
        if hasattr(item, "type_name"):
            name = item.type_name
        self.setText(f"Add {name}")

    def redo(self):
        # Выполняется при первом добавлении И при Ctrl+Y (Redo)

        # Проверка: если предмет уже на сцене, повторно добавлять нельзя (будет краш)
        if self.item.scene() != self.scene:
            self.scene.addItem(self.item)

    def undo(self):
        # Выполняется при Ctrl+Z (Undo)
        self.scene.removeItem(self.item)
        # Фигура исчезла с экрана, но self.item хранит её в памяти!


class DeleteShapeCommand(QUndoCommand):
    def __init__(self, scene, item):
        super().__init__()
        self.scene = scene
        self.item = item

        name = getattr(item, 'type_name', 'Shape')
        self.setText(f"Delete {name}")

    def redo(self):
        self.scene.removeItem(self.item)

    def undo(self):
        self.scene.addItem(self.item)


class MoveCommand(QUndoCommand):
    def __init__(self, item, old_pos, new_pos):
        super().__init__()
        self.item = item
        self.old_pos = old_pos
        self.new_pos = new_pos
        self.setText(f"Move {getattr(item, 'type_name', 'Item')}")

    def undo(self):
        self.item.setPos(self.old_pos)

    def redo(self):
        self.item.setPos(self.new_pos)

class ChangeColorCommand(QUndoCommand):
    def __init__(self, item, new_color_hex):
        super().__init__()
        self.item = item
        self.new_color = new_color_hex

        # Запоминаем старый цвет (берем из текущего пера фигуры)
        if hasattr(item, "pen"):
            self.old_color = item.pen().color().name()
        else:
            self.old_color = "#000000"

        self.setText(f"Change Color to {new_color_hex}")

    def redo(self):
        if hasattr(self.item, "set_active_color"):
            self.item.set_active_color(self.new_color)

    def undo(self):
        if hasattr(self.item, "set_active_color"):
            self.item.set_active_color(self.old_color)


class ChangeWidthCommand(QUndoCommand):
    def __init__(self, item, new_width):
        super().__init__()
        self.item = item
        self.new_width = new_width

        # Запоминаем старую толщину
        if hasattr(item, "pen"):
            self.old_width = item.pen().width()
        else:
            self.old_width = 2

        self.setText(f"Change Width to {new_width}")

    def redo(self):
        # Используем метод, который есть в нашем интерфейсе Shape (shapes.py)
        if hasattr(self.item, "set_stroke_width"):
            self.item.set_stroke_width(self.new_width)
        else:
            # Если метода нет, меняем через стандартное перо
            p = self.item.pen()
            p.setWidth(self.new_width)
            self.item.setPen(p)

    def undo(self):
        if hasattr(self.item, "set_stroke_width"):
            self.item.set_stroke_width(self.old_width)
        else:
            p = self.item.pen()
            p.setWidth(self.old_width)
            self.item.setPen(p)