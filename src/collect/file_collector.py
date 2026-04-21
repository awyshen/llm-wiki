"""
本地文件收集器

负责从本地文件系统收集文档，支持导入单个文件或整个目录。
"""

import os
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any

from ..core.config import get_config
from ..core.logger import get_logger
from ..core.error_handler import ErrorHandler
from ..storage.database import get_db_manager
from ..storage.models import Document, ProcessingStatus

logger = get_logger(__name__)


class FileCollector:
    """本地文件收集器"""

    def __init__(self):
        self.config = get_config()
        self.db_manager = get_db_manager()
        self.raw_dir = os.path.join(self.config.data_dir, "raw")
        # 确保原始文件目录存在
        os.makedirs(self.raw_dir, exist_ok=True)
        
        # 配置参数
        self.similarity_threshold = self.config.get("file_similarity_threshold", 0.9)
        self.max_file_size_for_similarity = self.config.get("max_file_size_for_similarity", 10 * 1024 * 1024)  # 10MB
        self.batch_size = self.config.get("similarity_batch_size", 10)  # 批量处理大小

    @ErrorHandler.handle_storage_exceptions()
    def import_file(self, file_path: str) -> str:
        """
        导入单个文件

        Args:
            file_path: 文件路径

        Returns:
            文档ID

        Raises:
            FileNotFoundError: 文件不存在
            PermissionError: 没有权限访问文件
            ValueError: 文件已存在或内容相似
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")

        if not os.path.isfile(file_path):
            raise ValueError(f"路径不是文件: {file_path}")

        # 提取文件信息
        filename = os.path.basename(file_path)
        file_type = os.path.splitext(filename)[1].lstrip('.').lower()
        title = os.path.splitext(filename)[0]
        
        # 检查文件名重复
        if self.check_duplicate_filename(filename):
            logger.info(f"文件 {filename} 已存在，跳过导入")
            raise ValueError(f"文件 {filename} 已存在")
        
        # 提取文本内容
        extracted_text = self._extract_text(file_path, file_type)
        
        # 检查内容相似性
        similar_files = self.check_similar_files(file_path, extracted_text)
        if similar_files:
            # 按相似度排序，取最高的一个
            similar_files.sort(key=lambda x: x["similarity"], reverse=True)
            most_similar = similar_files[0]
            logger.info(f"文件 {filename} 与现有文件 {most_similar['filename']} 内容相似 (相似度: {most_similar['similarity']:.2f})，跳过导入")
            raise ValueError(f"文件 {filename} 与现有文件 {most_similar['filename']} 内容相似 (相似度: {most_similar['similarity']:.2f})")

        # 生成唯一的文档ID
        doc_id = str(uuid.uuid4())

        # 复制文件到原始文件目录
        dest_path = os.path.join(self.raw_dir, f"{doc_id}_{filename}")
        try:
            # 复制文件到统一的存储位置
            import shutil
            shutil.copy2(file_path, dest_path)
            stored_path = dest_path

            # 文本内容已经在前面提取过了

            # 保存到数据库
            with self.db_manager.get_session() as session:
                logger.info(f"开始导入文件: {filename}, 文档ID: {doc_id}")
                document = Document(
                    id=doc_id,
                    title=title,
                    filename=filename,
                    file_path=stored_path,
                    file_type=file_type,
                    extracted_text=extracted_text,
                    processing_status=ProcessingStatus.PENDING.value,
                    created_at=datetime.utcnow()
                )
                session.add(document)
                session.commit()

            logger.info(f"成功导入文件: {filename}, 文档ID: {doc_id}, 提取文本长度: {len(extracted_text) if extracted_text else 0}")
            return doc_id
        except Exception as e:
            logger.error(f"导入文件失败: {file_path}, 错误: {str(e)}")
            raise
    
    @ErrorHandler.handle_storage_exceptions()
    def import_file_storage(self, file_storage) -> dict:
        """
        导入FileStorage对象（用于API文件上传）

        Args:
            file_storage: Flask FileStorage对象

        Returns:
            包含文档信息的字典

        Raises:
            ValueError: 文件为空或已存在或内容相似
        """
        if file_storage.filename == "":
            raise ValueError("文件名不能为空")

        # 提取文件信息
        filename = file_storage.filename
        file_type = os.path.splitext(filename)[1].lstrip('.').lower()
        title = os.path.splitext(filename)[0]
        
        # 检查文件名重复
        if self.check_duplicate_filename(filename):
            logger.info(f"文件 {filename} 已存在，跳过导入")
            raise ValueError(f"文件 {filename} 已存在")

        # 生成唯一的文档ID
        doc_id = str(uuid.uuid4())

        # 保存文件到原始文件目录
        dest_path = os.path.join(self.raw_dir, f"{doc_id}_{filename}")
        try:
            # 保存FileStorage对象到磁盘
            file_storage.save(dest_path)
            stored_path = dest_path

            # 提取文本内容
            extracted_text = self._extract_text(stored_path, file_type)

            # 检查内容相似性
            similar_files = self.check_similar_files(stored_path, extracted_text)
            if similar_files:
                # 按相似度排序，取最高的一个
                similar_files.sort(key=lambda x: x["similarity"], reverse=True)
                most_similar = similar_files[0]
                logger.info(f"文件 {filename} 与现有文件 {most_similar['filename']} 内容相似 (相似度: {most_similar['similarity']:.2f})，跳过导入")
                raise ValueError(f"文件 {filename} 与现有文件 {most_similar['filename']} 内容相似 (相似度: {most_similar['similarity']:.2f})")

            # 保存到数据库
            with self.db_manager.get_session() as session:
                logger.info(f"开始导入文件: {filename}, 文档ID: {doc_id}")
                document = Document(
                    id=doc_id,
                    title=title,
                    filename=filename,
                    file_path=stored_path,
                    file_type=file_type,
                    extracted_text=extracted_text,
                    processing_status=ProcessingStatus.PENDING.value,
                    created_at=datetime.utcnow()
                )
                session.add(document)
                session.commit()

            logger.info(f"成功导入文件: {filename}, 文档ID: {doc_id}, 提取文本长度: {len(extracted_text) if extracted_text else 0}")
            # 返回文档信息字典，避免Session绑定问题
            return {
                "id": doc_id,
                "title": title,
                "filename": filename,
                "file_path": stored_path,
                "file_type": file_type,
                "processing_status": ProcessingStatus.PENDING.value
            }
        except Exception as e:
            logger.error(f"导入文件失败: {filename}, 错误: {str(e)}")
            raise
    
    def _extract_text(self, file_path: str, file_type: str) -> str:
        """
        提取文件文本内容

        Args:
            file_path: 文件路径
            file_type: 文件类型

        Returns:
            提取的文本内容
        """
        try:
            # 导入文档处理器
            from ..process.document_processor import DocumentProcessor
            processor = DocumentProcessor()
            text = processor.extract_text(file_path, file_type)
            
            # 验证提取的文本内容
            if not text or len(text.strip()) == 0:
                logger.warning(f"文件 {file_path} 提取的文本内容为空")
                return ""
            
            logger.info(f"成功提取文件 {file_path} 的文本内容，长度: {len(text)}")
            return text
        except Exception as e:
            logger.error(f"提取文件文本失败: {file_path}, 错误: {str(e)}")
            # 提取失败时返回空字符串，不影响文件导入
            return ""

    @ErrorHandler.handle_storage_exceptions()
    def import_directory(self, directory_path: str) -> List[str]:
        """
        导入目录中的所有文件

        Args:
            directory_path: 目录路径

        Returns:
            导入的文档ID列表

        Raises:
            FileNotFoundError: 目录不存在
            PermissionError: 没有权限访问目录
        """
        if not os.path.exists(directory_path):
            raise FileNotFoundError(f"目录不存在: {directory_path}")

        if not os.path.isdir(directory_path):
            raise ValueError(f"路径不是目录: {directory_path}")

        imported_doc_ids = []

        # 支持的文件类型
        supported_extensions = {
            'md', 'txt', 'pdf', 'doc', 'docx', 'rtf', 'html', 'htm',
            'csv', 'xlsx', 'xls', 'ppt', 'pptx'
        }

        # 遍历目录中的所有文件
        for root, _, files in os.walk(directory_path):
            for file in files:
                file_ext = os.path.splitext(file)[1].lstrip('.').lower()
                if file_ext in supported_extensions:
                    file_path = os.path.join(root, file)
                    try:
                        doc_id = self.import_file(file_path)
                        imported_doc_ids.append(doc_id)
                    except Exception as e:
                        logger.error(f"导入文件失败: {file_path}, 错误: {str(e)}")
                        # 继续处理其他文件
                        continue

        logger.info(f"成功导入 {len(imported_doc_ids)} 个文件")
        return imported_doc_ids

    def get_supported_file_types(self) -> List[str]:
        """
        获取支持的文件类型

        Returns:
            支持的文件类型列表
        """
        return [
            'md', 'txt', 'pdf', 'doc', 'docx', 'rtf', 'html', 'htm',
            'csv', 'xlsx', 'xls', 'ppt', 'pptx'
        ]

    @ErrorHandler.handle_storage_exceptions()
    def import_files(self, file_paths: List[str]) -> Dict[str, List[str]]:
        """
        批量导入多个文件

        Args:
            file_paths: 文件路径列表

        Returns:
            导入结果，包含成功和失败的文件列表
        """
        results = {
            "success": [],
            "failed": []
        }

        for file_path in file_paths:
            try:
                doc_id = self.import_file(file_path)
                results["success"].append({
                    "file_path": file_path,
                    "doc_id": doc_id,
                    "filename": os.path.basename(file_path)
                })
            except Exception as e:
                results["failed"].append({
                    "file_path": file_path,
                    "error": str(e),
                    "filename": os.path.basename(file_path)
                })

        logger.info(f"批量导入完成: 成功 {len(results['success'])} 个，失败 {len(results['failed'])} 个")
        return results

    def validate_file(self, file_path: str) -> bool:
        """
        验证文件是否支持

        Args:
            file_path: 文件路径

        Returns:
            是否支持该文件
        """
        if not os.path.isfile(file_path):
            return False

        file_ext = os.path.splitext(file_path)[1].lstrip('.').lower()
        return file_ext in self.get_supported_file_types()

    def check_duplicate_filename(self, filename: str) -> bool:
        """
        检查是否存在相同文件名的文件

        Args:
            filename: 文件名

        Returns:
            是否存在相同文件名的文件
        """
        try:
            with self.db_manager.get_session() as session:
                # 区分大小写查询相同文件名的文件
                existing_documents = session.query(Document).filter(Document.filename == filename).all()
                return len(existing_documents) > 0
        except Exception as e:
            logger.error(f"检查文件名重复失败: {e}")
            # 出错时默认不视为重复，避免阻止文件导入
            return False

    def calculate_file_hash(self, file_path: str) -> str:
        """
        计算文件的哈希值，用于快速比较文件内容

        Args:
            file_path: 文件路径

        Returns:
            文件的哈希值
        """
        import hashlib
        try:
            hasher = hashlib.md5()
            with open(file_path, 'rb') as f:
                # 分块读取文件，避免大文件占用过多内存
                for chunk in iter(lambda: f.read(4096), b''):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception as e:
            logger.error(f"计算文件哈希失败: {e}")
            return None

    def calculate_text_similarity(self, text1: str, text2: str) -> float:
        """
        计算两个文本之间的相似度

        Args:
            text1: 第一个文本
            text2: 第二个文本

        Returns:
            相似度分数，范围0-1
        """
        try:
            # 简单的文本相似度计算，使用余弦相似度
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity

            # 检查文本是否为空
            if not text1 or not text2:
                return 0.0

            # 计算TF-IDF向量
            vectorizer = TfidfVectorizer(stop_words='english', max_features=1000)
            tfidf_matrix = vectorizer.fit_transform([text1, text2])

            # 计算余弦相似度
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            return float(similarity)
        except ImportError:
            # 如果sklearn不可用，使用简单的编辑距离算法
            return self._calculate_edit_distance_similarity(text1, text2)
        except Exception as e:
            logger.error(f"计算文本相似度失败: {e}")
            # 出错时使用编辑距离作为备选
            return self._calculate_edit_distance_similarity(text1, text2)

    def _calculate_edit_distance_similarity(self, text1: str, text2: str) -> float:
        """
        使用编辑距离计算文本相似度

        Args:
            text1: 第一个文本
            text2: 第二个文本

        Returns:
            相似度分数，范围0-1
        """
        from difflib import SequenceMatcher

        if not text1 or not text2:
            return 0.0

        matcher = SequenceMatcher(None, text1, text2)
        similarity = matcher.ratio()
        return similarity

    def check_similar_files(self, file_path: str, text_content: str) -> List[Dict[str, Any]]:
        """
        检查是否存在内容相似的文件

        Args:
            file_path: 文件路径
            text_content: 文件的文本内容

        Returns:
            相似文件列表，每个元素包含文档信息和相似度
        """
        similar_files = []
        
        try:
            # 检查文件大小，跳过过大的文件
            file_size = os.path.getsize(file_path)
            if file_size > self.max_file_size_for_similarity:
                logger.info(f"文件 {file_path} 过大 ({file_size} bytes)，跳过相似度检查")
                return similar_files
            
            # 从数据库获取所有文档，批量处理
            with self.db_manager.get_session() as session:
                # 获取所有文档，按创建时间倒序，优先检查最近的文件
                documents = session.query(Document).order_by(Document.created_at.desc()).all()
                
                # 批量处理
                for i in range(0, len(documents), self.batch_size):
                    batch = documents[i:i + self.batch_size]
                    for doc in batch:
                        # 跳过空内容的文档
                        if not doc.extracted_text:
                            continue
                        
                        # 计算相似度
                        similarity = self.calculate_text_similarity(text_content, doc.extracted_text)
                        
                        # 如果相似度达到阈值，添加到相似文件列表
                        if similarity >= self.similarity_threshold:
                            similar_files.append({
                                "doc_id": doc.id,
                                "filename": doc.filename,
                                "similarity": similarity,
                                "created_at": doc.created_at
                            })
                            logger.info(f"发现相似文件: {doc.filename} (相似度: {similarity:.2f})")
                            
                            # 找到一个相似文件后可以提前返回，提高性能
                            if len(similar_files) >= 3:  # 最多返回3个相似文件
                                return similar_files
        except Exception as e:
            logger.error(f"检查相似文件失败: {e}")
        
        return similar_files
