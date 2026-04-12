"""
高级搜索模块

提供语义搜索、多条件搜索、模糊搜索等高级搜索功能，支持搜索结果排序和过滤。
"""

import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from ..core.config import get_config
from ..core.logger import get_logger
from ..storage.database import get_db_manager
from ..storage.models import Document, WikiPage, Entity, Tag
from ..storage.vector import get_vector_store

logger = get_logger(__name__)


@dataclass
class SearchResult:
    """搜索结果数据结构"""
    id: str
    title: str
    type: str  # document, wiki_page, entity
    content: str
    score: float
    metadata: Dict[str, Any]


class AdvancedSearch:
    """
    高级搜索类
    
    支持多种搜索模式：
    - 语义搜索：基于向量相似度计算
    - 全文搜索：基于数据库查询
    - 模糊搜索：支持拼音、首字母缩写匹配
    
    支持搜索结果排序：
    - 相关性：基于相似度分数
    - 时间：基于创建/更新时间
    - 热度：基于访问频次
    """
    
    def __init__(self):
        self.config = get_config()
        self.db = get_db_manager()
        self.vector_store = get_vector_store()
    
    def search(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        top_k: int = 20,
        include_semantic: bool = True,
        include_fuzzy: bool = True,
        sort_by: str = "relevance"
    ) -> List[SearchResult]:
        """
        执行高级搜索
        
        Args:
            query: 搜索关键词
            filters: 过滤条件字典，支持按分类、类型等筛选
            top_k: 返回结果数量限制
            include_semantic: 是否启用语义搜索
            include_fuzzy: 是否启用模糊搜索
            sort_by: 排序方式 (relevance, time, popularity)
        
        Returns:
            搜索结果列表，按指定方式排序
        """
        start_time = time.time()
        results = []
        
        # 1. 语义搜索（基于向量数据库）
        if include_semantic and self.config.search.enable_semantic_search:
            semantic_results = self._semantic_search(query, filters, top_k)
            results.extend(semantic_results)
            logger.debug(f"语义搜索完成，找到 {len(semantic_results)} 条结果")
        
        # 2. 全文搜索（基于数据库）
        full_text_results = self._full_text_search(query, filters, top_k)
        results.extend(full_text_results)
        logger.debug(f"全文搜索完成，找到 {len(full_text_results)} 条结果")
        
        # 3. 模糊搜索（支持拼音、首字母）
        if include_fuzzy and self.config.search.enable_fuzzy_search:
            fuzzy_results = self._fuzzy_search(query, filters, top_k)
            results.extend(fuzzy_results)
            logger.debug(f"模糊搜索完成，找到 {len(fuzzy_results)} 条结果")
        
        # 4. 去重处理
        unique_results = self._deduplicate_results(results)
        logger.debug(f"去重后剩余 {len(unique_results)} 条结果")
        
        # 5. 排序处理
        sorted_results = self._sort_results(unique_results, sort_by)
        
        # 6. 限制结果数量
        final_results = sorted_results[:top_k]
        
        logger.info(f"搜索完成，耗时: {time.time() - start_time:.3f}秒, 结果数: {len(final_results)}")
        
        return final_results
    
    def _semantic_search(self, query: str, filters: Dict[str, Any], top_k: int) -> List[SearchResult]:
        """
        语义搜索：基于向量相似度计算
        
        Args:
            query: 搜索查询
            filters: 过滤条件
            top_k: 返回数量
        
        Returns:
            搜索结果列表
        """
        try:
            vector_results = self.vector_store.search(query, top_k=top_k, filter=filters)
            
            results = []
            for doc_id, score, metadata in vector_results:
                results.append(SearchResult(
                    id=doc_id,
                    title=metadata.get('title', 'Unknown'),
                    type=metadata.get('type', 'document'),
                    content=metadata.get('content', '')[:200] + '...',
                    score=score,
                    metadata=metadata
                ))
            
            return results
        except Exception as e:
            logger.error(f"语义搜索失败: {e}")
            return []
    
    def _full_text_search(self, query: str, filters: Dict[str, Any], top_k: int) -> List[SearchResult]:
        """
        全文搜索：基于数据库LIKE查询
        
        Args:
            query: 搜索查询
            filters: 过滤条件
            top_k: 返回数量
        
        Returns:
            搜索结果列表
        """
        try:
            with self.db.get_session() as session:
                # 构建基础查询
                wiki_pages = session.query(WikiPage)
                
                # 应用过滤条件
                if filters:
                    if 'category' in filters:
                        wiki_pages = wiki_pages.filter(WikiPage.category == filters['category'])
                    if 'page_type' in filters:
                        wiki_pages = wiki_pages.filter(WikiPage.page_type == filters['page_type'])
                
                # 简单的全文搜索（SQLite LIKE查询）
                search_terms = query.split()
                for term in search_terms:
                    wiki_pages = wiki_pages.filter(
                        (WikiPage.title.ilike(f'%{term}%')) | 
                        (WikiPage.content.ilike(f'%{term}%'))
                    )
                
                pages = wiki_pages.limit(top_k).all()
                
                results = []
                for page in pages:
                    score = self._calculate_score(page, query)
                    results.append(SearchResult(
                        id=page.id,
                        title=page.title,
                        type='wiki_page',
                        content=page.content[:200] + '...',
                        score=score,
                        metadata={
                            'category': page.category,
                            'page_type': page.page_type,
                            'created_at': page.created_at.isoformat() if page.created_at else None,
                            'updated_at': page.updated_at.isoformat() if page.updated_at else None,
                            'view_count': page.view_count or 0
                        }
                    ))
                
                return results
        except Exception as e:
            logger.error(f"全文搜索失败: {e}")
            return []
    
    def _fuzzy_search(self, query: str, filters: Dict[str, Any], top_k: int) -> List[SearchResult]:
        """
        模糊搜索：支持拼音、首字母缩写匹配
        
        Args:
            query: 搜索查询
            filters: 过滤条件
            top_k: 返回数量
        
        Returns:
            搜索结果列表
        """
        try:
            import pypinyin
            
            def get_pinyin(text):
                """生成拼音和首字母"""
                try:
                    pinyin_list = pypinyin.lazy_pinyin(text, style=pypinyin.NORMAL)
                    pinyin = ''.join(pinyin_list)
                    first_letters = ''.join([p[0] for p in pinyin_list])
                    return pinyin, first_letters
                except Exception:
                    return text, text[0] if text else ''
            
            query_pinyin, query_first_letters = get_pinyin(query)
            
            with self.db.get_session() as session:
                wiki_pages = session.query(WikiPage)
                
                # 应用过滤条件
                if filters:
                    if 'category' in filters:
                        wiki_pages = wiki_pages.filter(WikiPage.category == filters['category'])
                
                pages = wiki_pages.limit(100).all()
                
                results = []
                for page in pages:
                    page_pinyin, page_first_letters = get_pinyin(page.title)
                    
                    # 检查匹配：拼音包含、首字母包含、或分词匹配
                    if (query_pinyin in page_pinyin or 
                        query_first_letters in page_first_letters or
                        any(q in page_pinyin for q in query.split())):
                        score = 0.7 + (len(query) / len(page.title)) * 0.3
                        results.append(SearchResult(
                            id=page.id,
                            title=page.title,
                            type='wiki_page',
                            content=page.content[:200] + '...',
                            score=score,
                            metadata={
                                'category': page.category,
                                'page_type': page.page_type
                            }
                        ))
                
                return results[:top_k]
                
        except ImportError:
            logger.warning("pypinyin未安装，跳过模糊搜索")
            return []
        except Exception as e:
            logger.error(f"模糊搜索失败: {e}")
            return []
    
    def _calculate_score(self, page: WikiPage, query: str) -> float:
        """
        计算搜索匹配分数
        
        Args:
            page: Wiki页面对象
            query: 搜索查询
        
        Returns:
            匹配分数 (0.0-1.0)
        """
        score = 0.0
        query_lower = query.lower()
        title_lower = page.title.lower()
        content_lower = page.content.lower()
        
        # 标题完全匹配权重最高
        if query_lower == title_lower:
            score = 1.0
        elif query_lower in title_lower:
            score += 0.5
            # 标题开头匹配额外加分
            if title_lower.startswith(query_lower):
                score += 0.2
        
        # 内容匹配权重次之
        if query_lower in content_lower:
            score += 0.2
        
        # 分词匹配加分
        for term in query.split():
            term_lower = term.lower()
            if term_lower in title_lower:
                score += 0.05
            if term_lower in content_lower:
                score += 0.03
        
        return min(score, 1.0)
    
    def _deduplicate_results(self, results: List[SearchResult]) -> List[SearchResult]:
        """
        去重搜索结果
        
        Args:
            results: 原始搜索结果列表
        
        Returns:
            去重后的搜索结果列表
        """
        seen = set()
        unique = []
        
        for result in results:
            key = f"{result.type}_{result.id}"
            if key not in seen:
                seen.add(key)
                unique.append(result)
        
        return unique
    
    def _sort_results(self, results: List[SearchResult], sort_by: str) -> List[SearchResult]:
        """
        排序搜索结果
        
        Args:
            results: 搜索结果列表
            sort_by: 排序方式
        
        Returns:
            排序后的搜索结果列表
        """
        if sort_by == "relevance":
            return sorted(results, key=lambda x: x.score, reverse=True)
        elif sort_by == "time":
            return sorted(results, key=lambda x: x.metadata.get('updated_at', ''), reverse=True)
        elif sort_by == "popularity":
            return sorted(results, key=lambda x: x.metadata.get('view_count', 0), reverse=True)
        else:
            return sorted(results, key=lambda x: x.score, reverse=True)
    
    def get_facets(self, query: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        获取搜索面（用于过滤统计）
        
        Args:
            query: 搜索查询
        
        Returns:
            搜索面统计信息，包含分类和页面类型
        """
        try:
            with self.db.get_session() as session:
                # 获取分类统计
                categories = session.query(WikiPage.category).distinct().all()
                category_facet = [
                    {"value": cat[0], "count": session.query(WikiPage).filter(
                        WikiPage.category == cat[0]
                    ).count()}
                    for cat in categories if cat[0]
                ]
                
                # 获取页面类型统计
                page_types = session.query(WikiPage.page_type).distinct().all()
                type_facet = [
                    {"value": pt[0], "count": session.query(WikiPage).filter(
                        WikiPage.page_type == pt[0]
                    ).count()}
                    for pt in page_types if pt[0]
                ]
                
                return {
                    "categories": category_facet,
                    "page_types": type_facet
                }
        except Exception as e:
            logger.error(f"获取搜索面失败: {e}")
            return {"categories": [], "page_types": []}
    
    def index_document(self, document_id: str, content: str, metadata: Dict[str, Any]):
        """
        将文档索引到向量存储
        
        Args:
            document_id: 文档ID
            content: 文档内容
            metadata: 文档元数据
        
        Returns:
            是否成功索引
        """
        try:
            self.vector_store.add(
                documents=[content],
                ids=[document_id],
                metadatas=[metadata]
            )
            return True
        except Exception as e:
            logger.error(f"索引文档失败: {e}")
            return False
    
    def remove_from_index(self, document_id: str):
        """
        从索引中移除文档
        
        Args:
            document_id: 文档ID
        
        Returns:
            是否成功移除
        """
        try:
            self.vector_store.delete([document_id])
            return True
        except Exception as e:
            logger.error(f"从索引移除文档失败: {