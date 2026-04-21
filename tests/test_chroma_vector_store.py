"""
Chroma向量存储测试

测试Chroma向量存储的功能，特别是优化函数。
"""

import unittest
from src.storage.vector.chroma import ChromaVectorStore


class TestChromaVectorStore(unittest.TestCase):
    """Chroma向量存储测试类"""

    def setUp(self):
        """设置测试环境"""
        self.vector_store = ChromaVectorStore()
        
        # 清空缓存，确保测试环境干净
        self.vector_store.search_cache.clear()

    def test_clear_related_search_cache(self):
        """测试清理相关搜索缓存"""
        # 添加一些测试缓存
        self.vector_store.search_cache["search:人工智能:5:None"] = [("doc1", 0.9, {})]
        self.vector_store.search_cache["search:机器学习:5:None"] = [("doc2", 0.8, {})]
        self.vector_store.search_cache["search:深度学习:5:None"] = [("doc3", 0.7, {})]
        
        # 清理与文档相关的缓存
        test_documents = ["人工智能是一种重要的技术"]
        self.vector_store._clear_related_search_cache(test_documents)
        
        # 验证缓存是否被正确清理
        self.assertNotIn("search:人工智能:5:None", self.vector_store.search_cache)
        self.assertIn("search:机器学习:5:None", self.vector_store.search_cache)
        self.assertIn("search:深度学习:5:None", self.vector_store.search_cache)

    def test_clear_related_search_cache_empty(self):
        """测试清理空文档列表的情况"""
        # 添加一些测试缓存
        self.vector_store.search_cache["search:人工智能:5:None"] = [("doc1", 0.9, {})]
        
        # 清理空文档列表
        self.vector_store._clear_related_search_cache([])
        
        # 验证缓存未被清理
        self.assertIn("search:人工智能:5:None", self.vector_store.search_cache)

    def test_clear_related_search_cache_by_ids(self):
        """测试根据文档ID清理相关搜索缓存"""
        # 添加一些测试缓存
        self.vector_store.search_cache["search:人工智能:5:None"] = [("doc1", 0.9, {}), ("doc2", 0.8, {})]
        self.vector_store.search_cache["search:机器学习:5:None"] = [("doc3", 0.7, {})]
        
        # 清理包含指定文档ID的缓存
        self.vector_store._clear_related_search_cache_by_ids(["doc1"])
        
        # 验证缓存是否被正确清理
        self.assertNotIn("search:人工智能:5:None", self.vector_store.search_cache)
        self.assertIn("search:机器学习:5:None", self.vector_store.search_cache)

    def test_clear_related_search_cache_by_ids_empty(self):
        """测试清理空ID列表的情况"""
        # 添加一些测试缓存
        self.vector_store.search_cache["search:人工智能:5:None"] = [("doc1", 0.9, {})]
        
        # 清理空ID列表
        self.vector_store._clear_related_search_cache_by_ids([])
        
        # 验证缓存未被清理
        self.assertIn("search:人工智能:5:None", self.vector_store.search_cache)

    def test_optimize(self):
        """测试优化向量存储"""
        # 添加一些测试缓存，超过最大缓存大小
        for i in range(600):
            self.vector_store.search_cache[f"search:test{i}:5:None"] = [(f"doc{i}", 0.9, {})]
        
        # 执行优化
        self.vector_store.optimize()
        
        # 验证缓存大小是否被优化
        self.assertLessEqual(len(self.vector_store.search_cache), 500)

    def test_optimize_cache(self):
        """测试优化缓存"""
        # 添加一些测试缓存，超过最大缓存大小
        for i in range(600):
            self.vector_store.search_cache[f"search:test{i}:5:None"] = [(f"doc{i}", 0.9, {})]
        
        # 执行缓存优化
        self.vector_store._optimize_cache()
        
        # 验证缓存大小是否被优化
        self.assertLessEqual(len(self.vector_store.search_cache), 500)


if __name__ == "__main__":
    unittest.main()
