import os
from pathlib import Path
from .rules import (
    SCAN_RULES,
    EXCLUDE_ABSOLUTE_DIRS,
    EXCLUDE_DIR_NAMES,
    EXCLUDE_FILE_NAMES,
    MAX_CONTENT_SCAN_SIZE,
)
# 新增：引入自定义规则匹配
from .custom_rules import match_custom_rules


def normalize_path(path: str) -> str:
    return os.path.normpath(path).lower()


def should_exclude_dir(dir_path: str) -> bool:
    norm = normalize_path(dir_path)
    for ex in EXCLUDE_ABSOLUTE_DIRS:
        ex_norm = normalize_path(ex)
        if norm == ex_norm or norm.startswith(ex_norm + os.sep):
            return True
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
    文件分类入口
    优先级：自定义规则 > 内置规则
    """
    file_path = os.path.normpath(file_path)
    file_name = os.path.basename(file_path)

    # 排除系统文件
    if should_exclude_file(file_name):
        return None

    # ── 1. 优先匹配自定义规则 ──────────────────
    custom_match = match_custom_rules(file_path)
    if custom_match is not None:
        return custom_match

    # ── 2. 内置规则匹配 ────────────────────────
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