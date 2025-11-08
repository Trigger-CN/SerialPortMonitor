import sys
from PyQt5.QtWidgets import QApplication
from ui.main_window import MainWindow
from styles.vs_code_theme import VSCodeTheme

def main():
    """程序主入口"""
    app = QApplication(sys.argv)
    app.setApplicationName("串口监看工具 - VSCode风格")
    
    # 应用VSCode风格主题
    VSCodeTheme.apply_theme(app)
    
    # 创建并显示主窗口
    monitor = MainWindow()
    monitor.show()
    
    # 运行应用
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()