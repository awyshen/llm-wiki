"""
实体提取器

从文档中提取实体并建立实体关系。
"""

import re
import spacy
from typing import List, Dict, Any
from ..core.config import get_config
from ..core.logger import get_logger
from ..core.error_handler import ErrorHandler

logger = get_logger(__name__)


class EntityExtractor:
    """实体提取器"""

    def __init__(self):
        """初始化实体提取器"""
        self.config = get_config()
        self.nlp = None
        self._load_spacy_model()

    def _load_spacy_model(self):
        """加载Spacy模型"""
        try:
            # 尝试加载中文模型
            self.nlp = spacy.load("zh_core_web_sm")
            logger.info("加载中文Spacy模型成功")
        except Exception as e:
            try:
                # 尝试加载英文模型
                self.nlp = spacy.load("en_core_web_sm")
                logger.info("加载英文Spacy模型成功")
            except Exception as e2:
                logger.warning(f"无法加载Spacy模型: {e2}")
                self.nlp = None

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

        entities = []

        # 使用Spacy提取实体
        if self.nlp:
            doc = self.nlp(text)
            for ent in doc.ents:
                entity = {
                    "id": str(id(ent)),  # 临时ID，实际应用中应该使用更稳定的ID生成方法
                    "name": ent.text,
                    "type": ent.label_,
                    "start_pos": ent.start_char,
                    "end_pos": ent.end_char
                }
                entities.append(entity)
        else:
            # 如果没有Spacy模型，使用简单的规则提取
            entities = self._extract_entities_simple(text)

        return entities

    def _extract_entities_simple(self, text: str) -> List[Dict[str, Any]]:
        """
        使用简单规则提取实体

        Args:
            text: 要提取实体的文本

        Returns:
            提取的实体列表
        """
        entities = []

        # 提取可能的人名（简单规则）
        # 这里只是示例，实际应用中需要更复杂的规则
        name_patterns = [
            r"[\u4e00-\u9fa5]{2,4}",  # 中文名字
            r"[A-Z][a-z]+\s+[A-Z][a-z]+"  # 英文名字
        ]

        for pattern in name_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                entity = {
                    "id": str(id(match)),
                    "name": match.group(),
                    "type": "PERSON",
                    "start_pos": match.start(),
                    "end_pos": match.end()
                }
                entities.append(entity)

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
        relations = []

        # 简单的关系提取示例
        # 实际应用中可能需要使用更复杂的NLP技术
        if len(entities) >= 2:
            # 提取相邻实体之间的关系
            for i in range(len(entities) - 1):
                entity1 = entities[i]
                entity2 = entities[i + 1]

                # 提取两个实体之间的文本
                relation_text = text[entity1["end_pos"]:entity2["start_pos"]].strip()

                if relation_text:
                    relation = {
                        "id": f"{entity1['id']}_{entity2['id']}",
                        "subject": entity1["id"],
                        "object": entity2["id"],
                        "predicate": relation_text,
                        "confidence": 0.5  # 简单规则的置信度
                    }
                    relations.append(relation)

        return relations

    @ErrorHandler.handle_processing_exceptions()
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
            type_mapping = {
                "PERSON": "人物",
                "ORG": "组织",
                "GPE": "地点",
                "LOC": "地点",
                "DATE": "日期",
                "TIME": "时间",
                "MONEY": "货币",
                "PERCENT": "百分比",
                "FAC": "设施",
                "PRODUCT": "产品",
                "EVENT": "事件",
                "WORK_OF_ART": "艺术作品",
                "LAW": "法律",
                "LANGUAGE": "语言",
                "NORP": "民族/宗教/政治团体",
                "ORDINAL": "序数",
                "CARDINAL": "基数"
            }

            if enhanced_entity["type"] in type_mapping:
                enhanced_entity["type_cn"] = type_mapping[enhanced_entity["type"]]
            else:
                enhanced_entity["type_cn"] = enhanced_entity["type"]

            enhanced_entities.append(enhanced_entity)

        return enhanced_entities

    def get_entity_statistics(self, entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        获取实体统计信息

        Args:
            entities: 实体列表

        Returns:
            实体统计信息
        """
        stats = {
            "total": len(entities),
            "by_type": {}
        }

        for entity in entities:
            entity_type = entity["type"]
            if entity_type not in stats["by_type"]:
                stats["by_type"][entity_type] = 0
            stats["by_type"][entity_type] += 1

        return stats
