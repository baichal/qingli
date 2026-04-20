#!/usr/bin/env python3
"""
智能分类器文件内容学习测试脚本
测试智能分类器是否能够根据文件内信息自动学习判断
"""

import os
import time
from core.intelligent_classifier import intelligent_classifier


def create_test_files():
    """创建测试文件"""
    test_files = {
        # 个人文件 - 包含个人信息
        "personal_info.txt": """姓名：张三
邮箱：zhangsan@example.com
电话：13812345678
身份证：110101199001011234
地址：北京市朝阳区

这是我的个人信息，请勿泄露。
""",
        
        # 个人文件 - 包含个人笔记
        "personal_note.txt": """# 个人笔记

今天去了公园，拍了很多照片。
明天要去面试，准备一下简历。

家庭计划：下个月去旅行。
""",
        
        # 系统文件 - 包含系统相关内容
        "system_config.txt": r"""# Windows System Configuration

[System]
OSVersion=10.0.19041
BuildNumber=19041

[Registry]
Key=HKLM\SOFTWARE\Microsoft\Windows

[Services]
Service=W32Time
""",
        
        # 软件文件 - 包含软件相关内容
        "software_log.txt": r"""# Node.js Application Log

[AppData]
Path=C:\Users\User\AppData\Roaming\node_modules

[Cache]
Size=1024MB

[Build]
Version=1.0.0
"""
    }
    
    # 创建测试文件
    for filename, content in test_files.items():
        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"创建测试文件: {filename}")
    
    return list(test_files.keys())


def test_content_learning():
    """测试文件内容学习能力"""
    print("=== 智能分类器文件内容学习测试 ===")
    print()
    
    # 创建测试文件
    test_files = create_test_files()
    print()
    
    # 测试初始分类
    print("1. 初始分类测试:")
    initial_results = {}
    for filename in test_files:
        try:
            # 获取文件状态信息
            stat = os.stat(filename)
            stat_info = {
                "size": stat.st_size,
                "mtime_ts": int(stat.st_mtime)
            }
            
            result = intelligent_classifier.classify_file(filename, stat_info)
            initial_results[filename] = result
            print(f"  {filename}:")
            print(f"    分类: {result['category']}, 置信度: {result['confidence']:.2f}")
            print(f"    理由: {result['reason']}")
        except Exception as e:
            print(f"  {filename}: 错误 - {str(e)}")
    print()
    
    # 提供反馈，让智能分类器学习
    print("2. 提供学习反馈:")
    feedback_map = {
        "personal_info.txt": True,  # 个人文件
        "personal_note.txt": True,   # 个人文件
        "system_config.txt": False,  # 系统文件
        "software_log.txt": False    # 软件文件
    }
    
    for filename, is_personal in feedback_map.items():
        try:
            intelligent_classifier.learn_from_feedback(filename, is_personal, 1.0)
            print(f"  学习: {filename} {'个人文件' if is_personal else '非个人文件'}")
        except Exception as e:
            print(f"  学习失败: {filename} - {str(e)}")
    print()
    
    # 测试学习后的分类
    print("3. 学习后的分类测试:")
    learned_results = {}
    for filename in test_files:
        try:
            # 获取文件状态信息
            stat = os.stat(filename)
            stat_info = {
                "size": stat.st_size,
                "mtime_ts": int(stat.st_mtime)
            }
            
            result = intelligent_classifier.classify_file(filename, stat_info)
            learned_results[filename] = result
            print(f"  {filename}:")
            print(f"    分类: {result['category']}, 置信度: {result['confidence']:.2f}")
            print(f"    理由: {result['reason']}")
        except Exception as e:
            print(f"  {filename}: 错误 - {str(e)}")
    print()
    
    # 分析学习效果
    print("4. 学习效果分析:")
    for filename in test_files:
        initial = initial_results.get(filename, {})
        learned = learned_results.get(filename, {})
        
        if initial and learned:
            initial_conf = initial.get("confidence", 0)
            learned_conf = learned.get("confidence", 0)
            conf_diff = learned_conf - initial_conf
            
            print(f"  {filename}:")
            print(f"    初始置信度: {initial_conf:.2f}")
            print(f"    学习后置信度: {learned_conf:.2f}")
            print(f"    置信度变化: {conf_diff:+.2f}")
            print(f"    初始分类: {initial.get('category', 'unknown')}")
            print(f"    学习后分类: {learned.get('category', 'unknown')}")
    print()
    
    # 显示学习统计
    stats = intelligent_classifier.get_learning_stats()
    print("5. 学习统计:")
    print(f"  总学习次数: {stats['total_learning']}")
    print(f"  学习的扩展名: {stats['extensions_learned']}")
    print(f"  学习的目录模式: {stats['dir_patterns_learned']}")
    print(f"  学习的文件名模式: {stats['filename_patterns_learned']}")
    print()
    
    # 清理测试文件
    print("6. 清理测试文件:")
    for filename in test_files:
        if os.path.exists(filename):
            os.remove(filename)
            print(f"  删除: {filename}")
    print()
    
    print("=== 测试完成 ===")


def main():
    """主测试函数"""
    # 重置学习数据，确保测试结果不受之前学习的影响
    intelligent_classifier.reset_learning()
    print("已重置学习数据")
    print()
    
    # 运行测试
    test_content_learning()


if __name__ == "__main__":
    main()
