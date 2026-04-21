import os
import sys
import json
import threading
import webbrowser
import time
import re
from flask import (
    Flask, render_template, request,
    jsonify, Response, stream_with_context, send_file
)

def _validate_path(path: str) -> bool:
    """验证路径是否安全，防止目录遍历攻击"""
    if not path:
        return False
    try:
        # 规范化路径
        normalized_path = os.path.normpath(path)
        # 检查是否包含路径遍历字符
        if '..' in normalized_path:
            return False
        # 检查路径是否存在
        if not os.path.exists(normalized_path):
            return False
        return True
    except Exception:
        return False
from core.scanner import scanner
from core.file_ops import (
    delete_to_trash, delete_permanently,
    preview_file, export_list
)
from core.progress_manager import (
    should_resume_scan, load_scan_progress, clear_scan_progress
)
# 在 app.py 顶部 import 区域新增
from core.custom_rules import (
    list_rules, get_rule, create_rule, update_rule,
    delete_rule, clear_all_rules, toggle_rule,
    test_rule, validate_rule_payload, CONDITION_TYPES,
)
from core.personal_dirs import (
    list_personal_dirs, add_personal_dir, remove_personal_dir,
    clear_all_personal_dirs, is_personal_dir,
)
# 新增：引入智能分类器
from core.intelligent_classifier import intelligent_classifier

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False


# ─────────────────────────────────────────
# 页面路由
# ─────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


# ─────────────────────────────────────────
# 扫描 API
# ─────────────────────────────────────────

@app.route("/api/drives", methods=["GET"])
def get_drives():
    """获取所有可用盘符"""
    drives = []
    for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        drive = f"{letter}:\\"
        if os.path.exists(drive):
            try:
                total, used, free = _get_disk_usage(drive)
                drives.append({
                    "drive": drive,
                    "letter": letter,
                    "total": total,
                    "used": used,
                    "free": free,
                    "total_human": _human_size(total),
                    "free_human": _human_size(free),
                })
            except Exception:
                drives.append({
                    "drive": drive,
                    "letter": letter,
                    "total": 0,
                    "used": 0,
                    "free": 0,
                    "total_human": "未知",
                    "free_human": "未知",
                })
    return jsonify({"drives": drives})


@app.route("/api/scan/start", methods=["POST"])
def scan_start():
    """开始扫描"""
    if scanner.is_running:
        return jsonify({"success": False, "msg": "扫描正在进行中"})

    data = request.get_json() or {}
    drives = data.get("drives", None)
    extra_exclude = data.get("extra_exclude", [])
    resume = data.get("resume", False)
    fast_mode = data.get("fast_mode", False)

    ok = scanner.start(drives=drives, extra_exclude=extra_exclude, resume=resume, fast_mode=fast_mode)
    return jsonify({"success": ok, "msg": "扫描已启动" if ok else "启动失败"})


@app.route("/api/scan/check_resume", methods=["GET"])
def check_resume():
    """检查是否有可恢复的扫描"""
    can_resume = should_resume_scan()
    resume_data = None
    if can_resume:
        resume_data = load_scan_progress()
        if resume_data:
            # 只返回必要的信息
            resume_data = {
                "datetime": resume_data.get("datetime"),
                "scanned_files": resume_data.get("progress", {}).get("scanned_files", 0),
                "matched_files": resume_data.get("progress", {}).get("matched_files", 0),
                "scanned_dirs": resume_data.get("progress", {}).get("scanned_dirs", 0),
                "current_drive": resume_data.get("current_drive", ""),
            }
    return jsonify({
        "can_resume": can_resume,
        "resume_data": resume_data,
    })


@app.route("/api/scan/clear_resume", methods=["POST"])
def clear_resume():
    """清除扫描进度"""
    clear_scan_progress()
    return jsonify({"success": True, "msg": "进度已清除"})


@app.route("/api/scan/stop", methods=["POST"])
def scan_stop():
    """停止扫描"""
    scanner.stop()
    return jsonify({"success": True, "msg": "扫描已停止"})


@app.route("/api/scan/pause", methods=["POST"])
def scan_pause():
    """暂停扫描"""
    ok = scanner.pause()
    return jsonify({"success": ok, "msg": "扫描已暂停" if ok else "暂停失败"})


@app.route("/api/scan/resume", methods=["POST"])
def scan_resume():
    """继续扫描"""
    ok = scanner.resume()
    return jsonify({"success": ok, "msg": "扫描已继续" if ok else "继续失败"})


@app.route("/api/scan/progress")
def scan_progress():
    """SSE 实时推送扫描进度"""
    def generate():
        last_matched = 0
        while True:
            progress = scanner.get_progress()
            current_matched = progress.get("matched_files", 0)

            # 有新结果时，附带推送新增文件
            new_items = []
            if current_matched > last_matched:
                result = scanner.get_results(
                    page=last_matched // 50 + 1,
                    page_size=current_matched - last_matched
                )
                new_items = result.get("data", [])
                last_matched = current_matched

            payload = json.dumps({
                "progress": progress,
                "new_items": new_items,
            }, ensure_ascii=False)

            yield f"data: {payload}\n\n"

            if progress["status"] in ("done", "error", "stopped"):
                # 最后推送一次完整进度
                time.sleep(0.5)
                final = scanner.get_progress()
                yield f"data: {json.dumps({'progress': final, 'new_items': [], 'finished': True}, ensure_ascii=False)}\n\n"
                break

            time.sleep(1)

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.route("/api/scan/results", methods=["GET"])
def scan_results():
    """获取扫描结果（分页+过滤）"""
    category = request.args.get("category", None)
    risk = request.args.get("risk", None)
    keyword = request.args.get("keyword", None)
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 100))

    result = scanner.get_results(
        category=category,
        risk=risk,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    return jsonify(result)


@app.route("/api/scan/summary", methods=["GET"])
def scan_summary():
    """获取分类汇总"""
    summary = scanner.get_summary()
    progress = scanner.get_progress()
    return jsonify({
        "summary": summary,
        "progress": progress,
    })

# ==================== 路径修复函数 ====================
def _fix_windows_path(path: str) -> str:
    """智能修复被损坏的 Windows 路径（反斜杠丢失是最常见问题）"""
    if not path or not isinstance(path, str):
        return path

    path = path.strip()

    # 情况1：盘符后直接跟字母（如 C:Users → C:\Users）
    if re.match(r'^[A-Za-z]:[^\\\/]', path):
        path = path[0:2] + '\\' + path[2:]

    # 情况2：统一正斜杠为反斜杠
    path = path.replace('/', '\\')

    # 情况3：多个连续反斜杠 → 保留一个
    path = re.sub(r'\\+', '\\\\', path)

    # 规范化路径
    try:
        path = os.path.normpath(path)
    except Exception:
        pass

    return path

# ─────────────────────────────────────────
# 文件操作 API
# ─────────────────────────────────────────

@app.route("/api/file/preview", methods=["POST"])
def file_preview():
    data = request.get_json() or {}
    raw_path = data.get("path", "")
    path = _fix_windows_path(raw_path)

    if not path:
        return jsonify({"type": "error", "content": "路径不能为空"})

    if not _validate_path(path):
        return jsonify({"type": "error", "content": "路径无效或不安全"})

    result = preview_file(path)
    return jsonify(result)


@app.route("/api/file/delete/trash", methods=["POST"])
def file_delete_trash():
    """移入回收站"""
    data  = request.get_json() or {}
    paths = data.get("paths", [])
    if not paths:
        return jsonify({"success": False, "msg": "未提供文件路径"})

    # ★ 过滤掉不存在或不安全的路径
    valid_paths   = [p for p in paths if _validate_path(p)]
    invalid_paths = [p for p in paths if not _validate_path(p)]

    result = delete_to_trash(valid_paths)

    # 从用户操作中学习：删除的文件不是个人文件
    if valid_paths:
        try:
            intelligent_classifier.learn_from_action(valid_paths, "delete")
        except Exception:
            pass

    # 不存在的路径也从结果集移除（已经没了）
    _remove_from_results(paths)

    if invalid_paths:
        result["invalid"] = invalid_paths
        result["invalid_count"] = len(invalid_paths)

    return jsonify({"success": True, **result})


@app.route("/api/file/delete/permanent", methods=["POST"])
def file_delete_permanent():
    """永久删除"""
    data    = request.get_json() or {}
    paths   = data.get("paths", [])
    confirm = data.get("confirm", False)

    if not confirm:
        return jsonify({"success": False, "msg": "需要确认才能永久删除"})
    if not paths:
        return jsonify({"success": False, "msg": "未提供文件路径"})

    # ★ 过滤掉不存在或不安全的路径
    valid_paths   = [p for p in paths if _validate_path(p)]
    invalid_paths = [p for p in paths if not _validate_path(p)]

    result = delete_permanently(valid_paths)

    # 从用户操作中学习：删除的文件不是个人文件
    if valid_paths:
        try:
            intelligent_classifier.learn_from_action(valid_paths, "delete")
        except Exception:
            pass

    _remove_from_results(paths)

    if invalid_paths:
        result["invalid"] = invalid_paths
        result["invalid_count"] = len(invalid_paths)

    return jsonify({"success": True, **result})


@app.route("/api/file/export", methods=["POST"])
def file_export():
    """导出文件清单"""
    data = request.get_json() or {}
    ids = data.get("ids", [])

    with scanner.results_lock:
        if ids:
            results = [r for r in scanner.results if r["id"] in ids]
        else:
            results = list(scanner.results)

    export_path = export_list(results)
    return jsonify({
        "success": True,
        "path": export_path,
        "count": len(results),
    })


@app.route("/api/file/serve", methods=["GET"])
def serve_file():
    """服务文件（用于视频/图片播放）"""
    raw_path = request.args.get("path", "")
    path = _fix_windows_path(raw_path)
    
    if not path or not _validate_path(path):
        return jsonify({"success": False, "msg": "文件不存在或路径不安全"}), 404
    
    ext = os.path.splitext(path)[1].lower()
    
    # 确定MIME类型
    mime_types = {
        ".mp4": "video/mp4",
        ".webm": "video/webm",
        ".ogg": "video/ogg",
        ".mov": "video/quicktime",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".svg": "image/svg+xml",
    }
    
    mime_type = mime_types.get(ext, "application/octet-stream")
    
    return send_file(path, mimetype=mime_type)


@app.route("/api/file/open_dir", methods=["POST"])
def open_dir():
    data = request.get_json() or {}
    raw_path = data.get("path", "")
    path = _fix_windows_path(raw_path)
    is_dir = data.get("is_dir", False)

    if not path:
        return jsonify({"success": False, "msg": "路径不能为空"})

    if not _validate_path(path):
        return jsonify({"success": False, "msg": "路径无效或不安全"})

    try:
        import subprocess
        import sys

        if is_dir:
            # 如果是目录，直接打开该目录
            os.startfile(path)
        else:
            # 如果是文件，打开目录并选中文件
            # 使用 explorer /select, 来打开目录并选中文件
            subprocess.Popen(['explorer', '/select,', path])
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "msg": f"打开失败: {str(e)}"})


# ─────────────────────────────────────────
# 工具函数
# ─────────────────────────────────────────

def _remove_from_results(paths: list):
    """从扫描结果中移除已处理的文件"""
    path_set = set(paths)
    with scanner.results_lock:
        scanner.results = [
            r for r in scanner.results if r["path"] not in path_set
        ]


def _get_disk_usage(drive: str):
    import shutil
    usage = shutil.disk_usage(drive)
    return usage.total, usage.used, usage.free


def _human_size(size: int) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"


def open_browser():
    """延迟打开浏览器"""
    time.sleep(1.2)
    webbrowser.open("http://localhost:8899")


# ─────────────────────────────────────────
# 自定义规则 API
# ─────────────────────────────────────────

@app.route("/api/custom_rules", methods=["GET"])
def api_list_rules():
    """获取所有自定义规则"""
    rules = list_rules()
    return jsonify({
        "success": True,
        "rules": rules,
        "total": len(rules),
        "condition_types": CONDITION_TYPES,
    })


def safe_reclassify():
    """安全地重新分类：只有在扫描停止时才执行"""
    # 检查扫描是否正在运行
    if scanner.is_running or scanner.progress.get("status") == "running":
        return False
    scanner.reclassify_results()
    return True


@app.route("/api/custom_rules", methods=["POST"])
def api_create_rule():
    """新建自定义规则"""
    payload = request.get_json() or {}
    errors = validate_rule_payload(payload)
    if errors:
        return jsonify({"success": False, "errors": errors})
    rule = create_rule(payload)
    # 安全重新分类
    safe_reclassify()
    return jsonify({"success": True, "rule": rule})


@app.route("/api/custom_rules/<rule_id>", methods=["PUT"])
def api_update_rule(rule_id):
    """更新自定义规则"""
    payload = request.get_json() or {}
    errors = validate_rule_payload(payload)
    if errors:
        return jsonify({"success": False, "errors": errors})
    rule = update_rule(rule_id, payload)
    if rule is None:
        return jsonify({"success": False, "errors": ["规则不存在"]})
    # 安全重新分类
    safe_reclassify()
    return jsonify({"success": True, "rule": rule})


@app.route("/api/custom_rules/<rule_id>", methods=["DELETE"])
def api_delete_rule(rule_id):
    """删除单条规则"""
    ok = delete_rule(rule_id)
    # 安全重新分类
    safe_reclassify()
    return jsonify({"success": ok, "msg": "删除成功" if ok else "规则不存在"})


@app.route("/api/custom_rules/<rule_id>/toggle", methods=["POST"])
def api_toggle_rule(rule_id):
    """启用/禁用规则"""
    data = request.get_json() or {}
    enabled = data.get("enabled", True)
    ok = toggle_rule(rule_id, enabled)
    # 安全重新分类
    safe_reclassify()
    return jsonify({"success": ok})


@app.route("/api/custom_rules/clear", methods=["POST"])
def api_clear_rules():
    """一键清除所有自定义规则"""
    count = clear_all_rules()
    # 安全重新分类
    safe_reclassify()
    return jsonify({
        "success": True,
        "cleared": count,
        "msg": f"已清除 {count} 条自定义规则",
    })


@app.route("/api/custom_rules/test", methods=["POST"])
def api_test_rule():
    """测试规则是否命中指定路径"""
    data = request.get_json() or {}
    payload = data.get("rule", {})
    test_path = data.get("path", "").strip()

    if not test_path:
        return jsonify({"success": False, "msg": "请输入测试路径"})

    # 验证规则 payload
    if not isinstance(payload, dict):
        return jsonify({"success": False, "msg": "规则格式无效"})

    # 路径不需要真实存在（content_keyword类型除外）
    result = test_rule(payload, test_path)
    return jsonify({"success": True, "result": result})

# ─────────────────────────────────────────
# 个人目录 API
# ─────────────────────────────────────────

@app.route("/api/personal_dirs", methods=["GET"])
def api_list_personal_dirs():
    """获取所有个人目录"""
    dirs = list_personal_dirs()
    return jsonify({
        "success": True,
        "dirs": dirs,
        "total": len(dirs),
    })


@app.route("/api/personal_dirs", methods=["POST"])
def api_add_personal_dir():
    """添加个人目录"""
    data = request.get_json() or {}
    dir_path = data.get("path", "").strip()
    
    if not dir_path:
        return jsonify({"success": False, "msg": "请提供目录路径"})
    if not os.path.isdir(dir_path):
        return jsonify({"success": False, "msg": "目录不存在或不是目录"})
    
    ok = add_personal_dir(dir_path)
    return jsonify({
        "success": ok,
        "msg": "添加成功" if ok else "添加失败",
    })


@app.route("/api/personal_dirs", methods=["DELETE"])
def api_remove_personal_dir():
    """移除个人目录"""
    data = request.get_json() or {}
    dir_path = data.get("path", "").strip()
    
    if not dir_path:
        return jsonify({"success": False, "msg": "请提供目录路径"})
    
    ok = remove_personal_dir(dir_path)
    return jsonify({
        "success": ok,
        "msg": "移除成功" if ok else "移除失败",
    })


@app.route("/api/personal_dirs/clear", methods=["POST"])
def api_clear_personal_dirs():
    """清空所有个人目录"""
    clear_all_personal_dirs()
    return jsonify({
        "success": True,
        "msg": "已清空所有个人目录",
    })


# ─────────────────────────────────────────
# 智能识别 API
# ─────────────────────────────────────────

from core.smart_recognizer import (
    is_suspected_personal,
    get_smart_suggestion,
    learn_from_positive_example,
    learn_from_negative_example,
    batch_learn_from_positive,
    get_learning_stats,
    _load_learned_patterns,
)
from core.personal_dirs import add_personal_dir

@app.route("/api/smart/analyze", methods=["POST"])
def api_smart_analyze():
    """分析文件是否为疑似个人内容"""
    data = request.get_json() or {}
    file_path = data.get("path", "").strip()
    
    if not file_path:
        return jsonify({"success": False, "msg": "请提供文件路径"})
    
    if not _validate_path(file_path):
        return jsonify({"success": False, "msg": "路径无效或不安全"})
    
    is_suspected, score, reason, confidence = is_suspected_personal(file_path)
    return jsonify({
        "success": True,
        "is_suspected": is_suspected,
        "score": score,
        "reason": reason,
        "confidence": confidence,
    })

@app.route("/api/smart/suggestion", methods=["POST"])
def api_smart_suggestion():
    """获取智能建议"""
    data = request.get_json() or {}
    file_path = data.get("path", "").strip()
    
    if not file_path:
        return jsonify({"success": False, "msg": "请提供文件路径"})
    
    if not _validate_path(file_path):
        return jsonify({"success": False, "msg": "路径无效或不安全"})
    
    suggestion = get_smart_suggestion(file_path)
    return jsonify({
        "success": True,
        "suggestion": suggestion,
    })

@app.route("/api/smart/learn/positive", methods=["POST"])
def api_smart_learn_positive():
    """学习正例（用户标记为个人目录）"""
    data = request.get_json() or {}
    dir_path = data.get("path", "").strip()
    file_paths = data.get("file_paths", [])
    
    if not dir_path:
        return jsonify({"success": False, "msg": "请提供目录路径"})
    
    learn_from_positive_example(dir_path, file_paths)
    
    return jsonify({
        "success": True,
        "msg": "学习成功",
    })

@app.route("/api/smart/learn/negative", methods=["POST"])
def api_smart_learn_negative():
    """学习反例（用户确认不是个人内容）"""
    data = request.get_json() or {}
    dir_path = data.get("path", "").strip()
    
    if not dir_path:
        return jsonify({"success": False, "msg": "请提供目录路径"})
    
    learn_from_negative_example(dir_path)
    return jsonify({
        "success": True,
        "msg": "学习成功",
    })

@app.route("/api/smart/learn/batch_positive", methods=["POST"])
def api_smart_learn_batch_positive():
    """批量学习正例"""
    data = request.get_json() or {}
    dir_paths = data.get("dir_paths", [])
    all_file_paths = data.get("all_file_paths", [])
    
    if not dir_paths:
        return jsonify({"success": False, "msg": "请提供目录路径列表"})
    
    batch_learn_from_positive(dir_paths, all_file_paths)
    
    return jsonify({
        "success": True,
        "msg": f"成功学习 {len(dir_paths)} 个目录",
    })

@app.route("/api/smart/mark_and_learn", methods=["POST"])
def api_smart_mark_and_learn():
    """标记目录为个人目录并学习"""
    data = request.get_json() or {}
    dir_path = data.get("path", "").strip()
    file_paths = data.get("file_paths", [])
    
    if not dir_path:
        return jsonify({"success": False, "msg": "请提供目录路径"})
    if not os.path.isdir(dir_path):
        return jsonify({"success": False, "msg": "目录不存在或不是目录"})
    
    add_personal_dir(dir_path)
    learn_from_positive_example(dir_path, file_paths)
    
    return jsonify({
        "success": True,
        "msg": "已标记并学习成功",
    })

@app.route("/api/smart/stats", methods=["GET"])
def api_smart_stats():
    """获取学习统计信息"""
    stats = get_learning_stats()
    return jsonify({
        "success": True,
        "stats": stats,
    })

@app.route("/api/smart/patterns", methods=["GET"])
def api_smart_patterns():
    """获取学习到的模式"""
    patterns = _load_learned_patterns()
    return jsonify({
        "success": True,
        "patterns": patterns,
    })


# ─────────────────────────────────────────
# 智能分类器 API
# ─────────────────────────────────────────

@app.route("/api/intelligent/classify", methods=["POST"])
def api_intelligent_classify():
    """使用智能分类器分类文件（深度分析）"""
    data = request.get_json() or {}
    file_path = data.get("path", "").strip()
    
    if not file_path:
        return jsonify({"success": False, "msg": "请提供文件路径"})
    
    if not _validate_path(file_path):
        return jsonify({"success": False, "msg": "路径无效或不安全"})
    
    try:
        # 获取文件状态信息
        stat_info = {}
        if os.path.exists(file_path):
            stat = os.stat(file_path)
            stat_info = {
                "size": stat.st_size,
                "mtime_ts": int(stat.st_mtime)
            }
        
        result = intelligent_classifier.classify_file(file_path, stat_info)
        return jsonify({
            "success": True,
            "result": result
        })
    except Exception as e:
        return jsonify({"success": False, "msg": str(e)})


@app.route("/api/intelligent/classify/fast", methods=["POST"])
def api_intelligent_classify_fast():
    """使用智能分类器分类文件（快速分析）"""
    data = request.get_json() or {}
    file_path = data.get("path", "").strip()
    
    if not file_path:
        return jsonify({"success": False, "msg": "请提供文件路径"})
    
    if not _validate_path(file_path):
        return jsonify({"success": False, "msg": "路径无效或不安全"})
    
    try:
        # 获取文件状态信息
        stat_info = {}
        if os.path.exists(file_path):
            stat = os.stat(file_path)
            stat_info = {
                "size": stat.st_size,
                "mtime_ts": int(stat.st_mtime)
            }
        
        result = intelligent_classifier.classify_file_fast(file_path, stat_info)
        return jsonify({
            "success": True,
            "result": result
        })
    except Exception as e:
        return jsonify({"success": False, "msg": str(e)})


@app.route("/api/intelligent/feedback", methods=["POST"])
def api_intelligent_feedback():
    """提供分类反馈，让智能分类器学习"""
    data = request.get_json() or {}
    file_path = data.get("path", "").strip()
    is_personal = data.get("is_personal", True)
    confidence = data.get("confidence", 1.0)
    
    if not file_path:
        return jsonify({"success": False, "msg": "请提供文件路径"})
    
    try:
        intelligent_classifier.learn_from_feedback(file_path, is_personal, confidence)
        return jsonify({
            "success": True,
            "msg": "学习成功"
        })
    except Exception as e:
        return jsonify({"success": False, "msg": str(e)})


@app.route("/api/intelligent/stats", methods=["GET"])
def api_intelligent_stats():
    """获取智能分类器学习统计信息"""
    try:
        stats = intelligent_classifier.get_learning_stats()
        return jsonify({
            "success": True,
            "stats": stats
        })
    except Exception as e:
        return jsonify({"success": False, "msg": str(e)})


@app.route("/api/intelligent/reset", methods=["POST"])
def api_intelligent_reset():
    """重置智能分类器学习数据"""
    try:
        intelligent_classifier.reset_learning()
        return jsonify({
            "success": True,
            "msg": "学习数据已重置"
        })
    except Exception as e:
        return jsonify({"success": False, "msg": str(e)})


@app.route("/api/intelligent/learn_from_logs", methods=["POST"])
def api_learn_from_logs():
    """从系统操作日志中学习用户操作习惯"""
    try:
        result = intelligent_classifier.learn_from_system_logs()
        return jsonify({
            "success": True,
            "msg": result
        })
    except Exception as e:
        return jsonify({"success": False, "msg": str(e)})


# ─────────────────────────────────────────
# 筛选结果 API
# ─────────────────────────────────────────

@app.route("/api/scan/results", methods=["POST"])
def api_scan_results():
    """获取扫描结果（支持筛选）"""
    data = request.get_json() or {}
    
    # 筛选条件
    time_range = data.get("time_range", "all")  # all, 1month, 3months, 1year, older1year, custom
    time_start = data.get("time_start")  # 自定义开始日期 (YYYY-MM-DD)
    time_end = data.get("time_end")      # 自定义结束日期 (YYYY-MM-DD)
    category = data.get("category", "all")       # all, 或分类key
    personal_only = data.get("personal_only", False)  # 只显示个人目录文件
    suspected_only = data.get("suspected_only", False)  # 只显示疑似个人内容
    page = data.get("page", 1)
    page_size = data.get("page_size", 50)
    
    with scanner.results_lock:
        results = list(scanner.results)
    
    # 应用筛选
    import time
    now_ts = int(time.time())
    
    # 时间范围筛选
    if time_range != "all":
        time_days = {
            "1month": 30,
            "3months": 90,
            "1year": 365,
        }
        if time_range in time_days:
            cutoff_ts = now_ts - (time_days[time_range] * 24 * 60 * 60)
            results = [r for r in results if r.get("mtime_ts", 0) >= cutoff_ts]
        elif time_range == "older1year":
            cutoff_ts = now_ts - (365 * 24 * 60 * 60)
            results = [r for r in results if r.get("mtime_ts", 0) < cutoff_ts]
        elif time_range == "custom" and time_start and time_end:
            # 自定义日期范围
            from datetime import datetime
            try:
                start_ts = int(datetime.strptime(time_start, "%Y-%m-%d").timestamp())
                end_ts = int(datetime.strptime(time_end + " 23:59:59", "%Y-%m-%d %H:%M:%S").timestamp())
                results = [r for r in results if start_ts <= r.get("mtime_ts", 0) <= end_ts]
            except:
                pass
    
    # 分类筛选
    if category != "all":
        results = [r for r in results if r.get("category_key") == category]
    
    # 个人目录筛选
    if personal_only:
        results = [r for r in results if r.get("is_personal", False)]
    
    # 疑似个人内容筛选
    if suspected_only:
        results = [r for r in results if r.get("is_suspected", False)]
    
    # 🔴 检查文件是否存在，过滤掉已删除的文件
    valid_results = []
    removed_count = 0
    
    for r in results:
        path = r.get("path", "")
        if path and os.path.exists(path):
            valid_results.append(r)
        else:
            removed_count += 1
    
    results = valid_results
    
    # 分页
    total = len(results)
    start = (page - 1) * page_size
    end = start + page_size
    paged_results = results[start:end]
    
    return jsonify({
        "success": True,
        "results": paged_results,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
        "removed_count": removed_count,
    })


# ─────────────────────────────────────────
# 启动入口
# ─────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 50)
    print("  离职文件清理工具")
    print("  访问地址: http://localhost:8899")
    print("  按 Ctrl+C 退出")
    print("=" * 50)

    # 自动打开浏览器
    t = threading.Thread(target=open_browser, daemon=True)
    t.start()

    app.run(
        host="127.0.0.1",
        port=8899,
        debug=False,
        threaded=True,
    )
