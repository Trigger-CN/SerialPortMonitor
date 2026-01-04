# update_dialog.py

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTextEdit, QMessageBox)
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QDesktopServices
from styles.vs_code_theme import VSCodeTheme
from ui.widgets import StyledButton
import version


class UpdateDialog(QDialog):
    """更新对话框"""
    
    def __init__(self, latest_version: str, download_url: str, release_notes: str, parent=None):
        super().__init__(parent)
        self.latest_version = latest_version
        self.download_url = download_url
        self.release_notes = release_notes
        self.current_version = version.get_version()
        
        self.setWindowTitle("🔄 检查更新")
        self.resize(500, 400)
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 标题
        title_label = QLabel("发现新版本！")
        title_label.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {VSCodeTheme.BLUE};")
        layout.addWidget(title_label)
        
        # 版本信息
        version_layout = QVBoxLayout()
        current_version_label = QLabel(f"当前版本: v{self.current_version}")
        current_version_label.setStyleSheet(f"color: {VSCodeTheme.FOREGROUND};")
        version_layout.addWidget(current_version_label)
        
        latest_version_label = QLabel(f"最新版本: v{self.latest_version}")
        latest_version_label.setStyleSheet(f"color: {VSCodeTheme.GREEN}; font-weight: bold;")
        version_layout.addWidget(latest_version_label)
        layout.addLayout(version_layout)
        
        # 更新说明
        notes_label = QLabel("更新说明:")
        notes_label.setStyleSheet(f"color: {VSCodeTheme.FOREGROUND}; font-weight: bold;")
        layout.addWidget(notes_label)
        
        notes_text = QTextEdit()
        notes_text.setReadOnly(True)
        notes_text.setPlainText(self.release_notes)
        notes_text.setStyleSheet(f"""
            background-color: {VSCodeTheme.BACKGROUND_LIGHT};
            color: {VSCodeTheme.FOREGROUND};
            border: 1px solid {VSCodeTheme.BACKGROUND_LIGHTER};
            border-radius: 4px;
            padding: 8px;
        """)
        notes_text.setMaximumHeight(150)
        layout.addWidget(notes_text)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        
        self.download_btn = StyledButton("⬇️ 前往下载")
        self.download_btn.clicked.connect(self.open_download_page)
        button_layout.addWidget(self.download_btn)
        
        self.close_btn = StyledButton("❌ 关闭")
        self.close_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
    
    def open_download_page(self):
        """打开下载页面"""
        if self.download_url:
            QDesktopServices.openUrl(QUrl(self.download_url))
        else:
            # 如果没有下载链接，打开 releases 页面
            releases_url = version.get_github_url() + "/releases/latest"
            QDesktopServices.openUrl(QUrl(releases_url))
        self.accept()

