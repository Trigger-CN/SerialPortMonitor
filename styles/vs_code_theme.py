from PyQt5.QtGui import QPalette, QColor
from PyQt5.QtCore import Qt

class VSCodeTheme:
    """VSCode深色主题配色方案"""
    
    # 颜色定义
    BACKGROUND = "#1e1e1e"
    BACKGROUND_LIGHT = "#252526"
    BACKGROUND_LIGHTER = "#2d2d30"
    FOREGROUND = "#cccccc"
    FOREGROUND_DARK = "#858585"
    ACCENT = "#007acc"
    ACCENT_HOVER = "#005a9e"
    GREEN = "#4EC9B0"
    YELLOW = "#DCDCAA"
    ORANGE = "#CE9178"
    RED = "#F44747"
    PURPLE = "#C586C0"
    BLUE = "#569CD6"
    
    # 字体
    FONT_FAMILY = "Consolas, 'Courier New', monospace"
    
    @staticmethod
    def apply_theme(app):
        """应用深色主题到整个应用"""
        app.setStyle("Fusion")
        
        dark_palette = QPalette()
        dark_palette.setColor(QPalette.Window, QColor(VSCodeTheme.BACKGROUND))
        dark_palette.setColor(QPalette.WindowText, QColor(VSCodeTheme.FOREGROUND))
        dark_palette.setColor(QPalette.Base, QColor(VSCodeTheme.BACKGROUND_LIGHT))
        dark_palette.setColor(QPalette.AlternateBase, QColor(VSCodeTheme.BACKGROUND))
        dark_palette.setColor(QPalette.ToolTipBase, QColor(VSCodeTheme.BACKGROUND_LIGHT))
        dark_palette.setColor(QPalette.ToolTipText, QColor(VSCodeTheme.FOREGROUND))
        dark_palette.setColor(QPalette.Text, QColor(VSCodeTheme.FOREGROUND))
        dark_palette.setColor(QPalette.Button, QColor(VSCodeTheme.BACKGROUND_LIGHT))
        dark_palette.setColor(QPalette.ButtonText, QColor(VSCodeTheme.FOREGROUND))
        dark_palette.setColor(QPalette.BrightText, Qt.red)
        dark_palette.setColor(QPalette.Link, QColor(VSCodeTheme.ACCENT))
        dark_palette.setColor(QPalette.Highlight, QColor(VSCodeTheme.ACCENT))
        dark_palette.setColor(QPalette.HighlightedText, Qt.white)
        
        app.setPalette(dark_palette)
        
        # 全局样式表
        app.setStyleSheet(f"""
            QMainWindow {{
                background-color: {VSCodeTheme.BACKGROUND};
                color: {VSCodeTheme.FOREGROUND};
            }}
            QStatusBar {{
                background-color: {VSCodeTheme.BACKGROUND_LIGHT};
                color: {VSCodeTheme.FOREGROUND};
                border-top: 1px solid {VSCodeTheme.BACKGROUND_LIGHTER};
            }}
        """)