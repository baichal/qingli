import os
import json
import re
import time
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from collections import Counter

PERSONAL_KEYWORDS = [
    "我的", "私人", "个人", "private", "personal", "my", "mine",
    "简历", "resume", "cv", "身份证", "护照", "passport", "idcard",
    "合同", "contract", "offer", "薪资", "工资", "salary", "payroll",
    "银行", "bank", "保险", "insurance", "医疗", "medical", "health",
    "日记", "diary", "笔记", "note", "备忘录", "memo",
    "照片", "photo", "picture", "image", "pic", "相册", "album",
    "视频", "video", "movie", "film", "音乐", "music", "song", "audio",
    "下载", "download", "桌面", "desktop", "文档", "document", "doc",
    "备份", "backup", "存档", "archive", "个人项目", "project",
    "家庭", "family", "旅行", "travel", "旅游", "trip", "vacation",
    "婚礼", "wedding", "生日", "birthday", "纪念日", "anniversary",
]

PERSONAL_FILENAME_PATTERNS = [
    r"简历", r"resume", r"cv", r"身份证", r"护照", r"id.*card",
    r"合同", r"contract", r"offer", r"薪资", r"工资", r"salary",
    r"银行", r"bank", r"保险", r"insurance", r"医疗", r"medical",
    r"日记", r"diary", r"笔记", r"note", r"个人", r"私人",
    r"my.*file", r"personal.*file", r"备份", r"backup", r"存档",
    r"旅行", r"travel", r"旅游", r"trip", r"照片", r"photo",
    r"IMG_\d+", r"DSC_\d+", r"VID_\d+", r"微信图片", r"微信截图",
    r"mmexport\d+", r"Screenshot_\d+", r"屏幕截图", r"截屏",
]

PERSONAL_EXTENSIONS = [
    ".docx", ".doc", ".pdf", ".xlsx", ".xls", ".pptx", ".ppt",
    ".txt", ".md", ".rtf", ".odt", ".ods", ".odp", ".wps",
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp",
    ".heic", ".heif", ".raw", ".psd", ".ai", ".svg",
    ".mp4", ".avi", ".mov", ".mkv", ".flv", ".wmv", ".webm",
    ".mp3", ".wav", ".flac", ".aac", ".m4a", ".wma",
    ".zip", ".rar", ".7z", ".tar", ".gz", ".bz2",
    ".eml", ".msg", ".pst", ".mbox",
]

PROGRAM_DIRS = [
    # Windows 系统目录
    "program files", "program files (x86)", "windows", "winnt",
    "programdata", "appdata", "local settings",
    
    # 常见软件数据目录
    "appdata\\local", "appdata\\roaming", "appdata\\locallow",
    
    # 开发工具目录
    ".git", "node_modules", "venv", "virtualenv", "__pycache__", ".venv",
    "build", "dist", "target", "obj", "bin", "lib",
    
    # 缓存/临时目录
    "temp", "tmp", "cache", "caches", "crashpad", "crash reports",
    "logs", "log", "gpu cache", "code cache", "shader cache",
    "cachestorage", "service worker", "autosave", "auto-save",
    "render cache", "rendercache", "media cache", "mediacache",
    "preview cache", "previewcache", "proxy files", "proxyfiles",
    "thumbnails", "thumbnail", "draft", "drafts",
    
    # SDK/工具目录
    "sdk", "ndk", "gradle", "maven", ".gradle", ".m2",
    "go/pkg", "gopath", ".cargo", ".gem",
    
    # 常见软件目录
    "wechat files", "wechat_files", "xwechat files", "xwechat_files",
    "tencent files", "dingtalk", "lark", "feishu",
    "wxwork", "telegram desktop", "microsoft teams", "slack",
    "discord", "skype", "thunderbird", "foxmail", "netease mail master",
    "outlook", "baidunetdisk", "baiduyunguanjia", "onedrive",
    "nutstore", "dropbox", "googledrive", "box", "google\\chrome",
    "microsoft\\edge", "mozilla\\firefox", "brave-browser",
    "opera software", "vivaldi", "360chrome", "360se6", "code",
    "jetbrains", "postman", "insomnia", "sourcetree", "github desktop",
    "gitkraken", "dbeaver", "navicat", "hbuilderx", "wechatdevtools",
    "android studio", "xshell", "xftp", "finalshell", "terminus",
    "mobaxterm", "notion", "obsidian", "typora", "onenote", "evernote",
    "youdaonote", "wiz", "logseq", "roamresearch", "netease\\cloudmusic",
    "qqmusiccache", "qqmusic", "kugou", "kuwo", "spotify", "iqiyi",
    "youku", "tencentvideo", "mango", "bilibili", "potplayer", "vlc",
    "jianying", "jianyingpresets", "capcut", "prproj", "after effects",
    "premiere", "达芬奇", "davinci", "final cut", "figma", "sketch",
    "adobe", "affinity", "blender", "wpsoffice", "wps", "libreoffice",
    "zoom", "todesk", "teamviewer", "anydesk", "sunlogin", "1password",
    "bitwarden", "keepass", "lastpass", "steam", "epic games", "battle.net",
    "origin", "ubisoft", "wegame", "unity", "unreal", "ue5", "ue4", "godot",
    
    # 其他常见目录
    "backup", "backups", "trash", "recycle", "trashbin", ".trash",
    "recycler", "$recycle.bin", "system volume information",
]

LEARNED_PATTERNS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "learned_patterns.json")

def _load_learned_patterns() -> Dict:
    """加载学习到的模式"""
    if not os.path.exists(LEARNED_PATTERNS_FILE):
        return {
            "path_keywords": [],
            "dir_patterns": [],
            "filename_patterns": [],
            "extension_weights": {},
            "positive_examples": [],
            "negative_examples": [],
            "learn_count": 0,
        }
    try:
        with open(LEARNED_PATTERNS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "learn_count" not in data:
                data["learn_count"] = 0
            if "extension_weights" not in data:
                data["extension_weights"] = {}
            return data
    except Exception:
        return {
            "path_keywords": [],
            "dir_patterns": [],
            "filename_patterns": [],
            "extension_weights": {},
            "positive_examples": [],
            "negative_examples": [],
            "learn_count": 0,
        }

def _save_learned_patterns(patterns: Dict):
    """保存学习到的模式"""
    try:
        with open(LEARNED_PATTERNS_FILE, "w", encoding="utf-8") as f:
            json.dump(patterns, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存学习模式失败: {e}")

def analyze_path_features(file_path: str, stat_info: Optional[Dict] = None) -> Dict:
    """分析路径特征（增强版）"""
    features = {
        "has_personal_keyword": False,
        "has_personal_filename": False,
        "is_personal_extension": False,
        "in_user_dir": False,
        "in_program_dir": False,
        "depth": 0,
        "size_score": 0,
        "time_score": 0,
        "score": 0,
        "confidence": 0.0,
    }
    
    file_path_lower = file_path.lower()
    filename = os.path.basename(file_path).lower()
    ext = Path(file_path).suffix.lower()
    dir_path = os.path.dirname(file_path).lower()
    
    # 🔴 最高优先级：检查是否在程序目录中（直接排除）
    # 使用标准化的分隔符检查，避免漏判
    norm_dir_path = os.sep + dir_path + os.sep
    for prog_dir in PROGRAM_DIRS:
        prog_dir_norm = os.sep + prog_dir.lower() + os.sep
        if prog_dir_norm in norm_dir_path or dir_path.endswith(prog_dir.lower()):
            features["in_program_dir"] = True
            features["score"] = -999  # 直接排除
            return features
    
    # 检查关键词（更严格，避免宽泛匹配）
    keyword_count = 0
    for keyword in PERSONAL_KEYWORDS:
        kw_lower = keyword.lower()
        # 避免太宽泛的匹配（比如只匹配单个字母或太短的词）
        if len(kw_lower) < 3:
            # 短关键词要求完整单词匹配
            pattern = r'\b' + re.escape(kw_lower) + r'\b'
            if re.search(pattern, file_path_lower):
                keyword_count += 1
        else:
            # 长关键词可以直接包含匹配
            if kw_lower in file_path_lower:
                keyword_count += 1
    if keyword_count > 0:
        features["has_personal_keyword"] = True
        features["score"] += min(keyword_count * 2, 5)
    
    # 检查文件名模式
    pattern_match_count = 0
    for pattern in PERSONAL_FILENAME_PATTERNS:
        if re.search(pattern, filename, re.IGNORECASE):
            pattern_match_count += 1
    if pattern_match_count > 0:
        features["has_personal_filename"] = True
        features["score"] += min(pattern_match_count * 3, 6)
    
    # 检查扩展名
    if ext in PERSONAL_EXTENSIONS:
        features["is_personal_extension"] = True
        features["score"] += 1  # 降低扩展名的权重，单独扩展名不应该有太高分数
    
    # 检查是否在用户目录
    user_profile = os.environ.get("USERPROFILE", "")
    if user_profile:
        user_profile_lower = user_profile.lower()
        if file_path_lower.startswith(user_profile_lower):
            features["in_user_dir"] = True
            features["score"] += 1
            
            # 检查是否在特定的用户子目录
            desktop = os.path.join(user_profile, "desktop").lower()
            documents = os.path.join(user_profile, "documents").lower()
            downloads = os.path.join(user_profile, "downloads").lower()
            pictures = os.path.join(user_profile, "pictures").lower()
            videos = os.path.join(user_profile, "videos").lower()
            music = os.path.join(user_profile, "music").lower()
            
            # 检查是否确实在这些目录中（而不是子目录）
            for subdir in [desktop, documents, downloads, pictures, videos, music]:
                subdir_with_sep = subdir + os.sep
                if dir_path == subdir or subdir_with_sep in norm_dir_path:
                    features["score"] += 2
                    break
    
    # 计算路径深度
    features["depth"] = file_path.count(os.sep)
    if 2 <= features["depth"] <= 6:
        features["score"] += 1
    
    # 文件大小分析（如果有stat信息）
    if stat_info:
        size = stat_info.get("size", 0)
        if 1024 <= size <= 100 * 1024 * 1024:  # 1KB - 100MB
            features["size_score"] = 1
            features["score"] += 1
        elif size > 100 * 1024 * 1024:  # > 100MB
            features["size_score"] = 2
            features["score"] += 2
    
    # 时间分析（如果有stat信息）
    if stat_info:
        now_ts = int(time.time())
        mtime_ts = stat_info.get("mtime_ts", 0)
        days_since_modified = (now_ts - mtime_ts) / (24 * 60 * 60)
        
        if days_since_modified < 30:  # 最近1个月
            features["time_score"] = 2
            features["score"] += 2
        elif days_since_modified < 365:  # 最近1年
            features["time_score"] = 1
            features["score"] += 1
    
    # 计算置信度
    max_possible_score = 20
    features["confidence"] = min(max(features["score"], 0) / max_possible_score, 1.0)
    
    return features

def check_learned_patterns(file_path: str, patterns: Dict) -> Tuple[bool, int, float]:
    """检查学习到的模式（增强版）"""
    score = 0
    confidence_boost = 0.0
    file_path_lower = file_path.lower()
    filename = os.path.basename(file_path).lower()
    ext = Path(file_path).suffix.lower()
    
    # 检查路径关键词（带权重）
    keyword_hits = 0
    for keyword in patterns.get("path_keywords", []):
        if keyword.lower() in file_path_lower:
            keyword_hits += 1
            score += 2
    if keyword_hits > 0:
        confidence_boost += 0.1 * min(keyword_hits, 3)
    
    # 检查目录模式
    dir_path = os.path.dirname(file_path).lower()
    dir_hits = 0
    for pattern in patterns.get("dir_patterns", []):
        if pattern.lower() in dir_path:
            dir_hits += 1
            score += 3
    if dir_hits > 0:
        confidence_boost += 0.15 * min(dir_hits, 2)
    
    # 检查扩展名权重
    if ext in patterns.get("extension_weights", {}):
        ext_weight = patterns["extension_weights"][ext]
        score += ext_weight
        confidence_boost += 0.1
    
    # 检查正例和反例
    for example in patterns.get("positive_examples", []):
        example_lower = example.lower()
        if file_path_lower == example_lower or file_path_lower.startswith(example_lower + os.sep):
            score += 8
            confidence_boost += 0.3
            break
    
    for example in patterns.get("negative_examples", []):
        example_lower = example.lower()
        if file_path_lower == example_lower or file_path_lower.startswith(example_lower + os.sep):
            score -= 10
            confidence_boost -= 0.3
            break
    
    return score > 0, max(0, score), min(confidence_boost, 0.5)

def is_suspected_personal(file_path: str, stat_info: Optional[Dict] = None) -> Tuple[bool, int, str, float]:
    """判断是否为疑似个人内容（增强版）
    
    Returns:
        (is_suspected, score, reason, confidence)
    """
    patterns = _load_learned_patterns()
    
    # 分析基础特征
    features = analyze_path_features(file_path, stat_info)
    
    # 🔴 如果在程序目录中，直接排除
    if features["in_program_dir"] or features["score"] < 0:
        return False, features["score"], "", 0.0
    
    base_score = features["score"]
    base_confidence = features["confidence"]
    
    # 检查学习到的模式
    learned_match, learned_score, learned_confidence = check_learned_patterns(file_path, patterns)
    
    total_score = base_score + learned_score
    total_confidence = min(base_confidence + learned_confidence, 1.0)
    
    # 判断理由
    reasons = []
    if features["has_personal_keyword"]:
        reasons.append("包含个人关键词")
    if features["has_personal_filename"]:
        reasons.append("文件名特征匹配")
    if features["is_personal_extension"]:
        reasons.append("文件类型匹配")
    if features["in_user_dir"]:
        reasons.append("在用户目录")
    if features["size_score"] > 0:
        reasons.append("文件大小适中")
    if features["time_score"] > 0:
        reasons.append("时间较近")
    if learned_match:
        reasons.append("学习模式匹配")
    
    # 🔴 提高阈值，减少误判
    # 默认阈值：5分（比之前的3分高很多）
    # 学习越多，阈值越高
    threshold = 5
    learn_count = patterns.get("learn_count", 0)
    if learn_count > 5:
        threshold = 6
    if learn_count > 10:
        threshold = 7
    if learn_count > 20:
        threshold = 8
    
    is_suspected = total_score >= threshold
    reason_str = ", ".join(reasons) if reasons else ""
    
    return is_suspected, total_score, reason_str, total_confidence

def learn_from_positive_example(dir_path: str, file_paths: Optional[List[str]] = None):
    """从正例学习（用户标记为个人目录）（增强版）"""
    patterns = _load_learned_patterns()
    
    dir_path = os.path.normpath(dir_path)
    dir_path_lower = dir_path.lower()
    
    # 添加到正例
    if dir_path not in patterns["positive_examples"]:
        patterns["positive_examples"].append(dir_path)
        patterns["learn_count"] = patterns.get("learn_count", 0) + 1
    
    # 提取路径关键词
    parts = dir_path_lower.split(os.sep)
    for part in parts:
        if part and len(part) > 2 and part not in PROGRAM_DIRS:
            if part not in patterns["path_keywords"]:
                patterns["path_keywords"].append(part)
    
    # 提取目录模式（多级）
    current_dir = dir_path
    for _ in range(3):  # 最多向上3级
        parent_dir = os.path.dirname(current_dir)
        if parent_dir and parent_dir != current_dir:
            parent_dir_lower = parent_dir.lower()
            if parent_dir_lower not in patterns["dir_patterns"]:
                patterns["dir_patterns"].append(parent_dir_lower)
            current_dir = parent_dir
        else:
            break
    
    # 从文件列表学习扩展名
    if file_paths:
        ext_counter = Counter()
        for fp in file_paths:
            ext = Path(fp).suffix.lower()
            if ext:
                ext_counter[ext] += 1
        
        for ext, count in ext_counter.items():
            if count >= 2:  # 至少2个文件才学习
                current_weight = patterns["extension_weights"].get(ext, 0)
                patterns["extension_weights"][ext] = current_weight + min(count, 3)
    
    _save_learned_patterns(patterns)

def learn_from_negative_example(dir_path: str):
    """从反例学习（用户确认不是个人目录）"""
    patterns = _load_learned_patterns()
    
    dir_path = os.path.normpath(dir_path)
    if dir_path not in patterns["negative_examples"]:
        patterns["negative_examples"].append(dir_path)
        patterns["learn_count"] = patterns.get("learn_count", 0) + 1
    
    _save_learned_patterns(patterns)

def batch_learn_from_positive(dir_paths: List[str], all_file_paths: Optional[List[str]] = None):
    """批量学习正例"""
    patterns = _load_learned_patterns()
    
    for dir_path in dir_paths:
        dir_path = os.path.normpath(dir_path)
        dir_path_lower = dir_path.lower()
        
        if dir_path not in patterns["positive_examples"]:
            patterns["positive_examples"].append(dir_path)
            patterns["learn_count"] = patterns.get("learn_count", 0) + 1
        
        parts = dir_path_lower.split(os.sep)
        for part in parts:
            if part and len(part) > 2 and part not in PROGRAM_DIRS:
                if part not in patterns["path_keywords"]:
                    patterns["path_keywords"].append(part)
    
    if all_file_paths:
        ext_counter = Counter()
        for fp in all_file_paths:
            ext = Path(fp).suffix.lower()
            if ext:
                ext_counter[ext] += 1
        
        for ext, count in ext_counter.items():
            if count >= 3:
                current_weight = patterns["extension_weights"].get(ext, 0)
                patterns["extension_weights"][ext] = current_weight + min(count, 5)
    
    _save_learned_patterns(patterns)

def get_smart_suggestion(file_path: str, stat_info: Optional[Dict] = None) -> Optional[Dict]:
    """获取智能建议（增强版）"""
    is_suspected, score, reason, confidence = is_suspected_personal(file_path, stat_info)
    
    if is_suspected:
        confidence_pct = int(confidence * 100)
        suggestion_level = "high" if confidence > 0.6 else "medium" if confidence > 0.3 else "low"
        
        return {
            "is_suspected": True,
            "score": score,
            "reason": reason,
            "confidence": confidence,
            "confidence_pct": confidence_pct,
            "level": suggestion_level,
            "suggestion": "建议标记为个人目录",
        }
    return None

def get_learning_stats() -> Dict:
    """获取学习统计信息"""
    patterns = _load_learned_patterns()
    return {
        "learn_count": patterns.get("learn_count", 0),
        "positive_examples": len(patterns.get("positive_examples", [])),
        "negative_examples": len(patterns.get("negative_examples", [])),
        "path_keywords": len(patterns.get("path_keywords", [])),
        "dir_patterns": len(patterns.get("dir_patterns", [])),
        "extensions_learned": len(patterns.get("extension_weights", {})),
    }
