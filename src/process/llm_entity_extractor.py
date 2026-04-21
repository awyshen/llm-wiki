"""
基于LLM的实体提取器

使用LLM进行实体抽取和关系提取，支持扩展实体类型。
"""

import json
import hashlib
from typing import List, Dict, Any, Optional
from ..core.config import get_config
from ..core.logger import get_logger
from ..core.error_handler import ErrorHandler
from .llm_client import get_llm_client

logger = get_logger(__name__)


class LLMEntityExtractor:
    """基于LLM的实体提取器"""

    def __init__(self):
        """初始化基于LLM的实体提取器"""
        self.config = get_config()
        self.llm_client = get_llm_client()
        
        # 实体类型定义
        self.entity_types = {
            # 基础实体类型
            "PERSON": "人物",
            "ORG": "组织",
            "LOCATION": "地点",
            "TIME": "时间",
            "VALUE": "数值",
            "DATE": "日期",
            "MONEY": "货币",
            "PERCENT": "百分比",
            "CARDINAL": "基数",
            "ORDINAL": "序数",
            
            # 扩展实体类型
            "TECHNOLOGY": "技术",
            "PRODUCT": "产品",
            "CONCEPT": "概念",
            "EVENT": "事件",
            "DOCUMENT": "文档",
            "LANGUAGE": "语言",
            "LAW": "法律",
            "WORK_OF_ART": "艺术作品",
            "FAC": "设施",
            "GPE": "地缘政治实体",
            "LIVNG_BEING": "生物",
            "MATERIAL": "材料",
            "MEASURE": "度量",
            "ORGANIZATION": "组织",
            "PHENOMENON": "现象",
            "PROCESS": "过程",
            "SUBSTANCE": "物质",
            "SYMBOL": "符号",
            "VEHICLE": "交通工具"
        }
        
        # 缓存机制
        self.cache = {}
        self.cache_size = 1000
        self.cache_ttl = 3600  # 缓存有效期（秒）

    @ErrorHandler.handle_processing_exceptions()
    def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """
        从文本中提取实体

        Args:
            text: 要提取实体的文本

        Returns:
            提取的实体列表
        """
        if not text:
            return []

        # 生成缓存键
        cache_key = self._generate_cache_key(text, "entities")
        
        # 检查缓存
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            logger.debug("从缓存获取实体抽取结果")
            return cached_result

        # 构建提示词
        prompt = self._get_entity_extraction_prompt(text)
        # logger.info(f"实体抽取提示词: {prompt}")
        
        # 调用LLM
        try:
            result = self.llm_client.generate_wiki_page(
                title="实体抽取",
                content=prompt,
                use_batch=False,
                system_prompt="你是一个实体抽取专家，擅长从文本中提取实体信息。",
                task_type="entity_extraction"
            )
            
            # 解析结果
            entities = self._parse_entity_result(result)
            logger.info(f"实体抽取结果: {entities}")
        except Exception as e:
            logger.error(f"LLM实体抽取失败: {e}")
            # 回退到基础实体抽取
            from .entity_extractor import EntityExtractor
            base_extractor = EntityExtractor()
            entities = base_extractor.extract_entities(text)

        # 增强实体信息
        entities = self.enhance_entities(entities)
        
        # 缓存结果
        self._add_to_cache(cache_key, entities)
        
        return entities

    @ErrorHandler.handle_processing_exceptions()
    def extract_entity_relations(self, text: str, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        提取实体之间的关系

        Args:
            text: 文本
            entities: 实体列表

        Returns:
            实体关系列表
        """
        if not text or not entities:
            return []

        # 生成缓存键
        cache_key = self._generate_cache_key(text + str(entities), "relations")
        
        # 检查缓存
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            logger.debug("从缓存获取关系提取结果")
            return cached_result

        # 构建提示词
        prompt = self._get_relation_extraction_prompt(text, entities)
        
        # 调用LLM
        try:
            result = self.llm_client.generate_wiki_page(
                title="关系提取",
                content=prompt,
                use_batch=False,
                system_prompt="你是一个关系提取专家，擅长从文本中提取实体之间的关系。",
                task_type="entity_extraction"
            )
            
            # 解析结果
            relations = self._parse_relation_result(result)
        except Exception as e:
            logger.error(f"LLM关系提取失败: {e}")
            # 回退到基础关系提取
            from .entity_extractor import EntityExtractor
            base_extractor = EntityExtractor()
            relations = base_extractor.extract_entity_relations(text, entities)

        # 缓存结果
        self._add_to_cache(cache_key, relations)
        
        return relations

    def _get_entity_extraction_prompt(self, text: str) -> str:
        """
        获取实体抽取提示词

        Args:
            text: 要提取实体的文本

        Returns:
            提示词
        """
        entity_types_str = ", ".join([f"{k} ({v})" for k, v in self.entity_types.items()])
        
        prompt = f"# 任务：实体抽取\n\n"
        prompt += f"## 文本\n{text[:4000]}...\n\n"  # 限制文本长度
        prompt += "## 实体类型\n"
        prompt += f"{entity_types_str}\n\n"
        prompt += "## 输出要求\n"
        prompt += "- 从文本中提取所有实体\n"
        prompt += "- 为每个实体指定正确的类型\n"
        prompt += "- 提供实体在文本中的起始和结束位置\n"
        prompt += "- 只提取有意义的实体，避免提取无意义的词语\n\n"
        prompt += "## 返回格式\n"
        prompt += "```json\n"
        prompt += "{\n"
        prompt += '  "entities": [\n'
        prompt += '    {\n'
        prompt += '      "id": "实体ID",\n'
        prompt += '      "name": "实体名称",\n'
        prompt += '      "type": "实体类型",\n'
        prompt += '      "start_pos": 起始位置,\n'
        prompt += '      "end_pos": 结束位置\n'
        prompt += '    }\n'
        prompt += '  ]\n'
        prompt += "}\n"
        prompt += "```\n\n"
        prompt += "请严格按照JSON格式返回，不要添加任何额外内容。"
        
        return prompt

    def _get_relation_extraction_prompt(self, text: str, entities: List[Dict[str, Any]]) -> str:
        """
        获取关系提取提示词

        Args:
            text: 文本
            entities: 实体列表

        Returns:
            提示词
        """
        entities_str = json.dumps(entities, ensure_ascii=False, indent=2)
        
        prompt = f"# 任务：关系提取\n\n"
        prompt += f"## 文本\n{text[:4000]}...\n\n"  # 限制文本长度
        prompt += "## 实体列表\n"
        prompt += f"{entities_str}\n\n"
        prompt += "## 输出要求\n"
        prompt += "- 提取实体之间的关系\n"
        prompt += "- 为每个关系指定主语、宾语和谓词\n"
        prompt += "- 提供关系的置信度\n"
        prompt += "- 只提取有意义的关系\n\n"
        prompt += "## 返回格式\n"
        prompt += "```json\n"
        prompt += "{\n"
        prompt += '  "relations": [\n'
        prompt += '    {\n'
        prompt += '      "id": "关系ID",\n'
        prompt += '      "subject": "主语实体ID",\n'
        prompt += '      "object": "宾语实体ID",\n'
        prompt += '      "predicate": "谓词",\n'
        prompt += '      "confidence": 置信度\n'
        prompt += '    }\n'
        prompt += '  ]\n'
        prompt += "}\n"
        prompt += "```\n\n"
        prompt += "请严格按照JSON格式返回，不要添加任何额外内容。"
        
        return prompt

    def _parse_entity_result(self, result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        解析实体抽取结果

        Args:
            result: LLM返回的结果

        Returns:
            实体列表
        """
        entities = []
        
        try:
            if "entities" in result:
                entities = result["entities"]
        except Exception as e:
            logger.error(f"解析实体结果失败: {e}")
            entities = []
        
        return entities

    def _parse_relation_result(self, result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        解析关系提取结果

        Args:
            result: LLM返回的结果

        Returns:
            关系列表
        """
        relations = []
        
        try:
            if "relations" in result:
                relations = result["relations"]
        except Exception as e:
            logger.error(f"解析关系结果失败: {e}")
            relations = []
        
        return relations

    def _generate_cache_key(self, text: str, task: str) -> str:
        """
        生成缓存键

        Args:
            text: 文本内容
            task: 任务类型

        Returns:
            缓存键
        """
        text_hash = hashlib.md5(text[:1000].encode()).hexdigest()
        return f"{task}:{text_hash}"

    def _get_from_cache(self, key: str) -> Optional[List[Dict[str, Any]]]:
        """
        从缓存中获取结果

        Args:
            key: 缓存键

        Returns:
            缓存的结果，如果不存在或过期则返回None
        """
        import time
        
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

    def _add_to_cache(self, key: str, result: List[Dict[str, Any]]):
        """
        添加结果到缓存

        Args:
            key: 缓存键
            result: 结果
        """
        import time
        
        # 检查缓存大小
        if len(self.cache) >= self.cache_size:
            # 删除最旧的缓存
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k]["timestamp"])
            del self.cache[oldest_key]
        
        # 添加到缓存
        self.cache[key] = {"result": result, "timestamp": time.time()}

    def enhance_entities(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        增强实体信息

        Args:
            entities: 实体列表

        Returns:
            增强后的实体列表
        """
        enhanced_entities = []

        for entity in entities:
            enhanced_entity = entity.copy()

            # 添加实体类型的中文标签
            entity_type = enhanced_entity.get("type", "")
            if entity_type in self.entity_types:
                enhanced_entity["type_cn"] = self.entity_types[entity_type]
            else:
                enhanced_entity["type_cn"] = entity_type

            enhanced_entities.append(enhanced_entity)

        return enhanced_entities

    def get_entity_types(self) -> Dict[str, str]:
        """
        获取支持的实体类型

        Returns:
            实体类型字典
        """
        return self.entity_types


# 全局LLM实体提取器实例
llm_entity_extractor = LLMEntityExtractor()


def get_llm_entity_extractor() -> LLMEntityExtractor:
    """
    获取LLM实体提取器实例

    Returns:
        LLM实体提取器实例
    """
    return llm_entity_extractor
