"""
错误处理装饰器
"""

from typing import Callable, Optional, Any, TypeVar, Generic
import functools
import time
from .logger import get_logger
from .exceptions import (
    BaseError,
    ProcessingError,
    StorageError,
    LLMError,
    ValidationError,
    NetworkError,
    ConfigurationError,
    TimeoutError,
)

logger = get_logger(__name__)

# 类型变量
T = TypeVar("T")


class ErrorHandler(Generic[T]):
    """错误处理器"""

    @staticmethod
    def handle_exceptions(
        retry_count: int = 0,
        retry_delay: float = 1.0,
        backoff_factor: float = 2.0,
        allowed_exceptions: Optional[tuple] = None,
        default_return: Optional[Any] = None,
        log_level: str = "error",
    ) -> Callable[[Callable[..., T]], Callable[..., T]]:
        """
        异常处理装饰器

        Args:
            retry_count: 重试次数
            retry_delay: 初始重试延迟（秒）
            backoff_factor: 退避因子
            allowed_exceptions: 允许重试的异常类型
            default_return: 异常发生时的默认返回值
            log_level: 日志级别

        Returns:
            装饰后的函数
        """

        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            @functools.wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> T:
                retries = 0
                current_delay = retry_delay

                while retries <= retry_count:
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        # 记录异常
                        error_message = f"函数 {func.__name__} 执行失败: {str(e)}"
                        if log_level == "debug":
                            logger.debug(error_message, exc_info=True)
                        elif log_level == "info":
                            logger.info(error_message, exc_info=True)
                        elif log_level == "warning":
                            logger.warning(error_message, exc_info=True)
                        else:
                            logger.error(error_message, exc_info=True)

                        # 检查是否是允许重试的异常
                        if allowed_exceptions and not isinstance(e, allowed_exceptions):
                            break

                        # 检查是否还有重试次数
                        if retries < retry_count:
                            logger.info(
                                f"将在 {current_delay:.2f} 秒后重试，剩余重试次数: {retry_count - retries}"
                            )
                            time.sleep(current_delay)
                            current_delay *= backoff_factor
                            retries += 1
                        else:
                            break

                # 如果设置了默认返回值，则返回默认值
                if default_return is not None:
                    logger.warning(
                        f"函数 {func.__name__} 执行失败，返回默认值: {default_return}"
                    )
                    return default_return

                # 否则重新抛出异常
                raise

            return wrapper

        return decorator

    @staticmethod
    def handle_llm_exceptions(
        retry_count: int = 3,
        retry_delay: float = 1.0,
        backoff_factor: float = 2.0,
        default_return: Optional[Any] = None,
    ) -> Callable[[Callable[..., T]], Callable[..., T]]:
        """
        LLM异常处理装饰器

        Args:
            retry_count: 重试次数
            retry_delay: 初始重试延迟（秒）
            backoff_factor: 退避因子
            default_return: 异常发生时的默认返回值

        Returns:
            装饰后的函数
        """
        return ErrorHandler.handle_exceptions(
            retry_count=retry_count,
            retry_delay=retry_delay,
            backoff_factor=backoff_factor,
            allowed_exceptions=(LLMError, NetworkError, TimeoutError),
            default_return=default_return,
            log_level="error",
        )

    @staticmethod
    def handle_storage_exceptions(
        retry_count: int = 3,
        retry_delay: float = 1.0,
        backoff_factor: float = 2.0,
        default_return: Optional[Any] = None,
    ) -> Callable[[Callable[..., T]], Callable[..., T]]:
        """
        存储异常处理装饰器

        Args:
            retry_count: 重试次数
            retry_delay: 初始重试延迟（秒）
            backoff_factor: 退避因子
            default_return: 异常发生时的默认返回值

        Returns:
            装饰后的函数
        """
        return ErrorHandler.handle_exceptions(
            retry_count=retry_count,
            retry_delay=retry_delay,
            backoff_factor=backoff_factor,
            allowed_exceptions=(StorageError,),
            default_return=default_return,
            log_level="error",
        )

    @staticmethod
    def handle_processing_exceptions(
        retry_count: int = 1,
        retry_delay: float = 1.0,
        backoff_factor: float = 2.0,
        default_return: Optional[Any] = None,
    ) -> Callable[[Callable[..., T]], Callable[..., T]]:
        """
        处理异常处理装饰器

        Args:
            retry_count: 重试次数
            retry_delay: 初始重试延迟（秒）
            backoff_factor: 退避因子
            default_return: 异常发生时的默认返回值

        Returns:
            装饰后的函数
        """
        return ErrorHandler.handle_exceptions(
            retry_count=retry_count,
            retry_delay=retry_delay,
            backoff_factor=backoff_factor,
            allowed_exceptions=(ProcessingError,),
            default_return=default_return,
            log_level="error",
        )


# 全局错误处理器实例
error_handler = ErrorHandler()


# 便捷函数
handle_exceptions = error_handler.handle_exceptions
handle_llm_exceptions = error_handler.handle_llm_exceptions
handle_storage_exceptions = error_handler.handle_storage_exceptions
handle_processing_exceptions = error_handler.handle_processing_exceptions
