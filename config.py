import os

class Config:
    APP_NAME = "文件清理工具"
    VERSION = "1.0.0"
    
    HOST = "127.0.0.1"
    PORT = 8899
    DEBUG = False
    
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_DIR = os.path.join(BASE_DIR, "data")
    
    RULES_CUSTOM_FILE = os.path.join(BASE_DIR, "rules_custom.json")
    LEARNED_PATTERNS_FILE = os.path.join(BASE_DIR, "learned_patterns.json")
    
    MAX_PREVIEW_SIZE = 50 * 1024
    MAX_CONTENT_SCAN_SIZE = 100 * 1024
    MAX_IMAGE_PREVIEW_SIZE = 10 * 1024 * 1024
    
    @classmethod
    def ensure_data_dir(cls):
        os.makedirs(cls.DATA_DIR, exist_ok=True)
