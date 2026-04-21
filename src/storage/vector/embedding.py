"""
嵌入生成模块

提供文本嵌入生成功能，支持缓存机制减少重复计算。
"""

import os
import pickle
import hashlib
from typing import List, Optional
from functools import lru_cache

from sentence_transformers import SentenceTransformer

from src.core.config import get_config
from src.core.logger import get_logger

logger = get_logger(__name__)


class EmbeddingService:
    """
    嵌入生成服务
    """

    def __init__(self):
        config = get_config()
        self.model_name = config.vector_store.embedding_model
        self.cache_dir = os.path.join(config.data_dir, "embedding_cache")
        self.batch_size = 32  # 批处理大小

        # 创建缓存目录
        os.makedirs(self.cache_dir, exist_ok=True)

        # 加载嵌入模型
        self.model = self._load_model()

        # 内存缓存
        self.memory_cache = {}
        self.max_cache_size = 1000  # 内存缓存大小

    def _load_model(self):
        """
        加载嵌入模型

        Returns:
            嵌入模型实例
        """
        try:
            logger.info(f"加载嵌入模型: {self.model_name}")
            model = SentenceTransformer(self.model_name)
            logger.info("嵌入模型加载成功")
            return model
        except Exception as e:
            logger.error(f"加载嵌入模型失败: {e}")
            # 直接创建简单嵌入服务，避免继续尝试加载其他模型
            logger.info("创建简单嵌入服务...")
            self._create_simple_embedding()
            return self.model

    def _generate_cache_key(self, text: str) -> str:
        """
        生成缓存键

        Args:
            text: 文本内容

        Returns:
            缓存键
        """
        key = f"{self.model_name}:{text}"
        return hashlib.md5(key.encode()).hexdigest()

    def _get_from_cache(self, text: str) -> Optional[List[float]]:
        """
        从缓存获取嵌入

        Args:
            text: 文本内容

        Returns:
            嵌入向量或None
        """
        # 先检查内存缓存
        cache_key = self._generate_cache_key(text)
        if cache_key in self.memory_cache:
            logger.debug("从内存缓存获取嵌入")
            return self.memory_cache[cache_key]

        # 检查磁盘缓存
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.bin")
        if os.path.exists(cache_file):
            try:
                with open(cache_file, "rb") as f:
                    embedding = pickle.load(f)
                logger.debug("从磁盘缓存获取嵌入")

                # 更新内存缓存
                self._update_memory_cache(cache_key, embedding)
                return embedding
            except Exception as e:
                logger.error(f"读取缓存失败: {e}")
                return None

        return None

    def _update_memory_cache(self, key: str, value: List[float]) -> None:
        """
        更新内存缓存

        Args:
            key: 缓存键
            value: 嵌入向量
        """
        if len(self.memory_cache) >= self.max_cache_size:
            # 移除最早的项
            oldest_key = next(iter(self.memory_cache))
            del self.memory_cache[oldest_key]
        self.memory_cache[key] = value

    def _save_to_cache(self, text: str, embedding: List[float]) -> None:
        """
        保存嵌入到缓存

        Args:
            text: 文本内容
            embedding: 嵌入向量
        """
        cache_key = self._generate_cache_key(text)
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.bin")

        try:
            with open(cache_file, "wb") as f:
                pickle.dump(embedding, f)

            # 更新内存缓存
            self._update_memory_cache(cache_key, embedding)
        except Exception as e:
            logger.error(f"保存缓存失败: {e}")

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        生成文本嵌入

        Args:
            texts: 文本列表

        Returns:
            嵌入向量列表
        """
        embeddings = []
        texts_to_process = []
        indices_to_process = []

        # 检查缓存
        for i, text in enumerate(texts):
            cached_embedding = self._get_from_cache(text)
            if cached_embedding:
                embeddings.append(cached_embedding)
            else:
                texts_to_process.append(text)
                indices_to_process.append(i)

        # 处理未缓存的文本
        if texts_to_process:
            logger.debug(f"处理 {len(texts_to_process)} 个未缓存的文本")

            # 批处理生成嵌入
            batch_embeddings = []
            for i in range(0, len(texts_to_process), self.batch_size):
                batch = texts_to_process[i : i + self.batch_size]
                batch_result = self.model.encode(batch, show_progress_bar=False)
                batch_embeddings.extend(batch_result.tolist())

            # 填充结果并缓存
            for i, idx in enumerate(indices_to_process):
                embedding = batch_embeddings[i]
                embeddings.insert(idx, embedding)
                self._save_to_cache(texts_to_process[i], embedding)

        return embeddings

    def generate_embedding(self, text: str) -> List[float]:
        """
        生成单个文本的嵌入

        Args:
            text: 文本内容

        Returns:
            嵌入向量
        """
        return self.generate_embeddings([text])[0]

    def clear_cache(self) -> bool:
        """
        清理缓存

        Returns:
            是否清理成功
        """
        try:
            # 清空内存缓存
            self.memory_cache.clear()

            # 清空磁盘缓存
            for file in os.listdir(self.cache_dir):
                file_path = os.path.join(self.cache_dir, file)
                if os.path.isfile(file_path):
                    os.remove(file_path)

            logger.info("嵌入缓存清理成功")
            return True
        except Exception as e:
            logger.error(f"清理缓存失败: {e}")
            return False

    def get_cache_size(self) -> int:
        """
        获取缓存大小

        Returns:
            缓存文件数量
        """
        try:
            return len(
                [
                    f
                    for f in os.listdir(self.cache_dir)
                    if os.path.isfile(os.path.join(self.cache_dir, f))
                ]
            )
        except Exception:
            return 0

    def _create_simple_embedding(self):
        """
        创建简单的嵌入服务

        当无法加载SentenceTransformer模型时使用
        """

        class SimpleEmbedding:
            """
            简单的嵌入实现
            """

            def encode(self, texts, show_progress_bar=False):
                """
                简单的文本编码

                Args:
                    texts: 文本列表
                    show_progress_bar: 是否显示进度条

                Returns:
                    嵌入向量
                """
                import numpy as np

                embeddings = []
                for text in texts:
                    # 简单的基于字符频率的嵌入
                    char_counts = {}
                    for char in text:
                        char_counts[char] = char_counts.get(char, 0) + 1
                    # 生成固定长度的向量
                    vector = np.zeros(384)  # 与all-MiniLM-L6-v2相同的维度
                    for i, (char, count) in enumerate(char_counts.items()):
                        if i < 384:
                            vector[i] = count / len(text)
                    embeddings.append(vector)
                return np.array(embeddings)

        self.model = SimpleEmbedding()


# 全局嵌入服务实例
embedding_service = EmbeddingService()


def get_embedding_service() -> EmbeddingService:
    """
    获取嵌入服务实例

    Returns:
        嵌入服务实例
    """
    return embedding_service
