"""
核心模块

提供系统核心功能，包括配置管理、日志记录、异常处理等。

模块结构:
- config.py: 配置管理
- logger.py: 日志记录
- exceptions.py: 异常定义
- error_handler.py: 错误处理
- error_monitor.py: 错误监控
- performance_monitor.py: 性能监控
- resilience.py: 系统韧性
"""

from .performance_monitor import performance_monitor, monitor_performance

__all__ = ["performance_monitor", "monitor_performance"]
