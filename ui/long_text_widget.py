import sys
import math
from enum import Enum
from PyQt5.QtWidgets import (QApplication, QMainWindow, QAbstractScrollArea, 
                             QVBoxLayout, QWidget, QPushButton, QHBoxLayout, 
                             QComboBox, QScrollBar, QCheckBox, QMessageBox, 
                             QFontComboBox, QSpinBox, QColorDialog, QGroupBox, QLabel)
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import (QPainter, QFont, QColor, QFontMetrics, QKeySequence, 
                         QClipboard, QGuiApplication)

class ViewMode(Enum):
    TEXT_ONLY = 0
    HEX_STREAM = 1

class HugeTextWidget(QAbstractScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # --- 核心配置 ---
        self._bytes_per_line = 32 
        self._encoding = 'utf-8'
        
        # --- 数据存储 ---
        self._lines = []        
        self._raw_bytes = b""   
        self._view_mode = ViewMode.TEXT_ONLY
        
        # --- 交互状态 ---
        self._sel_start_pos = None 
        self._sel_end_pos = None   
        self._is_selecting = False
        self._auto_scroll = True 
        
        # --- 样式定义 (默认暗色主题) ---
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
        
        # --- 字体初始化 ---
        # 建议默认使用等宽字体，否则 Hex 模式对齐会很丑
        self._font = QFont("Consolas", 10)
        self._font_metrics = QFontMetrics(self._font)
        self._line_num_area_width = 60
        self._current_line_index = -1 
        
        # 初始化计算
        self.setFont(self._font)
        self._update_metrics() # 计算行高和字宽
        self._apply_style()    # 应用背景色
        
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMouseTracking(True)

        self.verticalScrollBar().valueChanged.connect(self.viewport().update)
        self.horizontalScrollBar().valueChanged.connect(self.viewport().update)

    def _apply_style(self):
        """应用背景色到 Viewport"""
        self.viewport().setStyleSheet(f"background-color: {self._colors['bg'].name()};")

    def _update_metrics(self):
        """当字体改变时，必须重新计算所有尺寸"""
        self.setFont(self._font) # 确保 Painter 使用新字体
        self._font_metrics = QFontMetrics(self._font)
        self._line_height = max(1, self._font_metrics.lineSpacing())
        self._char_width = max(1, self._font_metrics.width('A')) # 作为一个基准
        
        # 更新行号区域宽度 (根据字体大小可能需要调整)
        digits = len(str(len(self._lines))) if self._lines else 4
        self._line_num_area_width = 20 + (digits * self._char_width)
        
        # 尺寸变了，滚动条范围也得变
        self._update_scrollbars()
        self.viewport().update()

    # ===========================
    # API: 外观设置 (新增功能)
    # ===========================
    def set_font_family(self, family: str):
        """设置字体家族 (建议使用 Monospace/Consolas 等等宽字体)"""
        self._font.setFamily(family)
        self._update_metrics()

    def set_font_size(self, size: int):
        """设置字体大小 (pt)"""
        self._font.setPointSize(size)
        self._update_metrics()

    def set_text_color(self, color: QColor):
        """设置主要文本颜色"""
        self._colors['text'] = QColor(color)
        self.viewport().update()
        
    def set_bg_color(self, color: QColor):
        """设置背景颜色"""
        self._colors['bg'] = QColor(color)
        self._apply_style()

    def set_color_theme(self, color_dict: dict):
        """批量设置颜色 (用于一键切换主题)"""
        self._colors.update(color_dict)
        self._apply_style()
        self.viewport().update()

    # ===========================
    # 交互事件
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
        y = point.y()
        x = point.x() + self.horizontalScrollBar().value()
        row = self.verticalScrollBar().value() + (y // self._line_height)
        row = max(0, min(row, len(self._lines) - 1))
        rel_x = x - self._line_num_area_width
        col = max(0, round(rel_x / self._char_width))
        if 0 <= row < len(self._lines):
            col = min(col, len(self._lines[row]))
        return (row, col)

    def _get_normalized_selection(self):
        if not self._sel_start_pos or not self._sel_end_pos: return None, None
        r1, c1 = self._sel_start_pos
        r2, c2 = self._sel_end_pos
        if r1 < r2: return (r1, c1), (r2, c2)
        elif r1 > r2: return (r2, c2), (r1, c1)
        else: return (r1, min(c1, c2)), (r1, max(c1, c2))

    def copy_selection(self):
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
    # 渲染逻辑
    # ===========================
    def paintEvent(self, event):
        painter = QPainter(self.viewport())
        painter.setFont(self._font) # 关键：使用当前设置的字体
        
        x_offset = -self.horizontalScrollBar().value()
        painter.translate(x_offset, 0)
        
        if self._view_mode == ViewMode.HEX_STREAM:
            self._paint_hex_stream(painter, x_offset)
        else:
            self._paint_text_mode(painter, x_offset)

    def _paint_text_mode(self, painter, x_offset):
        viewport_h = self.viewport().height()
        viewport_w = self.viewport().width() + abs(x_offset)
        
        first_row = self.verticalScrollBar().value()
        rows_visible = math.ceil(viewport_h / self._line_height) + 1
        last_row = min(first_row + rows_visible, len(self._lines))
        
        # 背景 (行号区)
        painter.translate(-x_offset, 0) 
        painter.fillRect(0, 0, self._line_num_area_width, viewport_h, self._colors['line_num_bg'])
        painter.translate(x_offset, 0) 
        
        sel_start, sel_end = self._get_normalized_selection()

        for row in range(first_row, last_row):
            line_text = self._lines[row]
            draw_y = (row - first_row) * self._line_height
            
            # 高亮当前行
            if row == self._current_line_index:
                painter.fillRect(self._line_num_area_width, draw_y, 
                                 viewport_w, self._line_height, self._colors['highlight'])
            
            # 选中背景
            if sel_start and sel_end:
                if sel_start[0] <= row <= sel_end[0]:
                    s_char = sel_start[1] if row == sel_start[0] else 0
                    e_char = sel_end[1] if row == sel_end[0] else len(line_text) + 1
                    if e_char > s_char:
                        sel_x = self._line_num_area_width + 5 + (s_char * self._char_width)
                        sel_w = (e_char - s_char) * self._char_width
                        painter.fillRect(sel_x, draw_y, sel_w, self._line_height, self._colors['selection'])

            # 行号
            painter.translate(-x_offset, 0)
            painter.setPen(self._colors['line_num_text'])
            painter.drawText(0, draw_y, self._line_num_area_width - 5, self._line_height, 
                             Qt.AlignRight | Qt.AlignVCenter, str(row + 1))
            painter.translate(x_offset, 0)
            
            # 文本
            painter.setPen(self._colors['text'])
            painter.drawText(self._line_num_area_width + 5, draw_y, 
                             viewport_w, self._line_height, 
                             Qt.AlignLeft | Qt.AlignVCenter, line_text)

    def _paint_hex_stream(self, painter, x_offset):
        viewport_h = self.viewport().height()
        first_row_idx = self.verticalScrollBar().value()
        rows_visible = math.ceil(viewport_h / self._line_height) + 1
        total_bytes = len(self._raw_bytes)
        max_rows = math.ceil(total_bytes / self._bytes_per_line)
        last_row_idx = min(first_row_idx + rows_visible, max_rows)
        
        # 布局计算 (依赖当前的 _char_width)
        w_char = self._char_width
        x_addr_end = self._line_num_area_width + (10 * w_char)
        x_hex_start = x_addr_end + (2 * w_char)
        x_hex_end = x_hex_start + (self._bytes_per_line * 3 * w_char)
        x_ascii_start = x_hex_end + (3 * w_char)
        
        painter.translate(-x_offset, 0)
        painter.fillRect(0, 0, x_addr_end, viewport_h, self._colors['line_num_bg'])
        painter.translate(x_offset, 0)

        for i in range(first_row_idx, last_row_idx):
            draw_y = (i - first_row_idx) * self._line_height
            start_byte = i * self._bytes_per_line
            end_byte = min(start_byte + self._bytes_per_line, total_bytes)
            chunk = self._raw_bytes[start_byte:end_byte]
            
            # 地址
            painter.translate(-x_offset, 0)
            painter.setPen(self._colors['offset_text'])
            painter.drawText(0, draw_y, x_addr_end - 5, self._line_height, 
                             Qt.AlignRight | Qt.AlignVCenter, f"{start_byte:08X}")
            painter.translate(x_offset, 0)
            
            # Hex
            hex_parts = [f"{b:02X}" for b in chunk]
            painter.setPen(self._colors['hex_text'])
            painter.drawText(x_hex_start, draw_y, x_hex_end, self._line_height,
                             Qt.AlignLeft | Qt.AlignVCenter, " ".join(hex_parts))
            
            # ASCII
            ascii_parts = [chr(b) if 32 <= b <= 126 else "." for b in chunk]
            painter.setPen(self._colors['text'])
            painter.drawText(x_ascii_start, draw_y, 10000, self._line_height,
                             Qt.AlignLeft | Qt.AlignVCenter, "".join(ascii_parts))

    # ===========================
    # 逻辑与 API
    # ===========================
    def resizeEvent(self, event):
        self._update_scrollbars()
        super().resizeEvent(event)

    def _update_scrollbars(self):
        viewport_h = self.viewport().height()
        # 避免除以0
        line_h = max(1, self._line_height)
        rows_per_page = viewport_h // line_h
        
        if self._view_mode == ViewMode.HEX_STREAM:
            total_rows = math.ceil(len(self._raw_bytes) / self._bytes_per_line)
            # 计算内容宽度
            chars = 12 + (self._bytes_per_line * 3) + 3 + self._bytes_per_line
            content_width = chars * self._char_width + self._line_num_area_width
        else:
            total_rows = len(self._lines)
            # 文本模式: 简单起见设为 viewport 宽，若要横向滚动需遍历最长行（耗时）
            content_width = self.viewport().width()
            
        v_max = max(0, total_rows - rows_per_page)
        self.verticalScrollBar().setRange(0, v_max)
        self.verticalScrollBar().setPageStep(rows_per_page)
        
        h_max = max(0, content_width - self.viewport().width())
        self.horizontalScrollBar().setRange(0, int(h_max))
        self.horizontalScrollBar().setPageStep(self.viewport().width())

    def set_view_mode(self, mode: ViewMode):
        self._view_mode = mode
        self._sel_start_pos = None
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
        scrollbar = self.verticalScrollBar()
        was_at_bottom = scrollbar.value() >= (scrollbar.maximum() - 1)
        
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
# Demo: 包含外观控制的演示窗口
# ===========================
class DemoWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("全能文本控件 Demo (支持字体/颜色)")
        self.resize(1200, 800)
        
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        
        # --- 1. 顶部功能栏 (功能开关) ---
        ctrl_layout = QHBoxLayout()
        self.check_auto = QCheckBox("Auto Scroll")
        self.check_auto.setChecked(True)
        self.check_auto.stateChanged.connect(lambda s: self.text_viewer.set_auto_scroll(s == Qt.Checked))
        
        self.combo_mode = QComboBox()
        self.combo_mode.addItems(["Text Mode", "Hex Mode"])
        self.combo_mode.currentIndexChanged.connect(lambda i: self.text_viewer.set_view_mode(ViewMode(i)))
        
        self.btn_add = QPushButton("Append Data")
        self.btn_add.clicked.connect(self.add_test_data)
        
        ctrl_layout.addWidget(self.check_auto)
        ctrl_layout.addWidget(self.combo_mode)
        ctrl_layout.addWidget(self.btn_add)
        ctrl_layout.addStretch()
        
        # --- 2. 外观设置栏 (新增) ---
        style_group = QGroupBox("Appearance Settings")
        style_layout = QHBoxLayout(style_group)
        
        # 字体选择
        style_layout.addWidget(QLabel("Font:"))
        self.font_combo = QFontComboBox()
        # 过滤只显示等宽字体 (可选，但推荐，因为 Hex 模式依赖对齐)
        self.font_combo.setFontFilters(QFontComboBox.MonospacedFonts) 
        self.font_combo.currentFontChanged.connect(self.on_font_family_changed)
        # 默认设为 Consolas 或 Courier
        font_idx = -1
        for i in range(self.font_combo.count()):
            if "Consolas" in self.font_combo.itemText(i):
                font_idx = i
                break
        if font_idx != -1: self.font_combo.setCurrentIndex(font_idx)
        
        style_layout.addWidget(self.font_combo)

        # 字号选择
        style_layout.addWidget(QLabel("Size:"))
        self.spin_size = QSpinBox()
        self.spin_size.setRange(6, 72)
        self.spin_size.setValue(10)
        self.spin_size.valueChanged.connect(self.text_viewer.set_font_size)
        style_layout.addWidget(self.spin_size)
        
        # 颜色选择
        self.btn_color = QPushButton("Text Color")
        self.btn_color.clicked.connect(self.pick_color)
        style_layout.addWidget(self.btn_color)

        self.btn_bg_color = QPushButton("BG Color")
        self.btn_bg_color.clicked.connect(self.pick_bg_color)
        style_layout.addWidget(self.btn_bg_color)
        
        style_layout.addStretch()

        main_layout.addLayout(ctrl_layout)
        main_layout.addWidget(style_group)
        
        # --- 3. 文本控件 ---
        self.text_viewer = HugeTextWidget()
        main_layout.addWidget(self.text_viewer)
        
        # 初始化
        self.text_viewer.set_content("Initialization Complete.\nTry changing font settings above.\n")

    def on_font_family_changed(self, font):
        self.text_viewer.set_font_family(font.family())

    def pick_color(self):
        color = QColorDialog.getColor(Qt.white, self, "Select Text Color")
        if color.isValid():
            self.text_viewer.set_text_color(color)

    def pick_bg_color(self):
        color = QColorDialog.getColor(Qt.black, self, "Select Background Color")
        if color.isValid():
            self.text_viewer.set_bg_color(color)

    def add_test_data(self):
        # 混合数据测试
        part1 = b"System Check: " + b"A"*20 + b"\n"
        part2 = b"\x00\x01\x02\x03" * 5
        part3 = "\n中文显示测试: 你好世界\n".encode('utf-8')
        self.text_viewer.append_raw_bytes(part1 + part2 + part3)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    # 高分屏支持
    app.setAttribute(Qt.AA_EnableHighDpiScaling)
    app.setAttribute(Qt.AA_UseHighDpiPixmaps)
    
    win = DemoWindow()
    win.show()
    sys.exit(app.exec_())