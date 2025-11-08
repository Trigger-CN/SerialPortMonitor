# main_window.py

import sys
from PyQt5.QtWidgets import (QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QLabel, QApplication, QWidget,
                             QStackedWidget, QProgressBar)
from PyQt5.QtCore import QTimer, QThread, pyqtSignal, QMutex
from ui.widgets import (StyledComboBox, CustomBaudrateComboBox, StyledButton, 
                       StyledTextEdit, StyledLineEdit, StyledCheckBox, 
                       StyledGroupBox, ComparisonTextDisplay, StyledLazyTextEdit)
from core.serial_manager import SerialManager
from core.port_scanner import PortScanner
from utils.data_processor import DataProcessor
from utils.data_cache import DataCacheManager
from styles.vs_code_theme import VSCodeTheme
from utils.file_handler import FileHandler
from utils.config_handler import ConfigHandler  # 导入ConfigHandler类
from PyQt5.QtWidgets import QFileDialog

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
    
    def stop(self):
        """停止线程"""
        self.mutex.lock()
        self._is_running = False
        self.mutex.unlock()
        self.quit()
        self.wait(1000)
    
    def run(self):
        """线程执行函数"""
        try:
            if not self._is_running:
                return
                
            if self.display_mode == "comparison":
                self.process_comparison_chunks()
            else:
                self.process_normal_chunks()
                    
        except Exception as e:
            print(f"懒加载线程错误: {e}")
        finally:
            self.finished.emit()
    
    def process_normal_chunks(self):
        """处理普通模式的懒加载块"""
        chunks = list(DataProcessor.get_lazy_display_chunks(
            self.data_cache, self.hex_display, self.show_timestamp
        ))
        
        total_chunks = len(chunks)
        for i, chunk in enumerate(chunks):
            if not self._is_running:
                return
                
            self.chunk_ready.emit(i, chunk)
            progress = int((i + 1) / total_chunks * 100) if total_chunks > 0 else 100
            self.progress_updated.emit(progress)
    
    def process_comparison_chunks(self):
        """处理对照模式的懒加载块"""
        chunks = list(DataProcessor.get_lazy_comparison_chunks(
            self.data_cache, self.show_timestamp
        ))
        
        total_chunks = len(chunks)
        for i, (text_chunk, hex_chunk) in enumerate(chunks):
            if not self._is_running:
                return
                
            self.chunk_ready.emit(i, (text_chunk, hex_chunk))
            progress = int((i + 1) / total_chunks * 100) if total_chunks > 0 else 100
            self.progress_updated.emit(progress)

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
        
        # 工作线程
        self.lazy_worker = None
        self.is_closing = False
        
        # 懒加载相关
        self.use_lazy_loading = True
        self.initial_chunks_loaded = False
        
        self.init_ui()
        self.init_connections()
        self.refresh_ports()
        
        # 加载配置
        self.load_config()
    
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("🔧 跨平台串口监看工具 - VSCode风格 + 懒加载")
        self.setGeometry(100, 100, 1000, 800)
        
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
        opetion_layout = QVBoxLayout()
        opetion_layout.setSpacing(10)
        opetion_layout.setContentsMargins(5, 5, 5, 5)  # 收窄边距
        layout.addLayout(opetion_layout)

        # 创建各个UI组件
        self.create_serial_config_section(opetion_layout)
        # 添加文件保存路径设置
        self.create_log_path_section(opetion_layout)
        self.create_send_section(opetion_layout)
        self.create_data_display_section(layout)
        self.create_status_bar()
        
        # 初始化定时器用于读取串口数据
        self.receive_timer = QTimer()
        self.receive_timer.timeout.connect(self.read_serial_data)

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
        config_layout.addWidget(QLabel("📡 串口:"))
        self.port_combo = StyledComboBox()
        config_layout.addWidget(self.port_combo)
        
        # 波特率选择
        config_layout.addWidget(QLabel("⚡ 波特率:"))
        self.baud_combo = CustomBaudrateComboBox()
        config_layout.addWidget(self.baud_combo)
        
        # 刷新串口按钮
        self.refresh_btn = StyledButton("🔄 刷新")
        config_layout.addWidget(self.refresh_btn)

        self.timestamp = StyledCheckBox("⏰ 显示时间戳")
        config_layout.addWidget(self.timestamp)
        
        self.auto_scroll = StyledCheckBox("📜 自动滚动")
        self.auto_scroll.setChecked(True)
        self.auto_scroll.toggled.connect(self.on_auto_scroll_changed)
        config_layout.addWidget(self.auto_scroll)

        # 打开/关闭串口按钮
        self.connect_btn = StyledButton("🔌 打开串口")
        config_layout.addWidget(self.connect_btn)
        
        self.clear_btn = StyledButton("🗑️ 清空显示")
        config_layout.addWidget(self.clear_btn)

        # 缓存控制按钮
        self.clear_cache_btn = StyledButton("🗑️ 清空缓存")
        config_layout.addWidget(self.clear_cache_btn)
        
        config_layout.addStretch()
        config_group.setLayout(config_layout)
        layout.addWidget(config_group)
    
    def create_data_display_section(self, layout):
        """创建数据显示区域"""
        data_group = StyledGroupBox("📊 数据监视")
        data_layout = QVBoxLayout()
        
        # 统计信息栏
        stats_layout = QHBoxLayout()
        self.stats_label = QLabel("📨 接收: 0 字节 | 📤 发送: 0 字节")
        self.stats_label.setStyleSheet(f"color: {VSCodeTheme.GREEN}; font-weight: bold;")
        stats_layout.addWidget(self.stats_label)
        
        # 缓存信息
        self.cache_label = QLabel("💾 缓存: 0 包, 0 字节")
        self.cache_label.setStyleSheet(f"color: {VSCodeTheme.BLUE}; font-weight: bold;")
        stats_layout.addWidget(self.cache_label)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximum(100)
        stats_layout.addWidget(self.progress_bar)
        
        stats_layout.addStretch()
        data_layout.addLayout(stats_layout)
        
        # 显示模式选择
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("显示模式:"))
        
        self.display_normal = StyledCheckBox("📄 普通模式")
        self.display_normal.setChecked(True)
        self.display_normal.toggled.connect(lambda: self.on_display_mode_changed("normal"))
        mode_layout.addWidget(self.display_normal)
        
        self.display_hex = StyledCheckBox("🔢 十六进制模式")
        self.display_hex.toggled.connect(lambda: self.on_display_mode_changed("hex"))
        mode_layout.addWidget(self.display_hex)
        
        self.display_comparison = StyledCheckBox("📊 对照模式")
        self.display_comparison.toggled.connect(lambda: self.on_display_mode_changed("comparison"))
        mode_layout.addWidget(self.display_comparison)
        
        # 懒加载选项
        self.lazy_loading_check = StyledCheckBox("🚀 懒加载模式")
        self.lazy_loading_check.setChecked(True)
        self.lazy_loading_check.setToolTip("启用懒加载以提高大数据量时的显示性能")
        mode_layout.addWidget(self.lazy_loading_check)
        
        mode_layout.addStretch()
        data_layout.addLayout(mode_layout)
        
        # 数据展示区域
        self.display_stack = QStackedWidget()
        
        # 普通/十六进制显示 - 使用懒加载文本框
        self.normal_display = StyledLazyTextEdit()
        self.normal_display.setPlaceholderText("串口数据将显示在这里...")
        self.normal_display.load_more_requested.connect(self.on_normal_load_more)
        
        # 对照显示
        self.comparison_display = ComparisonTextDisplay()
        self.comparison_display.connect_load_signals(
            self.on_comparison_load_more, self.on_comparison_load_more
        )
        
        # 添加到堆叠窗口
        self.display_stack.addWidget(self.normal_display)
        self.display_stack.addWidget(self.comparison_display)
        
        data_layout.addWidget(self.display_stack)
        
        data_group.setLayout(data_layout)
        layout.addWidget(data_group)
    
    def create_send_section(self, layout):
        """创建数据发送区域"""
        send_group = StyledGroupBox("📤 发送数据")
        send_group.setFixedWidth(250)  # 设置固定宽度
        
        send_layout = QVBoxLayout()
        
        # 发送输入区域
        input_layout = QVBoxLayout()
        self.send_input = StyledLineEdit()
        self.send_input.setPlaceholderText("输入要发送的数据... (回车发送)")
        input_layout.addWidget(self.send_input)
        
        self.send_btn = StyledButton("🚀 发送")
        input_layout.addWidget(self.send_btn)
        send_layout.addLayout(input_layout)
        
        # 选项区域
        option_layout = QHBoxLayout()
        
        self.hex_send = StyledCheckBox("🔢 十六进制发送")
        option_layout.addWidget(self.hex_send)
        
        option_layout.addStretch()
        

        
        send_layout.addLayout(option_layout)
        send_group.setLayout(send_layout)
        layout.addWidget(send_group)
    
    def create_status_bar(self):
        """创建状态栏"""
        self.status_label = QLabel("✅ 就绪 - 选择串口并点击打开连接")
        self.status_label.setStyleSheet(f"color: {VSCodeTheme.GREEN};")
        self.statusBar().addWidget(self.status_label)
    
    def init_connections(self):
        """初始化信号连接"""
        # 按钮连接
        self.refresh_btn.clicked.connect(self.refresh_ports)
        self.connect_btn.clicked.connect(self.toggle_serial)
        self.send_btn.clicked.connect(self.send_data)
        self.send_input.returnPressed.connect(self.send_data)
        self.clear_btn.clicked.connect(self.clear_display)
        self.clear_cache_btn.clicked.connect(self.clear_cache)
        
        # 波特率组合框信号连接
        self.baud_combo.custom_baudrate_selected.connect(self.on_baudrate_changed)
        
        # 数据缓存信号连接
        self.data_cache.cache_updated.connect(self.on_cache_updated)
        
        # 串口管理器信号连接
        self.serial_manager.data_received.connect(self.on_data_received)
        self.serial_manager.connection_changed.connect(self.on_connection_changed)
        self.serial_manager.error_occurred.connect(self.on_error_occurred)
    
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
                    self.display_comparison.setChecked(False)
                    self.display_stack.setCurrentIndex(0)
                elif self.display_mode == "hex":
                    self.display_normal.setChecked(False)
                    self.display_hex.setChecked(True)
                    self.display_comparison.setChecked(False)
                    self.display_stack.setCurrentIndex(0)
                elif self.display_mode == "comparison":
                    self.display_normal.setChecked(False)
                    self.display_hex.setChecked(False)
                    self.display_comparison.setChecked(True)
                    self.display_stack.setCurrentIndex(1)
            
            # 设置懒加载模式
            if 'lazy_loading' in config:
                self.lazy_loading_check.setChecked(config['lazy_loading'])
            
            # 设置时间戳显示
            if 'timestamp' in config:
                self.timestamp.setChecked(config['timestamp'])
            
            # 设置自动滚动
            if 'auto_scroll' in config:
                self.auto_scroll.setChecked(config['auto_scroll'])
            
            # 设置日志路径
            if 'log_path' in config:
                self.log_path_input.setText(config['log_path'])
        
        except Exception as e:
            self.status_label.setText(f"❌ 加载配置失败: {str(e)}")
            QMessageBox.critical(self, "加载配置失败", str(e))
    
    def save_config(self):
        """保存配置文件"""
        config = {
            'port': self.port_combo.currentText(),
            'baudrate': self.baud_combo.get_baudrate(),
            'display_mode': self.display_mode,
            'lazy_loading': self.lazy_loading_check.isChecked(),
            'timestamp': self.timestamp.isChecked(),
            'auto_scroll': self.auto_scroll.isChecked(),
            'log_path': self.log_path_input.text().strip()
        }
        
        try:
            ConfigHandler.save_config(config)
        except Exception as e:
            self.status_label.setText(f"❌ 保存配置失败: {str(e)}")
            QMessageBox.critical(self, "保存配置失败", str(e))
    
    def on_normal_load_more(self, chunk_index: int):
        """普通模式懒加载请求"""
        if self.lazy_worker and self.lazy_worker.isRunning():
            return
        
        self.start_lazy_loading(chunk_index)
    
    def on_comparison_load_more(self, chunk_index: int):
        """对照模式懒加载请求"""
        if self.lazy_worker and self.lazy_worker.isRunning():
            return
        
        self.start_lazy_loading(chunk_index)
    
    def start_lazy_loading(self, start_chunk: int = 0):
        """启动懒加载"""
        if self.is_closing:
            return
        
        # 停止现有工作线程
        if self.lazy_worker and self.lazy_worker.isRunning():
            self.lazy_worker.stop()
        
        packet_count, total_bytes = self.data_cache.get_cache_info()
        
        # 小数据量直接加载，不启用懒加载
        if total_bytes < 50000 and not self.initial_chunks_loaded:
            self.refresh_display_direct()
            return
        
        self.use_lazy_loading = self.lazy_loading_check.isChecked()
        
        if not self.use_lazy_loading:
            self.refresh_display_direct()
            return
        
        # 显示进度条
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # 创建并启动懒加载工作线程
        self.lazy_worker = LazyDisplayUpdateWorker(
            self.data_cache,
            self.display_mode,
            self.display_mode == "hex",
            self.timestamp.isChecked()
        )
        self.lazy_worker.chunk_ready.connect(self.on_chunk_ready)
        self.lazy_worker.progress_updated.connect(self.progress_bar.setValue)
        self.lazy_worker.finished.connect(self.on_lazy_loading_finished)
        self.lazy_worker.start()
        
        self.status_label.setText("🚀 懒加载中...")
        self.initial_chunks_loaded = True
    
    def on_chunk_ready(self, chunk_index: int, content):
        """块数据准备就绪"""
        if self.is_closing:
            return
        
        if self.display_mode == "comparison":
            if isinstance(content, tuple) and len(content) == 2:
                text_content, hex_content = content
                self.comparison_display.append_chunk(text_content, hex_content, chunk_index)
        else:
            if isinstance(content, str):
                self.normal_display.append_chunk(chunk_index, content)
    
    def on_lazy_loading_finished(self):
        """懒加载完成"""
        if self.is_closing:
            return
        
        self.progress_bar.setVisible(False)
        self.status_label.setText("✅ 懒加载完成")
        
        if self.auto_scroll.isChecked():
            self.scroll_to_bottom()
    
    def refresh_display_direct(self):
        """直接刷新显示（用于小数据量）"""
        if self.display_mode == "comparison":
            self.refresh_comparison_display()
        else:
            self.refresh_normal_display()
    
    def refresh_normal_display(self):
        """刷新普通显示模式的内容"""
        display_text = self.data_processor.process_cached_data_for_normal(
            self.data_cache,
            self.display_mode == "hex",
            self.timestamp.isChecked()
        )
        
        self.normal_display.setPlainText(display_text)
        
        if self.auto_scroll.isChecked():
            self.scroll_to_bottom()
    
    def refresh_comparison_display(self):
        """刷新对照显示模式的内容"""
        text_display, hex_display = self.data_processor.process_cached_data_for_comparison(
            self.data_cache,
            self.timestamp.isChecked()
        )
        
        self.comparison_display.clear()
        self.comparison_display.append_text(text_display, hex_display)
        
        if self.auto_scroll.isChecked():
            self.scroll_to_bottom()
    
    def on_cache_updated(self):
        """缓存更新时的处理"""
        self.update_cache_info()
    
    def update_cache_info(self):
        """更新缓存信息显示"""
        packet_count, total_bytes = self.data_cache.get_cache_info()
        self.cache_label.setText(f"💾 缓存: {packet_count} 包, {total_bytes} 字节")
    
    def refresh_display(self):
        """刷新当前显示模式的内容"""
        if self.is_closing:
            return
            
        packet_count, total_bytes = self.data_cache.get_cache_info()
        
        # 清空显示
        if self.display_mode == "comparison":
            self.comparison_display.clear()
        else:
            self.normal_display.clear()
        
        # 小数据量直接加载
        if total_bytes < 50000:
            self.refresh_display_direct()
        else:
            # 大数据量使用懒加载
            self.start_lazy_loading()
    
    def on_display_mode_changed(self, mode: str):
        """显示模式改变时的处理"""
        if self.is_closing:
            return
            
        # 确保只有一个模式被选中
        if mode == "normal":
            self.display_hex.setChecked(False)
            self.display_comparison.setChecked(False)
            self.display_mode = "normal"
            self.display_stack.setCurrentIndex(0)
        elif mode == "hex":
            self.display_normal.setChecked(False)
            self.display_comparison.setChecked(False)
            self.display_mode = "hex"
            self.display_stack.setCurrentIndex(0)
        elif mode == "comparison":
            self.display_normal.setChecked(False)
            self.display_hex.setChecked(False)
            self.display_mode = "comparison"
            self.display_stack.setCurrentIndex(1)
        
        # 重置懒加载状态
        self.initial_chunks_loaded = False
        
        # 刷新显示
        self.refresh_display()
        
        self.status_label.setText(f"📊 显示模式: {self.get_display_mode_name(mode)}")
    
    def on_auto_scroll_changed(self, enabled: bool):
        """自动滚动设置改变时的处理"""
        # 如果启用自动滚动，滚动到底部
        if enabled:
            self.scroll_to_bottom()
    
    def scroll_to_bottom(self):
        """滚动到底部"""
        if self.display_mode == "comparison":
            self.comparison_display.scroll_to_bottom()
        else:
            scrollbar = self.normal_display.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
    
    def get_display_mode_name(self, mode: str) -> str:
        """获取显示模式名称"""
        names = {
            "normal": "普通模式",
            "hex": "十六进制模式", 
            "comparison": "文本/十六进制对照模式"
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
        
        if self.serial_manager.connect_serial(port, baudrate):
            self.receive_timer.start(10)
    
    def disconnect_serial(self):
        """断开串口连接"""
        if self.serial_manager.get_connection_status():
            port_name = self.port_combo.currentData() or self.port_combo.currentText()
            if self.display_mode == "comparison":
                text_display, hex_display = self.data_processor.process_cached_data_for_comparison(
                    self.data_cache,
                    self.timestamp.isChecked()
                )
                log_data = f"{text_display}    {hex_display}"
            else:
                log_data = self.data_processor.process_cached_data_for_normal(
                    self.data_cache,
                    self.display_mode == "hex",
                    self.timestamp.isChecked()
                )
            
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
        self.serial_manager.read_data()
    
    def on_data_received(self, data):
        """处理接收到的数据"""
        self.received_count += len(data)
        self.update_stats()
        
        # 添加数据到缓存
        self.data_cache.add_data(data)
        
        # 根据当前显示模式实时更新显示（只更新新数据，不重新处理整个缓存）
        if self.display_mode == "comparison":
            self.append_comparison_data(data)
        else:
            self.append_normal_data(data)
        
        # 如果启用了自动滚动，滚动到底部
        if self.auto_scroll.isChecked():
            self.scroll_to_bottom()
    
    def append_normal_data(self, data):
        """追加数据到普通显示模式（实时更新，不处理整个缓存）"""
        processed_data = self.data_processor.process_received_data(
            data, 
            self.display_mode == "hex",
            self.timestamp.isChecked()
        )
        
        cursor = self.normal_display.textCursor()
        cursor.movePosition(cursor.End)
        cursor.insertText(processed_data)
    
    def append_comparison_data(self, data):
        """追加数据到对照显示模式（实时更新，不处理整个缓存）"""
        # 分割数据为文本和十六进制行
        text_lines, hex_lines = self.data_processor.split_data_for_comparison(data)
        
        # 格式化显示内容
        text_display, hex_display = self.data_processor.format_comparison_display(
            text_lines, hex_lines, self.timestamp.isChecked()
        )
        
        # 追加到对照显示控件
        self.comparison_display.append_text(text_display, hex_display)
    
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
        if self.display_mode == "comparison":
            self.comparison_display.clear()
        else:
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
    
    def on_error_occurred(self, error_msg):
        """处理错误信息"""
        self.status_label.setText(f"❌ {error_msg}")
        self.status_label.setStyleSheet(f"color: {VSCodeTheme.RED};")
        QMessageBox.critical(self, "错误", error_msg)
    
    def closeEvent(self, event):
        """关闭事件处理"""
        self.is_closing = True
        
        # 停止工作线程
        if self.lazy_worker and self.lazy_worker.isRunning():
            self.lazy_worker.stop()
        
        # 断开串口连接
        self.disconnect_serial()
        
        # 保存配置
        self.save_config()
        
        event.accept()
