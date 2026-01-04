# update_checker.py

import json
import re
import platform
from typing import Optional, Dict, Tuple
from PyQt5.QtCore import QObject, pyqtSignal, QUrl
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
import version


class UpdateChecker(QObject):
    """更新检查器"""
    
    # 信号：检查完成
    update_available = pyqtSignal(str, str, str)  # (最新版本, 下载链接, 更新说明)
    no_update = pyqtSignal()  # 无更新
    check_failed = pyqtSignal(str)  # 检查失败 (错误信息)
    
    def __init__(self):
        super().__init__()
        self.network_manager = QNetworkAccessManager()
        self.current_version = version.get_version()
        self.github_repo = "Trigger-CN/SerialPortMonitor"
        
    def check_for_updates(self):
        """检查更新"""
        try:
            # GitHub Releases API URL
            url = QUrl(f"https://api.github.com/repos/{self.github_repo}/releases/latest")
            request = QNetworkRequest(url)
            request.setRawHeader(b"User-Agent", b"SerialMonitor-UpdateChecker")
            
            reply = self.network_manager.get(request)
            reply.finished.connect(lambda: self._handle_reply(reply))
            
        except Exception as e:
            self.check_failed.emit(f"检查更新失败: {str(e)}")
    
    def _handle_reply(self, reply: QNetworkReply):
        """处理网络响应"""
        try:
            if reply.error() != QNetworkReply.NoError:
                self.check_failed.emit(f"网络错误: {reply.errorString()}")
                reply.deleteLater()
                return
            
            data = reply.readAll().data()
            reply.deleteLater()
            
            try:
                release_info = json.loads(data.decode('utf-8'))
            except json.JSONDecodeError:
                self.check_failed.emit("解析响应数据失败")
                return
            
            # 获取版本号
            tag_name = release_info.get('tag_name', '')
            latest_version = self._parse_version(tag_name)
            
            if not latest_version:
                self.check_failed.emit("无法解析版本号")
                return
            
            # 比较版本
            if self._compare_versions(self.current_version, latest_version) >= 0:
                self.no_update.emit()
                return
            
            # 获取下载链接
            download_url = self._get_download_url(release_info.get('assets', []))
            
            # 获取更新说明
            release_notes = release_info.get('body', '无更新说明')
            if len(release_notes) > 500:
                release_notes = release_notes[:500] + "..."
            
            # 发出有更新的信号
            self.update_available.emit(latest_version, download_url, release_notes)
            
        except Exception as e:
            self.check_failed.emit(f"处理更新信息失败: {str(e)}")
    
    def _parse_version(self, tag_name: str) -> Optional[str]:
        """从标签名解析版本号"""
        if not tag_name:
            return None
        
        # 移除 'v' 前缀
        version_str = tag_name.lstrip('v')
        
        # 验证版本号格式 (例如: 1.0.0, 1.2.3, 0.1.0)
        if re.match(r'^\d+\.\d+\.\d+', version_str):
            return version_str
        
        return None
    
    def _compare_versions(self, current: str, latest: str) -> int:
        """
        比较版本号
        返回: 
        - 负数: current < latest (需要更新)
        - 0: current == latest (无需更新)
        - 正数: current > latest (开发版本可能)
        """
        # 处理开发版本
        if current == "0.0.0" or current.startswith("dev-"):
            # 开发版本始终提示更新（但可以忽略）
            return -1
        
        try:
            def version_tuple(v: str):
                parts = v.split('.')
                return tuple(int(x) for x in parts[:3])
            
            current_tuple = version_tuple(current)
            latest_tuple = version_tuple(latest)
            
            if current_tuple < latest_tuple:
                return -1
            elif current_tuple > latest_tuple:
                return 1
            else:
                return 0
        except (ValueError, IndexError):
            # 版本号格式错误，假设需要更新
            return -1
    
    def _get_download_url(self, assets: list) -> str:
        """根据平台获取下载链接"""
        system = platform.system()
        
        if system == "Windows":
            pattern = r"SerialMonitor-v\d+\.\d+\.\d+-Windows\.exe$"
        elif system == "Darwin":  # macOS
            pattern = r"SerialMonitor-v\d+\.\d+\.\d+-macOS\.zip$"
        elif system == "Linux":
            pattern = r"SerialMonitor-v\d+\.\d+\.\d+-Linux$"
        else:
            # 未知平台，返回第一个资源链接或 GitHub releases 页面
            if assets:
                return assets[0].get('browser_download_url', '')
            return f"https://github.com/{self.github_repo}/releases/latest"
        
        # 查找匹配的资源
        for asset in assets:
            name = asset.get('name', '')
            if re.search(pattern, name):
                return asset.get('browser_download_url', '')
        
        # 如果没找到匹配的资源，返回 releases 页面
        return f"https://github.com/{self.github_repo}/releases/latest"
    
    def get_current_version(self) -> str:
        """获取当前版本"""
        return self.current_version
    
    def get_releases_page_url(self) -> str:
        """获取 Releases 页面 URL"""
        return f"https://github.com/{self.github_repo}/releases/latest"

