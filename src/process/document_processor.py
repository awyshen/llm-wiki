"""
文档处理器

优化文档分块和提取算法，提高处理效率。
"""

from typing import List, Dict, Any, Optional
import re
import hashlib
import os
from functools import lru_cache

from ..core.config import Config, get_config
from ..core.logger import get_logger
from ..core.exceptions import ProcessingError
from ..core.error_handler import handle_processing_exceptions
from ..core.error_monitor import record_error

logger = get_logger(__name__)


class DocumentProcessor:
    """文档处理器"""

    def __init__(self, config: Optional[Config] = None):
        self.config = config or get_config()
        self.chunk_size = self.config.processing.extraction.get("max_chunk_size", 2000)
        self.overlap_size = self.config.processing.extraction.get("overlap_size", 200)
        self.min_chunk_size = self.config.processing.extraction.get(
            "min_chunk_size", 100
        )
        self.cache_dir = os.path.join(
            os.path.join(self.config.data_dir, "temp"), "extraction_cache"
        )
        os.makedirs(self.cache_dir, exist_ok=True)

    @handle_processing_exceptions(retry_count=1, default_return="")
    def extract_text(self, file_path: str, file_type: str) -> str:
        """
        提取文档文本

        Args:
            file_path: 文件路径
            file_type: 文件类型

        Returns:
            提取的文本
        """
        # 生成缓存键
        cache_key = self._generate_cache_key(file_path)
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.txt")

        # 检查缓存
        if os.path.exists(cache_file):
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    logger.info(f"从缓存中读取文本: {file_path}")
                    return f.read()
            except Exception as e:
                logger.warning(f"读取缓存失败: {e}")

        # 提取文本
        text = ""
        try:
            if file_type == "pdf":
                import PyPDF2

                with open(file_path, "rb") as f:
                    reader = PyPDF2.PdfReader(f)
                    text = "\n".join([page.extract_text() for page in reader.pages])
            elif file_type == "docx":
                from docx import Document

                doc = Document(file_path)
                text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            elif file_type == "md" or file_type == "txt":
                with open(file_path, "r", encoding="utf-8") as f:
                    text = f.read()
            elif file_type == "html":
                from bs4 import BeautifulSoup

                with open(file_path, "r", encoding="utf-8") as f:
                    soup = BeautifulSoup(f, "html.parser")
                    text = soup.get_text()
            else:
                error = ProcessingError(
                    f"不支持的文件类型: {file_type}", details={"file_type": file_type}
                )
                record_error(error, {"file_path": file_path})
                logger.warning(f"不支持的文件类型: {file_type}")
        except Exception as e:
            error = ProcessingError(f"提取文本失败 {file_path}: {str(e)}", cause=e)
            record_error(error, {"file_path": file_path, "file_type": file_type})
            raise

        # 保存缓存
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                f.write(text)
        except Exception as e:
            logger.warning(f"保存缓存失败: {e}")

        return text

    @handle_processing_exceptions(default_return=[])
    def chunk_document(self, text: str) -> List[str]:
        """
        智能分块文档

        Args:
            text: 文档文本

        Returns:
            分块列表
        """
        if not text:
            return []

        # 基于段落和句子进行分块
        chunks = []
        current_chunk = []
        current_size = 0

        # 按段落分割
        paragraphs = re.split(r"\n\s*\n", text)

        for paragraph in paragraphs:
            if not paragraph.strip():
                continue

            # 按句子分割段落
            sentences = re.split(r"(?<=[。！？.!?])\s*", paragraph)

            for sentence in sentences:
                if not sentence.strip():
                    continue

                sentence_size = len(sentence)

                # 如果当前块加上这个句子会超过最大块大小
                if current_size + sentence_size > self.chunk_size:
                    # 如果当前块不为空，添加到结果中
                    if current_chunk:
                        chunk_text = " ".join(current_chunk)
                        if len(chunk_text) >= self.min_chunk_size:
                            chunks.append(chunk_text)

                        # 重置当前块，保留重叠部分
                        if self.overlap_size > 0 and current_chunk:
                            overlap_text = " ".join(current_chunk[-self.overlap_size :])
                            current_chunk = [overlap_text, sentence]
                            current_size = len(overlap_text) + sentence_size
                        else:
                            current_chunk = [sentence]
                            current_size = sentence_size
                    else:
                        # 如果当前块为空，直接添加句子
                        current_chunk = [sentence]
                        current_size = sentence_size
                else:
                    # 添加句子到当前块
                    current_chunk.append(sentence)
                    current_size += sentence_size

        # 添加最后一个块
        if current_chunk:
            chunk_text = " ".join(current_chunk)
            if len(chunk_text) >= self.min_chunk_size:
                chunks.append(chunk_text)

        return chunks

    @handle_processing_exceptions(default_return=[])
    def batch_process(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        批量处理文档

        Args:
            documents: 文档列表，每个文档包含file_path和file_type

        Returns:
            处理后的文档列表，每个文档包含text和chunks
        """
        results = []

        for doc in documents:
            try:
                file_path = doc.get("file_path")
                file_type = doc.get("file_type", file_path.split(".")[-1].lower())

                # 提取文本
                text = self.extract_text(file_path, file_type)

                # 分块
                chunks = self.chunk_document(text)

                results.append(
                    {
                        "file_path": file_path,
                        "text": text,
                        "chunks": chunks,
                        "success": True,
                    }
                )
            except Exception as e:
                error = ProcessingError(
                    f"处理文档失败 {doc.get('file_path')}: {str(e)}", cause=e
                )
                record_error(error, {"file_path": doc.get("file_path")})
                results.append(
                    {
                        "file_path": doc.get("file_path"),
                        "text": "",
                        "chunks": [],
                        "success": False,
                        "error": str(e),
                    }
                )

        return results

    def _generate_cache_key(self, file_path: str) -> str:
        """
        生成缓存键

        Args:
            file_path: 文件路径

        Returns:
            缓存键
        """
        # 组合文件路径和修改时间
        mtime = os.path.getmtime(file_path)
        key = f"{file_path}:{mtime}"
        return hashlib.md5(key.encode()).hexdigest()

    @lru_cache(maxsize=1000)
    def get_chunk_embedding(self, chunk: str) -> Optional[List[float]]:
        """
        获取块的嵌入向量（缓存版）

        Args:
            chunk: 文本块

        Returns:
            嵌入向量
        """
        try:
            from sentence_transformers import SentenceTransformer

            model = SentenceTransformer(
                self.config.vector_db.get(
                    "embedding_model", "sentence-transformers/all-MiniLM-L6-v2"
                )
            )
            return model.encode(chunk).tolist()
        except Exception as e:
            logger.error(f"生成嵌入向量失败: {e}")
            return None
