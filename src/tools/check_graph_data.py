#!/usr/bin/env python3
"""
检查知识图谱数据
"""

from src.storage.database import get_db_manager
from src.storage.models import Entity, EntityRelationship


def check_graph_data():
    """
    检查知识图谱数据
    """
    print("=== 知识图谱数据检查 ===")
    
    try:
        db = get_db_manager()
        with db.get_session() as session:
            # 检查实体数量
            entity_count = session.query(Entity).count()
            print(f"实体数量: {entity_count}")
            
            # 检查关系数量
            relationship_count = session.query(EntityRelationship).count()
            print(f"关系数量: {relationship_count}")
            
            # 显示前10个实体
            if entity_count > 0:
                print("\n实体列表 (前10个):")
                entities = session.query(Entity).limit(10).all()
                for entity in entities:
                    print(f"  - {entity.id}: {entity.name} ({entity.type})")
            else:
                print("\n没有实体数据")
            
            # 显示前10个关系
            if relationship_count > 0:
                print("\n关系列表 (前10个):")
                relationships = session.query(EntityRelationship).limit(10).all()
                for rel in relationships:
                    print(f"  - {rel.subject_id} -> {rel.predicate} -> {rel.object_id}")
            else:
                print("\n没有关系数据")
                
    except Exception as e:
        print(f"检查数据失败: {e}")


if __name__ == "__main__":
    check_graph_data()
