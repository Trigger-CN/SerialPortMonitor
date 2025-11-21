import sys
import math
from enum import Enum
from PyQt5.QtWidgets import (QApplication, QMainWindow, QAbstractScrollArea, 
                             QVBoxLayout, QWidget, QPushButton, QHBoxLayout, 
                             QLabel, QMessageBox, QComboBox, QScrollBar)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QFont, QColor, QFontMetrics

class ViewMode(Enum):
    TEXT_ONLY = 0      # 纯文本 (按行)
    HEX_STREAM = 1     # Hex 流模式 (32字节/行, 右侧ASCII对照)
    TEXT_WITH_HEX = 2  # 文本+Hex对照 (按行, 左右分栏)

class HugeTextWidget(QAbstractScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # --- 核心配置 ---
        self._bytes_per_line = 32  # <--- 核心修改：改为32字节每行
        
        # --- 数据存储 ---
        self._lines = []        
        self._raw_bytes = b""   
        self._line_styles = {}  
        
        self._view_mode = ViewMode.TEXT_ONLY
        self._encoding = 'utf-8'
        
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
            'hex_text': QColor("#569CD6"),
            'offset_text': QColor("#2B91AF"),
            'separator': QColor("#444444")
        }
        
        self._line_num_area_width = 60
        self._current_line_index = -1 
        
        # 初始化
        self.setFont(self._font)
        self.viewport().setStyleSheet(f"background-color: {self._colors['bg'].name()};")
        
        # 连接滚动条事件
        self.verticalScrollBar().valueChanged.connect(self.viewport().update)
        self.horizontalScrollBar().valueChanged.connect(self.viewport().update)

    def _update_metrics(self):
        self._line_height = self._font_metrics.lineSpacing()
        self._char_width = self._font_metrics.width('A')

    # ===========================
    # Core: 绘制逻辑
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
        viewport_h = self.viewport().height()
        viewport_w = self.viewport().width() + abs(x_offset) # 逻辑宽度
        
        first_row = self.verticalScrollBar().value()
        rows_visible = math.ceil(viewport_h / self._line_height) + 1
        last_row = min(first_row + rows_visible, len(self._lines))
        
        # 绘制行号背景 (固定在左侧，不受水平滚动影响)
        # 我们需要逆向 translate 回去绘制固定UI
        painter.translate(-x_offset, 0) 
        painter.fillRect(0, 0, self._line_num_area_width, viewport_h, self._colors['line_num_bg'])
        painter.translate(x_offset, 0) # 恢复
        
        split_x = 0
        if self._view_mode == ViewMode.TEXT_WITH_HEX:
            # 动态计算分割线位置，保证左侧至少留出 500px 或者一半
            split_x = max(500, viewport_w // 2)
            painter.setPen(self._colors['separator'])
            painter.drawLine(split_x, 0, split_x, viewport_h)

        for row in range(first_row, last_row):
            line_text = self._lines[row]
            draw_y = (row - first_row) * self._line_height
            
            # 高亮背景
            if row == self._current_line_index:
                painter.fillRect(self._line_num_area_width, draw_y, 
                                 viewport_w, self._line_height, self._colors['highlight'])
            
            # 行号 (固定位置绘制)
            painter.translate(-x_offset, 0)
            painter.setPen(self._colors['line_num_text'])
            painter.drawText(0, draw_y, self._line_num_area_width - 5, self._line_height, 
                             Qt.AlignRight | Qt.AlignVCenter, str(row + 1))
            painter.translate(x_offset, 0)
            
            # 绘制左侧文本
            painter.setPen(self._colors['text'])
            text_limit = (split_x - self._line_num_area_width - 10) if self._view_mode == ViewMode.TEXT_WITH_HEX else viewport_w
            
            painter.drawText(self._line_num_area_width + 5, draw_y, 
                             text_limit, self._line_height, 
                             Qt.AlignLeft | Qt.AlignVCenter, line_text)
            
            # 绘制右侧 HEX
            if self._view_mode == ViewMode.TEXT_WITH_HEX:
                try:
                    line_bytes = line_text.encode(self._encoding, errors='replace')
                    # 这里的 Hex 仅仅是当前行的 Hex，不强制 32 字节对齐，而是有多少显示多少
                    hex_str = " ".join(f"{b:02X}" for b in line_bytes)
                    painter.setPen(self._colors['hex_text'])
                    painter.drawText(split_x + 10, draw_y, 
                                     viewport_w - split_x, self._line_height,
                                     Qt.AlignLeft | Qt.AlignVCenter, hex_str)
                except: pass

    def _paint_hex_stream(self, painter, x_offset):
        """渲染 32字节/行 的 Hex 流模式"""
        viewport_h = self.viewport().height()
        viewport_w = self.viewport().width()
        
        first_row_idx = self.verticalScrollBar().value()
        rows_visible = math.ceil(viewport_h / self._line_height) + 1
        
        total_bytes = len(self._raw_bytes)
        # 计算总行数 (基于32字节每行)
        max_rows = math.ceil(total_bytes / self._bytes_per_line)
        last_row_idx = min(first_row_idx + rows_visible, max_rows)
        
        # --- 布局计算 (单位: 像素) ---
        # 1. 地址区: 8 chars
        # 2. Hex区: 32 bytes * 3 chars (XX + space)
        # 3. ASCII区: 32 chars
        
        w_char = self._char_width
        x_addr_end = self._line_num_area_width + (10 * w_char)
        x_hex_start = x_addr_end + (2 * w_char)
        # Hex区域宽度 = 32 * 3 * char_width
        x_hex_end = x_hex_start + (self._bytes_per_line * 3 * w_char)
        x_ascii_start = x_hex_end + (3 * w_char)
        
        # 绘制左侧固定背景 (行号/地址栏)
        painter.translate(-x_offset, 0)
        painter.fillRect(0, 0, x_addr_end, viewport_h, self._colors['line_num_bg'])
        painter.translate(x_offset, 0)

        for i in range(first_row_idx, last_row_idx):
            draw_y = (i - first_row_idx) * self._line_height
            start_byte = i * self._bytes_per_line
            end_byte = min(start_byte + self._bytes_per_line, total_bytes)
            
            chunk = self._raw_bytes[start_byte:end_byte]
            
            # 1. 绘制地址 (固定在左侧)
            painter.translate(-x_offset, 0) # 暂时取消偏移以绘制固定列
            painter.setPen(self._colors['offset_text'])
            addr_str = f"{start_byte:08X}"
            painter.drawText(0, draw_y, x_addr_end - 5, self._line_height, 
                             Qt.AlignRight | Qt.AlignVCenter, addr_str)
            painter.translate(x_offset, 0) # 恢复偏移
            
            # 2. 绘制 Hex 数据 (每8个字节加一个额外空格，方便阅读)
            hex_parts = []
            for idx, b in enumerate(chunk):
                hex_parts.append(f"{b:02X}")
                # 可选：每8字节加额外分隔符，这里保持简单空格
            
            hex_str = " ".join(hex_parts)
            
            painter.setPen(self._colors['hex_text'])
            painter.drawText(x_hex_start, draw_y, x_hex_end - x_hex_start, self._line_height,
                             Qt.AlignLeft | Qt.AlignVCenter, hex_str)
            
            # 3. 绘制 ASCII 数据
            ascii_parts = []
            for b in chunk:
                if 32 <= b <= 126:
                    ascii_parts.append(chr(b))
                else:
                    ascii_parts.append(".")
            
            painter.setPen(self._colors['text'])
            painter.drawText(x_ascii_start, draw_y, 10000, self._line_height,
                             Qt.AlignLeft | Qt.AlignVCenter, "".join(ascii_parts))

    # ===========================
    # 滚动条与布局更新
    # ===========================
    def resizeEvent(self, event):
        self._update_scrollbars()
        super().resizeEvent(event)

    def _update_scrollbars(self):
        # 1. 垂直滚动条
        viewport_h = self.viewport().height()
        rows_per_page = viewport_h // self._line_height
        
        if self._view_mode == ViewMode.HEX_STREAM:
            total_rows = math.ceil(len(self._raw_bytes) / self._bytes_per_line)
        else:
            total_rows = len(self._lines)
            
        v_max = max(0, total_rows - rows_per_page)
        self.verticalScrollBar().setRange(0, v_max)
        self.verticalScrollBar().setPageStep(rows_per_page)
        
        # 2. 水平滚动条 (关键：根据内容宽度计算)
        viewport_w = self.viewport().width()
        content_width = 0
        
        if self._view_mode == ViewMode.HEX_STREAM:
            # 估算宽度: 地址 + 间隔 + Hex(32*3) + 间隔 + ASCII(32)
            # 大约 140-150 个字符宽度
            chars_count = 10 + 2 + (self._bytes_per_line * 3) + 3 + self._bytes_per_line
            content_width = chars_count * self._char_width + self._line_num_area_width
        
        elif self._view_mode == ViewMode.TEXT_WITH_HEX:
            # 估算宽度: 左侧文本区域 + 分割线 + 右侧Hex区域
            # 这里假设一个比较大的宽度以容纳并排显示
            content_width = viewport_w * 1.5 
        
        else: # TEXT_ONLY
            # 文本模式一般不需要水平滚动，除非加上最长行计算(比较耗时)，这里简单处理
            content_width = viewport_w
            
        h_max = max(0, content_width - viewport_w)
        self.horizontalScrollBar().setRange(0, int(h_max))
        self.horizontalScrollBar().setPageStep(viewport_w)

    # ===========================
    # API 接口保持不变...
    # ===========================
    def set_view_mode(self, mode: ViewMode):
        self._view_mode = mode
        self.verticalScrollBar().setValue(0)
        self.horizontalScrollBar().setValue(0) # 切换模式重置水平滚动
        self._update_scrollbars()
        self.viewport().update()

    def set_content(self, text_content):
        self._lines = text_content.splitlines()
        self._raw_bytes = text_content.encode(self._encoding, errors='replace')
        self._update_scrollbars()
        self.viewport().update()

    def set_bytes_content(self, raw_data: bytes):
        """(可选) 直接设置二进制数据"""
        self._raw_bytes = raw_data
        # 尝试解码为文本行，解不出来的用 replacement char
        try:
            text = raw_data.decode(self._encoding, errors='replace')
            self._lines = text.splitlines()
        except:
            self._lines = ["(Binary Data Decode Failed)"]
            
        self._update_scrollbars()
        self._update_line_num_width()
        self.viewport().update()

    def append_lines(self, new_lines):
        # 这是一个稍微复杂的操作，因为要同步 update bytes
        # 考虑到性能，如果频繁 append，建议只用于 Log 文本模式
        if isinstance(new_lines, str):
            new_lines = new_lines.splitlines()
        self._lines.extend(new_lines)
        
        # 同步追加 bytes (加换行符)
        additional_bytes = ("\n".join(new_lines) + "\n").encode(self._encoding)
        self._raw_bytes += additional_bytes
        
        self._update_scrollbars()
        self.viewport().update()

    def append_bytes(self, data: bytes):
        """
        追加原始字节数据 (API)
        自动处理 Hex 视图的更新和 Text 视图的行拼接
        """
        if not data:
            return

        # 1. 记录追加前的状态 (用于判断是否需要拼接文本行)
        # 如果当前 raw_bytes 为空，或者以换行符结尾，说明是新的一行开始
        # 注意：这里简单检查 \n (0x0A)，兼容 Windows \r\n，因为 \n 通常是最后的字符
        is_new_line_start = True
        if len(self._raw_bytes) > 0:
            last_byte = self._raw_bytes[-1]
            if last_byte != 10: # 10 is \n
                is_new_line_start = False

        # 2. 更新底层字节存储 (Hex 视图的数据源)
        self._raw_bytes += data

        # 3. 更新文本行存储 (Text 视图的数据源)
        # 尝试解码新数据
        try:
            new_text = data.decode(self._encoding, errors='replace')
        except Exception:
            new_text = "<?>" # 理论上 errors='replace' 不会抛异常，这里防万一

        new_lines = new_text.splitlines()

        # 特殊处理：splitlines() 会吃掉字符串末尾的换行符
        # 例如 "abc\n".splitlines() -> ["abc"]
        # 如果 data 仅仅包含一个换行符 b'\n'，new_lines 会是空列表
        # 我们需要根据上下文决定如何处理

        if not is_new_line_start and self._lines:
            # 情况 A: 上次的数据没换行 (例如 b"Hell")
            # 这次的数据 (例如 b"o World\n") 需要先拼接到上一行
            
            if new_lines:
                # 取出新数据的第一段，拼接到最后一行
                self._lines[-1] += new_lines[0]
                # 将剩余的新行追加到列表
                if len(new_lines) > 1:
                    self._lines.extend(new_lines[1:])
            else:
                # 如果 new_lines 为空 (例如 data=b'\n' 或 data=b''), 
                # 但 raw_bytes 确实增加了。
                # 如果 data 中包含换行符 (被 splitlines 吃掉了)，
                # 实际上我们在 Text 视图中通常不显式显示末尾的空行，
                # 除非为了光标定位。作为 Log Viewer，保持 splitlines 的行为即可。
                # 唯一例外：如果追加了纯文本内容但没有换行符 (data=b"xyz")
                if new_text and not (new_text.endswith('\n') or new_text.endswith('\r')):
                     self._lines[-1] += new_text
        else:
            # 情况 B: 上次结束是换行，或者是第一次添加
            if new_lines:
                self._lines.extend(new_lines)
            elif new_text and not (new_text.endswith('\n') or new_text.endswith('\r')):
                 # 数据不包含换行符，直接作为新行添加
                 self._lines.append(new_text)

        # 4. 刷新界面
        self._update_scrollbars()
        
        # 自动滚动到底部 (可选，通常追加日志时用户希望自动滚动)
        if self.verticalScrollBar().value() > self.verticalScrollBar().maximum() - 20:
            self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())
        
        self.viewport().update()

    def _update_line_num_width(self):
        digits = len(str(len(self._lines)))
        self._line_num_area_width = 20 + (digits * 10)


    def clear(self):
        """清空内容"""
        self._lines = []
        self._line_styles = {}
        self._update_scrollbars()
        self.viewport().update()

    def goto_line(self, line_no):
        """跳转到指定行"""
        line_idx = line_no - 1
        if 0 <= line_idx < len(self._lines):
            self._current_line_index = line_idx
            self.verticalScrollBar().setValue(line_idx)
            self.viewport().update()
            return True
        return False

    def find_text(self, query, start_from=0):
        """简单的查找功能，返回找到的行号索引"""
        for i in range(start_from, len(self._lines)):
            if query in self._lines[i]:
                self.goto_line(i + 1)
                return i
        return -1

    def set_line_style(self, line_idx, color_hex=None, bg_hex=None):
        """设置某行的样式（文本颜色，背景颜色）"""
        if 0 <= line_idx < len(self._lines):
            self._line_styles[line_idx] = (color_hex, bg_hex)
            self.viewport().update()

    def set_global_style(self, bg_color, text_color, font_size=10):
        """自定义控件整体风格"""
        self._bg_color = QColor(bg_color)
        self._text_color = QColor(text_color)
        self._font = QFont("Consolas", font_size)
        self._font_metrics = QFontMetrics(self._font)
        self._line_height = self._font_metrics.lineSpacing()
        self._char_width = self._font_metrics.width('A')
        
        self.viewport().setStyleSheet(f"background-color: {self._bg_color.name()};")
        self.setFont(self._font)
        self._update_scrollbars()
        self.viewport().update()

    def scroll_to_bottom(self):
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())

    def _update_line_num_width(self):
        """根据行数动态调整行号区域宽度"""
        digits = len(str(len(self._lines)))
        self._line_num_area_width = 20 + (digits * 10)
# ===========================
# Demo: 验证窗口
# ===========================
class DemoWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("超级文本/Hex 浏览控件 Demo")
        self.resize(1200, 800)
        
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # --- 顶部控制栏 ---
        top_bar = QHBoxLayout()
        
        self.combo_mode = QComboBox()
        self.combo_mode.addItems(["纯文本模式 (Text Only)", "Hex 流模式 (Hex Stream)", "文本/Hex 对照 (Side-by-Side)"])
        self.combo_mode.currentIndexChanged.connect(self.change_mode)
        
        self.btn_gen = QPushButton("生成 10MB 混合数据")
        self.btn_gen.clicked.connect(self.generate_data)
        
        top_bar.addWidget(QLabel("显示模式:"))
        top_bar.addWidget(self.combo_mode)
        top_bar.addWidget(self.btn_gen)
        top_bar.addStretch()
        
        layout.addLayout(top_bar)
        
        self.text_viewer = HugeTextWidget()
        layout.addWidget(self.text_viewer)
        
        # 初始提示
        self.text_viewer.set_content("请点击生成数据...\n支持中文显示。\nHex Mode allows viewing raw bytes.")

    def change_mode(self, index):
        modes = [ViewMode.TEXT_ONLY, ViewMode.HEX_STREAM]
        self.text_viewer.set_view_mode(modes[index])

    def generate_data(self):
        # 模拟生成一些包含中文、英文、符号的数据
        lines = []
        for i in range(50000):
            lines.append(f"行号 {i:05d}: Python Qt5 高性能控件测试 - ASCII: ABCabc123 - 中文: 你好世界")
        
        full_text = "\n".join(lines)
        self.text_viewer.set_content(full_text)
        QMessageBox.information(self, "完成", f"已加载 {len(lines)} 行文本。\n尝试切换 Hex 模式查看底层编码！")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion") # 稍微好看点的风格
    win = DemoWindow()
    win.show()
    sys.exit(app.exec_())