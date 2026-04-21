#!/usr/bin/env python3
"""
知识图谱模块单元测试
"""

import unittest
import json
import os
from src.process.knowledge_graph_builder import KnowledgeGraphBuilder, get_knowledge_graph_builder
from src.interface.graph_visualization import KnowledgeGraphVisualization
from src.collect.file_collector import FileCollector
from src.process.knowledge_processor import KnowledgeProcessor


class TestKnowledgeGraph(unittest.TestCase):
    """知识图谱模块测试"""

    def setUp(self):
        """设置测试环境"""
        self.graph_builder = get_knowledge_graph_builder()
        self.graph_builder.clear()  # 清空图谱数据
        self.visualizer = KnowledgeGraphVisualization()
        self.file_collector = FileCollector()
        self.processor = KnowledgeProcessor()

    def test_graph_builder_initialization(self):
        """测试知识图谱构建器初始化"""
        self.assertIsInstance(self.graph_builder, KnowledgeGraphBuilder)
        self.assertEqual(len(self.graph_builder.get_entities()), 0)
        self.assertEqual(len(self.graph_builder.get_relations()), 0)

    def test_graph_visualization_initialization(self):
        """测试知识图谱可视化初始化"""
        self.assertIsInstance(self.visualizer, KnowledgeGraphVisualization)

    def test_build_from_text(self):
        """测试从文本构建知识图谱"""
        test_text = "张三是李四的朋友，李四是王五的同事。"
        self.graph_builder.clear()
        result = self.graph_builder.build_from_text(test_text, "test_doc", "document")
        
        # 验证图谱构建结果
        self.assertIn("entities", result)
        self.assertIn("relations", result)
        self.assertGreater(len(result["entities"]), 0)
        self.assertGreater(len(result["relations"]), 0)

    def test_save_to_database(self):
        """测试保存知识图谱到数据库"""
        test_text = "张三是李四的朋友，李四是王五的同事。"
        self.graph_builder.clear()
        self.graph_builder.build_from_text(test_text, "test_doc", "document")
        result = self.graph_builder.save_to_database()
        self.assertTrue(result)

    def test_get_graph_data(self):
        """测试获取图谱数据"""
        graph_data = self.visualizer.get_graph_data(max_nodes=10)
        self.assertIn("nodes", graph_data)
        self.assertIn("links", graph_data)
        self.assertIn("stats", graph_data)
        self.assertIn("timestamp", graph_data)

    def test_get_graph_statistics(self):
        """测试获取图谱统计信息"""
        stats = self.visualizer.get_graph_statistics()
        self.assertIn("nodes", stats)
        self.assertIn("links", stats)
        self.assertIn("entity_types", stats)

    def test_export_graph(self):
        """测试导出图谱"""
        # 测试JSON格式导出
        json_data = self.visualizer.export_graph(format="json")
        self.assertIsInstance(json_data, dict)
        self.assertIn("nodes", json_data)
        self.assertIn("links", json_data)
        
        # 测试CSV格式导出
        csv_data = self.visualizer.export_graph(format="csv")
        self.assertIsInstance(csv_data, str)
        self.assertIn("type,id,label,type,size", csv_data)

    def test_import_graph(self):
        """测试导入图谱"""
        # 先导出一个图谱
        export_data = self.visualizer.export_graph(format="json")
        # 然后导入
        import_result = self.visualizer.import_graph(export_data)
        self.assertIn("success", import_result)
        self.assertTrue(import_result["success"])

    def test_find_path(self):
        """测试路径查找"""
        # 这里需要有实际的实体ID才能测试
        # 暂时跳过，需要在有实际数据时测试
        pass

    def test_get_related_entities(self):
        """测试获取相关实体"""
        # 这里需要有实际的实体ID才能测试
        # 暂时跳过，需要在有实际数据时测试
        pass

    def test_file_collector_import(self):
        """测试文件收集器导入功能"""
        # 创建一个测试文件
        test_file_path = "/tmp/test_wiki.txt"
        with open(test_file_path, "w", encoding="utf-8") as f:
            f.write("测试文档内容：张三是李四的朋友，李四是王五的同事。")
        
        # 测试导入单个文件
        doc_id = self.file_collector.import_file(test_file_path)
        self.assertIsInstance(doc_id, str)
        
        # 测试批量导入
        import_result = self.file_collector.import_files([test_file_path])
        self.assertIn("success", import_result)
        self.assertIn("failed", import_result)
        
        # 清理测试文件
        os.remove(test_file_path)

    def test_knowledge_processor(self):
        """测试知识处理器"""
        # 获取处理统计信息
        stats = self.processor.get_processing_stats()
        self.assertIn("total", stats)
        self.assertIn("pending", stats)
        self.assertIn("processing", stats)
        self.assertIn("completed", stats)
        self.assertIn("failed", stats)


if __name__ == "__main__":
    unittest.main()
