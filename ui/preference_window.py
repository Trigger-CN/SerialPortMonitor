# preference_window.py

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QLabel, QPushButton, 
                             QHBoxLayout, QComboBox, QLineEdit, QCheckBox)
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
        self.setGeometry(100, 100, 400, 300)
        
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
        
        log_display_layout.addWidget(QLabel("字体大小:"))
        self.font_size_input = StyledLineEdit()
        self.font_size_input.setPlaceholderText("输入字体大小...")
        log_display_layout.addWidget(self.font_size_input)
        
        log_display_layout.addWidget(QLabel("字体颜色:"))
        self.font_color_input = StyledLineEdit()
        self.font_color_input.setPlaceholderText("输入字体颜色的十六进制代码...")
        log_display_layout.addWidget(self.font_color_input)
        
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
            if 'font_size' in config:
                self.font_size_input.setText(str(config['font_size']))
            if 'font_color' in config:
                self.font_color_input.setText(config['font_color'])
        except Exception as e:
            self.status_label.setText(f"❌ 加载配置失败: {str(e)}")
            QMessageBox.critical(self, "加载配置失败", str(e))

    def save_preferences(self):
        """保存配置文件"""
        config = {
            'data_bits': int(self.data_bits_combo.currentText()),
            'stop_bits': self.stop_bits_combo.currentText(),
            'parity': self.parity_combo.currentText(),
            'font_size': int(self.font_size_input.text()) if self.font_size_input.text() else 10,
            'font_color': self.font_color_input.text() or VSCodeTheme.FOREGROUND
        }
        
        try:
            ConfigHandler.save_config(config)
            self.close()
        except Exception as e:
            QMessageBox.critical(self, "保存配置失败", str(e))
