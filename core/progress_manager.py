import os
import json
import time
from datetime import datetime
from pathlib import Path

SCAN_PROGRESS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "scan_progress.json"
)


def save_scan_progress(data: dict):
    """保存扫描进度到文件"""
    try:
        data["timestamp"] = time.time()
        data["datetime"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(SCAN_PROGRESS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def load_scan_progress() -> dict | None:
    """加载扫描进度"""
    try:
        if os.path.exists(SCAN_PROGRESS_FILE):
            with open(SCAN_PROGRESS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return None


def clear_scan_progress():
    """清除扫描进度"""
    try:
        if os.path.exists(SCAN_PROGRESS_FILE):
            os.remove(SCAN_PROGRESS_FILE)
    except Exception:
        pass


def should_resume_scan() -> bool:
    """是否应该恢复扫描"""
    progress = load_scan_progress()
    if not progress:
        return False
    # 检查进度是否在24小时内
    if "timestamp" in progress:
        age = time.time() - progress["timestamp"]
        return age < 86400  # 24小时
    return False
