from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QSpinBox, QDoubleSpinBox, QPushButton, QColorDialog)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from src.logic.commands import ChangeColorCommand, ChangeWidthCommand

class PropertiesPanel(QWidget):
    def __init__(self, scene, undo_stack):
        super().__init__()
        self.scene = scene
        self.undo_stack = undo_stack
        self._init_ui()

        # ПАТТЕРН OBSERVER: Подписываемся на сигнал сцены о смене выделения.
        # Как только пользователь кликнет по фигуре, вызовется наш метод.
        self.scene.selectionChanged.connect(self.on_selection_changed)

    def _init_ui(self):
        """Создание интерфейса панели"""
        self.setMinimumWidth(250) # Фиксируем ширину, чтобы UI не "прыгал"
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignTop)

        # 1. Заголовок (Интроспекция)
        self.label_obj_type = QLabel("ОБЪЕКТ: не выбран")
        self.label_obj_type.setStyleSheet("font-weight: bold; color: #ff9d00; margin-bottom: 10px;")
        layout.addWidget(self.label_obj_type)

        # Контейнер для настроек (его мы будем выключать/включать)
        self.container = QWidget()
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(0, 0, 0, 0)

        # --- СЕКЦИЯ ГЕОМЕТРИИ (X, Y) ---
        geo_layout = QHBoxLayout()
        # QDoubleSpinBox используем для точности координат (с плавающей точкой)
        self.spin_x = QDoubleSpinBox(); self.spin_x.setPrefix("X: ")
        self.spin_y = QDoubleSpinBox(); self.spin_y.setPrefix("Y: ")

        for s in [self.spin_x, self.spin_y]:
            s.setRange(-10000, 10000)
            s.setDecimals(1)
            s.valueChanged.connect(self.on_geo_changed)
            geo_layout.addWidget(s)
        self.container_layout.addLayout(geo_layout)

        # --- СЕКЦИЯ ТОЛЩИНЫ ---
        width_layout = QHBoxLayout()
        width_layout.addWidget(QLabel("Толщина:"))
        self.spin_width = QSpinBox()
        self.spin_width.setRange(1, 20)
        self.spin_width.valueChanged.connect(self.on_width_changed)
        width_layout.addWidget(self.spin_width)
        self.container_layout.addLayout(width_layout)

        # --- СЕКЦИЯ ЦВЕТА ---
        self.btn_color = QPushButton("Цвет линии")
        self.btn_color.setFixedHeight(35)
        self.btn_color.clicked.connect(self.on_change_color)
        self.container_layout.addWidget(self.btn_color)

        layout.addWidget(self.container)
        self.container.setEnabled(False) # По умолчанию всё неактивно

    def _get_all_shapes(self, items):
        """Рекурсивная функция для поиска всех фигур (даже внутри групп)"""
        all_shapes = []
        for item in items:
            # Если у объекта есть дети (это группа), идем вглубь
            if hasattr(item, 'childItems') and item.childItems():
                all_shapes.extend(self._get_all_shapes(item.childItems()))
            else:
                all_shapes.append(item)
        return all_shapes

    def on_selection_changed(self):
        """MODEL -> VIEW: Обновление панели при выборе объекта"""
        try:
            # Проверка на "живучесть" объекта (защита от RuntimeError при закрытии)
            if not self.scene: return
            selected = self.scene.selectedItems()
        except (RuntimeError, AttributeError):
            return

        if not selected:
            self.label_obj_type.setText("ОБЪЕКТ: не выбран")
            self.container.setEnabled(False)

            self.block_signals(True)
            self.spin_x.setValue(0)
            self.spin_y.setValue(0)
            self.spin_width.setSpecialValueText("")
            self.spin_width.setValue(1)

            # ВОТ ЭТО ОБНУЛЯЕТ КНОПКУ ЦВЕТА К СТАНДАРТУ
            self.btn_color.setText("Цвет линии")
            self.btn_color.setStyleSheet("""
                QPushButton {
                    background-color: none;
                    color: black;
                    border: 1px solid #999;
                }
            """)
            self.block_signals(False)
            return

        self.container.setEnabled(True)

        # Интроспекция: узнаем имя класса выбранного объекта
        if len(selected) > 1:
            self.label_obj_type.setText(f"ВЫБРАНО: {len(selected)} объектов")
        else:
            self.label_obj_type.setText(f"ОБЪЕКТ: {type(selected[0]).__name__.upper()}")

        # Собираем данные для проверки Mixed Values
        all_child_shapes = self._get_all_shapes(selected)

        # Блокируем сигналы, чтобы обновление UI не вызывало методы on_changed (зацикливание)
        self.block_signals(True)

        # Обновляем координаты (по первому объекту)
        self.spin_x.setValue(selected[0].x())
        self.spin_y.setValue(selected[0].y())

        # Логика Mixed Width (Разная толщина)
        widths = [s.pen().width() for s in all_child_shapes if hasattr(s, 'pen')]
        if len(set(widths)) > 1:
            self.spin_width.setSpecialValueText("Mixed") # Показывает текст вместо числа
            self.spin_width.setValue(self.spin_width.minimum())
        elif widths:
            self.spin_width.setSpecialValueText("")
            self.spin_width.setValue(widths[0])

        # Логика Mixed Color + Отображение HEX кода
        colors = [s.pen().color().name() for s in all_child_shapes if hasattr(s, 'pen')]
        if len(set(colors)) > 1:
            self.btn_color.setText("Цвет: Mixed")
            self.btn_color.setStyleSheet("border: 2px dashed #777;")
        elif colors:
            hex_code = colors[0].upper()
            self.btn_color.setText(f"Цвет: {hex_code}")

            # Определяем яркость, чтобы выбрать цвет текста (белый или черный)
            lum = QColor(colors[0]).lightness()
            text_color = "black" if lum > 160 else "white"
            self.btn_color.setStyleSheet(f"background-color: {hex_code}; color: {text_color}; font-weight: bold;")

        self.block_signals(False)

    def on_geo_changed(self):
        """VIEW -> MODEL: Изменение позиции из панели"""
        for item in self.scene.selectedItems():
            item.setPos(self.spin_x.value(), self.spin_y.value())

    def on_width_changed(self, value):
        """Изменение толщины через команду"""
        selected = self.scene.selectedItems()
        if not selected: return

        # Чтобы не спамить командами при каждом шаге спинбокса,
        # здесь используется макрос.
        self.undo_stack.beginMacro("Change Width")
        for item in selected:
            if hasattr(item, 'set_active_color'):
                cmd = ChangeWidthCommand(item, value)
                self.undo_stack.push(cmd)
        self.undo_stack.endMacro()

    def on_change_color(self):
        """Вызов диалога и создание команды"""
        color = QColorDialog.getColor()
        if color.isValid():
            hex_color = color.name()
            selected = self.scene.selectedItems()
            if not selected: return

            # МАКРОС: Один клик в палитре = одна запись в Undo
            self.undo_stack.beginMacro("Change Color")
            for item in selected:
                if hasattr(item, 'set_active_color'):
                    cmd = ChangeColorCommand(item, hex_color)
                    self.undo_stack.push(cmd)
            self.undo_stack.endMacro()

            self.on_selection_changed()

    def block_signals(self, block):
        """Вспомогательный метод для блокировки сигналов всех виджетов"""
        self.spin_x.blockSignals(block)
        self.spin_y.blockSignals(block)
        self.spin_width.blockSignals(block)