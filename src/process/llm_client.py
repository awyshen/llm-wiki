"""
LLM客户端
"""

from typing import Optional, Dict, Any, List
import requests
import json
import time
from dataclasses import dataclass
import threading
from queue import Queue
from collections import defaultdict
import hashlib

from ..core.config import Config, get_config
from ..core.logger import get_logger
from ..core.exceptions import LLMError, NetworkError, TimeoutError, ConfigurationError
from ..core.error_handler import handle_llm_exceptions
from ..core.error_monitor import record_error
from ..core.resilience import circuit_breaker, retry_with_backoff

logger = get_logger(__name__)


@dataclass
class LLMRequest:
    """LLM请求数据"""

    title: str
    content: str
    provider: Optional[str] = None
    callback: Optional[callable] = None
    task_type: str = "wiki_page"
    system_prompt: Optional[str] = None


class LLMClient:
    """LLM客户端"""

    def __init__(self, config: Optional[Config] = None):
        self.config = config or get_config()
        self.default_provider = self.config.llm.get("default_provider", "openai")
        self.session = requests.Session()
        self.session.timeout = self.config.llm.get(self.default_provider, {}).get(
            "timeout", 60
        )

        # 批处理相关配置
        self.batch_size = 5  # 每批处理的请求数
        self.batch_interval = 0.5  # 批处理间隔（秒）

        # 批处理队列和锁
        self.request_queue = Queue()
        self.batch_processing = False
        self.batch_lock = threading.Lock()
        self.provider_queues = defaultdict(list)

        # 缓存机制
        self.cache = {}
        self.cache_size = self.config.performance.get("cache_size", 1000)
        self.cache_ttl = self.config.performance.get(
            "cache_ttl", 3600
        )  # 缓存有效期（秒）
        self.cache_lock = threading.Lock()

        # 启动批处理线程
        self.batch_thread = threading.Thread(target=self._batch_processor, daemon=True)
        self.batch_thread.start()

    @handle_llm_exceptions(default_return=None)
    def generate_wiki_page(
        self,
        title: str,
        content: str,
        provider: Optional[str] = None,
        use_batch: bool = True,
        system_prompt: Optional[str] = None,
        task_type: str = "wiki_page",
    ) -> Dict[str, Any]:
        """
        生成Wiki页面或执行其他任务

        Args:
            title: 标题
            content: 内容
            provider: LLM提供商，可选值：openai, anthropic
            use_batch: 是否使用批处理
            system_prompt: 系统提示
            task_type: 任务类型，可选值：wiki_page, entity_extraction
        Returns:
            任务结果
        """
        # 生成缓存键
        cache_key = self._generate_cache_key(title, content, provider, task_type)

        # 检查缓存
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            logger.info(f"使用缓存结果: {title}")
            return cached_result

        if use_batch:
            # 使用批处理
            result_queue = Queue()

            def callback(result):
                # 缓存结果
                self._add_to_cache(cache_key, result)
                result_queue.put(result)

            request = LLMRequest(
                title=title, 
                content=content, 
                provider=provider, 
                callback=callback,
                task_type=task_type,
                system_prompt=system_prompt
            )

            self.request_queue.put(request)
            # 等待批处理结果
            result = result_queue.get()
            return result
        else:
            # 直接调用API
            provider = provider or self.default_provider
            logger.info(f"使用{provider}执行任务 {task_type}: {title}")

            try:
                if provider == "openai":
                    result = self._call_openai_api(title, content, system_prompt, task_type)
                elif provider == "anthropic":
                    result = self._call_anthropic_api(title, content, task_type)
                else:
                    error = LLMError(
                        f"不支持的LLM提供商: {provider}", details={"provider": provider}
                    )
                    record_error(error, {"title": title})
                    logger.error(f"不支持的LLM提供商: {provider}")
                    # 回退到模拟结果
                    result = self._get_mock_result(title, content, task_type)

                # 缓存结果
                self._add_to_cache(cache_key, result)
                return result
            except Exception as e:
                error = LLMError(f"LLM API调用失败: {str(e)}", cause=e)
                record_error(error, {"title": title, "provider": provider, "task_type": task_type})
                logger.error(f"LLM API调用失败: {e}")
                # 出错时回退到模拟结果
                result = self._get_mock_result(title, content, task_type)
                # 缓存模拟结果
                self._add_to_cache(cache_key, result)
                return result

    def _generate_cache_key(
        self, title: str, content: str, provider: Optional[str], task_type: str = "wiki_page"
    ) -> str:
        """
        生成缓存键

        Args:
            title: 标题
            content: 内容
            provider: LLM提供商
            task_type: 任务类型

        Returns:
            缓存键
        """
        provider = provider or self.default_provider
        # 使用标题、内容的前500个字符和任务类型生成哈希作为缓存键
        content_hash = hashlib.md5(content[:500].encode()).hexdigest()
        return f"{provider}:{task_type}:{title}:{content_hash}"

    def _get_from_cache(self, key: str) -> Optional[Dict[str, Any]]:
        """
        从缓存中获取结果

        Args:
            key: 缓存键

        Returns:
            缓存的结果，如果不存在或过期则返回None
        """
        with self.cache_lock:
            if key in self.cache:
                cached_data = self.cache[key]
                timestamp = cached_data["timestamp"]
                result = cached_data["result"]

                # 检查缓存是否过期
                if time.time() - timestamp < self.cache_ttl:
                    return result
                else:
                    # 删除过期缓存
                    del self.cache[key]
        return None

    def _add_to_cache(self, key: str, result: Dict[str, Any]):
        """
        添加结果到缓存

        Args:
            key: 缓存键
            result: 结果
        """
        with self.cache_lock:
            # 检查缓存大小
            if len(self.cache) >= self.cache_size:
                # 删除最旧的缓存
                oldest_key = min(
                    self.cache.keys(), key=lambda k: self.cache[k]["timestamp"]
                )
                del self.cache[oldest_key]

            # 添加到缓存
            self.cache[key] = {"result": result, "timestamp": time.time()}

    def _batch_processor(self):
        """
        批处理处理器线程
        """
        while True:
            time.sleep(self.batch_interval)

            # 收集队列中的请求
            requests = []
            while not self.request_queue.empty() and len(requests) < self.batch_size:
                requests.append(self.request_queue.get())

            if requests:
                logger.info(f"处理批处理请求，共{len(requests)}个")
                self._process_batch(requests)

    def _process_batch(self, requests: List[LLMRequest]):
        """
        处理批处理请求

        Args:
            requests: 请求列表
        """
        # 按提供商分组
        provider_requests = defaultdict(list)
        for req in requests:
            provider = req.provider or self.default_provider
            provider_requests[provider].append(req)

        # 处理每个提供商的请求
        for provider, reqs in provider_requests.items():
            try:
                if provider == "openai":
                    self._batch_call_openai_api(reqs)
                elif provider == "anthropic":
                    self._batch_call_anthropic_api(reqs)
                else:
                    # 对于不支持的提供商，单独处理
                    for req in reqs:
                        result = self._get_mock_result(req.title, req.content)
                        if req.callback:
                            req.callback(result)
            except Exception as e:
                logger.error(f"批处理{provider}请求失败: {e}")
                # 失败时单独处理每个请求
                for req in reqs:
                    result = self._get_mock_result(req.title, req.content)
                    if req.callback:
                        req.callback(result)

    def _batch_call_openai_api(self, requests: List[LLMRequest]):
        """
        批量调用OpenAI API

        Args:
            requests: 请求列表
        """
        openai_config = self.config.llm.get("openai", {})
        api_key = openai_config.get("api_key")
        base_url = openai_config.get("api_base_url", "https://api.openai.com/v1")
        model = openai_config.get("model", "gpt-4")
        temperature = openai_config.get("temperature", 0.3)
        max_tokens = openai_config.get("max_tokens", 4096)

        if not api_key:
            logger.warning("OpenAI API密钥未配置，使用模拟结果")
            for req in requests:
                result = self._get_mock_result(req.title, req.content, req.task_type)
                if req.callback:
                    req.callback(result)
            return

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        # 构建批量请求
        for req in requests:
            # 根据任务类型选择不同的prompt生成方法
            if req.task_type == "entity_extraction":
                prompt = req.content  # 实体抽取任务直接使用content作为prompt
                system_prompt = req.system_prompt or "你是一个实体抽取专家，擅长从文本中提取实体信息。"
            else:
                prompt = self._get_wiki_page_prompt(req.title, req.content)
                system_prompt = req.system_prompt or "你是一个专业的知识库整理助手，擅长将文档内容转化为结构化的Wiki页面。"

            data = {
                "model": model,
                "messages": [
                    {
                        "role": "system",
                        "content": system_prompt,
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
                "response_format": {"type": "json_object"},
            }

            try:
                response = self.session.post(
                    f"{base_url}/chat/completions", headers=headers, json=data
                )
                response.raise_for_status()

                result = response.json()
                wiki_data = json.loads(result["choices"][0]["message"]["content"])
                if req.callback:
                    req.callback(wiki_data)
            except Exception as e:
                logger.error(f"批量调用OpenAI API失败: {e}")
                result = self._get_mock_result(req.title, req.content, req.task_type)
                if req.callback:
                    req.callback(result)

    def _batch_call_anthropic_api(self, requests: List[LLMRequest]):
        """
        批量调用Anthropic API

        Args:
            requests: 请求列表
        """
        anthropic_config = self.config.llm.get("anthropic", {})
        api_key = anthropic_config.get("api_key")
        model = anthropic_config.get("model", "claude-3-opus-20240229")
        temperature = anthropic_config.get("temperature", 0.3)
        max_tokens = anthropic_config.get("max_tokens", 4096)

        if not api_key:
            logger.warning("Anthropic API密钥未配置，使用模拟结果")
            for req in requests:
                result = self._get_mock_result(req.title, req.content, req.task_type)
                if req.callback:
                    req.callback(result)
            return

        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        }

        # 构建批量请求
        for req in requests:
            # 根据任务类型选择不同的prompt生成方法
            if req.task_type == "entity_extraction":
                prompt = req.content  # 实体抽取任务直接使用content作为prompt
            else:
                prompt = self._get_wiki_page_prompt(req.title, req.content)

            data = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
                "max_tokens": max_tokens,
                "response_format": {"type": "json"},
            }

            try:
                response = self.session.post(
                    "https://api.anthropic.com/v1/messages", headers=headers, json=data
                )
                response.raise_for_status()

                result = response.json()
                wiki_data = json.loads(result["content"][0]["text"])
                if req.callback:
                    req.callback(wiki_data)
            except Exception as e:
                logger.error(f"批量调用Anthropic API失败: {e}")
                result = self._get_mock_result(req.title, req.content, req.task_type)
                if req.callback:
                    req.callback(result)

    @circuit_breaker(failure_threshold=3, recovery_timeout=30)
    @retry_with_backoff(max_retries=3, base_delay=1.0, backoff_factor=2.0)
    def _call_openai_api(self, title: str, content: str, system_prompt: Optional[str] = None, task_type: str = "wiki_page") -> Dict[str, Any]:
        """
        调用OpenAI API

        Args:
            title: 标题
            content: 内容
            system_prompt: 系统提示
            task_type: 任务类型

        Returns:
            任务结果
        """
        openai_config = self.config.llm.get("openai", {})
        api_key = openai_config.get("api_key")
        base_url = openai_config.get("api_base_url", "https://api.openai.com/v1")
        model = openai_config.get("model", "gpt-4")
        temperature = openai_config.get("temperature", 0.3)
        max_tokens = openai_config.get("max_tokens", 4096)
        
        if system_prompt is None:
            if task_type == "entity_extraction":
                system_prompt = "你是一个实体抽取专家，擅长从文本中提取实体信息。"
            else:
                system_prompt = "你是一个专业的知识库整理助手，擅长将文档内容转化为结构化的Wiki页面。"

        if not api_key:
            error = ConfigurationError("OpenAI API密钥未配置")
            record_error(error, {"title": title, "task_type": task_type})
            logger.warning("OpenAI API密钥未配置，使用模拟结果")
            return self._get_mock_result(title, content, task_type)

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        # 根据任务类型选择不同的prompt生成方法
        if task_type == "entity_extraction":
            prompt = content  # 实体抽取任务直接使用content作为prompt
        else:
            prompt = self._get_wiki_page_prompt(title, content)

        logger.info(f"执行任务 {task_type}，使用系统提示: {system_prompt[:100]}...")
        logger.debug(f"执行任务 {task_type}，使用prompt: {prompt[:200]}...")

        data = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
        }

        try:
            response = self.session.post(
                f"{base_url}/chat/completions", headers=headers, json=data
            )
            response.raise_for_status()

            result = response.json()
            wiki_data = json.loads(result["choices"][0]["message"]["content"])
            return wiki_data
        except requests.exceptions.Timeout as e:
            error = TimeoutError(f"OpenAI API调用超时: {str(e)}", cause=e)
            record_error(error, {"title": title, "provider": "openai", "task_type": task_type})
            raise
        except requests.exceptions.RequestException as e:
            error = NetworkError(f"OpenAI API网络错误: {str(e)}", cause=e)
            record_error(error, {"title": title, "provider": "openai", "task_type": task_type})
            raise
        except json.JSONDecodeError as e:
            error = LLMError(f"解析OpenAI响应失败: {str(e)}", cause=e)
            record_error(error, {"title": title, "provider": "openai", "task_type": task_type})
            raise

    @circuit_breaker(failure_threshold=3, recovery_timeout=30)
    @retry_with_backoff(max_retries=3, base_delay=1.0, backoff_factor=2.0)
    def _call_anthropic_api(self, title: str, content: str, task_type: str = "wiki_page") -> Dict[str, Any]:
        """
        调用Anthropic API

        Args:
            title: 标题
            content: 内容
            task_type: 任务类型

        Returns:
            任务结果
        """
        anthropic_config = self.config.llm.get("anthropic", {})
        api_key = anthropic_config.get("api_key")
        model = anthropic_config.get("model", "claude-3-opus-20240229")
        temperature = anthropic_config.get("temperature", 0.3)
        max_tokens = anthropic_config.get("max_tokens", 4096)

        if not api_key:
            error = ConfigurationError("Anthropic API密钥未配置")
            record_error(error, {"title": title, "task_type": task_type})
            logger.warning("Anthropic API密钥未配置，使用模拟结果")
            return self._get_mock_result(title, content, task_type)

        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        }

        # 根据任务类型选择不同的prompt生成方法
        if task_type == "entity_extraction":
            prompt = content  # 实体抽取任务直接使用content作为prompt
        else:
            prompt = self._get_wiki_page_prompt(title, content)

        data = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response_format": {"type": "json"},
        }

        try:
            response = self.session.post(
                "https://api.anthropic.com/v1/messages", headers=headers, json=data
            )
            response.raise_for_status()

            result = response.json()
            wiki_data = json.loads(result["content"][0]["text"])
            return wiki_data
        except requests.exceptions.Timeout as e:
            error = TimeoutError(f"Anthropic API调用超时: {str(e)}", cause=e)
            record_error(error, {"title": title, "provider": "anthropic", "task_type": task_type})
            raise
        except requests.exceptions.RequestException as e:
            error = NetworkError(f"Anthropic API网络错误: {str(e)}", cause=e)
            record_error(error, {"title": title, "provider": "anthropic", "task_type": task_type})
            raise
        except json.JSONDecodeError as e:
            error = LLMError(f"解析Anthropic响应失败: {str(e)}", cause=e)
            record_error(error, {"title": title, "provider": "anthropic", "task_type": task_type})
            raise

    def _get_wiki_page_prompt(self, title: str, content: str) -> str:
        """
        获取Wiki页面生成提示词

        Args:
            title: 标题
            content: 内容

        Returns:
            提示词
        """
        # 优化提示词，减少token使用
        # 1. 缩短指令文本
        # 2. 更精确的内容限制
        # 3. 标准化JSON格式要求
        prompt = f"# 任务：生成Wiki页面\n\n"
        prompt += f"## 标题\n{title}\n\n"
        prompt += f"## 内容\n{content[:8000]}...\n\n"  # 进一步限制内容长度
        prompt += "## 输出要求\n"
        prompt += "- 结构化整理内容\n"
        prompt += "- 生成不超过150字的摘要\n"
        prompt += "- 提取相关标签\n"
        prompt += "- 识别相关主题\n\n"
        prompt += "## 返回格式\n"
        prompt += "```json\n"
        prompt += "{\n"
        prompt += '  "title": "页面标题",\n'
        prompt += '  "content": "结构化内容",\n'
        prompt += '  "summary": "页面摘要",\n'
        prompt += '  "category": "分类",\n'
        prompt += '  "tags": ["标签1", "标签2"],\n'
        prompt += '  "related_topics": ["主题1", "主题2"]\n'
        prompt += "}\n"
        prompt += "```\n\n"
        prompt += "请严格按照JSON格式返回，不要添加任何额外内容。"
        return prompt

    def _get_mock_result(self, title: str, content: str, task_type: str = "wiki_page") -> Dict[str, Any]:
        """
        获取模拟结果

        Args:
            title: 标题
            content: 内容
            task_type: 任务类型

        Returns:
            任务结果
        """
        if task_type == "entity_extraction":
            # 实体抽取任务的模拟结果
            return {
                "entities": [
                    {
                        "id": "1",
                        "name": "测试",
                        "type": "CONCEPT",
                        "start_pos": 0,
                        "end_pos": 2
                    }
                ],
                "relations": []
            }
        else:
            # Wiki页面任务的模拟结果
            return {
                "title": title,
                "content": content,
                "summary": f"这是关于{title}的摘要",
                "category": "默认分类",
                "tags": ["测试", "文档"],
                "related_topics": ["相关主题1", "相关主题2"],
            }


# 全局LLM客户端实例
llm_client = LLMClient()


def get_llm_client() -> LLMClient:
    """
    获取LLM客户端

    Returns:
        LLM客户端
    """
    return llm_client
