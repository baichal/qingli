#!/usr/bin/env python3
"""
智能分类器非文本文件测试脚本
测试智能分类器是否能够正确处理非文本文件（如mp4）
"""

import os
import time
from core.intelligent_classifier import intelligent_classifier


def test_non_text_files():
    """测试非文本文件分类"""
    print("=== 智能分类器非文本文件测试 ===")
    print()
    
    # 测试文件列表
    test_files = [
        # 个人媒体文件
        ("C:\\Users\\User\\Pictures\\家庭照片.jpg", "personal"),
        ("C:\\Users\\User\\Videos\\旅行视频.mp4", "personal"),
        ("C:\\Users\\User\\Music\\个人音乐.mp3", "personal"),
        
        # 软件安装文件
        ("C:\\Users\\User\\Downloads\\setup.exe", "software"),
        ("C:\\Users\\User\\Downloads\\installer.msi", "software"),
        
        # 系统文件
        ("C:\\Windows\\System32\\kernel32.dll", "system"),
        ("C:\\Windows\\Boot\\BCD", "system"),
        
        # 压缩文件
        ("C:\\Users\\User\\Downloads\\archive.zip", "software"),
        ("C:\\Users\\User\\Documents\\个人资料.rar", "personal"),
    ]
    
    correct = 0
    total = len(test_files)
    
    start_time = time.time()
    
    for file_path, expected_category in test_files:
        try:
            # 模拟文件存在
            stat_info = {
                "size": 1024 * 1024,  # 1MB
                "mtime_ts": int(time.time() - 86400)  # 1天前
            }
            
            result = intelligent_classifier.classify_file(file_path, stat_info)
            category = result["category"]
            confidence = result["confidence"]
            reason = result["reason"]
            
            is_correct = category == expected_category
            if is_correct:
                correct += 1
            
            status = "✓" if is_correct else "✗"
            print(f"{status} {file_path}")
            print(f"  预期: {expected_category}, 实际: {category}, 置信度: {confidence:.2f}")
            print(f"  理由: {reason}")
            print()
            
        except Exception as e:
            print(f"✗ {file_path}")
            print(f"  错误: {str(e)}")
            print()
    
    end_time = time.time()
    elapsed_time = end_time - start_time
    
    accuracy = (correct / total) * 100
    print(f"=== 测试结果 ===")
    print(f"总测试文件: {total}")
    print(f"正确分类: {correct}")
    print(f"准确率: {accuracy:.2f}%")
    print(f"测试时间: {elapsed_time:.2f} 秒")
    print()
    
    return accuracy


def main():
    """主测试函数"""
    # 重置学习数据，确保测试结果不受之前学习的影响
    intelligent_classifier.reset_learning()
    print("已重置学习数据")
    print()
    
    # 运行测试
    accuracy = test_non_text_files()
    
    print("=== 测试完成 ===")
    print(f"非文本文件分类准确率: {accuracy:.2f}%")


if __name__ == "__main__":
    main()
