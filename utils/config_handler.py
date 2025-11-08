# config_handler.py

import json
import os

class ConfigHandler:
    """配置文件处理工具类"""
    
    CONFIG_FILE = "config.json"
    
    @staticmethod
    def load_config() -> dict:
        """加载配置文件"""
        if not os.path.exists(ConfigHandler.CONFIG_FILE):
            return {}
        
        try:
            with open(ConfigHandler.CONFIG_FILE, 'r') as config_file:
                config = json.load(config_file)
            return config
        except Exception as e:
            raise Exception(f"加载配置失败: {str(e)}")
    
    @staticmethod
    def save_config(config: dict):
        """保存配置文件"""
        try:
            with open(ConfigHandler.CONFIG_FILE, 'w') as config_file:
                json.dump(config, config_file, indent=4)
        except Exception as e:
            raise Exception(f"保存配置失败: {str(e)}")
