from PyQt5.QtWidgets import (QComboBox, QPushButton, QTextEdit, 
                             QLineEdit, QCheckBox, QGroupBox, QSplitter,
                             QHBoxLayout, QWidget, QLabel, QVBoxLayout)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import pyqtSignal, Qt
from styles.vs_code_theme import VSCodeTheme
from .lazy_text_edit import LazyTextEdit

class StyledLazyTextEdit(LazyTextEdit):
    """带样式的懒加载文本框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        font = QFont(VSCodeTheme.FONT_FAMILY, 10)
        self.setFont(font)

class ComparisonTextDisplay(QWidget):
    """文本和十六进制对照显示控件（懒加载版本）"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.connect_scroll_bars()
    
    def init_ui(self):
        """初始化UI"""
        layout = QHBoxLayout(self)
        layout.setSpacing(5)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建分割器
        self.splitter = QSplitter(Qt.Horizontal)
        
        # 文本显示区域
        text_widget = QWidget()
        text_layout = QVBoxLayout(text_widget)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.addWidget(QLabel("📝 文本显示"))
        self.text_display = StyledLazyTextEdit()
        self.text_display.setPlaceholderText("文本内容将显示在这里...")
        text_layout.addWidget(self.text_display)
        
        # 十六进制显示区域
        hex_widget = QWidget()
        hex_layout = QVBoxLayout(hex_widget)
        hex_layout.setContentsMargins(0, 0, 0, 0)
        hex_layout.addWidget(QLabel("🔢 十六进制显示"))
        self.hex_display = StyledLazyTextEdit()
        self.hex_display.setPlaceholderText("十六进制内容将显示在这里...")
        hex_layout.addWidget(self.hex_display)
        
        # 添加到分割器
        self.splitter.addWidget(text_widget)
        self.splitter.addWidget(hex_widget)
        
        # 设置分割比例
        self.splitter.setSizes([400, 400])
        
        layout.addWidget(self.splitter)
    
    def connect_scroll_bars(self):
        """连接滚动条实现同步滚动"""
        # 文本区域的垂直滚动条
        text_vbar = self.text_display.verticalScrollBar()
        hex_vbar = self.hex_display.verticalScrollBar()
        
        # 连接滚动条信号
        text_vbar.valueChanged.connect(hex_vbar.setValue)
        hex_vbar.valueChanged.connect(text_vbar.setValue)
    
    def set_total_chunks(self, total_chunks: int):
        """设置总块数"""
        self.text_display.set_total_chunks(total_chunks)
        self.hex_display.set_total_chunks(total_chunks)
    
    def append_chunk(self, text_content: str, hex_content: str, chunk_index: int):
        """追加一个内容块到两个显示区域"""
        self.text_display.append_chunk(chunk_index, text_content)
        self.hex_display.append_chunk(chunk_index, hex_content)
    
    def append_text(self, text_content: str, hex_content: str):
        """追加文本到两个显示区域（直接追加，不分块）"""
        # 追加文本内容
        text_cursor = self.text_display.textCursor()
        text_cursor.movePosition(text_cursor.End)
        text_cursor.insertText(text_content + '\n')
        
        # 追加十六进制内容
        hex_cursor = self.hex_display.textCursor()
        hex_cursor.movePosition(hex_cursor.End)
        hex_cursor.insertText(hex_content + '\n')
    
    def clear(self):
        """清空两个显示区域"""
        self.text_display.clear()
        self.hex_display.clear()
    
    def scroll_to_bottom(self):
        """滚动到底部"""
        self.text_display.verticalScrollBar().setValue(
            self.text_display.verticalScrollBar().maximum()
        )
        self.hex_display.verticalScrollBar().setValue(
            self.hex_display.verticalScrollBar().maximum()
        )
    
    def connect_load_signals(self, text_slot, hex_slot):
        """连接加载信号"""
        self.text_display.load_more_requested.connect(text_slot)
        self.hex_display.load_more_requested.connect(hex_slot)

# 其他控件类保持不变...
class StyledComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
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

class StyledTextEdit(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        font = QFont(VSCodeTheme.FONT_FAMILY, 10)
        self.setFont(font)
        self.setStyleSheet(f"""
            QTextEdit {{
                background-color: {VSCodeTheme.BACKGROUND};
                color: {VSCodeTheme.FOREGROUND};
                border: 1px solid {VSCodeTheme.BACKGROUND_LIGHTER};
                border-radius: 3px;
                padding: 8px;
                selection-background-color: {VSCodeTheme.ACCENT};
            }}
            QScrollBar:vertical {{
                background-color: {VSCodeTheme.BACKGROUND_LIGHT};
                width: 12px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {VSCodeTheme.BACKGROUND_LIGHTER};
                border-radius: 6px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {VSCodeTheme.ACCENT};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                border: none;
                background: none;
            }}
        """)

class StyledLineEdit(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
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