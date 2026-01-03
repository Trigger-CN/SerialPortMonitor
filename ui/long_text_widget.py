import sys
import math
import time
import re
from datetime import datetime
from enum import Enum
from PyQt5.QtWidgets import (QApplication, QMainWindow, QAbstractScrollArea, 
                             QVBoxLayout, QWidget, QPushButton, QHBoxLayout, 
                             QComboBox, QCheckBox, QMessageBox, 
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
        self._lines = []           # 文本内容
        self._current_line_index = -1 
        self._line_timestamps = [] # 时间戳 (float time.time())
        self._raw_bytes = b""      # 原始字节
        
        # --- 状态开关 ---
        self._view_mode = ViewMode.TEXT_ONLY
        self._show_timestamp = False # <--- 新增开关
        self._auto_scroll = True 
        
        # --- 交互状态 ---
        self._sel_start_pos = None 
        self._sel_end_pos = None   
        self._is_selecting = False
        
        # --- 高亮规则 ---
        self._highlight_rules = []  # 存储高亮规则列表
        
        # --- 过滤功能 ---
        self._filter_pattern = None  # 正则表达式模式对象
        self._filter_enabled = False  # 是否启用过滤
        self._filter_regex_str = ""  # 原始正则表达式字符串
        
        # --- 性能优化：换行结果缓存 ---
        self._wrapped_lines_cache = {}  # 缓存换行结果: {(line_idx, available_width): wrapped_lines}
        self._cached_available_width = None  # 缓存时的可用宽度
        
        # --- 样式定义 ---
        self._colors = {
            'bg': QColor("#1E1E1E"),
            'text': QColor("#D4D4D4"),
            'line_num_bg': QColor("#252526"),
            'line_num_text': QColor("#858585"),
            'timestamp_text': QColor("#569CD6"), # <--- 时间戳颜色
            'highlight': QColor("#264F78"),
            'selection': QColor("#204060"),
            'hex_text': QColor("#B5CEA8"),
            'offset_text': QColor("#2B91AF"),
        }
        
        # --- 字体初始化 ---
        self._font = QFont("Consolas", 10)
        self._font_metrics = QFontMetrics(self._font)
        
        # 布局尺寸
        self._line_num_area_width = 0 
        self._timestamp_width = 0 
        
        self.setFont(self._font)
        self._update_metrics()
        self._apply_style()
        
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMouseTracking(True)

        self.verticalScrollBar().valueChanged.connect(self.viewport().update)
        self.horizontalScrollBar().valueChanged.connect(self.viewport().update)

    def resizeEvent(self, event):
        """窗口大小改变时，重新计算滚动条"""
        super().resizeEvent(event)
        if self._view_mode == ViewMode.TEXT_ONLY:
            self._update_scrollbars()
        self.viewport().update()

    def _apply_style(self):
        self.viewport().setStyleSheet(f"background-color: {self._colors['bg'].name()};")

    def _update_metrics(self):
        """重新计算布局尺寸"""
        old_available_width = self._cached_available_width
        
        self.setFont(self._font)
        self._font_metrics = QFontMetrics(self._font)
        self._line_height = max(1, self._font_metrics.lineSpacing())
        self._char_width = max(1, self._font_metrics.width('A'))
        
        # 1. 计算时间戳区域宽度 (HH:MM:SS.mmm) -> 约 12个字符
        if self._show_timestamp:
            # 预留宽度: "12:34:56.789 "
            self._timestamp_width = self._font_metrics.width("00:00:00.000 ")
        else:
            self._timestamp_width = 0

        # 2. 计算行号区域宽度
        digits = len(str(len(self._lines))) if self._lines else 4
        # 基础行号宽 + 左右padding
        line_num_width = 20 + (digits * self._char_width)
        
        # 左侧总固定区域宽度 = 时间戳宽 + 行号宽
        self._line_num_area_width = self._timestamp_width + line_num_width
        
        # 如果可用宽度改变，清除换行缓存
        new_available_width = self._get_available_width()
        if old_available_width != new_available_width:
            self._wrapped_lines_cache.clear()
        self._cached_available_width = new_available_width
        
        self._update_scrollbars()
        self.viewport().update()
    
    def _clear_wrapped_cache(self):
        """清除换行缓存"""
        self._wrapped_lines_cache.clear()

    # ===========================
    # API: 核心功能
    # ===========================
    def set_show_timestamp(self, show: bool):
        """开启/关闭时间戳显示"""
        self._show_timestamp = show
        self._update_metrics() # 重新计算布局宽度

    def append_raw_bytes(self, data: bytes):
        """追加数据，同时自动打标时间戳"""
        if not data: return
        
        now = time.time() # 获取当前时间
        
        scrollbar = self.verticalScrollBar()
        was_at_bottom = scrollbar.value() >= (scrollbar.maximum() - 1)
        
        is_new_line_start = True
        if len(self._raw_bytes) > 0 and self._raw_bytes[-1] != 10:
            is_new_line_start = False
        
        self._raw_bytes += data
        try: new_text = data.decode(self._encoding, errors='replace')
        except: new_text = ""
        
        new_lines_list = new_text.splitlines()
        
        # --- 核心逻辑: 同步更新 _lines 和 _line_timestamps ---
        
        if not is_new_line_start and self._lines:
            # 情况A: 拼接到上一行
            if new_lines_list:
                self._lines[-1] += new_lines_list[0]
                # 上一行的时间戳保持不变，或者更新为最新追加时间? 通常保持第一次创建的时间
                
                if len(new_lines_list) > 1:
                    # 追加剩余新行
                    self._lines.extend(new_lines_list[1:])
                    # 为新行生成时间戳
                    self._line_timestamps.extend([now] * (len(new_lines_list) - 1))
            else:
                 # 纯文本无换行追加
                 if new_text and not (new_text.endswith('\n') or new_text.endswith('\r')):
                     self._lines[-1] += new_text
        else:
            # 情况B: 纯新增行
            if new_lines_list:
                self._lines.extend(new_lines_list)
                self._line_timestamps.extend([now] * len(new_lines_list))
            elif new_text and not (new_text.endswith('\n') or new_text.endswith('\r')):
                 self._lines.append(new_text)
                 self._line_timestamps.append(now)

        # 补齐：极端情况下如果 timestamp 列表长度小于 lines (比如 set_content 只设了文本)
        # 填充 0 或者当前时间
        if len(self._line_timestamps) < len(self._lines):
            diff = len(self._lines) - len(self._line_timestamps)
            self._line_timestamps.extend([now] * diff)

        self._update_scrollbars()
        
        # 如果行数增加导致行号位数变化(99->100)，需要重新计算宽度
        # 简单优化：每增加100行或者1000行检查一次，或者简单地每次 check
        self._update_line_num_width_dynamic()
        
        if self._auto_scroll or was_at_bottom:
            self.scroll_to_bottom()
        self.viewport().update()

    def _update_line_num_width_dynamic(self):
        """追加内容时动态检查是否需要扩宽行号区域"""
        if not self._lines: return
        digits = len(str(len(self._lines)))
        # 预估现有宽度能否容纳
        current_digits_width = self._line_num_area_width - self._timestamp_width - 20
        needed_width = digits * self._char_width
        
        if needed_width > current_digits_width:
            self._update_metrics()

    def _get_chars_per_line(self):
        """计算每行能显示的字符数（考虑边距）- 保留用于兼容性，实际应使用实际宽度"""
        viewport_w = self.viewport().width()
        available_width = viewport_w - self._line_num_area_width - 10  # 减去左侧区域和右边距
        if available_width <= 0:
            return 1
        return max(1, int(available_width / self._char_width))

    def _get_available_width(self):
        """获取可用于文本显示的宽度（考虑边距）"""
        viewport_w = self.viewport().width()
        available_width = viewport_w - self._line_num_area_width - 10  # 减去左侧区域和右边距
        return max(1, available_width)

    def _get_wrapped_lines(self, text, line_idx=None, use_cache=True):
        """将文本按可用宽度分割成多行，返回行列表（考虑全角/半角字符）
        
        Args:
            text: 要换行的文本
            line_idx: 行索引，用于缓存（可选）
            use_cache: 是否使用缓存
        """
        if not text:
            return ['']
        
        available_width = self._get_available_width()
        
        # 尝试从缓存获取
        if use_cache and line_idx is not None:
            cache_key = (line_idx, available_width)
            if cache_key in self._wrapped_lines_cache:
                return self._wrapped_lines_cache[cache_key]
        
        text_width = self._font_metrics.width(text)
        
        # 如果文本宽度不超过可用宽度，直接返回
        if text_width <= available_width:
            result = [text]
        else:
            wrapped = []
            current_start = 0
            current_end = 0
            current_width = 0
            
            i = 0
            while i < len(text):
                char = text[i]
                char_width = self._font_metrics.width(char)
                
                # 如果当前字符加上当前行的宽度超过可用宽度，需要换行
                if current_width + char_width > available_width and current_end > current_start:
                    # 保存当前行
                    wrapped.append(text[current_start:current_end])
                    current_start = current_end
                    current_width = 0
                
                # 如果单个字符就超过可用宽度（极端情况），强制添加
                if current_start == current_end and char_width > available_width:
                    wrapped.append(char)
                    current_start = i + 1
                    current_end = i + 1
                    current_width = 0
                else:
                    current_end = i + 1
                    current_width += char_width
                
                i += 1
            
            # 添加最后一行
            if current_end > current_start:
                wrapped.append(text[current_start:current_end])
            
            result = wrapped if wrapped else [text]
        
        # 存入缓存
        if use_cache and line_idx is not None:
            cache_key = (line_idx, available_width)
            self._wrapped_lines_cache[cache_key] = result
        
        return result

    def _get_display_line_count(self, line_idx):
        """获取指定原始行的显示行数（考虑换行和全角字符）"""
        if line_idx < 0 or line_idx >= len(self._lines):
            return 0
        text = self._lines[line_idx]
        if not text:
            return 1
        wrapped_lines = self._get_wrapped_lines(text, line_idx=line_idx, use_cache=True)
        return len(wrapped_lines)

    def _get_total_display_lines(self):
        """获取总显示行数（所有原始行换行后的总行数，考虑过滤）"""
        total = 0
        for i in range(len(self._lines)):
            # 如果启用过滤且不匹配，跳过这一行
            if not self._line_matches_filter(self._lines[i]):
                continue
            total += self._get_display_line_count(i)
        return total

    def _display_row_to_source_row_col(self, display_row):
        """将显示行号映射到原始行号和列号（考虑过滤）"""
        current_display = 0
        for src_row in range(len(self._lines)):
            # 如果启用过滤且不匹配，跳过这一行
            if not self._line_matches_filter(self._lines[src_row]):
                continue
            
            display_count = self._get_display_line_count(src_row)
            if current_display + display_count > display_row:
                # 在这一行的某个显示行中
                wrapped_lines = self._get_wrapped_lines(self._lines[src_row], line_idx=src_row, use_cache=True)
                local_display = display_row - current_display
                if local_display < len(wrapped_lines):
                    # 计算到当前显示行的字符偏移
                    col = 0
                    for i in range(local_display):
                        col += len(wrapped_lines[i])
                    return (src_row, col)
                else:
                    # 在最后一行，返回行尾
                    return (src_row, len(self._lines[src_row]))
            current_display += display_count
        # 超出范围，返回最后一行（考虑过滤）
        if self._lines:
            # 找到最后一个匹配的行
            for i in range(len(self._lines) - 1, -1, -1):
                if self._line_matches_filter(self._lines[i]):
                    return (i, len(self._lines[i]))
            return (len(self._lines) - 1, len(self._lines[-1]))
        return (0, 0)

    def _source_row_col_to_display_row(self, src_row, col):
        """将原始行号和列号映射到显示行号（考虑过滤）"""
        if src_row < 0 or src_row >= len(self._lines):
            return 0
        
        # 计算之前所有原始行的显示行数（只计算匹配过滤的行）
        display_row = 0
        for i in range(src_row):
            if self._line_matches_filter(self._lines[i]):
                display_row += self._get_display_line_count(i)
        
        # 如果当前行不匹配过滤，返回之前的总行数
        if not self._line_matches_filter(self._lines[src_row]):
            return display_row
        
        # 计算在当前行的哪个显示行
        wrapped_lines = self._get_wrapped_lines(self._lines[src_row], line_idx=src_row, use_cache=True)
        char_count = 0
        for i, wrapped_line in enumerate(wrapped_lines):
            if col < char_count + len(wrapped_line):
                return display_row + i
            char_count += len(wrapped_line)
        
        # 如果列号超出，返回最后一个显示行
        return display_row + len(wrapped_lines) - 1

    # ===========================
    # 渲染逻辑
    # ===========================
    def paintEvent(self, event):
        painter = QPainter(self.viewport())
        painter.setFont(self._font)
        
        x_offset = -self.horizontalScrollBar().value()
        painter.translate(x_offset, 0)
        
        if self._view_mode == ViewMode.HEX_STREAM:
            self._paint_hex_stream(painter, x_offset)
        else:
            self._paint_text_mode(painter, x_offset)

    def _paint_text_mode(self, painter, x_offset):
        viewport_h = self.viewport().height()
        viewport_w = self.viewport().width() + abs(x_offset)
        
        first_display_row = self.verticalScrollBar().value()
        rows_visible = math.ceil(viewport_h / self._line_height) + 1
        last_display_row = first_display_row + rows_visible
        
        # 1. 绘制左侧背景 (包含时间戳区域 + 行号区域)
        painter.translate(-x_offset, 0) 
        painter.fillRect(0, 0, self._line_num_area_width, viewport_h, self._colors['line_num_bg'])
        painter.translate(x_offset, 0) 
        
        sel_start, sel_end = self._get_normalized_selection()
        
        # 遍历所有原始行，找出需要绘制的显示行
        current_display_row = 0
        for src_row in range(len(self._lines)):
            line_text = self._lines[src_row]
            
            # 过滤：如果启用过滤且不匹配，跳过这一行
            if not self._line_matches_filter(line_text):
                continue
            
            wrapped_lines = self._get_wrapped_lines(line_text, line_idx=src_row, use_cache=True)
            display_count = len(wrapped_lines)
            
            for wrap_idx, wrapped_text in enumerate(wrapped_lines):
                display_row = current_display_row + wrap_idx
                
                # 只绘制可见范围内的行
                if display_row < first_display_row:
                    continue
                if display_row >= last_display_row:
                    break
                
                draw_y = (display_row - first_display_row) * self._line_height
                is_first_wrap_line = (wrap_idx == 0)
                
                # 高亮当前行（只有原始行的第一行显示高亮）
                if src_row == self._current_line_index and is_first_wrap_line:
                    painter.fillRect(self._line_num_area_width, draw_y, viewport_w, self._line_height, self._colors['highlight'])
                
                # 绘制选择背景
                if sel_start and sel_end:
                    if sel_start[0] <= src_row <= sel_end[0]:
                        # 重用已计算的 wrapped_lines，避免重复计算
                        start_char_in_line = 0
                        for i in range(wrap_idx):
                            start_char_in_line += len(wrapped_lines[i])
                        end_char_in_line = start_char_in_line + len(wrapped_text)
                        
                        # 计算选择范围在这一行的部分
                        if src_row == sel_start[0] and src_row == sel_end[0]:
                            # 同一行的选择
                            sel_start_char = max(start_char_in_line, sel_start[1])
                            sel_end_char = min(end_char_in_line, sel_end[1])
                            if sel_end_char > sel_start_char:
                                # 计算选择区域在当前显示行中的位置
                                text_before_sel = wrapped_text[:max(0, sel_start_char - start_char_in_line)]
                                selected_text = line_text[sel_start_char:sel_end_char]
                                sel_x = self._line_num_area_width + 5 + self._font_metrics.width(text_before_sel)
                                sel_w = self._font_metrics.width(selected_text)
                                painter.fillRect(sel_x, draw_y, sel_w, self._line_height, self._colors['selection'])
                        elif src_row == sel_start[0]:
                            # 选择开始行
                            sel_start_char = max(start_char_in_line, sel_start[1])
                            if sel_start_char < end_char_in_line:
                                text_before_sel = wrapped_text[:max(0, sel_start_char - start_char_in_line)]
                                selected_text = line_text[sel_start_char:end_char_in_line]
                                sel_x = self._line_num_area_width + 5 + self._font_metrics.width(text_before_sel)
                                sel_w = self._font_metrics.width(selected_text)
                                painter.fillRect(sel_x, draw_y, sel_w, self._line_height, self._colors['selection'])
                        elif src_row == sel_end[0]:
                            # 选择结束行
                            sel_end_char = min(end_char_in_line, sel_end[1])
                            if sel_end_char > start_char_in_line:
                                selected_text = line_text[start_char_in_line:sel_end_char]
                                sel_x = self._line_num_area_width + 5
                                sel_w = self._font_metrics.width(selected_text)
                                painter.fillRect(sel_x, draw_y, sel_w, self._line_height, self._colors['selection'])
                        elif sel_start[0] < src_row < sel_end[0]:
                            # 中间行，全选
                            sel_x = self._line_num_area_width + 5
                            sel_w = self._font_metrics.width(wrapped_text)
                            painter.fillRect(sel_x, draw_y, sel_w, self._line_height, self._colors['selection'])

                # --- 绘制左侧区域 (固定不动) ---
                painter.translate(-x_offset, 0)
                
                # A. 绘制时间戳 (只有第一行显示)
                if is_first_wrap_line and self._show_timestamp and src_row < len(self._line_timestamps):
                    ts = self._line_timestamps[src_row]
                    if ts > 0:
                        # 格式化时间 HH:MM:SS.mmm
                        dt = datetime.fromtimestamp(ts)
                        time_str = dt.strftime("%H:%M:%S") + f".{int(ts*1000)%1000:03d}"
                        
                        painter.setPen(self._colors['timestamp_text'])
                        # 左对齐显示在最左边
                        painter.drawText(5, draw_y, self._timestamp_width, self._line_height, 
                                         Qt.AlignLeft | Qt.AlignVCenter, time_str)

                # B. 绘制行号（第一行显示行号，后续行显示"-"）
                painter.setPen(self._colors['line_num_text'])
                if is_first_wrap_line:
                    # 第一行显示行号
                    line_num_str = str(src_row + 1)
                else:
                    # 换行显示"-"
                    line_num_str = "-"
                
                painter.drawText(0, draw_y, self._line_num_area_width - 5, self._line_height, 
                                 Qt.AlignRight | Qt.AlignVCenter, line_num_str)
                
                painter.translate(x_offset, 0)
                # --- 左侧绘制结束 ---

                # C. 绘制高亮和文本内容
                text_x = self._line_num_area_width + 5
                
                # 计算当前显示行在原始行中的字符偏移
                chars_per_line = self._get_chars_per_line()
                start_char_offset = wrap_idx * chars_per_line
                end_char_offset = min(start_char_offset + len(wrapped_text), len(line_text))
                
                # 获取原始行的完整文本用于匹配
                full_line_text = line_text
                
                # 绘制高亮背景
                if self._highlight_rules and full_line_text:
                    # 查找匹配位置（相对于原始行的位置）
                    matches = self._find_highlight_matches(full_line_text)
                    
                    for match_start, match_end, match_color in matches:
                        # 检查匹配是否在当前显示行范围内
                        if match_end <= start_char_offset or match_start >= end_char_offset:
                            continue
                        
                        # 计算在当前显示行中的位置
                        display_match_start = max(0, match_start - start_char_offset)
                        display_match_end = min(len(wrapped_text), match_end - start_char_offset)
                        
                        if display_match_end > display_match_start:
                            # 使用QFontMetrics计算实际文本宽度（正确处理全角/半角字符）
                            text_before_match = wrapped_text[:display_match_start]
                            matched_text = wrapped_text[display_match_start:display_match_end]
                            
                            # 计算匹配文本的起始X位置和宽度
                            highlight_x = text_x + self._font_metrics.width(text_before_match)
                            highlight_w = self._font_metrics.width(matched_text)
                            
                            painter.fillRect(highlight_x, draw_y, highlight_w, self._line_height, match_color)
                
                # 绘制文本内容（在高亮背景之上）
                painter.setPen(self._colors['text'])
                painter.drawText(text_x, draw_y, 
                                 viewport_w, self._line_height, 
                                 Qt.AlignLeft | Qt.AlignVCenter, wrapped_text)
            
            current_display_row += display_count
            if current_display_row >= last_display_row:
                break

    # _paint_hex_stream 保持不变，但需要适配 _line_num_area_width 的变化
    def _paint_hex_stream(self, painter, x_offset):
        viewport_h = self.viewport().height()
        first_row_idx = self.verticalScrollBar().value()
        rows_visible = math.ceil(viewport_h / self._line_height) + 1
        total_bytes = len(self._raw_bytes)
        max_rows = math.ceil(total_bytes / self._bytes_per_line)
        last_row_idx = min(first_row_idx + rows_visible, max_rows)
        
        # 布局计算
        w_char = self._char_width
        # Hex模式下，左侧固定区域只显示地址，我们忽略 timestamp (或者你可以选择显示第一字节的时间)
        # 这里为了整洁，Hex模式下我们使用独立的布局计算，或者复用 line_num_area_width
        
        # 策略：Hex模式下通常不需要每行显示时间戳，只显示地址偏移
        # 所以这里我们手动覆盖 x_addr_end，不使用 self._line_num_area_width，
        # 除非你想在Hex模式也显示时间（通常不需要）
        x_addr_end = 10 * w_char + 20 
        
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
            
            painter.translate(-x_offset, 0)
            painter.setPen(self._colors['offset_text'])
            painter.drawText(0, draw_y, x_addr_end - 5, self._line_height, 
                             Qt.AlignRight | Qt.AlignVCenter, f"{start_byte:08X}")
            painter.translate(x_offset, 0)
            
            hex_parts = [f"{b:02X}" for b in chunk]
            painter.setPen(self._colors['hex_text'])
            painter.drawText(x_hex_start, draw_y, x_hex_end, self._line_height,
                             Qt.AlignLeft | Qt.AlignVCenter, " ".join(hex_parts))
            
            ascii_parts = [chr(b) if 32 <= b <= 126 else "." for b in chunk]
            painter.setPen(self._colors['text'])
            painter.drawText(x_ascii_start, draw_y, 10000, self._line_height,
                             Qt.AlignLeft | Qt.AlignVCenter, "".join(ascii_parts))

    # ===========================
    # 辅助与设置
    # ===========================
    def set_encoding(self, encoding: str):
        """设置字符编码"""
        self._encoding = encoding.lower()
    
    def set_highlight_rules(self, rules):
        """
        设置高亮规则
        
        Args:
            rules: 规则列表，每个规则为字典，格式：
                {
                    'keyword': str,      # 关键字
                    'use_regex': bool,   # 是否使用正则表达式
                    'color': str         # 颜色（如 '#FFFF00'）
                }
        """
        self._highlight_rules = rules if rules else []
        self.viewport().update()
    
    def clear_highlight_rules(self):
        """清空所有高亮规则"""
        self._highlight_rules = []
        self.viewport().update()
    
    def _find_highlight_matches(self, text):
        """
        查找文本中的所有高亮匹配位置
        
        Returns:
            list: 匹配位置列表，每个元素为 (start, end, color)
        """
        matches = []
        if not text or not self._highlight_rules:
            return matches
        
        for rule in self._highlight_rules:
            keyword = rule.get('keyword', '')
            if not keyword:
                continue
            
            use_regex = rule.get('use_regex', False)
            color = QColor(rule.get('color', '#FFFF00'))
            if not color.isValid():
                color = QColor('#FFFF00')
            
            try:
                if use_regex:
                    # 使用正则表达式
                    pattern = re.compile(keyword)
                    for match in pattern.finditer(text):
                        matches.append((match.start(), match.end(), color))
                else:
                    # 普通字符串匹配
                    start = 0
                    while True:
                        pos = text.find(keyword, start)
                        if pos == -1:
                            break
                        matches.append((pos, pos + len(keyword), color))
                        start = pos + 1
            except (re.error, Exception):
                # 如果正则表达式错误，跳过这条规则
                continue
        
        # 按位置排序
        matches.sort(key=lambda x: x[0])
        return matches
    
    def _line_matches_filter(self, line_text):
        """
        检查行是否匹配过滤条件
        
        Args:
            line_text: 行文本
            
        Returns:
            bool: 如果启用过滤且模式存在，返回是否匹配；否则返回 True
        """
        if not self._filter_enabled or not self._filter_pattern:
            return True
        
        try:
            return bool(self._filter_pattern.search(line_text))
        except (re.error, Exception):
            # 如果正则表达式错误，显示所有行
            return True
    
    def set_filter_pattern(self, pattern_str):
        """
        设置过滤正则表达式模式
        
        Args:
            pattern_str: 正则表达式字符串，如果为空则清除过滤
        """
        self._filter_regex_str = pattern_str
        if pattern_str:
            try:
                self._filter_pattern = re.compile(pattern_str)
            except re.error:
                # 如果正则表达式无效，清除模式
                self._filter_pattern = None
        else:
            self._filter_pattern = None
        
        # 清除换行缓存，因为过滤可能改变显示的行
        self._clear_wrapped_cache()
        self._update_scrollbars()
        self.viewport().update()
    
    def set_filter_enabled(self, enabled):
        """
        启用或禁用过滤功能
        
        Args:
            enabled: 是否启用过滤
        """
        self._filter_enabled = enabled
        # 清除换行缓存，因为过滤可能改变显示的行
        self._clear_wrapped_cache()
        self._update_scrollbars()
        self.viewport().update()

    def set_font_family(self, family: str):
        self._font.setFamily(family)
        self._clear_wrapped_cache()  # 字体改变时清除缓存
        self._update_metrics()

    def set_font_size(self, size: int):
        self._font.setPointSize(size)
        self._clear_wrapped_cache()  # 字体改变时清除缓存
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

    def _update_scrollbars(self):
        viewport_h = self.viewport().height()
        line_h = max(1, self._line_height)
        rows_per_page = viewport_h // line_h
        
        if self._view_mode == ViewMode.HEX_STREAM:
            total_rows = math.ceil(len(self._raw_bytes) / self._bytes_per_line)
            chars = 12 + (self._bytes_per_line * 3) + 3 + self._bytes_per_line
            content_width = chars * self._char_width + 40 # Hex模式简易宽
        else:
            # Text模式：使用显示行数（考虑换行）
            total_rows = self._get_total_display_lines()
            # 文本模式下，由于自动换行，不需要水平滚动条
            content_width = self.viewport().width()
            
        v_max = max(0, total_rows - rows_per_page)
        self.verticalScrollBar().setRange(0, v_max)
        self.verticalScrollBar().setPageStep(rows_per_page)
        
        # 文本模式下禁用水平滚动条（因为自动换行）
        if self._view_mode == ViewMode.TEXT_ONLY:
            self.horizontalScrollBar().setRange(0, 0)
            self.horizontalScrollBar().setPageStep(self.viewport().width())
        else:
            h_max = max(0, content_width - self.viewport().width())
            self.horizontalScrollBar().setRange(0, int(h_max))
            self.horizontalScrollBar().setPageStep(self.viewport().width())

    def clear(self):
        self._lines = []
        self._line_timestamps = [] # 清空时间戳
        self._raw_bytes = b""
        self._sel_start_pos = None
        self._sel_end_pos = None
        self._clear_wrapped_cache()  # 清除换行缓存
        self._update_metrics() # 重置宽度
        self._update_scrollbars()
        self.viewport().update()
        
    def set_content(self, text: str):
        self._lines = text.splitlines()
        # 对于批量设置的内容，时间戳统一设为当前时间，或者 0
        now = time.time()
        self._line_timestamps = [now] * len(self._lines)
        self._raw_bytes = text.encode(self._encoding, errors='replace')
        self._clear_wrapped_cache()  # 清除换行缓存
        self._update_metrics()
        self._update_scrollbars()
        self.viewport().update()

    # (其他鼠标、选择、复制逻辑保持不变，省略以节省空间)
    # ... 必须保留 mousePressEvent, mouseMoveEvent, mouseReleaseEvent, keyPressEvent, _map_point_to_pos, copy_selection 等
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
        
        # 计算显示行号
        display_row = self.verticalScrollBar().value() + (y // self._line_height)
        
        # 将显示行映射到原始行和列（考虑过滤）
        src_row, base_col = self._display_row_to_source_row_col(display_row)
        
        if 0 <= src_row < len(self._lines):
            # 确保该行匹配过滤（应该总是匹配，因为 _display_row_to_source_row_col 已经处理了）
            if not self._line_matches_filter(self._lines[src_row]):
                # 如果不匹配，返回行首
                return (src_row, 0)
            
            line_text = self._lines[src_row]
            wrapped_lines = self._get_wrapped_lines(line_text, line_idx=src_row, use_cache=True)
            
            # 找到该显示行在原始行中的起始位置（考虑过滤）
            current_display = 0
            for i in range(src_row):
                if self._line_matches_filter(self._lines[i]):
                    current_display += self._get_display_line_count(i)
            local_display = display_row - current_display
            
            if 0 <= local_display < len(wrapped_lines):
                # 获取当前显示行的文本
                wrapped_text = wrapped_lines[local_display]
                
                # 减去行号区域(包含时间戳)
                rel_x = x - self._line_num_area_width - 5
                
                # 使用实际宽度找到鼠标位置对应的字符索引
                col_offset = 0
                current_width = 0
                for i, char in enumerate(wrapped_text):
                    char_width = self._font_metrics.width(char)
                    if current_width + char_width / 2 > rel_x:
                        # 鼠标在当前位置的字符上，选择该字符
                        col_offset = i
                        break
                    current_width += char_width
                    col_offset = i + 1
                
                # 计算原始行中的列号
                base_col = 0
                for i in range(local_display):
                    base_col += len(wrapped_lines[i])
                col = base_col + col_offset
            else:
                # 超出范围，返回行尾或行首
                col = len(line_text) if local_display >= len(wrapped_lines) else 0
        else:
            col = 0
        
        if 0 <= src_row < len(self._lines):
            col = min(col, len(self._lines[src_row]))
            col = max(0, col)
        
        return (src_row, col)

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
        
    def set_auto_scroll(self, enabled: bool):
        self._auto_scroll = enabled
        if enabled: self.scroll_to_bottom()

    def scroll_to_bottom(self):
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())
        
    def set_view_mode(self, mode: ViewMode):
        self._view_mode = mode
        self._update_scrollbars()
        self.viewport().update()

    def goto_line(self, line_no):
        """跳转到指定行（原始行号）"""
        line_idx = line_no - 1
        if 0 <= line_idx < len(self._lines):
            self._current_line_index = line_idx
            # 将原始行号转换为显示行号
            display_row = self._source_row_col_to_display_row(line_idx, 0)
            self.verticalScrollBar().setValue(display_row)
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
        
        self._clear_wrapped_cache()  # 字体改变时清除缓存
        self.viewport().setStyleSheet(f"background-color: {self._bg_color.name()};")
        self.setFont(self._font)
        self._update_metrics()  # 使用 _update_metrics 而不是直接调用 _update_scrollbars
        self.viewport().update()

    def scroll_to_bottom(self):
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())

    # 返回缓存的数据
    def get_cached_data(self):
        return self._raw_bytes.decode(self._encoding, errors='replace')
# ===========================
# Demo
# ===========================
class DemoWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("超级日志控件 - 包含时间戳")
        self.resize(1200, 800)
        
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        
        # --- 控制栏 ---
        ctrl_layout = QHBoxLayout()
        
        self.check_timestamp = QCheckBox("显示时间戳 (Show Timestamp)")
        self.check_timestamp.stateChanged.connect(lambda s: self.text_viewer.set_show_timestamp(s == Qt.Checked))
        
        self.btn_add = QPushButton("模拟接收日志")
        self.btn_add.clicked.connect(self.add_log)
        
        ctrl_layout.addWidget(self.check_timestamp)
        ctrl_layout.addWidget(self.btn_add)
        ctrl_layout.addStretch()
        
        main_layout.addLayout(ctrl_layout)
        
        self.text_viewer = HugeTextWidget()
        main_layout.addWidget(self.text_viewer)
        
        self.text_viewer.set_content("System Init...\nWaiting for data...\n")

    def add_log(self):
        # 模拟不同时刻收到的数据
        import time
        t_str = f"Data received at {time.time()}\n"
        self.text_viewer.append_raw_bytes(t_str.encode('utf-8'))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = DemoWindow()
    win.show()
    sys.exit(app.exec_())