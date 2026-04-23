"""
对话管理器

管理基于文档内容的问答对话系统，支持对话session管理和文档自动更新功能。
"""

from typing import Dict, Any, List, Optional, Tuple
import uuid
import time
import json
import re
from datetime import datetime
from dataclasses import dataclass
from collections import defaultdict

from ..core.config import get_config
from ..core.logger import get_logger
from ..core.error_handler import ErrorHandler
from .llm_client import get_llm_client
from ..storage.wiki_storage import WikiStorage
from ..storage.database import get_db_manager
from ..storage.models import WikiPage, Document, Feedback
from ..storage.vector.factory import get_vector_store

logger = get_logger(__name__)


@dataclass
class DialogMessage:
    """对话消息"""
    role: str  # user 或 assistant
    content: str
    timestamp: float
    message_id: str = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.message_id is None:
            self.message_id = str(uuid.uuid4())
        if self.metadata is None:
            self.metadata = {}


class DialogSession:
    """对话会话"""
    
    def __init__(self, session_id: str = None, document_id: str = None, wiki_page_id: str = None):
        """
        初始化对话会话
        
        Args:
            session_id: 会话ID
            document_id: 文档ID
            wiki_page_id: Wiki页面ID
        """
        self.session_id = session_id or str(uuid.uuid4())
        self.document_id = document_id
        self.wiki_page_id = wiki_page_id
        self.messages: List[DialogMessage] = []
        self.start_time = time.time()
        self.last_activity_time = time.time()
        self.important_info: List[Dict[str, Any]] = []
        self.context: Dict[str, Any] = {}
    
    def add_message(self, role: str, content: str, metadata: Dict[str, Any] = None) -> DialogMessage:
        """
        添加对话消息
        
        Args:
            role: 角色，user 或 assistant
            content: 消息内容
            metadata: 元数据
        
        Returns:
            对话消息对象
        """
        message = DialogMessage(
            role=role,
            content=content,
            timestamp=time.time(),
            metadata=metadata
        )
        self.messages.append(message)
        self.last_activity_time = time.time()
        return message
    
    def add_important_info(self, info: Dict[str, Any]):
        """
        添加重要信息
        
        Args:
            info: 重要信息
        """
        info["added_at"] = time.time()
        self.important_info.append(info)
    
    def get_context(self) -> Dict[str, Any]:
        """
        获取对话上下文
        
        Returns:
            对话上下文
        """
        return self.context
    
    def update_context(self, key: str, value: Any):
        """
        更新对话上下文
        
        Args:
            key: 键
            value: 值
        """
        self.context[key] = value
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典
        
        Returns:
            字典表示
        """
        return {
            "session_id": self.session_id,
            "document_id": self.document_id,
            "wiki_page_id": self.wiki_page_id,
            "messages": [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp,
                    "message_id": msg.message_id,
                    "metadata": msg.metadata
                }
                for msg in self.messages
            ],
            "start_time": self.start_time,
            "last_activity_time": self.last_activity_time,
            "important_info": self.important_info,
            "context": self.context
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DialogSession":
        """
        从字典创建对话会话
        
        Args:
            data: 字典数据
        
        Returns:
            对话会话对象
        """
        session = cls(
            session_id=data.get("session_id"),
            document_id=data.get("document_id"),
            wiki_page_id=data.get("wiki_page_id")
        )
        session.messages = [
            DialogMessage(
                role=msg["role"],
                content=msg["content"],
                timestamp=msg["timestamp"],
                message_id=msg.get("message_id"),
                metadata=msg.get("metadata")
            )
            for msg in data.get("messages", [])
        ]
        session.start_time = data.get("start_time", time.time())
        session.last_activity_time = data.get("last_activity_time", time.time())
        session.important_info = data.get("important_info", [])
        session.context = data.get("context", {})
        return session


class DialogManager:
    """对话管理器"""
    
    def __init__(self):
        """初始化对话管理器"""
        self.config = get_config()
        self.llm_client = get_llm_client()
        self.wiki_storage = WikiStorage()
        self.db = get_db_manager()
        self.vector_store = get_vector_store()
        self.sessions: Dict[str, DialogSession] = {}
        # 配置参数
        dialog_config = getattr(self.config, "dialog", {})
        performance_config = getattr(self.config, "performance", {})
        self.session_timeout = performance_config.get("session_timeout", 3600)  # 会话超时时间（秒）
        self.similarity_threshold = dialog_config.get("similarity_threshold", 0.7)  # 相似度阈值
        self.response_time_threshold = performance_config.get("response_time_threshold", 5000)  # 响应时间阈值（毫秒）
        self.accuracy_threshold = dialog_config.get("accuracy_threshold", 90)  # 准确率阈值（%）
        self.max_retrieval_results = dialog_config.get("max_retrieval_results", 10)  # 最大检索结果数
        self.max_depth = dialog_config.get("max_depth", 3)  # 最大检索深度
        
    def create_session(self, document_id: str = None, wiki_page_id: str = None) -> str:
        """
        创建对话会话
        
        Args:
            document_id: 文档ID
            wiki_page_id: Wiki页面ID
        
        Returns:
            会话ID
        """
        session = DialogSession(document_id=document_id, wiki_page_id=wiki_page_id)
        self.sessions[session.session_id] = session
        logger.info(f"创建对话会话: {session.session_id}")
        return session.session_id
    
    def get_session(self, session_id: str) -> Optional[DialogSession]:
        """
        获取对话会话
        
        Args:
            session_id: 会话ID
        
        Returns:
            对话会话对象，如果不存在则返回None
        """
        session = self.sessions.get(session_id)
        if session:
            # 检查会话是否超时
            if time.time() - session.last_activity_time > self.session_timeout:
                logger.info(f"对话会话超时: {session_id}")
                del self.sessions[session_id]
                return None
        return session
    
    def delete_session(self, session_id: str):
        """
        删除对话会话
        
        Args:
            session_id: 会话ID
        """
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"删除对话会话: {session_id}")
    
    def cleanup_expired_sessions(self):
        """
        清理过期会话
        """
        expired_sessions = []
        for session_id, session in self.sessions.items():
            if time.time() - session.last_activity_time > self.session_timeout:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            del self.sessions[session_id]
            logger.info(f"清理过期对话会话: {session_id}")
    
    @ErrorHandler.handle_processing_exceptions()
    def process_message(self, session_id: str, message: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        处理用户消息

        Args:
            session_id: 会话ID
            message: 用户消息
            metadata: 元数据

        Returns:
            处理结果
        """
        # 记录开始时间
        start_time = time.time()

        # 获取会话
        session = self.get_session(session_id)
        if not session:
            return {
                "success": False,
                "error": "会话不存在或已过期"
            }

        # 添加用户消息
        session.add_message("user", message, metadata)

        # 获取相关文档内容
        context = self._get_context(session, message)

        # 生成回答
        answer = self._generate_answer(session, message, context)

        # 添加助手消息
        session.add_message("assistant", answer)

        # 提取重要信息
        important_info = self._extract_important_info(message, answer)
        for info in important_info:
            session.add_important_info(info)

        # 更新文档
        if important_info:
            self._update_document(session, important_info)

        # 计算响应时间
        response_time = (time.time() - start_time) * 1000  # 转换为毫秒
        logger.info(f"响应时间: {response_time:.2f} 毫秒")

        # 检查响应时间是否超过阈值
        if response_time > self.response_time_threshold:
            logger.warning(f"响应时间超过阈值: {response_time:.2f} 毫秒")

        return {
            "success": True,
            "answer": answer,
            "important_info": important_info,
            "response_time": response_time,
            "confidence": self._calculate_confidence(self._validate_results(self._retrieve_relevant_info(message, session), message))
        }
    
    def _get_context(self, session: DialogSession, query: str = None) -> str:
        """
        获取对话上下文

        Args:
            session: 对话会话
            query: 用户问题

        Returns:
            上下文文本
        """
        context = ""

        # 确保所有文档内容都已添加到向量存储
        self._ensure_documents_in_vector_store()

        # 获取相关文档片段
        if query:
            # 检索相关信息
            search_results = self._retrieve_relevant_info(query, session, top_k=self.max_retrieval_results)
            # 验证检索结果
            validated_results = self._validate_results(search_results, query)
            
            if validated_results:
                context += "# 相关信息\n"
                for i, (_, score, metadata) in enumerate(validated_results[:3]):  # 只使用前3个最相关的结果
                    content = metadata.get("content", "")
                    context += f"## 相关信息 {i+1} (相似度: {score:.2f})\n{content[:500]}...\n\n"

        # 获取文档内容
        if session.document_id:
            with self.db.get_session() as db_session:
                document = db_session.query(Document).filter(Document.id == session.document_id).first()
                if document and document.extracted_text:
                    context += f"# 文档内容\n{document.extracted_text[:1000]}...\n\n"

        # 获取Wiki页面内容
        if session.wiki_page_id:
            with self.db.get_session() as db_session:
                wiki_page = db_session.query(WikiPage).filter(WikiPage.id == session.wiki_page_id).first()
                if wiki_page and wiki_page.content:
                    context += f"# Wiki页面内容\n{wiki_page.content[:1000]}...\n\n"

        # 获取对话历史
        if session.messages:
            context += "# 对话历史\n"
            for msg in session.messages[-5:]:  # 只使用最近5条消息
                context += f"{msg.role}: {msg.content}\n"

        return context

    def _ensure_documents_in_vector_store(self):
        """
        确保所有文档内容都已添加到向量存储
        """
        try:
            logger.info("开始确保文档添加到向量存储")
            with self.db.get_session() as db_session:
                # 获取所有已完成处理的文档
                documents = db_session.query(Document).filter(Document.processing_status == "completed").all()
                logger.info(f"找到 {len(documents)} 个已完成处理的文档")
                
                for document in documents:
                    if document.extracted_text:
                        logger.info(f"处理文档: {document.title or document.filename}")
                        # 检查文档是否已经在向量存储中
                        # 这里简化处理，直接添加，向量存储会自动处理重复ID
                        documents_list = [document.extracted_text]
                        ids_list = [document.id]
                        metadatas_list = [{
                            "document_id": document.id,
                            "title": document.title or document.filename,
                            "file_type": document.file_type,
                            "content": document.extracted_text
                        }]
                        
                        # 添加到向量存储
                        self.vector_store.add(documents=documents_list, ids=ids_list, metadatas=metadatas_list)
                        logger.info(f"文档已添加到向量存储: {document.title or document.filename}")
                    else:
                        logger.info(f"跳过空文档: {document.title or document.filename}")
        except Exception as e:
            logger.error(f"确保文档添加到向量存储失败: {e}")
    
    def _generate_answer(self, session: DialogSession, message: str, context: str) -> str:
        """
        生成回答

        Args:
            session: 对话会话
            message: 用户消息
            context: 上下文

        Returns:
            回答
        """
        # 计算检索结果的置信度
        confidence = 0.0
        if message:
            search_results = self._retrieve_relevant_info(message, session, top_k=self.max_retrieval_results)
            validated_results = self._validate_results(search_results, message)
            confidence = self._calculate_confidence(validated_results)
            logger.error(f"检索结果数量: {len(validated_results)}, 置信度: {confidence}")

        # 检查置信度是否低于阈值，对人物查询使用更低的阈值
        if self._is_person_query(message):
            if confidence < 0.5:
                return "没有该信息"
        else:
            if confidence < self.similarity_threshold:
                return "没有该信息"

        # 构建提示词
        prompt = f"# 任务：基于文档内容回答问题\n\n"
        prompt += f"## 上下文\n{context}\n\n"
        prompt += f"## 用户问题\n{message}\n\n"
        prompt += "## 输出要求\n"
        prompt += "- 基于上下文内容回答问题\n"
        prompt += "- 回答要准确、简洁\n"
        prompt += "- 只使用上下文提供的信息，不要添加额外信息\n"
        prompt += "- 如果无法回答，请返回'没有该信息'\n"

        # 调用LLM
        result = self.llm_client.generate_wiki_page(
            title="回答问题",
            content=prompt,
            use_batch=False,
            system_prompt="你是一个基于文档内容的问答专家，擅长根据提供的上下文回答用户问题。",
            task_type="question_answering"
        )

        # 提取回答
        answer = result.get("answer", "")
        if not answer:
            answer = result.get("content", "没有该信息")

        # 确保回答符合要求
        if "无法回答" in answer or "没有相关信息" in answer:
            return "没有该信息"

        return answer
    
    def _extract_important_info(self, message: str, answer: str) -> List[Dict[str, Any]]:
        """
        提取重要信息
        
        Args:
            message: 用户消息
            answer: 助手回答
        
        Returns:
            重要信息列表
        """
        # 构建提示词
        prompt = f"# 任务：提取重要信息\n\n"
        prompt += f"## 用户问题\n{message}\n\n"
        prompt += f"## 助手回答\n{answer}\n\n"
        prompt += "## 输出要求\n"
        prompt += "- 从对话中提取重要信息\n"
        prompt += "- 重要信息包括：新的事实、概念、关系等\n"
        prompt += "- 每个重要信息要包含：内容、类型、重要性\n"
        prompt += "- 输出格式为JSON\n"
        prompt += "\n## 返回格式\n"
        prompt += "```json\n"
        prompt += "{\n"
        prompt += '  "important_info": [\n'
        prompt += '    {\n'
        prompt += '      "content": "重要信息内容",\n'
        prompt += '      "type": "信息类型",\n'
        prompt += '      "importance": 重要性（1-5）\n'
        prompt += '    }\n'
        prompt += '  ]\n'
        prompt += "}\n"
        prompt += "```\n"
        
        # 调用LLM
        result = self.llm_client.generate_wiki_page(
            title="提取重要信息",
            content=prompt,
            use_batch=False,
            system_prompt="你是一个信息提取专家，擅长从对话中提取重要信息。",
            task_type="info_extraction"
        )
        
        # 提取重要信息
        important_info = result.get("important_info", [])
        if not isinstance(important_info, list):
            important_info = []
        
        return important_info
    
    def _preprocess_query(self, query: str) -> str:
        """
        预处理用户问题

        Args:
            query: 用户问题

        Returns:
            预处理后的问题
        """
        # 去除多余的空格和换行符
        query = re.sub(r'\s+', ' ', query.strip())
        # 转换为小写
        query = query.lower()
        # 去除停用词
        stop_words = {'的', '了', '是', '在', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这'}
        words = query.split()
        filtered_words = [word for word in words if word not in stop_words]
        return ' '.join(filtered_words)

    def _retrieve_relevant_info(self, query: str, session: DialogSession, top_k: int = 5) -> List[Tuple[str, float, Dict[str, Any]]]:
        """
        检索相关信息

        Args:
            query: 用户问题
            session: 对话会话
            top_k: 返回结果数量

        Returns:
            检索结果列表，每个元素为(id, score, metadata)
        """
        # 预处理查询
        processed_query = self._preprocess_query(query)
        logger.error(f"预处理查询: {processed_query}")

        # 构建过滤条件
        filter_conditions = {}
        if session.document_id:
            filter_conditions["document_id"] = session.document_id
        if session.wiki_page_id:
            filter_conditions["wiki_page_id"] = session.wiki_page_id
        logger.error(f"过滤条件: {filter_conditions}")

        # 对于人物查询，使用更广泛的搜索
        if self._is_person_query(query):
            # 提取人物名称
            person_name = ' '.join(processed_query.split())
            logger.error(f"人物查询，提取人物名称: {person_name}")
            # 执行多次搜索以提高召回率
            all_results = []
            
            # 1. 使用原始查询进行搜索
            results1 = self.vector_store.search(processed_query, top_k=top_k, filter=filter_conditions)
            logger.error(f"使用原始查询搜索结果: {results1}")
            all_results.extend(results1)
            
            # 2. 使用人物名称进行搜索
            if person_name:
                results2 = self.vector_store.search(person_name, top_k=top_k, filter=filter_conditions)
                logger.error(f"使用人物名称搜索结果: {results2}")
                all_results.extend(results2)
            
            # 3. 如果查询是"张勇是谁"，尝试使用"张勇"进行搜索
            if '是谁' in query or '谁是' in query:
                # 提取可能的人名
                name_candidates = self._extract_name_candidates(query)
                logger.error(f"提取的人名候选: {name_candidates}")
                for candidate in name_candidates:
                    results3 = self.vector_store.search(candidate, top_k=top_k, filter=filter_conditions)
                    logger.error(f"使用人名候选 {candidate} 搜索结果: {results3}")
                    all_results.extend(results3)
            
            # 4. 尝试使用人物名称的变体进行搜索（简单的同义词处理）
            if person_name:
                name_variants = self._generate_name_variants(person_name)
                logger.error(f"生成的人名变体: {name_variants}")
                for variant in name_variants:
                    results4 = self.vector_store.search(variant, top_k=top_k, filter=filter_conditions)
                    logger.error(f"使用人名变体 {variant} 搜索结果: {results4}")
                    all_results.extend(results4)
            
            # 5. 尝试使用更广泛的搜索，不使用过滤条件
            if not all_results:
                results5 = self.vector_store.search(person_name, top_k=top_k, filter=None)
                logger.error(f"使用更广泛搜索（无过滤条件）结果: {results5}")
                all_results.extend(results5)
            
            # 去重并按相似度排序
            unique_results = []
            seen_ids = set()
            for result in all_results:
                doc_id, score, metadata = result
                if doc_id not in seen_ids:
                    seen_ids.add(doc_id)
                    unique_results.append(result)
            
            # 按相似度排序
            unique_results.sort(key=lambda x: x[1], reverse=True)
            logger.error(f"去重并排序后的搜索结果: {unique_results}")
            
            # 返回前top_k个结果
            search_results = unique_results[:top_k]
        else:
            # 对于普通查询，使用标准的向量搜索
            search_results = self.vector_store.search(processed_query, top_k=top_k, filter=filter_conditions)
            # 按相似度排序
            search_results.sort(key=lambda x: x[1], reverse=True)
            logger.error(f"普通查询搜索结果: {search_results}")

        return search_results
    
    def _generate_name_variants(self, name: str) -> List[str]:
        """
        生成人名的变体形式

        Args:
            name: 原始人名

        Returns:
            人名变体列表
        """
        variants = []
        
        # 添加原始名称
        variants.append(name)
        
        # 尝试不同的分词形式（对于中文名字）
        if len(name) >= 2:
            # 对于双字名字，尝试单独搜索每个字
            if len(name) == 2:
                variants.append(name[0])
                variants.append(name[1])
            # 对于三字或四字名字，尝试不同的组合
            elif len(name) == 3:
                variants.append(name[0:2])
                variants.append(name[1:3])
            elif len(name) == 4:
                variants.append(name[0:2])
                variants.append(name[2:4])
                variants.append(name[0:3])
                variants.append(name[1:4])
        
        # 去重
        return list(set(variants))

    def _extract_name_candidates(self, query: str) -> List[str]:
        """
        从查询中提取可能的人名候选

        Args:
            query: 用户问题

        Returns:
            人名候选列表
        """
        # 简单的规则提取
        candidates = []
        
        # 移除疑问词
        question_words = ['谁', '是谁', '什么', '哪里', '什么时候', '为什么', '怎么样', '如何']
        cleaned_query = query
        for word in question_words:
            cleaned_query = cleaned_query.replace(word, '')
        
        # 提取可能的人名
        # 假设人名是2-4个汉字
        import re
        chinese_chars = re.findall(r'[\u4e00-\u9fa5]{2,4}', cleaned_query)
        candidates.extend(chinese_chars)
        
        # 去重
        return list(set(candidates))

    def _validate_results(self, results: List[Tuple[str, float, Dict[str, Any]]], query: str) -> List[Tuple[str, float, Dict[str, Any]]]:
        """
        验证检索结果

        Args:
            results: 检索结果列表
            query: 用户问题

        Returns:
            验证后的结果列表
        """
        if not results:
            return []

        # 交叉验证：检查结果之间的一致性
        validated_results = []
        for i, (doc_id, score, metadata) in enumerate(results):
            # 检查相似度阈值，对人物查询使用更低的阈值
            if self._is_person_query(query):
                # 对人物查询使用更低的相似度阈值
                if score < 0.4:
                    continue
            else:
                # 对普通查询使用标准阈值
                if score < self.similarity_threshold:
                    continue

            # 检查结果是否与查询相关，传递文档标题
            content = metadata.get("content", "")
            title = metadata.get("title", "")
            logger.error(f"验证文档: {title}, 相似度: {score}, 内容: {content[:100]}...")
            if self._is_relevant(content, query, title):
                validated_results.append((doc_id, score, metadata))
                logger.error(f"文档 {title} 被视为相关")
            else:
                logger.error(f"文档 {title} 被视为不相关")

        logger.error(f"验证后的结果数量: {len(validated_results)}")
        return validated_results

    def _is_relevant(self, content: str, query: str, title: str = "") -> bool:
        """
        判断内容是否与查询相关

        Args:
            content: 文档内容
            query: 用户问题
            title: 文档标题

        Returns:
            是否相关
        """
        # 预处理查询和内容
        processed_query = self._preprocess_query(query)
        processed_content = self._preprocess_query(content)
        processed_title = self._preprocess_query(title)
        
        # 简单的关键词匹配
        query_words = set(processed_query.split())
        content_words = set(processed_content.split())
        title_words = set(processed_title.split())
        all_words = content_words.union(title_words)
        intersection = query_words.intersection(all_words)
        
        # 对于人物查询，使用更宽松的匹配
        if self._is_person_query(query):
            # 提取人物名称
            person_name = ' '.join(query_words)
            
            # 检查内容中是否包含人物名称
            if person_name in processed_content:
                return True
            
            # 检查标题中是否包含人物名称
            if person_name in processed_title:
                return True
            
            # 检查内容中是否包含人物相关的实体
            if self._contains_person_entity(content, person_name):
                return True
            
            # 检查内容中是否包含人物名称的任何部分
            if len(person_name) >= 2:
                name_parts = self._generate_name_variants(person_name)
                for part in name_parts:
                    if (part in processed_content or part in processed_title) and len(part) >= 2:
                        return True
        
        # 对于普通查询，使用标准的关键词匹配
        return len(intersection) > 0

    def _is_person_query(self, query: str) -> bool:
        """
        判断是否为人物查询

        Args:
            query: 用户问题

        Returns:
            是否为人物查询
        """
        # 检查查询是否包含人物相关的关键词
        person_keywords = ['谁', '是谁', '人物', '个人', '生平', '简介', '背景']
        for keyword in person_keywords:
            if keyword in query:
                return True
        # 检查查询是否只有一个词，可能是人名
        processed_query = self._preprocess_query(query)
        words = processed_query.split()
        if len(words) == 1 and len(words[0]) >= 2:
            return True
        return False

    def _contains_person_entity(self, content: str, person_name: str) -> bool:
        """
        检查内容中是否包含指定的人物实体

        Args:
            content: 文档内容
            person_name: 人物名称

        Returns:
            是否包含人物实体
        """
        # 简单的字符串匹配
        if person_name in content:
            return True
        # 检查内容中是否包含人物相关的描述
        person_indicators = ['先生', '女士', '教授', '博士', '主任', '经理', '总裁', 'CEO', '创始人']
        for indicator in person_indicators:
            if f'{person_name}{indicator}' in content:
                return True
        return False

    def _calculate_confidence(self, results: List[Tuple[str, float, Dict[str, Any]]]) -> float:
        """
        计算检索结果的置信度

        Args:
            results: 检索结果列表

        Returns:
            置信度分数（0-1）
        """
        if not results:
            return 0.0

        # 基于相似度分数计算置信度
        total_score = sum(score for _, score, _ in results)
        avg_score = total_score / len(results)

        # 基于结果数量调整置信度
        confidence = avg_score * min(len(results) / 3, 1.0)

        return min(confidence, 1.0)

    def _handle_feedback(self, session_id: str, feedback: Dict[str, Any]):
        """
        处理用户反馈

        Args:
            session_id: 会话ID
            feedback: 反馈信息
        """
        try:
            with self.db.get_session() as db_session:
                # 创建反馈记录
                feedback_record = Feedback(
                    session_id=session_id,
                    feedback_type=feedback.get("type"),
                    content=feedback.get("content"),
                    feedback_metadata=json.dumps(feedback.get("metadata", {})),
                    created_at=datetime.utcnow()
                )
                db_session.add(feedback_record)
                db_session.commit()
                logger.info(f"记录用户反馈: {session_id}")

                # 基于反馈优化检索算法
                # 这里可以实现更复杂的反馈处理逻辑
        except Exception as e:
            logger.error(f"处理用户反馈失败: {e}")

    def _update_document(self, session: DialogSession, important_info: List[Dict[str, Any]]):
        """
        更新文档

        Args:
            session: 对话会话
            important_info: 重要信息列表
        """
        # 只更新重要性大于3的信息
        significant_info = [info for info in important_info if info.get("importance", 0) > 3]
        if not significant_info:
            return

        # 更新Wiki页面
        if session.wiki_page_id:
            with self.db.get_session() as db_session:
                wiki_page = db_session.query(WikiPage).filter(WikiPage.id == session.wiki_page_id).first()
                if wiki_page:
                    # 构建更新内容
                    update_content = "\n## 对话补充信息\n"
                    for info in significant_info:
                        update_content += f"- {info.get('content', '')}（{info.get('type', '信息')}）\n"

                    # 更新页面内容
                    wiki_page.content += update_content
                    db_session.commit()
                    logger.info(f"更新Wiki页面: {session.wiki_page_id}")

        # 更新文档
        if session.document_id:
            # 这里可以实现文档更新逻辑
            pass
    
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        获取会话信息
        
        Args:
            session_id: 会话ID
        
        Returns:
            会话信息
        """
        session = self.get_session(session_id)
        if session:
            return session.to_dict()
        return None
    
    def list_sessions(self) -> List[Dict[str, Any]]:
        """
        列出所有会话

        Returns:
            会话列表
        """
        # 清理过期会话
        self.cleanup_expired_sessions()

        return [session.to_dict() for session in self.sessions.values()]

    def submit_feedback(self, session_id: str, feedback: Dict[str, Any]) -> Dict[str, Any]:
        """
        提交用户反馈

        Args:
            session_id: 会话ID
            feedback: 反馈信息

        Returns:
            处理结果
        """
        # 获取会话
        session = self.get_session(session_id)
        if not session:
            return {
                "success": False,
                "error": "会话不存在或已过期"
            }

        # 处理反馈
        self._handle_feedback(session_id, feedback)

        return {
            "success": True,
            "message": "反馈提交成功"
        }


# 全局对话管理器实例
dialog_manager = DialogManager()


def get_dialog_manager() -> DialogManager:
    """
    获取对话管理器实例
    
    Returns:
        对话管理器实例
    """
    return dialog_manager
