"""
知识图谱构建器

从文档和Wiki页面中提取实体和关系，构建知识图谱。
"""

from typing import List, Dict, Any, Optional, Tuple
import uuid
import re
import time
from difflib import SequenceMatcher
from ..core.config import get_config
from ..core.logger import get_logger
from ..core.error_handler import ErrorHandler
from .llm_entity_extractor import get_llm_entity_extractor
from ..storage.database import get_db_manager
from ..storage.models import WikiPage, Document, Entity, EntityRelationship

logger = get_logger(__name__)


class KnowledgeGraphBuilder:
    """知识图谱构建器"""

    def __init__(self):
        """初始化知识图谱构建器"""
        self.config = get_config()
        self.db = get_db_manager()
        self.entity_extractor = get_llm_entity_extractor()
        
        # 知识图谱数据结构
        self.graph = {
            "entities": {},  # 实体字典，键为实体ID，值为实体信息
            "relations": []  # 关系列表
        }
        
        # 不确定实体存储，用于存储匹配度未达阈值的实体
        self.uncertain_entities = []

    @ErrorHandler.handle_processing_exceptions()
    def build_from_wiki_page(self, page_id: str) -> Dict[str, Any]:
        """
        从Wiki页面构建知识图谱

        Args:
            page_id: Wiki页面ID

        Returns:
            构建的知识图谱
        """
        try:
            logger.info(f"从Wiki页面构建知识图谱: {page_id}")
            
            # 获取Wiki页面
            with self.db.get_session() as session:
                page = session.query(WikiPage).filter(WikiPage.id == page_id).first()
                if not page:
                    logger.error(f"Wiki页面不存在: {page_id}")
                    return self.graph
            
            # 提取实体
            entities = self.entity_extractor.extract_entities(page.content)
            
            # 提取实体关系
            relations = self.entity_extractor.extract_entity_relations(page.content, entities)
            
            # 构建知识图谱
            self._build_graph(entities, relations, page.id, "wiki_page")
            
            logger.info(f"从Wiki页面构建知识图谱完成，实体数: {len(self.graph['entities'])}, 关系数: {len(self.graph['relations'])}")
            return self.graph
        except Exception as e:
            logger.error(f"从Wiki页面构建知识图谱失败: {e}")
            return self.graph

    @ErrorHandler.handle_processing_exceptions()
    def build_from_document(self, document_id: str) -> Dict[str, Any]:
        """
        从文档构建知识图谱

        Args:
            document_id: 文档ID

        Returns:
            构建的知识图谱
        """
        try:
            logger.info(f"从文档构建知识图谱: {document_id}")
            
            # 获取文档
            with self.db.get_session() as session:
                document = session.query(Document).filter(Document.id == document_id).first()
                if not document:
                    logger.error(f"文档不存在: {document_id}")
                    return self.graph
            
            # 提取实体
            entities = self.entity_extractor.extract_entities(document.extracted_text)
            
            # 提取实体关系
            relations = self.entity_extractor.extract_entity_relations(document.extracted_text, entities)
            
            # 构建知识图谱
            self._build_graph(entities, relations, document.id, "document")
            
            logger.info(f"从文档构建知识图谱完成，实体数: {len(self.graph['entities'])}, 关系数: {len(self.graph['relations'])}")
            return self.graph
        except Exception as e:
            logger.error(f"从文档构建知识图谱失败: {e}")
            return self.graph

    @ErrorHandler.handle_processing_exceptions()
    def build_from_text(self, text: str, source_id: str, source_type: str) -> Dict[str, Any]:
        """
        从文本构建知识图谱

        Args:
            text: 文本内容
            source_id: 来源ID
            source_type: 来源类型（wiki_page 或 document）

        Returns:
            构建的知识图谱
        """
        try:
            logger.info(f"从文本构建知识图谱: {source_id}")
            
            # 提取实体
            entities = self.entity_extractor.extract_entities(text)
            
            # 提取实体关系
            relations = self.entity_extractor.extract_entity_relations(text, entities)
            
            # 构建知识图谱
            self._build_graph(entities, relations, source_id, source_type)
            
            logger.info(f"从文本构建知识图谱完成，实体数: {len(self.graph['entities'])}, 关系数: {len(self.graph['relations'])}")
            return self.graph
        except Exception as e:
            logger.error(f"从文本构建知识图谱失败: {e}")
            return self.graph

    def _build_graph(self, entities: List[Dict[str, Any]], relations: List[Dict[str, Any]], source_id: str, source_type: str):
        """
        构建知识图谱

        Args:
            entities: 实体列表
            relations: 关系列表
            source_id: 来源ID
            source_type: 来源类型
        """
        # 实体ID映射，用于更新关系中的实体ID
        entity_id_map = {}
        entity_name_map = {}  # 用于通过实体名称查找实体ID，避免重复
        
        # 添加实体
        for entity in entities:
            original_id = entity.get("id")
            entity_name = entity.get("name", "").strip()
            entity_type = entity.get("type", "其他")
            entity_description = entity.get("description", "")
            entity_attributes = entity.get("attributes", {})  # 实体属性
            
            # 查找匹配的现有实体
            matching_entity_id = self._find_matching_entity(entity)
            
            if matching_entity_id:
                # 使用匹配的现有实体ID
                entity_id = matching_entity_id
                # 更新现有实体的信息
                existing_entity = self.graph["entities"].get(entity_id)
                if existing_entity:
                    # 合并属性
                    existing_attributes = existing_entity.get("attributes", {})
                    merged_attributes = {**existing_attributes, **entity_attributes}  # 后者覆盖前者
                    existing_entity["attributes"] = merged_attributes
                    # 如果有新的描述，使用新的描述
                    if entity_description and not existing_entity.get("description"):
                        existing_entity["description"] = entity_description
            else:
                # 生成新的实体ID
                if entity_name:
                    # 生成唯一的实体ID
                    entity_id = f"{source_type}_{source_id}_{entity.get('start_pos', 0)}"
                else:
                    # 没有实体名称时，使用位置信息生成ID
                    entity_id = f"{source_type}_{source_id}_{entity.get('start_pos', 0)}"
                
                # 确保实体ID唯一
                counter = 1
                base_entity_id = entity_id
                while entity_id in self.graph["entities"]:
                    entity_id = f"{base_entity_id}_{counter}"
                    counter += 1
                
                # 丰富实体信息
                entity_info = {
                    "id": entity_id,
                    "name": entity_name,
                    "type": entity_type,
                    "description": entity_description,
                    "attributes": entity_attributes,
                    "source_id": source_id,
                    "source_type": source_type
                }
                
                self.graph["entities"][entity_id] = entity_info
            
            # 记录实体ID映射
            if original_id:
                entity_id_map[original_id] = entity_id
            if entity_name:
                entity_name_map[entity_name] = entity_id
        
        # 添加关系
        added_relations = set()  # 用于避免重复关系
        for relation in relations:
            # 确保关系中的实体ID存在
            subject_id = relation.get("subject")
            object_id = relation.get("object")
            predicate = relation.get("predicate", "").strip()
            confidence = relation.get("confidence", 0.0)
            relation_attributes = relation.get("attributes", {})  # 关系属性
            
            if not subject_id or not object_id or not predicate:
                continue
            
            # 更新实体ID
            if subject_id in entity_id_map:
                subject_id = entity_id_map[subject_id]
            if object_id in entity_id_map:
                object_id = entity_id_map[object_id]
            
            # 检查实体是否存在
            if subject_id not in self.graph["entities"] or object_id not in self.graph["entities"]:
                continue
            
            # 避免重复关系
            relation_key = f"{subject_id}_{object_id}_{predicate}"
            if relation_key in added_relations:
                continue
            added_relations.add(relation_key)
            
            # 丰富关系信息
            relation_info = {
                "subject": subject_id,
                "object": object_id,
                "predicate": predicate,
                "confidence": confidence,
                "attributes": relation_attributes,
                "source_id": source_id,
                "source_type": source_type
            }
            
            self.graph["relations"].append(relation_info)

    def save_to_database(self) -> bool:
        """
        将知识图谱保存到数据库

        Returns:
            是否保存成功
        """
        try:
            import json
            with self.db.get_session() as session:
                # 批量保存实体
                entity_ids = set()
                for entity_id, entity in self.graph["entities"].items():
                    try:
                        # 检查实体是否已存在
                        existing_entity = session.query(Entity).filter(Entity.id == entity_id).first()
                        if not existing_entity:
                            db_entity = Entity(
                                id=entity_id,
                                name=entity.get("name", ""),
                                type=entity.get("type", "概念"),
                                description=entity.get("description", ""),
                                metadata=json.dumps(entity.get("attributes", {}), ensure_ascii=False) if entity.get("attributes") else "{}"
                            )
                            session.add(db_entity)
                            entity_ids.add(entity_id)
                        else:
                            # 更新现有实体信息
                            existing_entity.name = entity.get("name", existing_entity.name)
                            existing_entity.type = entity.get("type", existing_entity.type)
                            existing_entity.description = entity.get("description", existing_entity.description)
                            existing_entity.metadata = json.dumps(entity.get("attributes", {}), ensure_ascii=False) if entity.get("attributes") else existing_entity.metadata
                    except Exception as e:
                        logger.error(f"保存实体失败 {entity_id}: {e}")
                        continue
                
                # 批量保存关系
                relation_keys = set()
                for relation in self.graph["relations"]:
                    try:
                        subject_id = relation.get("subject")
                        object_id = relation.get("object")
                        predicate = relation.get("predicate", "")
                        confidence = relation.get("confidence", 0)
                        source = relation.get("source", "")
                        attributes = relation.get("attributes", {})
                        
                        if not subject_id or not object_id or not predicate:
                            continue
                        
                        # 检查关系是否已存在
                        relation_key = f"{subject_id}_{object_id}_{predicate}"
                        if relation_key in relation_keys:
                            continue
                        
                        existing_relation = session.query(EntityRelationship).filter(
                            EntityRelationship.subject_id == subject_id,
                            EntityRelationship.object_id == object_id,
                            EntityRelationship.predicate == predicate
                        ).first()
                        
                        if not existing_relation:
                            db_relation = EntityRelationship(
                                id=str(uuid.uuid4()),
                                subject_id=subject_id,
                                object_id=object_id,
                                predicate=predicate,
                                confidence=confidence,
                                source=source,
                                metadata=json.dumps(attributes, ensure_ascii=False) if attributes else "{}"
                            )
                            session.add(db_relation)
                            relation_keys.add(relation_key)
                        else:
                            # 更新现有关系信息
                            existing_relation.confidence = confidence
                            existing_relation.source = source
                            existing_relation.metadata = json.dumps(attributes, ensure_ascii=False) if attributes else existing_relation.metadata
                    except Exception as e:
                        logger.error(f"保存关系失败: {e}")
                        continue
                
                session.commit()
                logger.info(f"知识图谱保存到数据库成功：{len(entity_ids)} 个新实体，{len(relation_keys)} 个新关系")
                return True
        except Exception as e:
            logger.error(f"保存知识图谱到数据库失败: {e}")
            return False

    def get_entities(self) -> Dict[str, Any]:
        """
        获取知识图谱中的实体

        Returns:
            实体字典
        """
        return self.graph["entities"]

    def get_relations(self) -> List[Dict[str, Any]]:
        """
        获取知识图谱中的关系

        Returns:
            关系列表
        """
        return self.graph["relations"]

    def get_entity(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """
        获取指定实体

        Args:
            entity_id: 实体ID

        Returns:
            实体信息，如果不存在则返回None
        """
        return self.graph["entities"].get(entity_id)

    def get_relations_by_entity(self, entity_id: str) -> List[Dict[str, Any]]:
        """
        获取与指定实体相关的关系

        Args:
            entity_id: 实体ID

        Returns:
            关系列表
        """
        related_relations = []
        for relation in self.graph["relations"]:
            if relation.get("subject") == entity_id or relation.get("object") == entity_id:
                related_relations.append(relation)
        return related_relations

    def clear(self):
        """
        清空知识图谱
        """
        self.graph = {
            "entities": {},
            "relations": []
        }

    def to_json(self) -> str:
        """
        将知识图谱转换为JSON字符串

        Returns:
            JSON字符串
        """
        import json
        return json.dumps(self.graph, ensure_ascii=False, indent=2)

    def from_json(self, json_str: str):
        """
        从JSON字符串加载知识图谱

        Args:
            json_str: JSON字符串
        """
        import json
        try:
            self.graph = json.loads(json_str)
        except Exception as e:
            logger.error(f"从JSON加载知识图谱失败: {e}")

    def save_to_file(self, file_path: str):
        """
        将知识图谱保存到文件

        Args:
            file_path: 文件路径
        """
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(self.to_json())
            logger.info(f"知识图谱保存到文件: {file_path}")
        except Exception as e:
            logger.error(f"保存知识图谱到文件失败: {e}")

    def load_from_file(self, file_path: str):
        """
        从文件加载知识图谱

        Args:
            file_path: 文件路径
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                json_str = f.read()
            self.from_json(json_str)
            logger.info(f"从文件加载知识图谱: {file_path}")
        except Exception as e:
            logger.error(f"从文件加载知识图谱失败: {e}")

    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """
        计算两个字符串的相似度

        Args:
            str1: 第一个字符串
            str2: 第二个字符串

        Returns:
            相似度分数，范围0-1
        """
        # 移除标点符号和空格
        def clean_string(s):
            # 使用更安全的正则表达式，避免  转义问题
            s = re.sub(r'[\s\W]', '', s.lower())
            return s

        str1_clean = clean_string(str1)
        str2_clean = clean_string(str2)

        # 如果其中一个字符串为空，返回0
        if not str1_clean or not str2_clean:
            return 0.0

        # 使用SequenceMatcher计算相似度
        matcher = SequenceMatcher(None, str1_clean, str2_clean)
        return matcher.ratio()

    def _find_matching_entity(self, entity: Dict[str, Any]) -> Optional[str]:
        """
        查找与给定实体匹配的现有实体

        Args:
            entity: 实体信息

        Returns:
            匹配的实体ID，如果没有匹配则返回None
        """
        entity_name = entity.get("name", "").strip()
        entity_type = entity.get("type", "").strip()

        if not entity_name:
            return None

        # 首先在当前图谱中查找
        best_match = None
        best_similarity = 0.7

        for existing_entity_id, existing_entity in self.graph["entities"].items():
            existing_name = existing_entity.get("name", "").strip()
            existing_type = existing_entity.get("type", "").strip()

            # 检查类型是否匹配
            if existing_type and entity_type and existing_type != entity_type:
                continue

            # 计算名称相似度
            similarity = self._calculate_similarity(entity_name, existing_name)
            if similarity > best_similarity:
                best_similarity = similarity
                best_match = existing_entity_id

        if best_match:
            logger.info(f"找到匹配实体: {entity_name} -> {self.graph['entities'][best_match].get('name')} (相似度: {best_similarity:.2f})")
            return best_match

        # 从数据库中查找，优化查询，只查找同类型的实体
        try:
            with self.db.get_session() as session:
                # 构建查询
                query = session.query(Entity)
                if entity_type:
                    query = query.filter(Entity.type == entity_type)
                
                # 限制查询结果数量，提高性能
                existing_entities = query.limit(100).all()
                
                for existing_entity in existing_entities:
                    existing_name = existing_entity.name.strip()
                    existing_type = existing_entity.type.strip()

                    # 检查类型是否匹配
                    if existing_type and entity_type and existing_type != entity_type:
                        continue

                    # 计算名称相似度
                    similarity = self._calculate_similarity(entity_name, existing_name)
                    if similarity > best_similarity:
                        best_similarity = similarity
                        best_match = existing_entity.id

                if best_match:
                    logger.info(f"从数据库找到匹配实体: {entity_name} -> {existing_entity.name} (相似度: {best_similarity:.2f})")
                    # 将匹配的实体添加到当前图谱中
                    if best_match not in self.graph["entities"]:
                        entity_info = {
                            "id": best_match,
                            "name": existing_entity.name,
                            "type": existing_entity.type,
                            "description": existing_entity.description or "",
                            "attributes": {},
                            "source_id": "database",
                            "source_type": "database"
                        }
                        self.graph["entities"][best_match] = entity_info
                    return best_match
        except Exception as e:
            logger.error(f"从数据库查找匹配实体失败: {e}")

        return None

    def _merge_entities(self, entity_id1: str, entity_id2: str) -> str:
        """
        合并两个实体

        Args:
            entity_id1: 第一个实体ID
            entity_id2: 第二个实体ID

        Returns:
            保留的实体ID
        """
        entity1 = self.graph["entities"].get(entity_id1)
        entity2 = self.graph["entities"].get(entity_id2)

        if not entity1 or not entity2:
            return entity_id1 or entity_id2

        # 保留信息更丰富的实体
        def get_entity_score(entity):
            score = 0
            if entity.get("description"):
                score += 1
            if entity.get("attributes"):
                score += len(entity.get("attributes", {}))
            return score

        score1 = get_entity_score(entity1)
        score2 = get_entity_score(entity2)

        if score2 > score1:
            # 交换，保留分数高的实体
            entity_id1, entity_id2 = entity_id2, entity_id1
            entity1, entity2 = entity2, entity1

        # 合并属性
        attributes1 = entity1.get("attributes", {})
        attributes2 = entity2.get("attributes", {})
        merged_attributes = {**attributes1, **attributes2}  # 后者覆盖前者

        # 更新实体1的属性
        entity1["attributes"] = merged_attributes

        # 如果实体2有更详细的描述，使用实体2的描述
        if entity2.get("description") and not entity1.get("description"):
            entity1["description"] = entity2.get("description")

        # 更新关系中的实体ID
        for relation in self.graph["relations"]:
            if relation.get("subject") == entity_id2:
                relation["subject"] = entity_id1
            if relation.get("object") == entity_id2:
                relation["object"] = entity_id1

        # 从图谱中删除实体2
        if entity_id2 in self.graph["entities"]:
            del self.graph["entities"][entity_id2]

        logger.info(f"合并实体: {entity_id2} -> {entity_id1}")
        return entity_id1

    def add_uncertain_entity(self, entity: Dict[str, Any], similarity_score: float):
        """
        添加不确定实体

        Args:
            entity: 实体信息
            similarity_score: 相似度分数
        """
        uncertain_entity = {
            "entity": entity,
            "similarity_score": similarity_score,
            "created_at": time.time(),
            "source_id": entity.get("source_id"),
            "source_type": entity.get("source_type")
        }
        self.uncertain_entities.append(uncertain_entity)
        logger.info(f"添加不确定实体: {entity.get('name')} (相似度: {similarity_score:.2f})")

    def process_uncertain_entities(self):
        """
        处理不确定实体
        """
        if not self.uncertain_entities:
            logger.info("没有不确定实体需要处理")
            return

        logger.info(f"开始处理 {len(self.uncertain_entities)} 个不确定实体")

        # 按相似度分数排序
        self.uncertain_entities.sort(key=lambda x: x["similarity_score"], reverse=True)

        # 尝试合并相似的不确定实体
        processed = []
        for i, uncertain_entity in enumerate(self.uncertain_entities):
            if i in processed:
                continue

            entity = uncertain_entity["entity"]
            entity_name = entity.get("name", "").strip()
            entity_type = entity.get("type", "").strip()

            # 查找相似的不确定实体
            similar_entities = []
            for j, other_uncertain in enumerate(self.uncertain_entities):
                if i == j or j in processed:
                    continue

                other_entity = other_uncertain["entity"]
                other_name = other_entity.get("name", "").strip()
                other_type = other_entity.get("type", "").strip()

                # 检查类型是否匹配
                if other_type and entity_type and other_type != entity_type:
                    continue

                # 计算相似度
                similarity = self._calculate_similarity(entity_name, other_name)
                if similarity >= 0.7:
                    similar_entities.append((j, other_uncertain))

            # 合并相似实体
            if similar_entities:
                logger.info(f"合并 {len(similar_entities) + 1} 个相似的不确定实体")
                # 这里可以实现更复杂的合并逻辑
                # 暂时只标记为处理过
                processed.extend([i] + [j for j, _ in similar_entities])

        # 清理已处理的不确定实体
        self.uncertain_entities = [self.uncertain_entities[i] for i in range(len(self.uncertain_entities)) if i not in processed]
        logger.info(f"处理完成，剩余 {len(self.uncertain_entities)} 个不确定实体")

    def save_uncertain_entities(self, file_path: str):
        """
        保存不确定实体到文件

        Args:
            file_path: 文件路径
        """
        try:
            import json
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(self.uncertain_entities, f, ensure_ascii=False, indent=2)
            logger.info(f"不确定实体保存到文件: {file_path}")
        except Exception as e:
            logger.error(f"保存不确定实体失败: {e}")

    def load_uncertain_entities(self, file_path: str):
        """
        从文件加载不确定实体

        Args:
            file_path: 文件路径
        """
        try:
            import json
            with open(file_path, "r", encoding="utf-8") as f:
                self.uncertain_entities = json.load(f)
            logger.info(f"从文件加载不确定实体: {file_path}")
        except Exception as e:
            logger.error(f"加载不确定实体失败: {e}")


# 全局知识图谱构建器实例
knowledge_graph_builder = KnowledgeGraphBuilder()


def get_knowledge_graph_builder() -> KnowledgeGraphBuilder:
    """
    获取知识图谱构建器实例

    Returns:
        知识图谱构建器实例
    """
    return knowledge_graph_builder
