#!/usr/bin/env python3
"""
知识图谱可视化功能测试脚本
"""

import json
from src.interface.graph_visualization import KnowledgeGraphVisualization


def test_graph_visualization():
    """测试知识图谱可视化功能"""
    print("=== 测试知识图谱可视化功能 ===")
    
    # 初始化可视化对象
    visualizer = KnowledgeGraphVisualization()
    
    # 测试1: 获取图谱数据
    print("\n1. 测试获取图谱数据:")
    graph_data = visualizer.get_graph_data(max_nodes=50)
    print(f"   节点数量: {len(graph_data['nodes'])}")
    print(f"   边数量: {len(graph_data['links'])}")
    print(f"   图谱统计: {json.dumps(graph_data['stats'], ensure_ascii=False, indent=2)}")
    
    # 测试2: 导出图谱为JSON
    print("\n2. 测试导出图谱为JSON:")
    json_data = visualizer.export_graph(format="json")
    print(f"   导出成功，节点数: {len(json_data['nodes'])}")
    
    # 测试3: 导出图谱为CSV
    print("\n3. 测试导出图谱为CSV:")
    csv_data = visualizer.export_graph(format="csv")
    print(f"   导出成功，CSV长度: {len(csv_data)}")
    print(f"   前1000个字符: {csv_data[:1000]}...")
    
    # 测试4: 测试图谱统计信息
    print("\n4. 测试图谱统计信息:")
    stats = visualizer.get_graph_statistics()
    print(f"   节点总数: {stats['nodes']}")
    print(f"   边总数: {stats['links']}")
    print(f"   实体类型分布: {json.dumps(stats['entity_types'], ensure_ascii=False, indent=2)}")
    
    # 测试5: 测试实体关系获取
    print("\n5. 测试实体关系获取:")
    if graph_data['nodes']:
        entity_id = graph_data['nodes'][0]['id']
        relations = visualizer.get_entity_relations(entity_id)
        print(f"   实体 {entity_id} 的关系数量: {len(relations)}")
        if relations:
            print(f"   前3个关系: {json.dumps(relations[:3], ensure_ascii=False, indent=2)}")
    else:
        print("   没有实体数据，跳过实体关系测试")
    
    # 测试6: 测试导入功能
    print("\n6. 测试导入图谱功能:")
    if graph_data['nodes']:
        import_result = visualizer.import_graph(graph_data)
        print(f"   导入结果: {json.dumps(import_result, ensure_ascii=False, indent=2)}")
    else:
        print("   没有实体数据，跳过导入测试")
    
    print("\n=== 测试完成 ===")


if __name__ == "__main__":
    test_graph_visualization()