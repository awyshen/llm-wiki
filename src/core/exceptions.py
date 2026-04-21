"""
异常定义
"""

from typing import Optional, Dict, Any
import traceback


class BaseError(Exception):
    """基础错误类"""

    def __init__(
        self,
        message: str,
        code: str = "UNKNOWN_ERROR",
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        """
        初始化基础错误

        Args:
            message: 错误消息
            code: 错误代码
            details: 错误详情
            cause: 原始异常
        """
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}
        self.cause = cause
        self.traceback = traceback.format_exc() if cause else traceback.format_exc()

    def to_dict(self) -> Dict[str, Any]:
        """将错误转换为字典"""
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details,
            "cause": str(self.cause) if self.cause else None,
        }


class ProcessingError(BaseError):
    """处理错误"""

    def __init__(
        self,
        message: str,
        code: str = "PROCESSING_ERROR",
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(message, code, details, cause)


class StorageError(BaseError):
    """存储错误"""

    def __init__(
        self,
        message: str,
        code: str = "STORAGE_ERROR",
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(message, code, details, cause)


class LLMError(BaseError):
    """LLM错误"""

    def __init__(
        self,
        message: str,
        code: str = "LLM_ERROR",
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(message, code, details, cause)


class ValidationError(BaseError):
    """验证错误"""

    def __init__(
        self,
        message: str,
        code: str = "VALIDATION_ERROR",
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(message, code, details, cause)


class NetworkError(BaseError):
    """网络错误"""

    def __init__(
        self,
        message: str,
        code: str = "NETWORK_ERROR",
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(message, code, details, cause)


class ConfigurationError(BaseError):
    """配置错误"""

    def __init__(
        self,
        message: str,
        code: str = "CONFIGURATION_ERROR",
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(message, code, details, cause)


class TimeoutError(BaseError):
    """超时错误"""

    def __init__(
        self,
        message: str,
        code: str = "TIMEOUT_ERROR",
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(message, code, details, cause)
