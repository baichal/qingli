#!/usr/bin/env python3
"""
智能分类器测试脚本
测试智能分类器的性能和准确性
"""

import os
import time
from core.intelligent_classifier import intelligent_classifier


def test_file_classification():
    """测试文件分类"""
    print("=== 智能分类器测试 ===")
    print()
    
    # 测试文件列表
    test_files = [
        # 个人文件
        ("C:\\Users\\User\\Desktop\\简历.pdf", "personal"),
        ("C:\\Users\\User\\Documents\\个人笔记.txt", "personal"),
        ("C:\\Users\\User\\Pictures\\家庭照片.jpg", "personal"),
        ("C:\\Users\\User\\Downloads\\电影.mp4", "personal"),
        
        # 系统文件
        ("C:\\Windows\\System32\\kernel32.dll", "system"),
        ("C:\\Program Files\\Windows Defender\\MsMpEng.exe", "system"),
        ("C:\\Windows\\Boot\\BCD", "system"),
        
        # 软件文件
        ("C:\\Users\\User\\AppData\\Local\\Google\\Chrome\\User Data\\Default\\History", "software"),
        ("C:\\Program Files\\Node.js\\node.exe", "software"),
        ("C:\\Users\\User\\Projects\\venv\\Scripts\\python.exe", "software"),
        
        # 不确定的文件
        ("C:\\Users\\User\\Documents\\report.docx", "personal"),
        ("C:\\Users\\User\\Desktop\\setup.exe", "software"),
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


def test_learning_capability():
    """测试学习能力"""
    print("=== 学习能力测试 ===")
    print()
    
    # 测试文件
    test_file = "C:\\Users\\User\\Documents\\project_report.pdf"
    
    # 初始分类
    print("1. 初始分类:")
    result1 = intelligent_classifier.classify_file(test_file)
    print(f"   分类: {result1['category']}, 置信度: {result1['confidence']:.2f}")
    print(f"   理由: {result1['reason']}")
    print()
    
    # 提供反馈
    print("2. 提供反馈 (标记为个人文件):")
    intelligent_classifier.learn_from_feedback(test_file, True, 1.0)
    print("   反馈已记录")
    print()
    
    # 再次分类
    print("3. 再次分类:")
    result2 = intelligent_classifier.classify_file(test_file)
    print(f"   分类: {result2['category']}, 置信度: {result2['confidence']:.2f}")
    print(f"   理由: {result2['reason']}")
    print()
    
    # 检查学习效果
    improvement = result2['confidence'] - result1['confidence']
    print(f"学习效果: 置信度提升 {improvement:.2f}")
    print()
    
    return improvement


def test_performance():
    """测试性能"""
    print("=== 性能测试 ===")
    print()
    
    # 生成测试文件路径
    test_files = []
    for i in range(100):
        test_files.append(f"C:\\Users\\User\\Documents\\file_{i}.txt")
    
    start_time = time.time()
    
    for file_path in test_files:
        intelligent_classifier.classify_file(file_path)
    
    end_time = time.time()
    elapsed_time = end_time - start_time
    files_per_second = len(test_files) / elapsed_time
    
    print(f"测试文件数: {len(test_files)}")
    print(f"总时间: {elapsed_time:.2f} 秒")
    print(f"处理速度: {files_per_second:.2f} 文件/秒")
    print()
    
    return files_per_second


def test_edge_cases():
    """测试边缘情况"""
    print("=== 边缘情况测试 ===")
    print()
    
    edge_cases = [
        ("", "空路径"),
        ("C:\\", "根目录"),
        ("C:\\Users\\User\\AppData\\Local\\Temp\\temp.txt", "临时文件"),
        ("C:\\Users\\User\\Desktop\\System32.exe", "混淆文件名"),
    ]
    
    for file_path, description in edge_cases:
        try:
            result = intelligent_classifier.classify_file(file_path)
            print(f"{description}: {file_path}")
            print(f"  分类: {result['category']}, 置信度: {result['confidence']:.2f}")
            print(f"  理由: {result['reason']}")
            print()
        except Exception as e:
            print(f"{description}: {file_path}")
            print(f"  错误: {str(e)}")
            print()


def main():
    """主测试函数"""
    print("智能分类器综合测试")
    print("=" * 50)
    print()
    
    # 测试分类准确性
    accuracy = test_file_classification()
    
    # 测试学习能力
    improvement = test_learning_capability()
    
    # 测试性能
    performance = test_performance()
    
    # 测试边缘情况
    test_edge_cases()
    
    # 显示学习统计
    stats = intelligent_classifier.get_learning_stats()
    print("=== 学习统计 ===")
    print(f"总学习次数: {stats['total_learning']}")
    print(f"学习的扩展名: {stats['extensions_learned']}")
    print(f"学习的目录模式: {stats['dir_patterns_learned']}")
    print(f"学习的文件名模式: {stats['filename_patterns_learned']}")
    print()
    
    print("=== 测试完成 ===")
    print(f"准确率: {accuracy:.2f}%")
    print(f"学习效果: 置信度提升 {improvement:.2f}")
    print(f"性能: {performance:.2f} 文件/秒")
    print()


if __name__ == "__main__":
    main()
