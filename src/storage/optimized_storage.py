"""
优化存储管理

减少不必要的I/O操作，提高存储访问效率。
"""

from typing import Optional, Dict, Any, List
import os
import json
import pickle
import hashlib
from functools import lru_cache

from ..core.config import Config, get_config
from ..core.logger import get_logger

logger = get_logger(__name__)


class OptimizedStorage:
    """优化存储管理"""

    def __init__(self, config: Optional[Config] = None):
        self.config = config or get_config()
        self.data_dir = self.config.paths.get("data_dir", "./data")
        self.wiki_dir = self.config.paths.get("wiki_dir", "./data/wiki")
        self.cache_dir = os.path.join(self.data_dir, "cache")
        self.batch_size = 100  # 批量操作大小

        # 创建必要的目录
        for directory in [self.data_dir, self.wiki_dir, self.cache_dir]:
            os.makedirs(directory, exist_ok=True)

        # 批处理缓冲区
        self.batch_buffer = {}

    def write_file(self, file_path: str, content: str, use_cache: bool = True) -> bool:
        """
        写入文件，支持缓存

        Args:
            file_path: 文件路径
            content: 文件内容
            use_cache: 是否使用缓存

        Returns:
            是否写入成功
        """
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            # 检查缓存
            if use_cache:
                cache_key = self._generate_cache_key(file_path, content)
                cache_file = os.path.join(self.cache_dir, f"{cache_key}.bin")

                # 如果缓存存在且内容相同，跳过写入
                if os.path.exists(cache_file):
                    logger.debug(f"文件内容未变化，跳过写入: {file_path}")
                    return True

                # 写入文件
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)

                # 更新缓存
                with open(cache_file, "wb") as f:
                    pickle.dump(
                        {"content": content, "timestamp": os.path.getmtime(file_path)},
                        f,
                    )
            else:
                # 直接写入文件
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)

            return True
        except Exception as e:
            logger.error(f"写入文件失败 {file_path}: {e}")
            return False

    def read_file(self, file_path: str, use_cache: bool = True) -> Optional[str]:
        """
        读取文件，支持缓存

        Args:
            file_path: 文件路径
            use_cache: 是否使用缓存

        Returns:
            文件内容
        """
        try:
            if not os.path.exists(file_path):
                return None

            # 检查缓存
            if use_cache:
                cache_key = self._generate_cache_key(file_path)
                cache_file = os.path.join(self.cache_dir, f"{cache_key}.bin")

                # 检查缓存是否有效
                if os.path.exists(cache_file):
                    with open(cache_file, "rb") as f:
                        cached_data = pickle.load(f)

                    # 检查文件是否被修改
                    if os.path.getmtime(file_path) == cached_data.get("timestamp"):
                        logger.debug(f"从缓存中读取文件: {file_path}")
                        return cached_data.get("content")

            # 直接读取文件
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # 更新缓存
            if use_cache:
                cache_key = self._generate_cache_key(file_path, content)
                cache_file = os.path.join(self.cache_dir, f"{cache_key}.bin")
                with open(cache_file, "wb") as f:
                    pickle.dump(
                        {"content": content, "timestamp": os.path.getmtime(file_path)},
                        f,
                    )

            return content
        except Exception as e:
            logger.error(f"读取文件失败 {file_path}: {e}")
            return None

    def batch_write(self, files: Dict[str, str]) -> Dict[str, bool]:
        """
        批量写入文件

        Args:
            files: 文件路径到内容的映射

        Returns:
            每个文件的写入结果
        """
        results = {}

        for file_path, content in files.items():
            results[file_path] = self.write_file(file_path, content)

        return results

    def batch_read(self, file_paths: List[str]) -> Dict[str, Optional[str]]:
        """
        批量读取文件

        Args:
            file_paths: 文件路径列表

        Returns:
            每个文件的内容
        """
        results = {}

        for file_path in file_paths:
            results[file_path] = self.read_file(file_path)

        return results

    def add_to_batch(self, file_path: str, content: str) -> None:
        """
        添加到批处理缓冲区

        Args:
            file_path: 文件路径
            content: 文件内容
        """
        self.batch_buffer[file_path] = content

        # 如果缓冲区达到批量大小，执行批量写入
        if len(self.batch_buffer) >= self.batch_size:
            self.flush_batch()

    def flush_batch(self) -> Dict[str, bool]:
        """
        执行批处理写入

        Returns:
            每个文件的写入结果
        """
        if not self.batch_buffer:
            return {}

        results = self.batch_write(self.batch_buffer)
        self.batch_buffer.clear()
        return results

    def delete_file(self, file_path: str) -> bool:
        """
        删除文件

        Args:
            file_path: 文件路径

        Returns:
            是否删除成功
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)

                # 清理缓存
                cache_key = self._generate_cache_key(file_path)
                cache_file = os.path.join(self.cache_dir, f"{cache_key}.bin")
                if os.path.exists(cache_file):
                    os.remove(cache_file)

            return True
        except Exception as e:
            logger.error(f"删除文件失败 {file_path}: {e}")
            return False

    def _generate_cache_key(self, file_path: str, content: Optional[str] = None) -> str:
        """
        生成缓存键

        Args:
            file_path: 文件路径
            content: 文件内容（可选）

        Returns:
            缓存键
        """
        if content is not None:
            key = f"{file_path}:{content}"
        else:
            key = file_path
        return hashlib.md5(key.encode()).hexdigest()

    @lru_cache(maxsize=1000)
    def get_file_metadata(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        获取文件元数据（缓存版）

        Args:
            file_path: 文件路径

        Returns:
            文件元数据
        """
        try:
            if not os.path.exists(file_path):
                return None

            return {
                "size": os.path.getsize(file_path),
                "mtime": os.path.getmtime(file_path),
                "ctime": os.path.getctime(file_path),
            }
        except Exception as e:
            logger.error(f"获取文件元数据失败 {file_path}: {e}")
            return None

    def clear_cache(self) -> bool:
        """
        清理缓存

        Returns:
            是否清理成功
        """
        try:
            for file in os.listdir(self.cache_dir):
                file_path = os.path.join(self.cache_dir, file)
                if os.path.isfile(file_path):
                    os.remove(file_path)

            return True
        except Exception as e:
            logger.error(f"清理缓存失败: {e}")
            return False
