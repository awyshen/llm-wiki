"""
日志管理
"""

import logging
import os
from datetime import datetime
from typing import Dict, Any, Optional


class EnhancedFormatter(logging.Formatter):
    """增强的日志格式化器"""

    def format(self, record: logging.LogRecord) -> str:
        """
        格式化日志记录

        Args:
            record: 日志记录

        Returns:
            格式化后的日志字符串
        """
        # 添加额外的上下文信息
        if hasattr(record, "extra") and isinstance(record.extra, dict):
            extra_info = " | ".join([f"{k}={v}" for k, v in record.extra.items()])
            record.msg = f"{record.msg} | {extra_info}"

        return super().format(record)


def get_logger(name: str, log_level: int = logging.INFO) -> logging.Logger:
    """
    获取日志记录器

    Args:
        name: 日志记录器名称
        log_level: 日志级别

    Returns:
        日志记录器
    """
    # 创建日志目录
    log_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "logs",
    )
    os.makedirs(log_dir, exist_ok=True)

    # 创建日志文件名
    log_file = os.path.join(
        log_dir, f"llm-wiki_{datetime.now().strftime('%Y-%m-%d')}.log"
    )
    error_log_file = os.path.join(
        log_dir, f"llm-wiki_error_{datetime.now().strftime('%Y-%m-%d')}.log"
    )

    # 创建日志记录器
    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    # 避免重复添加处理器
    if not logger.handlers:
        # 创建文件处理器（所有级别）
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)

        # 创建错误文件处理器（仅错误及以上）
        error_file_handler = logging.FileHandler(error_log_file, encoding="utf-8")
        error_file_handler.setLevel(logging.ERROR)

        # 创建控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)

        # 创建格式化器
        formatter = EnhancedFormatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        # 设置格式化器
        file_handler.setFormatter(formatter)
        error_file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # 添加处理器
        logger.addHandler(file_handler)
        logger.addHandler(error_file_handler)
        logger.addHandler(console_handler)

    return logger


def log_with_context(
    logger: logging.Logger,
    level: int,
    message: str,
    extra: Optional[Dict[str, Any]] = None,
    exc_info: Optional[Exception] = None,
) -> None:
    """
    带上下文信息的日志记录

    Args:
        logger: 日志记录器
        level: 日志级别
        message: 日志消息
        extra: 额外的上下文信息
        exc_info: 异常信息
    """
    if extra:
        logger.log(level, message, extra={"extra": extra}, exc_info=exc_info)
    else:
        logger.log(level, message, exc_info=exc_info)


# 便捷函数
def debug(
    logger: logging.Logger,
    message: str,
    extra: Optional[Dict[str, Any]] = None,
    exc_info: Optional[Exception] = None,
) -> None:
    """记录调试级别日志"""
    log_with_context(logger, logging.DEBUG, message, extra, exc_info)


def info(
    logger: logging.Logger,
    message: str,
    extra: Optional[Dict[str, Any]] = None,
    exc_info: Optional[Exception] = None,
) -> None:
    """记录信息级别日志"""
    log_with_context(logger, logging.INFO, message, extra, exc_info)


def warning(
    logger: logging.Logger,
    message: str,
    extra: Optional[Dict[str, Any]] = None,
    exc_info: Optional[Exception] = None,
) -> None:
    """记录警告级别日志"""
    log_with_context(logger, logging.WARNING, message, extra, exc_info)


def error(
    logger: logging.Logger,
    message: str,
    extra: Optional[Dict[str, Any]] = None,
    exc_info: Optional[Exception] = None,
) -> None:
    """记录错误级别日志"""
    log_with_context(logger, logging.ERROR, message, extra, exc_info)


def critical(
    logger: logging.Logger,
    message: str,
    extra: Optional[Dict[str, Any]] = None,
    exc_info: Optional[Exception] = None,
) -> None:
    """记录严重错误级别日志"""
    log_with_context(logger, logging.CRITICAL, message, extra, exc_info)
