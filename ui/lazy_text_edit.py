from PyQt5.QtWidgets import QTextEdit, QScrollBar
from PyQt5.QtCore import QTimer, pyqtSignal
from PyQt5.QtGui import QTextCursor
from styles.vs_code_theme import VSCodeTheme

class LazyTextEdit(QTextEdit):
    """支持懒加载的文本框"""
    
    # 信号：当需要加载更多内容时发出
    load_more_requested = pyqtSignal(int)  # 请求加载第几块
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.loaded_chunks = set()  # 已加载的块索引
        self.total_chunks = 0  # 总块数
        self.chunk_size = 10000  # 每个块的字符数
        self.is_loading = False
        
        # 设置样式
        self.setStyleSheet(f"""
            QTextEdit {{
                background-color: {VSCodeTheme.BACKGROUND};
                color: {VSCodeTheme.FOREGROUND};
                border: 1px solid {VSCodeTheme.BACKGROUND_LIGHTER};
                border-radius: 3px;
                padding: 8px;
                selection-background-color: {VSCodeTheme.ACCENT};
            }}
        """)
        
        # 监控滚动事件
        self.verticalScrollBar().valueChanged.connect(self.on_scroll)
        
        # 延迟加载定时器
        self.load_timer = QTimer()
        self.load_timer.setSingleShot(True)
        self.load_timer.timeout.connect(self.process_pending_loads)
        
        self.pending_loads = set()
    
    def set_total_chunks(self, total_chunks: int):
        """设置总块数"""
        self.total_chunks = total_chunks
        self.loaded_chunks.clear()
    
    def append_chunk(self, chunk_index: int, content: str):
        """追加一个内容块"""
        if chunk_index in self.loaded_chunks:
            return
            
        self.loaded_chunks.add(chunk_index)
        
        # 保存当前滚动位置
        scrollbar = self.verticalScrollBar()
        old_value = scrollbar.value()
        old_max = scrollbar.maximum()
        
        # 追加内容
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)
        
        if chunk_index > 0 and cursor.position() > 0:
            cursor.insertText("\n")
        
        cursor.insertText(content)
        
        # 恢复滚动位置
        if old_max > 0:
            # 计算新的滚动位置（保持相对位置）
            new_max = scrollbar.maximum()
            if new_max > 0:
                ratio = old_value / old_max if old_max > 0 else 0
                scrollbar.setValue(int(ratio * new_max))
    
    def on_scroll(self, value):
        """滚动事件处理"""
        scrollbar = self.verticalScrollBar()
        max_value = scrollbar.maximum()
        
        # 如果滚动到底部附近，加载更多内容
        if value >= max_value * 0.8:  # 距离底部20%时开始加载
            self.schedule_load_more()
    
    def schedule_load_more(self):
        """调度加载更多内容"""
        # 找到第一个未加载的块
        for i in range(self.total_chunks):
            if i not in self.loaded_chunks and i not in self.pending_loads:
                self.pending_loads.add(i)
                break
        
        # 启动延迟加载定时器（避免频繁加载）
        if not self.load_timer.isActive():
            self.load_timer.start(10)  # 100ms后处理
    
    def process_pending_loads(self):
        """处理待加载的块"""
        for chunk_index in sorted(self.pending_loads):
            self.load_more_requested.emit(chunk_index)
        
        self.pending_loads.clear()
    
    def clear(self):
        """清空内容"""
        super().clear()
        self.loaded_chunks.clear()
        self.total_chunks = 0
        self.pending_loads.clear()
        if self.load_timer.isActive():
            self.load_timer.stop()