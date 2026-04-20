import os
import time
import threading
import hashlib
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue

from .classifier import classify_file, should_exclude_dir
from .rules import (
    USER_PROFILE,
    SCAN_RULES,
    SOFTWARE_ROOT_DIRS,
    SOFTWARE_CORE_KEYWORDS,
    KNOWN_SOFTWARE_DIRS,
    KNOWN_CACHE_DIRS,
)
from .progress_manager import (
    save_scan_progress,
    load_scan_progress,
    clear_scan_progress,
    should_resume_scan,
)
from .personal_dirs import is_personal_dir
from .smart_recognizer import is_suspected_personal


# ─────────────────────────────────────────
# 软件目录识别
# ─────────────────────────────────────────

def _normalize(path: str) -> str:
    return os.path.normpath(path).lower()


def _check_parent_for_software(dir_path: str, checked_paths: set) -> tuple[bool, str]:
    """检查父目录是否是软件目录（避免递归）
    
    Returns:
        (is_parent_software, parent_software_name)
    """
    parent = os.path.dirname(dir_path)
    if not parent or parent == dir_path:
        return False, ""
    
    parent_norm = _normalize(parent)
    if parent_norm in checked_paths:
        return False, ""
    
    checked_paths.add(parent_norm)
    
    # 先用核心关键词检查父目录（不触发智能分析，避免递归）
    parent_dir_name = os.path.basename(parent_norm)
    for keyword, name in SOFTWARE_CORE_KEYWORDS.items():
        kw_lower = keyword.lower()
        if kw_lower in parent_dir_name or kw_lower in parent_norm:
            return True, name
    
    # 再检查精确匹配
    for keyword, name in KNOWN_SOFTWARE_DIRS.items():
        if keyword.lower() == parent_dir_name:
            return True, name
    
    # 继续向上检查
    return _check_parent_for_software(parent, checked_paths)


def _analyze_dir_intelligently(dir_path: str) -> tuple[bool, str]:
    """智能分析目录是否为软件目录（不依赖完整关键词列表）
    
    Returns:
        (is_software, software_name)
    """
    norm = _normalize(dir_path)
    dir_name = os.path.basename(norm)
    
    # 特征1：检查是否在典型的软件安装位置
    software_locations = [
        "program files",
        "program files (x86)",
        "appdata\\local",
        "appdata\\roaming",
        "appdata\\locallow",
    ]
    in_software_location = any(loc in norm for loc in software_locations)
    
    # 特征2：检查目录名是否包含典型软件相关词汇
    software_indicators = [
        "app", "application", "bin", "lib", "library", "sdk", "tools",
        "assets", "static", "webcontent", "resources", "data", "res",
        "plugin", "plugins", "extension", "extensions", "module", "modules",
        "build", "dist", "release", "debug", "obj",
    ]
    has_software_indicator = any(ind in dir_name or ind in norm for ind in software_indicators)
    
    # 特征3：检查目录结构（快速查看子目录）
    has_software_structure = False
    try:
        if os.path.isdir(dir_path):
            subdirs = []
            try:
                with os.scandir(dir_path) as it:
                    for entry in it:
                        if entry.is_dir(follow_symlinks=False):
                            subdirs.append(entry.name.lower())
                            if len(subdirs) >= 10:
                                break
            except (PermissionError, OSError):
                pass
            
            # 检查是否有典型的软件子目录
            typical_subdirs = ["bin", "lib", "assets", "static", "res", "resources", "data"]
            has_software_structure = any(sd in subdirs for sd in typical_subdirs)
    except Exception:
        pass
    
    # 特征4：检查是否在已识别软件目录的子目录中（使用非递归方式）
    parent_is_software, parent_software_name = _check_parent_for_software(dir_path, set())
    
    # 综合判断
    score = 0
    reasons = []
    
    if in_software_location:
        score += 3
        reasons.append("在软件安装位置")
    
    if has_software_indicator:
        score += 2
        reasons.append("包含软件特征词")
    
    if has_software_structure:
        score += 2
        reasons.append("有软件目录结构")
    
    if parent_is_software:
        score += 4
        reasons.append("父目录是软件目录")
    
    # 如果分数足够高，认为是软件目录
    if score >= 3:
        # 尝试获取一个合理的软件名称
        software_name = dir_name
        
        # 如果是父目录的子目录，使用父目录的软件名
        if parent_is_software and parent_software_name:
            software_name = parent_software_name
        
        return True, software_name
    
    return False, ""


def _get_software_name(dir_path: str) -> str | None:
    """已知软件 → 返回软件名，未知 → 返回 None
    为离职清理场景优化：四层识别策略，避免命名变体漏判
    
    识别优先级：
    1. 核心关键词识别（最高优先级，只要包含就识别）
    2. 智能分析识别（自动判断）
    3. 精确匹配目录名
    4. 路径/分隔符模糊匹配
    """
    norm = _normalize(dir_path)
    dir_name = os.path.basename(norm)
    
    # 1. 最高优先级：核心关键词识别
    # 对于常用软件，只要目录名或路径中包含核心关键词就识别
    # 这样可以避免命名变体（wechat files、wechat_files、xwechat_files等）的漏判
    for keyword, name in SOFTWARE_CORE_KEYWORDS.items():
        kw_lower = keyword.lower()
        if kw_lower in dir_name or kw_lower in norm:
            return name
    
    # 2. 第二优先级：智能分析识别
    # 不依赖关键词，自动分析目录特征
    is_software, software_name = _analyze_dir_intelligently(dir_path)
    if is_software:
        return software_name
    
    # 3. 第三优先级：精确匹配目录名（最准确）
    for keyword, name in KNOWN_SOFTWARE_DIRS.items():
        if keyword.lower() == dir_name:
            return name
    
    # 4. 第四优先级：完整路径匹配（带路径分隔符）
    for keyword, name in KNOWN_SOFTWARE_DIRS.items():
        kw_lower = keyword.lower()
        if ('\\' + kw_lower + '\\' in norm or 
            norm.endswith('\\' + kw_lower)):
            return name
    
    # 5. 第五优先级：目录名包含完整关键词（带分隔符）
    for keyword, name in KNOWN_SOFTWARE_DIRS.items():
        kw_lower = keyword.lower()
        if len(keyword) >= 3:
            if (dir_name.startswith(kw_lower + ' ') or 
                dir_name.endswith(' ' + kw_lower) or
                ' ' + kw_lower + ' ' in dir_name or
                dir_name.startswith(kw_lower + '_') or
                dir_name.endswith('_' + kw_lower) or
                '_' + kw_lower + '_' in dir_name or
                dir_name.startswith(kw_lower + '-') or
                dir_name.endswith('-' + kw_lower) or
                '-' + kw_lower + '-' in dir_name):
                return name
    
    # 6. 第六优先级：对较长的关键词（≥5字符），适当放宽匹配
    for keyword, name in KNOWN_SOFTWARE_DIRS.items():
        kw_lower = keyword.lower()
        if len(keyword) >= 5:
            if kw_lower in dir_name:
                return name
    
    return None


def _is_software_root_child(dir_path: str) -> bool:
    """是否是软件根目录（AppData/Roaming、AppData/Local）的直接子目录，且看起来像软件目录"""
    parent = os.path.dirname(os.path.normpath(dir_path))
    parent_norm = _normalize(parent)
    dir_name = os.path.basename(_normalize(dir_path))
    
    is_root_child = False
    for root in SOFTWARE_ROOT_DIRS:
        if _normalize(root) == parent_norm:
            is_root_child = True
            break
    
    if not is_root_child:
        return False
    
    # 排除一些明显不是软件目录的情况
    exclude_names = [
        "desktop", "documents", "downloads", "pictures", 
        "videos", "music", "contacts", "favorites",
        "links", "saved games", "searches", "3d objects",
        "onedrive", "百度网盘", "wechat files", "tencent files",
        "xwechat files", "wechat_files", "xwechat_files",
        "temp", "tmp", "cache", "caches", "logs"
    ]
    
    if dir_name in exclude_names:
        return False
    
    # 排除太短的目录名（小于3个字符）
    if len(dir_name) < 3:
        return False
    
    # 排除纯数字的目录名
    if dir_name.isdigit():
        return False
    
    return True


def _is_software_dir(dir_path: str) -> bool:
    """是否应识别为软件目录"""
    if _get_software_name(dir_path) is not None:
        return True
    if _is_software_root_child(dir_path):
        return True
    return False


def _get_cache_name(dir_path: str) -> str | None:
    """已知缓存目录 → 返回缓存名，未知 → 返回 None"""
    norm = _normalize(dir_path)
    dir_name = os.path.basename(norm)
    
    # 第一优先级：精确匹配目录名
    for keyword, name in KNOWN_CACHE_DIRS.items():
        if keyword.lower() == dir_name:
            return name
    
    # 第二优先级：目录名包含关键词（缓存识别可以更宽松）
    for keyword, name in KNOWN_CACHE_DIRS.items():
        kw_lower = keyword.lower()
        if kw_lower in dir_name:
            return name
    
    # 第三优先级：路径中包含完整关键词（带路径分隔符）
    for keyword, name in KNOWN_CACHE_DIRS.items():
        kw_lower = keyword.lower()
        if ('\\' + kw_lower + '\\' in norm or 
            norm.endswith('\\' + kw_lower) or
            norm.startswith(kw_lower + '\\')):
            return name
    
    # 第四优先级：路径中包含关键词子字符串
    for keyword, name in KNOWN_CACHE_DIRS.items():
        if keyword.lower() in norm:
            return name
    
    return None


def _is_cache_dir(dir_path: str) -> bool:
    """是否应识别为缓存目录"""
    return _get_cache_name(dir_path) is not None


def _is_user_created_dir(dir_path: str, root_path: str) -> bool:
    """是否为用户自建目录（非系统/非软件目录）"""
    norm = _normalize(dir_path)
    dir_name = os.path.basename(norm)
    
    # 检查是否直接在根目录下
    parent = os.path.dirname(os.path.normpath(dir_path))
    if _normalize(parent) != _normalize(root_path):
        return False
    
    # 排除一些常见的系统默认目录
    exclude_dir_names = [
        "desktop", "documents", "downloads", "pictures", 
        "videos", "music", "appdata", "contacts", "favorites",
        "links", "saved games", "searches", "3d objects",
        "onedrive", "百度网盘", "wechat files", "tencent files",
        "xwechat files", "wechat_files", "xwechat_files"
    ]
    
    if dir_name.lower() in exclude_dir_names:
        return False
    
    return True


def _path_truly_exists(path: str) -> bool:
    """
    严格校验路径是否真实存在
    同时处理：符号链接失效 / 网络路径 / 权限问题
    """
    try:
        if not os.path.lexists(path):
            return False
        if not os.path.exists(path):
            return False
        os.stat(path)
        return True
    except (OSError, PermissionError):
        return False


# ─────────────────────────────────────────
# Scanner
# ─────────────────────────────────────────

class Scanner:
    def __init__(self):
        self.is_running   = False
        self.is_paused    = False
        self.results      = []
        self.results_lock = threading.Lock()
        self.progress     = self._empty_progress()
        self._stop_event  = threading.Event()
        self._pause_event = threading.Event()
        self._scan_thread = None
        self._processed_paths = set()
        self._processed_paths_lock = threading.Lock()
        self._current_drive = ""
        self._extra_exclude = []
        self._resume_data = None
        self._last_progress_save = 0
        
        # 跟踪软件目录和缓存目录，避免处理其中的文件
        self._special_dirs = set()
        self._special_dirs_lock = threading.Lock()
        
        # 线程池配置
        self._max_workers = max(4, os.cpu_count() or 4)
        self._file_queue = Queue(maxsize=10000)
    
    # ── 公开接口 ──────────────────────────────

    def start(self, drives: list = None, extra_exclude: list = None, resume: bool = False):
        if self.is_running:
            return False
        
        self._stop_event.clear()
        self._extra_exclude = extra_exclude or []
        self._resume_data = None
        
        if resume and should_resume_scan():
            self._resume_data = load_scan_progress()
            if self._resume_data:
                self.results = self._resume_data.get("results", [])
                self._processed_paths = set(self._resume_data.get("processed_paths", []))
                self._special_dirs = set()
                self.progress = self._resume_data.get("progress", self._empty_progress("running"))
                self.progress["status"] = "running"
                if "start_time" not in self.progress:
                    self.progress["start_time"] = time.time()
        else:
            self.results = []
            self._processed_paths = set()
            self._special_dirs = set()
            self.progress = self._empty_progress("running")
            clear_scan_progress()
        
        self.is_running = True
        self._scan_thread = threading.Thread(
            target=self._scan_worker,
            args=(drives,),
            daemon=True,
        )
        self._scan_thread.start()
        return True

    def stop(self):
        self._stop_event.set()
        self._pause_event.set()
        self.is_running = False
        self.is_paused = False
        self.progress["status"] = "stopped"
        self._save_current_progress()
    
    def pause(self):
        """暂停扫描"""
        if not self.is_running or self.is_paused:
            return False
        self.is_paused = True
        self._pause_event.clear()
        self.progress["status"] = "paused"
        self._save_current_progress()
        return True
    
    def resume(self):
        """继续扫描"""
        if not self.is_running or not self.is_paused:
            return False
        self.is_paused = False
        self._pause_event.set()
        self.progress["status"] = "running"
        return True

    def get_results(self, category=None, risk=None,
                    keyword=None, page=1, page_size=100):
        with self.results_lock:
            data = list(self.results)
        if category:
            data = [r for r in data if r["category_key"] == category]
        if risk:
            data = [r for r in data if r["risk"] == risk]
        if keyword:
            kw = keyword.lower()
            data = [r for r in data
                    if kw in r["name"].lower() or kw in r["path"].lower()]
        total = len(data)
        start = (page - 1) * page_size
        return {
            "total":     total,
            "page":      page,
            "page_size": page_size,
            "data":      data[start: start + page_size],
        }

    def get_summary(self):
        with self.results_lock:
            data = list(self.results)
        summary = {}
        for item in data:
            key = item["category_key"]
            if key not in summary:
                summary[key] = {
                    "key":          key,
                    "label":        item["category_label"],
                    "icon":         item["category_icon"],
                    "risk":         item["risk"],
                    "color":        item["color"],
                    "count":        0,
                    "total_size":   0,
                    "is_dir_group": item.get("is_dir", False),
                }
            summary[key]["count"] += 1
        return list(summary.values())

    def get_progress(self):
        p = dict(self.progress)
        if p["start_time"]:
            p["elapsed"] = round(time.time() - p["start_time"], 1)
        return p

    def reclassify_results(self):
        """重新分类已有的扫描结果（在自定义规则变更后调用）"""
        from .rules import SCAN_RULES
        
        with self.results_lock:
            new_results = []
            for item in self.results:
                # 跳过目录项，只重新分类文件
                if item.get("is_dir", False):
                    new_results.append(item)
                    continue
                
                # 重新分类文件
                category = classify_file(item["path"])
                if category is not None:
                    item.update({
                        "category_key": category["key"],
                        "category_label": category["label"],
                        "category_icon": category["icon"],
                        "risk": category["risk"],
                        "color": category["color"],
                        "match_reason": category["match_reason"],
                    })
                    new_results.append(item)
                else:
                    cat_key = item.get("category_key", "")
                    if cat_key.startswith("custom_"):
                        continue
                    else:
                        new_results.append(item)
            self.results = new_results

    # ── 进度保存 ──────────────────────────────

    def _save_current_progress(self):
        """保存当前扫描进度"""
        try:
            with self.results_lock, self._processed_paths_lock:
                data = {
                    "progress": dict(self.progress),
                    "results": list(self.results),
                    "processed_paths": list(self._processed_paths),
                    "current_drive": self._current_drive,
                    "extra_exclude": self._extra_exclude,
                }
                save_scan_progress(data)
        except Exception:
            pass

    def _should_save_progress(self) -> bool:
        """是否应该保存进度（每10秒保存一次）"""
        now = time.time()
        if now - self._last_progress_save >= 10:
            self._last_progress_save = now
            return True
        return False

    # ── 扫描主流程 ────────────────────────────

    def _scan_worker(self, drives):
        try:
            if not drives:
                drives = self._get_all_drives()
            
            # 如果是恢复扫描，使用保存的驱动器
            if self._resume_data and "current_drive" in self._resume_data:
                saved_drive = self._resume_data.get("current_drive")
                if saved_drive in drives:
                    idx = drives.index(saved_drive)
                    drives = drives[idx:]
            
            # 设置 pause_event 为已设置（初始状态不暂停）
            self._pause_event.set()
            
            for drive in drives:
                if self._stop_event.is_set():
                    break
                
                # 检查暂停
                self._check_pause()
                
                self._current_drive = drive
                self.progress["current_drive"] = drive
                self._scan_drive(drive)
                
                if self._should_save_progress():
                    self._save_current_progress()
            
            self.progress["status"] = "done"
            clear_scan_progress()
        except Exception as e:
            self.progress["status"] = "error"
            self.progress["error"]  = str(e)
            self._save_current_progress()
        finally:
            self.is_running = False
            self.is_paused = False
    
    def _check_pause(self):
        """检查是否暂停，如果暂停则等待"""
        while not self._stop_event.is_set() and not self._pause_event.is_set():
            time.sleep(0.1)

    def _scan_drive(self, drive_path: str):
        if drive_path.upper().startswith("C:"):
            roots = [USER_PROFILE]
        else:
            roots = [drive_path]
        for root in roots:
            if _path_truly_exists(root):
                self._walk_directory(root)

    def _walk_directory(self, root_path: str):
        try:
            for dirpath, dirnames, filenames in os.walk(
                root_path, topdown=True,
                onerror=self._handle_walk_error,
                followlinks=False,
            ):
                if self._stop_event.is_set():
                    break
                
                # 检查暂停
                self._check_pause()

                self.progress["current_path"] = dirpath
                self.progress["scanned_dirs"] += 1

                # 检查当前目录是否应该被排除
                dirpath_norm = _normalize(dirpath)
                is_excluded = False
                
                for ex_path in self._extra_exclude:
                    ex_path_norm = _normalize(ex_path)
                    if dirpath_norm == ex_path_norm or dirpath_norm.startswith(ex_path_norm + os.sep):
                        is_excluded = True
                        break
                
                if is_excluded or should_exclude_dir(dirpath):
                    dirnames[:] = []
                    continue
                
                # 检查当前目录本身是否是软件目录或缓存目录
                # 如果是，则处理它并跳过该目录下的所有内容
                dir_is_processed = False
                with self._processed_paths_lock:
                    if dirpath in self._processed_paths:
                        dir_is_processed = True
                
                if not dir_is_processed:
                    if _is_cache_dir(dirpath):
                        self._process_cache_dir(dirpath)
                        dirnames[:] = []
                        continue
                    
                    if _is_software_dir(dirpath):
                        self._process_software_dir(dirpath)
                        dirnames[:] = []
                        continue

                kept = []
                for d in dirnames:
                    full_sub = os.path.join(dirpath, d)

                    if not _path_truly_exists(full_sub):
                        continue

                    # 检查子目录是否在额外排除列表中
                    sub_excluded = False
                    full_sub_norm = _normalize(full_sub)
                    for ex_path in self._extra_exclude:
                        ex_path_norm = _normalize(ex_path)
                        if full_sub_norm == ex_path_norm or full_sub_norm.startswith(ex_path_norm + os.sep):
                            sub_excluded = True
                            break
                    if sub_excluded:
                        continue

                    if should_exclude_dir(full_sub):
                        continue

                    if _is_cache_dir(full_sub):
                        self._process_cache_dir(full_sub)
                        continue

                    if _is_software_dir(full_sub):
                        self._process_software_dir(full_sub)
                        continue

                    kept.append(d)

                dirnames[:] = kept

                if _normalize(dirpath) == _normalize(root_path):
                    for d in dirnames:
                        full_sub = os.path.join(dirpath, d)
                        if _path_truly_exists(full_sub) and _is_user_created_dir(full_sub, root_path):
                            self._process_user_dir(full_sub)

                # 检查当前目录是否在特殊目录中，如果是则跳过文件处理
                dirpath_norm = _normalize(dirpath)
                is_special_dir = False
                with self._special_dirs_lock:
                    for special_dir in self._special_dirs:
                        if dirpath_norm == special_dir or dirpath_norm.startswith(special_dir + os.sep):
                            is_special_dir = True
                            break
                
                # 另外检查当前目录是否已被处理（如果是软件目录或缓存目录）
                if not is_special_dir:
                    with self._processed_paths_lock:
                        if dirpath in self._processed_paths:
                            is_special_dir = True
                
                if is_special_dir:
                    continue

                # 收集文件并使用多线程处理
                files_to_process = []
                for filename in filenames:
                    if self._stop_event.is_set():
                        break
                    full_file = os.path.join(dirpath, filename)
                    
                    with self._processed_paths_lock:
                        if full_file in self._processed_paths:
                            continue
                    
                    if _path_truly_exists(full_file):
                        files_to_process.append(full_file)
                        self.progress["scanned_files"] += 1

                if files_to_process:
                    self._process_files_batch(files_to_process)

                if self._should_save_progress():
                    self._save_current_progress()

        except PermissionError:
            pass
        except Exception:
            pass

    def _process_files_batch(self, file_paths: list):
        """批量处理文件（使用线程池）"""
        if not file_paths:
            return
        
        # 如果已停止，直接返回
        if self._stop_event.is_set():
            return
        
        # 使用更简单的方式处理，避免复杂的取消逻辑
        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            futures = []
            for fp in file_paths:
                if self._stop_event.is_set():
                    break
                futures.append(executor.submit(self._process_file_safe, fp))
            
            # 等待所有任务完成或停止信号
            for future in futures:
                if self._stop_event.is_set():
                    break
                try:
                    future.result(timeout=0.1)
                except Exception:
                    pass

    def _process_file_safe(self, file_path: str):
        """安全处理单个文件（线程安全）"""
        try:
            self._process_file(file_path)
        except Exception:
            pass

    # ── 软件目录处理 ──────────────────────────

    def _process_software_dir(self, dir_path: str):
        """软件目录整体标记"""
        try:
            with self._processed_paths_lock:
                if dir_path in self._processed_paths:
                    return
                self._processed_paths.add(dir_path)
            
            # 添加到特殊目录集合，避免处理该目录下的文件
            with self._special_dirs_lock:
                self._special_dirs.add(_normalize(dir_path))
            
            if not _path_truly_exists(dir_path):
                return

            software_name = _get_software_name(dir_path)
            dir_name      = os.path.basename(dir_path)
            is_known      = software_name is not None

            if not is_known:
                software_name = dir_name

            stat  = os.stat(dir_path)
            mtime = datetime.fromtimestamp(stat.st_mtime).strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            self.progress["matched_files"] += 1

            item = {
                "id":             hashlib.md5(
                                    dir_path.encode("utf-8")
                                  ).hexdigest(),
                "name":           (
                                    f"{software_name} 数据目录"
                                    if is_known
                                    else f"未知软件目录 ({dir_name})"
                                  ),
                "path":           dir_path,
                "dir":            os.path.dirname(dir_path),
                "size":           0,
                "size_human":     "目录",
                "mtime":          mtime,
                "ctime":          mtime,
                "ext":            "",
                "is_dir":         True,
                "is_known":       is_known,
                "software_name":  software_name,
                "dir_name":       dir_name,
                "category_key":   "software",
                "category_label": "软件目录",
                "category_icon":  "💾",
                "risk":           "low",
                "color":          "#722ed1",
                "match_reason":   [
                                    "known_software" if is_known
                                    else "software_root_child"
                                  ],
            }

            with self.results_lock:
                existing = {r["path"] for r in self.results}
                if dir_path not in existing:
                    self.results.append(item)

        except PermissionError:
            pass
        except Exception:
            pass

    def _process_cache_dir(self, dir_path: str):
        """应用缓存目录处理"""
        try:
            with self._processed_paths_lock:
                if dir_path in self._processed_paths:
                    return
                self._processed_paths.add(dir_path)
            
            # 添加到特殊目录集合，避免处理该目录下的文件
            with self._special_dirs_lock:
                self._special_dirs.add(_normalize(dir_path))
            
            if not _path_truly_exists(dir_path):
                return

            cache_name = _get_cache_name(dir_path)
            dir_name = os.path.basename(dir_path)
            is_known = cache_name is not None

            if not is_known:
                cache_name = dir_name

            stat = os.stat(dir_path)
            mtime = datetime.fromtimestamp(stat.st_mtime).strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            self.progress["matched_files"] += 1

            item = {
                "id": hashlib.md5(dir_path.encode("utf-8")).hexdigest(),
                "name": f"{cache_name} 缓存" if is_known else f"缓存目录 ({dir_name})",
                "path": dir_path,
                "dir": os.path.dirname(dir_path),
                "size": 0,
                "size_human": "目录",
                "mtime": mtime,
                "ctime": mtime,
                "ext": "",
                "is_dir": True,
                "is_known": is_known,
                "software_name": cache_name,
                "dir_name": dir_name,
                "category_key": "cache",
                "category_label": "应用缓存",
                "category_icon": "🗑️",
                "risk": "low",
                "color": "#faad14",
                "match_reason": ["cache_dir"],
            }

            with self.results_lock:
                existing = {r["path"] for r in self.results}
                if dir_path not in existing:
                    self.results.append(item)

        except PermissionError:
            pass
        except Exception:
            pass

    def _process_user_dir(self, dir_path: str):
        """用户自建目录处理"""
        try:
            with self._processed_paths_lock:
                if dir_path in self._processed_paths:
                    return
                self._processed_paths.add(dir_path)
            
            if not _path_truly_exists(dir_path):
                return

            dir_name = os.path.basename(dir_path)
            stat = os.stat(dir_path)
            mtime = datetime.fromtimestamp(stat.st_mtime).strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            self.progress["matched_files"] += 1

            item = {
                "id": hashlib.md5(dir_path.encode("utf-8")).hexdigest(),
                "name": dir_name,
                "path": dir_path,
                "dir": os.path.dirname(dir_path),
                "size": 0,
                "size_human": "目录",
                "mtime": mtime,
                "ctime": mtime,
                "ext": "",
                "is_dir": True,
                "is_known": False,
                "software_name": "",
                "dir_name": dir_name,
                "category_key": "user_dir",
                "category_label": "自建目录",
                "category_icon": "📁",
                "risk": "medium",
                "color": "#1890ff",
                "match_reason": ["user_created"],
            }

            with self.results_lock:
                existing = {r["path"] for r in self.results}
                if dir_path not in existing:
                    self.results.append(item)

        except PermissionError:
            pass
        except Exception:
            pass

    # ── 文件处理 ──────────────────────────────

    def _process_file(self, file_path: str):
        """处理单个文件"""
        try:
            with self._processed_paths_lock:
                if file_path in self._processed_paths:
                    return
                self._processed_paths.add(file_path)

            category = classify_file(file_path)
            
            # 检查是否在个人目录中
            file_dir = os.path.dirname(file_path)
            is_personal = is_personal_dir(file_dir)
            
            # 获取文件stat信息
            if not _path_truly_exists(file_path):
                return
            
            stat  = os.stat(file_path)
            size  = stat.st_size
            mtime = datetime.fromtimestamp(stat.st_mtime).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            ctime = datetime.fromtimestamp(stat.st_ctime).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            mtime_ts = int(stat.st_mtime)
            ctime_ts = int(stat.st_ctime)
            
            stat_info = {
                "size": size,
                "mtime_ts": mtime_ts,
                "ctime_ts": ctime_ts,
            }
            
            # 检查是否为疑似个人内容（增强版）
            is_suspected = False
            suspected_score = 0
            suspected_reason = ""
            suspected_confidence = 0.0
            if not is_personal:
                is_suspected, suspected_score, suspected_reason, suspected_confidence = is_suspected_personal(file_path, stat_info)
            
            # 如果是个人目录或疑似个人内容，即使没有分类也要保留
            if category is None and not is_personal and not is_suspected:
                return
            if category and category.get("key") == "software":
                return

            self.progress["total_size"]    += size
            self.progress["matched_files"] += 1

            # 如果是个人目录但没有分类，设置默认分类
            if is_personal and category is None:
                category = {
                    "key": "personal_dir",
                    "label": "个人目录文件",
                    "icon": "🏠",
                    "risk": "medium",
                    "color": "#1890ff",
                    "match_reason": ["personal_dir"],
                }
            # 如果是疑似个人内容但没有分类，设置默认分类
            elif is_suspected and category is None:
                category = {
                    "key": "suspected_personal",
                    "label": "疑似个人内容",
                    "icon": "❓",
                    "risk": "medium",
                    "color": "#faad14",
                    "match_reason": ["suspected_personal"],
                }

            with self.results_lock:
                self.results.append({
                    "id":             hashlib.md5(
                                        file_path.encode("utf-8")
                                      ).hexdigest(),
                    "name":           os.path.basename(file_path),
                    "path":           file_path,
                    "dir":            os.path.dirname(file_path),
                    "size":           size,
                    "size_human":     self._human_size(size),
                    "mtime":          mtime,
                    "ctime":          ctime,
                    "mtime_ts":       mtime_ts,
                    "ctime_ts":       ctime_ts,
                    "ext":            Path(file_path).suffix.lower(),
                    "is_dir":         False,
                    "is_known":       True,
                    "software_name":  "",
                    "dir_name":       "",
                    "category_key":   category["key"],
                    "category_label": category["label"],
                    "category_icon":  category["icon"],
                    "risk":           category["risk"],
                    "color":          category["color"],
                    "match_reason":   category["match_reason"],
                    "is_personal":    is_personal,
                    "is_suspected":   is_suspected,
                    "suspected_score": suspected_score,
                    "suspected_reason": suspected_reason,
                    "suspected_confidence": suspected_confidence,
                })

        except PermissionError:
            pass
        except FileNotFoundError:
            pass
        except Exception:
            pass

    # ── 工具方法 ──────────────────────────────

    def _get_all_drives(self) -> list:
        drives = []
        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            drive = f"{letter}:\\"
            if _path_truly_exists(drive):
                drives.append(drive)
        return drives

    def _handle_walk_error(self, error):
        pass

    @staticmethod
    def _empty_progress(status="idle") -> dict:
        return {
            "status":        status,
            "current_path":  "",
            "scanned_files": 0,
            "matched_files": 0,
            "scanned_dirs":  0,
            "total_size":    0,
            "start_time":    time.time() if status == "running" else None,
            "elapsed":       0,
            "current_drive": "",
        }

    @staticmethod
    def _human_size(size: int) -> str:
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"


scanner = Scanner()
