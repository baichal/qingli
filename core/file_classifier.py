import os
import re
from pathlib import Path
from typing import Tuple, Optional

class FileClassifier:
    """增强的文件分类器 - 专门用于识别系统文件、软件文件和个人文件"""
    
    # 系统文件扩展名
    SYSTEM_EXTENSIONS = {
        '.sys', '.dll', '.exe', '.msi', '.inf', '.cat', '.pdb',
        '.ocx', '.scr', '.drv', '.vxd', '.cpl', '.msc', '.mui',
        '.manifest', '.winmd', '.appx', '.msix', '.eula'
    }
    
    # 系统文件名关键词
    SYSTEM_FILENAME_KEYWORDS = {
        'ntuser', 'desktop', 'thumbs', 'pagefile', 'hiberfil',
        'swapfile', 'system', 'config', 'software', 'default',
        'sam', 'security', 'bcd', 'boot', 'bootmgr', 'winload',
        'winsxs', 'assembly', 'installer', 'servicing',
    }
    
    # 系统目录模式
    SYSTEM_DIR_PATTERNS = [
        r'^[A-Za-z]:\\Windows',
        r'^[A-Za-z]:\\Program Files',
        r'^[A-Za-z]:\\Program Files \(x86\)',
        r'^[A-Za-z]:\\ProgramData',
        r'^[A-Za-z]:\\\$Recycle\.Bin',
        r'^[A-Za-z]:\\System Volume Information',
        r'^[A-Za-z]:\\Recovery',
        r'^[A-Za-z]:\\\$WinREAgent',
        r'^[A-Za-z]:\\Users\\All Users',
        r'^[A-Za-z]:\\Users\\Default',
        r'^[A-Za-z]:\\Users\\Default User',
        r'\\AppData\\Local(?!\\Temp)',
        r'\\AppData\\Roaming',
        r'\\AppData\\LocalLow',
    ]
    
    # 个人文件专属目录
    PERSONAL_SPECIAL_DIRS = [
        'Desktop', 'Documents', 'Downloads', 'Pictures',
        'Videos', 'Music', 'Favorites', 'Links'
    ]
    
    # 个人文件扩展名
    PERSONAL_EXTENSIONS = {
        '.docx', '.doc', '.pdf', '.xlsx', '.xls', '.pptx', '.ppt',
        '.txt', '.md', '.rtf', '.odt', '.ods', '.odp', '.wps',
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp',
        '.heic', '.raw', '.psd', '.ai', '.svg', '.mp4', '.mov',
        '.avi', '.mkv', '.wmv', '.flv', '.rmvb', '.m4v', '.mp3',
        '.flac', '.wav', '.aac', '.m4a', '.ogg', '.wma', '.zip',
        '.rar', '.7z', '.tar', '.gz', '.bz2', '.eml', '.msg',
        '.pst', '.mbox'
    }
    
    # 个人文件关键词
    PERSONAL_FILENAME_KEYWORDS = {
        '简历', 'resume', 'cv', '身份证', '护照', 'passport',
        '合同', 'contract', 'offer', '薪资', '工资', 'salary',
        '银行', 'bank', '保险', 'insurance', '医疗', 'medical',
        '日记', 'diary', '笔记', 'note', '备忘录', 'memo',
        '照片', 'photo', 'picture', 'image', 'pic', '相册', 'album',
        '视频', 'video', 'movie', 'film', '音乐', 'music', 'song',
        'IMG_', 'DSC_', 'VID_', '微信图片', '微信截图',
        'mmexport', 'Screenshot_', '屏幕截图', '截屏',
        '我的', '私人', '个人', 'private', 'personal', 'my'
    }
    
    @classmethod
    def is_system_file(cls, file_path: str) -> bool:
        """判断是否为系统文件"""
        path_lower = file_path.lower()
        filename = os.path.basename(file_path).lower()
        ext = Path(file_path).suffix.lower()
        
        # 1. 首先检查是否在个人专属目录中（如果是，则不是系统文件）
        for dir_name in cls.PERSONAL_SPECIAL_DIRS:
            dir_pattern = os.sep + dir_name.lower() + os.sep
            if dir_pattern in path_lower or path_lower.endswith(os.sep + dir_name.lower()):
                return False
        
        # 2. 检查系统扩展名
        if ext in cls.SYSTEM_EXTENSIONS:
            return True
        
        # 3. 检查系统文件名关键词
        for keyword in cls.SYSTEM_FILENAME_KEYWORDS:
            if keyword in filename:
                return True
        
        # 4. 检查系统目录模式
        for pattern in cls.SYSTEM_DIR_PATTERNS:
            if re.match(pattern, file_path, re.IGNORECASE):
                return True
        
        return False
    
    @classmethod
    def is_personal_file(cls, file_path: str, filename: Optional[str] = None, 
                       ext: Optional[str] = None) -> Tuple[bool, str]:
        """
        判断是否为个人文件
        
        Returns:
            (is_personal, reason)
        """
        if filename is None:
            filename = os.path.basename(file_path)
        if ext is None:
            ext = Path(file_path).suffix.lower()
        
        filename_lower = filename.lower()
        path_lower = file_path.lower()
        
        # 1. 检查是否在个人专属目录
        for dir_name in cls.PERSONAL_SPECIAL_DIRS:
            dir_pattern = os.path.sep + dir_name.lower() + os.path.sep
            if dir_pattern in path_lower or path_lower.endswith(os.path.sep + dir_name.lower()):
                return True, f"在{dir_name}目录中"
        
        # 2. 检查个人文件关键词
        for keyword in cls.PERSONAL_FILENAME_KEYWORDS:
            if keyword.lower() in filename_lower:
                return True, f"文件名包含关键词: {keyword}"
        
        # 3. 检查个人文件扩展名
        if ext in cls.PERSONAL_EXTENSIONS:
            return True, f"文件类型为个人常用格式"
        
        return False, ""
    
    @classmethod
    def classify_file_type(cls, file_path: str) -> dict:
        """
        综合文件分类
        
        Returns:
            {
                'is_system': bool,
                'is_personal': bool,
                'is_software': bool,
                'category': str,
                'reason': str
            }
        """
        filename = os.path.basename(file_path)
        ext = Path(file_path).suffix.lower()
        path_lower = file_path.lower()
        
        result = {
            'is_system': False,
            'is_personal': False,
            'is_software': False,
            'category': 'unknown',
            'reason': ''
        }
        
        # 1. 首先检查是否为个人文件（最高优先级，避免误判）
        is_personal, personal_reason = cls.is_personal_file(file_path, filename, ext)
        if is_personal:
            result['is_personal'] = True
            result['category'] = 'personal'
            result['reason'] = personal_reason
            return result
        
        # 2. 检查系统文件
        if cls.is_system_file(file_path):
            result['is_system'] = True
            result['category'] = 'system'
            result['reason'] = '识别为系统文件'
            return result
        
        # 3. 检查软件文件
        is_soft, soft_reason = cls._is_software_file(file_path)
        if is_soft:
            result['is_software'] = True
            result['category'] = 'software'
            result['reason'] = soft_reason
            return result
        
        return result
    
    @classmethod
    def _is_software_file(cls, file_path: str) -> Tuple[bool, str]:
        """判断是否为软件相关文件"""
        path_lower = file_path.lower()
        
        # 软件数据目录特征
        software_indicators = [
            r'\\appdata\\',
            r'\\program files',
            r'\\programdata\\',
            r'\\node_modules\\',
            r'\\venv\\',
            r'\\.venv\\',
            r'\\__pycache__\\',
            r'\\.git\\',
            r'\\build\\',
            r'\\dist\\',
        ]
        
        for pattern in software_indicators:
            if re.search(pattern, path_lower):
                return True, '在软件数据目录中'
        
        return False, ""

# 单例实例
file_classifier = FileClassifier()
