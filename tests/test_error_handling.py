"""
测试错误处理机制
"""

import time
from src.core.exceptions import BaseError, ProcessingError, LLMError, NetworkError, ConfigurationError, TimeoutError
from src.core.error_handler import handle_exceptions, handle_llm_exceptions, handle_processing_exceptions
from src.core.resilience import circuit_breaker, retry_with_backoff, fallback
from src.core.error_monitor import record_error, get_error_stats, generate_error_report
from src.core.logger import get_logger

logger = get_logger(__name__)


# 测试异常类
def test_exception_classes():
    """测试异常类的功能"""
    # 测试基础异常
    base_error = BaseError("测试基础错误", code="TEST_ERROR", details={"test": "data"})
    assert base_error.message == "测试基础错误"
    assert base_error.code == "TEST_ERROR"
    assert base_error.details == {"test": "data"}
    assert base_error.to_dict() == {
        "code": "TEST_ERROR",
        "message": "测试基础错误",
        "details": {"test": "data"},
        "cause": None
    }
    
    # 测试处理错误
    processing_error = ProcessingError("测试处理错误", cause=Exception("原始异常"))
    assert processing_error.message == "测试处理错误"
    assert processing_error.code == "PROCESSING_ERROR"
    assert processing_error.cause is not None
    
    # 测试LLM错误
    llm_error = LLMError("测试LLM错误")
    assert llm_error.message == "测试LLM错误"
    assert llm_error.code == "LLM_ERROR"
    
    # 测试网络错误
    network_error = NetworkError("测试网络错误")
    assert network_error.message == "测试网络错误"
    assert network_error.code == "NETWORK_ERROR"
    
    # 测试配置错误
    config_error = ConfigurationError("测试配置错误")
    assert config_error.message == "测试配置错误"
    assert config_error.code == "CONFIGURATION_ERROR"
    
    # 测试超时错误
    timeout_error = TimeoutError("测试超时错误")
    assert timeout_error.message == "测试超时错误"
    assert timeout_error.code == "TIMEOUT_ERROR"


# 测试错误处理装饰器
def test_error_handler():
    """测试错误处理装饰器的功能"""
    # 测试基本装饰器
    @handle_exceptions(retry_count=2, default_return="默认值")
    def test_func(fail: bool):
        if fail:
            raise Exception("测试异常")
        return "成功"
    
    # 测试成功情况
    assert test_func(fail=False) == "成功"
    
    # 测试失败情况，应该返回默认值
    assert test_func(fail=True) == "默认值"
    
    # 测试LLM异常处理装饰器
    @handle_llm_exceptions(default_return="LLM默认值")
    def test_llm_func(fail: bool):
        if fail:
            raise LLMError("LLM测试异常")
        return "LLM成功"
    
    # 测试成功情况
    assert test_llm_func(fail=False) == "LLM成功"
    
    # 测试失败情况，应该返回默认值
    assert test_llm_func(fail=True) == "LLM默认值"
    
    # 测试处理异常装饰器
    @handle_processing_exceptions(default_return="处理默认值")
    def test_processing_func(fail: bool):
        if fail:
            raise ProcessingError("处理测试异常")
        return "处理成功"
    
    # 测试成功情况
    assert test_processing_func(fail=False) == "处理成功"
    
    # 测试失败情况，应该返回默认值
    assert test_processing_func(fail=True) == "处理默认值"


# 测试断路器
def test_circuit_breaker():
    """测试断路器的功能"""
    # 创建一个断路器
    @circuit_breaker(failure_threshold=2, recovery_timeout=1)
    def test_circuit_func(fail: bool):
        if fail:
            raise Exception("断路器测试异常")
        return "断路器成功"
    
    # 第一次失败，断路器应该还是关闭状态
    try:
        test_circuit_func(fail=True)
        assert False, "应该抛出异常"
    except Exception:
        pass
    
    # 第二次失败，断路器应该打开
    try:
        test_circuit_func(fail=True)
        assert False, "应该抛出异常"
    except Exception:
        pass
    
    # 第三次失败，断路器应该已经打开，抛出服务不可用异常
    try:
        test_circuit_func(fail=False)
        assert False, "应该抛出服务不可用异常"
    except BaseError as e:
        assert e.code == "SERVICE_UNAVAILABLE"
    
    # 等待恢复时间
    time.sleep(1.1)
    
    # 断路器应该进入半开状态，尝试执行
    try:
        result = test_circuit_func(fail=False)
        assert result == "断路器成功"
    except Exception:
        assert False, "应该成功执行"


# 测试重试机制
def test_retry_with_backoff():
    """测试重试机制的功能"""
    retry_count = 0
    
    @retry_with_backoff(max_retries=2, base_delay=0.1)
    def test_retry_func(fail: bool):
        nonlocal retry_count
        retry_count += 1
        if fail:
            raise Exception("重试测试异常")
        return "重试成功"
    
    # 测试成功情况
    retry_count = 0
    result = test_retry_func(fail=False)
    assert result == "重试成功"
    assert retry_count == 1
    
    # 测试失败情况，应该重试3次
    retry_count = 0
    try:
        test_retry_func(fail=True)
        assert False, "应该抛出异常"
    except Exception:
        pass
    assert retry_count == 3


# 测试降级策略
def test_fallback():
    """测试降级策略的功能"""
    def fallback_func():
        return "降级成功"
    
    @fallback(fallback_func)
    def test_fallback_func(fail: bool):
        if fail:
            raise Exception("降级测试异常")
        return "主函数成功"
    
    # 测试成功情况
    result = test_fallback_func(fail=False)
    assert result == "主函数成功"
    
    # 测试失败情况，应该使用降级函数
    result = test_fallback_func(fail=True)
    assert result == "降级成功"


# 测试错误监控
def test_error_monitor():
    """测试错误监控的功能"""
    # 记录一个错误
    error = LLMError("监控测试错误", details={"test": "data"})
    record_error(error, {"context": "测试上下文"})
    
    # 获取错误统计
    stats = get_error_stats(days=1)
    assert stats['total_errors'] >= 1
    assert 'LLM_ERROR' in stats['errors_by_code']
    
    # 生成错误报告
    report_file = generate_error_report(days=1)
    assert report_file.endswith('.json')


if __name__ == "__main__":
    # 运行所有测试
    test_exception_classes()
    print("✓ 异常类测试通过")
    
    test_error_handler()
    print("✓ 错误处理装饰器测试通过")
    
    test_circuit_breaker()
    print("✓ 断路器测试通过")
    
    test_retry_with_backoff()
    print("✓ 重试机制测试通过")
    
    test_fallback()
    print("✓ 降级策略测试通过")
    
    test_error_monitor()
    print("✓ 错误监控测试通过")
    
    print("\n所有测试通过！")