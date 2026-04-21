#!/usr/bin/env python3
"""
测试实体相关功能
"""

import sys
import os
import json
import requests

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.process.llm_entity_extractor import get_llm_entity_extractor


def test_entity_relations_extraction():
    """测试实体关系提取功能"""
    print("测试实体关系提取功能...")
    
    # 获取实体提取器
    extractor = get_llm_entity_extractor()
    
    # 测试文本
    test_text = "苹果公司在2023年发布了新款iPhone，由蒂姆·库克担任CEO。"
    
    # 先提取实体
    entities = extractor.extract_entities(test_text)
    print(f"提取的实体: {entities}")
    
    # 提取实体关系
    relations = extractor.extract_entity_relations(test_text, entities)
    print(f"提取的关系: {relations}")
    print("实体关系提取测试完成！")


def test_get_entities_api():
    """测试获取实体API"""
    print("\n测试获取实体API...")
    
    # 使用Flask的测试客户端来测试API端点
    from src.api.app import create_app
    
    # 创建测试应用
    app = create_app()
    client = app.test_client()
    
    # 测试不同的请求参数
    test_cases = [
        # 无参数
        {},
        # 带类型参数
        {"type": "PERSON"},
        # 带名称参数
        {"name": "测试"},
        # 带分页参数
        {"limit": "10", "offset": "0"},
        # 无效参数
        {"limit": "2000"},
    ]
    
    for i, params in enumerate(test_cases):
        print(f"\n测试用例 {i+1}: {params}")
        try:
            # 发送GET请求
            response = client.get("/api/entities", query_string=params)
            # 打印结果
            print(f"状态码: {response.status_code}")
            print(f"响应: {response.get_json()}")
        except Exception as e:
            print(f"错误: {e}")
    
    print("获取实体API测试完成！")


if __name__ == "__main__":
    test_entity_relations_extraction()
    test_get_entities_api()
    print("\n所有测试完成！")
