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
    def extract_entities(self, text: str, extract_important_only: bool = True) -> List[Dict[str, Any]]:
        """
        从文本中提取实体

        Args:
            text: 要提取实体的文本
            extract_important_only: 是否只提取重要实体

        Returns:
            提取的实体列表
        """
        if not text:
            return []

        # 生成缓存键
        cache_key = self._generate_cache_key(text, f"entities_{extract_important_only}")
        
        # 检查缓存
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            logger.debug("从缓存获取实体抽取结果")
            return cached_result

        # 构建提示词
        prompt = self._get_entity_extraction_prompt(text, extract_important_only)
        
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
        
        # 评估实体重要性
        if extract_important_only:
            entities = self._evaluate_entity_importance(entities, text)
        
        # 缓存结果
        self._add_to_cache(cache_key, entities)
        
        return entities
    
    def _evaluate_entity_importance(self, entities: List[Dict[str, Any]], text: str) -> List[Dict[str, Any]]:
        """
        评估实体重要性

        Args:
            entities: 实体列表
            text: 原始文本

        Returns:
            重要实体列表
        """
        important_entities = []
        
        # 计算文本长度
        text_length = len(text)
        
        # 计算实体频率
        entity_freq = {}
        for entity in entities:
            entity_name = entity.get("name", "").strip()
            if entity_name:
                entity_freq[entity_name] = entity_freq.get(entity_name, 0) + 1
        
        # 评估每个实体的重要性
        for entity in entities:
            entity_name = entity.get("name", "").strip()
            entity_type = entity.get("type", "").strip()
            start_pos = entity.get("start_pos", 0)
            end_pos = entity.get("end_pos", 0)
            
            # 计算重要性分数
            importance_score = 0.0
            
            # 1. 基于实体类型的重要性
            type_importance = {
                "PERSON": 0.9,
                "ORG": 0.8,
                "LOCATION": 0.7,
                "TECHNOLOGY": 0.85,
                "PRODUCT": 0.75,
                "CONCEPT": 0.7,
                "EVENT": 0.8,
                "DOCUMENT": 0.6,
                "LAW": 0.85,
                "WORK_OF_ART": 0.6,
                "FAC": 0.6,
                "GPE": 0.7,
                "LIVNG_BEING": 0.6,
                "MATERIAL": 0.5,
                "MEASURE": 0.5,
                "ORGANIZATION": 0.8,
                "PHENOMENON": 0.6,
                "PROCESS": 0.6,
                "SUBSTANCE": 0.5,
                "SYMBOL": 0.5,
                "VEHICLE": 0.5,
                "TIME": 0.6,
                "VALUE": 0.5,
                "DATE": 0.6,
                "MONEY": 0.7,
                "PERCENT": 0.6,
                "CARDINAL": 0.4,
                "ORDINAL": 0.4
            }
            
            if entity_type in type_importance:
                importance_score += type_importance[entity_type]
            else:
                importance_score += 0.5
            
            # 2. 基于出现频率的重要性
            freq = entity_freq.get(entity_name, 1)
            freq_score = min(freq / 10, 1.0)  # 最多加1.0分
            importance_score += freq_score * 0.3
            
            # 3. 基于位置的重要性（文本开头的实体更重要）
            position_score = 1.0 - (start_pos / text_length)
            importance_score += position_score * 0.2
            
            # 4. 基于实体长度的重要性（太长或太短的实体可能不太重要）
            entity_length = len(entity_name)
            if 2 <= entity_length <= 20:
                length_score = 1.0
            elif entity_length < 2:
                length_score = 0.3
            else:
                length_score = max(0.5, 1.0 - (entity_length - 20) / 50)
            importance_score += length_score * 0.1
            
            # 标准化分数
            importance_score = min(importance_score, 2.0) / 2.0
            
            # 添加重要性分数
            entity["importance_score"] = importance_score
            
            # 只保留重要性分数大于0.6的实体
            if importance_score > 0.6:
                important_entities.append(entity)
        
        # 按重要性分数排序
        important_entities.sort(key=lambda x: x.get("importance_score", 0), reverse=True)
        
        # 限制返回实体数量
        max_entities = 50  # 最多返回50个实体
        important_entities = important_entities[:max_entities]
        
        logger.info(f"重要实体提取完成，保留 {len(important_entities)} 个实体")
        return important_entities

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

    def _get_entity_extraction_prompt(self, text: str, extract_important_only: bool = True) -> str:
        """
        获取实体抽取提示词

        Args:
            text: 要提取实体的文本
            extract_important_only: 是否只提取重要实体

        Returns:
            提示词
        """
        entity_types_str = ", ".join([f"{k} ({v})" for k, v in self.entity_types.items()])
        
        prompt = f"# 任务：实体抽取\n\n"
        prompt += f"## 文本\n{text[:4000]}...\n\n"  # 限制文本长度
        prompt += "## 实体类型\n"
        prompt += f"{entity_types_str}\n\n"
        prompt += "## 输出要求\n"
        if extract_important_only:
            prompt += "- 从文本中提取关键实体，过滤掉次要或无关实体\n"
            prompt += "- 关键实体通常是：人物、组织、地点、技术、产品、概念、事件等\n"
            prompt += "- 过滤掉：常见的虚词、冠词、介词等无意义的词语\n"
        else:
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
            
            # 时间格式标准化处理
            if entity_type in ["TIME", "DATE"]:
                entity_name = enhanced_entity.get("name", "").strip()
                if entity_name:
                    standard_time = self._standardize_time_format(entity_name)
                    if standard_time:
                        enhanced_entity["standard_time"] = standard_time

            enhanced_entities.append(enhanced_entity)

        return enhanced_entities
    
    def _standardize_time_format(self, time_str: str) -> Optional[str]:
        """
        标准化时间格式

        Args:
            time_str: 时间字符串

        Returns:
            标准化后的时间字符串，格式为YYYY-MM-DD HH:MM:SS，若无法解析则返回None
        """
        import re
        from datetime import datetime
        
        # 常见时间格式模式
        patterns = [
            # 格式：YYYY-MM-DD HH:MM:SS
            (r'^(\d{4})[-/](\d{1,2})[-/](\d{1,2})\s+(\d{1,2}):(\d{2}):(\d{2})$', '%Y-%m-%d %H:%M:%S'),
            # 格式：YYYY-MM-DD HH:MM
            (r'^(\d{4})[-/](\d{1,2})[-/](\d{1,2})\s+(\d{1,2}):(\d{2})$', '%Y-%m-%d %H:%M'),
            # 格式：YYYY-MM-DD
            (r'^(\d{4})[-/](\d{1,2})[-/](\d{1,2})$', '%Y-%m-%d'),
            # 格式：MM-DD-YYYY
            (r'^(\d{1,2})[-/](\d{1,2})[-/](\d{4})$', '%m-%d-%Y'),
            # 格式：YYYY年MM月DD日
            (r'^(\d{4})年(\d{1,2})月(\d{1,2})日$', '%Y年%m月%d日'),
            # 格式：YYYY年MM月
            (r'^(\d{4})年(\d{1,2})月$', '%Y年%m月'),
            # 格式：MM/DD/YYYY HH:MM:SS
            (r'^(\d{1,2})/(\d{1,2})/(\d{4})\s+(\d{1,2}):(\d{2}):(\d{2})$', '%m/%d/%Y %H:%M:%S'),
            # 格式：MM/DD/YYYY HH:MM
            (r'^(\d{1,2})/(\d{1,2})/(\d{4})\s+(\d{1,2}):(\d{2})$', '%m/%d/%Y %H:%M'),
            # 格式：MM/DD/YYYY
            (r'^(\d{1,2})/(\d{1,2})/(\d{4})$', '%m/%d/%Y'),
        ]
        
        # 尝试匹配每种模式
        for pattern, format_str in patterns:
            match = re.match(pattern, time_str)
            if match:
                try:
                    # 解析时间
                    dt = datetime.strptime(time_str, format_str)
                    # 格式化为标准格式
                    return dt.strftime('%Y-%m-%d %H:%M:%S')
                except ValueError:
                    continue
        
        # 处理相对时间
        relative_patterns = [
            # 今天
            (r'^今天$', lambda: datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
            # 昨天
            (r'^昨天$', lambda: (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')),
            # 明天
            (r'^明天$', lambda: (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')),
            # 本周
            (r'^本周$', lambda: datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
            # 上周
            (r'^上周$', lambda: (datetime.now() - timedelta(weeks=1)).strftime('%Y-%m-%d %H:%M:%S')),
            # 本月
            (r'^本月$', lambda: datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
            # 上月
            (r'^上月$', lambda: (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')),
            # 今年
            (r'^今年$', lambda: datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
            # 去年
            (r'^去年$', lambda: (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d %H:%M:%S')),
        ]
        
        for pattern, func in relative_patterns:
            if re.match(pattern, time_str):
                try:
                    from datetime import timedelta
                    return func()
                except Exception:
                    continue
        
        # 处理时间点
        time_point_patterns = [
            # 格式：HH:MM:SS
            (r'^(\d{1,2}):(\d{2}):(\d{2})$', '%H:%M:%S'),
            # 格式：HH:MM
            (r'^(\d{1,2}):(\d{2})$', '%H:%M'),
        ]
        
        for pattern, format_str in time_point_patterns:
            match = re.match(pattern, time_str)
            if match:
                try:
                    # 解析时间
                    dt = datetime.strptime(time_str, format_str)
                    # 使用当前日期
                    today = datetime.now().strftime('%Y-%m-%d')
                    # 格式化为标准格式
                    return f"{today} {dt.strftime('%H:%M:%S')}"
                except ValueError:
                    continue
        
        # 无法解析的时间格式
        logger.debug(f"无法标准化时间格式: {time_str}")
        return None

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
