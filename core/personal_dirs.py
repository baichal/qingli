import os
import json
from pathlib import Path
from typing import List, Optional
from .smart_recognizer import learn_from_positive_example, learn_from_negative_example

PERSONAL_DIRS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "personal_dirs.json")

def _load_personal_dirs() -> list:
    """加载个人目录列表"""
    if not os.path.exists(PERSONAL_DIRS_FILE):
        return []
    try:
        with open(PERSONAL_DIRS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def _save_personal_dirs(dirs: list):
    """保存个人目录列表"""
    try:
        with open(PERSONAL_DIRS_FILE, "w", encoding="utf-8") as f:
            json.dump(dirs, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存个人目录失败: {e}")

def list_personal_dirs() -> list:
    """获取所有个人目录"""
    return _load_personal_dirs()

def is_personal_dir(dir_path: str) -> bool:
    """检查目录是否是个人目录（或其子目录）"""
    dir_path = os.path.normpath(dir_path).lower()
    personal_dirs = _load_personal_dirs()
    for pd in personal_dirs:
        pd_norm = os.path.normpath(pd).lower()
        if dir_path == pd_norm or dir_path.startswith(pd_norm + os.sep):
            return True
    return False

def add_personal_dir(dir_path: str, file_paths: Optional[List[str]] = None) -> bool:
    """添加个人目录"""
    dir_path = os.path.normpath(dir_path)
    if not os.path.isdir(dir_path):
        return False
    
    personal_dirs = _load_personal_dirs()
    
    # 检查是否已存在（或其子目录/父目录）
    pd_norm = dir_path.lower()
    filtered = []
    for pd in personal_dirs:
        existing = os.path.normpath(pd).lower()
        if existing == pd_norm:
            return True  # 已存在
        if existing.startswith(pd_norm + os.sep):
            continue  # 新目录是现有目录的父目录，删除现有子目录
        if pd_norm.startswith(existing + os.sep):
            return True  # 现有目录是新目录的父目录，无需添加
    
    filtered.append(dir_path)
    personal_dirs = [pd for pd in personal_dirs if pd not in filtered]
    personal_dirs.append(dir_path)
    
    _save_personal_dirs(personal_dirs)
    
    # 学习这个正例
    learn_from_positive_example(dir_path, file_paths)
    
    return True

def remove_personal_dir(dir_path: str) -> bool:
    """移除个人目录"""
    dir_path = os.path.normpath(dir_path)
    personal_dirs = _load_personal_dirs()
    
    pd_norm = dir_path.lower()
    new_dirs = [pd for pd in personal_dirs if os.path.normpath(pd).lower() != pd_norm]
    
    if len(new_dirs) == len(personal_dirs):
        return False  # 没找到
    
    _save_personal_dirs(new_dirs)
    return True

def clear_all_personal_dirs():
    """清空所有个人目录"""
    _save_personal_dirs([])
