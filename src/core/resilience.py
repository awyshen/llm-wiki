"""
弹性和恢复策略
"""

import time
import threading
from typing import Callable, Optional, Any, Dict, TypeVar
import functools

from .logger import get_logger
from .exceptions import BaseError

logger = get_logger(__name__)

# 类型变量
T = TypeVar("T")


class CircuitBreaker:
    """断路器模式实现"""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        reset_timeout: float = 60.0,
    ):
        """
        初始化断路器

        Args:
            failure_threshold: 失败阈值，超过此值则打开断路器
            recovery_timeout: 恢复超时时间（秒），在此时间后尝试半开状态
            reset_timeout: 重置超时时间（秒），在此时间后完全重置
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.reset_timeout = reset_timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.lock = threading.RLock()

    def __call__(self, func: Callable[..., T]) -> Callable[..., T]:
        """
        断路器装饰器

        Args:
            func: 被装饰的函数

        Returns:
            装饰后的函数
        """

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            if not self._should_execute():
                raise BaseError(
                    f"服务暂时不可用，断路器状态: {self.state}",
                    code="SERVICE_UNAVAILABLE",
                )

            try:
                result = func(*args, **kwargs)
                self._record_success()
                return result
            except Exception as e:
                self._record_failure()
                raise

        return wrapper

    def _should_execute(self) -> bool:
        """
        判断是否应该执行操作

        Returns:
            是否应该执行
        """
        with self.lock:
            current_time = time.time()

            if self.state == "CLOSED":
                return True
            elif self.state == "OPEN":
                # 检查是否超过恢复时间
                if current_time - self.last_failure_time > self.recovery_timeout:
                    # 进入半开状态
                    self.state = "HALF_OPEN"
                    logger.info("断路器状态从 OPEN 变为 HALF_OPEN")
                    return True
                return False
            elif self.state == "HALF_OPEN":
                return True
            return False

    def _record_success(self) -> None:
        """
        记录成功
        """
        with self.lock:
            if self.state == "HALF_OPEN":
                # 半开状态下成功，关闭断路器
                self.state = "CLOSED"
                self.failure_count = 0
                logger.info("断路器状态从 HALF_OPEN 变为 CLOSED")

    def _record_failure(self) -> None:
        """
        记录失败
        """
        with self.lock:
            current_time = time.time()
            self.failure_count += 1
            self.last_failure_time = current_time

            if self.state == "CLOSED" and self.failure_count >= self.failure_threshold:
                # 关闭状态下失败次数达到阈值，打开断路器
                self.state = "OPEN"
                logger.warning(
                    f"断路器状态从 CLOSED 变为 OPEN，失败次数: {self.failure_count}"
                )
            elif self.state == "HALF_OPEN":
                # 半开状态下失败，重新打开断路器
                self.state = "OPEN"
                logger.warning("断路器状态从 HALF_OPEN 变为 OPEN")

    def reset(self) -> None:
        """
        重置断路器
        """
        with self.lock:
            self.state = "CLOSED"
            self.failure_count = 0
            self.last_failure_time = 0
            logger.info("断路器已重置")

    def get_state(self) -> str:
        """
        获取断路器状态

        Returns:
            断路器状态
        """
        with self.lock:
            return self.state


class RetryWithBackoff:
    """带退避策略的重试机制"""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0,
    ):
        """
        初始化重试机制

        Args:
            max_retries: 最大重试次数
            base_delay: 基础延迟（秒）
            max_delay: 最大延迟（秒）
            backoff_factor: 退避因子
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor

    def __call__(self, func: Callable[..., T]) -> Callable[..., T]:
        """
        重试装饰器

        Args:
            func: 被装饰的函数

        Returns:
            装饰后的函数
        """

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception = None

            for attempt in range(self.max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < self.max_retries:
                        # 计算退避时间
                        delay = min(
                            self.base_delay * (self.backoff_factor**attempt),
                            self.max_delay,
                        )
                        logger.warning(
                            f"尝试 {attempt+1}/{self.max_retries+1} 失败: {str(e)}，将在 {delay:.2f} 秒后重试"
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"所有 {self.max_retries+1} 次尝试都失败了: {str(e)}"
                        )

            # 所有尝试都失败，抛出最后一个异常
            raise last_exception

        return wrapper


class FallbackStrategy:
    """降级策略"""

    def __init__(
        self,
        fallback_func: Callable[..., T],
        *fallback_args: Any,
        **fallback_kwargs: Any,
    ):
        """
        初始化降级策略

        Args:
            fallback_func: 降级函数
            *fallback_args: 降级函数的位置参数
            **fallback_kwargs: 降级函数的关键字参数
        """
        self.fallback_func = fallback_func
        self.fallback_args = fallback_args
        self.fallback_kwargs = fallback_kwargs

    def __call__(self, func: Callable[..., T]) -> Callable[..., T]:
        """
        降级装饰器

        Args:
            func: 被装饰的函数

        Returns:
            装饰后的函数
        """

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.warning(f"主函数执行失败: {str(e)}，使用降级函数")
                try:
                    return self.fallback_func(
                        *self.fallback_args, **self.fallback_kwargs
                    )
                except Exception as fallback_e:
                    logger.error(f"降级函数执行也失败: {str(fallback_e)}")
                    raise

        return wrapper


class ServiceResilience:
    """服务弹性管理"""

    def __init__(self):
        """初始化服务弹性管理"""
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.lock = threading.RLock()

    def get_circuit_breaker(self, service_name: str, **kwargs: Any) -> CircuitBreaker:
        """
        获取或创建断路器

        Args:
            service_name: 服务名称
            **kwargs: 断路器参数

        Returns:
            断路器实例
        """
        with self.lock:
            if service_name not in self.circuit_breakers:
                self.circuit_breakers[service_name] = CircuitBreaker(**kwargs)
            return self.circuit_breakers[service_name]

    def wrap_service(
        self,
        service_name: str,
        fallback: Optional[Callable[..., T]] = None,
        **breaker_kwargs: Any,
    ) -> Callable[[Callable[..., T]], Callable[..., T]]:
        """
        包装服务，添加弹性策略

        Args:
            service_name: 服务名称
            fallback: 降级函数
            **breaker_kwargs: 断路器参数

        Returns:
            装饰器
        """

        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            # 获取或创建断路器
            circuit_breaker = self.get_circuit_breaker(service_name, **breaker_kwargs)

            # 应用断路器
            wrapped_func = circuit_breaker(func)

            # 应用重试机制
            wrapped_func = RetryWithBackoff()(wrapped_func)

            # 应用降级策略
            if fallback:
                wrapped_func = FallbackStrategy(fallback)(wrapped_func)

            return wrapped_func

        return decorator


# 全局服务弹性管理实例
service_resilience = ServiceResilience()


# 便捷函数
def circuit_breaker(**kwargs: Any) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    断路器装饰器

    Args:
        **kwargs: 断路器参数

    Returns:
        装饰器
    """
    cb = CircuitBreaker(**kwargs)
    return cb.__call__


def retry_with_backoff(**kwargs: Any) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    带退避策略的重试装饰器

    Args:
        **kwargs: 重试参数

    Returns:
        装饰器
    """
    rwb = RetryWithBackoff(**kwargs)
    return rwb.__call__


def fallback(
    fallback_func: Callable[..., T], *fallback_args: Any, **fallback_kwargs: Any
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    降级装饰器

    Args:
        fallback_func: 降级函数
        *fallback_args: 降级函数的位置参数
        **fallback_kwargs: 降级函数的关键字参数

    Returns:
        装饰器
    """
    fs = FallbackStrategy(fallback_func, *fallback_args, **fallback_kwargs)
    return fs.__call__


def wrap_service(
    service_name: str,
    fallback: Optional[Callable[..., T]] = None,
    **breaker_kwargs: Any,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    包装服务，添加弹性策略

    Args:
        service_name: 服务名称
        fallback: 降级函数
        **breaker_kwargs: 断路器参数

    Returns:
        装饰器
    """
    return service_resilience.wrap_service(service_name, fallback, **breaker_kwargs)
