"""
错误监控和报告机制
"""

import time
import json
import os
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import threading

from .logger import get_logger
from .exceptions import BaseError

logger = get_logger(__name__)


class ErrorMonitor:
    """错误监控器"""

    def __init__(self):
        """初始化错误监控器"""
        self.error_store = []
        self.error_counter = Counter()
        self.error_by_time = defaultdict(list)
        self.lock = threading.RLock()
        self.report_dir = os.path.join(
            os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            ),
            "reports",
        )
        os.makedirs(self.report_dir, exist_ok=True)

    def record_error(
        self, error: BaseError, context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        记录错误

        Args:
            error: 错误对象
            context: 错误上下文
        """
        with self.lock:
            error_info = {
                "timestamp": datetime.now().isoformat(),
                "code": error.code,
                "message": error.message,
                "details": error.details,
                "cause": str(error.cause) if error.cause else None,
                "traceback": error.traceback,
                "context": context or {},
            }

            # 添加到错误存储
            self.error_store.append(error_info)

            # 更新错误计数器
            self.error_counter[error.code] += 1

            # 按时间分组
            time_key = datetime.now().strftime("%Y-%m-%d %H:%M")
            self.error_by_time[time_key].append(error_info)

            # 限制错误存储大小
            if len(self.error_store) > 10000:
                self.error_store = self.error_store[-10000:]

    def get_error_stats(self, days: int = 1) -> Dict[str, Any]:
        """
        获取错误统计信息

        Args:
            days: 统计天数

        Returns:
            错误统计信息
        """
        with self.lock:
            cutoff_time = datetime.now() - timedelta(days=days)
            recent_errors = [
                e
                for e in self.error_store
                if datetime.fromisoformat(e["timestamp"]) >= cutoff_time
            ]

            stats = {
                "total_errors": len(recent_errors),
                "errors_by_code": dict(Counter(e["code"] for e in recent_errors)),
                "errors_by_time": defaultdict(int),
            }

            # 按时间统计
            for error in recent_errors:
                time_key = datetime.fromisoformat(error["timestamp"]).strftime(
                    "%Y-%m-%d %H"
                )
                stats["errors_by_time"][time_key] += 1

            return stats

    def generate_error_report(self, days: int = 1) -> str:
        """
        生成错误报告

        Args:
            days: 报告天数

        Returns:
            报告文件路径
        """
        stats = self.get_error_stats(days)

        report_content = {
            "report_time": datetime.now().isoformat(),
            "report_period": f"最近{days}天",
            "stats": stats,
            "top_errors": [],
        }

        # 获取前10个最常见的错误
        top_errors = sorted(
            stats["errors_by_code"].items(), key=lambda x: x[1], reverse=True
        )[:10]
        for code, count in top_errors:
            # 查找该错误的示例
            example_error = next(
                (e for e in self.error_store if e["code"] == code), None
            )
            if example_error:
                report_content["top_errors"].append(
                    {
                        "code": code,
                        "count": count,
                        "example": {
                            "message": example_error["message"],
                            "cause": example_error["cause"],
                            "context": example_error["context"],
                        },
                    }
                )

        # 生成报告文件名
        report_file = os.path.join(
            self.report_dir,
            f"error_report_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.json",
        )

        # 写入报告文件
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report_content, f, ensure_ascii=False, indent=2)

        return report_file

    def get_error_trend(self, hours: int = 24) -> Dict[str, List[Dict[str, Any]]]:
        """
        获取错误趋势

        Args:
            hours: 趋势小时数

        Returns:
            错误趋势数据
        """
        with self.lock:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            trend_data = defaultdict(list)

            # 按小时统计
            for i in range(hours):
                hour_start = cutoff_time + timedelta(hours=i)
                hour_end = hour_start + timedelta(hours=1)
                hour_key = hour_start.strftime("%Y-%m-%d %H:00")

                # 统计该小时的错误
                hour_errors = [
                    e
                    for e in self.error_store
                    if datetime.fromisoformat(e["timestamp"]) >= hour_start
                    and datetime.fromisoformat(e["timestamp"]) < hour_end
                ]

                trend_data["timestamps"].append(hour_key)
                trend_data["counts"].append(len(hour_errors))

                # 按错误代码统计
                code_counts = Counter(e["code"] for e in hour_errors)
                for code, count in code_counts.items():
                    if code not in trend_data:
                        trend_data[code] = [0] * hours
                    trend_data[code][i] = count

            return dict(trend_data)

    def clear_old_errors(self, days: int = 7) -> int:
        """
        清理旧错误

        Args:
            days: 保留天数

        Returns:
            清理的错误数量
        """
        with self.lock:
            cutoff_time = datetime.now() - timedelta(days=days)
            old_count = len(self.error_store)
            self.error_store = [
                e
                for e in self.error_store
                if datetime.fromisoformat(e["timestamp"]) >= cutoff_time
            ]

            # 清理按时间分组的错误
            old_time_keys = [
                k
                for k, v in self.error_by_time.items()
                if datetime.strptime(k, "%Y-%m-%d %H:%M") < cutoff_time
            ]
            for key in old_time_keys:
                del self.error_by_time[key]

            return old_count - len(self.error_store)


# 全局错误监控器实例
error_monitor = ErrorMonitor()


def record_error(error: BaseError, context: Optional[Dict[str, Any]] = None) -> None:
    """
    记录错误的便捷函数

    Args:
        error: 错误对象
        context: 错误上下文
    """
    error_monitor.record_error(error, context)


def get_error_stats(days: int = 1) -> Dict[str, Any]:
    """
    获取错误统计信息的便捷函数

    Args:
        days: 统计天数

    Returns:
        错误统计信息
    """
    return error_monitor.get_error_stats(days)


def generate_error_report(days: int = 1) -> str:
    """
    生成错误报告的便捷函数

    Args:
        days: 报告天数

    Returns:
        报告文件路径
    """
    return error_monitor.generate_error_report(days)


def get_error_trend(hours: int = 24) -> Dict[str, List[Dict[str, Any]]]:
    """
    获取错误趋势的便捷函数

    Args:
        hours: 趋势小时数

    Returns:
        错误趋势数据
    """
    return error_monitor.get_error_trend(hours)


def clear_old_errors(days: int = 7) -> int:
    """
    清理旧错误的便捷函数

    Args:
        days: 保留天数

    Returns:
        清理的错误数量
    """
    return error_monitor.clear_old_errors(days)
