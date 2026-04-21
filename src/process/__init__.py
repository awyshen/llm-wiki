"""
处理模块

负责处理收集到的文档，包括文档解析、知识提取、Wiki页面生成等。

模块结构:
- document_processor.py: 文档处理器
- knowledge_processor.py: 知识处理器
- llm_client.py: LLM客户端
- entity_extractor.py: 实体提取器
- knowledge_graph_builder.py: 知识图谱构建器
"""

from .knowledge_processor import KnowledgeProcessor
from .document_processor import DocumentProcessor

__all__ = ["KnowledgeProcessor", "DocumentProcessor"]
