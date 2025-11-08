import serial.tools.list_ports
from typing import List, Dict

class PortScanner:
    """串口端口扫描器"""
    
    @staticmethod
    def get_available_ports() -> List[Dict]:
        """获取所有可用串口信息"""
        ports = serial.tools.list_ports.comports()
        port_list = []
        
        for port in ports:
            port_info = {
                'device': port.device,
                'description': port.description or '未知设备',
                'hwid': port.hwid,
                'vid': port.vid if port.vid else None,
                'pid': port.pid if port.pid else None,
                'serial_number': port.serial_number,
                'location': port.location,
                'manufacturer': port.manufacturer,
                'product': port.product,
                'interface': port.interface
            }
            port_list.append(port_info)
        
        return port_list
    
    @staticmethod
    def get_port_display_name(port_info: Dict) -> str:
        """获取端口显示名称"""
        description = port_info['description']
        if port_info['manufacturer']:
            description = f"{description} ({port_info['manufacturer']})"
        return f"{port_info['device']} - {description}"
    
    @staticmethod
    def validate_port(port_device: str) -> bool:
        """验证端口是否可用"""
        try:
            with serial.Serial(port_device, timeout=1):
                return True
        except:
            return False