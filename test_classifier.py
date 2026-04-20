#!/usr/bin/env python3
"""测试文件分类器功能"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.file_classifier import file_classifier
from core.rules import should_exclude_path

def test_system_files():
    """测试系统文件识别"""
    print("=== 系统文件识别测试 ===")
    test_paths = [
        r"C:\Windows\System32\ntdll.dll",
        r"C:\Windows\System32\kernel32.dll",
        r"C:\Windows\System32\explorer.exe",
        r"C:\Windows\System32\drivers\etc\hosts",
        r"C:\Program Files\Common Files\system.dll",
        r"C:\pagefile.sys",
    ]
    
    for path in test_paths:
        is_sys = file_classifier.is_system_file(path)
        excluded = should_exclude_path(path)
        print(f"{path:60} -> system:{is_sys}, excluded:{excluded}")

def test_personal_files():
    """测试个人文件识别"""
    print("\n=== 个人文件识别测试 ===")
    test_paths = [
        r"C:\Users\Test\Desktop\简历.docx",
        r"C:\Users\Test\Documents\工作笔记.txt",
        r"C:\Users\Test\Pictures\IMG_1234.jpg",
        r"C:\Users\Test\Downloads\视频.mp4",
        r"C:\Users\Test\Music\歌曲.mp3",
        r"D:\备份\个人照片.zip",
    ]
    
    for path in test_paths:
        is_personal, reason = file_classifier.is_personal_file(path)
        classification = file_classifier.classify_file_type(path)
        print(f"{path:60} -> personal:{is_personal}, reason:{reason}")
        print(f"  category:{classification['category']}, reason:{classification['reason']}")

def test_software_files():
    """测试软件文件识别"""
    print("\n=== 软件文件识别测试 ===")
    test_paths = [
        r"C:\Users\Test\AppData\Roaming\Microsoft\Windows\Start Menu\Programs",
        r"C:\Users\Test\AppData\Local\Google\Chrome\User Data\Default\Cache",
        r"C:\Users\Test\AppData\Roaming\Tencent\QQ\Misc",
        r"C:\Users\Test\AppData\Local\Temp\test.tmp",
        r"C:\node_modules\some_package\index.js",
    ]
    
    for path in test_paths:
        classification = file_classifier.classify_file_type(path)
        print(f"{path:60} -> category:{classification['category']}, reason:{classification['reason']}")

def test_exclude_paths():
    """测试路径排除"""
    print("\n=== 路径排除测试 ===")
    test_paths = [
        r"C:\Windows",
        r"C:\Program Files",
        r"C:\ProgramData",
        r"C:\$Recycle.Bin",
        r"C:\Users\Test\AppData\Local",
        r"C:\Users\Test\AppData\Roaming",
        r"C:\Users\Test\Desktop",  # 这个不应该被排除
    ]
    
    for path in test_paths:
        excluded = should_exclude_path(path)
        is_sys = file_classifier.is_system_file(path)
        print(f"{path:60} -> excluded:{excluded}, is_system:{is_sys}")

if __name__ == "__main__":
    print("文件分类器测试")
    print("=" * 70)
    
    test_system_files()
    test_personal_files()
    test_software_files()
    test_exclude_paths()
    
    print("\n" + "=" * 70)
    print("测试完成")
