"""
搜索功能测试

测试混合搜索机制的功能和性能。
"""

import unittest
import time
from src.search.advanced_search import AdvancedSearch


class TestAdvancedSearch(unittest.TestCase):
    """测试高级搜索功能"""

    def setUp(self):
        """设置测试环境"""
        self.searcher = AdvancedSearch()

    def test_search_basic(self):
        """测试基本搜索功能"""
        # 测试关键词搜索
        results = self.searcher.search("test")
        self.assertIsInstance(results, list)
        
        # 测试不同搜索类型
        results_keyword = self.searcher._keyword_search("test")
        self.assertIsInstance(results_keyword, list)
        
        if self.searcher.vector_store:
            results_semantic = self.searcher._semantic_search("test")
            self.assertIsInstance(results_semantic, list)

    def test_hybrid_search(self):
        """测试混合搜索功能"""
        # 生成测试数据
        keyword_results = [
            {"id": "1", "title": "Test Page 1", "score": 0.8, "search_type": "keyword"},
            {"id": "2", "title": "Another Page", "score": 0.5, "search_type": "keyword"}
        ]
        
        semantic_results = [
            {"id": "1", "title": "Test Page 1", "score": 0.9, "search_type": "semantic"},
            {"id": "3", "title": "Semantic Match", "score": 0.7, "search_type": "semantic"}
        ]
        
        # 测试混合搜索
        hybrid_results = self.searcher._hybrid_search(keyword_results, semantic_results, 0.5)
        self.assertIsInstance(hybrid_results, list)
        self.assertEqual(len(hybrid_results), 3)  # 去重后应该有3个结果
        
        # 检查得分计算
        for result in hybrid_results:
            if result["id"] == "1":
                # 混合得分应该在0.8和0.9之间
                self.assertGreater(result["score"], 0.8)
                self.assertLess(result["score"], 0.9)

    def test_calculate_keyword_score(self):
        """测试关键词得分计算"""
        # 创建模拟对象
        class MockItem:
            def __init__(self, title, content):
                self.title = title
                self.content = content
        
        # 测试完全匹配
        item1 = MockItem("test", "content")
        score1 = self.searcher._calculate_keyword_score(item1, "test")
        self.assertEqual(score1, 1.0)
        
        # 测试标题匹配
        item2 = MockItem("test page", "content")
        score2 = self.searcher._calculate_keyword_score(item2, "test")
        self.assertGreater(score2, 0.5)
        
        # 测试内容匹配
        item3 = MockItem("page", "this is a test content")
        score3 = self.searcher._calculate_keyword_score(item3, "test")
        self.assertGreater(score3, 0.2)
        self.assertLess(score3, 0.4)
        
        # 测试无匹配
        item4 = MockItem("page", "content")
        score4 = self.searcher._calculate_keyword_score(item4, "test")
        self.assertEqual(score4, 0.0)

    def test_search_performance(self):
        """测试搜索性能"""
        # 测试关键词搜索性能
        start_time = time.time()
        results_keyword = self.searcher._keyword_search("test")
        keyword_time = time.time() - start_time
        print(f"关键词搜索时间: {keyword_time:.4f}秒")
        
        # 测试语义搜索性能（如果向量存储可用）
        if self.searcher.vector_store:
            start_time = time.time()
            results_semantic = self.searcher._semantic_search("test")
            semantic_time = time.time() - start_time
            print(f"语义搜索时间: {semantic_time:.4f}秒")
            
            # 测试混合搜索性能
            start_time = time.time()
            results_hybrid = self.searcher.search("test")
            hybrid_time = time.time() - start_time
            print(f"混合搜索时间: {hybrid_time:.4f}秒")
            
            # 确保搜索时间在合理范围内
            self.assertLess(hybrid_time, 5.0)  # 混合搜索时间应小于5秒
        else:
            # 如果向量存储不可用，只测试关键词搜索
            start_time = time.time()
            results_hybrid = self.searcher.search("test")
            hybrid_time = time.time() - start_time
            print(f"混合搜索时间（仅关键词）: {hybrid_time:.4f}秒")
            self.assertLess(hybrid_time, 2.0)  # 仅关键词搜索时间应小于2秒

    def test_search_results_order(self):
        """测试搜索结果排序"""
        results = self.searcher.search("test")
        
        # 检查结果是否按得分降序排序
        if results:
            scores = [result.get("score", 0) for result in results]
            for i in range(len(scores) - 1):
                self.assertGreaterEqual(scores[i], scores[i + 1])

    def test_search_with_different_weights(self):
        """测试不同权重的混合搜索"""
        # 测试纯关键词搜索
        results_keyword = self.searcher.search("test", hybrid_weight=0.0)
        self.assertIsInstance(results_keyword, list)
        
        # 测试纯语义搜索（如果向量存储可用）
        if self.searcher.vector_store:
            results_semantic = self.searcher.search("test", hybrid_weight=1.0)
            self.assertIsInstance(results_semantic, list)


if __name__ == "__main__":
    unittest.main()
