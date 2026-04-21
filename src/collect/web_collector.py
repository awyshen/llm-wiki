"""
网络内容收集器

负责从网络上收集内容，比如网页、博客文章等。
"""

import os
import uuid
import requests
from datetime import datetime
from typing import List, Optional, Dict, Any
from bs4 import BeautifulSoup

from ..core.config import get_config
from ..core.logger import get_logger
from ..core.error_handler import ErrorHandler
from ..storage.database import get_db_manager
from ..storage.models import Document, ProcessingStatus

logger = get_logger(__name__)


class WebCollector:
    """网络内容收集器"""

    def __init__(self):
        """初始化网络内容收集器"""
        self.config = get_config()
        self.db_manager = get_db_manager()
        self.raw_dir = os.path.join(self.config.data_dir, "raw")
        # 确保原始文件目录存在
        os.makedirs(self.raw_dir, exist_ok=True)

        # 请求头
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    @ErrorHandler.handle_llm_exceptions()
    def import_url(self, url: str) -> str:
        """
        导入单个URL的内容

        Args:
            url: 网页URL

        Returns:
            文档ID

        Raises:
            requests.RequestException: 网络请求失败
            ValueError: URL格式不正确
        """
        if not url.startswith(('http://', 'https://')):
            raise ValueError(f"URL格式不正确: {url}")

        # 生成唯一的文档ID
        doc_id = str(uuid.uuid4())

        try:
            # 获取网页内容
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()  # 检查请求是否成功

            # 解析网页内容
            soup = BeautifulSoup(response.content, 'html.parser')

            # 提取标题
            title = self._extract_title(soup)
            if not title:
                title = url

            # 提取正文内容
            content = self._extract_content(soup)

            # 保存到数据库
            with self.db_manager.get_session() as session:
                document = Document(
                    id=doc_id,
                    title=title,
                    filename=f"web_{doc_id}.html",
                    file_path=url,
                    file_type="html",
                    extracted_text=content,
                    processing_status=ProcessingStatus.PENDING.value,
                    created_at=datetime.utcnow()
                )
                session.add(document)
                session.commit()

            # 保存网页内容到文件
            file_path = os.path.join(self.raw_dir, f"web_{doc_id}.html")
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(response.text)

            logger.info(f"成功导入URL: {url}, 文档ID: {doc_id}")
            return doc_id
        except Exception as e:
            logger.error(f"导入URL失败: {url}, 错误: {str(e)}")
            raise

    @ErrorHandler.handle_llm_exceptions()
    def import_urls(self, urls: List[str]) -> List[str]:
        """
        导入多个URL的内容

        Args:
            urls: URL列表

        Returns:
            导入的文档ID列表
        """
        imported_doc_ids = []

        for url in urls:
            try:
                doc_id = self.import_url(url)
                imported_doc_ids.append(doc_id)
            except Exception as e:
                logger.error(f"导入URL失败: {url}, 错误: {str(e)}")
                # 继续处理其他URL
                continue

        logger.info(f"成功导入 {len(imported_doc_ids)} 个URL")
        return imported_doc_ids

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """
        从网页中提取标题

        Args:
            soup: BeautifulSoup对象

        Returns:
            标题字符串
        """
        # 尝试从title标签获取
        title_tag = soup.find('title')
        if title_tag and title_tag.text.strip():
            return title_tag.text.strip()

        # 尝试从h1标签获取
        h1_tag = soup.find('h1')
        if h1_tag and h1_tag.text.strip():
            return h1_tag.text.strip()

        # 尝试从meta标签获取
        meta_title = soup.find('meta', {'name': 'title'})
        if meta_title and meta_title.get('content'):
            return meta_title.get('content').strip()

        meta_og_title = soup.find('meta', {'property': 'og:title'})
        if meta_og_title and meta_og_title.get('content'):
            return meta_og_title.get('content').strip()

        return ""

    def _extract_content(self, soup: BeautifulSoup) -> str:
        """
        从网页中提取正文内容

        Args:
            soup: BeautifulSoup对象

        Returns:
            正文内容字符串
        """
        # 移除脚本和样式标签
        for script in soup(['script', 'style']):
            script.decompose()

        # 尝试从常见的内容容器中提取
        content_containers = [
            soup.find('main'),
            soup.find('article'),
            soup.find('div', {'class': 'content'}),
            soup.find('div', {'class': 'article'}),
            soup.find('div', {'class': 'post'}),
            soup.find('div', {'id': 'content'}),
            soup.find('div', {'id': 'article'}),
            soup.find('div', {'id': 'post'}),
        ]

        for container in content_containers:
            if container:
                text = container.get_text(separator='\n', strip=True)
                if text:
                    return text

        # 如果没有找到特定容器，返回整个网页的文本
        text = soup.get_text(separator='\n', strip=True)
        return text

    def validate_url(self, url: str) -> bool:
        """
        验证URL是否有效

        Args:
            url: URL字符串

        Returns:
            URL是否有效
        """
        if not url.startswith(('http://', 'https://')):
            return False

        try:
            response = requests.head(url, headers=self.headers, timeout=10)
            return response.status_code < 400
        except Exception:
            return False

    def get_url_info(self, url: str) -> Optional[Dict[str, Any]]:
        """
        获取URL的信息

        Args:
            url: URL字符串

        Returns:
            URL信息字典，包含标题、状态码等
        """
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')
            title = self._extract_title(soup)

            return {
                'url': url,
                'title': title,
                'status_code': response.status_code,
                'content_type': response.headers.get('Content-Type', ''),
                'content_length': response.headers.get('Content-Length', '')
            }
        except Exception as e:
            logger.error(f"获取URL信息失败: {url}, 错误: {str(e)}")
            return None
