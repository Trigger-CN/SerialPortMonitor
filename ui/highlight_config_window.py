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
    
    def __init__(self, index, parent=None):
        super().__init__(parent)
        self.index = index
        self.color = QColor("#19277f")  # 默认黄色
        self.init_ui()
    
    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # 序号标签
        label = QLabel(f"{self.index + 1}.")
        label.setFixedWidth(30)
        label.setStyleSheet(f"color: {VSCodeTheme.FOREGROUND};")
        layout.addWidget(label)
        
        # 关键字输入
        self.keyword_input = StyledLineEdit()
        self.keyword_input.setPlaceholderText("keyword (regex supported)")
        layout.addWidget(self.keyword_input, 2)
        
        # 正则表达式复选框
        self.regex_checkbox = StyledCheckBox("Regex")
        layout.addWidget(self.regex_checkbox)
        
        # 颜色按钮
        self.color_btn = QPushButton()
        self.color_btn.setFixedSize(40, 30)
        self.update_color_button()
        self.color_btn.clicked.connect(self.pick_color)
        layout.addWidget(self.color_btn)
        
        # 删除按钮
        self.delete_btn = StyledButton("Delete")
        self.delete_btn.setFixedWidth(50)
        layout.addWidget(self.delete_btn)
    
    def pick_color(self):
        color = QColorDialog.getColor(self.color, self, "Select Highlight Color")
        if color.isValid():
            self.color = color
            self.update_color_button()
    
    def update_color_button(self):
        """更新颜色按钮样式"""
        self.color_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.color.name()};
                border: 2px solid {VSCodeTheme.BACKGROUND_LIGHTER};
                border-radius: 4px;
            }}
            QPushButton:hover {{
                border: 2px solid {VSCodeTheme.ACCENT};
            }}
        """)
    
    def get_rule(self):
        """获取规则数据"""
        keyword = self.keyword_input.text().strip()
        if not keyword:
            return None
        return {
            'keyword': keyword,
            'use_regex': self.regex_checkbox.isChecked(),
            'color': self.color.name()
        }
    
    def set_rule(self, rule):
        """设置规则数据"""
        if rule:
            self.keyword_input.setText(rule.get('keyword', ''))
            self.regex_checkbox.setChecked(rule.get('use_regex', False))
            color_name = rule.get('color', '#19277f')
            self.color = QColor(color_name)
            if not self.color.isValid():
                self.color = QColor("#19277f")
            self.update_color_button()


class HighlightConfigWindow(QDialog):
    """高亮配置窗口"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Highlight Configuration")
        self.resize(700, 600)
        self.rule_widgets = []
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # 标题和说明
        title_label = QLabel("Configure highlight rules")
        title_label.setStyleSheet(f"color: {VSCodeTheme.FOREGROUND}; font-size: 14px; font-weight: bold;")
        layout.addWidget(title_label)
        
        info_label = QLabel("Tip: Check 'Regex' to use regular expressions")
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
        self.scroll_layout.addStretch()
        
        scroll_area.setWidget(scroll_widget)
        layout.addWidget(scroll_area)
        
        # 添加规则按钮
        add_btn_layout = QHBoxLayout()
        add_btn_layout.addStretch()
        self.add_rule_btn = StyledButton("Add Rule")
        self.add_rule_btn.clicked.connect(self.add_rule)
        add_btn_layout.addWidget(self.add_rule_btn)
        add_btn_layout.addStretch()
        layout.addLayout(add_btn_layout)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.apply_btn = StyledButton("Apply")
        self.apply_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.apply_btn)
        
        self.cancel_btn = StyledButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        
        for i in range(10):
            self.add_rule_widget(i)
    
    def add_rule_widget(self, index):
        """添加规则控件"""
        rule_widget = HighlightRuleWidget(index, self)
        rule_widget.delete_btn.clicked.connect(lambda checked, idx=index: self.remove_rule(idx))
        self.rule_widgets.append(rule_widget)
        self.scroll_layout.insertWidget(index, rule_widget)
    
    def add_rule(self):
        """添加新规则（如果有空槽位）"""
        # 检查是否有空的规则
        for widget in self.rule_widgets:
            if not widget.get_rule():
                widget.keyword_input.setFocus()
                return
        QMessageBox.information(self, "Info", "Maximum 10 rules allowed")
    
    def remove_rule(self, index):
        """删除规则"""
        if 0 <= index < len(self.rule_widgets):
            widget = self.rule_widgets[index]
            widget.keyword_input.clear()
            widget.regex_checkbox.setChecked(False)
            widget.color = QColor("#FFFF00")
            widget.update_color_button()
    
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
        for i, rule in enumerate(rules):
            if i < len(self.rule_widgets):
                self.rule_widgets[i].set_rule(rule)
