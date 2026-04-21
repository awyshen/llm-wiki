"""
性能监控

监控文档处理的性能指标，评估优化效果。
"""

from typing import Dict, Any, Optional
import time
import psutil
import os
import statistics
from datetime import datetime

from .logger import get_logger

logger = get_logger(__name__)


class PerformanceMonitor:
    """性能监控"""

    def __init__(self):
        self.metrics = {}
        self.start_time = None
        self.process = psutil.Process(os.getpid())

    def start(self, operation: str) -> None:
        """
        开始监控操作

        Args:
            operation: 操作名称
        """
        if operation not in self.metrics:
            self.metrics[operation] = []

        self.start_time = {
            "time": time.time(),
            "memory": self.process.memory_info().rss,
            "operation": operation,
        }

        logger.debug(f"开始监控操作: {operation}")

    def stop(self, operation: str) -> Dict[str, Any]:
        """
        停止监控操作

        Args:
            operation: 操作名称

        Returns:
            性能指标
        """
        if not self.start_time or self.start_time["operation"] != operation:
            logger.warning(f"未开始监控操作: {operation}")
            return {}

        end_time = time.time()
        end_memory = self.process.memory_info().rss

        metrics = {
            "operation": operation,
            "duration": end_time - self.start_time["time"],
            "memory_used": end_memory - self.start_time["memory"],
            "start_time": self.start_time["time"],
            "end_time": end_time,
            "timestamp": datetime.utcnow().isoformat(),
        }

        self.metrics[operation].append(metrics)

        logger.debug(
            f"操作完成: {operation}, 耗时: {metrics['duration']:.2f}秒, 内存使用: {metrics['memory_used']/1024/1024:.2f}MB"
        )

        self.start_time = None
        return metrics

    def get_metrics(self, operation: Optional[str] = None) -> Dict[str, Any]:
        """
        获取性能指标

        Args:
            operation: 操作名称，None表示所有操作

        Returns:
            性能指标
        """
        if operation:
            if operation not in self.metrics:
                return {}
            return {
                "operation": operation,
                "count": len(self.metrics[operation]),
                "avg_duration": (
                    statistics.mean([m["duration"] for m in self.metrics[operation]])
                    if self.metrics[operation]
                    else 0
                ),
                "max_duration": (
                    max([m["duration"] for m in self.metrics[operation]])
                    if self.metrics[operation]
                    else 0
                ),
                "min_duration": (
                    min([m["duration"] for m in self.metrics[operation]])
                    if self.metrics[operation]
                    else 0
                ),
                "avg_memory_used": (
                    statistics.mean([m["memory_used"] for m in self.metrics[operation]])
                    if self.metrics[operation]
                    else 0
                ),
                "details": self.metrics[operation],
            }
        else:
            all_metrics = {}
            for op, data in self.metrics.items():
                all_metrics[op] = {
                    "count": len(data),
                    "avg_duration": (
                        statistics.mean([m["duration"] for m in data]) if data else 0
                    ),
                    "max_duration": max([m["duration"] for m in data]) if data else 0,
                    "min_duration": min([m["duration"] for m in data]) if data else 0,
                    "avg_memory_used": (
                        statistics.mean([m["memory_used"] for m in data]) if data else 0
                    ),
                }
            return all_metrics

    def reset(self, operation: Optional[str] = None) -> None:
        """
        重置性能指标

        Args:
            operation: 操作名称，None表示所有操作
        """
        if operation:
            if operation in self.metrics:
                del self.metrics[operation]
        else:
            self.metrics.clear()

        logger.debug(f"重置性能指标: {operation or '所有操作'}")

    def log_summary(self) -> None:
        """
        记录性能摘要
        """
        all_metrics = self.get_metrics()

        if not all_metrics:
            logger.info("没有性能指标记录")
            return

        logger.info("性能监控摘要:")
        for operation, metrics in all_metrics.items():
            logger.info(f"  {operation}:")
            logger.info(f"    执行次数: {metrics['count']}")
            logger.info(f"    平均耗时: {metrics['avg_duration']:.2f}秒")
            logger.info(f"    最大耗时: {metrics['max_duration']:.2f}秒")
            logger.info(f"    最小耗时: {metrics['min_duration']:.2f}秒")
            logger.info(
                f"    平均内存使用: {metrics['avg_memory_used']/1024/1024:.2f}MB"
            )


# 全局性能监控实例
performance_monitor = PerformanceMonitor()


def monitor_performance(operation: str):
    """
    性能监控装饰器

    Args:
        operation: 操作名称
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            performance_monitor.start(operation)
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                performance_monitor.stop(operation)

        return wrapper

    return decorator
