import os
import json
import uuid
import re
from datetime import datetime
from pathlib import Path

# 自定义规则存储文件路径
CUSTOM_RULES_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "rules_custom.json"
)

# 条件类型定义
CONDITION_TYPES = {
    "filename_keyword": "文件名关键词",
    "filename_regex":   "文件名正则",
    "path_contains":    "路径包含",
    "path_regex":       "路径正则",
    "extension":        "扩展名",
    "content_keyword":  "内容关键词",
}

# 风险等级对应颜色
RISK_COLORS = {
    "high":   "#ff4d4f",
    "medium": "#faad14",
    "low":    "#52c41a",
}


# ─────────────────────────────────────────
# 持久化读写
# ─────────────────────────────────────────

def _load_store() -> dict:
    """读取本地 JSON 文件"""
    if not os.path.exists(CUSTOM_RULES_FILE):
        return {"version": 1, "rules": []}
    try:
        with open(CUSTOM_RULES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "rules" not in data:
                data["rules"] = []
            return data
    except Exception:
        return {"version": 1, "rules": []}


def _save_store(store: dict):
    """写入本地 JSON 文件"""
    with open(CUSTOM_RULES_FILE, "w", encoding="utf-8") as f:
        json.dump(store, f, ensure_ascii=False, indent=2)


# ─────────────────────────────────────────
# CRUD
# ─────────────────────────────────────────

def list_rules() -> list:
    """获取所有自定义规则"""
    return _load_store()["rules"]


def get_rule(rule_id: str) -> dict | None:
    """根据ID获取单条规则"""
    for r in list_rules():
        if r["id"] == rule_id:
            return r
    return None


def create_rule(payload: dict) -> dict:
    """
    新建规则
    payload: {
        name, icon, risk, enabled,
        logic,          # "OR" | "AND"
        case_sensitive, # bool
        conditions: [{ type, value }]
    }
    """
    rule = _build_rule(payload)
    store = _load_store()
    store["rules"].append(rule)
    _save_store(store)
    return rule


def update_rule(rule_id: str, payload: dict) -> dict | None:
    """更新规则"""
    store = _load_store()
    for i, r in enumerate(store["rules"]):
        if r["id"] == rule_id:
            updated = _build_rule(payload, rule_id=rule_id,
                                  created_at=r.get("created_at"))
            store["rules"][i] = updated
            _save_store(store)
            return updated
    return None


def delete_rule(rule_id: str) -> bool:
    """删除单条规则"""
    store = _load_store()
    before = len(store["rules"])
    store["rules"] = [r for r in store["rules"] if r["id"] != rule_id]
    if len(store["rules"]) < before:
        _save_store(store)
        return True
    return False


def clear_all_rules() -> int:
    """一键清除所有自定义规则，返回清除数量"""
    store = _load_store()
    count = len(store["rules"])
    store["rules"] = []
    _save_store(store)
    return count


def toggle_rule(rule_id: str, enabled: bool) -> bool:
    """启用/禁用规则"""
    store = _load_store()
    for r in store["rules"]:
        if r["id"] == rule_id:
            r["enabled"] = enabled
            r["updated_at"] = _now()
            _save_store(store)
            return True
    return False


# ─────────────────────────────────────────
# 规则匹配
# ─────────────────────────────────────────

def match_custom_rules(file_path: str) -> dict | None:
    """
    对单个文件尝试匹配所有启用的自定义规则
    返回第一个命中的规则信息，未命中返回 None
    优先级：风险 high > medium > low，同级按创建时间
    """
    rules = [r for r in list_rules() if r.get("enabled", True)]
    if not rules:
        return None

    # 按风险等级排序，高风险优先
    risk_order = {"high": 0, "medium": 1, "low": 2}
    rules.sort(key=lambda r: risk_order.get(r.get("risk", "low"), 9))

    file_path_norm = os.path.normpath(file_path)
    file_name = os.path.basename(file_path_norm)
    ext = Path(file_path_norm).suffix.lower()

    for rule in rules:
        if _rule_matches(rule, file_path_norm, file_name, ext):
            return {
                "key":            f"custom_{rule['id']}",
                "label":          rule["name"],
                "icon":           rule.get("icon", "📁"),
                "risk":           rule.get("risk", "medium"),
                "color":          RISK_COLORS.get(rule.get("risk", "medium"), "#faad14"),
                "match_reason":   [f"custom_rule:{rule['name']}"],
                "is_custom":      True,
                "custom_rule_id": rule["id"],
            }

    return None


def _rule_matches(rule: dict, file_path: str, file_name: str, ext: str) -> bool:
    """
    判断单条规则是否命中
    logic=OR：任意条件命中即命中
    logic=AND：所有条件都要命中
    """
    conditions = rule.get("conditions", [])
    if not conditions:
        return False

    logic = rule.get("logic", "OR").upper()
    case_sensitive = rule.get("case_sensitive", False)
    flags = 0 if case_sensitive else re.IGNORECASE

    results = [
        _condition_matches(cond, file_path, file_name, ext, flags)
        for cond in conditions
    ]

    if logic == "AND":
        return all(results)
    else:
        return any(results)


def _condition_matches(cond: dict, file_path: str,
                       file_name: str, ext: str, flags: int) -> bool:
    """单个条件匹配"""
    ctype = cond.get("type", "")
    value = cond.get("value", "").strip()
    if not value:
        return False

    try:
        if ctype == "filename_keyword":
            if flags & re.IGNORECASE:
                return value.lower() in file_name.lower()
            return value in file_name

        elif ctype == "filename_regex":
            return bool(re.search(value, file_name, flags))

        elif ctype == "path_contains":
            if flags & re.IGNORECASE:
                return value.lower() in file_path.lower()
            return value in file_path

        elif ctype == "path_regex":
            return bool(re.search(value, file_path, flags))

        elif ctype == "extension":
            # 支持多个扩展名逗号分隔
            exts = [e.strip().lower() for e in value.split(",") if e.strip()]
            return ext.lower() in exts

        elif ctype == "content_keyword":
            return _scan_content(file_path, value, flags)

    except re.error:
        # 正则语法错误，视为不匹配
        return False
    except Exception:
        return False

    return False


def _scan_content(file_path: str, keyword: str, flags: int) -> bool:
    """扫描文件内容是否包含关键词"""
    MAX_SIZE = 100 * 1024  # 100KB
    try:
        if os.path.getsize(file_path) > MAX_SIZE:
            return False
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        return bool(re.search(re.escape(keyword), content, flags))
    except Exception:
        return False


# ─────────────────────────────────────────
# 规则测试
# ─────────────────────────────────────────

def test_rule(payload: dict, test_path: str) -> dict:
    """
    测试规则是否命中指定路径
    返回详细的匹配报告
    """
    file_path = os.path.normpath(test_path)
    file_name = os.path.basename(file_path)
    ext = Path(file_path).suffix.lower()

    case_sensitive = payload.get("case_sensitive", False)
    flags = 0 if case_sensitive else re.IGNORECASE
    logic = payload.get("logic", "OR").upper()
    conditions = payload.get("conditions", [])

    condition_results = []
    for cond in conditions:
        ctype = cond.get("type", "")
        value = cond.get("value", "")
        try:
            hit = _condition_matches(cond, file_path, file_name, ext, flags)
            condition_results.append({
                "type":       ctype,
                "type_label": CONDITION_TYPES.get(ctype, ctype),
                "value":      value,
                "hit":        hit,
                "error":      None,
            })
        except re.error as e:
            condition_results.append({
                "type":       ctype,
                "type_label": CONDITION_TYPES.get(ctype, ctype),
                "value":      value,
                "hit":        False,
                "error":      f"正则语法错误: {e}",
            })

    hit_list = [r["hit"] for r in condition_results]
    if logic == "AND":
        final_hit = all(hit_list) if hit_list else False
    else:
        final_hit = any(hit_list) if hit_list else False

    return {
        "hit":               final_hit,
        "logic":             logic,
        "file_name":         file_name,
        "file_path":         file_path,
        "condition_results": condition_results,
    }


def validate_rule_payload(payload: dict) -> list:
    """
    校验规则数据合法性
    返回错误列表，空列表表示合法
    """
    errors = []

    if not payload.get("name", "").strip():
        errors.append("规则名称不能为空")

    if payload.get("risk") not in ("high", "medium", "low"):
        errors.append("风险等级必须是 high/medium/low")

    conditions = payload.get("conditions", [])
    if not conditions:
        errors.append("至少需要一个匹配条件")

    for i, cond in enumerate(conditions):
        ctype = cond.get("type", "")
        value = cond.get("value", "").strip()

        if ctype not in CONDITION_TYPES:
            errors.append(f"条件{i+1}: 未知条件类型 '{ctype}'")
            continue

        if not value:
            errors.append(f"条件{i+1}: 条件值不能为空")
            continue

        # 校验正则语法
        if ctype in ("filename_regex", "path_regex"):
            try:
                re.compile(value)
            except re.error as e:
                errors.append(f"条件{i+1}: 正则语法错误 - {e}")

    return errors


# ─────────────────────────────────────────
# 内部工具
# ─────────────────────────────────────────

def _build_rule(payload: dict, rule_id: str = None,
                created_at: str = None) -> dict:
    """构建规则对象"""
    risk = payload.get("risk", "medium")
    return {
        "id":             rule_id or str(uuid.uuid4()),
        "name":           payload.get("name", "未命名规则").strip(),
        "icon":           payload.get("icon", "📁"),
        "risk":           risk,
        "color":          RISK_COLORS.get(risk, "#faad14"),
        "enabled":        payload.get("enabled", True),
        "logic":          payload.get("logic", "OR").upper(),
        "case_sensitive": payload.get("case_sensitive", False),
        "conditions":     payload.get("conditions", []),
        "created_at":     created_at or _now(),
        "updated_at":     _now(),
    }


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")