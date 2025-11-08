import serial
from PyQt5.QtCore import QObject, pyqtSignal
from typing import Optional

class SerialManager(QObject):
    """串口通信管理器"""
    
    # 信号定义
    data_received = pyqtSignal(bytes)
    connection_changed = pyqtSignal(bool)
    error_occurred = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.serial_port: Optional[serial.Serial] = None
        self.is_connected = False
        
    def connect_serial(self, port: str, baudrate: int = 115200, 
                      bytesize: int = serial.EIGHTBITS,
                      parity: str = serial.PARITY_NONE,
                      stopbits: float = serial.STOPBITS_ONE,
                      timeout: float = 0.1) -> bool:
        """连接串口"""
        try:
            self.serial_port = serial.Serial(
                port=port,
                baudrate=baudrate,
                bytesize=bytesize,
                parity=parity,
                stopbits=stopbits,
                timeout=timeout
            )
            
            if self.serial_port.is_open:
                self.is_connected = True
                self.connection_changed.emit(True)
                return True
            else:
                self.error_occurred.emit("无法打开串口")
                return False
                
        except Exception as e:
            self.error_occurred.emit(f"连接错误: {str(e)}")
            return False
    
    def disconnect_serial(self):
        """断开串口连接"""
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
        
        self.is_connected = False
        self.connection_changed.emit(False)
    
    def send_data(self, data: bytes) -> int:
        """发送数据"""
        if not self.serial_port or not self.serial_port.is_open:
            self.error_occurred.emit("串口未连接")
            return 0
            
        try:
            return self.serial_port.write(data)
        except Exception as e:
            self.error_occurred.emit(f"发送错误: {str(e)}")
            return 0
    
    def read_data(self) -> bytes:
        """读取数据"""
        if not self.serial_port or not self.serial_port.is_open:
            return b""
            
        try:
            if self.serial_port.in_waiting > 0:
                data = self.serial_port.read(self.serial_port.in_waiting)
                if data:
                    self.data_received.emit(data)
                return data
        except Exception as e:
            self.error_occurred.emit(f"读取错误: {str(e)}")
        
        return b""
    
    def get_connection_status(self) -> bool:
        """获取连接状态"""
        return self.is_connected and self.serial_port and self.serial_port.is_open