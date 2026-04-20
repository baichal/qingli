import os
import re
from pathlib import Path

def normalize_path(path: str) -> str:
    """标准化路径"""
    return os.path.normpath(path)

def path_exists(path: str) -> bool:
    """安全检查路径是否存在"""
    try:
        return os.path.exists(path)
    except Exception:
        return False

def human_size(size: int) -> str:
    """将字节转换为人类可读的格式"""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"

def is_text_file(file_path: str, sample_size: int = 8192) -> bool:
    """简单判断是否为文本文件"""
    try:
        with open(file_path, "rb") as f:
            chunk = f.read(sample_size)
        return b"\x00" not in chunk
    except Exception:
        return False

def get_file_extension(file_path: str) -> str:
    """获取文件扩展名（小写）"""
    return Path(file_path).suffix.lower()

def escape_html(s: str) -> str:
    """转义 HTML 特殊字符"""
    if not s:
        return ""
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;") \
                 .replace('"', "&quot;").replace("'", "&#39;")

def safe_filename(filename: str) -> str:
    """生成安全的文件名"""
    filename = str(filename)
    filename = re.sub(r'[<>:\"/\\|?*]', '_', filename)
    return filename.strip()
