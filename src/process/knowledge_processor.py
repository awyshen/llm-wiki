"""
知识处理器

协调文档处理流程，调用LLM进行知识提取和Wiki页面生成。
"""

from typing import Optional, Dict, Any, List
from datetime import datetime

from ..core.config import Config, get_config
from ..core.logger import get_logger
from ..core.exceptions import ProcessingError
from ..storage.database import get_db_manager
from ..storage.models import Document, WikiPage, Entity, Tag, ProcessingStatus
from ..storage.wiki_storage import WikiStorage, WikiPageData
from .llm_client import LLMClient, get_llm_client

logger = get_logger(__name__)


class KnowledgeProcessor:
    """知识处理器"""
    
    def __init__(
        self, 
        config: Optional[Config] = None,
        llm_client: Optional[LLMClient] = None
    ):
        self.config = config or get_config()
        self.llm = llm_client or get_llm_client()
        self.db = get_db_manager()
        self.wiki_storage = WikiStorage(config)
    
    def process_pending_documents(self) -> Dict[str, int]:
        """
        处理所有待处理的文档
        
        Returns:
            处理统计信息
        """
        # 获取待处理的文档
        with self.db.get_session() as session:
            pending_docs = session.query(Document).filter(
                Document.processing_status.in_([
                    ProcessingStatus.PENDING.value,
                    ProcessingStatus.FAILED.value
                ])
            ).all()
        
        stats = {"success": 0, "failed": 0, "total": len(pending_docs)}
        
        for doc in pending_docs:
            try:
                if self.process_document(doc.id):
                    stats["success"] += 1
                else:
                    stats["failed"] += 1
            except Exception as e:
                logger.error(f"处理文档失败 {doc.id}: {e}")
                stats["failed"] += 1
        
        logger.info(f"批量处理完成: {stats}")
        return stats
    
    def process_document(self, document_id: str) -> bool:
        """
        处理单个文档
        
        Args:
            document_id: 文档ID
        
        Returns:
            是否处理成功
        """
        # 获取文档
        with self.db.get_session() as session:
            document = session.query(Document).filter(
                Document.id == document_id
            ).first()
            
            if not document:
                logger.error(f"文档不存在: {document_id}")
                return False
            
            # 更新状态为处理中
            document.processing_status = ProcessingStatus.PROCESSING.value
            document.processing_attempts += 1
            session.commit()
        
        try:
            # 提取文本内容
            content = document.extracted_text or ""
            if not content:
                logger.warning(f"文档内容为空: {document_id}")
                content = ""
            
            # 生成标题
            title = document.title or document.filename
            
            # 使用LLM生成Wiki页面
            logger.info(f"正在处理文档: {title}")
            wiki_data = self.llm.generate_wiki_page(title, content)
            
            # 创建Wiki页面数据
            page_data = WikiPageData(
                title=wiki_data.get("title", title),
                content=wiki_data.get("content", content),
                summary=wiki_data.get("summary", ""),
                category=wiki_data.get("category", "未分类"),
                tags=wiki_data.get("tags", []),
                metadata={
                    "source_document_id": document_id,
                    "related_topics": wiki_data.get("related_topics", [])
                }
            )
            
            # 保存Wiki页面
            file_path = self.wiki_storage.save_page(page_data, page_type="article")
            
            # 更新数据库
            with self.db.get_session() as session:
                document = session.query(Document).filter(
                    Document.id == document_id
                ).first()
                
                # 创建WikiPage记录
                wiki_page = WikiPage(
                    title=page_data.title,
                    slug=self.wiki_storage._slugify(page_data.title),
                    content=page_data.content,
                    summary=page_data.summary,
                    file_path=file_path,
                    category=page_data.category,
                    page