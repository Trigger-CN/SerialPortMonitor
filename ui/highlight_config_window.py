# highlight_config_window.py

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QLineEdit, QCheckBox, QColorDialog,
                             QScrollArea, QWidget, QMessageBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from ui.widgets import StyledButton, StyledLineEdit, StyledCheckBox, StyledGroupBox
from styles.vs_code_theme import VSCodeTheme


class HighlightRuleWidget(QWidget):
    """单个高亮规则控件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # 默认背景色使用全局背景色
        self.bg_color = QColor(VSCodeTheme.BACKGROUND)
        self.text_color = None  # 默认字体颜色（None表示使用默认文本颜色）
        self.index_label = None  # 序号标签引用
        self.init_ui()
    
    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # 序号标签
        self.index_label = QLabel("1.")
        self.index_label.setFixedWidth(30)
        self.index_label.setStyleSheet(f"color: {VSCodeTheme.FOREGROUND};")
        layout.addWidget(self.index_label)
        
        # 关键字输入
        self.keyword_input = StyledLineEdit()
        self.keyword_input.setPlaceholderText("keyword (regex supported)")
        layout.addWidget(self.keyword_input, 2)
        
        # 正则表达式复选框
        self.regex_checkbox = StyledCheckBox("Regex")
        layout.addWidget(self.regex_checkbox)
        
        # 字体颜色按钮
        text_color_label = QLabel("字体:")
        text_color_label.setStyleSheet(f"color: {VSCodeTheme.FOREGROUND};")
        text_color_label.setFixedWidth(35)
        layout.addWidget(text_color_label)
        
        self.text_color_btn = QPushButton()
        self.text_color_btn.setFixedSize(40, 30)
        self.text_color_btn.setToolTip("点击选择字体颜色（留空使用默认颜色）")
        self.update_text_color_button()
        self.text_color_btn.clicked.connect(self.pick_text_color)
        layout.addWidget(self.text_color_btn)
        
        # 背景颜色按钮
        bg_color_label = QLabel("背景:")
        bg_color_label.setStyleSheet(f"color: {VSCodeTheme.FOREGROUND};")
        bg_color_label.setFixedWidth(35)
        layout.addWidget(bg_color_label)
        
        self.bg_color_btn = QPushButton()
        self.bg_color_btn.setFixedSize(40, 30)
        self.bg_color_btn.setToolTip("点击选择背景颜色")
        self.update_bg_color_button()
        self.bg_color_btn.clicked.connect(self.pick_bg_color)
        layout.addWidget(self.bg_color_btn)
        
        # 删除按钮
        self.delete_btn = StyledButton("删除")
        self.delete_btn.setFixedWidth(50)
        layout.addWidget(self.delete_btn)
    
    def update_index(self, index):
        """更新序号标签"""
        if self.index_label:
            self.index_label.setText(f"{index + 1}.")
    
    def pick_text_color(self):
        """选择字体颜色"""
        initial_color = self.text_color if self.text_color else QColor(VSCodeTheme.FOREGROUND)
        color = QColorDialog.getColor(initial_color, self, "选择字体颜色")
        if color.isValid():
            self.text_color = color
            self.update_text_color_button()
        else:
            # 如果用户取消，可以选择清除颜色（使用默认）
            pass
    
    def pick_bg_color(self):
        """选择背景颜色"""
        color = QColorDialog.getColor(self.bg_color, self, "选择背景颜色")
        if color.isValid():
            self.bg_color = color
            self.update_bg_color_button()
    
    def update_text_color_button(self):
        """更新字体颜色按钮样式"""
        if self.text_color:
            color_name = self.text_color.name()
            display_text = "A"
        else:
            color_name = VSCodeTheme.FOREGROUND
            display_text = "默认"
        
        self.text_color_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {color_name};
                color: {'white' if self._is_dark_color(self.text_color if self.text_color else QColor(color_name)) else 'black'};
                border: 2px solid {VSCodeTheme.BACKGROUND_LIGHTER};
                border-radius: 4px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                border: 2px solid {VSCodeTheme.ACCENT};
            }}
        """)
        self.text_color_btn.setText(display_text)
    
    def update_bg_color_button(self):
        """更新背景颜色按钮样式"""
        self.bg_color_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.bg_color.name()};
                border: 2px solid {VSCodeTheme.BACKGROUND_LIGHTER};
                border-radius: 4px;
            }}
            QPushButton:hover {{
                border: 2px solid {VSCodeTheme.ACCENT};
            }}
        """)
    
    def _is_dark_color(self, color):
        """判断颜色是否为深色"""
        if not color:
            return True
        # 计算亮度
        brightness = (color.red() * 299 + color.green() * 587 + color.blue() * 114) / 1000
        return brightness < 128
    
    def get_rule(self):
        """获取规则数据"""
        keyword = self.keyword_input.text().strip()
        if not keyword:
            return None
        rule = {
            'keyword': keyword,
            'use_regex': self.regex_checkbox.isChecked()
        }
        # 如果设置了背景颜色且不是全局背景色，添加到规则中
        if self.bg_color and self.bg_color.name().upper() != VSCodeTheme.BACKGROUND.upper():
            rule['bg_color'] = self.bg_color.name()
        # 如果设置了字体颜色，添加到规则中
        if self.text_color:
            rule['text_color'] = self.text_color.name()
        return rule
    
    def set_rule(self, rule):
        """设置规则数据"""
        if rule:
            self.keyword_input.setText(rule.get('keyword', ''))
            self.regex_checkbox.setChecked(rule.get('use_regex', False))
            
            # 设置背景颜色（可选）
            bg_color_name = rule.get('bg_color', rule.get('color'))  # 兼容旧格式
            if bg_color_name:
                self.bg_color = QColor(bg_color_name)
                if not self.bg_color.isValid():
                    self.bg_color = QColor(VSCodeTheme.BACKGROUND)  # 使用全局背景色
            else:
                self.bg_color = QColor(VSCodeTheme.BACKGROUND)  # 默认使用全局背景色
            self.update_bg_color_button()
            
            # 设置字体颜色
            text_color_name = rule.get('text_color')
            if text_color_name:
                self.text_color = QColor(text_color_name)
                if not self.text_color.isValid():
                    self.text_color = None
            else:
                self.text_color = None
            self.update_text_color_button()


class HighlightConfigWindow(QDialog):
    """高亮配置窗口"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("高亮配置")
        self.resize(800, 600)
        self.rule_widgets = []
        self.init_ui()
        # 不在初始化时添加默认规则，由 set_rules 统一处理
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # 标题和说明
        title_label = QLabel("配置高亮规则")
        title_label.setStyleSheet(f"color: {VSCodeTheme.FOREGROUND}; font-size: 14px; font-weight: bold;")
        layout.addWidget(title_label)
        
        info_label = QLabel("提示: 勾选 'Regex' 可使用正则表达式。可以设置字体颜色和背景颜色。")
        info_label.setStyleSheet(f"color: {VSCodeTheme.FOREGROUND_DARK}; font-size: 11px;")
        layout.addWidget(info_label)
        
        # 滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet(f"""
            QScrollArea {{
                border: 1px solid {VSCodeTheme.BACKGROUND_LIGHTER};
                border-radius: 5px;
                background-color: {VSCodeTheme.BACKGROUND};
            }}
        """)
        
        scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(scroll_widget)
        self.scroll_layout.setSpacing(5)
        self.scroll_layout.setContentsMargins(10, 10, 10, 10)
        # 不在这里添加stretch，在add_rule_widget中动态管理
        
        scroll_area.setWidget(scroll_widget)
        layout.addWidget(scroll_area)
        
        # 所有按钮区域（一行）
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        # 全部高亮使能按钮
        self.enable_highlight_btn = StyledButton("启用全部高亮")
        self.enable_highlight_btn.setCheckable(True)
        self.enable_highlight_btn.setChecked(True)  # 默认启用
        self.enable_highlight_btn.toggled.connect(self.on_highlight_enabled_changed)
        button_layout.addWidget(self.enable_highlight_btn)
        
        # 添加规则按钮
        self.add_rule_btn = StyledButton("添加规则")
        self.add_rule_btn.clicked.connect(self.add_rule)
        button_layout.addWidget(self.add_rule_btn)
        
        # 重置为默认按钮
        self.reset_default_btn = StyledButton("重置为默认")
        self.reset_default_btn.clicked.connect(self.reset_to_default)
        button_layout.addWidget(self.reset_default_btn)
        
        button_layout.addStretch()
        
        # 应用按钮
        self.apply_btn = StyledButton("应用")
        self.apply_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.apply_btn)
        
        # 取消按钮
        self.cancel_btn = StyledButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
    
    def add_rule_widget(self, rule=None):
        """动态添加规则控件"""
        # 确保stretch在最后
        self._ensure_stretch_at_end()
        
        # 在stretch之前插入
        index = len(self.rule_widgets)
        rule_widget = HighlightRuleWidget(self)
        rule_widget.update_index(index)
        rule_widget.delete_btn.clicked.connect(lambda checked, widget=rule_widget: self.remove_rule_widget(widget))
        
        # 插入到stretch之前
        self.scroll_layout.insertWidget(index, rule_widget)
        self.rule_widgets.append(rule_widget)
        
        # 如果有规则数据，设置它
        if rule:
            rule_widget.set_rule(rule)
        
        # 更新所有序号
        self._update_all_indices()
        
        return rule_widget
    
    def _ensure_stretch_at_end(self):
        """确保stretch在布局的最后"""
        # 检查最后一项是否是stretch
        count = self.scroll_layout.count()
        if count == 0:
            # 如果没有项目，添加stretch
            self.scroll_layout.addStretch()
        else:
            # 检查最后一项
            last_item = self.scroll_layout.itemAt(count - 1)
            if last_item and last_item.spacerItem() is None:
                # 最后一项不是stretch，添加一个
                self.scroll_layout.addStretch()
    
    def add_rule(self):
        """添加新规则"""
        # 动态添加新规则控件
        new_widget = self.add_rule_widget()
        # 聚焦到新添加的关键字输入框
        new_widget.keyword_input.setFocus()
    
    def _add_default_rules_if_empty(self):
        """如果没有现有规则，添加默认高亮词条"""
        if len(self.rule_widgets) == 0:
            self.add_default_rules()
    
    def add_default_rules(self, clear_existing=False):
        """添加默认高亮规则
        
        Args:
            clear_existing: 是否清除现有规则（用于按钮点击时）
        """
        # 如果是从按钮点击，清除现有规则
        if clear_existing:
            self._clear_all_rules()
        
        # 检查是否已有默认规则，避免重复添加
        existing_keywords = set()
        for widget in self.rule_widgets:
            rule = widget.get_rule()
            if rule:
                existing_keywords.add(rule.get('keyword', ''))
        
        default_rules = [
            {
                'keyword': r'(?i)\berror\b',  # 忽略大小写
                'use_regex': True,
                'text_color': '#F4684C'  # 浅红色文字，无背景
            },
            {
                'keyword': r'(?i)\bwarn(ing)?\b',  # 忽略大小写
                'use_regex': True,
                'text_color': '#DCDCAA'  # 浅黄色文字，无背景
            },
            {
                'keyword': r'(?i)\binfo\b',  # 忽略大小写
                'use_regex': True,
                'text_color': '#4EC9B0'  # 青色文字，无背景
            },
            {
                'keyword': r'(?i)\bdebug\b',  # 忽略大小写
                'use_regex': True,
                'text_color': '#CE9178'  # 橙色文字，无背景
            },
            {
                'keyword': r'(?i)\bsuccess\b',  # 忽略大小写
                'use_regex': True,
                'text_color': '#4EC9B0'  # 青色文字，无背景
            }
        ]
        
        # 只添加不存在的默认规则
        for rule in default_rules:
            keyword = rule.get('keyword', '')
            if keyword not in existing_keywords:
                self.add_rule_widget(rule)
    
    def remove_rule_widget(self, widget):
        """删除规则控件"""
        if widget in self.rule_widgets:
            # 从布局中移除
            self.scroll_layout.removeWidget(widget)
            # 从列表中移除
            self.rule_widgets.remove(widget)
            # 删除控件
            widget.deleteLater()
            # 更新所有序号
            self._update_all_indices()
            # 确保stretch在最后
            self._ensure_stretch_at_end()
    
    def _update_all_indices(self):
        """更新所有规则控件的序号"""
        for index, widget in enumerate(self.rule_widgets):
            widget.update_index(index)
    
    def get_rules(self):
        """获取所有规则"""
        rules = []
        for widget in self.rule_widgets:
            rule = widget.get_rule()
            if rule:
                rules.append(rule)
        return rules
    
    def set_rules(self, rules):
        """设置规则"""
        # 清除所有现有规则控件
        self._clear_all_rules()
        
        # 动态添加规则控件
        if rules:
            for rule in rules:
                # 验证规则数据有效性
                if isinstance(rule, dict) and rule.get('keyword'):
                    self.add_rule_widget(rule)
        else:
            # 如果没有规则，添加默认规则
            self._add_default_rules_if_empty()
    
    def _clear_all_rules(self):
        """清除所有规则控件"""
        # 先断开所有信号连接，避免点击残留控件时出错
        for widget in self.rule_widgets[:]:  # 使用切片复制列表，避免迭代时修改
            try:
                widget.delete_btn.clicked.disconnect()
            except:
                pass
            self.scroll_layout.removeWidget(widget)
            widget.deleteLater()
        # 清空列表
        self.rule_widgets.clear()
        # 移除所有布局项（包括stretch）
        while self.scroll_layout.count() > 0:
            item = self.scroll_layout.takeAt(0)
            if item:
                if item.widget():
                    # 如果是控件，删除它
                    item.widget().deleteLater()
                # 对于stretch（spacerItem），takeAt已经移除了，不需要额外操作
                # 删除布局项引用
                del item
    
    def on_highlight_enabled_changed(self, enabled):
        """高亮使能状态改变"""
        if enabled:
            self.enable_highlight_btn.setText("启用全部高亮")
            self.enable_highlight_btn.set_checked_style()
        else:
            self.enable_highlight_btn.setText("禁用全部高亮")
            self.enable_highlight_btn.set_default_style()
    
    def is_highlight_enabled(self):
        """获取高亮使能状态"""
        return self.enable_highlight_btn.isChecked()
    
    def set_highlight_enabled(self, enabled):
        """设置高亮使能状态"""
        self.enable_highlight_btn.setChecked(enabled)
        self.on_highlight_enabled_changed(enabled)
    
    def reset_to_default(self):
        """重置全部高亮为默认"""
        reply = QMessageBox.question(
            self, 
            "确认重置", 
            "确定要重置所有高亮规则为默认值吗？这将清除所有现有规则。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # 清除所有规则控件
            self._clear_all_rules()
            
            # 添加默认规则
            self.add_default_rules()
            
            # 确保高亮是启用的
            self.set_highlight_enabled(True)
            
            QMessageBox.information(self, "提示", "已重置为默认高亮规则")
