"""
测试优化后的文档处理流程
"""

import time
import os
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.process.knowledge_processor import KnowledgeProcessor
from src.process.document_processor import DocumentProcessor
from src.core.performance_monitor import performance_monitor


def test_document_processor():
    """测试文档处理器"""
    print("测试文档处理器...")
    
    processor = DocumentProcessor()
    
    # 创建测试文档
    test_content = """这是一个测试文档，用于测试文档分块和提取算法。

这个文档包含多个段落，每个段落包含多个句子。

文档分块算法应该能够智能地将文档分成合理的块，保留段落和句子的完整性。

同时，提取算法应该能够高效地从不同格式的文件中提取文本内容。
"""
    
    # 测试分块功能
    start_time = time.time()
    chunks = processor.chunk_document(test_content)
    end_time = time.time()
    
    print(f"分块完成，耗时: {end_time - start_time:.4f}秒")
    print(f"生成的块数: {len(chunks)}")
    for i, chunk in enumerate(chunks):
        print(f"块 {i+1} 长度: {len(chunk)}")
    
    return chunks


def test_knowledge_processor():
    """测试知识处理器"""
    print("\n测试知识处理器...")
    
    processor = KnowledgeProcessor()
    
    # 测试批处理功能
    start_time = time.time()
    stats = processor.process_pending_documents()
    end_time = time.time()
    
    print(f"批处理完成，耗时: {end_time - start_time:.4f}秒")
    print(f"处理统计: {stats}")
    
    return stats


def test_performance_monitor():
    """测试性能监控"""
    print("\n测试性能监控...")
    
    # 运行一些操作来生成性能数据
    test_document_processor()
    test_knowledge_processor()
    
    # 打印性能摘要
    performance_monitor.log_summary()


if __name__ == "__main__":
    print("开始测试优化后的文档处理流程...")
    test_performance_monitor()
    print("测试完成！")
