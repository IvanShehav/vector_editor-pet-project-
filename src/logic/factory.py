from src.logic.shapes import Rectangle, Line, Ellipse, Group, Polygon

class ShapeFactory:
    @staticmethod
    def create_shape(shape_type: str, start_point, end_point, color: str):
        """
        start_point, end_point: QPointF (координаты сцены)
        """
        x1, y1 = start_point.x(), start_point.y()
        x2, y2 = end_point.x(), end_point.y()

        # Для линий нам нужны именно точки начала и конца (даже если тянем назад)
        if shape_type == 'line':
            return Line(x1, y1, x2, y2, color)

        # Для прямоугольных фигур (Rect, Ellipse) нужна нормализация
        x = min(x1, x2)
        y = min(y1, y2)
        w = abs(x2 - x1)
        h = abs(y2 - y1)

        if shape_type == 'rect':
            return Rectangle(x, y, w, h, color)
        elif shape_type == 'ellipse':
            return Ellipse(x, y, w, h, color)
        else:
            # Важно: Фабрика должна сообщать, если её попросили невозможного
            raise ValueError(f"Неизвестный тип фигуры: {shape_type}")

    @staticmethod
    def from_dict(data: dict):
        shape_type = data.get("type")

        if shape_type == "group":
            return ShapeFactory._create_group(data)
        # Добавляем "polygon" в этот список
        elif shape_type in ["rect", "line", "ellipse", "polygon"]:
            return ShapeFactory._create_primitive(data)
        else:
            raise ValueError(f"Unknown type: {shape_type}")

    @staticmethod
    def _create_primitive(data: dict):
        props = data.get("props", {})
        shape_type = data.get("type")
        color = props.get("color", "black")
        # Берем толщину из пропсов, если её нет — по умолчанию 2
        width = props.get("width", 2)

        obj = None

        if shape_type == "rect":
            obj = Rectangle(0, 0, props.get('w', 0), props.get('h', 0), color, width)
        elif shape_type == "ellipse":
            obj = Ellipse(0, 0, props.get('w', 0), props.get('h', 0), color, width)
        elif shape_type == "line":
            obj = Line(props.get('x1', 0), props.get('y1', 0),
                       props.get('x2', 0), props.get('y2', 0), color, width)
        elif shape_type == "polygon":
            from PySide6.QtCore import QPointF
            from src.logic.shapes import Polygon

            # Конвертируем список списков в список QPointF
            pts = [QPointF(p[0], p[1]) for p in props.get("points", [])]
            is_closed = props.get("is_closed", True)

            # Создаем полигон
            obj = Polygon(pts, color, width, is_closed)

        if obj:
            # 2. Восстанавливаем позицию
            pos_data = data.get("pos", [0, 0])
            target_x = pos_data[0]
            target_y = pos_data[1]

            # Если для примитивов (кроме линий и полигонов) pos нулевой,
            # берем x/y из пропсов (совместимость со старым форматом)
            if shape_type in ["rect", "ellipse"] and target_x == 0 and target_y == 0:
                target_x = props.get('x', 0)
                target_y = props.get('y', 0)

            obj.setPos(target_x, target_y)

            if hasattr(obj, 'apply_initial_config'):
                obj.apply_initial_config()

        return obj

    @staticmethod
    def _create_group(data: dict):
        children_data = data.get("children", [])

        if len(children_data) == 1:
            # Просто восстанавливаем этого одного ребенка и возвращаем его
            single_child = ShapeFactory.from_dict(children_data[0])
            return single_child

        # Если детей 0 (пустая группа), можем вернуть None или пустую группу
        if not children_data:
            return None

        group = Group()

        # Позиция группы
        x, y = data.get("pos", [0, 0])
        group.setPos(x, y)

        for child_dict in children_data:
            child_item = ShapeFactory.from_dict(child_dict)
            if child_item:
                group.addToGroup(child_item)
                # Если у ребенка в JSON есть своя позиция, восстанавливаем её
                if "pos" in child_dict:
                    child_item.setPos(child_dict["pos"][0], child_dict["pos"][1])

        if hasattr(group, 'apply_initial_config'):
            group.apply_initial_config()

        return group