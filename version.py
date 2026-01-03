"""
版本信息文件
在GitHub Actions构建时，版本号会被自动更新
"""

__version__ = "0.0.0"  # 开发版本，在GitHub Actions构建时会被替换
__author__ = "Trigger-CN"

def get_version():
    """获取版本号"""
    return __version__

def get_author():
    """获取作者"""
    return __author__

def get_app_title():
    """获取应用程序标题（包含版本号和作者）"""
    if __version__ and __version__ != "0.0.0":
        return f"🔧串口监看工具 v{__version__} by {__author__}"
    else:
        return f"🔧串口监看工具 by {__author__}"

