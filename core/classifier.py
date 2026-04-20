import os
from pathlib import Path
from .rules import (
    SCAN_RULES,
    EXCLUDE_ABSOLUTE_DIRS,
    EXCLUDE_DIR_NAMES,
    EXCLUDE_FILE_NAMES,
    MAX_CONTENT_SCAN_SIZE,
    should_exclude_path,
)
# 新增：引入自定义规则匹配
from .custom_rules import match_custom_rules
# 新增：引入文件分类器
from .file_classifier import file_classifier
# 新增：引入智能分类器
from .intelligent_classifier import intelligent_classifier


def normalize_path(path: str) -> str:
    return os.path.normpath(path).lower()


def should_exclude_dir(dir_path: str) -> bool:
    """检查目录是否应该排除（增强版）"""
    # 1. 使用新的增强排除检查
    if should_exclude_path(dir_path):
        return True
    
    # 2. 保留原有检查作为补充
    norm = normalize_path(dir_path)
    dir_name = os.path.basename(dir_path)
    dir_name_lower = dir_name.lower()
    
    for ex_name in EXCLUDE_DIR_NAMES:
        if dir_name_lower == ex_name.lower():
            return True
        if ex_name.lower() in norm:
            return True
    
    return False


def should_exclude_file(file_name: str) -> bool:
    return file_name.lower() in [f.lower() for f in EXCLUDE_FILE_NAMES]


def _check_content_keywords(file_path: str, keywords: list) -> bool:
    if not keywords:
        return False
    try:
        size = os.path.getsize(file_path)
        if size > MAX_CONTENT_SCAN_SIZE:
            return False
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read().lower()
            return any(kw.lower() in content for kw in keywords)
    except Exception:
        return False


def classify_file(file_path: str) -> dict | None:
    """
    文件分类入口（增强版）
    优先级：系统文件排除 > 智能分类 > 自定义规则 > 内置规则
    """
    file_path = os.path.normpath(file_path)
    file_name = os.path.basename(file_path)

    # 1. 首先使用增强的路径排除检查
    if should_exclude_path(file_path):
        return None

    # 2. 使用智能分类器进行分类
    try:
        # 获取文件状态信息
        stat_info = {}
        if os.path.exists(file_path):
            stat = os.stat(file_path)
            stat_info = {
                "size": stat.st_size,
                "mtime_ts": int(stat.st_mtime)
            }
        
        # 使用智能分类器
        intelligent_result = intelligent_classifier.classify_file(file_path, stat_info)
        
        # 如果智能分类器确定为系统或软件文件，直接排除
        if intelligent_result["category"] in ["system", "software"] and intelligent_result["confidence"] > 0.7:
            return None
        
        # 如果智能分类器确定为个人文件，标记为疑似个人内容
        if intelligent_result["category"] == "personal" and intelligent_result["confidence"] > 0.5:
            # 继续执行后续分类，但添加智能分类信息
            pass
    except Exception:
        # 智能分类失败时，继续使用传统分类
        pass

    # 3. 检查是否为系统文件（使用新的文件分类器）
    if file_classifier.is_system_file(file_path):
        return None

    # 4. 排除系统文件
    if should_exclude_file(file_name):
        return None

    # ── 1. 优先匹配自定义规则 ──────────────────
    custom_match = match_custom_rules(file_path)
    if custom_match is not None:
        return custom_match

    # ── 内置规则匹配 ────────────────────────
    return _classify_builtin(file_path, file_name)


def _classify_builtin(file_path: str, file_name: str) -> dict | None:
    """内置规则匹配逻辑（原有逻辑不变）"""
    file_name_lower = file_name.lower()
    ext = Path(file_path).suffix.lower()

    matched_categories = []

    for cat_key, rule in SCAN_RULES.items():
        matched = False
        match_reason = []

        # 1. 优先路径匹配
        for p_path in rule.get("priority_paths", []):
            if p_path and normalize_path(file_path).startswith(
                normalize_path(p_path)
            ):
                matched = True
                match_reason.append("priority_path")
                break

        # 2. 精确文件名匹配
        for exact in rule.get("exact_filenames", []):
            if file_name_lower == exact.lower():
                matched = True
                match_reason.append("exact_filename")
                break

        # 3. 文件名关键词匹配
        if not matched:
            for kw in rule.get("filename_keywords", []):
                if kw.lower() in file_name_lower:
                    matched = True
                    match_reason.append(f"filename_keyword:{kw}")
                    break

        # 4. 扩展名匹配
        if not matched and ext:
            if ext in rule.get("extensions", []):
                matched = True
                match_reason.append(f"extension:{ext}")

        # 5. 内容关键词匹配
        if not matched:
            if _check_content_keywords(
                file_path, rule.get("content_keywords", [])
            ):
                matched = True
                match_reason.append("content_keyword")

        if matched:
            matched_categories.append({
                "key":          cat_key,
                "label":        rule["label"],
                "icon":         rule["icon"],
                "risk":         rule["risk"],
                "color":        rule["color"],
                "match_reason": match_reason,
                "is_custom":    False,
            })

    if not matched_categories:
        return None

    risk_order = {"high": 0, "medium": 1, "low": 2}
    matched_categories.sort(
        key=lambda x: risk_order.get(x["risk"], 9)
    )
    return matched_categories[0]