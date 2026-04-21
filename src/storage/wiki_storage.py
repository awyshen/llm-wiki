"""
Wiki存储管理
"""

from typing import Optional, Dict, Any, List
import os
import hashlib

from ..core.config import Config, get_config
from ..core.logger import get_logger

logger = get_logger(__name__)


class WikiPageData:
    """Wiki页面数据"""

    def __init__(
        self,
        title: str,
        content: str,
        summary: str = "",
        category: str = "未分类",
        tags: List[str] = None,
        metadata: Dict[str, Any] = None,
    ):
        self.title = title
        self.content = content
        self.summary = summary
        self.category = category
        self.tags = tags or []
        self.metadata = metadata or {}


class WikiStorage:
    """Wiki存储管理"""

    def __init__(self, config: Optional[Config] = None):
        self.config = config or get_config()
        self.wiki_dir = self.config.wiki_dir
        self.articles_dir = os.path.join(self.wiki_dir, "articles")
        self.entities_dir = os.path.join(self.wiki_dir, "entities")
        self.indices_dir = os.path.join(self.wiki_dir, "indices")

        # 创建必要的目录
        for directory in [
            self.wiki_dir,
            self.articles_dir,
            self.entities_dir,
            self.indices_dir,
        ]:
            os.makedirs(directory, exist_ok=True)

    def save_page(self, page_data: WikiPageData, page_type: str = "article") -> str:
        """
        保存Wiki页面

        Args:
            page_data: Wiki页面数据
            page_type: 页面类型 (article, entity, index)

        Returns:
            文件路径
        """
        # 确定保存目录
        if page_type == "article":
            save_dir = self.articles_dir
        elif page_type == "entity":
            save_dir = self.entities_dir
        elif page_type == "index":
            save_dir = self.indices_dir
        else:
            save_dir = self.articles_dir

        # 生成文件名
        slug = self._slugify(page_data.title)
        file_path = os.path.join(save_dir, f"{slug}.md")

        # 生成Markdown内容
        content = f"# {page_data.title}\n\n"
        content += f"## 摘要\n{page_data.summary}\n\n"
        content += f"## 内容\n{page_data.content}\n\n"
        content += f"## 分类\n{page_data.category}\n\n"
        if page_data.tags:
            content += f"## 标签\n{', '.join(page_data.tags)}\n\n"
        if page_data.metadata:
            content += f"## 元数据\n{str(page_data.metadata)}\n"

        # 保存文件
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            logger.info(f"保存Wiki页面: {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"保存Wiki页面失败: {e}")
            return ""

    def _slugify(self, text: str) -> str:
        """
        生成slug

        Args:
            text: 文本

        Returns:
            slug
        """
        # 移除特殊字符，替换空格为下划线
        slug = "".join(c if c.isalnum() else "_" for c in text)
        # 移除多余的下划线
        slug = "_".join(filter(None, slug.split("_")))
        # 转换为小写
        slug = slug.lower()
        return slug
