import os

class Config:
    APP_NAME = "文件清理工具"
    VERSION = "1.0.0"
    
    HOST = "127.0.0.1"
    PORT = 8899
    DEBUG = False
    
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_DIR = os.path.join(BASE_DIR, "data")
    
    # 数据文件路径
    RULES_CUSTOM_FILE = os.path.join(BASE_DIR, "rules_custom.json")
    PERSONAL_DIRS_FILE = os.path.join(BASE_DIR, "personal_dirs.json")
    LEARNED_PATTERNS_FILE = os.path.join(BASE_DIR, "learned_patterns.json")
    INTELLIGENT_LEARNING_FILE = os.path.join(BASE_DIR, "intelligent_learning.json")
    
    # 扫描和预览限制
    MAX_PREVIEW_SIZE = 50 * 1024  # 50KB
    MAX_CONTENT_SCAN_SIZE = 100 * 1024  # 100KB
    MAX_IMAGE_PREVIEW_SIZE = 10 * 1024 * 1024  # 10MB
    
    @classmethod
    def ensure_data_dir(cls):
        """确保数据目录存在"""
        os.makedirs(cls.DATA_DIR, exist_ok=True)
    
    @classmethod
    def ensure_default_files(cls):
        """确保所有必需的数据文件都存在"""
        cls.ensure_data_dir()
        
        # 确保 rules_custom.json 存在
        if not os.path.exists(cls.RULES_CUSTOM_FILE):
            with open(cls.RULES_CUSTOM_FILE, "w", encoding="utf-8") as f:
                import json
                json.dump({"version": 1, "rules": []}, f, ensure_ascii=False, indent=2)
        
        # 确保 personal_dirs.json 存在
        if not os.path.exists(cls.PERSONAL_DIRS_FILE):
            with open(cls.PERSONAL_DIRS_FILE, "w", encoding="utf-8") as f:
                import json
                json.dump([], f, ensure_ascii=False, indent=2)
        
        # 确保 learned_patterns.json 存在
        if not os.path.exists(cls.LEARNED_PATTERNS_FILE):
            with open(cls.LEARNED_PATTERNS_FILE, "w", encoding="utf-8") as f:
                import json
                json.dump({
                    "path_keywords": [],
                    "dir_patterns": [],
                    "filename_patterns": [],
                    "extension_weights": {},
                    "positive_examples": [],
                    "negative_examples": [],
                    "learn_count": 0
                }, f, ensure_ascii=False, indent=2)
        
        # 确保 intelligent_learning.json 存在
        if not os.path.exists(cls.INTELLIGENT_LEARNING_FILE):
            with open(cls.INTELLIGENT_LEARNING_FILE, "w", encoding="utf-8") as f:
                import json
                json.dump({
                    "version": 1,
                    "patterns": {
                        "personal_keywords": [],
                        "system_keywords": [],
                        "software_keywords": [],
                        "filename_patterns": {},
                        "extension_weights": {},
                        "dir_patterns": {}
                    },
                    "user_history": {
                        "deleted_files": [],
                        "kept_files": [],
                        "marked_personal": [],
                        "marked_system": []
                    },
                    "confidence_threshold": 0.6,
                    "learning_rate": 0.1,
                    "total_learning": 0
                }, f, ensure_ascii=False, indent=2)
