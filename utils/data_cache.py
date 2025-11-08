from typing import List, Tuple
from datetime import datetime
from PyQt5.QtCore import QObject, pyqtSignal

class DataCacheManager(QObject):
    """数据缓存管理器"""
    
    # 信号：当缓存更新时发出
    cache_updated = pyqtSignal()
    
    def __init__(self, max_cache_size: int = 1000000):  # 默认最大缓存1MB数据
        super().__init__()
        self.max_cache_size = max_cache_size
        self.current_cache_size = 0
        self.cached_data: List[Tuple[bytes, datetime]] = []  # 存储(数据, 时间戳)的列表
        self._is_paused = False
    
    def add_data(self, data: bytes):
        """添加数据到缓存"""
        if self._is_paused or not data:
            return
            
        # 添加数据和时间戳
        self.cached_data.append((data, datetime.now()))
        self.current_cache_size += len(data)
        
        # 如果超过最大缓存大小，移除最老的数据
        while self.current_cache_size > self.max_cache_size and self.cached_data:
            old_data, _ = self.cached_data.pop(0)
            self.current_cache_size -= len(old_data)
        
        # 发出更新信号
        self.cache_updated.emit()
    
    def get_all_data(self) -> bytes:
        """获取所有缓存数据的合并字节"""
        return b''.join(data for data, _ in self.cached_data)
    
    def get_all_data_with_timestamps(self) -> List[Tuple[bytes, datetime]]:
        """获取所有缓存数据（包含时间戳）"""
        return self.cached_data.copy()
    
    def clear(self):
        """清空缓存"""
        self.cached_data.clear()
        self.current_cache_size = 0
        self.cache_updated.emit()
    
    def get_cache_info(self) -> Tuple[int, int]:
        """获取缓存信息：(数据包数量, 总字节数)"""
        return len(self.cached_data), self.current_cache_size
    
    def pause(self):
        """暂停缓存更新"""
        self._is_paused = True
    
    def resume(self):
        """恢复缓存更新"""
        self._is_paused = False
    
    def is_paused(self) -> bool:
        """检查是否暂停"""
        return self._is_paused