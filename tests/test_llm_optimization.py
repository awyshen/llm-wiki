"""
LLM客户端优化测试
"""

import time
import random
from src.process.llm_client import LLMClient
from src.core.config import get_config


def test_batch_processing():
    """
    测试批处理功能
    """
    print("\n=== 测试批处理功能 ===")
    llm_client = LLMClient()
    
    # 创建多个请求
    start_time = time.time()
    results = []
    
    # 同时发起多个请求
    for i in range(10):
        title = f"测试页面{i}"
        content = f"这是测试内容{i}，用于测试批处理功能。" * 10
        result = llm_client.generate_wiki_page(title, content, use_batch=True)
        results.append(result)
    
    end_time = time.time()
    print(f"批处理10个请求耗时: {end_time - start_time:.2f}秒")
    print(f"成功处理 {len(results)} 个请求")


def test_cache_functionality():
    """
    测试缓存功能
    """
    print("\n=== 测试缓存功能 ===")
    llm_client = LLMClient()
    
    title = "缓存测试页面"
    content = "这是用于测试缓存功能的内容。" * 10
    
    # 第一次请求（应该不使用缓存）
    start_time = time.time()
    result1 = llm_client.generate_wiki_page(title, content, use_batch=False)
    end_time1 = time.time()
    print(f"第一次请求耗时: {end_time1 - start_time:.2f}秒")
    
    # 第二次请求（应该使用缓存）
    start_time = time.time()
    result2 = llm_client.generate_wiki_page(title, content, use_batch=False)
    end_time2 = time.time()
    print(f"第二次请求耗时: {end_time2 - start_time:.2f}秒")
    
    # 验证结果是否相同
    print(f"两次结果是否相同: {result1['title'] == result2['title'] and result1['summary'] == result2['summary']}")


def test_error_handling():
    """
    测试错误处理和重试机制
    """
    print("\n=== 测试错误处理和重试机制 ===")
    llm_client = LLMClient()
    
    # 创建一个测试请求
    title = "错误处理测试"
    content = "这是用于测试错误处理和重试机制的内容。" * 10
    
    try:
        # 这里我们不修改配置，让它使用模拟结果
        result = llm_client.generate_wiki_page(title, content, use_batch=False)
        print("错误处理测试成功，返回了结果")
        print(f"结果标题: {result['title']}")
    except Exception as e:
        print(f"错误处理测试失败: {e}")


def test_performance_improvement():
    """
    测试性能提升
    """
    print("\n=== 测试性能提升 ===")
    llm_client = LLMClient()
    
    # 测试数据
    test_data = [
        (f"测试页面{i}", f"这是测试内容{i}，用于测试性能。" * 10)
        for i in range(5)
    ]
    
    # 测试不使用批处理和缓存
    print("\n测试不使用批处理和缓存:")
    start_time = time.time()
    for title, content in test_data:
        llm_client.generate_wiki_page(title, content, use_batch=False)
    end_time = time.time()
    print(f"耗时: {end_time - start_time:.2f}秒")
    
    # 测试使用批处理和缓存
    print("\n测试使用批处理和缓存:")
    start_time = time.time()
    for title, content in test_data:
        llm_client.generate_wiki_page(title, content, use_batch=True)
    end_time = time.time()
    print(f"耗时: {end_time - start_time:.2f}秒")
    
    # 再次测试使用缓存
    print("\n测试使用缓存:")
    start_time = time.time()
    for title, content in test_data:
        llm_client.generate_wiki_page(title, content, use_batch=True)
    end_time = time.time()
    print(f"耗时: {end_time - start_time:.2f}秒")


if __name__ == "__main__":
    print("开始测试LLM客户端优化效果...")
    
    # 运行所有测试
    test_batch_processing()
    test_cache_functionality()
    test_error_handling()
    test_performance_improvement()
    
    print("\n测试完成！")
