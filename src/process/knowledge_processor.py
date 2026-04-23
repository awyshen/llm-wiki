"""
知识处理器

协调文档处理流程，调用LLM进行知识提取和Wiki页面生成。
"""

import json
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
import time

from ..core.config import Config, get_config
from ..core.logger import get_logger
from ..core.exceptions import ProcessingError
from ..core.performance_monitor import monitor_performance, performance_monitor
from ..storage.database import get_db_manager
from ..storage.models import Document, WikiPage, Entity, Tag, ProcessingStatus
from ..storage.wiki_storage import WikiStorage, WikiPageData
from ..storage.vector.factory import get_vector_store
from .llm_client import LLMClient, get_llm_client
from .knowledge_graph_builder import get_knowledge_graph_builder

logger = get_logger(__name__)


class KnowledgeProcessor:
    """知识处理器"""

    def __init__(
        self, config: Optional[Config] = None, llm_client: Optional[LLMClient] = None
    ):
        self.config = config or get_config()
        self.llm = llm_client or get_llm_client()
        self.db = get_db_manager()
        self.wiki_storage = WikiStorage(config)
        self.vector_store = get_vector_store()
        self.knowledge_graph_builder = get_knowledge_graph_builder()
        self.max_workers = min(
            10, self.config.performance.get("max_concurrent_requests", 10)
        )

    @monitor_performance("process_pending_documents")
    def process_pending_documents(self) -> Dict[str, int]:
        """
        处理所有待处理的文档

        Returns:
            处理统计信息
        """
        # 获取待处理的文档ID
        with self.db.get_session() as session:
            pending_docs = (
                session.query(Document)
                .filter(
                    Document.processing_status.in_(
                        [ProcessingStatus.PENDING.value, ProcessingStatus.FAILED.value]
                    )
                )
                .all()
            )
            document_ids = [doc.id for doc in pending_docs]

        stats = {"success": 0, "failed": 0, "total": len(document_ids), "time_taken": 0}

        if not document_ids:
            logger.info("没有待处理的文档")
            return stats

        start_time = time.time()

        # 批量更新文档状态为处理中
        with self.db.get_session() as session:
            for doc_id in document_ids:
                doc = session.query(Document).filter(Document.id == doc_id).first()
                if doc:
                    doc.processing_status = ProcessingStatus.PROCESSING.value
                    doc.processing_attempts += 1
            session.commit()

        # 并行处理文档

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有文档处理任务
            future_to_doc = {
                executor.submit(self._process_document_wrapper, doc_id): doc_id
                for doc_id in document_ids
            }

            # 收集处理结果
            for future in concurrent.futures.as_completed(future_to_doc):
                doc_id = future_to_doc[future]
                try:
                    result = future.result()
                    if result:
                        stats["success"] += 1
                    else:
                        stats["failed"] += 1
                except Exception as e:
                    logger.error(f"处理文档失败 {doc_id}: {e}")
                    stats["failed"] += 1

        stats["time_taken"] = time.time() - start_time
        logger.info(f"批量处理完成: {stats}")
        return stats

    def _process_document_wrapper(self, document_id: str) -> bool:
        """
        文档处理包装器，用于并行处理

        Args:
            document_id: 文档ID

        Returns:
            是否处理成功
        """
        try:
            return self.process_document(document_id)
        except Exception as e:
            logger.error(f"并行处理文档失败 {document_id}: {e}")
            # 更新文档状态为失败
            with self.db.get_session() as session:
                document = (
                    session.query(Document).filter(Document.id == document_id).first()
                )
                if document:
                    document.processing_status = ProcessingStatus.FAILED.value
                    session.commit()
            return False

    @monitor_performance("process_document")
    def process_document(self, document_id: str) -> bool:
        """
        处理单个文档

        Args:
            document_id: 文档ID

        Returns:
            是否处理成功
        """
        try:
            # 获取文档信息
            document, content, title = self._get_document_info(document_id)
            if not document:
                return False

            # 生成Wiki页面数据
            wiki_data = self.llm.generate_wiki_page(title, content)
            page_data = self._create_wiki_page_data(
                wiki_data, title, content, document_id
            )

            # 保存Wiki页面
            file_path = self.wiki_storage.save_page(page_data, page_type="article")

            # 更新索引
            self.wiki_storage.update_index()

            # 添加操作日志
            log_details = f"处理文档: {title}\n文件路径: {file_path}\n分类: {page_data.category}\n标签: {', '.join(page_data.tags)}"
            self.wiki_storage.add_to_log("文档处理", log_details)

            # 更新数据库
            wiki_page_id = self._update_database(document_id, page_data, file_path)

            # 构建知识图谱
            if wiki_page_id:
                self._build_knowledge_graph(document_id, wiki_page_id, content, page_data.content)

            # 将文档内容添加到向量存储
            try:
                # 准备文档内容和元数据
                documents = [content]
                ids = [document_id]
                metadatas = [{
                    "document_id": document_id,
                    "wiki_page_id": wiki_page_id,
                    "title": title,
                    "category": page_data.category,
                    "tags": page_data.tags,
                    "content": content
                }]
                
                # 添加到向量存储
                self.vector_store.add(documents=documents, ids=ids, metadatas=metadatas)
                logger.info(f"文档内容已添加到向量存储: {title}")
            except Exception as e:
                logger.error(f"将文档内容添加到向量存储失败: {e}")

            logger.info(f"文档处理成功: {title}")
            return True
        except Exception as e:
            logger.error(f"处理文档失败 {document_id}: {e}")
            self._mark_document_failed(document_id)
            return False

    def _get_document_info(self, document_id: str) -> tuple:
        """
        获取文档信息

        Args:
            document_id: 文档ID

        Returns:
            (document, content, title) 元组
        """
        with self.db.get_session() as session:
            document = (
                session.query(Document).filter(Document.id == document_id).first()
            )

            if not document:
                logger.error(f"文档不存在: {document_id}")
                return None, None, None

            # 提取文本内容和标题
            content = document.extracted_text or ""
            if not content:
                logger.warning(f"文档内容为空: {document_id}")
                content = ""

            title = document.title or document.filename
            return document, content, title

    def _create_wiki_page_data(
        self, wiki_data: dict, title: str, content: str, document_id: str
    ) -> WikiPageData:
        """
        创建Wiki页面数据

        Args:
            wiki_data: LLM生成的Wiki数据
            title: 文档标题
            content: 文档内容
            document_id: 文档ID

        Returns:
            WikiPageData对象
        """
        # 确保content是字符串，如果是字典则转换为JSON字符串
        wiki_content = wiki_data.get("content", content)
        if isinstance(wiki_content, dict):
            wiki_content = json.dumps(wiki_content, ensure_ascii=False)
        
        return WikiPageData(
            title=wiki_data.get("title", title),
            content=wiki_content,
            summary=wiki_data.get("summary", ""),
            category=wiki_data.get("category", "未分类"),
            tags=wiki_data.get("tags", []),
            metadata={
                "source_document_id": document_id,
                "related_topics": wiki_data.get("related_topics", []),
            },
        )

    def _update_database(
        self, document_id: str, page_data: WikiPageData, file_path: str
    ) -> Optional[str]:
        """
        更新数据库

        Args:
            document_id: 文档ID
            page_data: Wiki页面数据
            file_path: Wiki页面文件路径

        Returns:
            创建的Wiki页面ID，如果失败则返回None
        """
        with self.db.get_session() as session:
            document = (
                session.query(Document).filter(Document.id == document_id).first()
            )

            if not document:
                logger.error(f"文档不存在: {document_id}")
                return None

            # 创建WikiPage记录
            # 确保content是字符串，如果是字典则转换为JSON字符串
            content_str = page_data.content
            if isinstance(content_str, dict):
                content_str = json.dumps(content_str, ensure_ascii=False)
            
            wiki_page = WikiPage(
                title=page_data.title,
                slug=self.wiki_storage._slugify(page_data.title),
                content=content_str,
                summary=page_data.summary,
                file_path=file_path,
                category=page_data.category,
                page_metadata=json.dumps(page_data.metadata, ensure_ascii=False) if page_data.metadata else "{}",
            )
            session.add(wiki_page)

            # 更新文档状态
            document.processing_status = ProcessingStatus.COMPLETED.value
            document.processed_at = datetime.utcnow()
            document.wiki_page_id = wiki_page.id

            # 批量处理标签
            for tag_name in page_data.tags:
                tag = session.query(Tag).filter(Tag.name == tag_name).first()
                if not tag:
                    tag = Tag(name=tag_name)
                    session.add(tag)
                wiki_page.tags.append(tag)

            session.commit()
            return wiki_page.id

    def _mark_document_failed(self, document_id: str):
        """
        标记文档处理失败

        Args:
            document_id: 文档ID
        """
        with self.db.get_session() as session:
            document = (
                session.query(Document).filter(Document.id == document_id).first()
            )
            if document:
                document.processing_status = ProcessingStatus.FAILED.value
                session.commit()

    def _build_knowledge_graph(self, document_id: str, wiki_page_id: str, document_content: str, wiki_content: str):
        """
        构建知识图谱

        Args:
            document_id: 文档ID
            wiki_page_id: Wiki页面ID
            document_content: 文档内容
            wiki_content: Wiki页面内容
        """
        try:
            logger.info(f"为文档 {document_id} 构建知识图谱")
            
            # 清空之前的图谱数据，避免累积
            self.knowledge_graph_builder.clear()
            
            # 从文档构建知识图谱
            self.knowledge_graph_builder.build_from_text(document_content, document_id, "document")
            
            # 从Wiki页面构建知识图谱
            self.knowledge_graph_builder.build_from_text(wiki_content, wiki_page_id, "wiki_page")
            
            # 保存知识图谱到数据库
            save_result = self.knowledge_graph_builder.save_to_database()
            if save_result:
                logger.info(f"知识图谱保存到数据库成功")
            else:
                logger.error("知识图谱保存到数据库失败")
            
            # 保存知识图谱到文件
            import os
            data_dir = self.config.data_dir
            graph_file_path = os.path.join(data_dir, f"knowledge_graph_{document_id}.json")
            self.knowledge_graph_builder.save_to_file(graph_file_path)
            
            logger.info(f"知识图谱构建完成，保存到: {graph_file_path}")
        except Exception as e:
            logger.error(f"构建知识图谱失败: {e}")

    def process_documents(self, document_ids: List[str]) -> Dict[str, int]:
        """
        批量处理多个文档

        Args:
            document_ids: 文档ID列表

        Returns:
            处理统计信息
        """
        stats = {"success": 0, "failed": 0, "total": len(document_ids), "time_taken": 0}

        if not document_ids:
            logger.info("没有文档需要处理")
            return stats

        start_time = time.time()

        # 批量更新文档状态为处理中
        with self.db.get_session() as session:
            for doc_id in document_ids:
                doc = session.query(Document).filter(Document.id == doc_id).first()
                if doc:
                    doc.processing_status = ProcessingStatus.PROCESSING.value
                    doc.processing_attempts += 1
            session.commit()

        # 并行处理文档
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有文档处理任务
            future_to_doc = {
                executor.submit(self._process_document_wrapper, doc_id): doc_id
                for doc_id in document_ids
            }

            # 收集处理结果
            for future in concurrent.futures.as_completed(future_to_doc):
                doc_id = future_to_doc[future]
                try:
                    result = future.result()
                    if result:
                        stats["success"] += 1
                    else:
                        stats["failed"] += 1
                except Exception as e:
                    logger.error(f"处理文档失败 {doc_id}: {e}")
                    stats["failed"] += 1

        stats["time_taken"] = time.time() - start_time
        logger.info(f"批量处理完成: {stats}")
        return stats

    def get_processing_stats(self) -> Dict[str, int]:
        """
        获取处理统计信息

        Returns:
            处理统计信息
        """
        with self.db.get_session() as session:
            total = session.query(Document).count()
            pending = session.query(Document).filter(
                Document.processing_status == ProcessingStatus.PENDING.value
            ).count()
            processing = session.query(Document).filter(
                Document.processing_status == ProcessingStatus.PROCESSING.value
            ).count()
            completed = session.query(Document).filter(
                Document.processing_status == ProcessingStatus.COMPLETED.value
            ).count()
            failed = session.query(Document).filter(
                Document.processing_status == ProcessingStatus.FAILED.value
            ).count()
        
        return {
            "total": total,
            "pending": pending,
            "processing": processing,
            "completed": completed,
            "failed": failed
        }

    def run_health_check(self) -> Dict[str, Any]:
        """
        运行Wiki健康检查（Lint）

        Returns:
            健康检查结果
        """
        logger.info("开始运行Wiki健康检查...")
        
        # 检查Wiki健康状态
        wiki_health = self.wiki_storage.check_wiki_health()
        
        # 检查数据库状态
        db_status = self._check_database_health()
        
        # 检查知识图谱状态
        graph_status = self._check_graph_health()
        
        # 综合健康检查结果
        health_result = {
            "wiki": wiki_health,
            "database": db_status,
            "knowledge_graph": graph_status,
            "overall_status": "healthy" if not wiki_health["errors"] and not db_status["errors"] else "unhealthy"
        }
        
        # 添加健康检查日志
        log_details = f"健康检查结果:\n"
        log_details += f"Wiki状态: {health_result['wiki']}\n"
        log_details += f"数据库状态: {health_result['database']}\n"
        log_details += f"知识图谱状态: {health_result['knowledge_graph']}\n"
        log_details += f"整体状态: {health_result['overall_status']}"
        self.wiki_storage.add_to_log("健康检查", log_details)
        
        logger.info(f"健康检查完成: {health_result}")
        return health_result

    def _check_database_health(self) -> Dict[str, Any]:
        """
        检查数据库健康状态

        Returns:
            数据库健康状态
        """
        from sqlalchemy import text
        
        db_status = {
            "status": "healthy",
            "errors": [],
            "document_count": 0,
            "wiki_page_count": 0
        }
        
        try:
            with self.db.get_session() as session:
                # 检查数据库连接
                session.execute(text("SELECT 1"))
                
                # 统计文档数量
                db_status["document_count"] = session.query(Document).count()
                db_status["wiki_page_count"] = session.query(WikiPage).count()
                
        except Exception as e:
            db_status["status"] = "unhealthy"
            db_status["errors"].append(f"数据库连接失败: {str(e)}")
        
        return db_status

    def _check_graph_health(self) -> Dict[str, Any]:
        """
        检查知识图谱健康状态

        Returns:
            知识图谱健康状态
        """
        graph_status = {
            "status": "healthy",
            "errors": [],
            "entity_count": 0,
            "relation_count": 0
        }
        
        try:
            with self.db.get_session() as session:
                # 统计实体和关系数量
                graph_status["entity_count"] = session.query(Entity).count()
                # 注意：这里假设关系也存储在数据库中，需要根据实际模型调整
                # graph_status["relation_count"] = session.query(Relation).count()
                
        except Exception as e:
            graph_status["status"] = "unhealthy"
            graph_status["errors"].append(f"知识图谱检查失败: {str(e)}")
        
        return graph_status
