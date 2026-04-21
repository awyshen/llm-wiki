#!/usr/bin/env python3
"""
测试实体抽取功能
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.process.llm_entity_extractor import get_llm_entity_extractor
from src.process.llm_client import get_llm_client


def test_entity_extraction():
    """测试实体抽取功能"""
    print("测试实体抽取功能...")
    
    # 获取实体提取器
    extractor = get_llm_entity_extractor()
    
    # 测试文本
    test_text = "苹果公司在2023年发布了新款iPhone，由蒂姆·库克担任CEO。"
    
    # 提取实体
    entities = extractor.extract_entities(test_text)
    
    print(f"实体抽取结果: {entities}")
    print("实体抽取测试完成！")


def test_wiki_page_generation():
    """测试Wiki页面生成功能"""
    print("\n测试Wiki页面生成功能...")
    
    # 获取LLM客户端
    llm_client = get_llm_client()
    
    # 测试内容
    title = "测试页面"
    content = "这是一个测试页面，用于验证Wiki页面生成功能。"
    
    # 生成Wiki页面
    wiki_data = llm_client.generate_wiki_page(title, content, use_batch=False)
    
    print(f"Wiki页面生成结果: {wiki_data}")
    print("Wiki页面生成测试完成！")


def test_concurrent_tasks():
    """测试并发执行不同任务"""
    print("\n测试并发执行不同任务...")
    
    import threading
    
    # 定义实体抽取任务
    def run_entity_extraction():
        print("启动实体抽取任务...")
        extractor = get_llm_entity_extractor()
        test_text = "苹果公司在2023年发布了新款iPhone，由蒂姆·库克担任CEO。"
        entities = extractor.extract_entities(test_text)
        print(f"实体抽取任务完成: {entities}")
    
    # 定义Wiki页面生成任务
    def run_wiki_generation():
        print("启动Wiki页面生成任务...")
        llm_client = get_llm_client()
        title = "测试页面"
        content = "这是一个测试页面，用于验证Wiki页面生成功能。"
        wiki_data = llm_client.generate_wiki_page(title, content, use_batch=False)
        print(f"Wiki页面生成任务完成: {wiki_data}")
    
    # 创建并启动线程
    thread1 = threading.Thread(target=run_entity_extraction)
    thread2 = threading.Thread(target=run_wiki_generation)
    
    thread1.start()
    thread2.start()
    
    thread1.join()
    thread2.join()
    
    print("并发测试完成！")


if __name__ == "__main__":
    test_entity_extraction()
    test_wiki_page_generation()
    test_concurrent_tasks()
    print("\n所有测试完成！")
