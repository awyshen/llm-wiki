"""
向量存储模块

提供向量存储和嵌入生成功能，支持缓存和性能优化。
"""

from .base import VectorStoreBase
from .chroma import ChromaVectorStore
from .embedding import EmbeddingService, get_embedding_service
from .factory import VectorStoreFactory, get_vector_store

__all__ = [
    "VectorStoreBase",
    "ChromaVectorStore",
    "EmbeddingService",
    "VectorStoreFactory",
    "get_embedding_service",
    "get_vector_store",
]
