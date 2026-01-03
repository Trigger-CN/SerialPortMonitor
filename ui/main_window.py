# main_window.py

import sys
from PyQt5.QtWidgets import (QMainWindow, QVBoxLayout, QHBoxLayout,
                             QLabel, QApplication, QWidget,
                             QStackedWidget, QProgressBar, QMessageBox, QDialog)
from PyQt5.QtCore import QTimer, QThread, pyqtSignal, QMutex
from PyQt5.QtGui import QFont
from ui.widgets import (StyledComboBox, CustomBaudrateComboBox, StyledButton, 
                       StyledTextEdit, StyledLineEdit, StyledCheckBox, 
                       StyledGroupBox, ComparisonTextDisplay, StyledLazyTextEdit)
from ui.long_text_widget import HugeTextWidget, ViewMode
from core.serial_manager import SerialManager
from core.port_scanner import PortScanner
from utils.data_processor import DataProcessor
from utils.data_cache import DataCacheManager
from styles.vs_code_theme import VSCodeTheme
from utils.file_handler import FileHandler
from utils.config_handler import ConfigHandler  # 导入ConfigHandler类
from PyQt5.QtWidgets import QFileDialog
from ui.preference_window import PreferenceWindow
from ui.highlight_config_window import HighlightConfigWindow
from ui.log_window import LogWindow
import version

class LazyDisplayUpdateWorker(QThread):
    """懒加载显示更新工作线程"""
    
    chunk_ready = pyqtSignal(int, object)  # 块索引, 内容
    progress_updated = pyqtSignal(int)  # 进度百分比
    finished = pyqtSignal()
    
    def __init__(self, data_cache, display_mode, hex_display, show_timestamp):
        super().__init__()
        self.data_cache = data_cache
        self.display_mode = display_mode
        self.hex_display = hex_display
        self.show_timestamp = show_timestamp
        self.data_processor = DataProcessor()
        self._is_running = True
        self.mutex = QMutex()

class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        self.serial_manager = SerialManager()
        self.port_scanner = PortScanner()
        self.data_processor = DataProcessor()
        self.data_cache = DataCacheManager(max_cache_size=500000)
        
        # 统计数据
        self.received_count = 0
        self.sent_count = 0
        
        # 显示模式
        self.display_mode = "normal"

        self.is_closing = False
        
        # 懒加载相关
        self.use_lazy_loading = True
        self.initial_chunks_loaded = False
        
        self.init_ui()
        self.init_connections()
        self.refresh_ports()
        # 初始化高亮规则
        self._current_highlight_rules = []
        # 多窗口管理
        self.log_windows = []  # 存储所有日志窗口
        self._window_counter = 0  # 窗口计数器
        # 加载配置
        self.load_config()
    
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle(version.get_app_title())
        # self.setGeometry(100, 100, 1400, 1100)
        self.resize(1400, 1100)
        
        # 设置窗口样式
        self.setStyleSheet(f"background-color: {VSCodeTheme.BACKGROUND}; color: {VSCodeTheme.FOREGROUND};")
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        layout = QHBoxLayout(central_widget)
        layout.setSpacing(10)  # 调整间距
        layout.setContentsMargins(10, 10, 10, 10)  # 调整边距
        
        # 操作布局
        option_layout = QVBoxLayout()
        option_layout.setSpacing(5)
        option_layout.setContentsMargins(5, 5, 5, 5)  # 收窄边距
        layout.addLayout(option_layout)
        
        # 创建各个UI组件
        self.create_serial_config_section(option_layout)
        # 添加文件保存路径设置
        self.create_log_path_section(option_layout)
        self.create_send_section(option_layout)
        self.create_data_display_section(layout)
        self.create_status_bar()
        self.create_prefs_button(option_layout)
        
        # 初始化定时器用于读取串口数据
        self.receive_timer = QTimer()
        self.receive_timer.timeout.connect(self.read_serial_data)
        # 初始化显示模式
        self.display_mode = "normal"  # 默认设置为普通模式
        self.display_normal.setChecked(True)
        self.display_hex.setChecked(False)
        self.display_stack.setCurrentIndex(0)
        self.prefs_window = PreferenceWindow(self)
    
    def create_prefs_button(self, layout):
        """创建首选项按钮"""
        self.prefs_btn = StyledButton("🔧 设置首选项")
        self.prefs_btn.clicked.connect(self.show_preference_window)
        layout.addWidget(self.prefs_btn)
    
    def show_preference_window(self):
        """显示首选项窗口"""
        self.prefs_window.load_config()
        self.prefs_window.show()
    
    def apply_log_preferences(self):
        """应用日志显示首选项设置"""
        font = self.prefs_window.font_combo.currentFont().family()
        font_size = self.prefs_window.spin_size.value() or 10
        font_color = self.prefs_window.text_color or VSCodeTheme.FOREGROUND
        font_bg_color = self.prefs_window.bg_color or VSCodeTheme.BACKGROUND
        encoding = self.prefs_window.encoding_combo.currentText().lower()

        self.normal_display.set_font_size(font_size)
        self.normal_display.set_font_family(font)
        self.normal_display.set_text_color(font_color)
        self.normal_display.set_bg_color(font_bg_color)
        self.normal_display.set_encoding(encoding)
        
        # 同步设置到所有日志窗口
        for log_window in self.log_windows:
            if log_window and log_window.isVisible():
                log_window.set_font_size(font_size)
                log_window.set_font_family(font)
                log_window.set_text_color(font_color)
                log_window.set_bg_color(font_bg_color)
                log_window.set_encoding(encoding)
    
    def open_highlight_config(self):
        """打开高亮配置窗口"""
        if not hasattr(self, 'highlight_config_window'):
            self.highlight_config_window = HighlightConfigWindow(self)
        
        # 加载当前的高亮规则
        current_rules = getattr(self, '_current_highlight_rules', [])
        self.highlight_config_window.set_rules(current_rules)
        
        # 显示窗口
        if self.highlight_config_window.exec_() == QDialog.Accepted:
            # 获取规则并应用
            rules = self.highlight_config_window.get_rules()
            self._current_highlight_rules = rules
            self.normal_display.set_highlight_rules(rules)
            # 同步高亮规则到所有日志窗口
            for log_window in self.log_windows:
                if log_window and log_window.isVisible():
                    log_window.set_highlight_rules(rules)
            # 保存配置到文件
            self.save_config()

    def create_log_path_section(self, layout):
        """创建日志路径设置区域"""
        log_path_group = StyledGroupBox("📜 日志路径")
        log_path_group.setFixedWidth(250)  # 设置固定宽度
        
        log_path_layout = QVBoxLayout()
        
        log_path_layout.addWidget(QLabel("路径:"))
        self.log_path_input = StyledLineEdit()
        self.log_path_input.setPlaceholderText("选择或输入日志文件保存路径")
        log_path_layout.addWidget(self.log_path_input)
        
        self.log_path_btn = StyledButton("浏览")
        self.log_path_btn.clicked.connect(self.browse_log_path)
        log_path_layout.addWidget(self.log_path_btn)
        
        log_path_group.setLayout(log_path_layout)
        layout.addWidget(log_path_group)

    def browse_log_path(self):
        """打开文件对话框选择日志保存路径"""
        log_path = FileHandler.get_log_path(self.log_path_input.text().strip())
        if log_path:
            self.log_path_input.setText(log_path)

    def create_serial_config_section(self, layout):
        """创建串口配置区域"""
        config_group = StyledGroupBox("串口配置")
        config_group.setFixedWidth(250)  # 设置固定宽度
        
        config_layout = QVBoxLayout()
        config_layout.setSpacing(10)
        
        # 串口选择
        self.com_label = QLabel("📡串口:")
        config_layout.addWidget(self.com_label)
        self.port_combo = StyledComboBox()
        config_layout.addWidget(self.port_combo)
        
        # 波特率选择
        self.baud_label = QLabel("⚡波特率:")
        config_layout.addWidget(self.baud_label)
        self.baud_combo = CustomBaudrateComboBox()
        config_layout.addWidget(self.baud_combo)
        
        # 刷新串口按钮
        self.refresh_btn = StyledButton("🔄刷新")
        config_layout.addWidget(self.refresh_btn)

        # 打开/关闭串口按钮
        self.connect_btn = StyledButton("🔌打开串口")
        config_layout.addWidget(self.connect_btn)

        config_layout.addStretch()
        config_layout.addWidget(QLabel("显示配置:"))
        # 时间戳显示
        self.timestamp = StyledButton("⏰显示时间戳")
        self.timestamp.setCheckable(True)
        self.timestamp.toggled.connect(self.on_timestamp_changed)
        config_layout.addWidget(self.timestamp)
        
        # 自动滚动
        self.auto_scroll = StyledButton("📜自动滚动")
        self.auto_scroll.setCheckable(True)
        self.auto_scroll.toggled.connect(self.on_auto_scroll_changed)
        config_layout.addWidget(self.auto_scroll)
        
        # 查找高亮按钮
        self.highlight_btn = StyledButton("🔍查找高亮")
        self.highlight_btn.clicked.connect(self.open_highlight_config)
        config_layout.addWidget(self.highlight_btn)
        
        # 清空按钮（合并了清空显示和清空缓存）
        self.clear_btn = StyledButton("🗑️清空")
        config_layout.addWidget(self.clear_btn)
        # 统计信息栏
        stats_layout = QVBoxLayout()
        self.stats_label = QLabel("📨 接收: 0 字节 | 📤 发送: 0 字节")
        self.stats_label.setStyleSheet(f"color: {VSCodeTheme.GREEN}; font-weight: bold;")
        stats_layout.addWidget(self.stats_label)
        
        # 缓存信息
        self.cache_label = QLabel("💾 缓存: 0 包, 0 字节")
        self.cache_label.setStyleSheet(f"color: {VSCodeTheme.BLUE}; font-weight: bold;")
        stats_layout.addWidget(self.cache_label)
        
        stats_layout.addStretch()
        
        # 显示模式选择
        mode_layout = QVBoxLayout()

        self.display_normal = StyledCheckBox("📄普通模式")
        self.display_normal.toggled.connect(lambda checked: self.on_display_mode_changed("normal"))
        mode_layout.addWidget(self.display_normal)
        
        self.display_hex = StyledCheckBox("🔢十六进制模式")
        self.display_hex.toggled.connect(lambda checked: self.on_display_mode_changed("hex"))
        mode_layout.addWidget(self.display_hex)
        
        mode_layout.addStretch()
        config_layout.addLayout(mode_layout)
        config_layout.addLayout(stats_layout)


        config_group.setLayout(config_layout)
        layout.addWidget(config_group)
    
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
        self.filter_input.setPlaceholderText("输入正则表达式（如: error|warning）")
        self.filter_input.textChanged.connect(self.on_filter_pattern_changed)
        filter_layout.addWidget(self.filter_input)
        
        self.filter_enable_btn = StyledButton("启用过滤")
        self.filter_enable_btn.setCheckable(True)
        self.filter_enable_btn.toggled.connect(self.on_filter_enabled_changed)
        filter_layout.addWidget(self.filter_enable_btn)
        
        # 添加"添加窗口"按钮
        self.add_window_btn = StyledButton("➕ 添加窗口")
        self.add_window_btn.clicked.connect(self.create_log_window)
        filter_layout.addWidget(self.add_window_btn)
        
        data_layout.addLayout(filter_layout)
        
        # 数据展示区域
        self.display_stack = QStackedWidget()
                # Replace normal_display
        self.normal_display = HugeTextWidget()
        self.normal_display.set_view_mode(ViewMode.TEXT_ONLY)
        
        # Add to the display stack
        self.display_stack.addWidget(self.normal_display)
        
        data_layout.addWidget(self.display_stack)
        
        data_group.setLayout(data_layout)
        layout.addWidget(data_group)
    
    def create_send_section(self, layout):
        """创建数据发送区域"""
        send_group = StyledGroupBox("📤发送数据")
        send_group.setFixedWidth(250)  # 设置固定宽度
        
        send_layout = QVBoxLayout()
        
        # 发送输入区域
        input_layout = QVBoxLayout()
        self.send_input = StyledLineEdit()
        self.send_input.setPlaceholderText("输入要发送的数据... (回车发送)")
        input_layout.addWidget(self.send_input)
        
        self.send_btn = StyledButton("🚀发送")
        input_layout.addWidget(self.send_btn)
        send_layout.addLayout(input_layout)
        
        # 选项区域
        option_layout = QHBoxLayout()
        
        self.hex_send = StyledCheckBox("🔢十六进制发送")
        option_layout.addWidget(self.hex_send)
        
        option_layout.addStretch()
        
        send_layout.addLayout(option_layout)
        send_group.setLayout(send_layout)
        layout.addWidget(send_group)
    
    def create_status_bar(self):
        """创建状态栏"""
        self.status_label = QLabel("✅就绪 - 选择串口并点击打开连接")
        self.status_label.setStyleSheet(f"color: {VSCodeTheme.GREEN};")
        self.statusBar().addWidget(self.status_label)
    
    def init_connections(self):
        """初始化信号连接"""
        # 按钮连接
        self.refresh_btn.clicked.connect(self.refresh_ports)
        self.connect_btn.clicked.connect(self.toggle_serial)
        self.send_btn.clicked.connect(self.send_data)
        self.send_input.returnPressed.connect(self.send_data)
        self.clear_btn.clicked.connect(self.clear_cache)
        
        # 波特率组合框信号连接
        self.baud_combo.custom_baudrate_selected.connect(self.on_baudrate_changed)
        
        # 数据缓存信号连接
        self.data_cache.cache_updated.connect(self.on_cache_updated)
        
        # 串口管理器信号连接
        self.serial_manager.data_received.connect(self.on_data_received)
        self.serial_manager.connection_changed.connect(self.on_connection_changed)
        self.serial_manager.error_occurred.connect(self.error_occurred)

    def load_config(self):
        """加载配置文件"""
        try:
            config = ConfigHandler.load_config()
            
            # 设置端口
            if 'port' in config:
                self.port_combo.setCurrentText(config['port'])
            
            # 设置波特率
            if 'baudrate' in config:
                self.baud_combo.setCurrentText(str(config['baudrate']))
            
            # 设置显示模式
            if 'display_mode' in config:
                self.display_mode = config['display_mode']
                if self.display_mode == "normal":
                    self.display_normal.setChecked(True)
                    self.display_hex.setChecked(False)
                    self.display_stack.setCurrentIndex(0)
                elif self.display_mode == "hex":
                    self.display_normal.setChecked(False)
                    self.display_hex.setChecked(True)
                    self.display_stack.setCurrentIndex(0)

            # 设置时间戳显示
            if 'timestamp' in config:
                self.timestamp.setChecked(config['timestamp'])
            
            # 设置自动滚动
            if 'auto_scroll' in config:
                self.auto_scroll.setChecked(config['auto_scroll'])
            
            # 设置日志路径
            if 'log_path' in config:
                self.log_path_input.setText(config['log_path'])
            
            # 设置数据位
            if 'data_bits' in config:
                self.prefs_window.data_bits_combo.setCurrentText(str(config['data_bits']))
            
            # 设置停止位
            if 'stop_bits' in config:
                self.prefs_window.stop_bits_combo.setCurrentText(config['stop_bits'])
            
            # 设置校验位
            if 'parity' in config:
                self.prefs_window.parity_combo.setCurrentText(config['parity'])
            
            if 'font' in config:
                self.prefs_window.set_font_str(config['font'])
            if 'font_size' in config:
                self.prefs_window.spin_size.setValue(config['font_size'])
            if 'font_color' in config:
                self.prefs_window.text_color = config['font_color']
            if 'bg_color' in config:
                self.prefs_window.bg_color = config['bg_color']
            if 'encoding' in config:
                encoding_text = config['encoding'].upper()
                if encoding_text in ["UTF-8", "GBK", "GB2312", "ASCII", "LATIN-1", "UTF-16", "UTF-32"]:
                    if encoding_text == "LATIN-1":
                        encoding_text = "Latin-1"
                    self.prefs_window.encoding_combo.setCurrentText(encoding_text)

            self.apply_log_preferences()
            
            # 加载高亮规则
            if 'highlight_rules' in config:
                highlight_rules = config['highlight_rules']
                self._current_highlight_rules = highlight_rules if highlight_rules else []
                self.normal_display.set_highlight_rules(self._current_highlight_rules)

        except Exception as e:
            self.status_label.setText(f"❌ 加载配置失败: {str(e)}")
            QMessageBox.critical(self, "加载配置失败", str(e))
    
    def save_config(self):
        """保存配置文件"""
        config = {
            'port': self.port_combo.currentText(),
            'baudrate': self.baud_combo.get_baudrate(),
            'display_mode': self.display_mode,
            'timestamp': self.timestamp.isChecked(),
            'auto_scroll': self.auto_scroll.isChecked(),
            'log_path': self.log_path_input.text().strip(),
            'data_bits': int(self.prefs_window.data_bits_combo.currentText()),
            'stop_bits': self.prefs_window.stop_bits_combo.currentText(),
            'parity': self.prefs_window.parity_combo.currentText(),
            'encoding': self.prefs_window.encoding_combo.currentText(),
            'font': self.prefs_window.font_combo.currentFont().family(),
            'font_size': int(self.prefs_window.spin_size.value()) if self.prefs_window.spin_size.value() else 10,
            'font_color': self.prefs_window.text_color or VSCodeTheme.FOREGROUND,
            'bg_color': self.prefs_window.bg_color or VSCodeTheme.BACKGROUND_LIGHT,
            'highlight_rules': getattr(self, '_current_highlight_rules', [])
        }
        
        try:
            ConfigHandler.save_config(config)
        except Exception as e:
            self.status_label.setText(f"❌ 保存配置失败: {str(e)}")
            QMessageBox.critical(self, "保存配置失败", str(e))
    
    def on_cache_updated(self):
        """缓存更新时的处理"""
        self.update_cache_info()
    
    def update_cache_info(self):
        """更新缓存信息显示"""
        packet_count, total_bytes = self.data_cache.get_cache_info()
        self.cache_label.setText(f"💾 缓存: {packet_count} 包, {total_bytes} 字节")
    
    def on_display_mode_changed(self, mode: str):
        """显示模式改变时的处理"""
        if self.is_closing:
            return
        
        # 断开信号连接
        self.display_normal.toggled.disconnect()
        self.display_hex.toggled.disconnect()
        
        # 设置显示模式和按钮状态
        if mode == "normal":
            self.display_normal.setChecked(True)
            self.display_hex.setChecked(False)
            self.display_mode = "normal"
            self.display_stack.setCurrentIndex(0)
            self.normal_display.set_view_mode(ViewMode.TEXT_ONLY)
        elif mode == "hex":
            self.display_hex.setChecked(True)
            self.display_normal.setChecked(False)
            self.display_mode = "hex"
            self.display_stack.setCurrentIndex(0)
            self.normal_display.set_view_mode(ViewMode.HEX_STREAM)
        
        # 重新连接信号
        self.display_normal.toggled.connect(lambda checked: self.on_display_mode_changed("normal"))
        self.display_hex.toggled.connect(lambda checked: self.on_display_mode_changed("hex"))

        self.status_label.setText(f"📊 显示模式: {self.get_display_mode_name(mode)}")

    def on_timestamp_changed(self, enabled: bool):
        """时间戳显示设置改变时的处理"""
        if self.timestamp.isChecked():
            self.timestamp.set_checked_style()
        else:
            self.timestamp.set_default_style()
        show_timestamp = self.timestamp.isChecked()
        self.normal_display.set_show_timestamp(show_timestamp)
        
        # 同步时间戳设置到所有日志窗口
        for log_window in self.log_windows:
            if log_window and log_window.isVisible():
                log_window.set_show_timestamp(show_timestamp)

    def on_auto_scroll_changed(self, enabled: bool):
        """自动滚动设置改变时的处理"""
        # 如果启用自动滚动，滚动到底部
        auto_scroll_enabled = self.auto_scroll.isChecked()
        if auto_scroll_enabled:
            self.auto_scroll.set_checked_style()
            self.normal_display.set_auto_scroll(True)
        else:
            self.auto_scroll.set_default_style()
            self.normal_display.set_auto_scroll(False)
        
        # 同步自动滚动设置到所有日志窗口
        for log_window in self.log_windows:
            if log_window and log_window.isVisible():
                log_window.set_auto_scroll(auto_scroll_enabled)
    
    def on_filter_pattern_changed(self, pattern_str):
        """过滤表达式改变时的处理"""
        import re
        # 验证正则表达式是否有效
        if pattern_str:
            try:
                re.compile(pattern_str)
                is_valid = True
            except re.error:
                is_valid = False
        else:
            is_valid = True
        
        self.normal_display.set_filter_pattern(pattern_str)
        if self.filter_enable_btn.isChecked():
            # 如果已启用过滤，更新状态栏提示
            if pattern_str:
                if is_valid:
                    self.status_label.setText(f"🔍 过滤模式: {pattern_str}")
                else:
                    self.status_label.setText(f"❌ 无效的正则表达式: {pattern_str}")
                    self.status_label.setStyleSheet(f"color: {VSCodeTheme.RED};")
            else:
                self.status_label.setText("🔍 过滤表达式为空")
                self.status_label.setStyleSheet(f"color: {VSCodeTheme.GREEN};")
    
    def on_filter_enabled_changed(self, enabled: bool):
        """过滤使能状态改变时的处理"""
        self.normal_display.set_filter_enabled(enabled)
        if enabled:
            self.filter_enable_btn.set_checked_style()
            self.filter_enable_btn.setText("禁用过滤")
            pattern = self.filter_input.text()
            if pattern:
                import re
                try:
                    re.compile(pattern)
                    self.status_label.setText(f"🔍 过滤已启用: {pattern}")
                    self.status_label.setStyleSheet(f"color: {VSCodeTheme.GREEN};")
                except re.error:
                    self.status_label.setText(f"❌ 无效的正则表达式: {pattern}")
                    self.status_label.setStyleSheet(f"color: {VSCodeTheme.RED};")
            else:
                self.status_label.setText("🔍 过滤已启用（表达式为空，显示所有行）")
                self.status_label.setStyleSheet(f"color: {VSCodeTheme.GREEN};")
        else:
            self.filter_enable_btn.set_default_style()
            self.filter_enable_btn.setText("启用过滤")
            self.status_label.setText("🔍 过滤已禁用")
            self.status_label.setStyleSheet(f"color: {VSCodeTheme.GREEN};")
    
    def scroll_to_bottom(self):
        """滚动到底部"""
        scrollbar = self.normal_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def get_display_mode_name(self, mode: str) -> str:
        """获取显示模式名称"""
        names = {
            "normal": "普通模式",
            "hex": "十六进制模式", 
        }
        return names.get(mode, "未知模式")
    
    def on_baudrate_changed(self, baudrate):
        """波特率改变时的处理"""
        self.status_label.setText(f"⚡ 波特率设置为: {baudrate} bps")
    
    def refresh_ports(self):
        """刷新可用串口列表"""
        self.port_combo.clear()
        ports = self.port_scanner.get_available_ports()
        
        for port_info in ports:
            display_name = self.port_scanner.get_port_display_name(port_info)
            self.port_combo.addItem(display_name, port_info['device'])
        
        if not ports:
            self.port_combo.addItem("未发现串口")
            self.status_label.setText("❌ 未发现串口设备")
        else:
            self.status_label.setText(f"🔍 发现 {len(ports)} 个串口设备")
    
    def toggle_serial(self):
        """打开或关闭串口连接"""
        if self.serial_manager.get_connection_status():
            self.disconnect_serial()
        else:
            self.connect_serial()
    
    def connect_serial(self):
        """连接串口"""
        port = self.port_combo.currentData()
        if not port:
            # 如果没有设置数据，尝试从显示文本中提取
            display_text = self.port_combo.currentText()
            if ' - ' in display_text:
                port = display_text.split(' - ')[0]
            else:
                port = display_text
        
        # 使用自定义波特率控件的方法获取波特率
        baudrate = self.baud_combo.get_baudrate()
        data_bits = self.prefs_window.data_bits_combo.currentText()
        stop_bits = self.prefs_window.stop_bits_combo.currentText()
        parity = self.prefs_window.parity_combo.currentText()

        if self.serial_manager.connect_serial(port, baudrate, data_bits, stop_bits, parity):
            self.receive_timer.start(1)
            self.apply_log_preferences()
    
    def disconnect_serial(self):
        """断开串口连接"""
        if self.serial_manager.get_connection_status():
            port_name = self.port_combo.currentData() or self.port_combo.currentText()
            log_data = self.normal_display.get_cached_data()
            
            try:
                log_path = self.log_path_input.text().strip()
                log_full_path = FileHandler.save_log(port_name, log_data, log_path)
                self.status_label.setText(f"📜 日志已保存为: {log_full_path}")
            except Exception as e:
                self.status_label.setText(f"❌ 保存日志失败: {str(e)}")
                QMessageBox.critical(self, "保存日志失败", str(e))
        
        self.serial_manager.disconnect_serial()
        self.receive_timer.stop()
    
    def read_serial_data(self):
        """读取串口数据"""
        try:
            data = self.serial_manager.read_data()
            if data:
                self.data_processor.process_received_data(data, 
                                                          False,
                                                          self.timestamp.isChecked())
        except Exception as e:
            self.error_occurred(e)
    
    def error_occurred(self, error_msg):
        """处理错误信息"""
        self.status_label.setText(f"❌ {error_msg}")
        self.status_label.setStyleSheet(f"color: {VSCodeTheme.RED};")
        QMessageBox.critical(self, "错误", error_msg)
        # 断开串口连接以防止重复错误提示
        self.disconnect_serial()
    
    def on_data_received(self, data):
        """处理接收到的数据"""
        self.received_count += len(data)
        self.update_stats()
        self.normal_display.append_raw_bytes(data)
        
        # 向所有日志窗口发送数据
        for log_window in self.log_windows:
            if log_window and log_window.isVisible():
                log_window.append_data(data)
        
        # # 如果启用了自动滚动，滚动到底部
        # if self.auto_scroll.isChecked():
        #     self.scroll_to_bottom()

    def send_data(self):
        """发送数据"""
        text = self.send_input.text()
        if not text:
            return
        
        try:
            data = self.data_processor.process_send_data(
                text, 
                self.hex_send.isChecked()
            )
            
            sent_len = self.serial_manager.send_data(data)
            if sent_len > 0:
                self.sent_count += sent_len
                self.update_stats()
                self.send_input.clear()
        
        except ValueError as e:
            self.status_label.setText(f"❌ 数据格式错误: {str(e)}")
            QMessageBox.warning(self, "格式错误", f"十六进制数据格式错误: {str(e)}")
    
    def update_stats(self):
        """更新统计信息"""
        self.stats_label.setText(f"📨 接收: {self.received_count} 字节 | 📤 发送: {self.sent_count} 字节")
    
    def clear_display(self):
        """清空显示区域（但不清空缓存）"""
        self.normal_display.clear()
    
    def clear_cache(self):
        """清空数据缓存"""
        self.data_cache.clear()
        self.clear_display()
        self.received_count = 0
        self.sent_count = 0
        self.update_stats()
        self.update_cache_info()
        self.status_label.setText("🗑️ 缓存已清空")
    
    def on_connection_changed(self, connected):
        """处理连接状态变化"""
        if connected:
            self.connect_btn.setText("🔌 关闭串口")
            self.connect_btn.set_danger_style()
            self.refresh_btn.setEnabled(False)
            self.port_combo.setEnabled(False)
            self.baud_combo.setEnabled(False)
            port_name = self.port_combo.currentData() or self.port_combo.currentText()
            baudrate = self.baud_combo.get_baudrate()
            self.status_label.setText(f"✅ 已连接 {port_name} @ {baudrate} bps")
        else:
            self.connect_btn.setText("🔌 打开串口")
            self.connect_btn.set_default_style()
            self.refresh_btn.setEnabled(True)
            self.port_combo.setEnabled(True)
            self.baud_combo.setEnabled(True)
            self.status_label.setText("🔌 已断开连接")
    
    def create_log_window(self):
        """创建新的日志窗口"""
        self._window_counter += 1
        log_window = LogWindow(self, window_id=self._window_counter)
        
        # 应用当前的首选项设置
        font = self.prefs_window.font_combo.currentFont().family()
        font_size = self.prefs_window.spin_size.value() or 10
        font_color = self.prefs_window.text_color or VSCodeTheme.FOREGROUND
        font_bg_color = self.prefs_window.bg_color or VSCodeTheme.BACKGROUND
        encoding = self.prefs_window.encoding_combo.currentText().lower()
        
        log_window.set_font_size(font_size)
        log_window.set_font_family(font)
        log_window.set_text_color(font_color)
        log_window.set_bg_color(font_bg_color)
        log_window.set_encoding(encoding)
        log_window.set_show_timestamp(self.timestamp.isChecked())
        log_window.set_auto_scroll(self.auto_scroll.isChecked())
        
        # 应用当前的高亮规则
        log_window.set_highlight_rules(self._current_highlight_rules)
        
        # 同步历史数据到新窗口（可选：如果希望新窗口也显示历史数据）
        # 注意：由于新窗口有自己的过滤，历史数据会经过过滤后才显示
        try:
            historical_data = self.normal_display.get_cached_data()
            if historical_data:
                # 将历史数据作为字节发送到新窗口
                historical_bytes = historical_data.encode(encoding, errors='replace')
                log_window.append_data(historical_bytes)
        except Exception as e:
            # 如果获取历史数据失败，不影响新窗口的创建
            pass
        
        # 连接窗口关闭信号
        log_window.window_closed.connect(self.on_log_window_closed)
        
        # 添加到窗口列表
        self.log_windows.append(log_window)
        
        # 显示窗口
        log_window.show()
        
        self.status_label.setText(f"✅ 已创建日志窗口 {self._window_counter}")
    
    def on_log_window_closed(self, log_window):
        """处理日志窗口关闭事件"""
        if log_window in self.log_windows:
            self.log_windows.remove(log_window)
        self.status_label.setText(f"📋 当前有 {len(self.log_windows)} 个日志窗口")
    
    def closeEvent(self, event):
        """关闭事件处理"""
        self.is_closing = True
        
        # 关闭所有日志窗口
        for log_window in self.log_windows[:]:  # 使用切片复制列表，避免迭代时修改
            log_window.close()
        self.log_windows.clear()
        
        # 断开串口连接
        self.disconnect_serial()
        
        # 保存配置
        self.save_config()
        
        event.accept()
