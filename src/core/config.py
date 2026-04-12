"""
配置管理模块

负责加载和管理系统配置，支持YAML配置文件和环境变量覆盖。
"""

import os
import re
import yaml
from pathlib import Path
from typing import Any, Dict, Optional, List
from dataclasses import dataclass, field
from functools import lru_cache


@dataclass
class SystemConfig:
    """系统基础配置"""
    name: str = "LLM Wiki - AI驱动个人知识库"
    version: str = "1.0.0"
    description: str = "基于Karpathy理念的个人知识管理系统"
    language: str = "zh-CN"
    debug: bool = False
    log_level: str = "INFO"


@dataclass
class PathsConfig:
    """路径配置"""
    data_dir: str = "./data"
    raw_dir: str = "./data/raw"
    wiki_dir: str = "./data/wiki"
    backup_dir: str = "./data/backup"
    temp_dir: str = "./data/temp"
    logs_dir: str = "./logs"


@dataclass
class DatabaseConfig:
    """数据库配置"""
    type: str = "sqlite"
    url: str = "sqlite:///data/llm_wiki.db"
    echo: bool = False
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    pool_recycle: int = 3600


@dataclass
class VectorDBConfig:
    """向量数据库配置"""
    enabled: bool = True
    type: str = "chroma"
    path: str = "./data/vector_db"
    collection_name: str = "llm_wiki"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    chunk_size: int = 512
    chunk_overlap: int = 50


@dataclass
class EmbeddingConfig:
    """嵌入服务配置"""
    type: str = "local"
    dashvector_api_key: str = ""
    dashvector_endpoint: str = ""


@dataclass
class LLMProviderConfig:
    """LLM提供商配置"""
    api_key: str = ""
    base_url: str = ""
    model: str = "gpt-4"
    temperature: float = 0.3
    max_tokens: int = 4096
    timeout: int = 60


@dataclass
class LLMConfig:
    """LLM配置"""
    default_provider: str = "openai"
    openai: LLMProviderConfig = field(default_factory=lambda: LLMProviderConfig())
    anthropic: LLMProviderConfig = field(default_factory=lambda: LLMProviderConfig(
        model="claude-3-opus-20240229"
    ))


@dataclass
class ProcessingConfig:
    """知识处理配置"""
    auto_process: bool = True
    process_interval: int = 300


@dataclass
class FileWatcherConfig:
    """文件监控配置"""
    enabled: bool = True
    patterns: List[str] = field(default_factory=lambda: ["*.md", "*.txt", "*.pdf", "*.docx", "*.html"])
    ignore_patterns: List[str] = field(default_factory=lambda: [".*", "~*", "*.tmp"])


@dataclass
class ExtractionConfig:
    """知识提取配置"""
    max_chunk_size: int = 2000
    overlap_size: int = 200
    min_chunk_size: int = 100


@dataclass
class EntityExtractionConfig:
    """实体识别配置"""
    enabled: bool = True
    min_confidence: float = 0.7
    entity_types: List[str] = field(default_factory=lambda: [
        "人物", "组织", "地点", "概念", "技术", "项目", "事件"
    ])


@dataclass
class KnowledgeGraphConfig:
    """知识图谱配置"""
    enabled: bool = True
    min_similarity: float = 0.75
    max_relations_per_entity: int = 10
    auto_link: bool = True


@dataclass
class BackupConfig:
    """备份配置"""
    enabled: bool = True
    interval: int = 86400
    max_backups: int = 7
    compress: bool = True


@dataclass
class APIConfig:
    """API服务配置"""
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1
    reload: bool = False
    cors_origins: List[str] = field(default_factory=lambda: [
        "http://localhost:3000", "http://127.0.0.1:3000"
    ])


@dataclass
class WebUIConfig:
    """Web界面配置"""
    enabled: bool = True
    type: str = "gradio"
    port: int = 7860
    share: bool = False


@dataclass
class SecurityConfig:
    """安全配置"""
    secret_key: str = ""
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440
    password_min_length: int = 8
    max_login_attempts: int = 5
    lockout_duration: int = 1800


@dataclass
class PerformanceConfig:
    """性能配置"""
    max_concurrent_requests: int = 10
    request_timeout: int = 120
    cache_size: int = 1000
    cache_ttl: int = 3600


@dataclass
class SearchConfig:
    """搜索配置"""
    max_results: int = 50
    timeout: int = 5
    enable_semantic_search: bool = True
    enable_fuzzy_search: bool = True
    enable_history: bool = True
    max_history: int = 10


class Config:
    """主配置类"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.system = SystemConfig()
        self.paths = PathsConfig()
        self.database = DatabaseConfig()
        self.vector_db = VectorDBConfig()
        self.embedding = EmbeddingConfig()
        self.llm = LLMConfig()
        self.processing = ProcessingConfig()
        self.file_watcher = FileWatcherConfig()
        self.extraction = ExtractionConfig()
        self.entity_extraction = EntityExtractionConfig()
        self.knowledge_graph = KnowledgeGraphConfig()
        self.backup = BackupConfig()
        self.api = APIConfig()
        self.webui = WebUIConfig()
        self.security = SecurityConfig()
        self.performance = PerformanceConfig()
        self.search = SearchConfig()
        
        if config_path:
            self.load_from_file(config_path)
        else:
            # 尝试加载默认配置文件
            default_paths = [
                "./config/config.yaml",
                "../config/config.yaml",
                "/etc/llm-wiki/config.yaml",
            ]
            for path in default_paths:
                if os.path.exists(path):
                    self.load_from_file(path)
                    break
    
    def load_from_file(self, path: str) -> None:
        """从YAML文件加载配置"""
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        if data:
            self._update_from_dict(data)
    
    def _update_from_dict(self, data: Dict[str, Any]) -> None:
        """从字典更新配置"""
        # 处理系统配置
        if 'system' in data:
            self._update_dataclass(self.system, data['system'])
        
        # 处理路径配置
        if 'paths' in data:
            self._update_dataclass(self.paths, data['paths'])
        
        # 处理数据库配置
        if 'database' in data:
            self._update_dataclass(self.database, data['database'])
        
        # 处理向量数据库配置
        if 'vector_db' in data:
            self._update_dataclass(self.vector_db, data['vector_db'])
        
        # 处理嵌入服务配置
        if 'embedding' in data:
            self._update_dataclass(self.embedding, data['embedding'])
        
        # 处理LLM配置
        if 'llm' in data:
            llm_data = data['llm']
            if 'default_provider' in llm_data:
                self.llm.default_provider = llm_data['default_provider']
            if 'openai' in llm_data:
                self._update_dataclass(self.llm.openai, llm_data['openai'])
            if 'anthropic' in llm_data:
                self._update_dataclass(self.llm.anthropic, llm_data['anthropic'])
        
        # 处理其他配置...
        if 'processing' in data:
            self._update_dataclass(self.processing, data['processing'])
        if 'file_watcher' in data:
            self._update_dataclass(self.file_watcher, data['file_watcher'])
        if 'extraction' in data:
            self._update_dataclass(self.extraction, data['extraction'])
        if 'entity_extraction' in data:
            self._update_dataclass(self.entity_extraction, data['entity_extraction'])
        if 'knowledge_graph' in data:
            self._update_dataclass(self.knowledge_graph, data['knowledge_graph'])
        if 'backup' in data:
            self._update_dataclass(self.backup, data['backup'])
        if 'api' in data:
            self._update_dataclass(self.api, data['api'])
        if 'webui' in data:
            self._update_dataclass(self.webui, data['webui'])
        if 'security' in data:
            self._update_dataclass(self.security, data['security'])
        if 'performance' in data:
            self._update_dataclass(self.performance, data['performance'])
        if 'search' in data:
            self._update_dataclass(self.search, data['search'])
        
        # 处理环境变量覆盖
        self._apply_env_overrides()
    
    def _update_dataclass(self, obj: Any, data: Dict[str, Any]) -> None:
        """更新数据类实例"""
        for key, value in data.items():
            if hasattr(obj, key):
                # 处理环境变量引用 ${VAR_NAME}
                if isinstance(value, str):
                    value = self._resolve_env_vars(value)
                setattr(obj, key, value)
    
    def _resolve_env_vars(self, value: str) -> str:
        """解析环境变量引用"""
        pattern = r'\$\{([^}]+)\}'
        
        def replace_var(match):
            var_name = match.group(1)
            return os.environ.get(var_name, match.group(0))
        
        return re.sub(pattern, replace_var, value)
    
    def _apply_env_overrides(self) -> None:
        """应用环境变量覆盖"""
        # OpenAI API Key
        if os.environ.get('OPENAI_API_KEY'):
            self.llm.openai.api_key = os.environ['OPENAI_API_KEY']
        
        # Anthropic API Key
        if os.environ.get('ANTHROPIC_API_KEY'):
            self.llm.anthropic.api_key = os.environ['ANTHROPIC_API_KEY']
        
        # DashVector API Key
        if os.environ.get('DASHVECTOR_API_KEY'):
            self.embedding.dashvector_api_key = os.environ['DASHVECTOR_API_KEY']
        
        if os.environ.get('DASHVECTOR_ENDPOINT'):
            self.embedding.dashvector_endpoint = os.environ['DASHVECTOR_ENDPOINT']
        
        # Secret Key
        if os.environ.get('SECRET_KEY'):
            self.security.secret_key = os.environ['SECRET_KEY']
    
    def ensure_directories(self) -> None:
        """确保所有必要的目录存在"""
        dirs = [
            self.paths.data_dir,
            self.paths.raw_dir,
            self.paths.wiki_dir,
            self.paths.backup_dir,
            self.paths.temp_dir,
            self.paths.logs_dir,
        ]
        for dir_path in dirs:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    def to_dict(self) -> Dict[str, Any]:
        """将配置转换为字典"""
        def dataclass_to_dict(obj):
            if isinstance(obj, (list, tuple)):
                return [dataclass_to_dict(item) for item in obj]
            elif isinstance(obj, dict):
                return {k: dataclass_to_dict(v) for k, v in obj.items()}
            elif hasattr(obj, '__dataclass_fields__'):
                return {k: dataclass_to_dict(v) for k, v in obj.__dict__.items()}
            else:
                return obj
        
        return dataclass_to_dict(self.__dict__)


@lru_cache()
def get_config(config_path: Optional[str] = None) -> Config:
    """获取配置单例"""
    return Config(config_path)
