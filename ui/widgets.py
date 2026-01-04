from PyQt5.QtWidgets import (QComboBox, QPushButton, 
                             QLineEdit, QCheckBox, QGroupBox)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import pyqtSignal
from styles.vs_code_theme import VSCodeTheme

class StyledComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFont(QFont(VSCodeTheme.FONT_FAMILY, 10))
        self.setStyleSheet(f"""
            QComboBox {{
                background-color: {VSCodeTheme.BACKGROUND_LIGHT};
                color: {VSCodeTheme.FOREGROUND};
                border: 1px solid {VSCodeTheme.BACKGROUND_LIGHTER};
                border-radius: 3px;
                padding: 5px;
                min-width: 80px;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid {VSCodeTheme.FOREGROUND_DARK};
                width: 0px;
                height: 0px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {VSCodeTheme.BACKGROUND_LIGHT};
                color: {VSCodeTheme.FOREGROUND};
                selection-background-color: {VSCodeTheme.ACCENT};
                border: 1px solid {VSCodeTheme.BACKGROUND_LIGHTER};
            }}
            QComboBox:hover {{
                border: 1px solid {VSCodeTheme.ACCENT};
            }}
        """)

class CustomBaudrateComboBox(StyledComboBox):
    """支持自定义波特率的下拉框"""
    custom_baudrate_selected = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.NoInsert)
        self.setFont(QFont(VSCodeTheme.FONT_FAMILY, 10))
        self.lineEdit().setFont(QFont(VSCodeTheme.FONT_FAMILY, 10))
        # 常用波特率列表
        self.common_baudrates = [
            110, 300, 600, 1200, 2400, 4800, 9600, 14400, 19200, 
            28800, 38400, 56000, 57600, 115200, 128000, 230400, 
            256000, 460800, 500000, 576000, 921600, 1000000, 1152000, 
            1500000, 2000000, 2500000, 3000000, 3500000, 4000000
        ]
        
        for baudrate in self.common_baudrates:
            self.addItem(str(baudrate), baudrate)
        
        self.setCurrentText("115200")
        self.lineEdit().editingFinished.connect(self.on_editing_finished)
        self.currentTextChanged.connect(self.on_text_changed)
    
    def on_editing_finished(self):
        self.validate_and_emit()
    
    def on_text_changed(self, text):
        if self.lineEdit().hasFocus():
            self.validate_and_emit()
    
    def validate_and_emit(self):
        text = self.currentText().strip()
        if text:
            try:
                baudrate = int(text)
                if baudrate > 0:
                    self.custom_baudrate_selected.emit(baudrate)
                    if baudrate not in self.common_baudrates:
                        self.addItem(str(baudrate), baudrate)
                else:
                    self.show_error_style()
            except ValueError:
                self.show_error_style()
    
    def show_error_style(self):
        self.setStyleSheet(f"""
            QComboBox {{
                background-color: {VSCodeTheme.BACKGROUND_LIGHT};
                color: {VSCodeTheme.RED};
                border: 2px solid {VSCodeTheme.RED};
                border-radius: 3px;
                padding: 5px;
                min-width: 80px;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid {VSCodeTheme.RED};
                width: 0px;
                height: 0px;
            }}
        """)
        
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(3000, self.restore_style)
    
    def restore_style(self):
        self.setStyleSheet(f"""
            QComboBox {{
                background-color: {VSCodeTheme.BACKGROUND_LIGHT};
                color: {VSCodeTheme.FOREGROUND};
                border: 1px solid {VSCodeTheme.BACKGROUND_LIGHTER};
                border-radius: 3px;
                padding: 5px;
                min-width: 80px;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid {VSCodeTheme.FOREGROUND_DARK};
                width: 0px;
                height: 0px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {VSCodeTheme.BACKGROUND_LIGHT};
                color: {VSCodeTheme.FOREGROUND};
                selection-background-color: {VSCodeTheme.ACCENT};
                border: 1px solid {VSCodeTheme.BACKGROUND_LIGHTER};
            }}
            QComboBox:hover {{
                border: 1px solid {VSCodeTheme.ACCENT};
            }}
        """)
    
    def get_baudrate(self):
        try:
            return int(self.currentText())
        except ValueError:
            return 115200

class StyledButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.set_default_style()
        self.setFont(QFont(VSCodeTheme.FONT_FAMILY, 10))
    def set_default_style(self):
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {VSCodeTheme.ACCENT};
                color: white;
                border: none;
                border-radius: 3px;
                padding: 8px 16px;
                font-weight: bold;
                min-width: 80px;
            }}
            QPushButton:hover {{
                background-color: {VSCodeTheme.ACCENT_HOVER};
            }}
            QPushButton:pressed {{
                background-color: {VSCodeTheme.BLUE};
            }}
            QPushButton:disabled {{
                background-color: {VSCodeTheme.BACKGROUND_LIGHTER};
                color: {VSCodeTheme.FOREGROUND_DARK};
            }}
        """)
    
    def set_danger_style(self):
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {VSCodeTheme.RED};
                color: white;
                border: none;
                border-radius: 3px;
                padding: 8px 16px;
                font-weight: bold;
                min-width: 80px;
            }}
            QPushButton:hover {{
                background-color: #d32f2f;
            }}
        """)
    def set_checked_style(self):
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {VSCodeTheme.GREEN};
                color: white;
                border: none;
                border-radius: 3px;
                padding: 8px 16px;
                font-weight: bold;
                min-width: 80px;
            }}
            QPushButton:hover {{
                background-color: {VSCodeTheme.GREEN_HOVER};
            }}
            QPushButton:pressed {{
                background-color: {VSCodeTheme.GREEN_DARK};
            }}
        """)

class StyledLineEdit(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFont(QFont(VSCodeTheme.FONT_FAMILY, 10))
        self.setStyleSheet(f"""
            QLineEdit {{
                background-color: {VSCodeTheme.BACKGROUND_LIGHT};
                color: {VSCodeTheme.FOREGROUND};
                border: 1px solid {VSCodeTheme.BACKGROUND_LIGHTER};
                border-radius: 3px;
                padding: 8px;
                selection-background-color: {VSCodeTheme.ACCENT};
            }}
            QLineEdit:focus {{
                border: 1px solid {VSCodeTheme.ACCENT};
            }}
        """)

class StyledCheckBox(QCheckBox):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setFont(QFont(VSCodeTheme.FONT_FAMILY, 10))
        self.setStyleSheet(f"""
            QCheckBox {{
                color: {VSCodeTheme.FOREGROUND};
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border: 1px solid {VSCodeTheme.BACKGROUND_LIGHTER};
                border-radius: 3px;
                background-color: {VSCodeTheme.BACKGROUND_LIGHT};
            }}
            QCheckBox::indicator:checked {{
                background-color: {VSCodeTheme.ACCENT};
                border: 1px solid {VSCodeTheme.ACCENT};
            }}
            QCheckBox::indicator:checked:hover {{
                background-color: {VSCodeTheme.ACCENT_HOVER};
                border: 1px solid {VSCodeTheme.ACCENT_HOVER};
            }}
            QCheckBox::indicator:hover {{
                border: 1px solid {VSCodeTheme.ACCENT};
            }}
        """)

class StyledGroupBox(QGroupBox):
    def __init__(self, title, parent=None):
        super().__init__(title, parent)
        self.setFont(QFont(VSCodeTheme.FONT_FAMILY, 10))
        self.setStyleSheet(f"""
            QGroupBox {{
                color: {VSCodeTheme.FOREGROUND};
                font-weight: bold;
                border: 1px solid {VSCodeTheme.BACKGROUND_LIGHTER};
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
                color: {VSCodeTheme.BLUE};
            }}
        """)