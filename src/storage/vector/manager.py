"""
向量存储管理工具

提供向量存储的备份、恢复、优化等管理功能。
"""

import os
import shutil
import time
import datetime
import tarfile
from typing import Optional, List

from src.core.config import get_config
from src.core.logger import get_logger
from .chroma import ChromaVectorStore

logger = get_logger(__name__)


class VectorStoreManager:
    """
    向量存储管理类
    """

    def __init__(self):
        """
        初始化向量存储管理器
        """
        self.config = get_config()
        self.vector_store = ChromaVectorStore()
        self.backup_dir = os.path.join(self.config.data_dir, "vector_backups")
        os.makedirs(self.backup_dir, exist_ok=True)

    def backup(self, backup_name: Optional[str] = None) -> str:
        """
        备份向量存储

        Args:
            backup_name: 备份名称，默认为时间戳

        Returns:
            备份文件路径
        """
        try:
            # 生成备份文件名
            if not backup_name:
                timestamp = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                backup_name = f"vector_backup_{timestamp}"

            # 备份文件路径
            backup_path = os.path.join(self.backup_dir, f"{backup_name}.tar.gz")

            # 获取向量存储目录
            vector_db_path = self.vector_store.vector_db_path

            # 创建tar.gz文件
            with tarfile.open(backup_path, "w:gz") as tar:
                # 添加向量存储目录
                tar.add(vector_db_path, arcname=os.path.basename(vector_db_path))

            logger.info(f"向量存储备份成功: {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"备份向量存储失败: {e}")
            raise

    def restore(self, backup_path: str) -> bool:
        """
        恢复向量存储

        Args:
            backup_path: 备份文件路径

        Returns:
            是否恢复成功
        """
        try:
            # 检查备份文件是否存在
            if not os.path.exists(backup_path):
                logger.error(f"备份文件不存在: {backup_path}")
                return False

            # 获取向量存储目录
            vector_db_path = self.vector_store.vector_db_path

            # 备份当前向量存储（以防万一）
            temp_backup = os.path.join(self.backup_dir, f"temp_backup_{int(time.time())}")
            if os.path.exists(vector_db_path):
                shutil.copytree(vector_db_path, temp_backup)
                logger.info(f"创建临时备份: {temp_backup}")

            # 清空当前向量存储目录
            if os.path.exists(vector_db_path):
                shutil.rmtree(vector_db_path)
            os.makedirs(vector_db_path, exist_ok=True)

            # 解压备份文件
            with tarfile.open(backup_path, "r:gz") as tar:
                tar.extractall(path=os.path.dirname(vector_db_path))

            # 重新初始化向量存储
            self.vector_store = ChromaVectorStore()

            # 清理临时备份
            if os.path.exists(temp_backup):
                shutil.rmtree(temp_backup)

            logger.info(f"向量存储恢复成功: {backup_path}")
            return True
        except Exception as e:
            logger.error(f"恢复向量存储失败: {e}")
            # 尝试恢复临时备份
            if 'temp_backup' in locals() and os.path.exists(temp_backup):
                if os.path.exists(vector_db_path):
                    shutil.rmtree(vector_db_path)
                shutil.copytree(temp_backup, vector_db_path)
                logger.info(f"恢复临时备份: {temp_backup}")
            return False

    def list_backups(self) -> List[str]:
        """
        列出所有备份

        Returns:
            备份文件列表
        """
        try:
            backups = []
            for file in os.listdir(self.backup_dir):
                if file.endswith(".tar.gz"):
                    backup_path = os.path.join(self.backup_dir, file)
                    backups.append(backup_path)
            # 按修改时间排序，最新的在前
            backups.sort(key=os.path.getmtime, reverse=True)
            return backups
        except Exception as e:
            logger.error(f"列出备份失败: {e}")
            return []

    def optimize(self) -> bool:
        """
        优化向量存储

        Returns:
            是否优化成功
        """
        try:
            # 调用向量存储的优化方法
            self.vector_store.optimize()
            
            # 清理缓存
            self.vector_store.search_cache.clear()
            
            logger.info("向量存储优化成功")
            return True
        except Exception as e:
            logger.error(f"优化向量存储失败: {e}")
            return False

    def get_stats(self) -> dict:
        """
        获取向量存储统计信息

        Returns:
            统计信息
        """
        try:
            stats = {
                "document_count": self.vector_store.count(),
                "backup_count": len(self.list_backups()),
                "vector_db_path": self.vector_store.vector_db_path,
                "collection_name": self.vector_store.collection_name,
                "cache_size": len(self.vector_store.search_cache)
            }
            return stats
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {}

    def clean_old_backups(self, keep_days: int = 7) -> int:
        """
        清理旧备份

        Args:
            keep_days: 保留最近几天的备份

        Returns:
            清理的备份数量
        """
        try:
            backups = self.list_backups()
            cutoff_time = time.time() - (keep_days * 24 * 3600)
            deleted_count = 0

            for backup in backups:
                if os.path.getmtime(backup) < cutoff_time:
                    os.remove(backup)
                    deleted_count += 1
                    logger.info(f"删除旧备份: {backup}")

            logger.info(f"清理了 {deleted_count} 个旧备份")
            return deleted_count
        except Exception as e:
            logger.error(f"清理旧备份失败: {e}")
            return 0


# 全局向量存储管理器实例
vector_store_manager = VectorStoreManager()


def get_vector_store_manager() -> VectorStoreManager:
    """
    获取向量存储管理器实例

    Returns:
        向量存储管理器实例
    """
    return vector_store_manager
