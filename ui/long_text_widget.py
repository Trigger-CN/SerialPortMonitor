import sys
import math
from enum import Enum
from PyQt5.QtWidgets import (QApplication, QMainWindow, QAbstractScrollArea, 
                             QVBoxLayout, QWidget, QPushButton, QHBoxLayout, 
                             QComboBox, QScrollBar, QCheckBox, QMessageBox)
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import (QPainter, QFont, QColor, QFontMetrics, QKeySequence, 
                         QClipboard, QGuiApplication)

class ViewMode(Enum):
    TEXT_ONLY = 0      # 纯文本模式
    HEX_STREAM = 1     # Hex 流模式 (32字节/行)

class HugeTextWidget(QAbstractScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # --- 核心配置 ---
        self._bytes_per_line = 32 # Hex模式每行显示字节数
        self._encoding = 'utf-8'
        
        # --- 数据存储 ---
        self._lines = []        # 文本行缓存
        self._raw_bytes = b""   # 原始字节数据
        self._line_styles = {}  
        
        self._view_mode = ViewMode.TEXT_ONLY
        
        # --- 选择功能状态 ---
        self._sel_start_pos = None # (row, col)
        self._sel_end_pos = None   # (row, col)
        self._is_selecting = False
        
        # --- 自动滚动 ---
        self._auto_scroll = True 
        
        # --- 样式 ---
        self._font = QFont("Consolas", 10)
        self._font_metrics = QFontMetrics(self._font)
        self._update_metrics()
        
        self._colors = {
            'bg': QColor("#1E1E1E"),
            'text': QColor("#D4D4D4"),
            'line_num_bg': QColor("#252526"),
            'line_num_text': QColor("#858585"),
            'highlight': QColor("#264F78"),
            'selection': QColor("#204060"),
            'hex_text': QColor("#569CD6"),
            'offset_text': QColor("#2B91AF"),
        }
        
        self._line_num_area_width = 60
        self._current_line_index = -1 
        
        # 初始化设置
        self.setFont(self._font)
        self.viewport().setStyleSheet(f"background-color: {self._colors['bg'].name()};")
        self.setFocusPolicy(Qt.StrongFocus) # 允许键盘焦点 (Ctrl+C)
        self.setMouseTracking(True)         # 允许鼠标追踪 (拖拽选择)

        self.verticalScrollBar().valueChanged.connect(self.viewport().update)
        self.horizontalScrollBar().valueChanged.connect(self.viewport().update)

    def _update_metrics(self):
        self._line_height = self._font_metrics.lineSpacing()
        self._char_width = self._font_metrics.width('A')

    # ===========================
    # 交互事件: 鼠标选择 & 键盘复制
    # ===========================
    def mousePressEvent(self, event):
        if self._view_mode == ViewMode.TEXT_ONLY and event.button() == Qt.LeftButton:
            pos = self._map_point_to_pos(event.pos())
            self._sel_start_pos = pos
            self._sel_end_pos = pos
            self._is_selecting = True
            self.viewport().update()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._is_selecting and self._view_mode == ViewMode.TEXT_ONLY:
            pos = self._map_point_to_pos(event.pos())
            self._sel_end_pos = pos
            self.viewport().update()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._is_selecting = False
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        if event.matches(QKeySequence.Copy):
            self.copy_selection()
        else:
            super().keyPressEvent(event)

    def _map_point_to_pos(self, point: QPoint):
        """(像素 -> 行列) 映射，仅用于文本模式"""
        y = point.y()
        x = point.x() + self.horizontalScrollBar().value()
        
        row = self.verticalScrollBar().value() + (y // self._line_height)
        row = max(0, min(row, len(self._lines) - 1))
        
        rel_x = x - self._line_num_area_width
        if rel_x < 0: rel_x = 0
        col = round(rel_x / self._char_width)
        
        if 0 <= row < len(self._lines):
            line_len = len(self._lines[row])
            col = min(col, line_len)
        return (row, col)

    def _get_normalized_selection(self):
        if not self._sel_start_pos or not self._sel_end_pos: return None, None
        r1, c1 = self._sel_start_pos
        r2, c2 = self._sel_end_pos
        if r1 < r2: return (r1, c1), (r2, c2)
        elif r1 > r2: return (r2, c2), (r1, c1)
        else: return (r1, min(c1, c2)), (r1, max(c1, c2))

    def copy_selection(self):
        """复制逻辑"""
        if self._view_mode == ViewMode.HEX_STREAM:
            # Hex模式暂未实现精细选择，简单提示或复制全部可视区域（此处略，保持简单）
            return 

        start, end = self._get_normalized_selection()
        if start is None or start == end: return

        r1, c1 = start
        r2, c2 = end
        copied_text = []
        
        for r in range(r1, r2 + 1):
            if r >= len(self._lines): break
            line = self._lines[r]
            s_idx = c1 if r == r1 else 0
            e_idx = c2 if r == r2 else len(line)
            copied_text.append(line[s_idx:e_idx])
            
        QGuiApplication.clipboard().setText("\n".join(copied_text))

    # ===========================
    # 渲染逻辑 (Paint)
    # ===========================
    def paintEvent(self, event):
        painter = QPainter(self.viewport())
        painter.setFont(self._font)
        
        # 处理水平滚动偏移
        x_offset = -self.horizontalScrollBar().value()
        painter.translate(x_offset, 0)
        
        if self._view_mode == ViewMode.HEX_STREAM:
            self._paint_hex_stream(painter, x_offset)
        else:
            self._paint_text_mode(painter, x_offset)

    def _paint_text_mode(self, painter, x_offset):
        """纯文本模式渲染 (支持高亮和选择)"""
        viewport_h = self.viewport().height()
        viewport_w = self.viewport().width() + abs(x_offset)
        
        first_row = self.verticalScrollBar().value()
        rows_visible = math.ceil(viewport_h / self._line_height) + 1
        last_row = min(first_row + rows_visible, len(self._lines))
        
        # 1. 绘制左侧固定背景 (行号区)
        painter.translate(-x_offset, 0) 
        painter.fillRect(0, 0, self._line_num_area_width, viewport_h, self._colors['line_num_bg'])
        painter.translate(x_offset, 0) 
        
        sel_start, sel_end = self._get_normalized_selection()

        for row in range(first_row, last_row):
            line_text = self._lines[row]
            draw_y = (row - first_row) * self._line_height
            
            # A. 当前行高亮
            if row == self._current_line_index:
                painter.fillRect(self._line_num_area_width, draw_y, 
                                 viewport_w, self._line_height, self._colors['highlight'])
            
            # B. 选中区域背景
            if sel_start and sel_end:
                if sel_start[0] <= row <= sel_end[0]:
                    s_char = sel_start[1] if row == sel_start[0] else 0
                    e_char = sel_end[1] if row == sel_end[0] else len(line_text) + 1
                    if e_char > s_char:
                        sel_x = self._line_num_area_width + 5 + (s_char * self._char_width)
                        sel_w = (e_char - s_char) * self._char_width
                        painter.fillRect(sel_x, draw_y, sel_w, self._line_height, self._colors['selection'])

            # C. 绘制行号 (固定位置)
            painter.translate(-x_offset, 0)
            painter.setPen(self._colors['line_num_text'])
            painter.drawText(0, draw_y, self._line_num_area_width - 5, self._line_height, 
                             Qt.AlignRight | Qt.AlignVCenter, str(row + 1))
            painter.translate(x_offset, 0)
            
            # D. 绘制文本
            painter.setPen(self._colors['text'])
            painter.drawText(self._line_num_area_width + 5, draw_y, 
                             viewport_w, self._line_height, 
                             Qt.AlignLeft | Qt.AlignVCenter, line_text)

    def _paint_hex_stream(self, painter, x_offset):
        """Hex流模式渲染 (32字节/行)"""
        viewport_h = self.viewport().height()
        
        first_row_idx = self.verticalScrollBar().value()
        rows_visible = math.ceil(viewport_h / self._line_height) + 1
        
        total_bytes = len(self._raw_bytes)
        max_rows = math.ceil(total_bytes / self._bytes_per_line)
        last_row_idx = min(first_row_idx + rows_visible, max_rows)
        
        # 布局计算
        w_char = self._char_width
        x_addr_end = self._line_num_area_width + (10 * w_char)
        x_hex_start = x_addr_end + (2 * w_char)
        x_hex_end = x_hex_start + (self._bytes_per_line * 3 * w_char)
        x_ascii_start = x_hex_end + (3 * w_char)
        
        # 背景
        painter.translate(-x_offset, 0)
        painter.fillRect(0, 0, x_addr_end, viewport_h, self._colors['line_num_bg'])
        painter.translate(x_offset, 0)

        for i in range(first_row_idx, last_row_idx):
            draw_y = (i - first_row_idx) * self._line_height
            start_byte = i * self._bytes_per_line
            end_byte = min(start_byte + self._bytes_per_line, total_bytes)
            
            chunk = self._raw_bytes[start_byte:end_byte]
            
            # 1. 地址
            painter.translate(-x_offset, 0)
            painter.setPen(self._colors['offset_text'])
            painter.drawText(0, draw_y, x_addr_end - 5, self._line_height, 
                             Qt.AlignRight | Qt.AlignVCenter, f"{start_byte:08X}")
            painter.translate(x_offset, 0)
            
            # 2. Hex
            hex_parts = [f"{b:02X}" for b in chunk]
            painter.setPen(self._colors['hex_text'])
            painter.drawText(x_hex_start, draw_y, x_hex_end, self._line_height,
                             Qt.AlignLeft | Qt.AlignVCenter, " ".join(hex_parts))
            
            # 3. ASCII
            ascii_parts = [chr(b) if 32 <= b <= 126 else "." for b in chunk]
            painter.setPen(self._colors['text'])
            painter.drawText(x_ascii_start, draw_y, 10000, self._line_height,
                             Qt.AlignLeft | Qt.AlignVCenter, "".join(ascii_parts))

    # ===========================
    # 滚动条与 API
    # ===========================
    def resizeEvent(self, event):
        self._update_scrollbars()
        super().resizeEvent(event)

    def _update_scrollbars(self):
        viewport_h = self.viewport().height()
        rows_per_page = viewport_h // self._line_height
        
        if self._view_mode == ViewMode.HEX_STREAM:
            total_rows = math.ceil(len(self._raw_bytes) / self._bytes_per_line)
            # Hex模式内容通常很宽，需要计算
            chars = 12 + (self._bytes_per_line * 3) + 3 + self._bytes_per_line
            content_width = chars * self._char_width + self._line_num_area_width
        else:
            total_rows = len(self._lines)
            # 文本模式默认不强制开启水平滚动，除非为了支持极长行
            # 这里设为 viewport_w 表示不需要横滚，或者你可以设为最长行的宽度
            content_width = self.viewport().width()
            
        v_max = max(0, total_rows - rows_per_page)
        self.verticalScrollBar().setRange(0, v_max)
        self.verticalScrollBar().setPageStep(rows_per_page)
        
        h_max = max(0, content_width - self.viewport().width())
        self.horizontalScrollBar().setRange(0, int(h_max))
        self.horizontalScrollBar().setPageStep(self.viewport().width())

    def set_view_mode(self, mode: ViewMode):
        self._view_mode = mode
        self._sel_start_pos = None # 切换模式清空选择
        self._sel_end_pos = None
        self.verticalScrollBar().setValue(0)
        self.horizontalScrollBar().setValue(0)
        self._update_scrollbars()
        self.viewport().update()

    def set_auto_scroll(self, enabled: bool):
        self._auto_scroll = enabled
        if enabled: self.scroll_to_bottom()

    def scroll_to_bottom(self):
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())

    def append_raw_bytes(self, data: bytes):
        if not data: return
        
        # 智能滚动判断
        scrollbar = self.verticalScrollBar()
        was_at_bottom = scrollbar.value() >= (scrollbar.maximum() - 1)
        
        # 数据处理
        is_new_line_start = True
        if len(self._raw_bytes) > 0 and self._raw_bytes[-1] != 10:
            is_new_line_start = False
        
        self._raw_bytes += data
        try: new_text = data.decode(self._encoding, errors='replace')
        except: new_text = ""
        
        new_lines = new_text.splitlines()
        
        if not is_new_line_start and self._lines:
            if new_lines:
                self._lines[-1] += new_lines[0]
                if len(new_lines) > 1: self._lines.extend(new_lines[1:])
            else:
                if new_text and not (new_text.endswith('\n') or new_text.endswith('\r')):
                     self._lines[-1] += new_text
        else:
            if new_lines: self._lines.extend(new_lines)
            elif new_text and not (new_text.endswith('\n') or new_text.endswith('\r')):
                 self._lines.append(new_text)

        self._update_scrollbars()
        
        if self._auto_scroll or was_at_bottom:
            self.scroll_to_bottom()
        self.viewport().update()
        
    def clear(self):
        self._lines = []
        self._raw_bytes = b""
        self._sel_start_pos = None
        self._sel_end_pos = None
        self._update_scrollbars()
        self.viewport().update()
        
    def set_content(self, text: str):
        self._lines = text.splitlines()
        self._raw_bytes = text.encode(self._encoding, errors='replace')
        self._update_scrollbars()
        self.viewport().update()

# ===========================
# Demo 验证
# ===========================
class DemoWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("高性能文本控件 Demo")
        self.resize(1200, 700)
        
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # --- 控制栏 ---
        top_layout = QHBoxLayout()
        
        self.check_auto_scroll = QCheckBox("自动滚动")
        self.check_auto_scroll.setChecked(True)
        self.check_auto_scroll.stateChanged.connect(lambda s: self.text_viewer.set_auto_scroll(s == Qt.Checked))
        
        self.combo_mode = QComboBox()
        self.combo_mode.addItems(["纯文本模式 (Text)", "Hex流模式 (Hex)"])
        self.combo_mode.currentIndexChanged.connect(lambda i: self.text_viewer.set_view_mode(ViewMode(i)))
        
        self.btn_add = QPushButton("追加测试数据")
        self.btn_add.clicked.connect(self.add_test_data)
        
        self.btn_clear = QPushButton("清空")
        self.btn_clear.clicked.connect(lambda: self.text_viewer.clear())
        
        top_layout.addWidget(self.check_auto_scroll)
        top_layout.addWidget(self.combo_mode)
        top_layout.addWidget(self.btn_add)
        top_layout.addWidget(self.btn_clear)
        top_layout.addStretch()
        
        layout.addLayout(top_layout)
        
        # --- 控件 ---
        self.text_viewer = HugeTextWidget()
        layout.addWidget(self.text_viewer)
        
        self.text_viewer.set_content("就绪。\n尝试切换到 Hex 模式，或者用鼠标选中文本复制。")

    def add_test_data(self):
        # 修正：中文不能直接放在 b"" 中，必须用字符串 .encode()
        # 模拟混合数据: ASCII + 二进制 + UTF-8中文
        data = b"Hello World " * 5 + b"\n" + b"\x00\x01\xFF" * 10 + "\n中文测试\n".encode('utf-8')
        self.text_viewer.append_raw_bytes(data)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = DemoWindow()
    win.show()
    sys.exit(app.exec_())