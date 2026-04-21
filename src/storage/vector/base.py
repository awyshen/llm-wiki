"""
向量存储基础接口
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple


class VectorStoreBase(ABC):
    """
    向量存储基础接口
    """

    @abstractmethod
    def add(
        self,
        documents: List[str],
        ids: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """
        添加文档到向量存储

        Args:
            documents: 文档内容列表
            ids: 文档ID列表
            metadatas: 文档元数据列表
        """
        pass

    @abstractmethod
    def search(
        self, query: str, top_k: int = 5, filter: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        """
        搜索相似文档

        Args:
            query: 搜索查询
            top_k: 返回结果数量
            filter: 过滤条件

        Returns:
            搜索结果列表，每个元素为(id, score, metadata)
        """
        pass

    @abstractmethod
    def delete(self, ids: List[str]) -> None:
        """
        从向量存储中删除文档

        Args:
            ids: 文档ID列表
        """
        pass

    @abstractmethod
    def update(
        self,
        ids: List[str],
        documents: Optional[List[str]] = None,
        metadatas: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """
        更新向量存储中的文档

        Args:
            ids: 文档ID列表
            documents: 文档内容列表（可选）
            metadatas: 文档元数据列表（可选）
        """
        pass

    @abstractmethod
    def get(self, ids: List[str]) -> List[Dict[str, Any]]:
        """
        获取文档信息

        Args:
            ids: 文档ID列表

        Returns:
            文档信息列表
        """
        pass

    @abstractmethod
    def clear(self) -> None:
        """
        清空向量存储
        """
        pass

    @abstractmethod
    def count(self) -> int:
        """
        获取向量存储中的文档数量

        Returns:
            文档数量
        """
        pass
