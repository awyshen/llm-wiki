"""
Chroma向量存储实现

基于Chroma DB的向量存储实现，支持缓存和性能优化。
"""

import os
from typing import List, Dict, Any, Optional, Tuple

import chromadb
from chromadb.config import Settings

from .base import VectorStoreBase
from .embedding import get_embedding_service
from src.core.config import get_config
from src.core.logger import get_logger

logger = get_logger(__name__)


class ChromaVectorStore(VectorStoreBase):
    """
    Chroma向量存储实现
    """

    def __init__(self):
        config = get_config()
        self.vector_db_path = config.vector_store.path
        self.collection_name = config.vector_store.collection_name
        self.chunk_size = config.processing.extraction.max_chunk_size
        self.chunk_overlap = config.processing.extraction.max_chunk_size * 0.2

        # 初始化Chroma客户端
        self.client = self._init_client()

        # 获取或创建集合
        self.collection = self._get_or_create_collection()

        # 获取嵌入服务
        self.embedding_service = get_embedding_service()

        # 搜索缓存
        self.search_cache = {}
        self.max_search_cache_size = 500  # 搜索缓存大小
        
        # 标记向量存储是否可用
        self.available = self.collection is not None

    def _init_client(self):
        """
        初始化Chroma客户端

        Returns:
            Chroma客户端实例
        """
        try:
            # 创建向量数据库目录
            os.makedirs(self.vector_db_path, exist_ok=True)

            # 初始化客户端（使用chromadb 1.5.7 API）
            client = chromadb.PersistentClient(
                path=self.vector_db_path,
                settings=Settings(
                    anonymized_telemetry=False
                )
            )
            logger.info("Chroma客户端初始化成功")
            return client
        except Exception as e:
            logger.error(f"初始化Chroma客户端失败: {e}")
            raise

    def _get_or_create_collection(self):
        """
        获取或创建集合

        Returns:
            Chroma集合实例或None
        """
        try:
            # 检查集合是否存在
            collections = self.client.list_collections()
            collection_names = [col.name for col in collections]

            if self.collection_name in collection_names:
                collection = self.client.get_collection(self.collection_name)
                logger.info(f"获取现有集合: {self.collection_name}")
            else:
                # 创建新集合（使用chromadb 1.5.7 API）
                collection = self.client.create_collection(
                    name=self.collection_name,
                    metadata={"hnsw:space": "cosine"},  # 使用余弦相似度
                    embedding_function=None  # 不使用默认嵌入函数，使用自定义嵌入服务
                )
                logger.info(f"创建新集合: {self.collection_name}")

            return collection
        except Exception as e:
            logger.error(f"获取或创建集合失败: {e}")
            # 不抛出异常，返回None，允许系统继续初始化
            return None

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
        if not self.available:
            logger.warning("向量存储不可用，跳过添加文档")
            return
            
        try:
            # 生成嵌入
            embeddings = self.embedding_service.generate_embeddings(documents)

            # 添加到集合
            self.collection.add(
                documents=documents,
                embeddings=embeddings,
                ids=ids,
                metadatas=metadatas if metadatas else None,
            )

            logger.debug(f"添加 {len(documents)} 个文档到向量存储")

            # 清理相关搜索缓存
            self._clear_related_search_cache(documents)
        except Exception as e:
            logger.error(f"添加文档到向量存储失败: {e}")
            # 不抛出异常，允许系统继续运行

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
        if not self.available:
            logger.warning("向量存储不可用，返回空搜索结果")
            return []
            
        try:
            # 生成缓存键
            cache_key = self._generate_search_cache_key(query, top_k, filter)

            # 检查缓存
            if cache_key in self.search_cache:
                logger.debug("从搜索缓存获取结果")
                return self.search_cache[cache_key]

            # 生成查询嵌入
            query_embedding = self.embedding_service.generate_embedding(query)

            # 执行搜索（使用chromadb 1.5.7 API）
            results = self.collection.query(
                query_embeddings=[query_embedding], 
                n_results=top_k, 
                where=filter
            )

            # 处理结果
            search_results = []
            for i in range(len(results["ids"][0])):
                doc_id = results["ids"][0][i]
                score = 1 - results["distances"][0][i]  # 转换为相似度分数
                metadata = (
                    results["metadatas"][0][i] if results["metadatas"][0][i] else {}
                )
                search_results.append((doc_id, score, metadata))

            # 更新搜索缓存
            self._update_search_cache(cache_key, search_results)

            return search_results
        except Exception as e:
            logger.error(f"搜索失败: {e}")
            return []

    async def search_async(
        self, query: str, top_k: int = 5, filter: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        """
        异步搜索相似文档

        Args:
            query: 搜索查询
            top_k: 返回结果数量
            filter: 过滤条件

        Returns:
            搜索结果列表，每个元素为(id, score, metadata)
        """
        import asyncio
        
        # 使用线程池执行同步搜索
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self.search, query, top_k, filter
        )

    def search_batch(
        self, queries: List[str], top_k: int = 5, filter: Optional[Dict[str, Any]] = None
    ) -> List[List[Tuple[str, float, Dict[str, Any]]]]:
        """
        批量搜索相似文档

        Args:
            queries: 搜索查询列表
            top_k: 返回结果数量
            filter: 过滤条件

        Returns:
            搜索结果列表，每个元素为(id, score, metadata)的列表
        """
        if not self.available:
            logger.warning("向量存储不可用，返回空搜索结果")
            return [[] for _ in queries]
            
        results = []
        
        # 批量生成嵌入
        query_embeddings = self.embedding_service.generate_embeddings(queries)
        
        # 批量执行搜索
        for i, query in enumerate(queries):
            # 检查缓存
            cache_key = self._generate_search_cache_key(query, top_k, filter)
            if cache_key in self.search_cache:
                results.append(self.search_cache[cache_key])
            else:
                try:
                    # 执行搜索
                    search_result = self.collection.query(
                        query_embeddings=[query_embeddings[i]], n_results=top_k, where=filter
                    )
                    
                    # 处理结果
                    search_results = []
                    for j in range(len(search_result["ids"][0])):
                        doc_id = search_result["ids"][0][j]
                        score = 1 - search_result["distances"][0][j]  # 转换为相似度分数
                        metadata = (
                            search_result["metadatas"][0][j] if search_result["metadatas"][0][j] else {}
                        )
                        search_results.append((doc_id, score, metadata))
                    
                    # 更新搜索缓存
                    self._update_search_cache(cache_key, search_results)
                    results.append(search_results)
                except Exception as e:
                    logger.error(f"搜索失败: {e}")
                    results.append([])
        
        return results

    def optimize(self) -> None:
        """
        优化向量存储
        """
        if not self.available:
            logger.warning("向量存储不可用，跳过优化操作")
            return
            
        try:
            # Chroma 1.5.7会自动处理索引优化
            # 这里可以添加一些额外的优化操作
            
            # 优化缓存
            self._optimize_cache()
            
            logger.info("向量存储优化完成")
        except Exception as e:
            logger.error(f"优化向量存储失败: {e}")

    def _optimize_cache(self) -> None:
        """
        优化缓存
        """
        # 清理过期缓存
        if len(self.search_cache) > self.max_search_cache_size:
            # 保留最近使用的缓存项
            # 这里简化处理，实际可以实现LRU缓存
            while len(self.search_cache) > self.max_search_cache_size:
                oldest_key = next(iter(self.search_cache))
                del self.search_cache[oldest_key]
        logger.debug(f"缓存优化完成，当前缓存大小: {len(self.search_cache)}")

    def delete(self, ids: List[str]) -> None:
        """
        从向量存储中删除文档

        Args:
            ids: 文档ID列表
        """
        if not self.available:
            logger.warning("向量存储不可用，跳过删除文档")
            return
            
        try:
            self.collection.delete(ids=ids)
            logger.debug(f"从向量存储中删除 {len(ids)} 个文档")

            # 清理相关搜索缓存
            self._clear_related_search_cache_by_ids(ids)
        except Exception as e:
            logger.error(f"删除文档失败: {e}")
            # 不抛出异常，允许系统继续运行

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
        if not self.available:
            logger.warning("向量存储不可用，跳过更新文档")
            return
            
        try:
            # 生成嵌入（如果提供了新文档）
            embeddings = None
            if documents:
                embeddings = self.embedding_service.generate_embeddings(documents)

            # 更新文档
            self.collection.update(
                ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas
            )

            logger.debug(f"更新 {len(ids)} 个文档")

            # 清理相关搜索缓存
            if documents:
                self._clear_related_search_cache(documents)
            self._clear_related_search_cache_by_ids(ids)
        except Exception as e:
            logger.error(f"更新文档失败: {e}")
            # 不抛出异常，允许系统继续运行

    def get(self, ids: List[str]) -> List[Dict[str, Any]]:
        """
        获取文档信息

        Args:
            ids: 文档ID列表

        Returns:
            文档信息列表
        """
        if not self.available:
            logger.warning("向量存储不可用，返回空文档列表")
            return []
            
        try:
            results = self.collection.get(ids=ids)

            documents = []
            for i, doc_id in enumerate(results["ids"]):
                doc_info = {
                    "id": doc_id,
                    "document": results["documents"][i],
                    "metadata": (
                        results["metadatas"][i] if results["metadatas"][i] else {}
                    ),
                }
                documents.append(doc_info)

            return documents
        except Exception as e:
            logger.error(f"获取文档失败: {e}")
            return []

    def clear(self) -> None:
        """
        清空向量存储
        """
        if not self.available:
            logger.warning("向量存储不可用，跳过清空操作")
            return
            
        try:
            # 删除并重建集合
            self.client.delete_collection(self.collection_name)
            self.collection = self._get_or_create_collection()

            # 清空搜索缓存
            self.search_cache.clear()

            logger.info("向量存储已清空")
        except Exception as e:
            logger.error(f"清空向量存储失败: {e}")
            # 不抛出异常，允许系统继续运行

    def count(self) -> int:
        """
        获取向量存储中的文档数量

        Returns:
            文档数量
        """
        if not self.available:
            logger.warning("向量存储不可用，返回0")
            return 0
            
        try:
            return self.collection.count()
        except Exception as e:
            logger.error(f"获取文档数量失败: {e}")
            return 0

    def _generate_search_cache_key(
        self, query: str, top_k: int, filter: Optional[Dict[str, Any]]
    ) -> str:
        """
        生成搜索缓存键

        Args:
            query: 搜索查询
            top_k: 返回结果数量
            filter: 过滤条件

        Returns:
            缓存键
        """
        filter_str = str(filter) if filter else "None"
        return f"search:{query}:{top_k}:{filter_str}"

    def _update_search_cache(
        self, key: str, results: List[Tuple[str, float, Dict[str, Any]]]
    ) -> None:
        """
        更新搜索缓存

        Args:
            key: 缓存键
            results: 搜索结果
        """
        if len(self.search_cache) >= self.max_search_cache_size:
            # 移除最早的项
            oldest_key = next(iter(self.search_cache))
            del self.search_cache[oldest_key]
        self.search_cache[key] = results

    def _clear_related_search_cache(self, documents: List[str]) -> None:
        """
        清理与文档相关的搜索缓存

        Args:
            documents: 文档内容列表
        """
        try:
            if not documents:
                return
            
            # 智能清理：只清理可能与文档相关的搜索缓存
            
            # 清理包含这些文档相关内容的缓存
            keys_to_remove = []
            for key in self.search_cache:
                # 缓存键格式：search:{query}:{top_k}:{filter}
                if key.startswith("search:"):
                    query_part = key.split(":")[1]
                    # 检查文档是否包含查询，或者查询是否包含在文档中
                    if any(query_part in doc or doc in query_part for doc in documents):
                        keys_to_remove.append(key)
            
            # 执行清理
            for key in keys_to_remove:
                del self.search_cache[key]
            
            logger.debug(f"清理了 {len(keys_to_remove)} 个相关搜索缓存")
        except Exception as e:
            logger.error(f"清理相关搜索缓存失败: {e}")
            # 出错时回退到清空所有缓存
            self.search_cache.clear()

    def _clear_related_search_cache_by_ids(self, ids: List[str]) -> None:
        """
        根据文档ID清理相关搜索缓存

        Args:
            ids: 文档ID列表
        """
        try:
            if not ids:
                return
            
            # 智能清理：只清理包含指定文档ID的搜索缓存
            keys_to_remove = []
            for key, results in self.search_cache.items():
                # 检查缓存结果是否包含指定的文档ID
                if any(result[0] in ids for result in results):
                    keys_to_remove.append(key)
            
            # 执行清理
            for key in keys_to_remove:
                del self.search_cache[key]
            
            logger.debug(f"清理了 {len(keys_to_remove)} 个包含指定文档ID的搜索缓存")
        except Exception as e:
            logger.error(f"根据文档ID清理相关搜索缓存失败: {e}")
            # 出错时回退到清空所有缓存
            self.search_cache.clear()