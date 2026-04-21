"""
高级搜索测试

测试高级搜索功能，特别是 search_related_topics 函数。
"""

import unittest
from src.search.advanced_search import AdvancedSearch


class TestAdvancedSearch(unittest.TestCase):
    """高级搜索测试类"""

    def setUp(self):
        """设置测试环境"""
        self.advanced_search = AdvancedSearch()

    def test_search_related_topics(self):
        """测试搜索相关主题"""
        # 测试搜索相关主题
        topic = "人工智能"
        results = self.advanced_search.search_related_topics(topic)
        
        # 验证结果格式
        self.assertIsInstance(results, list)
        for result in results:
            self.assertIsInstance(result, dict)
            self.assertIn("id", result)
            self.assertIn("title", result)
            self.assertIn("score", result)
            self.assertIn("type", result)
        
        # 验证结果数量
        self.assertLessEqual(len(results), 10)

    def test_search_related_topics_empty(self):
        """测试搜索空主题"""
        # 测试搜索空主题
        topic = ""
        results = self.advanced_search.search_related_topics(topic)
        
        # 验证结果
        self.assertIsInstance(results, list)

    def test_search_related_topics_none(self):
        """测试搜索None主题"""
        # 测试搜索None主题
        topic = None
        results = self.advanced_search.search_related_topics(topic)
        
        # 验证结果
        self.assertIsInstance(results, list)


if __name__ == "__main__":
    unittest.main()
