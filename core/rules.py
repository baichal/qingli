import os
import sys

# ─────────────────────────────────────────
# 当前用户信息
# ─────────────────────────────────────────
CURRENT_USER = os.environ.get("USERNAME", "")
USER_PROFILE = os.environ.get("USERPROFILE", f"C:\\Users\\{CURRENT_USER}")
APPDATA      = os.environ.get("APPDATA", "")
LOCAL_APPDATA = os.environ.get("LOCALAPPDATA", "")

# ─────────────────────────────────────────
# 排除目录
# ─────────────────────────────────────────
EXCLUDE_ABSOLUTE_DIRS = [
    "C:\\Windows",
    "C:\\Windows\\System32",
    "C:\\Windows\\SysWOW64",
    "C:\\Windows\\WinSxS",
    "C:\\Windows\\Installer",
    "C:\\Program Files",
    "C:\\Program Files (x86)",
    "C:\\ProgramData",
    "C:\\Users\\All Users",
    "C:\\Users\\Default",
    "C:\\Users\\Default User",
    "C:\\System Volume Information",
    "C:\\$Recycle.Bin",
    "C:\\$WinREAgent",
    "C:\\Recovery",
]

EXCLUDE_DIR_NAMES = [
    "node_modules",
    "__pycache__",
    ".git",
    "venv",
    ".venv",
    "env",
    ".env",
    "dist",
    "build",
    ".gradle",
    ".m2",
    ".npm",
    ".yarn",
    "site-packages",
    "AppData\\Local\\Temp",
    "AppData\\LocalLow",
    "Temp",
    "tmp",
    "cache",
    "Cache",
    "CacheStorage",
    "Code Cache",
    "GPUCache",
    "ShaderCache",
    # 回收站
    "$Recycle.Bin",
    "$RECYCLE.BIN",
    "Recycle.Bin",
    "RECYCLE.BIN",
    "Recycled",
    "Recycler",
]

EXCLUDE_FILE_NAMES = [
    "pagefile.sys",
    "hiberfil.sys",
    "swapfile.sys",
    "desktop.ini",
    "thumbs.db",
    "ntuser.dat",
    "ntuser.ini",
    "NTUSER.DAT",
]

# ─────────────────────────────────────────
# 核心关键词识别表（高优先级，只要包含就识别）
# key:   核心关键词（小写）
# value: 软件显示名称
# 用途：对于常用软件，只要目录名包含核心关键词就识别，避免变体漏判
# ─────────────────────────────────────────
SOFTWARE_CORE_KEYWORDS = {
    # ── 聊天 / 即时通讯（最常用，高优先级）──────────────────
    "wechat":                "微信",
    "微信":                   "微信",
    "tencent":               "QQ",
    "qq":                    "QQ",
    "dingtalk":              "钉钉",
    "feishu":                "飞书",
    "lark":                  "飞书",
    "wxwork":                "企业微信",
    "telegram":              "Telegram",
    "teams":                 "Microsoft Teams",
    "slack":                 "Slack",
    "discord":               "Discord",
    "skype":                 "Skype",
    
    # ── 视频编辑 ───────────────────────────
    "jianying":              "剪映",
    "capcut":                "CapCut",
    "prproj":                "Adobe Premiere",
    "premiere":              "Adobe Premiere",
    "after effects":         "Adobe After Effects",
    "ae":                    "Adobe After Effects",
    "达芬奇":                 "DaVinci Resolve",
    "davinci":               "DaVinci Resolve",
    
    # ── 开发工具（重要，避免误扫描）─────────────────────
    "sdk":                   "SDK",
    "android-sdk":           "Android SDK",
    "android sdk":           "Android SDK",
    "platforms":             "Android SDK",
    "ndk":                   "Android NDK",
    "gradle":                "Gradle",
    "maven":                 "Maven",
    "node_modules":          "Node.js",
    "nodejs":                "Node.js",
    "python":                "Python",
    "anaconda":              "Anaconda",
    "miniconda":             "Miniconda",
    "venv":                  "Python虚拟环境",
    "virtualenv":            "Python虚拟环境",
    ".venv":                 "Python虚拟环境",
    "go/pkg":                "Go",
    "gopath":                "Go",
    "rust":                  "Rust",
    ".cargo":                "Rust",
    "cargo":                 "Rust",
    "ruby":                  "Ruby",
    ".gem":                  "Ruby",
    "gem":                   "Ruby",
    "php":                   "PHP",
    "composer":              "Composer",
    "vendor":                "Composer",
    "unity":                 "Unity",
    "unreal":                "Unreal Engine",
    "ue5":                   "Unreal Engine",
    "ue4":                   "Unreal Engine",
    "godot":                 "Godot",
    
    # ── 网盘 / 同步 ───────────────────────
    "baidunetdisk":          "百度网盘",
    "baiduyunguanjia":       "百度云管家",
    "onedrive":              "OneDrive",
    "nutstore":              "坚果云",
    "dropbox":               "Dropbox",
    "googledrive":           "Google Drive",
    "微云":                   "腾讯微云",
    
    # ── 媒体 / 娱乐 ──────────────────────
    "cloudmusic":            "网易云音乐",
    "qqmusic":               "QQ音乐",
    "kugou":                 "酷狗音乐",
    "kuwo":                  "酷我音乐",
    "spotify":               "Spotify",
    "iqiyi":                 "爱奇艺",
    "youku":                 "优酷",
    "tencentvideo":          "腾讯视频",
    "mango":                 "芒果TV",
    "bilibili":              "哔哩哔哩",
}

# ─────────────────────────────────────────
# 已知软件目录映射表（精确匹配，中等优先级）
# key:   目录名关键词（小写）
# value: 软件显示名称
# ─────────────────────────────────────────
KNOWN_SOFTWARE_DIRS = {
    # ── 聊天 / 即时通讯 ──────────────────
    "wechat files":          "微信",
    "wechat_files":          "微信",
    "微信文件":               "微信",
    "tencent files":         "QQ",
    "dingtalk":              "钉钉",
    "feishu":                "飞书",
    "lark":                  "飞书",
    "wxwork":                "企业微信",
    "telegram desktop":      "Telegram",
    "microsoft teams":       "Microsoft Teams",
    "slack":                 "Slack",
    "discord":               "Discord",
    "skype":                 "Skype",

    # ── 邮件客户端 ────────────────────────
    "thunderbird":           "Thunderbird",
    "foxmail":               "Foxmail",
    "netease mail master":   "网易邮件大师",
    "outlook":               "Outlook",

    # ── 网盘 / 同步 ───────────────────────
    "baidunetdisk":          "百度网盘",
    "baiduyunguanjia":       "百度云管家",
    "onedrive":              "OneDrive",
    "nutstore":              "坚果云",
    "dropbox":               "Dropbox",
    "googledrive":           "Google Drive",
    "box":                   "Box",
    "微云":                   "腾讯微云",

    # ── 浏览器 ───────────────────────────
    "google\\chrome":        "Google Chrome",
    "microsoft\\edge":       "Microsoft Edge",
    "mozilla\\firefox":      "Firefox",
    "brave-browser":         "Brave",
    "opera software":        "Opera",
    "vivaldi":               "Vivaldi",
    "360chrome":             "360极速浏览器",
    "360se6":                "360安全浏览器",

    # ── 开发工具 ──────────────────────────
    "code":                  "VS Code",
    "jetbrains":             "JetBrains IDE",
    "postman":               "Postman",
    "insomnia":              "Insomnia",
    "sourcetree":            "SourceTree",
    "github desktop":        "GitHub Desktop",
    "gitkraken":             "GitKraken",
    "dbeaver":               "DBeaver",
    "navicat":               "Navicat",
    "hbuilderx":             "HBuilderX",
    "wechatdevtools":        "微信开发者工具",
    "android studio":        "Android Studio",
    "xshell":                "Xshell",
    "xftp":                  "Xftp",
    "finalshell":            "FinalShell",
    "terminus":              "Terminus",
    "mobaxterm":             "MobaXterm",

    # ── 笔记 / 效率 ───────────────────────
    "notion":                "Notion",
    "obsidian":              "Obsidian",
    "typora":                "Typora",
    "onenote":               "OneNote",
    "evernote":              "Evernote",
    "youdaonote":            "有道云笔记",
    "印象笔记":               "印象笔记",
    "wiz":                   "为知笔记",
    "logseq":                "Logseq",
    "roamresearch":          "Roam Research",

    # ── 媒体 / 娱乐 ──────────────────────
    "netease\\cloudmusic":   "网易云音乐",
    "qqmusiccache":          "QQ音乐",
    "qqmusic":               "QQ音乐",
    "kugou":                 "酷狗音乐",
    "kuwo":                  "酷我音乐",
    "spotify":               "Spotify",
    "iqiyi":                 "爱奇艺",
    "youku":                 "优酷",
    "tencentvideo":          "腾讯视频",
    "mango":                 "芒果TV",
    "bilibili":              "哔哩哔哩",
    "potplayer":             "PotPlayer",
    "vlc":                   "VLC",

    # ── 视频编辑 ───────────────────────────
    "jianying":              "剪映",
    "jianyingpresets":       "剪映预设",
    "capcut":                "CapCut",
    "prproj":                "Adobe Premiere",
    "after effects":         "Adobe After Effects",
    "ae":                    "Adobe After Effects",
    "premiere":              "Adobe Premiere",
    "pr":                    "Adobe Premiere",
    "达芬奇":                 "DaVinci Resolve",
    "davinci":               "DaVinci Resolve",
    "final cut":             "Final Cut Pro",
    "剪映专业版":              "剪映专业版",
    "剪映专业版数据":           "剪映专业版",

    # ── 设计 / 创意 ──────────────────────
    "figma":                 "Figma",
    "sketch":                "Sketch",
    "adobe":                 "Adobe 系列",
    "affinity":              "Affinity",
    "blender":               "Blender",

    # ── 办公 ─────────────────────────────
    "wpsoffice":             "WPS Office",
    "wps":                   "WPS",
    "libreoffice":           "LibreOffice",
    "zoom":                  "Zoom",
    "todesk":                "ToDesk",
    "teamviewer":            "TeamViewer",
    "anydesk":               "AnyDesk",
    "sunlogin":              "向日葵远程",

    # ── 安全 ─────────────────────────────
    "1password":             "1Password",
    "bitwarden":             "Bitwarden",
    "keepass":               "KeePass",
    "lastpass":              "LastPass",

    # ── 游戏 ─────────────────────────────
    "steam":                 "Steam",
    "epic games":            "Epic Games",
    "battle.net":            "Battle.net",
    "origin":                "Origin/EA",
    "ubisoft":               "Ubisoft Connect",
    "wegame":                "WeGame",
}

# ─────────────────────────────────────────
# 软件根目录（这些目录下的所有子目录都视为软件目录）
# ─────────────────────────────────────────
SOFTWARE_ROOT_DIRS = [
    # AppData 下
    os.path.join(APPDATA),
    os.path.join(LOCAL_APPDATA),
    # 用户目录下的常见软件位置
    os.path.join(USER_PROFILE, "AppData", "Roaming"),
    os.path.join(USER_PROFILE, "AppData", "Local"),
]

# ─────────────────────────────────────────
# 扫描规则
# ─────────────────────────────────────────
SCAN_RULES = {

    # ── 高风险凭证 ──────────────────────────
    "credential": {
        "label": "高风险凭证",
        "icon": "🔴",
        "risk": "high",
        "color": "#ff4d4f",
        "priority_paths": [
            os.path.join(USER_PROFILE, ".ssh"),
            os.path.join(USER_PROFILE, ".aws"),
            os.path.join(USER_PROFILE, ".config"),
            os.path.join(USER_PROFILE, ".kube"),
            os.path.join(USER_PROFILE, ".gnupg"),
        ],
        "filename_keywords": [
            "id_rsa", "id_dsa", "id_ecdsa", "id_ed25519",
            "token", "secret", "password", "passwd", "credential",
            "private_key", "privatekey", "api_key", "apikey",
            "access_key", "auth_key",
        ],
        "extensions": [
            ".pem", ".key", ".ppk", ".p12", ".pfx",
            ".cer", ".crt", ".keystore",
        ],
        "content_keywords": [
            "password", "passwd", "secret", "api_key",
            "access_key", "token", "private_key",
            "BEGIN RSA PRIVATE KEY", "BEGIN OPENSSH PRIVATE KEY",
        ],
    },

    # ── 个人文档 ─────────────────────────────
    "document": {
        "label": "个人文档",
        "icon": "📄",
        "risk": "medium",
        "color": "#faad14",
        "priority_paths": [
            os.path.join(USER_PROFILE, "Desktop"),
            os.path.join(USER_PROFILE, "Documents"),
            os.path.join(USER_PROFILE, "Downloads"),
        ],
        "filename_keywords": [
            "简历", "resume", "cv", "身份证", "护照",
            "合同", "contract", "offer", "薪资", "工资",
            "银行", "bank", "保险", "个人", "私人",
            "日记", "diary", "笔记", "note",
        ],
        "extensions": [
            ".docx", ".doc", ".pdf", ".xlsx", ".xls",
            ".pptx", ".ppt", ".txt", ".md", ".rtf",
            ".odt", ".ods", ".odp", ".wps",
        ],
        "content_keywords": [],
    },

    # ── 个人媒体 ─────────────────────────────
    "media": {
        "label": "个人媒体",
        "icon": "🖼️",
        "risk": "low",
        "color": "#52c41a",
        "priority_paths": [
            os.path.join(USER_PROFILE, "Pictures"),
            os.path.join(USER_PROFILE, "Videos"),
            os.path.join(USER_PROFILE, "Music"),
        ],
        "filename_keywords": [],
        "extensions": [
            ".jpg", ".jpeg", ".png", ".gif", ".bmp",
            ".webp", ".tiff", ".ico", ".svg", ".heic",
            ".mp4", ".mov", ".avi", ".mkv", ".wmv",
            ".flv", ".rmvb", ".m4v",
            ".mp3", ".flac", ".wav", ".aac", ".m4a",
            ".ogg", ".wma",
        ],
        "content_keywords": [],
    },

    # ── 开发配置 ─────────────────────────────
    "devconfig": {
        "label": "开发配置文件",
        "icon": "💻",
        "risk": "high",
        "color": "#ff4d4f",
        "priority_paths": [
            os.path.join(USER_PROFILE, ".ssh"),
            os.path.join(USER_PROFILE, ".config"),
        ],
        "filename_keywords": [],
        "extensions": [],
        "exact_filenames": [
            ".env", ".env.local", ".env.production",
            ".env.development", ".env.test",
            ".netrc", ".gitconfig", ".npmrc", ".pypirc",
        ],
        "content_keywords": [
            "password", "secret", "api_key",
            "token", "access_key", "private",
        ],
    },

    # ── 自建目录 ─────────────────────────────
    "user_dir": {
        "label": "自建目录",
        "icon": "📁",
        "risk": "medium",
        "color": "#1890ff",
        "priority_paths": [],
        "filename_keywords": [],
        "extensions": [],
        "content_keywords": [],
    },
}

# ─────────────────────────────────────────
# 预览 & 内容扫描限制
# ─────────────────────────────────────────
MAX_PREVIEW_SIZE           = 50  * 1024
MAX_CONTENT_SCAN_SIZE      = 100 * 1024
MAX_IMAGE_PREVIEW_SIZE     = 10  * 1024 * 1024

TEXT_PREVIEW_EXTENSIONS = [
    ".txt", ".md", ".log", ".json", ".xml", ".yaml", ".yml",
    ".ini", ".cfg", ".conf", ".config", ".toml",
    ".env", ".sh", ".bat", ".ps1", ".py", ".js", ".ts",
    ".html", ".css", ".sql", ".csv",
    ".key", ".pem", ".ppk", ".gitconfig", ".npmrc",
    ".netrc", ".pypirc",
]

IMAGE_PREVIEW_EXTENSIONS = [
    ".jpg", ".jpeg", ".png", ".gif", ".bmp",
    ".webp", ".ico", ".heic",
]

VIDEO_PREVIEW_EXTENSIONS = [
    ".mp4", ".mov", ".avi", ".mkv", ".wmv",
    ".flv", ".rmvb", ".m4v",
]

# 应用缓存目录识别
KNOWN_CACHE_DIRS = {
    "cache": "缓存",
    "caches": "缓存",
    "temp": "临时文件",
    "tmp": "临时文件",
    "crashpad": "崩溃报告",
    "crash reports": "崩溃报告",
    "logs": "日志文件",
    "log": "日志文件",
    "gpu cache": "GPU缓存",
    "code cache": "代码缓存",
    "shader cache": "着色器缓存",
    "cachestorage": "缓存存储",
    "service worker": "Service Worker缓存",
    # 视频编辑相关缓存
    "autosave": "自动保存",
    "auto-save": "自动保存",
    "render cache": "渲染缓存",
    "rendercache": "渲染缓存",
    "media cache": "媒体缓存",
    "mediacache": "媒体缓存",
    "preview cache": "预览缓存",
    "previewcache": "预览缓存",
    "proxy files": "代理文件",
    "proxyfiles": "代理文件",
    "thumbnails": "缩略图缓存",
    "thumbnail": "缩略图缓存",
    # 剪映相关
    "draft": "草稿",
    "drafts": "草稿",
    "project": "工程文件",
    "projects": "工程文件",
    # 更多缓存目录
    "backup": "备份",
    "backups": "备份",
    "temp": "临时文件",
    "temps": "临时文件",
    "trash": "回收站",
    "recycle": "回收站",
    "trashbin": "回收站",
    ".trash": "回收站",
    # 浏览器缓存
    "browser cache": "浏览器缓存",
    "browsercache": "浏览器缓存",
    "chromecache": "Chrome缓存",
    # 开发工具缓存
    "build cache": "构建缓存",
    "buildcache": "构建缓存",
    "compilercache": "编译器缓存",
    "download": "下载",
    "downloads": "下载",
    # 缩略图和预览
    "preview": "预览",
    "previews": "预览",
    "thumbnail cache": "缩略图缓存",
    # 编辑器相关
    "workspace": "工作区缓存",
    "workspaces": "工作区缓存",
    # 数据相关
    "data cache": "数据缓存",
    "datacache": "数据缓存",
    "user data": "用户数据",
    "userdata": "用户数据",
    # 安装和更新
    "update": "更新缓存",
    "updates": "更新缓存",
    "install": "安装缓存",
    "installs": "安装缓存",
}