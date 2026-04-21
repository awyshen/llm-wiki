"""
存储模块

负责系统数据的存储和管理，包括数据库、Wiki文件、向量存储等。

模块结构:
- database.py: 数据库管理
- models.py: 数据模型
- wiki_storage.py: Wiki存储
- optimized_storage.py: 优化存储
- vector/: 向量存储
  - base.py: 基础接口
  - chroma.py: Chroma实现
  - embedding.py: 嵌入处理
  - factory.py: 工厂方法
"""

from .optimized_storage import OptimizedStorage

__all__ = ["OptimizedStorage"]
