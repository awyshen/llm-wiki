"""
文件系统监控器

负责监控文件系统的变化，当有新文件添加时自动导入到系统。
"""

import os
import time
import threading
from typing import List, Optional, Callable

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

from ..core.config import get_config
from ..core.logger import get_logger
from .file_collector import FileCollector

logger = get_logger(__name__)


class FileChangeHandler(FileSystemEventHandler):
    """文件系统变化处理器"""

    def __init__(self, collector: FileCollector, supported_extensions: set):
        """
        初始化文件变化处理器

        Args:
            collector: 文件收集器实例
            supported_extensions: 支持的文件扩展名集合
        """
        self.collector = collector
        self.supported_extensions = supported_extensions

    def on_created(self, event: FileSystemEvent):
        """
        当文件或目录被创建时调用

        Args:
            event: 文件系统事件
        """
        if not event.is_directory:
            file_path = event.src_path
            file_ext = os.path.splitext(file_path)[1].lstrip('.').lower()
            if file_ext in self.supported_extensions:
                try:
                    logger.info(f"检测到新文件: {file_path}")
                    self.collector.import_file(file_path)
                    logger.info(f"成功导入新文件: {file_path}")
                except Exception as e:
                    logger.error(f"导入新文件失败: {file_path}, 错误: {str(e)}")

    def on_modified(self, event: FileSystemEvent):
        """
        当文件或目录被修改时调用

        Args:
            event: 文件系统事件
        """
        # 可以在这里处理文件修改的逻辑
        pass

    def on_deleted(self, event: FileSystemEvent):
        """
        当文件或目录被删除时调用

        Args:
            event: 文件系统事件
        """
        # 可以在这里处理文件删除的逻辑
        pass


class FileWatcher:
    """文件系统监控器"""

    def __init__(self):
        """初始化文件系统监控器"""
        self.config = get_config()
        self.collector = FileCollector()
        self.observer = None
        self.running = False
        self.thread = None

        # 支持的文件类型
        self.supported_extensions = {
            'md', 'txt', 'pdf', 'doc', 'docx', 'rtf', 'html', 'htm',
            'csv', 'xlsx', 'xls', 'ppt', 'pptx'
        }

        # 监控的目录
        self.monitored_dirs = []

    def add_monitored_directory(self, directory: str):
        """
        添加监控目录

        Args:
            directory: 要监控的目录路径

        Raises:
            ValueError: 目录不存在
        """
        if not os.path.exists(directory):
            raise ValueError(f"目录不存在: {directory}")

        if not os.path.isdir(directory):
            raise ValueError(f"路径不是目录: {directory}")

        if directory not in self.monitored_dirs:
            self.monitored_dirs.append(directory)
            logger.info(f"添加监控目录: {directory}")

    def remove_monitored_directory(self, directory: str):
        """
        移除监控目录

        Args:
            directory: 要移除的目录路径
        """
        if directory in self.monitored_dirs:
            self.monitored_dirs.remove(directory)
            logger.info(f"移除监控目录: {directory}")

    def start(self):
        """
        开始监控
        """
        if self.running:
            logger.warning("监控已经在运行中")
            return

        if not self.monitored_dirs:
            # 如果没有指定监控目录，默认监控原始文件目录
            raw_dir = os.path.join(self.config.data_dir, "raw")
            os.makedirs(raw_dir, exist_ok=True)
            self.add_monitored_directory(raw_dir)
            logger.info(f"未指定监控目录，默认监控: {raw_dir}")

        # 创建事件处理器
        event_handler = FileChangeHandler(self.collector, self.supported_extensions)

        # 创建观察者
        self.observer = Observer()

        # 为每个监控目录添加观察
        for directory in self.monitored_dirs:
            self.observer.schedule(event_handler, directory, recursive=True)

        # 启动观察者
        self.observer.start()
        self.running = True

        # 创建并启动监控线程
        self.thread = threading.Thread(target=self._monitor_loop)
        self.thread.daemon = True
        self.thread.start()

        logger.info(f"文件系统监控已启动，监控目录: {self.monitored_dirs}")

    def stop(self):
        """
        停止监控
        """
        if not self.running:
            logger.warning("监控未运行")
            return

        self.running = False

        if self.observer:
            self.observer.stop()
            self.observer.join(timeout=5)
            self.observer = None

        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
            self.thread = None

        logger.info("文件系统监控已停止")

    def _monitor_loop(self):
        """
        监控循环
        """
        while self.running:
            time.sleep(1)

    def is_running(self) -> bool:
        """
        检查监控是否正在运行

        Returns:
            是否正在运行
        """
        return self.running

    def get_monitored_directories(self) -> List[str]:
        """
        获取当前监控的目录列表

        Returns:
            监控的目录列表
        """
        return self.monitored_dirs.copy()


# 全局文件监控器实例
file_watcher = FileWatcher()


def get_file_watcher() -> FileWatcher:
    """
    获取文件监控器实例

    Returns:
        文件监控器实例
    """
    return file_watcher
