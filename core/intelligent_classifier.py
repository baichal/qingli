import os
import re
import json
import time
from pathlib import Path
from typing import Tuple, Dict, Optional, List
from collections import Counter
import hashlib

import threading

class IntelligentClassifier:
    """增强的智能文件分类器 - 具有自主判断能力"""
    
    # 学习数据文件
    LEARNING_DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "intelligent_learning.json")
    
    def __init__(self):
        self.learning_data = self._load_learning_data()
        self._setup_patterns()
        self._lock = threading.RLock()  # 可重入锁，用于线程安全
        # 启动时从系统日志中学习用户操作习惯
        try:
            self.learn_from_system_logs()
        except Exception as e:
            print(f"启动时学习系统日志失败: {e}")
    
    def _load_learning_data(self, recursion_count: int = 0) -> Dict:
        """加载学习数据"""
        if recursion_count > 3:
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
            return self._load_learning_data(recursion_count + 1)
    
    def _save_learning_data(self):
        """保存学习数据"""
        try:
            with self._lock:
                with open(self.LEARNING_DATA_FILE, "w", encoding="utf-8") as f:
                    json.dump(self.learning_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存学习数据失败: {e}")
    
    def _setup_patterns(self):
        """设置初始模式"""
        # 个人文件关键词
        self.personal_keywords = set([
            "我的", "私人", "个人", "private", "personal", "my", "mine",
            "简历", "resume", "cv", "身份证", "护照", "passport", "idcard",
            "合同", "contract", "offer", "薪资", "工资", "salary", "payroll",
            "银行", "bank", "保险", "insurance", "医疗", "medical", "health",
            "日记", "diary", "笔记", "note", "备忘录", "memo", "journal",
            "照片", "photo", "picture", "image", "pic", "相册", "album", "img",
            "视频", "video", "movie", "film", "音乐", "music", "song", "audio",
            "下载", "download", "桌面", "desktop", "文档", "document", "doc",
            "备份", "backup", "存档", "archive", "家庭", "family", "home",
            "旅行", "travel", "旅游", "trip", "vacation", "婚礼", "wedding",
            "生日", "birthday", "纪念日", "anniversary", "庆祝", "celebration",
            "个人项目", "personal project", "我的项目", "my project",
            "个人资料", "personal info", "个人信息", "personal information",
            "联系方式", "contact", "联系信息", "contact info",
            "电话号码", "phone", "手机号码", "mobile", "cell",
            "邮箱", "email", "电子邮件", "e-mail",
            "地址", "address", "家庭地址", "home address",
            "银行卡", "bank card", "信用卡", "credit card",
            "驾照", "driver license", "驾驶证", "driving license",
            "学历", "education", "学位", "degree", "毕业证", "diploma",
            "证书", "certificate", "资格证", "certification",
            "成绩单", "transcript", "成绩", "grades",
            "推荐信", "recommendation", "reference letter",
            "个人总结", "personal summary", "工作总结", "work summary",
            "计划", "plan", "规划", "planning", "方案", "scheme",
            "报告", "report", "总结", "summary", "分析", "analysis",
            "设计", "design", "创意", "creativity", "创意设计", "creative design",
            "作品", "work", "作品集", "portfolio", "项目", "project"
        ])
        
        # 系统文件关键词
        self.system_keywords = set([
            "system", "windows", "program", "driver", "service",
            "kernel", "registry", "boot", "config", "dll", "sys",
            "exe", "msi", "inf", "cat", "pdb", "ocx", "scr",
            "win32", "win64", "x86", "x64", "system32", "syswow64",
            "ntdll", "kernel32", "user32", "gdi32", "advapi32", "shell32",
            "systemroot", "windir", "program files", "programdata",
            "appdata", "local settings", "common files", "microsoft",
            "windows nt", "windows defender", "windows update",
            "device manager", "control panel", "registry editor",
            "task manager", "system configuration", "boot configuration"
        ])
        
        # 软件文件关键词
        self.software_keywords = set([
            "appdata", "cache", "temp", "tmp", "node_modules",
            "venv", "git", "build", "dist", "logs", "crash",
            "browser", "chrome", "firefox", "edge", "opera",
            "application data", "local", "roaming", "locallow",
            "program files", "program files (x86)", "common files",
            "microsoft", "adobe", "google", "mozilla", "apple",
            "java", "python", "node", "npm", "yarn", "pip",
            "docker", "virtualbox", "vmware", "visual studio",
            "eclipse", "intellij", "jetbrains", "vscode", "sublime",
            "photoshop", "illustrator", "premiere", "after effects",
            "word", "excel", "powerpoint", "outlook", "access",
            "chrome", "firefox", "edge", "opera", "safari",
            "wechat", "qq", "钉钉", "企业微信", "飞书", "lark",
            "dropbox", "google drive", "onedrive", "百度网盘", "阿里云盘",
            "spotify", "qq音乐", "网易云音乐", "酷狗音乐",
            "steam", "epic games", "origin", "battle.net",
            "photoshop", "lightroom", "illustrator", "indesign",
            "autocad", "3ds max", "maya", "blender",
            "unity", "unreal", "godot", "game maker",
            "wireshark", "postman", "insomnia", "soapui",
            "mysql", "postgresql", "mongodb", "redis", "elasticsearch",
            "nginx", "apache", "iis", "tomcat", "jetty",
            "docker", "kubernetes", "ansible", "terraform", "chef",
            "jenkins", "gitlab", "github", "bitbucket", "azure devops",
            "vscode", "atom", "sublime text", "notepad++", "vim", "emacs",
            "intellij idea", "eclipse", "netbeans", "visual studio code",
            "pycharm", "webstorm", "phpstorm", "rubymine", "clion",
            "android studio", "xcode", "visual studio", "visual studio community",
            "sql server", "oracle", "db2", "sqlite", "mariadb",
            "chrome", "firefox", "edge", "opera", "safari", "brave",
            "thunderbird", "outlook", "mail", "gmail", "yahoo mail",
            "skype", "teams", "slack", "discord", "zoom", "webex",
            "photoshop", "lightroom", "illustrator", "indesign", "premiere", "after effects",
            "word", "excel", "powerpoint", "outlook", "access", "publisher",
            "acrobat", "reader", "pdf", "adobe reader", "foxit reader",
            "vlc", "media player", "itunes", "spotify", "winamp", "foobar2000",
            "photoshop", "gimp", "paint.net", "corel draw", "affinity photo",
            "autocad", "sketchup", "revit", "archicad", "vectorworks",
            "3ds max", "maya", "blender", "cinema 4d", "houdini",
            "unity", "unreal engine", "godot", "game maker studio", "construct",
            "audacity", "adobe audition", "logic pro", "pro tools", "garageband",
            "premiere pro", "final cut pro", "avid media composer", "davinci resolve",
            "after effects", "nuke", "fusion", "blender", "cinema 4d",
            "figma", "sketch", "adobe xd", "invision", "principle",
            "wordpress", "joomla", "drupal", "magento", "shopify", "wix",
            "apache", "nginx", "iis", "tomcat", "jetty", "jboss",
            "mysql", "postgresql", "mongodb", "redis", "elasticsearch", "cassandra",
            "python", "java", "javascript", "typescript", "php", "ruby", "go", "rust", "c", "c++", "c#", "swift", "kotlin", "dart", "scala", "perl", "bash", "powershell", "batch",
            "node.js", "express", "react", "angular", "vue", "svelte", "next.js", "nuxt.js", "gatsby", "sapper", "nestjs", "fastify", "koa", "hapi", "express",
            "django", "flask", "fastapi", "bottle", "pyramid", "tornado", "cherrypy", "web2py", "falcon", "sanic",
            "spring", "spring boot", "spring mvc", "hibernate", "mybatis", "struts", "jsf", "vaadin", "play framework", "vert.x",
            "laravel", "symfony", "codeigniter", "yii", "cakephp", "zend framework", "slim", "lumen", "phalcon", "fuelphp",
            "rails", "sinatra", "padrino", "hanami", "cuba", "roda", "ramaze", "merb", "mojolicious",
            "gin", "echo", "fiber", "beego", "chi", "martini", "revel", "iris", "buffalo",
            "actix", "rocket", "warp", "tide", "axum", "salvo", "poem", "gotham", "nickel",
            "flask", "django", "fastapi", "bottle", "pyramid", "tornado", "cherrypy", "web2py", "falcon", "sanic",
            "express", "koa", "hapi", "fastify", "nestjs", "adonis", "sails", "loopback", "meteor", "mean", "mern",
            "react", "vue", "angular", "svelte", "preact", "inferno", "riot", "solid", "qwik", "lit",
            "redux", "mobx", "zustand", "jotai", "recoil", "valtio", "xstate", "immer", "normalizr",
            "webpack", "vite", "rollup", "parcel", "browserify", "gulp", "grunt", "esbuild", "swc",
            "babel", "typescript", "coffeescript", "elm", "reason", "purescript", "clojurescript", "livescript",
            "sass", "less", "stylus", "postcss", "tailwind", "bootstrap", "foundation", "materialize", "bulma",
            "jest", "mocha", "chai", "sinon", "cypress", "puppeteer", "playwright", "testing-library", "enzyme",
            "eslint", "prettier", "stylelint", "commitlint", "husky", "lint-staged", "standard", "semistandard",
            "npm", "yarn", "pnpm", "lerna", "nx", "rush", "workspaces", "monorepo", "polyrepo",
            "git", "github", "gitlab", "bitbucket", "azure devops", "sourcehut", "gitea", "forgejo",
            "jenkins", "travis", "circleci", "github actions", "gitlab ci", "azure pipelines", "bitbucket pipelines",
            "docker", "kubernetes", "docker compose", "docker swarm", "minikube", "kind", "k3s", "openshift", "rancher",
            "terraform", "ansible", "puppet", "chef", "saltstack", "packer", "vagrant", "cloudformation", "arm",
            "aws", "azure", "google cloud", "digitalocean", "linode", "vultr", "heroku", "netlify", "vercel", "github pages",
            "mysql", "postgresql", "mongodb", "redis", "elasticsearch", "cassandra", "dynamodb", "aurora", "neptune", "documentdb",
            "sql", "nosql", "newsql", "graphql", "rest", "grpc", "soap", "graphql", "restful", "api", "microservices", "monolith",
            "frontend", "backend", "fullstack", "mobile", "desktop", "web", "ios", "android", "flutter", "react native", "xamarin", "ionic", "cordova",
            "agile", "scrum", "kanban", "waterfall", "devops", "ci/cd", "continuous integration", "continuous deployment", "continuous delivery",
            "agile", "scrum", "kanban", "waterfall", "devops", "ci/cd", "continuous integration", "continuous deployment", "continuous delivery"
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
        
        # 关键词匹配（添加单词边界检查）
        for keyword in self.personal_keywords:
            if len(keyword) < 3:
                # 短关键词要求完整单词匹配
                pattern = r'\b' + re.escape(keyword) + r'\b'
                if re.search(pattern, path_lower):
                    features["personal_keywords"] += 1
            else:
                # 长关键词可以直接包含匹配，但也要考虑边界
                if keyword in path_lower:
                    # 检查是否是完整单词或路径组件
                    if re.search(r'[\\/\s\._-]' + re.escape(keyword) + r'[\\/\s\._-]|^' + re.escape(keyword) + r'[\\/\s\._-]|[\\/\s\._-]' + re.escape(keyword) + r'$|^' + re.escape(keyword) + r'$', path_lower):
                        features["personal_keywords"] += 1
        for keyword in self.system_keywords:
            if len(keyword) < 3:
                pattern = r'\b' + re.escape(keyword) + r'\b'
                if re.search(pattern, path_lower):
                    features["system_keywords"] += 1
            else:
                if keyword in path_lower:
                    if re.search(r'[\\/\s\._-]' + re.escape(keyword) + r'[\\/\s\._-]|^' + re.escape(keyword) + r'[\\/\s\._-]|[\\/\s\._-]' + re.escape(keyword) + r'$|^' + re.escape(keyword) + r'$', path_lower):
                        features["system_keywords"] += 1
        for keyword in self.software_keywords:
            if len(keyword) < 3:
                pattern = r'\b' + re.escape(keyword) + r'\b'
                if re.search(pattern, path_lower):
                    features["software_keywords"] += 1
            else:
                if keyword in path_lower:
                    if re.search(r'[\\/\s\._-]' + re.escape(keyword) + r'[\\/\s\._-]|^' + re.escape(keyword) + r'[\\/\s\._-]|[\\/\s\._-]' + re.escape(keyword) + r'$|^' + re.escape(keyword) + r'$', path_lower):
                        features["software_keywords"] += 1
        
        # 目录特征
        user_profile = os.environ.get("USERPROFILE", "")
        if user_profile and path_lower.startswith(user_profile.lower()):
            features["is_user_dir"] = True
            
            # 检查是否在个人目录
            personal_dirs = [
                "desktop", "documents", "downloads", "pictures", "videos", "music",
                "favorites", "contacts", "links", "saved games", "searches", "3d objects",
                "onedrive", "dropbox", "google drive", "box", "icloud",
                "个人", "私人", "我的文档", "我的图片", "我的视频", "我的音乐",
                "documents and settings", "my documents", "my pictures", "my videos", "my music"
            ]
            for dir_name in personal_dirs:
                if f"{os.sep}{dir_name}{os.sep}" in path_lower:
                    features["personal_keywords"] += 2
                    break
        
        # 系统目录检查
        system_dirs = [
            "windows", "program files", "program files (x86)", "programdata", 
            "syswow64", "system32", "winnt", "system volume information",
            "recycler", "$recycle.bin", "appdata", "local settings",
            "common files", "microsoft", "windows.old", "windowsapps",
            "windows/system32", "windows/syswow64", "windows/system", "windows/inf"
        ]
        for dir_name in system_dirs:
            if f"{os.sep}{dir_name}{os.sep}" in path_lower or dir_name in path_lower:
                features["is_system_dir"] = True
                features["system_keywords"] += 2
                break
        
        # 软件目录检查
        software_dirs = [
            "appdata/local", "appdata/roaming", "appdata/locallow",
            "node_modules", "venv", "virtualenv", "env", ".venv",
            ".git", "build", "dist", "target", "obj", "bin", "lib",
            "cache", "temp", "tmp", "logs", "crash", "debug", "release",
            "node.js", "npm", "yarn", "pip", "composer", "gradle", "maven",
            "docker", "virtualbox", "vmware", "wsl", "linux", "ubuntu", "debian"
        ]
        for dir_name in software_dirs:
            if f"{os.sep}{dir_name}{os.sep}" in path_lower or dir_name in path_lower:
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
        
        # 内容分析（对于可查看内容的文件）
        # 可查看内容的文件类型
        content_viewable_extensions = [".txt", ".docx", ".pdf", ".md", ".rtf", ".odt", ".csv", ".xls", ".xlsx", ".json", ".xml", ".html", ".css", ".js", ".py", ".java", ".cpp", ".h", ".c", ".log", ".ini", ".conf", ".cfg"]
        
        # 不可查看内容的文件类型（跳过内容分析）
        content_non_viewable_extensions = [".mp4", ".mp3", ".avi", ".mov", ".wmv", ".flv", ".mkv", ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".zip", ".rar", ".7z", ".exe", ".dll", ".sys", ".msi", ".iso", ".img", ".bin", ".dat", ".db", ".sqlite", ".bak", ".tmp"]
        
        # 对于可查看内容的文件，进行内容分析
        if features["extension"] in content_viewable_extensions:
            try:
                size = os.path.getsize(file_path)
                # 增加文件大小限制，允许读取更大的文件以提高学习精度
                if size < 2 * 1024 * 1024:  # 小于2MB
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        # 增加内容读取长度，允许读取更多内容以提高学习精度
                        content = f.read(500000).lower()  # 最多读取500KB
                        # 检查个人内容关键词
                        personal_content_keywords = [
                            "我", "我的", "个人", "私人", "简历", "照片", "家庭", "联系方式", "电话", "邮箱", "地址", "身份证", "护照", "银行卡", "工资", "合同", "offer", "推荐信",
                            "个人信息", "个人资料", "个人总结", "个人计划", "个人项目", "个人作品", "个人简历", "个人照片", "个人视频", "个人音乐",
                            "家庭照片", "家庭视频", "家庭聚会", "家庭旅行", "家庭计划", "家庭活动",
                            "联系方式", "联系信息", "电话号码", "手机号码", "电子邮箱", "邮寄地址", "家庭地址", "工作地址",
                            "身份证号", "护照号", "银行卡号", "信用卡号", "社保号", "医保号", "驾照号", "学生证号",
                            "薪资", "工资", "奖金", "福利", "待遇", "收入", "支出", "财务", "理财", "投资",
                            "合同", "协议", "条款", "条件", "约定", "承诺", "保证", "责任", "义务", "权利",
                            "offer", "录用", "入职", "离职", "晋升", "调岗", "培训", "考核", "绩效", "评价",
                            "推荐信", "推荐", "介绍", "评价", "证明", "证书", "资质", "资格", "能力", "技能"
                        ]
                        for keyword in personal_content_keywords:
                            if keyword in content:
                                features["content_score"] += 1
                        
                        # 检查系统内容关键词
                        system_content_keywords = [
                            "system", "windows", "registry", "driver", "service", "kernel", "boot", "config",
                            "operating system", "os", "windows update", "device manager", "control panel", "task manager",
                            "registry editor", "system configuration", "boot configuration", "device driver", "system service",
                            "kernel mode", "user mode", "system32", "syswow64", "ntdll", "kernel32", "user32", "gdi32",
                            "advapi32", "shell32", "win32", "win64", "x86", "x64", "32bit", "64bit",
                            "systemroot", "windir", "program files", "programdata", "common files", "microsoft",
                            "windows nt", "windows defender", "windows firewall", "windows security", "windows defender firewall"
                        ]
                        for keyword in system_content_keywords:
                            if keyword in content:
                                features["system_keywords"] += 0.5
                        
                        # 检查软件内容关键词
                        software_content_keywords = [
                            "appdata", "cache", "temp", "node_modules", "venv", "git", "build", "dist",
                            "application", "software", "program", "app", "tool", "utility", "library", "framework",
                            "package", "dependency", "module", "component", "plugin", "extension", "addon", "feature",
                            "installation", "setup", "install", "uninstall", "update", "upgrade", "downgrade", "patch",
                            "development", "dev", "production", "prod", "test", "debug", "release", "build",
                            "compilation", "compile", "link", "build system", "make", "cmake", "gradle", "maven",
                            "npm", "yarn", "pip", "composer", "nuget", "cargo", "go mod", "gem",
                            "git", "github", "gitlab", "bitbucket", "version control", "source control", "repository", "repo",
                            "docker", "container", "kubernetes", "k8s", "orchestration", "deployment", "devops",
                            "ci", "cd", "continuous integration", "continuous deployment", "jenkins", "travis", "circleci", "github actions"
                        ]
                        for keyword in software_content_keywords:
                            if keyword in content:
                                features["software_keywords"] += 0.5
                        
                        # 提取内容模式
                        content_patterns = self._extract_content_patterns(content)
                        features["content_patterns"] = content_patterns
            except Exception:
                pass
        # 对于不可查看内容的文件，跳过内容分析，仅根据文件名和路径进行分析
        elif features["extension"] in content_non_viewable_extensions:
            # 仅根据文件名和路径进行分析
            # 添加针对非文本文件的特殊处理逻辑
            filename_lower = features["filename"].lower()
            
            # 个人文件相关关键词
            personal_file_keywords = ["照片", "图片", "视频", "音乐", "电影", "家庭", "个人", "私人", "简历", "作品集", "相册", "旅行", "婚礼", "生日", "纪念日", "个人资料"]
            
            # 系统文件相关关键词
            system_file_keywords = ["system", "windows", "driver", "service", "kernel", "boot", "config", "update", "patch"]
            
            # 软件文件相关关键词
            software_file_keywords = ["setup", "install", "uninstall", "update", "app", "software", "driver", "plugin", "extension", "package", "installer", "archive"]
            
            # 软件文件扩展名
            software_extensions = [".exe", ".msi", ".dll", ".sys", ".zip", ".rar", ".7z"]
            
            # 媒体文件扩展名
            media_extensions = [".mp4", ".mp3", ".avi", ".mov", ".wmv", ".flv", ".mkv", ".jpg", ".jpeg", ".png", ".gif", ".bmp"]
            
            # 根据文件名关键词进行分析
            for keyword in personal_file_keywords:
                if keyword in filename_lower:
                    features["personal_keywords"] += 1
            
            for keyword in system_file_keywords:
                if keyword in filename_lower:
                    features["system_keywords"] += 1
            
            for keyword in software_file_keywords:
                if keyword in filename_lower:
                    features["software_keywords"] += 1
            
            # 对于软件文件扩展名的特殊处理
            if features["extension"] in software_extensions:
                # 软件文件扩展名更可能是软件文件
                features["software_keywords"] += 2
                # 检查是否在下载目录中
                path_lower = features["path"].lower()
                if "downloads" in path_lower:
                    features["software_keywords"] += 1
            
            # 对于媒体文件的特殊处理
            if features["extension"] in media_extensions:
                # 媒体文件更可能是个人文件
                if features["is_user_dir"]:
                    features["personal_keywords"] += 1
                # 检查是否在个人媒体目录中
                path_lower = features["path"].lower()
                media_dirs = ["pictures", "photos", "images", "videos", "music", "media", "相册", "视频", "音乐"]
                for dir_name in media_dirs:
                    if f"{os.sep}{dir_name}{os.sep}" in path_lower:
                        features["personal_keywords"] += 2
                        break
        
        # 上下文分析（同一目录、父目录和子目录的文件）
        try:
            dir_path = features["dir_path"]
            if os.path.exists(dir_path):
                # 同一目录分析
                files_in_dir = os.listdir(dir_path)
                personal_file_count = 0
                system_file_count = 0
                software_file_count = 0
                
                for file in files_in_dir:  # 分析所有文件
                    file_lower = file.lower()
                    if any(pk in file_lower for pk in self.personal_keywords):
                        personal_file_count += 1
                    if any(sk in file_lower for sk in self.system_keywords):
                        system_file_count += 1
                    if any(swk in file_lower for swk in self.software_keywords):
                        software_file_count += 1
                
                # 父目录分析
                parent_dir = os.path.dirname(dir_path)
                if os.path.exists(parent_dir) and parent_dir != dir_path:
                    parent_files = os.listdir(parent_dir)
                    for file in parent_files:  # 分析所有文件
                        file_lower = file.lower()
                        if any(pk in file_lower for pk in self.personal_keywords):
                            personal_file_count += 0.5
                        if any(sk in file_lower for sk in self.system_keywords):
                            system_file_count += 0.5
                        if any(swk in file_lower for swk in self.software_keywords):
                            software_file_count += 0.5
                
                # 子目录分析
                try:
                    subdirs = [d for d in os.listdir(dir_path) if os.path.isdir(os.path.join(dir_path, d))]
                    for subdir in subdirs:  # 分析所有子目录
                        subdir_path = os.path.join(dir_path, subdir)
                        subdir_files = os.listdir(subdir_path)
                        for file in subdir_files:  # 分析每个子目录的所有文件
                            file_lower = file.lower()
                            if any(pk in file_lower for pk in self.personal_keywords):
                                personal_file_count += 0.3
                            if any(sk in file_lower for sk in self.system_keywords):
                                system_file_count += 0.3
                            if any(swk in file_lower for swk in self.software_keywords):
                                software_file_count += 0.3
                except Exception:
                    pass
                
                # 计算上下文得分
                max_count = max(personal_file_count, system_file_count, software_file_count)
                if max_count > 0:
                    if personal_file_count == max_count:
                        features["context_score"] = 1
                    elif system_file_count == max_count:
                        features["context_score"] = -1
                    elif software_file_count == max_count:
                        features["context_score"] = -2
        except Exception:
            pass
        
        return features
    
    def _calculate_confidence(self, features: Dict) -> float:
        """计算分类置信度"""
        score = 0
        max_score = 25  # 增加最大分数以容纳新特征
        
        # 关键词分数 - 增加权重
        score += min(features["personal_keywords"] * 1.0, 4)  # 增加个人关键词权重
        score += min(features["system_keywords"] * 1.0, 4)  # 增加系统关键词权重
        score += min(features["software_keywords"] * 1.0, 4)  # 增加软件关键词权重
        
        # 目录特征 - 增加权重
        if features["is_user_dir"]:
            score += 3  # 增加用户目录权重
        if features["is_system_dir"]:
            score += 3  # 增加系统目录权重
        if features["is_software_dir"]:
            score += 3  # 增加软件目录权重
        
        # 文件特征 - 调整权重
        score += features["size_score"] * 0.6  # 增加文件大小权重
        score += features["time_score"] * 0.6  # 增加时间权重
        score += features["creation_score"] * 0.4  # 增加创建时间权重
        score += features["content_score"] * 1.0  # 增加内容分析权重
        
        # 内容模式特征 - 增加权重
        content_patterns = features.get("content_patterns", {})
        if content_patterns:
            # 个人识别信息 - 增加权重
            personal_info_score = content_patterns.get("email_patterns", 0) * 0.6
            personal_info_score += content_patterns.get("phone_patterns", 0) * 0.6
            personal_info_score += content_patterns.get("id_patterns", 0) * 1.0  # 增加身份证等重要信息权重
            personal_info_score += content_patterns.get("address_patterns", 0) * 0.4
            score += min(personal_info_score, 3)  # 增加最大分数
            
            # 个人术语
            score += content_patterns.get("personal_terms", 0) * 0.4
            
            # 系统术语
            score += content_patterns.get("system_terms", 0) * 0.4
            
            # 软件术语
            score += content_patterns.get("software_terms", 0) * 0.4
        
        # 上下文特征 - 增加权重
        if features["context_score"] > 0:
            score += 1.5  # 增加个人文件上下文权重
        elif features["context_score"] == -1:
            score -= 1.5  # 增加系统文件上下文权重
        elif features["context_score"] == -2:
            score -= 2.0  # 增加软件文件上下文权重
        
        # 文件名和扩展名特征 - 调整权重
        score += features["filename_complexity"] * 0.6  # 增加文件名复杂度权重
        score += features["extension_rarity"] * 0.4  # 增加扩展名稀有度权重
        
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
        personal_score = features["personal_keywords"] + (3 if features["is_user_dir"] else 0)  # 增加用户目录权重
        personal_score += features["content_score"] * 1.5  # 保持内容分析权重
        personal_score += features["time_score"] * 0.6  # 增加时间权重
        personal_score += features["creation_score"] * 0.4  # 调整创建时间权重
        if features["context_score"] > 0:
            personal_score += 1.5  # 增加个人文件上下文权重
        
        system_score = features["system_keywords"] + (3 if features["is_system_dir"] else 0)  # 增加系统目录权重
        system_score += features["filename_complexity"] * 0.6  # 增加文件名复杂度权重
        if features["context_score"] == -1:
            system_score += 1.5  # 增加系统文件上下文权重
        
        software_score = features["software_keywords"] + (3 if features["is_software_dir"] else 0)  # 增加软件目录权重
        software_score += features["extension_rarity"] * 0.4  # 调整扩展名稀有度权重
        if features["context_score"] == -2:
            software_score += 2.0  # 增加软件文件上下文权重
        
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
            if features["context_score"] == -1:
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
            if features["context_score"] == -2:
                reasons.append("同一目录有其他软件文件")
            # 内容模式特征
            content_patterns = features.get("content_patterns", {})
            if content_patterns and content_patterns.get("software_terms", 0) > 0:
                reasons.append("包含软件术语")
        else:
            reasons.append("无法确定类别")
        
        return ", ".join(reasons) if reasons else "未知原因"
    
    def learn_from_feedback(self, file_path: str, is_personal: bool, confidence: float = 1.0):
        """从用户反馈中学习"""
        with self._lock:
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
            base_learning_rate = 0.15  # 增加初始学习率，让分类器更快适应
            # 随着学习次数增加，逐渐减小学习率，但保持一定的学习能力
            learning_rate = base_learning_rate * (1 - min(total_learning / 2000, 0.7))  # 减慢学习率衰减速度
            
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
            if total_learning % 5 == 0:  # 每5次学习调整一次，增加调整频率
                self._adjust_confidence_threshold()
            
            # 保存学习数据
            self._save_learning_data()
    
    def learn_from_action(self, file_paths: List[str], action: str):
        """从用户操作中学习"""
        for file_path in file_paths:
            file_hash = hashlib.md5(file_path.encode()).hexdigest()
            
            # 更新历史
            if action == "delete" and file_hash not in self.learning_data["user_history"]["deleted_files"]:
                with self._lock:
                    self.learning_data["user_history"]["deleted_files"].append(file_hash)
                # 学习为非个人文件
                self.learn_from_feedback(file_path, False, 0.8)
            elif action == "keep" and file_hash not in self.learning_data["user_history"]["kept_files"]:
                with self._lock:
                    self.learning_data["user_history"]["kept_files"].append(file_hash)
                # 学习为个人文件
                self.learn_from_feedback(file_path, True, 0.8)
    
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
        
        # 邮箱模式 - 只统计数量，不存储具体内容
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        email_matches = re.findall(email_pattern, content)
        patterns["email_patterns"] = len(email_matches)
        
        # 电话号码模式 - 只统计数量，不存储具体内容
        phone_pattern = r'1[3-9]\d{9}'  # 中国手机号
        phone_matches = re.findall(phone_pattern, content)
        patterns["phone_patterns"] = len(phone_matches)
        
        # 身份证号模式 - 只统计数量，不存储具体内容
        id_pattern = r'[1-9]\d{5}(19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[0-9Xx]'
        id_matches = re.findall(id_pattern, content)
        patterns["id_patterns"] = len(id_matches)
        
        # 地址模式 - 只统计数量，不存储具体内容
        address_pattern = r'[省市区县镇乡村]'
        address_matches = re.findall(address_pattern, content)
        patterns["address_patterns"] = len(address_matches)
        
        # 日期模式 - 只统计数量，不存储具体内容
        date_pattern = r'\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日]?'
        date_matches = re.findall(date_pattern, content)
        patterns["date_patterns"] = len(date_matches)
        
        # 数字模式 - 只统计数量，不存储具体内容
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
    
    def learn_from_system_logs(self):
        """从系统操作日志中学习用户操作习惯"""
        try:
            # 读取Windows事件日志
            import win32evtlog
            import win32evtlogutil
            import win32con
            
            # 打开系统事件日志
            server = "localhost"
            logtype = "Security"
            hand = win32evtlog.OpenEventLog(server, logtype)
            
            # 读取最近的事件
            flags = win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ
            events = win32evtlog.ReadEventLog(hand, flags, 0)
            
            # 分析事件
            file_operations = []
            for event in events:  # 处理所有事件
                try:
                    event_id = event.EventID & 0xFFFF
                    # 查找文件操作相关的事件
                    if event_id in [4663, 4656, 4658]:  # 文件操作事件ID
                        data = event.StringInserts
                        if data:
                            # 提取文件路径
                            for item in data:
                                if os.path.exists(item):
                                    # 假设删除操作是系统/软件文件
                                    # 假设创建/修改操作可能是个人文件
                                    if event_id == 4663:  # 文件删除
                                        file_operations.append((item, "delete"))
                                    else:  # 文件创建/修改
                                        file_operations.append((item, "create"))
                except Exception:
                    pass
            
            win32evtlog.CloseEventLog(hand)
            
            # 从文件操作中学习
            for file_path, operation in file_operations:
                if operation == "delete":
                    # 学习为非个人文件
                    self.learn_from_feedback(file_path, False, 0.9)
                elif operation == "create":
                    # 学习为个人文件
                    self.learn_from_feedback(file_path, True, 0.8)
            
            # 读取最近的文件操作历史
            # 从最近访问的文件中学习
            recent_files = []
            try:
                # 读取最近使用的文件
                import winreg
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\RecentDocs")
                for i in range(100):
                    try:
                        value = winreg.EnumValue(key, i)
                        if value[1]:
                            # 提取文件路径
                            path = value[1]
                            if os.path.exists(path):
                                recent_files.append(path)
                    except WindowsError:
                        break
                winreg.CloseKey(key)
            except Exception:
                pass
            
            # 从最近文件中学习
            for file_path in recent_files:  # 处理所有最近文件
                # 假设最近访问的文件可能是个人文件
                self.learn_from_feedback(file_path, True, 0.7)
            
            return f"从系统日志中学习了 {len(file_operations) + len(recent_files)} 个文件操作"
        except ImportError:
            # 如果没有win32evtlog模块，尝试其他方法
            try:
                # 读取最近的文件操作历史
                import os
                import glob
                
                # 读取最近访问的文件
                recent_files = []
                # 尝试读取Windows最近文件
                recent_dir = os.path.join(os.environ.get("USERPROFILE", ""), "AppData", "Roaming", "Microsoft", "Windows", "Recent")
                if os.path.exists(recent_dir):
                    lnk_files = glob.glob(os.path.join(recent_dir, "*.lnk"))
                    for lnk_file in lnk_files:  # 处理所有快捷方式
                        try:
                            # 尝试解析快捷方式
                            import winshell
                            shortcut = winshell.shortcut(lnk_file)
                            target = shortcut.path
                            if os.path.exists(target):
                                recent_files.append(target)
                        except Exception:
                            pass
                
                # 从最近文件中学习
                for file_path in recent_files:
                    # 假设最近访问的文件可能是个人文件
                    self.learn_from_feedback(file_path, True, 0.7)
                
                return f"从最近文件中学习了 {len(recent_files)} 个文件"
            except Exception:
                # 如果所有方法都失败，返回空
                return "无法读取系统日志"
        except Exception as e:
            print(f"读取系统日志失败: {e}")
            return "读取系统日志失败"

# 单例实例
intelligent_classifier = IntelligentClassifier()
