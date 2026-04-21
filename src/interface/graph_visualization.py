"""
知识图谱可视化

提供知识图谱的构建和可视化功能。
"""

from typing import Dict, List, Any, Optional
from ..core.config import get_config
from ..core.logger import get_logger
from ..core.error_handler import ErrorHandler
from ..storage.database import get_db_manager
from ..storage.models import Entity, EntityRelationship

logger = get_logger(__name__)


class KnowledgeGraphVisualization:
    """知识图谱可视化"""

    def __init__(self):
        """初始化知识图谱可视化"""
        self.config = get_config()
        self.db = get_db_manager()
    
    def _get_current_timestamp(self) -> str:
        """
        获取当前时间戳

        Returns:
            当前时间戳字符串
        """
        from datetime import datetime
        return datetime.utcnow().isoformat()
    
    def _get_entity_color(self, entity_type: str) -> str:
        """
        根据实体类型获取颜色

        Args:
            entity_type: 实体类型

        Returns:
            颜色字符串
        """
        # 预定义实体类型颜色映射
        color_map = {
            "人物": "#FF6B6B",  # 红色
            "组织": "#4ECDC4",  # 青色
            "地点": "#45B7D1",  # 蓝色
            "概念": "#FFA07A",  # 橙色
            "技术": "#98D8C8",  # 淡青色
            "项目": "#F7DC6F",  # 黄色
            "事件": "#BB8FCE",  # 紫色
            "时间": "#A9DFBF",  # 绿色
            "数值": "#F8C471",  # 琥珀色
            "其他": "#BDC3C7"   # 灰色
        }
        
        return color_map.get(entity_type, "#BDC3C7")  # 默认灰色

    @ErrorHandler.handle_processing_exceptions()
    def get_graph_data(self, entity_id: str = None, max_nodes: int = 50) -> Dict[str, Any]:
        """
        获取图谱数据

        Args:
            entity_id: 起始实体ID (可选)
            max_nodes: 最大节点数

        Returns:
            图谱数据，包含节点和边
        """
        nodes = []
        links = []
        node_set = set()

        try:
            with self.db.get_session() as session:
                if entity_id:
                    # 从指定实体开始构建图谱
                    entity = session.query(Entity).filter(Entity.id == entity_id).first()
                    if entity:
                        self._add_entity_to_graph(entity, nodes, links, node_set, max_nodes, session)
                else:
                    # 构建完整图谱（限制节点数）
                    entities = session.query(Entity).limit(max_nodes).all()
                    for entity in entities:
                        if len(node_set) >= max_nodes:
                            break
                        self._add_entity_to_graph(entity, nodes, links, node_set, max_nodes, session)

        except Exception as e:
            logger.error(f"获取图谱数据失败: {e}")

        # 确保数据结构完整，即使为空也有默认结构
        if not nodes and not links:
            logger.info("知识图谱为空，请先处理文档以生成实体和关系")
        
        # 计算图谱统计信息
        stats = self.get_graph_statistics()
        
        return {
            "nodes": nodes,
            "links": links,
            "stats": stats,
            "timestamp": self._get_current_timestamp()
        }

    def _add_entity_to_graph(self, entity: Entity, nodes: List[Dict], links: List[Dict], 
                           node_set: set, max_nodes: int, session):
        """
        将实体添加到图谱中

        Args:
            entity: 实体
            nodes: 节点列表
            links: 边列表
            node_set: 节点ID集合
            max_nodes: 最大节点数
            session: 数据库会话
        """
        if entity.id in node_set:
            return

        # 解析实体属性
        attributes = {}
        if entity.metadata:
            try:
                import json
                # 检查metadata是否为字符串类型
                if isinstance(entity.metadata, str):
                    attributes = json.loads(entity.metadata)
                else:
                    # 如果不是字符串，尝试转换为字符串
                    attributes = {}
            except Exception as e:
                logger.error(f"解析实体元数据失败: {e}")

        # 添加节点
        node = {
            "id": entity.id,
            "label": entity.name,
            "type": entity.type,
            "size": 15,
            "color": self._get_entity_color(entity.type),
            "description": entity.description or "",
            "attributes": attributes  # 包含实体属性
        }
        nodes.append(node)
        node_set.add(entity.id)

        # 添加关系
        relationships = session.query(EntityRelationship).filter(
            (EntityRelationship.subject_id == entity.id) | 
            (EntityRelationship.object_id == entity.id)
        ).limit(10).all()  # 限制每个实体的关系数量

        for rel in relationships:
            if len(node_set) >= max_nodes:
                break

            # 解析关系属性
            relation_attributes = {}
            if rel.metadata:
                try:
                    import json
                    # 检查metadata是否为字符串类型
                    if isinstance(rel.metadata, str):
                        relation_attributes = json.loads(rel.metadata)
                    else:
                        # 如果不是字符串，尝试转换为字符串
                        relation_attributes = {}
                except Exception as e:
                    logger.error(f"解析关系元数据失败: {e}")

            # 添加目标实体
            if rel.subject_id == entity.id:
                target_entity = session.query(Entity).filter(Entity.id == rel.object_id).first()
                if target_entity and target_entity.id not in node_set:
                    # 解析目标实体属性
                    target_attributes = {}
                    if target_entity.metadata:
                        try:
                            import json
                            # 检查metadata是否为字符串类型
                            if isinstance(target_entity.metadata, str):
                                target_attributes = json.loads(target_entity.metadata)
                            else:
                                # 如果不是字符串，尝试转换为字符串
                                target_attributes = {}
                        except Exception as e:
                            logger.error(f"解析目标实体元数据失败: {e}")

                    target_node = {
                        "id": target_entity.id,
                        "label": target_entity.name,
                        "type": target_entity.type,
                        "size": 12,
                        "color": self._get_entity_color(target_entity.type),
                        "description": target_entity.description or "",
                        "attributes": target_attributes
                    }
                    nodes.append(target_node)
                    node_set.add(target_entity.id)

                # 添加边
                link = {
                    "source": rel.subject_id,
                    "target": rel.object_id,
                    "label": rel.predicate,
                    "value": 1,
                    "color": "#999",
                    "confidence": rel.confidence or 0,
                    "attributes": relation_attributes  # 包含关系属性
                }
                links.append(link)
            else:
                target_entity = session.query(Entity).filter(Entity.id == rel.subject_id).first()
                if target_entity and target_entity.id not in node_set:
                    # 解析目标实体属性
                    target_attributes = {}
                    if target_entity.metadata:
                        try:
                            import json
                            # 检查metadata是否为字符串类型
                            if isinstance(target_entity.metadata, str):
                                target_attributes = json.loads(target_entity.metadata)
                            else:
                                # 如果不是字符串，尝试转换为字符串
                                target_attributes = {}
                        except Exception as e:
                            logger.error(f"解析目标实体元数据失败: {e}")

                    target_node = {
                        "id": target_entity.id,
                        "label": target_entity.name,
                        "type": target_entity.type,
                        "size": 12,
                        "color": self._get_entity_color(target_entity.type),
                        "description": target_entity.description or "",
                        "attributes": target_attributes
                    }
                    nodes.append(target_node)
                    node_set.add(target_entity.id)

                # 添加边
                link = {
                    "source": rel.object_id,
                    "target": rel.subject_id,
                    "label": rel.predicate,
                    "value": 1,
                    "color": "#999",
                    "confidence": rel.confidence or 0,
                    "attributes": relation_attributes  # 包含关系属性
                }
                links.append(link)

    @ErrorHandler.handle_processing_exceptions()
    def export_graph(self, format: str = "json") -> Any:
        """
        导出图谱

        Args:
            format: 导出格式 (json, csv)

        Returns:
            导出的图谱数据
        """
        graph_data = self.get_graph_data()

        if format == "json":
            return graph_data
        elif format == "csv":
            # 转换为CSV格式
            import csv
            import io
            output = io.StringIO()
            writer = csv.writer(output)
            
            # 写入节点
            writer.writerow(["type", "id", "label", "type", "size"])
            for node in graph_data["nodes"]:
                writer.writerow(["node", node["id"], node["label"], node["type"], node["size"]])
            
            # 写入边
            for link in graph_data["links"]:
                writer.writerow(["link", link["source"], link["target"], link["label"], link["value"]])
            
            return output.getvalue()
        else:
            return graph_data

    @ErrorHandler.handle_processing_exceptions()
    def import_graph(self, graph_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        导入图谱

        Args:
            graph_data: 图谱数据，包含nodes和links

        Returns:
            导入结果
        """
        from ..storage.database import get_db_manager
        from ..storage.models import Entity, EntityRelationship
        
        db = get_db_manager()
        imported_nodes = 0
        imported_links = 0
        
        try:
            with db.get_session() as session:
                # 导入节点
                for node in graph_data.get("nodes", []):
                    # 检查节点是否已存在
                    existing_entity = session.query(Entity).filter(Entity.id == node["id"]).first()
                    if not existing_entity:
                        entity = Entity(
                            id=node["id"],
                            name=node["label"],
                            type=node.get("type", "其他"),
                            description=node.get("description", ""),
                            metadata={}
                        )
                        session.add(entity)
                        imported_nodes += 1
                
                # 导入边
                for link in graph_data.get("links", []):
                    # 检查关系是否已存在
                    existing_relation = session.query(EntityRelationship).filter(
                        EntityRelationship.subject_id == link["source"],
                        EntityRelationship.object_id == link["target"],
                        EntityRelationship.predicate == link["label"]
                    ).first()
                    if not existing_relation:
                        # 生成唯一ID
                        import uuid
                        relation_id = str(uuid.uuid4())
                        
                        relation = EntityRelationship(
                            id=relation_id,
                            subject_id=link["source"],
                            object_id=link["target"],
                            predicate=link["label"],
                            confidence=link.get("confidence", 1.0),
                            metadata={}
                        )
                        session.add(relation)
                        imported_links += 1
                
                session.commit()
                
                return {
                    "success": True,
                    "imported_nodes": imported_nodes,
                    "imported_links": imported_links
                }
        except Exception as e:
            logger.error(f"导入图谱失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def get_entity_relations(self, entity_id: str) -> List[Dict[str, Any]]:
        """
        获取实体的关系

        Args:
            entity_id: 实体ID

        Returns:
            实体关系列表
        """
        relations = []

        try:
            with self.db.get_session() as session:
                entity = session.query(Entity).filter(Entity.id == entity_id).first()
                if entity:
                    # 获取作为主语的关系
                    subject_relations = session.query(EntityRelationship).filter(
                        EntityRelationship.subject_id == entity_id
                    ).all()
                    
                    for rel in subject_relations:
                        object_entity = session.query(Entity).filter(Entity.id == rel.object_id).first()
                        if object_entity:
                            relations.append({
                                "type": "outgoing",
                                "predicate": rel.predicate,
                                "object": {
                                    "id": object_entity.id,
                                    "name": object_entity.name,
                                    "type": object_entity.type
                                },
                                "confidence": rel.confidence
                            })
                    
                    # 获取作为宾语的关系
                    object_relations = session.query(EntityRelationship).filter(
                        EntityRelationship.object_id == entity_id
                    ).all()
                    
                    for rel in object_relations:
                        subject_entity = session.query(Entity).filter(Entity.id == rel.subject_id).first()
                        if subject_entity:
                            relations.append({
                                "type": "incoming",
                                "predicate": rel.predicate,
                                "subject": {
                                    "id": subject_entity.id,
                                    "name": subject_entity.name,
                                    "type": subject_entity.type
                                },
                                "confidence": rel.confidence
                            })
        except Exception as e:
            logger.error(f"获取实体关系失败: {e}")

        return relations

    def get_graph_statistics(self) -> Dict[str, Any]:
        """
        获取图谱统计信息

        Returns:
            图谱统计信息
        """
        stats = {
            "nodes": 0,
            "links": 0,
            "entity_types": {}
        }

        try:
            with self.db.get_session() as session:
                # 统计节点数
                stats["nodes"] = session.query(Entity).count()
                
                # 统计边数
                stats["links"] = session.query(EntityRelationship).count()
                
                # 统计实体类型
                entities = session.query(Entity).all()
                for entity in entities:
                    entity_type = entity.type
                    if entity_type not in stats["entity_types"]:
                        stats["entity_types"][entity_type] = 0
                    stats["entity_types"][entity_type] += 1
        except Exception as e:
            logger.error(f"获取图谱统计信息失败: {e}")

        return stats

    def find_path(self, start_entity_id: str, end_entity_id: str, max_depth: int = 5) -> List[Dict[str, Any]]:
        """
        查找两个实体之间的路径

        Args:
            start_entity_id: 起始实体ID
            end_entity_id: 目标实体ID
            max_depth: 最大搜索深度

        Returns:
            路径列表，每个路径包含节点和边
        """
        paths = []

        try:
            with self.db.get_session() as session:
                # 验证起始和目标实体是否存在
                start_entity = session.query(Entity).filter(Entity.id == start_entity_id).first()
                end_entity = session.query(Entity).filter(Entity.id == end_entity_id).first()
                
                if not start_entity or not end_entity:
                    logger.error("起始或目标实体不存在")
                    return paths

                # 广度优先搜索查找路径
                visited = set()
                queue = [(start_entity_id, [start_entity_id], [])]

                while queue:
                    current_id, path_nodes, path_edges = queue.pop(0)

                    if current_id == end_entity_id:
                        # 找到路径，构建完整路径信息
                        path = {
                            "nodes": [],
                            "edges": []
                        }
                        
                        # 添加路径节点
                        for node_id in path_nodes:
                            entity = session.query(Entity).filter(Entity.id == node_id).first()
                            if entity:
                                path["nodes"].append({
                                    "id": entity.id,
                                    "label": entity.name,
                                    "type": entity.type,
                                    "color": self._get_entity_color(entity.type)
                                })
                        
                        # 添加路径边
                        for edge in path_edges:
                            path["edges"].append(edge)
                        
                        paths.append(path)
                        continue

                    if len(path_nodes) >= max_depth:
                        continue

                    visited.add(current_id)

                    # 获取当前节点的所有关系
                    relationships = session.query(EntityRelationship).filter(
                        (EntityRelationship.subject_id == current_id) | 
                        (EntityRelationship.object_id == current_id)
                    ).all()

                    for rel in relationships:
                        # 确定目标节点
                        if rel.subject_id == current_id:
                            next_id = rel.object_id
                            edge = {
                                "source": rel.subject_id,
                                "target": rel.object_id,
                                "label": rel.predicate,
                                "color": "#3b82f6",  # 路径边使用蓝色
                                "value": 2
                            }
                        else:
                            next_id = rel.subject_id
                            edge = {
                                "source": rel.object_id,
                                "target": rel.subject_id,
                                "label": rel.predicate,
                                "color": "#3b82f6",  # 路径边使用蓝色
                                "value": 2
                            }

                        if next_id not in visited:
                            new_path_nodes = path_nodes.copy()
                            new_path_nodes.append(next_id)
                            new_path_edges = path_edges.copy()
                            new_path_edges.append(edge)
                            queue.append((next_id, new_path_nodes, new_path_edges))

        except Exception as e:
            logger.error(f"查找路径失败: {e}")

        return paths

    def get_related_entities(self, entity_id: str, depth: int = 2) -> Dict[str, Any]:
        """
        获取与指定实体相关的实体（按深度）

        Args:
            entity_id: 实体ID
            depth: 搜索深度

        Returns:
            相关实体和关系
        """
        related_data = {
            "nodes": [],
            "links": []
        }

        try:
            with self.db.get_session() as session:
                # 验证实体是否存在
                start_entity = session.query(Entity).filter(Entity.id == entity_id).first()
                if not start_entity:
                    logger.error("实体不存在")
                    return related_data

                # 广度优先搜索
                visited = set()
                queue = [(entity_id, 0)]

                while queue:
                    current_id, current_depth = queue.pop(0)

                    if current_depth > depth:
                        continue

                    if current_id not in visited:
                        visited.add(current_id)

                        # 添加当前节点
                        entity = session.query(Entity).filter(Entity.id == current_id).first()
                        if entity:
                            related_data["nodes"].append({
                                "id": entity.id,
                                "label": entity.name,
                                "type": entity.type,
                                "color": self._get_entity_color(entity.type),
                                "size": 15 if current_id == entity_id else 12
                            })

                        # 获取当前节点的所有关系
                        relationships = session.query(EntityRelationship).filter(
                            (EntityRelationship.subject_id == current_id) | 
                            (EntityRelationship.object_id == current_id)
                        ).all()

                        for rel in relationships:
                            # 确定目标节点
                            if rel.subject_id == current_id:
                                next_id = rel.object_id
                            else:
                                next_id = rel.subject_id

                            # 添加边
                            edge = {
                                "source": rel.subject_id,
                                "target": rel.object_id,
                                "label": rel.predicate,
                                "color": "#999",
                                "value": 1
                            }
                            related_data["links"].append(edge)

                            # 添加目标节点到队列
                            if next_id not in visited:
                                queue.append((next_id, current_depth + 1))

        except Exception as e:
            logger.error(f"获取相关实体失败: {e}")

        return related_data
