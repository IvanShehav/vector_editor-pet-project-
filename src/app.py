# src/app.py
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QPushButton, QFrame, QColorDialog, QFileDialog,
                               QMessageBox, QGraphicsView)
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtCore import Qt
from src.widgets.canvas import EditorCanvas
from src.widgets.properties import PropertiesPanel
from src.logic.strategies import JsonSaveStrategy, ImageSaveStrategy
from src.logic.factory import ShapeFactory
from src.logic.tools import SelectionTool, CreationTool, PolygonTool
import json

class VectorEditorWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Vector Editor")
        self.resize(1000, 700)
        self._setup_layout()
        self._init_ui()

    def _init_ui(self):
        self.statusBar().showMessage("Готов к работе")
        menubar = self.menuBar()
        stack = self.canvas.undo_stack

        file_menu = menubar.addMenu("&File")
        open_action = QAction("Open Project...", self)
        open_action.setShortcut(QKeySequence.Open)
        open_action.triggered.connect(self.on_open_clicked)
        file_menu.addAction(open_action)

        save_action = QAction("Save / Export...", self)
        save_action.setShortcut(QKeySequence.Save)
        save_action.triggered.connect(self.on_save_clicked)
        file_menu.addAction(save_action)

        file_menu.addSeparator()
        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        edit_menu = menubar.addMenu("&Edit")
        undo_action = stack.createUndoAction(self, "&Undo")
        undo_action.setShortcut(QKeySequence.Undo)
        redo_action = stack.createRedoAction(self, "&Redo")
        redo_action.setShortcut(QKeySequence.Redo)

        delete_action = QAction("Delete", self)
        delete_action.setShortcut(QKeySequence.Delete)
        delete_action.triggered.connect(self.canvas.delete_selected)

        group_action = QAction("Group", self)
        group_action.setShortcut(QKeySequence("Ctrl+G"))
        group_action.triggered.connect(self.canvas.group_selection)

        ungroup_action = QAction("Ungroup", self)
        ungroup_action.setShortcut(QKeySequence("Ctrl+U"))
        ungroup_action.triggered.connect(self.canvas.ungroup_selection)

        edit_menu.addAction(undo_action)
        edit_menu.addAction(redo_action)
        edit_menu.addSeparator()
        edit_menu.addAction(delete_action)
        edit_menu.addSeparator()
        edit_menu.addAction(group_action)
        edit_menu.addAction(ungroup_action)

        self.props_panel = PropertiesPanel(self.canvas.scene, stack)
        self.main_layout.addWidget(self.props_panel)


    def _setup_layout(self):
        container = QWidget()
        self.setCentralWidget(container)

        self.main_layout = QHBoxLayout(container)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        tools_panel = QFrame()
        tools_panel.setFixedWidth(120)
        tools_panel.setStyleSheet("background-color: #2b2b2b; border-right: 1px solid #1a1a1a;")

        tools_layout = QVBoxLayout(tools_panel)
        tools_layout.setContentsMargins(10, 20, 10, 10)
        tools_layout.setSpacing(15)

        tool_style = """
            QPushButton {
                background-color: #505050; color: #ffffff; border: none;
                border-radius: 6px; font-weight: bold; font-size: 13px; padding: 10px;
            }
            QPushButton:hover { background-color: #606060; }
            QPushButton:checked { background-color: #ff9d00; color: #000000; }
        """

        # Кнопки (добавлен Polygon)
        self.btn_select = QPushButton("Select")
        self.btn_line = QPushButton("Line")
        self.btn_rect = QPushButton("Rect")
        self.btn_ellipse = QPushButton("Ellipse")
        self.btn_poly = QPushButton("Polygon") # <--- ТУТ

        self.btn_color = QPushButton("Color")
        self.btn_color.setFixedHeight(50)
        self.btn_color.setStyleSheet("background-color: #000000; color: white; border-radius: 6px; border: 2px solid #555;")

        # Помещаем в список для стилизации
        buttons = [self.btn_select, self.btn_line, self.btn_rect, self.btn_ellipse, self.btn_poly]

        for btn in buttons:
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(tool_style)
            tools_layout.addWidget(btn)

        tools_layout.addWidget(self.btn_color)
        tools_layout.addStretch()

        self.canvas = EditorCanvas()
        self.main_layout.addWidget(tools_panel)
        self.main_layout.addWidget(self.canvas)


        self.btn_select.clicked.connect(lambda: self.on_change_tool("select"))
        self.btn_line.clicked.connect(lambda: self.on_change_tool("line"))
        self.btn_rect.clicked.connect(lambda: self.on_change_tool("rect"))
        self.btn_ellipse.clicked.connect(lambda: self.on_change_tool("ellipse"))
        self.btn_poly.clicked.connect(lambda: self.on_change_tool("polygon")) # <--- И ТУТ

        self.btn_color.clicked.connect(self.on_select_color)

        self.on_change_tool("select")

    def on_change_tool(self, tool_name):
        self.current_tool = tool_name

        # Радио-эффект кнопок
        self.btn_select.setChecked(tool_name == "select")
        self.btn_line.setChecked(tool_name == "line")
        self.btn_rect.setChecked(tool_name == "rect")
        self.btn_ellipse.setChecked(tool_name == "ellipse")
        self.btn_poly.setChecked(tool_name == "polygon")

        if tool_name == "polygon":
            # ВЫКЛЮЧАЕМ ладошку принудительно
            self.canvas.setDragMode(QGraphicsView.NoDrag)
            self.canvas.viewport().setCursor(Qt.CrossCursor) # Ставим крестик

            self.canvas.current_tool = PolygonTool(self.canvas)
            self.statusBar().showMessage("Инструмент: Многоугольник (Клик - точка, Enter - готово)")
        else:
            # Для остальных инструментов (select, rect и т.д.)
            self.canvas.set_tool(tool_name)

    def on_select_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            hex_color = color.name()
            # Обновляем кнопку
            self.btn_color.setStyleSheet(f"""
                QPushButton {{
                    background-color: {hex_color}; 
                    border: 2px solid #ff9d00; 
                    border-radius: 6px;
                }}
            """)
            # Передаем в холст
            self.canvas.current_color = hex_color



    def _collect_scene_data(self):
        # 1. Метаданные
        project_data = {
            "version": "1.0",
            "scene": {
                "width": self.canvas.scene.width(),
                "height": self.canvas.scene.height()
            },
            "shapes": []
        }

        # 2. Сбор фигур
        # scene.items() возвращает объекты от верхнего к нижнему.
        # Нам нужно наоборот (от фона к переднему плану), чтобы при загрузке
        # они наложились правильно.
        items_in_order = self.canvas.scene.items()[::-1]

        for item in items_in_order:
            # Проверяем, умеет ли объект сохраняться (наш ли это Shape?)
            # Игнорируем вспомогательные объекты (курсоры, сетку и т.д.)
            if hasattr(item, "to_dict"):
                project_data["shapes"].append(item.to_dict())

        return project_data

    def on_save_clicked(self):
        # Добавляем новый фильтр "PNG Cropped"
        filters = (
            "Vector Project (*.json);;"
            "PNG Image (*.png);;"
            "PNG Cropped (*.png);;" # Вариант для доп. задания
            "JPEG Image (*.jpg)"
        )

        filename, selected_filter = QFileDialog.getSaveFileName(
            self, "Save File", "", filters
        )

        if not filename:
            return

        strategy = None
        ext = filename.lower()

        # Выбираем стратегию на основе выбранного фильтра или расширения
        if "Cropped" in selected_filter:
            # Включаем crop_to_content=True
            strategy = ImageSaveStrategy("PNG", background_color="transparent", crop_to_content=True)
        elif ext.endswith(".png"):
            strategy = ImageSaveStrategy("PNG", background_color="transparent", crop_to_content=False)
        elif ext.endswith(".jpg") or ext.endswith(".jpeg"):
            strategy = ImageSaveStrategy("JPG", background_color="white", crop_to_content=False)
        else:
            if not ext.endswith(".json"):
                filename += ".json"
            strategy = JsonSaveStrategy()

        try:
            strategy.save(filename, self.canvas.scene)
            self.statusBar().showMessage(f"Сохранено успешно: {filename}", 3000)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить:\n{str(e)}")



    def on_open_clicked(self):
        # 1. Спрашиваем пользователя
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Открыть проект",
            "",
            "Vector Project (*.json *.vec)"
        )

        if not path:
            return # Пользователь нажал Отмена

        # 2. Попытка загрузки (Безопасный блок)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Проверка формата (необязательно, но полезно)
            if "version" not in data or "shapes" not in data:
                raise ValueError("Некорректный формат файла")

        except Exception as e:
            # Добавляем тип ошибки для наглядности
            error_msg = f"Тип ошибки: {type(e).__name__}\nОписание: {str(e)}"
            QMessageBox.critical(self, "Ошибка загрузки", f"Не удалось прочитать файл:\n{error_msg}")
            return

        # 3. Если чтение прошло успешно — применяем изменения
        # Сначала очищаем старое!
        self.canvas.scene.clear()
        self.canvas.undo_stack.clear()

        # 4. Восстанавливаем настройки сцены
        scene_info = data.get("scene", {})
        width = scene_info.get("width", 800)
        height = scene_info.get("height", 600)
        self.canvas.scene.setSceneRect(0, 0, width, height)

        # 5. Восстанавливаем фигуры
        shapes_data = data.get("shapes", [])

        # Счетчик ошибок (если вдруг одна фигура битая, не ломаем всё остальное)
        errors_count = 0

        for shape_dict in shapes_data:
            try:
                # ВАЖНО: Используем Фабрику из Модуля 4 (с рекурсией для групп)
                shape_obj = ShapeFactory.from_dict(shape_dict)

                # Добавляем на сцену
                self.canvas.scene.addItem(shape_obj)

            except Exception as e:
                print(f"Error loading shape: {e}")
                errors_count += 1

        # 6. Финал
        if errors_count > 0:
            self.statusBar().showMessage(f"Загружено с ошибками ({errors_count} фигур пропущено)")
        else:
            self.statusBar().showMessage(f"Проект загружен: {path}")