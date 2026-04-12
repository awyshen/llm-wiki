"""
Gradio Web界面

提供直观的Web交互界面
"""

import os
import json
from typing import Optional

import gradio as gr

from ..core.config import get_config
from ..core.logger import get_logger
from ..storage.wiki_storage import WikiStorage
from ..collect.file_collector import FileCollector
from ..process.knowledge_processor import KnowledgeProcessor
from ..storage.vector import get_vector_store
from .graph_visualization import KnowledgeGraphVisualization

logger = get_logger(__name__)


def create_gradio_ui() -> gr.Blocks:
    """创建Gradio界面"""
    config = get_config()
    wiki_storage = WikiStorage()
    file_collector = FileCollector()
    processor = KnowledgeProcessor()
    graph_visualizer = KnowledgeGraphVisualization()
    
    with gr.Blocks(
        title=config.system.name,
        theme=gr.themes.Soft(),
        css="""
            /* 全局样式优化 */
            .gradio-container { max-width: 1200px !important; }
            .tabitem { padding: 16px !important; }
            .markdown-text { font-size: 16px; line-height: 1.6; }
            .dataframe { font-size: 14px; }
            
            /* 响应式设计 */
            @media (max-width: 768px) {
                .gradio-container { padding: 10px !important; }
                .row { flex-direction: column !important; }
                .column { width: 100% !important; }
            }
            
            /* 性能优化 */
            .animate-fade-in { animation: fadeIn 0.3s ease-in-out; }
            @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
        """
    ) as demo:
        gr.Markdown(f"# {config.system.name}")
        gr.Markdown(f"{config.system.description}")
        
        with gr.Tabs():
            # 文档导入标签页
            with gr.TabItem("📄 文档导入"):
                gr.Markdown("### 导入文档到知识库")
                
                with gr.Row():
                    with gr.Column():
                        file_input = gr.File(
                            label="选择文件",
                            file_types=[".md", ".txt", ".pdf", ".docx", ".html"],
                            file_count="multiple"
                        )
                        import_btn = gr.Button("导入文档", variant="primary")
                    
                    with gr.Column():
                        import_output = gr.JSON(label="导入结果")
                
                def import_files(files):
                    if not files:
                        return {"error": "请选择文件"}
                    
                    results = []
                    for file in files:
                        result = file_collector.collect_file(file.name, copy_to_raw=True)
                        results.append({
                            "filename": os.path.basename(file.name),
                            "success": result.success,
                            "type": result.file_type,
                            "error": result.error_message
                        })
                    
                    return {
                        "total": len(results),
                        "success": sum(1 for r in results if r["success"]),
                        "details": results
                    }
                
                import_btn.click(import_files, inputs=[file_input], outputs=[import_output])
            
            # 文档处理标签页
            with gr.TabItem("⚙️ 文档处理"):
                gr.Markdown("### 处理待处理的文档")
                
                with gr.Row():
                    with gr.Column():
                        process_btn = gr.Button("开始处理", variant="primary")
                        stats_btn = gr.Button("刷新统计")
                    
                    with gr.Column():
                        process_output = gr.JSON(label="处理结果")
                
                def process_documents():
                    stats = processor.process_pending_documents()
                    return stats
                
                def get_stats():
                    return processor.get_processing_stats()
                
                process_btn.click(process_documents, outputs=[process_output])
                stats_btn.click(get_stats, outputs=[process_output])
            
            # Wiki浏览标签页
            with gr.TabItem("📚 Wiki浏览"):
                gr.Markdown("### 浏览知识库")
                
                with gr.Row():
                    with gr.Column(scale=1):
                        refresh_btn = gr.Button("刷新列表")
                        page_list = gr.Dataframe(
                            headers=["标题", "分类", "修改时间"],
                            label="页面列表"
                        )
                    
                    with gr.Column(scale=2):
                        page_content = gr.Markdown(label="页面内容")
                
                def refresh_pages():
                    pages = wiki_storage.list_pages()
                    data = [[
                        p.get("title", ""),
                        p.get("category", "未分类"),
                        p.get("modified", "")[:19]  # 去掉时区
                    ] for p in pages[:50]]
                    return data
                
                refresh_btn.click(refresh_pages, outputs=[page_list])
            
            # 搜索标签页
            with gr.TabItem("🔍 高级搜索"):
                gr.Markdown("### 高级搜索")
                
                from ..search.advanced_search import AdvancedSearch
                from ..search.search_history import SearchHistory
                from ..search.search_suggestions import SearchSuggestions
                
                advanced_search = AdvancedSearch()
                search_history = SearchHistory()
                search_suggestions = SearchSuggestions()
                
                with gr.Row():
                    with gr.Column(scale=1):
                        # 搜索控制
                        with gr.Accordion("搜索选项"):
                            search_input = gr.Textbox(
                                label="搜索关键词",
                                placeholder="输入搜索内容",
                                show_label=False
                            )
                            
                            # 搜索过滤器
                            category_filter = gr.Dropdown(
                                choices=["全部"],
                                value="全部",
                                label="分类"
                            )
                            
                            page_type_filter = gr.Dropdown(
                                choices=["全部"],
                                value="全部",
                                label="页面类型"
                            )
                            
                            sort_by = gr.Radio(
                                choices=["相关性", "时间", "热度"],
                                value="相关性",
                                label="排序方式"
                            )
                            
                            with gr.Row():
                                include_semantic = gr.Checkbox(
                                    label="语义搜索",
                                    value=True
                                )
                                include_fuzzy = gr.Checkbox(
                                    label="模糊搜索",
                                    value=True
                                )
                            
                            search_btn = gr.Button("搜索", variant="primary")
                            clear_btn = gr.Button("清空")
                        
                        # 搜索历史
                        with gr.Accordion("搜索历史"):
                            history_output = gr.Dataframe(
                                headers=["搜索词", "时间"],
                                datatype=["str", "str"],
                                col_count=(2, "fixed"),
                                label="最近搜索"
                            )
                            clear_history_btn = gr.Button("清空历史")
                    
                    with gr.Column(scale=2):
                        # 搜索结果
                        search_results = gr.Dataframe(
                            headers=["标题", "类型", "内容", "相关性"],
                            datatype=["str", "str", "str", "number"],
                            col_count=(4, "fixed"),
                            label="搜索结果"
                        )
                        
                        # 搜索信息
                        search_info = gr.Markdown("搜索信息：请输入搜索关键词")
                
                def perform_search(query, category, page_type, sort_by, include_semantic, include_fuzzy):
                    if not query:
                        return [], "请输入搜索关键词", get_search_history()
                    
                    # 构建过滤条件
                    filters = {}
                    if category != "全部":
                        filters['category'] = category
                    if page_type != "全部":
                        filters['page_type'] = page_type
                    
                    # 转换排序方式
                    sort_map = {
                        "相关性": "relevance",
                        "时间": "time",
                        "热度": "popularity"
                    }
                    sort_by_en = sort_map.get(sort_by, "relevance")
                    
                    # 执行搜索
                    results = advanced_search.search(
                        query=query,
                        filters=filters,
                        top_k=20,
                        include_semantic=include_semantic,
                        include_fuzzy=include_fuzzy,
                        sort_by=sort_by_en
                    )
                    
                    # 格式化结果
                    formatted_results = []
                    for result in results:
                        formatted_results.append([
                            result.title,
                            result.type,
                            result.content,
                            round(result.score, 3)
                        ])
                    
                    # 保存搜索历史
                    search_history.add(
                        query=query,
                        filters=filters,
                        results_count=len(results)
                    )
                    
                    # 搜索信息
                    info = f"## 搜索结果\n"\
                        f"- 搜索关键词: {query}\n"\
                        f"- 结果数量: {len(results)}\n"\
                        f"- 搜索模式: {'语义搜索' if include_semantic else ''}{' + 模糊搜索' if include_fuzzy else ''}"
                    
                    return formatted_results, info, get_search_history()
                
                def clear_search():
                    return "", [], "请输入搜索关键词"
                
                def get_search_history():
                    try:
                        history = search_history.get_recent(10)
                        return [[h['query'], h['timestamp'][:19]] for h in history]
                    except Exception as e:
                        logger.error(f"获取搜索历史失败: {e}")
                        return []
                
                def clear_history():
                    try:
                        search_history.clear()
                        return []
                    except Exception as e:
                        logger.error(f"清空搜索历史失败: {e}")
                        return []
                
                def get_filter_options():
                    from ..storage.database import get_db_manager
                    from ..storage.models import WikiPage
                    
                    try:
                        db = get_db_manager()
                        with db.get_session() as session:
                            # 获取分类选项
                            categories = session.query(WikiPage.category).distinct().all()
                            category_options = ["全部"] + [c[0] for c in categories if c[0]]
                            
                            # 获取页面类型选项
                            page_types = session.query(WikiPage.page_type).distinct().all()
                            page_type_options = ["全部"] + [pt[0] for pt in page_types if pt[0]]
                            
                            return category_options, page_type_options
                    except Exception as e:
                        logger.error(f"获取过滤器选项失败: {e}")
                        return ["全部"], ["全部"]
                
                search_btn.click(
                    perform_search,
                    inputs=[
                        search_input,
                        category_filter,
                        page_type_filter,
                        sort_by,
                        include_semantic,
                        include_fuzzy
                    ],
                    outputs=[search_results, search_info, history_output]
                )
                
                clear_btn.click(
                    clear_search,
                    outputs=[search_input, search_results, search_info]
                )
                
                clear_history_btn.click(
                    clear_history,
                    outputs=[history_output]
                )
                
                # 初始化过滤器选项
                category_options, page_type_options = get_filter_options()
                category_filter.choices = category_options
                page_type_filter.choices = page_type_options
                
                # 初始加载历史
                history_output.value = get_search_history()
            
            # 知识图谱标签页
            with gr.TabItem("🧠 知识图谱"):
                gr.Markdown("### 知识图谱可视化")
                
                with gr.Row():
                    with gr.Column(scale=1):
                        entity_input = gr.Textbox(
                            label="起始实体ID (可选)",
                            placeholder="留空显示全部"
                        )
                        max_nodes = gr.Slider(
                            label="最大节点数",
                            minimum=10,
                            maximum=100,
                            value=50,
                            step=10
                        )
                        refresh_graph_btn = gr.Button("刷新图谱", variant="primary")
                        
                        # 导出功能
                        export_format = gr.Dropdown(
                            label="导出格式",
                            choices=["json", "csv"],
                            value="json"
                        )
                        export_btn = gr.Button("导出图谱")
                        export_output = gr.Textbox(label="导出结果")
                    
                    with gr.Column(scale=3):
                        # 使用HTML组件显示D3.js图谱
                        graph_html = gr.HTML(label="知识图谱")
                
                def generate_graph_html(entity_id, nodes_count):
                    """生成图谱HTML"""
                    graph_data = graph_visualizer.get_graph_data(entity_id, nodes_count)
                    
                    # D3.js 图谱可视化HTML
                    html = f"""
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <meta charset="utf-8">
                        <title>知识图谱</title>
                        <script src="https://d3js.org/d3.v7.min.js"></script>
                        <style>
                            body {{ margin: 0; font-family: Arial, sans-serif; }}
                            .node {{ cursor: pointer; }}
                            .node text {{ font-size: 12px; }}
                            .link {{ stroke: #999; stroke-opacity: 0.6; }}
                            .link-label {{ font-size: 10px; fill: #666; }}
                            .tooltip {{ position: absolute; padding: 10px; background: #f9f9f9; border: 1px solid #ddd; border-radius: 5px; pointer-events: none; }}
                        </style>
                    </head>
                    <body>
                        <div id="graph-container" style="width: 100%; height: 600px;"></div>
                        <script>
                            const data = {json.dumps(graph_data)};
                            
                            const width = document.getElementById('graph-container').clientWidth;
                            const height = 600;
                            
                            const svg = d3.select('#graph-container')
                                .append('svg')
                                .attr('width', width)
                                .attr('height', height);
                            
                            const tooltip = d3.select('body')
                                .append('div')
                                .attr('class', 'tooltip')
                                .style('opacity', 0);
                            
                            // 力导向布局
                            const simulation = d3.forceSimulation(data.nodes)
                                .force('link', d3.forceLink(data.links).id(d => d.id).distance(100))
                                .force('charge', d3.forceManyBody().strength(-300))
                                .force('center', d3.forceCenter(width / 2, height / 2))
                                .force('collision', d3.forceCollide().radius(d => d.size + 10));
                            
                            // 定义颜色比例尺
                            const color = d3.scaleOrdinal()
                                .domain(['人物', '组织', '地点', '概念', '技术', '项目', '事件'])
                                .range(['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8', '#F7DC6F', '#BB8FCE']);
                            
                            // 绘制边
                            const link = svg.append('g')
                                .selectAll('line')
                                .data(data.links)
                                .enter()
                                .append('line')
                                .attr('class', 'link')
                                .attr('stroke-width', d => Math.sqrt(d.value));
                            
                            // 绘制边标签
                            const linkLabel = svg.append('g')
                                .selectAll('text')
                                .data(data.links)
                                .enter()
                                .append('text')
                                .attr('class', 'link-label')
                                .text(d => d.label);
                            
                            // 绘制节点
                            const node = svg.append('g')
                                .selectAll('g')
                                .data(data.nodes)
                                .enter()
                                .append('g')
                                .attr('class', 'node')
                                .call(d3.drag()
                                    .on('start', dragstarted)
                                    .on('drag', dragged)
                                    .on('end', dragended));
                            
                            // 节点圆形
                            node.append('circle')
                                .attr('r', d => d.size)
                                .attr('fill', d => color(d.type))
                                .on('mouseover', function(event, d) {
                                    tooltip.transition()
                                        .duration(200)
                                        .style('opacity', .9);
                                    tooltip.html(`<strong>${{d.label}}</strong><br>类型: ${{d.type}}`)
                                        .style('left', (event.pageX + 10) + 'px')
                                        .style('top', (event.pageY - 28) + 'px');
                                })
                                .on('mouseout', function() {
                                    tooltip.transition()
                                        .duration(500)
                                        .style('opacity', 0);
                                });
                            
                            // 节点标签
                            node.append('text')
                                .attr('dy', 4)
                                .attr('text-anchor', 'middle')
                                .text(d => d.label)
                                .attr('fill', '#333');
                            
                            // 模拟更新
                            simulation.on('tick', () => {
                                link
                                    .attr('x1', d => d.source.x)
                                    .attr('y1', d => d.source.y)
                                    .attr('x2', d => d.target.x)
                                    .attr('y2', d => d.target.y);
                                
                                linkLabel
                                    .attr('x', d => (d.source.x + d.target.x) / 2)
                                    .attr('y', d => (d.source.y + d.target.y) / 2);
                                
                                node
                                    .attr('transform', d => `translate(${d.x},${d.y})`);
                            });
                            
                            // 拖拽函数
                            function dragstarted(event, d) {
                                if (!event.active) simulation.alphaTarget(0.3).restart();
                                d.fx = d.x;
                                d.fy = d.y;
                            }
                            
                            function dragged(event, d) {
                                d.fx = event.x;
                                d.fy = event.y;
                            }
                            
                            function dragended(event, d) {
                                if (!event.active) simulation.alphaTarget(0);
                                d.fx = null;
                                d.fy = null;
                            }
                            
                            // 缩放功能
                            const zoom = d3.zoom()
                                .scaleExtent([0.1, 4])
                                .on('zoom', (event) => {
                                    svg.selectAll('g').attr('transform', event.transform);
                                });
                            
                            svg.call(zoom);
                        </script>
                    </body>
                    </html>
                    """
                    return html
                
                def export_graph(format):
                    result = graph_visualizer.export_graph(format)
                    if isinstance(result, str):
                        return result
                    elif isinstance(result, dict):
                        return json.dumps(result, ensure_ascii=False, indent=2)
                    return str(result)
                
                refresh_graph_btn.click(
                    generate_graph_html,
                    inputs=[entity_input, max_nodes],
                    outputs=[graph_html]
                )
                
                export_btn.click(
                    export_graph,
                    inputs=[export_format],
                    outputs=[export_output]
                )
                
                # 初始加载
                demo.load(
                    generate_graph_html,
                    inputs=[entity_input, max_nodes],
                    outputs=[graph_html]
                )
            
            # 系统状态标签页
            with gr.TabItem("📊 系统状态"):
                gr.Markdown("### 系统状态概览")
                
                status_btn = gr.Button("刷新状态")
                status_output = gr.JSON(label="系统状态")
                
                def get_system_status():
                    from ..storage.database import get_db_manager
                    from ..storage.models import Document, WikiPage, Entity, Tag
                    
                    db = get_db_manager()
                    
                    with db.get_session() as session:
                        doc_count = session.query(Document).count()
                        wiki_count = session.query(WikiPage).count()
                        entity_count = session.query(Entity).count()
                        tag_count = session.query(Tag).count()
                        
                        pending_count = session.query(Document).filter(
                            Document.processing_status == "pending"
                        ).count()
                    
                    return {
                        "系统信息": {
                            "名称": config.system.name,
                            "版本": config.system.version,
                        },
                        "数据统计": {
                            "文档总数": doc_count,
                            "待处理": pending_count,
                            "Wiki页面": wiki_count,
                            "实体": entity_count,
                            "标签": tag_count,
                        },
                        "路径": {
                            "数据目录": config.paths.data_dir,
                            "Wiki目录": config.paths.wiki_dir,
                            "备份目录": config.paths.backup_dir,
                        }
                    }
                
                status_btn.click(get_system_status, outputs=[status_output])
                
                # 初始化时加载状态
                demo.load(get_system_status, outputs=[status_output])
        
        gr.Markdown("---")
        gr.Markdown(f"**{