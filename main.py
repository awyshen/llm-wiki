#!/usr/bin/env python3
"""
LLM Wiki 主入口文件

提供命令行接口，支持初始化、导入、处理、搜索、启动服务等操作。
"""

import argparse
import sys
import os
from typing import Optional

from src.core.config import load_config, get_config
from src.core.logger import get_logger
from src.collect.file_collector import FileCollector
from src.process.knowledge_processor import KnowledgeProcessor
from src.api.app import create_app
from src.interface.gradio_ui import run_webui
from src.storage.database import get_db_manager
from src.storage.models import Base
from src.search.advanced_search import AdvancedSearch

logger = get_logger(__name__)


def init_system():
    """
    初始化系统
    """
    logger.info("正在初始化系统...")

    # 初始化数据库
    db_manager = get_db_manager()
    Base.metadata.create_all(bind=db_manager.engine)
    logger.info("数据库初始化完成")

    # 创建必要的目录
    config = get_config()
    data_dir = config.data_dir
    wiki_dir = config.wiki_dir

    # 确保数据目录存在
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(os.path.join(data_dir, "raw"), exist_ok=True)
    os.makedirs(os.path.join(data_dir, "wiki"), exist_ok=True)
    os.makedirs(os.path.join(data_dir, "wiki", "articles"), exist_ok=True)
    os.makedirs(os.path.join(data_dir, "wiki", "entities"), exist_ok=True)
    os.makedirs(os.path.join(data_dir, "wiki", "indices"), exist_ok=True)
    os.makedirs(os.path.join(data_dir, "backup"), exist_ok=True)

    logger.info("系统初始化完成")


def import_documents(path: str):
    """
    导入文档

    Args:
        path: 文件或目录路径
    """
    logger.info(f"正在导入文档: {path}")

    collector = FileCollector()

    if os.path.isfile(path):
        # 导入单个文件
        collector.import_file(path)
    elif os.path.isdir(path):
        # 导入目录
        collector.import_directory(path)
    else:
        logger.error(f"路径不存在: {path}")
        return

    logger.info("文档导入完成")


def process_documents():
    """
    处理待处理的文档
    """
    logger.info("正在处理文档...")

    processor = KnowledgeProcessor()
    stats = processor.process_pending_documents()

    logger.info(f"文档处理完成: {stats}")


def search_knowledge(query: str):
    """
    搜索知识库

    Args:
        query: 搜索关键词
    """
    logger.info(f"正在搜索: {query}")

    try:
        searcher = AdvancedSearch()
        results = searcher.search(query)
        
        logger.info(f"搜索完成，找到 {len(results)} 个结果")
        
        # 打印搜索结果
        print(f"\n搜索结果 ({len(results)}):")
        print("=" * 80)
        
        for i, result in enumerate(results[:10], 1):  # 只显示前10个结果
            print(f"{i}. [{result['type']}] {result['title']}")
            if 'content' in result and result['content']:
                print(f"   摘要: {result['content']}")
            if 'filename' in result:
                print(f"   文件: {result['filename']}")
            print("-" * 80)
            
        if len(results) > 10:
            print(f"... 还有 {len(results) - 10} 个结果未显示")
            
    except Exception as e:
        logger.error(f"搜索失败: {e}")
        print(f"搜索失败: {str(e)}")


def start_api():
    """
    启动API服务
    """
    logger.info("正在启动API服务...")

    app = create_app()
    config = get_config()

    # 强制使用 0.0.0.0 作为主机，确保绑定到所有网络接口
    host = "0.0.0.0"
    port = config.app.get("port", 8000)

    app.run(host=host, port=port, debug=config.app.get("debug", False))


def start_webui():
    """
    启动Web界面
    """
    logger.info("正在启动Web界面...")
    run_webui()


def main():
    """
    主函数
    """
    parser = argparse.ArgumentParser(description="LLM Wiki 命令行工具")

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # 初始化命令
    init_parser = subparsers.add_parser("init", help="初始化系统")

    # 导入命令
    import_parser = subparsers.add_parser("import", help="导入文档")
    import_parser.add_argument("path", help="文件或目录路径")

    # 处理命令
    process_parser = subparsers.add_parser("process", help="处理待处理的文档")

    # 搜索命令
    search_parser = subparsers.add_parser("search", help="搜索知识库")
    search_parser.add_argument("query", help="搜索关键词")

    # API服务命令
    api_parser = subparsers.add_parser("api", help="启动API服务")

    # Web界面命令
    webui_parser = subparsers.add_parser("webui", help="启动Web界面")

    args = parser.parse_args()

    if args.command == "init":
        init_system()
    elif args.command == "import":
        import_documents(args.path)
    elif args.command == "process":
        process_documents()
    elif args.command == "search":
        search_knowledge(args.query)
    elif args.command == "api":
        start_api()
    elif args.command == "webui":
        start_webui()
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
