"""
配置管理

提供配置加载、管理和访问功能。
"""

import os
import yaml
import time
from typing import Dict, Any, Optional, Union, Callable
from pydantic import BaseModel, Field, validator


class BaseConfig(BaseModel):
    """基础配置模型"""
    pass


class AppConfig(BaseConfig):
    """应用配置"""
    host: str = Field(default="0.0.0.0", description="服务器主机")
    port: int = Field(default=5000, description="服务器端口")
    debug: bool = Field(default=False, description="调试模式")


class OpenAIConfig(BaseConfig):
    api_key: str = Field(default="", description="LLM API密钥")
    api_base_url: str = Field(default="", description="LLM API基础URL")
    model: str = Field(default="gpt-3.5-turbo", description="LLM模型")
    temperature: float = Field(default=0.7, ge=0.0, le=1.0, description="温度参数")
    max_tokens: int = Field(default=1000, ge=1, description="最大token数")

class AnthropicConfig(BaseConfig):
    """Anthropic配置"""
    api_key: str = Field(default="", description="Anthropic API密钥")
    model: str = Field(default="claude-v1", description="Anthropic模型")
    temperature: float = Field(default=0.7, ge=0.0, le=1.0, description="温度参数")
    max_tokens: int = Field(default=1000, ge=1, description="最大token数")

class LLMConfig(BaseConfig):
    """LLM配置"""
    openai: OpenAIConfig = Field(default_factory=OpenAIConfig, description="OpenAI配置")
    anthropic: AnthropicConfig = Field(default_factory=AnthropicConfig, description="Anthropic配置")


class VectorStoreConfig(BaseConfig):
    """向量存储配置"""
    type: str = Field(default="chroma", description="向量存储类型")
    path: str = Field(default="./data/vector_db", description="向量存储路径")
    embedding_model: str = Field(default="text-embedding-ada-002", description="嵌入模型")
    collection_name: str = Field(default="llm_wiki", description="集合名称")
    # dashvector配置, type 类型为 dashvector
    # dashvector_api_key: str = Field(default="", description="dashvector API密钥")
    # dashvector_endpoint: str = Field(default="", description="dashvector Cluster Endpoint")


class DatabaseConfig(BaseConfig):
    """数据库配置"""
    url: str = Field(default="sqlite:///./data/llm_wiki.db", description="数据库连接URL")
    echo: bool = Field(default=False, description="是否打印SQL语句")
    pool_size: int = Field(default=5, description="连接池大小")
    max_overflow: int = Field(default=10, description="最大溢出连接数")
    pool_timeout: int = Field(default=30, description="连接池超时时间（秒）")
    pool_recycle: int = Field(default=3600, description="连接回收时间（秒）")


class PerformanceConfig(BaseConfig):
    """性能配置"""
    cache_size: int = Field(default=1000, description="缓存大小")
    batch_size: int = Field(default=32, description="批处理大小")
    max_workers: int = Field(default=4, description="最大工作线程数")


class ExtractionConfig(BaseConfig):
    """提取配置"""
    max_chunk_size: int = Field(default=2000, description="最大 chunk 大小")
    min_chunk_size: int = Field(default=500, description="最小 chunk 大小")


class EmbeddingConfig(BaseConfig):
    """嵌入配置"""
    batch_size: int = Field(default=32, description="嵌入批处理大小")


class ProcessingLLMConfig(BaseConfig):
    """处理LLM配置"""
    max_tokens: int = Field(default=1000, description="最大 token 数")
    temperature: float = Field(default=0.7, description="温度参数")


class ProcessingConfig(BaseConfig):
    """处理配置"""
    extraction: ExtractionConfig = Field(default_factory=ExtractionConfig)
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    llm: ProcessingLLMConfig = Field(default_factory=ProcessingLLMConfig)

class SystemConfig(BaseConfig):
    """系统配置"""
    name: str = Field(default="LLM Wiki", description="系统名称")
    version: str = Field(default="1.0.0", description="系统版本")
    language: str = Field(default="zh-CN", description="系统语言")
    log_level: str = Field(default="INFO", description="日志级别")

class WebuiConfig(BaseConfig):
    """WebUI配置"""
    host: str = Field(default="0.0.0.0", description="WebUI主机")
    port: int = Field(default=7860, description="WebUI端口")
    debug: bool = Field(default=False, description="调试模式")
    share: bool = Field(default=False, description="gradio share")

class ConfigSchema(BaseModel):
    """配置模式"""
    system: SystemConfig = Field(default_factory=SystemConfig)
    app: AppConfig = Field(default_factory=AppConfig)
    webui: WebuiConfig = Field(default_factory=WebuiConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    vector_store: VectorStoreConfig = Field(default_factory=VectorStoreConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)
    processing: ProcessingConfig = Field(default_factory=ProcessingConfig)
    data_dir: str = Field(default="./data", description="数据目录")
    wiki_dir: str = Field(default="./wiki", description="Wiki目录")
    log_level: str = Field(default="INFO", description="日志级别")


class Config:
    """配置类

    支持通过属性访问和字典访问两种方式获取配置值。
    对于嵌套配置，会自动返回新的Config对象。
    """

    def __init__(self, config_dict: Dict[str, Any], is_nested: bool = False):
        """
        初始化配置对象

        Args:
            config_dict: 配置字典
            is_nested: 是否为嵌套配置
        """
        if not is_nested:
            # 只对根配置进行验证
            self._schema = ConfigSchema(**config_dict)
            self._config = self._schema.dict()
        else:
            # 嵌套配置直接使用字典
            self._config = config_dict
        self._last_loaded = time.time()

    def __getattr__(self, name: str) -> Any:
        """
        通过属性访问获取配置值

        Args:
            name: 配置项名称

        Returns:
            配置值，如果是字典则返回Config对象

        Raises:
            AttributeError: 如果配置项不存在
        """
        if name in self._config:
            value = self._config[name]
            if isinstance(value, dict):
                return Config(value, is_nested=True)
            return value
        raise AttributeError(f"Config object has no attribute '{name}'")

    def __getitem__(self, name: str) -> Any:
        """
        通过字典访问获取配置值

        Args:
            name: 配置项名称

        Returns:
            配置值，如果是字典则返回Config对象
        """
        if name in self._config:
            value = self._config[name]
            if isinstance(value, dict):
                return Config(value, is_nested=True)
            return value
        raise KeyError(f"Config key '{name}' not found")

    def get(self, name: str, default: Any = None) -> Any:
        """
        获取配置值，支持默认值

        Args:
            name: 配置项名称
            default: 默认值

        Returns:
            配置值或默认值，如果是字典则返回Config对象
        """
        if name in self._config:
            value = self._config[name]
            if isinstance(value, dict):
                return Config(value, is_nested=True)
            return value
        return default

    def to_dict(self) -> Dict[str, Any]:
        """
        将配置转换为字典

        Returns:
            配置字典
        """
        return self._config

    @property
    def last_loaded(self) -> float:
        """
        获取最后加载时间

        Returns:
            最后加载时间戳
        """
        return self._last_loaded


def _replace_env_vars(obj: Any) -> Any:
    """
    替换环境变量

    Args:
        obj: 要处理的对象

    Returns:
        处理后的对象
    """
    if isinstance(obj, dict):
        return {k: _replace_env_vars(v) for k, v in obj.items()}
    elif isinstance(obj, str) and obj.startswith("${") and obj.endswith("}"):
        env_var = obj[2:-1]
        return os.environ.get(env_var, obj)
    return obj


# 配置缓存
_config_cache: Dict[str, Config] = {}
_config_mtime: Dict[str, float] = {}


def load_config(config_path: str = "config/config.yaml") -> Config:
    """
    加载配置文件

    Args:
        config_path: 配置文件路径

    Returns:
        配置对象
    """
    try:
        # 检查文件是否存在
        if not os.path.exists(config_path):
            # 如果配置文件不存在，返回默认配置
            return Config({})

        # 检查文件修改时间
        mtime = os.path.getmtime(config_path)
        if config_path in _config_cache and _config_mtime.get(config_path, 0) >= mtime:
            return _config_cache[config_path]

        with open(config_path, "r", encoding="utf-8") as f:
            config_dict = yaml.safe_load(f)

        if config_dict is None:
            config_dict = {}

        # 替换环境变量
        config_dict = _replace_env_vars(config_dict)
        config = Config(config_dict)

        # 更新缓存
        _config_cache[config_path] = config
        _config_mtime[config_path] = mtime

        return config
    except FileNotFoundError:
        # 文件不存在时返回默认配置
        return Config({})
    except yaml.YAMLError as e:
        raise ValueError(f"配置文件格式错误: {e}")


# 全局配置实例
config = load_config()


def get_config() -> Config:
    """
    获取全局配置对象

    Returns:
        配置对象
    """
    return config


def reload_config(config_path: str = "config/config.yaml") -> Config:
    """
    重新加载配置

    Args:
        config_path: 配置文件路径

    Returns:
        新的配置对象
    """
    global config
    # 清除缓存
    if config_path in _config_cache:
        del _config_cache[config_path]
        del _config_mtime[config_path]
    config = load_config(config_path)
    return config


def watch_config(config_path: str = "config/config.yaml", callback: Optional[Callable] = None):
    """
    监视配置文件变化

    Args:
        config_path: 配置文件路径
        callback: 配置变化时的回调函数
    """
    import threading
    import time

    def watcher():
        last_mtime = 0
        while True:
            if os.path.exists(config_path):
                current_mtime = os.path.getmtime(config_path)
                if current_mtime > last_mtime:
                    last_mtime = current_mtime
                    reload_config(config_path)
                    if callback:
                        callback()
            time.sleep(5)  # 每5秒检查一次

    thread = threading.Thread(target=watcher, daemon=True)
    thread.start()


# 配置文件路径
CONFIG_PATH = os.environ.get("LLM_WIKI_CONFIG", "config/config.yaml")
