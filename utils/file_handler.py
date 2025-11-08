# file_handler.py

from datetime import datetime
import os
from PyQt5.QtWidgets import QFileDialog

class FileHandler:
    """文件处理工具类"""
    
    @staticmethod
    def save_log(port_name: str, data: str, log_path: str = None) -> str:
        """保存日志文件"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"{port_name}_{timestamp}.log"
        
        if log_path:
            log_full_path = os.path.join(log_path, log_filename)
        else:
            log_full_path = os.path.join(os.getcwd(), log_filename)  # 默认保存在当前工作目录
        
        try:
            with open(log_full_path, 'w') as log_file:
                log_file.write(data)
            return log_full_path
        except Exception as e:
            raise Exception(f"保存日志失败: {str(e)}")
    
    @staticmethod
    def get_log_path(default_path: str = None) -> str:
        """获取日志保存路径"""
        options = QFileDialog.Options()
        log_path = QFileDialog.getExistingDirectory(None, "选择日志保存路径", default_path, options=options)
        return log_path
