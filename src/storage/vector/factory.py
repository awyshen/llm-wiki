"""
向量存储工厂

根据配置创建不同类型的向量存储实例。
"""

from typing import Optional

from .base import VectorStoreBase
from .chroma import ChromaVectorStore
from src.core.config import get_config
from src.core.logger import get_logger

logger = get_logger(__name__)


class VectorStoreFactory:
    """
    向量存储工厂类
    """

    @staticmethod
    def create_vector_store() -> Optional[VectorStoreBase]:
        """
        根据配置创建向量存储实例

        Returns:
            向量存储实例
        """
        config = get_config()

        if config.vector_store.type == "none":
            logger.info("向量数据库已禁用")
            return None

        vector_db_type = config.vector_store.type

        try:
            if vector_db_type == "chroma":
                logger.info("创建Chroma向量存储实例")
                return ChromaVectorStore()
            elif vector_db_type == "dashvector":
                logger.info("创建DashVector向量存储实例")
                # 这里可以实现DashVector的支持
                # return DashVectorStore()
                logger.warning("DashVector支持暂未实现，使用Chroma作为替代")
                return ChromaVectorStore()
            else:
                logger.warning(
                    f"不支持的向量数据库类型: {vector_db_type}，使用Chroma作为替代"
                )
                return ChromaVectorStore()
        except Exception as e:
            logger.error(f"创建向量存储实例失败: {e}")
            return None


# 全局向量存储实例
vector_store = VectorStoreFactory.create_vector_store()


def get_vector_store() -> Optional[VectorStoreBase]:
    """
    获取向量存储实例

    Returns:
        向量存储实例
    """
    return vector_store
