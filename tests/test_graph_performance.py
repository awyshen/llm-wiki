#!/usr/bin/env python3
"""
知识图谱可视化前端性能测试脚本
"""

import time
import requests
import json


def test_frontend_performance():
    """测试前端可视化界面性能"""
    print("=== 测试前端可视化界面性能 ===")
    
    # 测试1: 测试图谱数据获取性能
    print("\n1. 测试图谱数据获取性能:")
    start_time = time.time()
    
    # 模拟前端获取图谱数据的请求
    from src.interface.graph_visualization import KnowledgeGraphVisualization
    visualizer = KnowledgeGraphVisualization()
    
    # 测试不同节点数量下的响应时间
    for max_nodes in [10, 50, 100]:
        node_start = time.time()
        graph_data = visualizer.get_graph_data(max_nodes=max_nodes)
        node_end = time.time()
        print(f"   节点数 {max_nodes}: {node_end - node_start:.3f} 秒")
        print(f"     实际返回节点数: {len(graph_data['nodes'])}")
        print(f"     实际返回边数: {len(graph_data['links'])}")
    
    total_time = time.time() - start_time
    print(f"   总测试时间: {total_time:.3f} 秒")
    
    # 测试2: 测试图谱布局算法合理性
    print("\n2. 测试图谱布局算法合理性:")
    graph_data = visualizer.get_graph_data(max_nodes=50)
    nodes = graph_data['nodes']
    links = graph_data['links']
    
    # 计算节点分布
    if nodes:
        print(f"   节点数: {len(nodes)}")
        print(f"   边数: {len(links)}")
        print(f"   平均每个节点的连接数: {len(links) / len(nodes):.2f}")
        
        # 检查节点属性完整性
        print("\n3. 测试节点属性完整性:")
        required_attrs = ['id', 'label', 'type', 'size', 'color']
        for node in nodes[:5]:  # 检查前5个节点
            missing_attrs = [attr for attr in required_attrs if attr not in node]
            if missing_attrs:
                print(f"   节点 {node['id']} 缺少属性: {missing_attrs}")
            else:
                print(f"   节点 {node['id']} 属性完整")
        
        # 检查边属性完整性
        print("\n4. 测试边属性完整性:")
        edge_required_attrs = ['source', 'target', 'label', 'value']
        for edge in links[:5]:  # 检查前5个边
            missing_attrs = [attr for attr in edge_required_attrs if attr not in edge]
            if missing_attrs:
                print(f"   边 {edge.get('source')}->{edge.get('target')} 缺少属性: {missing_attrs}")
            else:
                print(f"   边 {edge['source']}->{edge['target']} 属性完整")
    
    # 测试5: 测试颜色编码准确性
    print("\n5. 测试节点分类颜色编码准确性:")
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
    
    # 测试实际颜色是否符合预期
    test_nodes = nodes[:10]  # 测试前10个节点
    for node in test_nodes:
        expected_color = color_map.get(node['type'], "#BDC3C7")
        actual_color = node['color']
        if expected_color == actual_color:
            print(f"   节点 {node['label']} (类型: {node['type']}) 颜色正确: {actual_color}")
        else:
            print(f"   节点 {node['label']} (类型: {node['type']}) 颜色错误: 预期 {expected_color}, 实际 {actual_color}")
    
    # 测试6: 测试关系类型标识清晰度
    print("\n6. 测试关系类型标识清晰度:")
    if links:
        # 统计关系类型
        relation_types = {}
        for link in links:
            predicate = link['label']
            relation_types[predicate] = relation_types.get(predicate, 0) + 1
        
        print("   关系类型分布:")
        for pred, count in relation_types.items():
            print(f"     {pred}: {count} 次")
    
    print("\n=== 前端性能测试完成 ===")


if __name__ == "__main__":
    test_frontend_performance()