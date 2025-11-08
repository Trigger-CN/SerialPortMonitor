from datetime import datetime
from typing import Tuple, List, Generator
from .data_cache import DataCacheManager

class DataProcessor:
    """数据处理工具类"""
    
    @staticmethod
    def bytes_to_hex(data: bytes) -> str:
        """将字节数据转换为十六进制字符串"""
        return ' '.join([f'{b:02X}' for b in data])
    
    @staticmethod
    def hex_to_bytes(hex_string: str) -> bytes:
        """将十六进制字符串转换为字节数据"""
        # 移除空格和其他分隔符
        hex_string = hex_string.replace(' ', '').replace(',', '').replace(':', '')
        try:
            return bytes.fromhex(hex_string)
        except ValueError:
            raise ValueError("无效的十六进制字符串")
    
    @staticmethod
    def bytes_to_text(data: bytes) -> str:
        """将字节数据转换为文本"""
        try:
            return data.decode('utf-8', errors='replace')
        except:
            # 如果UTF-8解码失败，返回十六进制表示
            return DataProcessor.bytes_to_hex(data)
    
    @staticmethod
    def text_to_bytes(text: str, add_newline: bool = True) -> bytes:
        """将文本转换为字节数据"""
        if add_newline:
            text = text + '\r\n'
        return text.encode('utf-8')
    
    @staticmethod
    def format_with_timestamp(data: str, timestamp: datetime = None) -> str:
        """为数据添加时间戳"""
        if timestamp is None:
            timestamp = datetime.now()
        time_str = timestamp.strftime("%H:%M:%S.%f")[:-3]
        return f"[{time_str}] {data}"
    
    @staticmethod
    def process_received_data(data: bytes, hex_display: bool = False, 
                            show_timestamp: bool = False, 
                            timestamp: datetime = None) -> str:
        """处理接收到的数据"""
        if hex_display:
            processed = DataProcessor.bytes_to_hex(data) + ' '
        else:
            processed = DataProcessor.bytes_to_text(data)
        
        if show_timestamp:
            processed = DataProcessor.format_with_timestamp(processed, timestamp)
        
        return processed
    
    @staticmethod
    def process_send_data(text: str, hex_send: bool = False) -> bytes:
        """处理要发送的数据"""
        if hex_send:
            return DataProcessor.hex_to_bytes(text)
        else:
            return DataProcessor.text_to_bytes(text, add_newline=True)
    
    @staticmethod
    def split_data_for_comparison(data: bytes, bytes_per_line: int = 16) -> Tuple[List[str], List[str]]:
        """
        将数据分割为文本和十六进制对照格式
        
        Args:
            data: 原始字节数据
            bytes_per_line: 每行显示的字节数
            
        Returns:
            Tuple[List[str], List[str]]: (文本行列表, 十六进制行列表)
        """
        text_lines = []
        hex_lines = []
        
        # 按指定字节数分割数据
        for i in range(0, len(data), bytes_per_line):
            chunk = data[i:i + bytes_per_line]
            
            # 处理文本显示
            text_line = ""
            for byte in chunk:
                if 32 <= byte <= 126:  # 可打印ASCII字符
                    text_line += chr(byte)
                else:
                    text_line += "."  # 非打印字符用点号表示
            text_lines.append(text_line)
            
            # 处理十六进制显示
            hex_line = ' '.join([f'{b:02X}' for b in chunk])
            # 补齐长度以便对齐
            hex_line += '   ' * (bytes_per_line - len(chunk))
            hex_lines.append(hex_line)
        
        return text_lines, hex_lines
    
    @staticmethod
    def format_comparison_display(text_lines: List[str], hex_lines: List[str], 
                                show_timestamp: bool = False,
                                timestamp: datetime = None) -> Tuple[str, str]:
        """
        格式化对照显示内容
        
        Returns:
            Tuple[str, str]: (文本显示内容, 十六进制显示内容)
        """
        text_display = ""
        hex_display = ""
        
        for i, (text_line, hex_line) in enumerate(zip(text_lines, hex_lines)):
            # 添加行号
            line_prefix = f"{i * 16:04X}: " if len(text_lines) > 1 else ""
            
            # 添加时间戳（只在第一行添加）
            time_prefix = ""
            if show_timestamp and i == 0 and timestamp:
                time_prefix = DataProcessor.format_with_timestamp("", timestamp)[:-1] + " "
            
            text_display += f"{time_prefix}{line_prefix}{text_line}\n"
            hex_display += f"{time_prefix}{line_prefix}{hex_line}\n"
        
        return text_display.rstrip(), hex_display.rstrip()
    
    @staticmethod
    def process_cached_data_for_normal(cache_manager: 'DataCacheManager', 
                                     hex_display: bool = False,
                                     show_timestamp: bool = False,
                                     max_chars: int = 500000) -> str:
        """处理缓存数据用于普通显示模式（性能优化版本）"""
        result = []
        total_chars = 0
        
        for data, timestamp in cache_manager.get_all_data_with_timestamps():
            processed = DataProcessor.process_received_data(
                data, hex_display, show_timestamp, timestamp
            )
            
            # 如果超过最大字符数，只保留最新的数据
            if total_chars + len(processed) > max_chars:
                # 计算需要截取的长度
                remaining_chars = max_chars - total_chars
                if remaining_chars > 100:  # 至少保留100个字符
                    processed = processed[-remaining_chars:]
                    result.append(processed)
                    total_chars += len(processed)
                break
            else:
                result.append(processed)
                total_chars += len(processed)
        
        return ''.join(result)
    
    @staticmethod
    def process_cached_data_for_comparison(cache_manager: 'DataCacheManager',
                                         show_timestamp: bool = False,
                                         max_bytes: int = 100000) -> Tuple[str, str]:
        """处理缓存数据用于对照显示模式（性能优化版本）"""
        # 只处理最近的数据，避免性能问题
        all_data = cache_manager.get_all_data()
        
        # 如果数据量太大，只取最后的部分
        if len(all_data) > max_bytes:
            all_data = all_data[-max_bytes:]
        
        text_lines, hex_lines = DataProcessor.split_data_for_comparison(all_data)
        
        # 获取第一个数据包的时间戳（如果有）
        first_timestamp = None
        cached_data = cache_manager.get_all_data_with_timestamps()
        if cached_data:
            first_timestamp = cached_data[0][1]
        
        text_display, hex_display = DataProcessor.format_comparison_display(
            text_lines, hex_lines, show_timestamp, first_timestamp
        )
        
        return text_display, hex_display
    
    @staticmethod
    def get_cached_data_summary(cache_manager: 'DataCacheManager') -> str:
        """获取缓存数据摘要（用于性能模式）"""
        packet_count, total_bytes = cache_manager.get_cache_info()
        
        if total_bytes > 100000:  # 超过100KB时显示摘要
            return f"[数据量较大: {packet_count} 包, {total_bytes} 字节 - 已启用性能模式]"
        return ""
    
    # ==================== 懒加载相关方法 ====================
    
    @staticmethod
    def get_lazy_display_chunks(cache_manager: 'DataCacheManager',
                              hex_display: bool = False,
                              show_timestamp: bool = False,
                              chunk_size: int = 10000) -> Generator[str, None, None]:
        """
        生成懒加载的显示块
        
        Args:
            cache_manager: 数据缓存管理器
            hex_display: 是否显示十六进制
            show_timestamp: 是否显示时间戳
            chunk_size: 每个块的大小（字符数）
            
        Yields:
            str: 显示文本块
        """
        current_chunk = ""
        current_size = 0
        
        for data, timestamp in cache_manager.get_all_data_with_timestamps():
            processed = DataProcessor.process_received_data(
                data, hex_display, show_timestamp, timestamp
            )
            
            # 如果当前块加上新数据超过块大小，先返回当前块
            if current_size + len(processed) > chunk_size and current_chunk:
                yield current_chunk
                current_chunk = ""
                current_size = 0
            
            current_chunk += processed
            current_size += len(processed)
        
        # 返回最后一个块
        if current_chunk:
            yield current_chunk
    
    @staticmethod
    def get_lazy_comparison_chunks(cache_manager: 'DataCacheManager',
                                 show_timestamp: bool = False,
                                 lines_per_chunk: int = 100) -> Generator[Tuple[str, str], None, None]:
        """
        生成懒加载的对照显示块
        
        Args:
            cache_manager: 数据缓存管理器
            show_timestamp: 是否显示时间戳
            lines_per_chunk: 每个块的行数
            
        Yields:
            Tuple[str, str]: (文本块, 十六进制块)
        """
        all_data = cache_manager.get_all_data()
        text_lines, hex_lines = DataProcessor.split_data_for_comparison(all_data)
        
        # 获取第一个数据包的时间戳（如果有）
        first_timestamp = None
        cached_data = cache_manager.get_all_data_with_timestamps()
        if cached_data:
            first_timestamp = cached_data[0][1]
        
        # 分批处理行
        for i in range(0, len(text_lines), lines_per_chunk):
            chunk_text_lines = text_lines[i:i + lines_per_chunk]
            chunk_hex_lines = hex_lines[i:i + lines_per_chunk]
            
            text_display, hex_display = DataProcessor.format_comparison_display(
                chunk_text_lines, chunk_hex_lines, show_timestamp and i == 0, first_timestamp
            )
            
            yield text_display, hex_display
    
    @staticmethod
    def estimate_total_chunks(cache_manager: 'DataCacheManager',
                            hex_display: bool = False,
                            chunk_size: int = 10000) -> int:
        """估算总块数"""
        total_chars = 0
        for data, _ in cache_manager.get_all_data_with_timestamps():
            # 估算处理后的字符数（粗略估算）
            if hex_display:
                total_chars += len(data) * 3  # 十六进制：每个字节约3个字符
            else:
                total_chars += len(data)  # 文本：每个字节约1个字符
        
        return max(1, (total_chars + chunk_size - 1) // chunk_size)
    
    @staticmethod
    def estimate_comparison_chunks(cache_manager: 'DataCacheManager',
                                 lines_per_chunk: int = 100) -> int:
        """估算对照模式总块数"""
        all_data = cache_manager.get_all_data()
        total_lines = (len(all_data) + 15) // 16  # 每行16字节
        return max(1, (total_lines + lines_per_chunk - 1) // lines_per_chunk)