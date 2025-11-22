# preference_window.py

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QLabel, QPushButton, QFontComboBox, QSpinBox, QColorDialog,
                             QHBoxLayout, QMessageBox, QComboBox, QLineEdit, QCheckBox)
from PyQt5.QtCore import Qt, QPoint
from styles.vs_code_theme import VSCodeTheme
from utils.config_handler import ConfigHandler
from ui.widgets import (StyledComboBox, CustomBaudrateComboBox, StyledButton, 
                       StyledTextEdit, StyledLineEdit, StyledCheckBox, 
                       StyledGroupBox, ComparisonTextDisplay, StyledLazyTextEdit)

class PreferenceWindow(QDialog):
    """首选项窗口"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🔧 设置首选项")
        self.resize(400, 300)
        self.text_color = VSCodeTheme.FOREGROUND
        self.bg_color = VSCodeTheme.BACKGROUND_LIGHT
        self.init_ui()
        self.load_config()

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        
        # 串口设置
        serial_group = StyledGroupBox("📡 串口设置")
        serial_layout = QVBoxLayout()
        
        serial_layout.addWidget(QLabel("数据位:"))
        self.data_bits_combo = StyledComboBox()
        self.data_bits_combo.addItems(["7", "8"])
        serial_layout.addWidget(self.data_bits_combo)
        
        serial_layout.addWidget(QLabel("停止位:"))
        self.stop_bits_combo = StyledComboBox()
        self.stop_bits_combo.addItems(["1", "1.5", "2"])
        serial_layout.addWidget(self.stop_bits_combo)
        
        serial_layout.addWidget(QLabel("校验位:"))
        self.parity_combo = StyledComboBox()
        self.parity_combo.addItems(["无", "奇", "偶"])
        serial_layout.addWidget(self.parity_combo)
        
        serial_group.setLayout(serial_layout)
        layout.addWidget(serial_group)
        
        # 日志显示设置
        log_display_group = StyledGroupBox("📜 日志显示设置")
        log_display_layout = QVBoxLayout()
        
        # 字体选择
        log_display_layout.addWidget(QLabel("Font:"))
        self.font_combo = QFontComboBox()
        # 过滤只显示等宽字体 (可选，但推荐，因为 Hex 模式依赖对齐)
        self.font_combo.setFontFilters(QFontComboBox.MonospacedFonts) 
        # 默认设为 Cascadia Code
        self.set_font_str("Cascadia Code")
        
        log_display_layout.addWidget(self.font_combo)

        # 字号选择
        log_display_layout.addWidget(QLabel("Size:"))
        self.spin_size = QSpinBox()
        self.spin_size.setRange(6, 72)
        self.spin_size.setValue(10)
        log_display_layout.addWidget(self.spin_size)
        
        # 颜色选择
        self.btn_color = QPushButton("Text Color")
        self.btn_color.clicked.connect(self.pick_color)
        log_display_layout.addWidget(self.btn_color)

        self.btn_bg_color = QPushButton("BG Color")
        self.btn_bg_color.clicked.connect(self.pick_bg_color)
        log_display_layout.addWidget(self.btn_bg_color)
        
        log_display_layout.addStretch()
        
        log_display_group.setLayout(log_display_layout)
        layout.addWidget(log_display_group)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        self.save_btn = StyledButton("💾 保存")
        self.save_btn.clicked.connect(self.save_preferences)
        button_layout.addWidget(self.save_btn)
        
        self.cancel_btn = StyledButton("❌ 取消")
        self.cancel_btn.clicked.connect(self.close)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
    
    def load_config(self):
        """加载配置文件"""
        try:
            config = ConfigHandler.load_config()
            if 'data_bits' in config:
                self.data_bits_combo.setCurrentText(str(config['data_bits']))
            if 'stop_bits' in config:
                self.stop_bits_combo.setCurrentText(str(config['stop_bits']))
            if 'parity' in config:
                self.parity_combo.setCurrentText(config['parity'])
            if 'font' in config:
                self.set_font_str(config['font'])
            if 'font_size' in config:
                self.spin_size.setValue(config['font_size'])
            if 'font_color' in config:
                self.text_color = config['font_color']
            if 'bg_color' in config:
                self.bg_color = config['bg_color']

        except Exception as e:
            QMessageBox.critical(self, "加载配置失败", str(e))

    def save_preferences(self):
        """保存配置文件"""
        config = {
            'data_bits': int(self.data_bits_combo.currentText()),
            'stop_bits': self.stop_bits_combo.currentText(),
            'parity': self.parity_combo.currentText(),
            'font': self.font_combo.currentFont().family(),
            'font_size': int(self.spin_size.value()) if self.spin_size.value() else 10,
            'font_color': self.text_color or VSCodeTheme.FOREGROUND,
            'bg_color': self.bg_color or VSCodeTheme.BACKGROUND_LIGHT
        }
        
        try:
            ConfigHandler.save_config(config)
            self.close()
        except Exception as e:
            QMessageBox.critical(self, "保存配置失败", str(e))

    def set_font_str(self, font_str):
        font_idx = -1
        for i in range(self.font_combo.count()):
            if font_str in self.font_combo.itemText(i):
                font_idx = i
                break
        if font_idx != -1: self.font_combo.setCurrentIndex(font_idx)

    def pick_color(self):
        color = QColorDialog.getColor(Qt.white, self, "Select Text Color")
        if color.isValid():
            self.text_color = color.name()

    def pick_bg_color(self):
        color = QColorDialog.getColor(Qt.black, self, "Select Background Color")
        if color.isValid():
            self.bg_color = color.name()
