"""
Wiki存储管理
"""

from typing import Optional, Dict, Any, List
import os
import hashlib
from datetime import datetime

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

    def update_index(self) -> str:
        """
        更新Wiki索引文件（index.md）

        Returns:
            文件路径
        """
        index_path = os.path.join(self.wiki_dir, "index.md")
        
        # 收集所有Wiki页面
        pages = []
        
        # 收集文章页面
        for filename in os.listdir(self.articles_dir):
            if filename.endswith(".md"):
                file_path = os.path.join(self.articles_dir, filename)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    # 提取标题
                    title = filename.replace(".md", "").replace("_", " ").title()
                    # 提取摘要
                    summary = ""
                    if "## 摘要\n" in content:
                        summary_start = content.find("## 摘要\n") + len("## 摘要\n")
                        summary_end = content.find("\n\n", summary_start)
                        if summary_end != -1:
                            summary = content[summary_start:summary_end]
                    # 提取分类
                    category = "未分类"
                    if "## 分类\n" in content:
                        category_start = content.find("## 分类\n") + len("## 分类\n")
                        category_end = content.find("\n\n", category_start)
                        if category_end != -1:
                            category = content[category_start:category_end]
                    pages.append({
                        "title": title,
                        "path": f"articles/{filename}",
                        "summary": summary,
                        "category": category
                    })
                except Exception as e:
                    logger.error(f"读取Wiki页面失败 {file_path}: {e}")
        
        # 按分类分组
        categories = {}
        for page in pages:
            category = page["category"]
            if category not in categories:
                categories[category] = []
            categories[category].append(page)
        
        # 生成索引内容
        content = "# Wiki 索引\n\n"
        content += "## 目录\n\n"
        
        for category, category_pages in categories.items():
            content += f"### {category}\n\n"
            for page in category_pages:
                content += f"- [{page['title']}]({page['path']}) - {page['summary'][:100]}...\n\n"
        
        # 保存索引文件
        try:
            with open(index_path, "w", encoding="utf-8") as f:
                f.write(content)
            logger.info(f"更新Wiki索引: {index_path}")
            return index_path
        except Exception as e:
            logger.error(f"更新Wiki索引失败: {e}")
            return ""

    def add_to_log(self, operation: str, details: str) -> str:
        """
        添加操作记录到日志文件（log.md）

        Args:
            operation: 操作类型
            details: 操作详情

        Returns:
            文件路径
        """
        log_path = os.path.join(self.wiki_dir, "log.md")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 生成日志条目
        log_entry = f"## {timestamp} - {operation}\n\n{details}\n\n"
        
        # 读取现有日志
        existing_content = ""
        if os.path.exists(log_path):
            try:
                with open(log_path, "r", encoding="utf-8") as f:
                    existing_content = f.read()
            except Exception as e:
                logger.error(f"读取日志文件失败: {e}")
        
        # 生成新日志内容（新条目在前）
        new_content = f"# Wiki 操作日志\n\n{log_entry}{existing_content}"
        
        # 保存日志文件
        try:
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            logger.info(f"添加操作记录: {log_path}")
            return log_path
        except Exception as e:
            logger.error(f"添加操作记录失败: {e}")
            return ""

    def check_wiki_health(self) -> Dict[str, Any]:
        """
        检查Wiki健康状态

        Returns:
            健康检查结果
        """
        health_status = {
            "total_pages": 0,
            "valid_pages": 0,
            "invalid_pages": 0,
            "errors": [],
            "warnings": [],
            "suggestions": []
        }
        
        # 检查所有Wiki页面
        for root, dirs, files in os.walk(self.wiki_dir):
            for file in files:
                if file.endswith(".md") and file not in ["index.md", "log.md"]:
                    file_path = os.path.join(root, file)
                    health_status["total_pages"] += 1
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read()
                        # 检查基本结构
                        if "# " not in content:
                            health_status["warnings"].append(f"页面 {file} 缺少标题")
                            health_status["suggestions"].append(f"为页面 {file} 添加标题")
                        if "## 摘要\n" not in content:
                            health_status["warnings"].append(f"页面 {file} 缺少摘要")
                            health_status["suggestions"].append(f"为页面 {file} 添加摘要部分")
                        if "## 内容\n" not in content:
                            health_status["warnings"].append(f"页面 {file} 缺少内容部分")
                            health_status["suggestions"].append(f"为页面 {file} 添加内容部分")
                        
                        # 检查内容质量
                        if len(content) < 100:
                            health_status["warnings"].append(f"页面 {file} 内容过短")
                            health_status["suggestions"].append(f"丰富页面 {file} 的内容")
                        
                        # 检查链接有效性
                        import re
                        links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', content)
                        for link_text, link_url in links:
                            if not link_url.startswith("http://") and not link_url.startswith("https://") and not os.path.exists(os.path.join(os.path.dirname(file_path), link_url)):
                                health_status["warnings"].append(f"页面 {file} 中的链接 {link_url} 无效")
                                health_status["suggestions"].append(f"修复页面 {file} 中的无效链接 {link_url}")
                        
                        health_status["valid_pages"] += 1
                    except Exception as e:
                        health_status["invalid_pages"] += 1
                        health_status["errors"].append(f"页面 {file} 读取失败: {str(e)}")
                        health_status["suggestions"].append(f"修复页面 {file} 的读取错误: {str(e)}")
        
        # 检查索引文件
        index_path = os.path.join(self.wiki_dir, "index.md")
        if not os.path.exists(index_path):
            health_status["warnings"].append("缺少索引文件 index.md")
            health_status["suggestions"].append("运行更新索引操作以创建index.md文件")
        
        # 检查日志文件
        log_path = os.path.join(self.wiki_dir, "log.md")
        if not os.path.exists(log_path):
            health_status["warnings"].append("缺少日志文件 log.md")
            health_status["suggestions"].append("执行任何Wiki操作以自动创建log.md文件")
        
        # 检查目录结构
        required_dirs = ["articles", "entities", "indices"]
        for dir_name in required_dirs:
            dir_path = os.path.join(self.wiki_dir, dir_name)
            if not os.path.exists(dir_path):
                health_status["warnings"].append(f"缺少目录 {dir_name}")
                health_status["suggestions"].append(f"创建目录 {dir_name}")
        
        logger.info(f"Wiki健康检查完成: {health_status}")
        return health_status

    def start_periodic_health_check(self, interval: int = 3600):
        """
        启动定期健康检查

        Args:
            interval: 检查间隔（秒），默认1小时
        """
        import threading
        
        def periodic_check():
            while True:
                logger.info("执行定期Wiki健康检查")
                health_status = self.check_wiki_health()
                
                # 记录健康检查结果到日志
                if health_status["errors"] or health_status["warnings"]:
                    log_details = f"定期健康检查发现问题:\n"
                    log_details += f"错误: {health_status['errors']}\n"
                    log_details += f"警告: {health_status['warnings']}\n"
                    log_details += f"建议: {health_status['suggestions']}\n"
                    self.add_to_log("定期健康检查", log_details)
                
                import time
                time.sleep(interval)
        
        # 启动后台线程
        check_thread = threading.Thread(target=periodic_check, daemon=True)
        check_thread.start()
        logger.info(f"定期健康检查已启动，间隔: {interval}秒")
