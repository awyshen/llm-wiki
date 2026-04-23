"""
高级搜索功能

支持全文搜索、语义搜索、实体关联查询等高级搜索功能。
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from ..core.config import get_config
from ..core.logger import get_logger
from ..storage.database import get_db_manager
from ..storage.models import WikiPage, Document
from ..storage.vector.chroma import ChromaVectorStore
from ..process.llm_entity_extractor import get_llm_entity_extractor

logger = get_logger(__name__)


class AdvancedSearch:
    """高级搜索类"""

    def __init__(self):
        self.config = get_config()
        self.db = get_db_manager()
        self.entity_extractor = get_llm_entity_extractor()
        
        # 初始化向量存储
        try:
            self.vector_store = ChromaVectorStore()
            logger.info("向量存储初始化成功")
        except Exception as e:
            logger.warning(f"向量存储初始化失败: {e}")
            self.vector_store = None

    def search(self, query: str, filters: Optional[Dict[str, Any]] = None, top_k: int = 20, hybrid_weight: float = 0.5, include_semantic: bool = True, include_fuzzy: bool = True, sort_by: str = "relevance") -> List[Dict[str, Any]]:
        """
        搜索知识库

        Args:
            query: 搜索关键词
            filters: 过滤条件
            top_k: 返回结果数量
            hybrid_weight: 混合搜索权重，0表示纯关键词搜索，1表示纯语义搜索
            include_semantic: 是否包含语义搜索
            include_fuzzy: 是否包含模糊搜索
            sort_by: 排序方式 (relevance, time, popularity)

        Returns:
            搜索结果列表
        """
        logger.info(f"搜索查询: {query}, 过滤条件: {filters}")

        # 提取查询中的实体
        query_entities = self.entity_extractor.extract_entities(query)
        logger.debug(f"从查询中提取到 {len(query_entities)} 个实体")

        # 关键词搜索结果
        keyword_results = self._keyword_search(query, top_k, filters)
        
        # 语义搜索结果
        semantic_results = []
        if self.vector_store and include_semantic:
            semantic_results = self._semantic_search(query, top_k)
        
        # 混合搜索结果
        hybrid_results = self._hybrid_search(keyword_results, semantic_results, hybrid_weight)

        # 基于实体匹配增强结果
        if query_entities:
            hybrid_results = self._enhance_results_with_entities(hybrid_results, query_entities)

        # 应用过滤条件
        if filters:
            hybrid_results = self._apply_filters(hybrid_results, filters)

        # 排序
        hybrid_results = self._sort_results(hybrid_results, sort_by)

        # 限制返回结果数量
        final_results = hybrid_results[:top_k]

        logger.info(f"搜索完成，找到 {len(final_results)} 个结果")
        return final_results

    def _keyword_search(self, query: str, top_k: int = 20, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        关键词搜索

        Args:
            query: 搜索关键词
            top_k: 返回结果数量
            filters: 过滤条件

        Returns:
            搜索结果列表
        """
        results = []

        with self.db.get_session() as session:
            # 搜索Wiki页面
            wiki_query = session.query(WikiPage).filter(
                WikiPage.title.contains(query) | WikiPage.content.contains(query)
            )
            
            # 应用过滤条件
            if filters:
                if 'category' in filters:
                    wiki_query = wiki_query.filter(WikiPage.category == filters['category'])
                if 'page_type' in filters:
                    wiki_query = wiki_query.filter(WikiPage.page_type == filters['page_type'])
            
            wiki_pages = wiki_query.limit(top_k).all()

            for page in wiki_pages:
                # 计算关键词匹配得分
                score = self._calculate_keyword_score(page, query)
                results.append(
                    {
                        "type": "wiki_page",
                        "id": page.id,
                        "title": page.title,
                        "content": (
                            page.content[:200] + "..."
                            if len(page.content) > 200
                            else page.content
                        ),
                        "category": page.category,
                        "score": score,
                        "search_type": "keyword"
                    }
                )

            # 搜索文档
            documents = (
                session.query(Document)
                .filter(
                    Document.title.contains(query)
                    | Document.extracted_text.contains(query)
                )
                .limit(top_k)
                .all()
            )

            for doc in documents:
                # 计算关键词匹配得分
                score = self._calculate_keyword_score(doc, query)
                results.append(
                    {
                        "type": "document",
                        "id": doc.id,
                        "title": doc.title,
                        "filename": doc.filename,
                        "content": (
                            doc.extracted_text[:200] + "..."
                            if doc.extracted_text and len(doc.extracted_text) > 200
                            else doc.extracted_text
                        ),
                        "score": score,
                        "search_type": "keyword"
                    }
                )

        return results

    def _semantic_search(self, query: str, top_k: int = 20) -> List[Dict[str, Any]]:
        """
        语义搜索

        Args:
            query: 搜索关键词
            top_k: 返回结果数量

        Returns:
            搜索结果列表
        """
        results = []

        # 执行语义搜索
        search_results = self.vector_store.search(query, top_k=top_k)

        # 处理搜索结果
        with self.db.get_session() as session:
            for doc_id, score, metadata in search_results:
                # 根据ID查找对应的文档或Wiki页面
                # 先尝试查找WikiPage
                wiki_page = session.query(WikiPage).filter(WikiPage.id == doc_id).first()
                if wiki_page:
                    results.append(
                        {
                            "type": "wiki_page",
                            "id": wiki_page.id,
                            "title": wiki_page.title,
                            "content": (
                                wiki_page.content[:200] + "..."
                                if len(wiki_page.content) > 200
                                else wiki_page.content
                            ),
                            "category": wiki_page.category,
                            "score": score,
                            "search_type": "semantic"
                        }
                    )
                else:
                    # 再尝试查找Document
                    document = session.query(Document).filter(Document.id == doc_id).first()
                    if document:
                        results.append(
                            {
                                "type": "document",
                                "id": document.id,
                                "title": document.title,
                                "filename": document.filename,
                                "content": (
                                    document.extracted_text[:200] + "..."
                                    if document.extracted_text and len(document.extracted_text) > 200
                                    else document.extracted_text
                                ),
                                "score": score,
                                "search_type": "semantic"
                            }
                        )

        return results

    def _hybrid_search(self, keyword_results: List[Dict[str, Any]], 
                      semantic_results: List[Dict[str, Any]], 
                      hybrid_weight: float = 0.5) -> List[Dict[str, Any]]:
        """
        混合搜索

        Args:
            keyword_results: 关键词搜索结果
            semantic_results: 语义搜索结果
            hybrid_weight: 混合搜索权重

        Returns:
            混合搜索结果
        """
        # 创建结果字典，用于去重和合并得分
        result_dict = {}

        # 添加关键词搜索结果
        for result in keyword_results:
            doc_id = result["id"]
            if doc_id not in result_dict:
                result_dict[doc_id] = result.copy()
            else:
                # 如果已经存在，更新得分
                result_dict[doc_id]["score"] = (1 - hybrid_weight) * result["score"] + \
                                              hybrid_weight * result_dict[doc_id].get("score", 0)

        # 添加语义搜索结果
        for result in semantic_results:
            doc_id = result["id"]
            if doc_id not in result_dict:
                result_dict[doc_id] = result.copy()
            else:
                # 如果已经存在，更新得分
                result_dict[doc_id]["score"] = (1 - hybrid_weight) * result_dict[doc_id].get("score", 0) + \
                                              hybrid_weight * result["score"]

        # 转换回列表
        return list(result_dict.values())

    def _calculate_keyword_score(self, item: Any, query: str) -> float:
        """
        计算关键词匹配得分

        Args:
            item: WikiPage或Document对象
            query: 搜索关键词

        Returns:
            匹配得分
        """
        score = 0.0

        # 检查标题匹配
        if hasattr(item, "title") and item.title:
            title_lower = item.title.lower()
            query_lower = query.lower()
            if query_lower in title_lower:
                # 标题匹配权重更高
                score += 0.7

        # 检查内容匹配
        content = ""
        if hasattr(item, "content") and item.content:
            content = item.content
        elif hasattr(item, "extracted_text") and item.extracted_text:
            content = item.extracted_text

        if content:
            content_lower = content.lower()
            query_lower = query.lower()
            if query_lower in content_lower:
                # 内容匹配权重较低
                score += 0.3

        # 检查完全匹配
        if hasattr(item, "title") and item.title == query:
            score = 1.0
        elif content == query:
            score = 0.9

        return score

    def _enhance_results_with_entities(self, results: List[Dict[str, Any]], query_entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        基于实体匹配增强搜索结果

        Args:
            results: 搜索结果列表
            query_entities: 查询中的实体列表

        Returns:
            增强后的搜索结果列表
        """
        enhanced_results = []
        
        for result in results:
            enhanced_result = result.copy()
            
            # 提取结果中的文本内容
            text = ""
            if "content" in result and result["content"]:
                text = result["content"]
            if "title" in result and result["title"]:
                text += " " + result["title"]
            
            # 检查实体匹配
            entity_match_count = 0
            for entity in query_entities:
                entity_name = entity.get("name", "")
                if entity_name and entity_name in text:
                    entity_match_count += 1
            
            # 根据实体匹配程度调整得分
            if entity_match_count > 0:
                # 每个匹配的实体增加0.1的得分
                entity_score = entity_match_count * 0.1
                enhanced_result["score"] = enhanced_result.get("score", 0) + entity_score
                enhanced_result["entity_matches"] = entity_match_count
            
            enhanced_results.append(enhanced_result)
        
        return enhanced_results

    def search_by_category(self, category: str) -> List[Dict[str, Any]]:
        """
        按分类搜索

        Args:
            category: 分类名称

        Returns:
            搜索结果列表
        """
        results = []

        with self.db.get_session() as session:
            pages = session.query(WikiPage).filter(WikiPage.category == category).all()

            for page in pages:
                results.append(
                    {
                        "id": page.id,
                        "title": page.title,
                        "category": page.category,
                        "content": (
                            page.content[:100] + "..."
                            if len(page.content) > 100
                            else page.content
                        ),
                    }
                )

        return results

    def _apply_filters(self, results: List[Dict[str, Any]], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        应用过滤条件

        Args:
            results: 搜索结果列表
            filters: 过滤条件

        Returns:
            过滤后的搜索结果列表
        """
        filtered_results = []
        
        for result in results:
            # 检查分类过滤
            if 'category' in filters and 'category' in result:
                if result['category'] != filters['category']:
                    continue
            
            # 检查页面类型过滤
            if 'page_type' in filters and 'page_type' in result:
                if result['page_type'] != filters['page_type']:
                    continue
            
            # 检查类型过滤
            if 'type' in filters:
                if result.get('type') != filters['type']:
                    continue
            
            filtered_results.append(result)
        
        return filtered_results

    def _sort_results(self, results: List[Dict[str, Any]], sort_by: str) -> List[Dict[str, Any]]:
        """
        对搜索结果进行排序

        Args:
            results: 搜索结果列表
            sort_by: 排序方式 (relevance, time, popularity)

        Returns:
            排序后的搜索结果列表
        """
        if sort_by == "relevance":
            # 按相关性排序
            results.sort(key=lambda x: x.get("score", 0), reverse=True)
        elif sort_by == "time":
            # 按时间排序（假设结果中有时间字段）
            results.sort(key=lambda x: x.get("modified", ""), reverse=True)
        elif sort_by == "popularity":
            # 按热度排序（假设结果中有热度字段）
            results.sort(key=lambda x: x.get("popularity", 0), reverse=True)
        
        return results

    def search_related_topics(self, topic: str) -> List[Dict[str, Any]]:
        """
        搜索相关主题

        Args:
            topic: 主题名称

        Returns:
            相关主题列表
        """
        try:
            logger.info(f"搜索相关主题: {topic}")
            
            # 初始化结果列表
            related_topics = []
            
            # 使用语义搜索找到相关内容
            if self.vector_store:
                # 执行语义搜索
                search_results = self.vector_store.search(topic, top_k=10)
                
                # 处理搜索结果
                with self.db.get_session() as session:
                    for doc_id, score, metadata in search_results:
                        # 根据ID查找对应的文档或Wiki页面
                        # 先尝试查找WikiPage
                        wiki_page = session.query(WikiPage).filter(WikiPage.id == doc_id).first()
                        if wiki_page:
                            related_topics.append({
                                "id": wiki_page.id,
                                "title": wiki_page.title,
                                "category": wiki_page.category,
                                "score": score,
                                "type": "wiki_page"
                            })
                        else:
                            # 再尝试查找Document
                            document = session.query(Document).filter(Document.id == doc_id).first()
                            if document:
                                related_topics.append({
                                    "id": document.id,
                                    "title": document.title,
                                    "filename": document.filename,
                                    "score": score,
                                    "type": "document"
                                })
            
            # 也可以使用关键词搜索来补充结果
            keyword_results = self._keyword_search(topic, top_k=10)
            for result in keyword_results:
                # 去重：检查是否已经在结果列表中
                if not any(item.get("id") == result.get("id") for item in related_topics):
                    related_topics.append({
                        "id": result.get("id"),
                        "title": result.get("title"),
                        "category": result.get("category"),
                        "filename": result.get("filename"),
                        "score": result.get("score"),
                        "type": result.get("type")
                    })
            
            # 按得分排序
            related_topics.sort(key=lambda x: x.get("score", 0), reverse=True)
            
            # 限制返回结果数量
            related_topics = related_topics[:10]
            
            logger.info(f"找到 {len(related_topics)} 个相关主题")
            return related_topics
        except Exception as e:
            logger.error(f"搜索相关主题失败: {e}")
            return []

    def save_query_answer_as_wiki_page(self, query: str, answer: str, related_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        将有价值的查询回答保存为Wiki新页面

        Args:
            query: 查询内容
            answer: 回答内容
            related_results: 相关搜索结果

        Returns:
            保存结果
        """
        from ..storage.wiki_storage import WikiStorage, WikiPageData
        from ..process.llm_client import get_llm_client
        
        try:
            logger.info(f"将查询回答保存为Wiki页面: {query}")
            
            # 初始化Wiki存储和LLM客户端
            wiki_storage = WikiStorage()
            llm_client = get_llm_client()
            
            # 生成页面标题
            title = self._generate_title_from_query(query)
            if not title:
                title = query[:50] + "..." if len(query) > 50 else query
            
            # 生成页面摘要
            summary = self._generate_summary(answer)
            if not summary:
                summary = answer[:100] + "..." if len(answer) > 100 else answer
            
            # 生成页面内容
            content = f"# 原始查询\n{query}\n\n# 回答\n{answer}\n\n"
            
            # 添加相关参考
            if related_results:
                content += "# 相关参考\n"
                for i, result in enumerate(related_results[:5], 1):
                    content += f"- [{result.get('title', '未知')}]({result.get('id', '')})\n"
            
            # 创建Wiki页面数据
            page_data = WikiPageData(
                title=title,
                content=content,
                summary=summary,
                category="查询回答",
                tags=["查询", "自动生成"],
                metadata={
                    "query": query,
                    "related_results": related_results,
                    "created_at": datetime.now().isoformat()
                }
            )
            
            # 保存Wiki页面
            file_path = wiki_storage.save_page(page_data, page_type="article")
            
            # 更新索引
            wiki_storage.update_index()
            
            # 添加操作日志
            log_details = f"保存查询回答为Wiki页面: {title}\n查询内容: {query}\n文件路径: {file_path}"
            wiki_storage.add_to_log("查询回答保存", log_details)
            
            logger.info(f"成功将查询回答保存为Wiki页面: {file_path}")
            return {
                "success": True,
                "file_path": file_path,
                "title": title
            }
        except Exception as e:
            logger.error(f"保存查询回答为Wiki页面失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _generate_title_from_query(self, query: str) -> str:
        """
        从查询生成页面标题

        Args:
            query: 查询内容

        Returns:
            页面标题
        """
        try:
            # 简单实现：使用查询的前50个字符作为标题
            title = query.strip()
            if len(title) > 50:
                title = title[:50] + "..."
            return title
        except Exception as e:
            logger.error(f"生成标题失败: {e}")
            return ""
    
    def _generate_summary(self, answer: str) -> str:
        """
        从回答生成页面摘要

        Args:
            answer: 回答内容

        Returns:
            页面摘要
        """
        try:
            # 简单实现：使用回答的前100个字符作为摘要
            summary = answer.strip()
            if len(summary) > 100:
                summary = summary[:100] + "..."
            return summary
        except Exception as e:
            logger.error(f"生成摘要失败: {e}")
            return ""
