import os
import re
import json
import time
from pathlib import Path
from typing import Tuple, Dict, Optional, List
from collections import Counter
import hashlib

class IntelligentClassifier:
    """增强的智能文件分类器 - 具有自主判断能力"""
    
    # 学习数据文件
    LEARNING_DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "intelligent_learning.json")
    
    def __init__(self):
        self.learning_data = self._load_learning_data()
        self._setup_patterns()
    
    def _load_learning_data(self) -> Dict:
        """加载学习数据"""
        if not os.path.exists(self.LEARNING_DATA_FILE):
            return {
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
            }
        try:
            with open(self.LEARNING_DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return self._load_learning_data()
    
    def _save_learning_data(self):
        """保存学习数据"""
        try:
            with open(self.LEARNING_DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(self.learning_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存学习数据失败: {e}")
    
    def _setup_patterns(self):
        """设置初始模式"""
        # 个人文件关键词
        self.personal_keywords = set([
            "我的", "私人", "个人", "private", "personal", "my",
            "简历", "resume", "cv", "身份证", "护照", "passport",
            "合同", "contract", "offer", "薪资", "工资", "salary",
            "银行", "bank", "保险", "insurance", "医疗", "medical",
            "日记", "diary", "笔记", "note", "备忘录", "memo",
            "照片", "photo", "picture", "image", "pic", "相册",
            "视频", "video", "movie", "film", "音乐", "music",
            "下载", "download", "桌面", "desktop", "文档", "document",
            "备份", "backup", "存档", "archive", "家庭", "family",
            "旅行", "travel", "旅游", "trip", "婚礼", "wedding",
            "生日", "birthday", "纪念日", "anniversary"
        ])
        
        # 系统文件关键词
        self.system_keywords = set([
            "system", "windows", "program", "driver", "service",
            "kernel", "registry", "boot", "config", "dll", "sys",
            "exe", "msi", "inf", "cat", "pdb", "ocx", "scr"
        ])
        
        # 软件文件关键词
        self.software_keywords = set([
            "appdata", "cache", "temp", "tmp", "node_modules",
            "venv", "git", "build", "dist", "logs", "crash",
            "browser", "chrome", "firefox", "edge", "opera"
        ])
    
    def classify_file(self, file_path: str, stat_info: Optional[Dict] = None) -> Dict:
        """
        智能文件分类
        
        Returns:
            {
                "category": "personal" | "system" | "software" | "unknown",
                "confidence": 0.0-1.0,
                "reason": str,
                "features": Dict
            }
        """
        features = self._extract_features(file_path, stat_info)
        confidence = self._calculate_confidence(features)
        category = self._determine_category(features, confidence)
        reason = self._generate_reason(features, category)
        
        return {
            "category": category,
            "confidence": confidence,
            "reason": reason,
            "features": features
        }
    
    def _extract_features(self, file_path: str, stat_info: Optional[Dict] = None) -> Dict:
        """提取文件特征"""
        features = {
            "path": file_path,
            "filename": os.path.basename(file_path),
            "extension": Path(file_path).suffix.lower(),
            "dir_path": os.path.dirname(file_path),
            "path_depth": file_path.count(os.sep),
            "personal_keywords": 0,
            "system_keywords": 0,
            "software_keywords": 0,
            "filename_patterns": [],
            "dir_patterns": [],
            "is_user_dir": False,
            "is_system_dir": False,
            "is_software_dir": False,
            "size_score": 0,
            "time_score": 0,
            "content_score": 0,
            "creation_score": 0,
            "filename_complexity": 0,
            "extension_rarity": 0,
            "context_score": 0
        }
        
        # 提取关键词特征
        path_lower = file_path.lower()
        filename_lower = features["filename"].lower()
        
        # 关键词匹配
        for keyword in self.personal_keywords:
            if keyword in path_lower:
                features["personal_keywords"] += 1
        for keyword in self.system_keywords:
            if keyword in path_lower:
                features["system_keywords"] += 1
        for keyword in self.software_keywords:
            if keyword in path_lower:
                features["software_keywords"] += 1
        
        # 目录特征
        user_profile = os.environ.get("USERPROFILE", "")
        if user_profile and path_lower.startswith(user_profile.lower()):
            features["is_user_dir"] = True
            
            # 检查是否在个人目录
            personal_dirs = ["desktop", "documents", "downloads", "pictures", "videos", "music"]
            for dir_name in personal_dirs:
                if f"{os.sep}{dir_name}{os.sep}" in path_lower:
                    features["personal_keywords"] += 2
                    break
        
        # 系统目录检查
        system_dirs = ["windows", "program files", "programdata", "syswow64", "system32"]
        for dir_name in system_dirs:
            if f"{os.sep}{dir_name}{os.sep}" in path_lower:
                features["is_system_dir"] = True
                features["system_keywords"] += 2
                break
        
        # 软件目录检查
        software_dirs = ["appdata", "node_modules", "venv", ".git", "build", "dist"]
        for dir_name in software_dirs:
            if f"{os.sep}{dir_name}{os.sep}" in path_lower:
                features["is_software_dir"] = True
                features["software_keywords"] += 2
                break
        
        # 文件大小分析
        if stat_info:
            size = stat_info.get("size", 0)
            if 1024 <= size <= 100 * 1024 * 1024:  # 1KB - 100MB
                features["size_score"] = 1
            elif size > 100 * 1024 * 1024:  # > 100MB
                features["size_score"] = 2
        
        # 时间分析
        if stat_info:
            now_ts = int(time.time())
            mtime_ts = stat_info.get("mtime_ts", 0)
            days_since_modified = (now_ts - mtime_ts) / (24 * 60 * 60)
            if days_since_modified < 30:  # 最近1个月
                features["time_score"] = 2
            elif days_since_modified < 365:  # 最近1年
                features["time_score"] = 1
        
        # 文件创建时间分析
        if os.path.exists(file_path):
            try:
                stat = os.stat(file_path)
                ctime_ts = int(stat.st_ctime)
                days_since_creation = (int(time.time()) - ctime_ts) / (24 * 60 * 60)
                if days_since_creation < 30:
                    features["creation_score"] = 2
                elif days_since_creation < 365:
                    features["creation_score"] = 1
            except Exception:
                pass
        
        # 文件名复杂度分析
        filename = features["filename"]
        features["filename_complexity"] = len(filename) / 50  # 文件名长度
        if re.search(r'\d{4,}', filename):  # 包含长数字
            features["filename_complexity"] += 0.5
        if re.search(r'[A-Z][a-z]+', filename):  # 驼峰命名
            features["filename_complexity"] += 0.3
        
        # 扩展名稀有度分析
        common_extensions = [".txt", ".docx", ".xlsx", ".pdf", ".jpg", ".png", ".mp4", ".mp3"]
        if features["extension"] not in common_extensions:
            features["extension_rarity"] = 1
        
        # 内容分析（对于文本文件）
        if features["extension"] in [".txt", ".docx", ".pdf", ".md", ".rtf", ".odt", ".csv", ".xls", ".xlsx"]:
            try:
                size = os.path.getsize(file_path)
                if size < 1024 * 1024:  # 小于1MB
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read().lower()
                        # 检查个人内容关键词
                        personal_content_keywords = ["我", "我的", "个人", "私人", "简历", "照片", "家庭", "联系方式", "电话", "邮箱", "地址", "身份证", "护照", "银行卡", "工资", "合同", "offer", "推荐信"]
                        for keyword in personal_content_keywords:
                            if keyword in content:
                                features["content_score"] += 1
                        
                        # 检查系统内容关键词
                        system_content_keywords = ["system", "windows", "registry", "driver", "service", "kernel", "boot", "config"]
                        for keyword in system_content_keywords:
                            if keyword in content:
                                features["system_keywords"] += 0.5
                        
                        # 检查软件内容关键词
                        software_content_keywords = ["appdata", "cache", "temp", "node_modules", "venv", "git", "build", "dist"]
                        for keyword in software_content_keywords:
                            if keyword in content:
                                features["software_keywords"] += 0.5
                        
                        # 提取内容模式
                        content_patterns = self._extract_content_patterns(content)
                        features["content_patterns"] = content_patterns
            except Exception:
                pass
        
        # 上下文分析（同一目录下的文件）
        try:
            dir_path = features["dir_path"]
            if os.path.exists(dir_path):
                files_in_dir = os.listdir(dir_path)
                personal_file_count = 0
                system_file_count = 0
                
                for file in files_in_dir[:20]:  # 只分析前20个文件
                    file_lower = file.lower()
                    if any(pk in file_lower for pk in self.personal_keywords):
                        personal_file_count += 1
                    if any(sk in file_lower for sk in self.system_keywords):
                        system_file_count += 1
                
                if personal_file_count > system_file_count:
                    features["context_score"] = 1
                elif system_file_count > personal_file_count:
                    features["context_score"] = -1
        except Exception:
            pass
        
        return features
    
    def _calculate_confidence(self, features: Dict) -> float:
        """计算分类置信度"""
        score = 0
        max_score = 20  # 增加最大分数以容纳新特征
        
        # 关键词分数
        score += min(features["personal_keywords"] * 0.8, 3)
        score += min(features["system_keywords"] * 0.8, 3)
        score += min(features["software_keywords"] * 0.8, 3)
        
        # 目录特征
        if features["is_user_dir"]:
            score += 2
        if features["is_system_dir"]:
            score += 2
        if features["is_software_dir"]:
            score += 2
        
        # 文件特征
        score += features["size_score"] * 0.5
        score += features["time_score"] * 0.5
        score += features["creation_score"] * 0.3
        score += features["content_score"] * 0.8
        
        # 内容模式特征
        content_patterns = features.get("content_patterns", {})
        if content_patterns:
            # 个人识别信息
            personal_info_score = content_patterns.get("email_patterns", 0) * 0.5
            personal_info_score += content_patterns.get("phone_patterns", 0) * 0.5
            personal_info_score += content_patterns.get("id_patterns", 0) * 0.8
            personal_info_score += content_patterns.get("address_patterns", 0) * 0.3
            score += min(personal_info_score, 2)
            
            # 个人术语
            score += content_patterns.get("personal_terms", 0) * 0.3
            
            # 系统术语
            score += content_patterns.get("system_terms", 0) * 0.3
            
            # 软件术语
            score += content_patterns.get("software_terms", 0) * 0.3
        
        # 上下文特征
        if features["context_score"] > 0:
            score += 1  # 同一目录下有较多个人文件
        elif features["context_score"] < 0:
            score -= 1  # 同一目录下有较多系统文件
        
        # 文件名和扩展名特征
        score += features["filename_complexity"] * 0.5
        score += features["extension_rarity"] * 0.3
        
        # 学习模式
        score += self._apply_learned_patterns(features)
        
        return min(max(score / max_score, 0.1), 1.0)  # 确保置信度在0.1-1.0之间
    
    def _apply_learned_patterns(self, features: Dict) -> float:
        """应用学习到的模式"""
        score = 0
        patterns = self.learning_data.get("patterns", {})
        
        # 扩展权重
        ext_weights = patterns.get("extension_weights", {})
        if features["extension"] in ext_weights:
            score += ext_weights[features["extension"]] * 0.1
        
        # 目录模式
        dir_patterns = patterns.get("dir_patterns", {})
        for pattern, weight in dir_patterns.items():
            if pattern in features["dir_path"].lower():
                score += weight * 0.1
        
        # 文件名模式
        filename_patterns = patterns.get("filename_patterns", {})
        for pattern, weight in filename_patterns.items():
            if pattern in features["filename"].lower():
                score += weight * 0.1
        
        # 内容模式
        content_patterns = patterns.get("content_patterns", {})
        if "personal_content" in content_patterns:
            score += content_patterns["personal_content"] * 0.1
        
        # 个人识别信息模式
        content_patterns = features.get("content_patterns", {})
        personal_info_patterns = patterns.get("personal_info_patterns", {})
        for key, weight in personal_info_patterns.items():
            if content_patterns.get(key, 0) > 0:
                score += weight * 0.1
        
        # 术语模式
        term_patterns = patterns.get("term_patterns", {})
        if "personal_terms" in term_patterns and content_patterns.get("personal_terms", 0) > 0:
            score += term_patterns["personal_terms"] * 0.1
        if "system_terms" in term_patterns and content_patterns.get("system_terms", 0) > 0:
            score += term_patterns["system_terms"] * 0.1
        if "software_terms" in term_patterns and content_patterns.get("software_terms", 0) > 0:
            score += term_patterns["software_terms"] * 0.1
        
        # 上下文模式
        context_patterns = patterns.get("context_patterns", {})
        if "personal_context" in context_patterns and features["context_score"] > 0:
            score += context_patterns["personal_context"] * 0.1
        
        return score
    
    def _determine_category(self, features: Dict, confidence: float) -> str:
        """确定文件类别"""
        # 基于特征确定类别
        personal_score = features["personal_keywords"] + (2 if features["is_user_dir"] else 0)
        personal_score += features["content_score"] * 1.5
        personal_score += features["time_score"] * 0.5
        personal_score += features["creation_score"] * 0.5
        if features["context_score"] > 0:
            personal_score += 1
        
        system_score = features["system_keywords"] + (2 if features["is_system_dir"] else 0)
        system_score += features["filename_complexity"] * 0.5
        if features["context_score"] < 0:
            system_score += 1
        
        software_score = features["software_keywords"] + (2 if features["is_software_dir"] else 0)
        software_score += features["extension_rarity"] * 0.5
        
        # 内容模式特征
        content_patterns = features.get("content_patterns", {})
        if content_patterns:
            # 个人识别信息
            personal_info_score = content_patterns.get("email_patterns", 0) + content_patterns.get("phone_patterns", 0) + content_patterns.get("id_patterns", 0)
            if personal_info_score > 0:
                personal_score += personal_info_score * 2
            
            # 个人术语
            personal_score += content_patterns.get("personal_terms", 0) * 1.2
            
            # 系统术语
            system_score += content_patterns.get("system_terms", 0) * 1.2
            
            # 软件术语
            software_score += content_patterns.get("software_terms", 0) * 1.2
        
        # 特殊处理：可执行文件的分类
        if features["extension"] == ".exe":
            # 检查是否在软件目录中
            if features["is_software_dir"]:
                software_score += 3
            # 检查文件名是否包含setup、install等软件相关词汇
            filename_lower = features["filename"].lower()
            if any(keyword in filename_lower for keyword in ["setup", "install", "uninstall", "update", "node", "python"]):
                software_score += 2
            # 检查路径是否包含软件相关目录
            path_lower = features["path"].lower()
            if any(dir_name in path_lower for dir_name in ["node.js", "venv", "scripts", "bin"]):
                software_score += 2
        
        # 优先考虑软件目录中的文件
        if features["is_software_dir"]:
            software_score += 2
            # 软件目录中的文件优先级高于系统关键词
            system_score -= 1
        
        # 特殊处理：setup.exe 在桌面目录
        if features["extension"] == ".exe" and "setup" in features["filename"].lower():
            software_score += 2
        
        max_score = max(personal_score, system_score, software_score)
        
        if max_score == personal_score and max_score > 0:
            return "personal"
        elif max_score == system_score and max_score > 0:
            return "system"
        elif max_score == software_score and max_score > 0:
            return "software"
        else:
            return "unknown"
    
    def _generate_reason(self, features: Dict, category: str) -> str:
        """生成分类理由"""
        reasons = []
        
        if category == "personal":
            if features["personal_keywords"] > 0:
                reasons.append("包含个人关键词")
            if features["is_user_dir"]:
                reasons.append("在用户目录中")
            if features["size_score"] > 0:
                reasons.append("文件大小适中")
            if features["time_score"] > 0:
                reasons.append("最近有修改")
            if features["creation_score"] > 0:
                reasons.append("最近创建")
            if features["content_score"] > 0:
                reasons.append("包含个人内容")
            if features["context_score"] > 0:
                reasons.append("同一目录有其他个人文件")
            # 内容模式特征
            content_patterns = features.get("content_patterns", {})
            if content_patterns:
                if content_patterns.get("email_patterns", 0) > 0:
                    reasons.append("包含邮箱地址")
                if content_patterns.get("phone_patterns", 0) > 0:
                    reasons.append("包含电话号码")
                if content_patterns.get("id_patterns", 0) > 0:
                    reasons.append("包含身份证号")
                if content_patterns.get("address_patterns", 0) > 0:
                    reasons.append("包含地址信息")
                if content_patterns.get("personal_terms", 0) > 0:
                    reasons.append("包含个人术语")
        elif category == "system":
            if features["system_keywords"] > 0:
                reasons.append("包含系统关键词")
            if features["is_system_dir"]:
                reasons.append("在系统目录中")
            if features["filename_complexity"] > 0.5:
                reasons.append("文件名复杂")
            if features["context_score"] < 0:
                reasons.append("同一目录有其他系统文件")
            # 内容模式特征
            content_patterns = features.get("content_patterns", {})
            if content_patterns and content_patterns.get("system_terms", 0) > 0:
                reasons.append("包含系统术语")
        elif category == "software":
            if features["software_keywords"] > 0:
                reasons.append("包含软件关键词")
            if features["is_software_dir"]:
                reasons.append("在软件目录中")
            if features["extension_rarity"] > 0:
                reasons.append("扩展名特殊")
            # 内容模式特征
            content_patterns = features.get("content_patterns", {})
            if content_patterns and content_patterns.get("software_terms", 0) > 0:
                reasons.append("包含软件术语")
        else:
            reasons.append("无法确定类别")
        
        return ", ".join(reasons) if reasons else "未知原因"
    
    def learn_from_feedback(self, file_path: str, is_personal: bool, confidence: float = 1.0):
        """从用户反馈中学习"""
        file_hash = hashlib.md5(file_path.encode()).hexdigest()
        
        # 更新用户历史
        history_key = "marked_personal" if is_personal else "marked_system"
        if file_hash not in self.learning_data["user_history"][history_key]:
            self.learning_data["user_history"][history_key].append(file_hash)
        
        # 提取特征进行学习
        features = self._extract_features(file_path)
        patterns = self.learning_data["patterns"]
        
        # 动态调整学习率
        total_learning = self.learning_data.get("total_learning", 0)
        base_learning_rate = 0.1
        # 随着学习次数增加，逐渐减小学习率
        learning_rate = base_learning_rate * (1 - min(total_learning / 1000, 0.8))
        
        # 学习扩展名权重
        ext = features["extension"]
        if ext:
            if ext not in patterns["extension_weights"]:
                patterns["extension_weights"][ext] = 0
            if is_personal:
                patterns["extension_weights"][ext] += learning_rate * confidence
            else:
                patterns["extension_weights"][ext] -= learning_rate * confidence
            # 确保权重不为负
            patterns["extension_weights"][ext] = max(0, patterns["extension_weights"][ext])
        
        # 学习目录模式
        dir_path = features["dir_path"]
        dir_pattern = os.path.basename(dir_path).lower()
        if dir_pattern:
            if dir_pattern not in patterns["dir_patterns"]:
                patterns["dir_patterns"][dir_pattern] = 0
            if is_personal:
                patterns["dir_patterns"][dir_pattern] += learning_rate * confidence
            else:
                patterns["dir_patterns"][dir_pattern] -= learning_rate * confidence
            patterns["dir_patterns"][dir_pattern] = max(0, patterns["dir_patterns"][dir_pattern])
        
        # 学习文件名模式
        filename = features["filename"].lower()
        if filename:
            # 提取文件名模式（去除数字和特殊字符）
            pattern = re.sub(r'\d+', '', filename)
            pattern = re.sub(r'[._-]+', ' ', pattern).strip()
            if pattern and len(pattern) > 3:
                if pattern not in patterns["filename_patterns"]:
                    patterns["filename_patterns"][pattern] = 0
                if is_personal:
                    patterns["filename_patterns"][pattern] += learning_rate * confidence
                else:
                    patterns["filename_patterns"][pattern] -= learning_rate * confidence
                patterns["filename_patterns"][pattern] = max(0, patterns["filename_patterns"][pattern])
        
        # 学习内容特征
        if features["content_score"] > 0:
            content_patterns = patterns.get("content_patterns", {})
            patterns["content_patterns"] = content_patterns
            if is_personal:
                content_patterns["personal_content"] = content_patterns.get("personal_content", 0) + learning_rate * confidence
            else:
                content_patterns["personal_content"] = max(0, content_patterns.get("personal_content", 0) - learning_rate * confidence)
        
        # 学习内容模式特征
        content_patterns = features.get("content_patterns", {})
        if content_patterns:
            # 学习个人识别信息模式
            if is_personal:
                for key in ["email_patterns", "phone_patterns", "id_patterns", "address_patterns"]:
                    if content_patterns.get(key, 0) > 0:
                        personal_info_patterns = patterns.get("personal_info_patterns", {})
                        patterns["personal_info_patterns"] = personal_info_patterns
                        personal_info_patterns[key] = personal_info_patterns.get(key, 0) + learning_rate * confidence
            
            # 学习术语模式
            term_patterns = patterns.get("term_patterns", {})
            patterns["term_patterns"] = term_patterns
            if is_personal:
                if content_patterns.get("personal_terms", 0) > 0:
                    term_patterns["personal_terms"] = term_patterns.get("personal_terms", 0) + learning_rate * confidence
            else:
                if content_patterns.get("system_terms", 0) > 0:
                    term_patterns["system_terms"] = term_patterns.get("system_terms", 0) + learning_rate * confidence
                if content_patterns.get("software_terms", 0) > 0:
                    term_patterns["software_terms"] = term_patterns.get("software_terms", 0) + learning_rate * confidence
        
        # 学习上下文特征
        if features["context_score"] != 0:
            context_patterns = patterns.get("context_patterns", {})
            patterns["context_patterns"] = context_patterns
            if is_personal:
                context_patterns["personal_context"] = context_patterns.get("personal_context", 0) + learning_rate * confidence
            else:
                context_patterns["personal_context"] = max(0, context_patterns.get("personal_context", 0) - learning_rate * confidence)
        
        # 更新学习计数
        self.learning_data["total_learning"] += 1
        
        # 自适应调整置信度阈值
        if total_learning % 10 == 0:  # 每10次学习调整一次
            self._adjust_confidence_threshold()
        
        # 保存学习数据
        self._save_learning_data()
    
    def learn_from_action(self, file_paths: List[str], action: str):
        """从用户操作中学习"""
        for file_path in file_paths:
            file_hash = hashlib.md5(file_path.encode()).hexdigest()
            
            # 更新历史
            if action == "delete" and file_hash not in self.learning_data["user_history"]["deleted_files"]:
                self.learning_data["user_history"]["deleted_files"].append(file_hash)
                # 学习为非个人文件
                self.learn_from_feedback(file_path, False, 0.8)
            elif action == "keep" and file_hash not in self.learning_data["user_history"]["kept_files"]:
                self.learning_data["user_history"]["kept_files"].append(file_hash)
                # 学习为个人文件
                self.learn_from_feedback(file_path, True, 0.8)
        
        self._save_learning_data()
    
    def get_learning_stats(self) -> Dict:
        """获取学习统计信息"""
        patterns = self.learning_data.get("patterns", {})
        history = self.learning_data.get("user_history", {})
        
        return {
            "total_learning": self.learning_data.get("total_learning", 0),
            "extensions_learned": len(patterns.get("extension_weights", {})),
            "dir_patterns_learned": len(patterns.get("dir_patterns", {})),
            "filename_patterns_learned": len(patterns.get("filename_patterns", {})),
            "deleted_files": len(history.get("deleted_files", [])),
            "kept_files": len(history.get("kept_files", [])),
            "marked_personal": len(history.get("marked_personal", [])),
            "marked_system": len(history.get("marked_system", []))
        }
    
    def _extract_content_patterns(self, content: str) -> Dict:
        """从内容中提取模式"""
        patterns = {
            "personal_terms": 0,
            "system_terms": 0,
            "software_terms": 0,
            "email_patterns": 0,
            "phone_patterns": 0,
            "id_patterns": 0,
            "address_patterns": 0,
            "date_patterns": 0,
            "number_patterns": 0
        }
        
        # 邮箱模式
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        email_matches = re.findall(email_pattern, content)
        patterns["email_patterns"] = len(email_matches)
        
        # 电话号码模式
        phone_pattern = r'1[3-9]\d{9}'  # 中国手机号
        phone_matches = re.findall(phone_pattern, content)
        patterns["phone_patterns"] = len(phone_matches)
        
        # 身份证号模式
        id_pattern = r'[1-9]\d{5}(19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[0-9Xx]'
        id_matches = re.findall(id_pattern, content)
        patterns["id_patterns"] = len(id_matches)
        
        # 地址模式
        address_pattern = r'[省市区县镇乡村]'
        address_matches = re.findall(address_pattern, content)
        patterns["address_patterns"] = len(address_matches)
        
        # 日期模式
        date_pattern = r'\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日]?'
        date_matches = re.findall(date_pattern, content)
        patterns["date_patterns"] = len(date_matches)
        
        # 数字模式
        number_pattern = r'\d{4,}'
        number_matches = re.findall(number_pattern, content)
        patterns["number_patterns"] = len(number_matches)
        
        # 个人术语
        personal_terms = ["我", "我的", "个人", "私人", "简历", "照片", "家庭"]
        for term in personal_terms:
            if term in content:
                patterns["personal_terms"] += 1
        
        # 系统术语
        system_terms = ["system", "windows", "registry", "driver"]
        for term in system_terms:
            if term in content:
                patterns["system_terms"] += 1
        
        # 软件术语
        software_terms = ["appdata", "cache", "temp", "node_modules"]
        for term in software_terms:
            if term in content:
                patterns["software_terms"] += 1
        
        return patterns
    
    def _adjust_confidence_threshold(self):
        """自适应调整置信度阈值"""
        history = self.learning_data.get("user_history", {})
        marked_personal = len(history.get("marked_personal", []))
        marked_system = len(history.get("marked_system", []))
        total_feedback = marked_personal + marked_system
        
        if total_feedback > 0:
            # 基于反馈比例调整阈值
            personal_ratio = marked_personal / total_feedback
            if personal_ratio > 0.7:
                # 如果大部分是个人文件，降低阈值以捕获更多个人文件
                self.learning_data["confidence_threshold"] = max(0.4, self.learning_data.get("confidence_threshold", 0.6) - 0.05)
            elif personal_ratio < 0.3:
                # 如果大部分是系统文件，提高阈值以减少误报
                self.learning_data["confidence_threshold"] = min(0.8, self.learning_data.get("confidence_threshold", 0.6) + 0.05)
        
    def reset_learning(self):
        """重置学习数据"""
        self.learning_data = {
            "version": 1,
            "patterns": {
                "personal_keywords": [],
                "system_keywords": [],
                "software_keywords": [],
                "filename_patterns": {},
                "extension_weights": {},
                "dir_patterns": {},
                "content_patterns": {},
                "context_patterns": {},
                "personal_info_patterns": {},
                "term_patterns": {}
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
        }
        self._save_learning_data()

# 单例实例
intelligent_classifier = IntelligentClassifier()
