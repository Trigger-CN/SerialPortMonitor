# log_window.py

from PyQt5.QtWidgets import (QMainWindow, QVBoxLayout, QHBoxLayout,
                             QLabel, QWidget, QMessageBox)
from PyQt5.QtCore import pyqtSignal, Qt
from ui.widgets import StyledLineEdit, StyledButton, StyledGroupBox, StyledCheckBox
from ui.long_text_widget import HugeTextWidget, ViewMode
from styles.vs_code_theme import VSCodeTheme
import version

class LogWindow(QMainWindow):
    """独立的日志显示窗口"""
    
    # 信号：窗口关闭时发出
    window_closed = pyqtSignal(object)
    
    def __init__(self, parent=None, window_id=None):
        super().__init__(parent)
        self.window_id = window_id or id(self)
        self.init_ui()
        
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle(f"{version.get_app_title()} - 日志窗口 {self.window_id}")
        self.resize(1200, 800)
        
        # 设置窗口样式
        self.setStyleSheet(f"background-color: {VSCodeTheme.BACKGROUND}; color: {VSCodeTheme.FOREGROUND};")
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 创建数据显示区域（与主窗口相同的布局）
        self.create_data_display_section(layout)
        
    def create_data_display_section(self, layout):
        """创建数据显示区域"""
        data_group = StyledGroupBox("📊数据监视")
        data_layout = QVBoxLayout()
        
        # 添加过滤控件
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(5)
        
        filter_label = QLabel("🔍 过滤表达式:")
        filter_layout.addWidget(filter_label)
        
        self.filter_input = StyledLineEdit()
        self.filter_input.setPlaceholderText("输入过滤表达式（如: error|warning）")
        self.filter_input.textChanged.connect(self.on_filter_pattern_changed)
        filter_layout.addWidget(self.filter_input)
        
        self.filter_regex_checkbox = StyledCheckBox("正则")
        self.filter_regex_checkbox.setChecked(True)  # 默认启用正则表达式
        self.filter_regex_checkbox.toggled.connect(self.on_filter_regex_changed)
        filter_layout.addWidget(self.filter_regex_checkbox)
        
        self.filter_enable_btn = StyledButton("启用过滤")
        self.filter_enable_btn.setCheckable(True)
        self.filter_enable_btn.toggled.connect(self.on_filter_enabled_changed)
        filter_layout.addWidget(self.filter_enable_btn)
        
        data_layout.addLayout(filter_layout)
        
        # 数据展示区域
        self.normal_display = HugeTextWidget()
        self.normal_display.set_view_mode(ViewMode.TEXT_ONLY)
        data_layout.addWidget(self.normal_display)
        
        data_group.setLayout(data_layout)
        layout.addWidget(data_group)
    
    def on_filter_pattern_changed(self, pattern_str):
        """过滤表达式改变时的处理"""
        import re
        use_regex = self.filter_regex_checkbox.isChecked()
        
        # 验证正则表达式是否有效（仅在正则模式下）
        if pattern_str and use_regex:
            try:
                re.compile(pattern_str)
                is_valid = True
            except re.error:
                is_valid = False
        else:
            is_valid = True
        
        self.normal_display.set_filter_pattern(pattern_str)
        if self.filter_enable_btn.isChecked():
            # 如果已启用过滤，更新窗口标题提示
            if pattern_str:
                if use_regex:
                    if is_valid:
                        self.setWindowTitle(f"{version.get_app_title()} - 日志窗口 {self.window_id} [过滤（正则）: {pattern_str}]")
                    else:
                        self.setWindowTitle(f"{version.get_app_title()} - 日志窗口 {self.window_id} [无效表达式]")
                else:
                    self.setWindowTitle(f"{version.get_app_title()} - 日志窗口 {self.window_id} [过滤（文本）: {pattern_str}]")
            else:
                self.setWindowTitle(f"{version.get_app_title()} - 日志窗口 {self.window_id} [过滤: 空]")
    
    def on_filter_regex_changed(self, use_regex: bool):
        """正则表达式使能状态改变时的处理"""
        self.normal_display.set_filter_use_regex(use_regex)
        # 重新验证并更新窗口标题
        pattern_str = self.filter_input.text()
        self.on_filter_pattern_changed(pattern_str)
    
    def on_filter_enabled_changed(self, enabled: bool):
        """过滤使能状态改变时的处理"""
        self.normal_display.set_filter_enabled(enabled)
        if enabled:
            self.filter_enable_btn.set_checked_style()
            self.filter_enable_btn.setText("禁用过滤")
            pattern = self.filter_input.text()
            use_regex = self.filter_regex_checkbox.isChecked()
            if pattern:
                if use_regex:
                    import re
                    try:
                        re.compile(pattern)
                        self.setWindowTitle(f"{version.get_app_title()} - 日志窗口 {self.window_id} [过滤（正则）: {pattern}]")
                    except re.error:
                        self.setWindowTitle(f"{version.get_app_title()} - 日志窗口 {self.window_id} [无效表达式]")
                else:
                    self.setWindowTitle(f"{version.get_app_title()} - 日志窗口 {self.window_id} [过滤（文本）: {pattern}]")
            else:
                self.setWindowTitle(f"{version.get_app_title()} - 日志窗口 {self.window_id} [过滤: 空]")
        else:
            self.filter_enable_btn.set_default_style()
            self.filter_enable_btn.setText("启用过滤")
            self.setWindowTitle(f"{version.get_app_title()} - 日志窗口 {self.window_id}")
    
    def append_data(self, data: bytes):
        """追加数据到显示区域"""
        self.normal_display.append_raw_bytes(data)
    
    def set_highlight_rules(self, rules):
        """设置高亮规则"""
        self.normal_display.set_highlight_rules(rules)
    
    def set_highlight_enabled(self, enabled):
        """设置高亮使能状态"""
        self.normal_display.set_highlight_enabled(enabled)
    
    def set_show_timestamp(self, show: bool):
        """设置是否显示时间戳"""
        self.normal_display.set_show_timestamp(show)
    
    def set_auto_scroll(self, enabled: bool):
        """设置自动滚动"""
        self.normal_display.set_auto_scroll(enabled)
    
    def set_font_family(self, family: str):
        """设置字体"""
        self.normal_display.set_font_family(family)
    
    def set_font_size(self, size: int):
        """设置字体大小"""
        self.normal_display.set_font_size(size)
    
    def set_text_color(self, color):
        """设置文本颜色"""
        from PyQt5.QtGui import QColor
        self.normal_display.set_text_color(QColor(color))
    
    def set_bg_color(self, color):
        """设置背景颜色"""
        from PyQt5.QtGui import QColor
        self.normal_display.set_bg_color(QColor(color))
    
    def set_encoding(self, encoding: str):
        """设置编码"""
        self.normal_display.set_encoding(encoding)
    
    def set_max_lines(self, max_lines: int):
        """设置最大显示行数"""
        self.normal_display.set_max_lines(max_lines)
    
    def clear(self):
        """清空显示"""
        self.normal_display.clear()
    
    def closeEvent(self, event):
        """关闭事件处理"""
        self.window_closed.emit(self)
        event.accept()

