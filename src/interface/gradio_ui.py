"""
Gradio Web界面

提供直观的Web交互界面
"""

import os
import json
from typing import Optional, Dict, List, Any

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
    
    # 定义全局CSS样式
    css = """
        /* 全局样式优化 */
        .gradio-container {
            max-width: 1200px !important;
            background-color: #f0f2f5 !important;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
        }
        
        /* 主题色彩 */
        :root {
            --primary-color: #3b82f6;
            --secondary-color: #64748b;
            --success-color: #10b981;
            --warning-color: #f59e0b;
            --error-color: #ef4444;
            --background-color: #ffffff;
            --text-color: #1e293b;
            --border-color: #e2e8f0;
            --hover-color: #f8fafc;
        }
        
        /* 标签页样式 */
        .tabitem {
            padding: 24px !important;
            background-color: var(--background-color) !important;
            border-radius: 12px !important;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06) !important;
            margin: 16px !important;
            animation: fadeIn 0.5s ease-in-out;
        }
        
        /* 标题样式 */
        .markdown-text h1, .markdown-text h2, .markdown-text h3 {
            color: var(--text-color) !important;
            font-weight: 700 !important;
            margin-bottom: 16px !important;
        }
        
        .markdown-text h1 {
            font-size: 24px !important;
        }
        
        .markdown-text h2 {
            font-size: 20px !important;
        }
        
        .markdown-text h3 {
            font-size: 16px !important;
        }
        
        /* 文本样式 */
        .markdown-text {
            font-size: 14px !important;
            line-height: 1.6 !important;
            color: var(--text-color) !important;
        }
        
        /* 数据表格样式 */
        .dataframe {
            font-size: 14px !important;
            border-radius: 8px !important;
            overflow: hidden !important;
            box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1) !important;
            border: 1px solid var(--border-color) !important;
        }
        
        .dataframe th {
            background-color: #f8fafc !important;
            font-weight: 600 !important;
            color: var(--text-color) !important;
            padding: 12px !important;
            text-align: left !important;
        }
        
        .dataframe td {
            padding: 12px !important;
            border-top: 1px solid var(--border-color) !important;
        }
        
        .dataframe tr:hover {
            background-color: var(--hover-color) !important;
        }
        
        /* 按钮样式 */
        .button-primary {
            background-color: var(--primary-color) !important;
            border: none !important;
            border-radius: 6px !important;
            padding: 10px 20px !important;
            font-weight: 600 !important;
            font-size: 14px !important;
            transition: all 0.3s ease !important;
            box-shadow: 0 1px 3px 0 rgba(59, 130, 246, 0.4) !important;
        }
        
        .button-primary:hover {
            background-color: #2563eb !important;
            transform: translateY(-1px) !important;
            box-shadow: 0 4px 6px -1px rgba(59, 130, 246, 0.4) !important;
        }
        
        .button-secondary {
            background-color: var(--secondary-color) !important;
            border: none !important;
            border-radius: 6px !important;
            padding: 10px 20px !important;
            font-weight: 500 !important;
            font-size: 14px !important;
            transition: all 0.3s ease !important;
        }
        
        .button-secondary:hover {
            background-color: #475569 !important;
            transform: translateY(-1px) !important;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1) !important;
        }
        
        /* 输入框样式 */
        .input-text, .dropdown, .slider {
            border-radius: 6px !important;
            border: 1px solid var(--border-color) !important;
            padding: 10px 14px !important;
            font-size: 14px !important;
            transition: all 0.3s ease !important;
            background-color: white !important;
        }
        
        .input-text:focus, .dropdown:focus, .slider:focus {
            border-color: var(--primary-color) !important;
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1) !important;
            outline: none !important;
        }
        
        /* 卡片样式 */
        .card {
            background-color: white !important;
            border-radius: 12px !important;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06) !important;
            padding: 20px !important;
            margin-bottom: 16px !important;
        }
        
        /* 响应式设计 */
        @media (max-width: 768px) {
            .gradio-container {
                padding: 16px !important;
            }
            
            .row {
                flex-direction: column !important;
            }
            
            .column {
                width: 100% !important;
                margin-bottom: 16px !important;
            }
            
            .tabitem {
                padding: 20px !important;
                margin: 8px !important;
            }
            
            .card {
                padding: 16px !important;
            }
        }
        
        /* 动画效果 */
        @keyframes fadeIn {
            from {
                opacity: 0;
                transform: translateY(10px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        /* 加载动画 */
        .loading {
            position: relative;
        }
        
        .loading::after {
            content: '';
            position: absolute;
            top: 50%;
            left: 50%;
            width: 24px;
            height: 24px;
            margin: -12px 0 0 -12px;
            border: 2px solid #f3f3f3;
            border-top: 2px solid var(--primary-color);
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        /* 知识图谱容器 */
        #graph-container {
            width: 100% !important;
            height: 600px !important;
            border-radius: 12px !important;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06) !important;
            background: white !important;
            overflow: hidden !important;
        }
        
        /* 自定义滚动条 */
        ::-webkit-scrollbar {
            width: 8px;
            height: 8px;
        }
        
        ::-webkit-scrollbar-track {
            background: #f1f5f9;
            border-radius: 4px;
        }
        
        ::-webkit-scrollbar-thumb {
            background: #cbd5e1;
            border-radius: 4px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: #94a3b8;
        }
    """
    
    with gr.Blocks(
        title=config.system.name,
        css=css
    ) as demo:
        # 顶部标题栏
        with gr.Row(elem_id="header"):
            gr.Markdown(f"# {config.system.name}", elem_id="app-title")
            gr.Markdown(f"版本: {config.system.version}", elem_id="app-version")
        
        gr.Markdown("LLM Wiki知识库管理系统", elem_id="app-description")
        
        with gr.Tabs():
            # 文档导入标签页
            with gr.TabItem("📄 文档导入"):
                gr.Markdown("### 导入文档到知识库")
                
                with gr.Row():
                    with gr.Column():
                        file_input = gr.File(
                            label="选择文件",
                            file_count="multiple"
                        )
                        import_btn = gr.Button("导入文档", variant="primary")
                    
                    with gr.Column():
                        import_output = gr.JSON(label="导入结果")
                
                def import_files(files):
                    """导入文件到知识库"""
                    if not files:
                        return {"error": "请选择文件"}
                    
                    results = []
                    for file in files:
                        try:
                            # 检查文件大小（限制100MB）
                            if os.path.getsize(file.name) > 100 * 1024 * 1024:
                                results.append({
                                    "filename": os.path.basename(file.name),
                                    "success": False,
                                    "type": os.path.splitext(file.name)[1].lstrip('.').lower(),
                                    "error": "文件大小超过限制（100MB）"
                                })
                                continue
                            
                            # 检查文件类型
                            file_ext = os.path.splitext(file.name)[1].lstrip('.').lower()
                            if file_ext not in file_collector.get_supported_file_types():
                                results.append({
                                    "filename": os.path.basename(file.name),
                                    "success": False,
                                    "type": file_ext,
                                    "error": "不支持的文件类型"
                                })
                                continue
                            
                            # 导入文件
                            doc_id = file_collector.import_file(file.name)
                            results.append({
                                "filename": os.path.basename(file.name),
                                "success": True,
                                "type": file_ext,
                                "doc_id": doc_id,
                                "error": None
                            })
                        except Exception as e:
                            results.append({
                                "filename": os.path.basename(file.name),
                                "success": False,
                                "type": os.path.splitext(file.name)[1].lstrip('.').lower(),
                                "error": str(e)
                            })
                    
                    return {
                        "total": len(results),
                        "success": sum(1 for r in results if r["success"]),
                        "details": results
                    }
                
                import_btn.click(import_files, inputs=[file_input], outputs=[import_output])
            
            # 文档管理标签页
            with gr.TabItem("📄 文档管理"):
                gr.Markdown("### 文档管理")
                
                with gr.Row():
                    with gr.Column():
                        # 文档列表控制
                        with gr.Row():
                            refresh_docs_btn = gr.Button("刷新文档列表", variant="primary")
                            filter_status = gr.Dropdown(
                                label="按状态筛选",
                                choices=["全部", "pending", "processing", "completed", "failed"],
                                value="全部"
                            )
                        
                        # 文档列表
                        doc_list = gr.Dataframe(
                            headers=["ID", "标题", "文件名", "类型", "状态", "创建时间"],
                            label="文档列表",
                            interactive=False,
                            wrap=True,
                            max_rows=10
                        )
                    
                    with gr.Column():
                        # 文档内容显示
                        doc_title = gr.Markdown(label="文档标题")
                        doc_content = gr.Markdown(label="文档内容")
                        doc_metadata = gr.JSON(label="文档元数据")
                
                def refresh_documents(status="全部"):
                    """刷新文档列表"""
                    from ..storage.database import get_db_manager
                    from ..storage.models import Document
                    
                    db = get_db_manager()
                    with db.get_session() as session:
                        query = session.query(Document)
                        
                        # 按状态筛选
                        if status != "全部":
                            query = query.filter(Document.processing_status == status)
                        
                        documents = query.all()
                        data = [[
                            doc.id,
                            doc.title,
                            doc.filename,
                            doc.file_type,
                            doc.processing_status,
                            doc.created_at.strftime("%Y-%m-%d %H:%M:%S") if doc.created_at else ""
                        ] for doc in documents]
                        return data
                
                def show_selected_document():
                    """显示选中文档的内容"""
                    # 由于Dataframe组件的限制，这里返回提示信息
                    return "# 请选择文档", "请在左侧列表中选择一个文档", {}
                
                # 事件绑定
                refresh_docs_btn.click(
                    refresh_documents,
                    inputs=[filter_status],
                    outputs=[doc_list]
                )
                
                filter_status.change(
                    refresh_documents,
                    inputs=[filter_status],
                    outputs=[doc_list]
                )
                
                # 显示文档内容按钮
                show_doc_btn = gr.Button("显示选中文档", variant="secondary")
                show_doc_btn.click(
                    show_selected_document,
                    inputs=None,
                    outputs=[doc_title, doc_content, doc_metadata]
                )
            
            # 文档处理标签页
            with gr.TabItem("⚙️ 文档处理"):
                gr.Markdown("### 处理待处理的文档")
                
                with gr.Row():
                    with gr.Column():
                        process_btn = gr.Button("开始处理", variant="primary")
                        stats_btn = gr.Button("刷新统计", variant="secondary")
                    
                    with gr.Column():
                        process_output = gr.JSON(label="处理结果")
                
                def process_documents():
                    """处理待处理的文档"""
                    try:
                        stats = processor.process_pending_documents()
                        return stats
                    except Exception as e:
                        logger.error(f"处理文档失败: {e}")
                        return {"error": str(e)}
                
                def get_stats():
                    """获取处理统计信息"""
                    try:
                        return processor.get_processing_stats()
                    except Exception as e:
                        logger.error(f"获取统计信息失败: {e}")
                        return {"error": str(e)}
                
                process_btn.click(process_documents, inputs=None, outputs=[process_output])
                stats_btn.click(get_stats, inputs=None, outputs=[process_output])
            
            # Wiki浏览标签页
            with gr.TabItem("📚 Wiki浏览"):
                gr.Markdown("### 浏览知识库")
                
                with gr.Row():
                    with gr.Column():
                        # 搜索和筛选
                        with gr.Row():
                            search_input = gr.Textbox(
                                label="搜索页面", 
                                placeholder="输入页面标题或内容",
                                show_label=False
                            )
                            refresh_btn = gr.Button("刷新列表", variant="primary")
                        
                        category_filter = gr.Dropdown(
                            label="按分类筛选", 
                            choices=["全部"], 
                            value="全部"
                        )
                        
                        # 页面列表
                        page_list = gr.Dataframe(
                            headers=["标题", "分类", "修改时间"],
                            label="页面列表",
                            interactive=False,
                            wrap=True,
                            max_rows=10
                        )
                    
                    with gr.Column():
                        # 页面内容显示
                        page_title = gr.Markdown(label="页面标题")
                        page_content = gr.Markdown(label="页面内容")
                        page_metadata = gr.JSON(label="页面元数据")
                
                def refresh_pages(search_term="", category="全部"):
                    """刷新页面列表"""
                    from ..storage.database import get_db_manager
                    from ..storage.models import WikiPage
                    
                    try:
                        db = get_db_manager()
                        with db.get_session() as session:
                            # 构建查询
                            query = session.query(WikiPage)
                            
                            # 搜索过滤
                            if search_term:
                                query = query.filter(
                                    WikiPage.title.contains(search_term) | 
                                    WikiPage.content.contains(search_term)
                                )
                            
                            # 分类过滤
                            if category != "全部":
                                query = query.filter(WikiPage.category == category)
                            
                            # 执行查询
                            pages = query.limit(50).all()
                            
                            # 转换数据格式
                            data = [[
                                page.title,
                                page.category or "未分类",
                                page.updated_at.strftime("%Y-%m-%d %H:%M:%S") if page.updated_at else ""
                            ] for page in pages]
                            return data
                    except Exception as e:
                        logger.error(f"刷新页面列表失败: {e}")
                        return []
                
                def get_category_options():
                    """获取分类选项"""
                    from ..storage.database import get_db_manager
                    from ..storage.models import WikiPage
                    
                    try:
                        db = get_db_manager()
                        with db.get_session() as session:
                            categories = session.query(WikiPage.category).distinct().all()
                            category_options = ["全部"] + [c[0] for c in categories if c[0]]
                            return category_options
                    except Exception as e:
                        logger.error(f"获取分类选项失败: {e}")
                        return ["全部"]
                
                def show_selected_content():
                    """显示选中页面的内容"""
                    # 由于Dataframe组件的限制，这里返回提示信息
                    return "# 请选择页面", "请在左侧列表中选择一个页面", {}
                
                # 初始化分类选项
                category_filter.choices = get_category_options()
                
                # 事件绑定
                refresh_btn.click(
                    refresh_pages,
                    inputs=[search_input, category_filter],
                    outputs=[page_list]
                )
                
                # 当搜索框或分类变化时自动刷新
                search_input.change(
                    refresh_pages,
                    inputs=[search_input, category_filter],
                    outputs=[page_list]
                )
                
                category_filter.change(
                    refresh_pages,
                    inputs=[search_input, category_filter],
                    outputs=[page_list]
                )
                
                # 显示页面内容按钮
                show_content_btn = gr.Button("显示选中页面", variant="secondary")
                show_content_btn.click(
                    show_selected_content,
                    inputs=None,
                    outputs=[page_title, page_content, page_metadata]
                )
            
            # 搜索标签页
            with gr.TabItem("🔍 高级搜索"):
                gr.Markdown("### 高级搜索")
                
                from ..search.advanced_search import AdvancedSearch
                from ..search.search_history import SearchHistory
                
                advanced_search = AdvancedSearch()
                search_history = SearchHistory()
                
                with gr.Row():
                    with gr.Column():
                        # 搜索控制
                        gr.Markdown("### 搜索选项")
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
                        
                        include_semantic = gr.Checkbox(
                            label="语义搜索",
                            value=True
                        )
                        include_fuzzy = gr.Checkbox(
                            label="模糊搜索",
                            value=True
                        )
                        
                        with gr.Row():
                            search_btn = gr.Button("搜索", variant="primary")
                            clear_btn = gr.Button("清空", variant="secondary")
                        
                        # 搜索历史
                        gr.Markdown("### 搜索历史")
                        history_output = gr.Dataframe(
                            headers=["搜索词", "时间"],
                            datatype=["str", "str"],
                            col_count=(2, "fixed"),
                            label="最近搜索",
                            wrap=True,
                            max_rows=5
                        )
                        clear_history_btn = gr.Button("清空历史", variant="secondary")
                    
                    with gr.Column():
                        # 搜索结果
                        search_results = gr.Dataframe(
                            headers=["标题", "类型", "内容", "相关性"],
                            datatype=["str", "str", "str", "number"],
                            col_count=(4, "fixed"),
                            label="搜索结果",
                            wrap=True,
                            max_rows=10
                        )
                        
                        # 搜索信息
                        search_info = gr.Markdown("搜索信息：请输入搜索关键词")
                
                def perform_search(query, category, page_type, sort_by, include_semantic, include_fuzzy):
                    """执行搜索"""
                    if not query:
                        return [], "请输入搜索关键词", get_search_history()
                    
                    try:
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
                            # 处理字典类型和对象类型的搜索结果
                            if isinstance(result, dict):
                                title = result.get('title', '')
                                doc_type = result.get('type', '')
                                content = result.get('content', '')
                                score = result.get('score', 0)
                            else:
                                title = getattr(result, 'title', '')
                                doc_type = getattr(result, 'type', '')
                                content = getattr(result, 'content', '')
                                score = getattr(result, 'score', 0)
                            formatted_results.append([
                                title,
                                doc_type,
                                content,
                                round(score, 3)
                            ])
                        
                        # 保存搜索历史
                        search_history.add(
                            query=query,
                            filters=filters,
                            results_count=len(results)
                        )
                        
                        # 搜索信息
                        info = f"## 搜索结果\n- 搜索关键词: {query}\n- 结果数量: {len(results)}\n- 搜索模式: {'语义搜索' if include_semantic else ''}{' + 模糊搜索' if include_fuzzy else ''}"
                        
                        return formatted_results, info, get_search_history()
                    except Exception as e:
                        logger.error(f"搜索失败: {e}")
                        return [], f"搜索失败: {str(e)}", get_search_history()
                
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
                            
                            # 暂时返回空的页面类型选项
                            page_type_options = ["全部"]
                            
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
                    inputs=None,
                    outputs=[search_input, search_results, search_info]
                )
                
                clear_history_btn.click(
                    clear_history,
                    inputs=None,
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
                    with gr.Column():
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
                        
                        # 路径查询功能
                        gr.Markdown("### 路径查询")
                        start_entity = gr.Textbox(
                            label="起始实体ID",
                            placeholder="输入起始实体ID"
                        )
                        end_entity = gr.Textbox(
                            label="目标实体ID",
                            placeholder="输入目标实体ID"
                        )
                        max_depth = gr.Slider(
                            label="最大深度",
                            minimum=1,
                            maximum=5,
                            value=3,
                            step=1
                        )
                        find_path_btn = gr.Button("查找路径", variant="secondary")
                        
                        # 相关实体查询
                        gr.Markdown("### 相关实体")
                        related_entity = gr.Textbox(
                            label="实体ID",
                            placeholder="输入实体ID"
                        )
                        search_depth = gr.Slider(
                            label="搜索深度",
                            minimum=1,
                            maximum=3,
                            value=2,
                            step=1
                        )
                        get_related_btn = gr.Button("获取相关实体", variant="secondary")
                        
                        # 图谱统计信息
                        graph_stats = gr.JSON(label="图谱统计")
                        
                        # 导出功能
                        export_format = gr.Dropdown(
                            label="导出格式",
                            choices=["json", "csv"],
                            value="json"
                        )
                        export_btn = gr.Button("导出图谱", variant="secondary")
                        export_output = gr.Textbox(label="导出结果", lines=5)
                    
                    with gr.Column():
                        # 使用HTML组件显示D3.js图谱
                        graph_html = gr.HTML(label="知识图谱")
                
                def generate_graph_html(entity_id, nodes_count):
                    """生成图谱HTML"""
                    try:
                        # 获取图谱数据
                        graph_data = graph_visualizer.get_graph_data(entity_id, nodes_count)
                        
                        # 检查图谱是否为空
                        if not graph_data["nodes"] and not graph_data["links"]:
                            # 返回空状态提示
                            empty_html = '''
                            <div style="
                                width: 100%; 
                                height: 500px; 
                                display: flex; 
                                flex-direction: column;
                                align-items: center; 
                                justify-content: center;
                                background-color: #f8f9fa;
                                border-radius: 12px;
                                font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                                color: #64748b;
                            ">
                                <div style="font-size: 64px; margin-bottom: 24px;">🧠</div>
                                <div style="font-size: 20px; font-weight: 600; margin-bottom: 16px; color: #1e293b;">知识图谱为空</div>
                                <div style="font-size: 14px; text-align: center; max-width: 300px;">请先在"文档导入"标签页导入文档，然后在"文档处理"标签页处理文档以生成实体和关系</div>
                            </div>
                            '''
                            return empty_html, graph_data.get("stats", {})
                        
                        # D3.js 图谱可视化HTML
                        html = '''
                        <!DOCTYPE html>
                        <html>
                        <head>
                            <meta charset="utf-8">
                            <title>知识图谱</title>
                            <script src="https://d3js.org/d3.v7.min.js"></script>
                            <style>
                                body {
                                    margin: 0;
                                    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                                    background-color: #f0f2f5;
                                }
                                #graph-container {
                                    width: 100%;
                                    height: 600px;
                                    border-radius: 12px;
                                    overflow: hidden;
                                    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
                                    background: white;
                                }
                                .node {
                                    cursor: pointer;
                                    transition: all 0.3s ease;
                                }
                                .node:hover {
                                    filter: brightness(1.1);
                                }
                                .node text {
                                    font-size: 12px;
                                    font-weight: 500;
                                    fill: #1e293b;
                                    pointer-events: none;
                                }
                                .link {
                                    stroke: #94a3b8;
                                    stroke-opacity: 0.6;
                                    transition: all 0.3s ease;
                                }
                                .link:hover {
                                    stroke-width: 3px;
                                    stroke-opacity: 1;
                                    stroke: #3b82f6;
                                }
                                .link-label {
                                    font-size: 10px;
                                    fill: #64748b;
                                    font-weight: 500;
                                    pointer-events: none;
                                }
                                .tooltip {
                                    position: absolute;
                                    padding: 12px 16px;
                                    background: rgba(255, 255, 255, 0.95);
                                    border: 1px solid #e2e8f0;
                                    border-radius: 8px;
                                    pointer-events: none;
                                    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
                                    font-size: 13px;
                                    z-index: 1000;
                                    max-width: 400px;
                                    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                                }
                                .tooltip-title {
                                    font-weight: 600;
                                    margin-bottom: 8px;
                                    color: #1e293b;
                                    font-size: 14px;
                                }
                                .tooltip-type {
                                    color: #3b82f6;
                                    font-size: 12px;
                                    margin-bottom: 4px;
                                }
                                .tooltip-desc {
                                    color: #64748b;
                                    font-size: 12px;
                                    line-height: 1.4;
                                    margin-bottom: 8px;
                                }
                                .tooltip-attributes {
                                    margin-top: 8px;
                                    border-top: 1px solid #e2e8f0;
                                    padding-top: 8px;
                                }
                                .tooltip-attribute {
                                    font-size: 11px;
                                    color: #64748b;
                                    margin-bottom: 2px;
                                }
                                .tooltip-attribute-key {
                                    font-weight: 500;
                                    color: #1e293b;
                                }
                                .control-panel {
                                    position: absolute;
                                    top: 16px;
                                    right: 16px;
                                    background: white;
                                    padding: 12px;
                                    border-radius: 8px;
                                    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
                                    font-size: 12px;
                                    z-index: 100;
                                }
                                .control-panel button {
                                    margin: 4px;
                                    padding: 6px 12px;
                                    border: 1px solid #e2e8f0;
                                    border-radius: 4px;
                                    background: #f8fafc;
                                    cursor: pointer;
                                    font-size: 12px;
                                    transition: all 0.2s ease;
                                    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                                }
                                .control-panel button:hover {
                                    background: #e2e8f0;
                                    border-color: #3b82f6;
                                }
                                .info-panel {
                                    position: absolute;
                                    bottom: 16px;
                                    left: 16px;
                                    background: rgba(255, 255, 255, 0.95);
                                    padding: 12px 16px;
                                    border-radius: 8px;
                                    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
                                    font-size: 12px;
                                    color: #64748b;
                                    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                                }
                                .info-panel strong {
                                    color: #1e293b;
                                }
                            </style>
                        </head>
                        <body>
                            <div id="graph-container"></div>
                            <div class="control-panel">
                                <button onclick="resetZoom()">重置缩放</button>
                                <button onclick="centerGraph()">居中图谱</button>
                                <button onclick="toggleLabels()">切换标签</button>
                            </div>
                            <div class="info-panel">
                                节点: <strong id="node-count">0</strong> | 
                                边: <strong id="link-count">0</strong> |
                                类型: <strong id="type-count">0</strong>
                            </div>
                            <script>
                                const data = ''' + json.dumps(graph_data) + ''';
                                
                                // 更新统计信息
                                document.getElementById('node-count').textContent = data.nodes.length;
                                document.getElementById('link-count').textContent = data.links.length;
                                
                                // 统计实体类型
                                const typeCount = new Set(data.nodes.map(node => node.type)).size;
                                document.getElementById('type-count').textContent = typeCount;
                                
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
                                    .force('link', d3.forceLink(data.links).id(d => d.id).distance(150))
                                    .force('charge', d3.forceManyBody().strength(-400))
                                    .force('center', d3.forceCenter(width / 2, height / 2))
                                    .force('collision', d3.forceCollide().radius(d => (d.size || 15) + 20));
                                
                                // 绘制边
                                const link = svg.append('g')
                                    .selectAll('line')
                                    .data(data.links)
                                    .enter()
                                    .append('line')
                                    .attr('class', 'link')
                                    .attr('stroke-width', d => Math.sqrt(d.value) || 1)
                                    .attr('stroke', d => d.color || '#94a3b8');
                                
                                // 绘制边标签
                                const linkLabel = svg.append('g')
                                    .selectAll('text')
                                    .data(data.links)
                                    .enter()
                                    .append('text')
                                    .attr('class', 'link-label')
                                    .text(d => d.label || '');
                                
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
                                    .attr('r', d => d.size || 15)
                                    .attr('fill', d => d.color || '#3b82f6')
                                    .on('mouseover', function(event, d) {
                                        tooltip.transition()
                                            .duration(200)
                                            .style('opacity', 0.9);
                                        
                                        // 构建工具提示内容
                                        let tooltipContent = '<div class="tooltip-title">' + (d.label || d.id) + '</div>';
                                        tooltipContent += '<div class="tooltip-type">类型: ' + (d.type || '未知') + '</div>';
                                        
                                        if (d.description) {
                                            tooltipContent += '<div class="tooltip-desc">' + d.description.substring(0, 150) + (d.description.length > 150 ? '...' : '') + '</div>';
                                        }
                                        
                                        // 添加属性信息
                                        if (d.attributes && Object.keys(d.attributes).length > 0) {
                                            tooltipContent += '<div class="tooltip-attributes">';
                                            tooltipContent += '<div style="font-weight: 500; margin-bottom: 4px; font-size: 12px; color: #1e293b;">属性:</div>';
                                            for (const [key, value] of Object.entries(d.attributes)) {
                                                const displayValue = typeof value === 'object' ? JSON.stringify(value) : value;
                                                tooltipContent += '<div class="tooltip-attribute"><span class="tooltip-attribute-key">' + key + ':</span> ' + displayValue + '</div>';
                                            }
                                            tooltipContent += '</div>';
                                        }
                                        
                                        tooltip.html(tooltipContent)
                                            .style('left', (event.pageX + 10) + 'px')
                                            .style('top', (event.pageY - 28) + 'px');
                                    })
                                    .on('mouseout', function() {
                                        tooltip.transition()
                                            .duration(500)
                                            .style('opacity', 0);
                                    });
                                
                                // 节点标签
                                const nodeLabels = node.append('text')
                                    .attr('dy', 4)
                                    .attr('text-anchor', 'middle')
                                    .text(d => d.label || d.id)
                                    .attr('fill', '#333')
                                    .style('display', 'block');
                                
                                // 切换标签显示
                                let labelsVisible = true;
                                function toggleLabels() {
                                    labelsVisible = !labelsVisible;
                                    nodeLabels.style('display', labelsVisible ? 'block' : 'none');
                                }
                                // 将toggleLabels暴露到全局
                                window.toggleLabels = toggleLabels;
                                
                                // 重置缩放
                                function resetZoom() {
                                    svg.transition()
                                        .duration(750)
                                        .call(zoom.transform, d3.zoomIdentity);
                                }
                                window.resetZoom = resetZoom;
                                
                                // 居中图谱
                                function centerGraph() {
                                    simulation.force('center', d3.forceCenter(width / 2, height / 2));
                                    simulation.alpha(0.3).restart();
                                }
                                window.centerGraph = centerGraph;
                                
                                // 缩放功能
                                const zoom = d3.zoom()
                                    .scaleExtent([0.1, 4])
                                    .on('zoom', (event) => {
                                        svg.selectAll('g').attr('transform', event.transform);
                                    });
                                
                                svg.call(zoom);
                                
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
                                
                                // 更新位置
                                simulation.on('tick', () => {
                                    link
                                        .attr('x1', d => d.source.x)
                                        .attr('y1', d => d.source.y)
                                        .attr('x2', d => d.target.x)
                                        .attr('y2', d => d.target.y);
                                    
                                    linkLabel
                                        .attr('x', d => (d.source.x + d.target.x) / 2)
                                        .attr('y', d => (d.source.y + d.target.y) / 2)
                                        .attr('text-anchor', 'middle')
                                        .attr('dy', -5);
                                    
                                    node
                                        .attr('transform', d => `translate(${d.x},${d.y})`);
                                });
                            </script>
                        </body>
                        </html>
                        '''
                        return html, graph_data.get("stats", {})
                    except Exception as e:
                        logger.error(f"生成图谱HTML失败: {e}")
                        return f"<div style='padding: 20px; text-align: center; color: var(--error-color);'>生成图谱失败: {str(e)}</div>", {}
                
                def export_graph(format):
                    """导出图谱"""
                    try:
                        result = graph_visualizer.export_graph(format)
                        if format == "json":
                            return json.dumps(result, ensure_ascii=False, indent=2)
                        else:
                            return result
                    except Exception as e:
                        logger.error(f"导出图谱失败: {e}")
                        return f"导出失败: {str(e)}"
                
                def find_path(start_id, end_id, depth):
                    """查找路径"""
                    try:
                        if not start_id or not end_id:
                            return f"<div style='padding: 20px; text-align: center; color: var(--error-color);'>请输入起始和目标实体ID</div>", {}
                        
                        paths = graph_visualizer.find_path(start_id, end_id, depth)
                        
                        if not paths:
                            return f"<div style='padding: 20px; text-align: center; color: var(--secondary-color);'>未找到路径</div>", {}
                        
                        # 生成路径可视化HTML
                        html = '''
                        <!DOCTYPE html>
                        <html>
                        <head>
                            <meta charset="utf-8">
                            <title>路径查询结果</title>
                            <script src="https://d3js.org/d3.v7.min.js"></script>
                            <style>
                                body {
                                    margin: 0;
                                    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                                    background-color: #f0f2f5;
                                }
                                #graph-container {
                                    width: 100%;
                                    height: 500px;
                                    border-radius: 12px;
                                    overflow: hidden;
                                    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
                                    background: white;
                                }
                                .node {
                                    cursor: pointer;
                                    transition: all 0.3s ease;
                                }
                                .node:hover {
                                    filter: brightness(1.1);
                                }
                                .node text {
                                    font-size: 12px;
                                    font-weight: 500;
                                    fill: #1e293b;
                                    pointer-events: none;
                                }
                                .link {
                                    stroke: #94a3b8;
                                    stroke-opacity: 0.6;
                                    transition: all 0.3s ease;
                                }
                                .link:hover {
                                    stroke-width: 3px;
                                    stroke-opacity: 1;
                                    stroke: #3b82f6;
                                }
                                .path-link {
                                    stroke: #3b82f6;
                                    stroke-width: 3;
                                    stroke-opacity: 1;
                                }
                                .link-label {
                                    font-size: 10px;
                                    fill: #64748b;
                                    font-weight: 500;
                                    pointer-events: none;
                                }
                                .tooltip {
                                    position: absolute;
                                    padding: 12px 16px;
                                    background: rgba(255, 255, 255, 0.95);
                                    border: 1px solid #e2e8f0;
                                    border-radius: 8px;
                                    pointer-events: none;
                                    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
                                    font-size: 13px;
                                    z-index: 1000;
                                    max-width: 300px;
                                    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                                }
                                .tooltip-title {
                                    font-weight: 600;
                                    margin-bottom: 8px;
                                    color: #1e293b;
                                    font-size: 14px;
                                }
                                .tooltip-type {
                                    color: #3b82f6;
                                    font-size: 12px;
                                    margin-bottom: 4px;
                                }
                                .info-panel {
                                    position: absolute;
                                    bottom: 16px;
                                    left: 16px;
                                    background: rgba(255, 255, 255, 0.95);
                                    padding: 12px 16px;
                                    border-radius: 8px;
                                    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
                                    font-size: 12px;
                                    color: #64748b;
                                    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                                }
                                .info-panel strong {
                                    color: #1e293b;
                                }
                            </style>
                        </head>
                        <body>
                            <div id="graph-container"></div>
                            <div class="info-panel">
                                路径数量: <strong id="path-count">0</strong> | 
                                节点数: <strong id="node-count">0</strong> |
                                边数: <strong id="link-count">0</strong>
                            </div>
                            <script>
                                const paths = ''' + json.dumps(paths) + ''';
                                
                                // 合并所有路径的节点和边
                                const allNodes = new Set();
                                const allLinks = new Set();
                                
                                paths.forEach(path => {
                                    path.nodes.forEach(node => allNodes.add(JSON.stringify(node)));
                                    path.edges.forEach(edge => allLinks.add(JSON.stringify(edge)));
                                });
                                
                                const nodes = Array.from(allNodes).map(JSON.parse);
                                const links = Array.from(allLinks).map(JSON.parse);
                                
                                // 更新统计信息
                                document.getElementById('path-count').textContent = paths.length;
                                document.getElementById('node-count').textContent = nodes.length;
                                document.getElementById('link-count').textContent = links.length;
                                
                                const width = document.getElementById('graph-container').clientWidth;
                                const height = 500;
                                
                                const svg = d3.select('#graph-container')
                                    .append('svg')
                                    .attr('width', width)
                                    .attr('height', height);
                                
                                const tooltip = d3.select('body')
                                    .append('div')
                                    .attr('class', 'tooltip')
                                    .style('opacity', 0);
                                
                                // 力导向布局
                                const simulation = d3.forceSimulation(nodes)
                                    .force('link', d3.forceLink(links).id(d => d.id).distance(150))
                                    .force('charge', d3.forceManyBody().strength(-400))
                                    .force('center', d3.forceCenter(width / 2, height / 2))
                                    .force('collision', d3.forceCollide().radius(d => (d.size || 15) + 20));
                                
                                // 绘制边
                                const link = svg.append('g')
                                    .selectAll('line')
                                    .data(links)
                                    .enter()
                                    .append('line')
                                    .attr('class', d => d.color === '#3b82f6' ? 'link path-link' : 'link')
                                    .attr('stroke-width', d => Math.sqrt(d.value) || 1)
                                    .attr('stroke', d => d.color || '#94a3b8');
                                
                                // 绘制边标签
                                const linkLabel = svg.append('g')
                                    .selectAll('text')
                                    .data(links)
                                    .enter()
                                    .append('text')
                                    .attr('class', 'link-label')
                                    .text(d => d.label || '');
                                
                                // 绘制节点
                                const node = svg.append('g')
                                    .selectAll('g')
                                    .data(nodes)
                                    .enter()
                                    .append('g')
                                    .attr('class', 'node')
                                    .call(d3.drag()
                                        .on('start', dragstarted)
                                        .on('drag', dragged)
                                        .on('end', dragended));
                                
                                // 节点圆形
                                node.append('circle')
                                    .attr('r', d => d.size || 15)
                                    .attr('fill', d => d.color || '#3b82f6')
                                    .on('mouseover', function(event, d) {
                                        tooltip.transition()
                                            .duration(200)
                                            .style('opacity', 0.9);
                                        tooltip.html(
                                            '<div class="tooltip-title">' + (d.label || d.id) + '</div>' +
                                            '<div class="tooltip-type">类型: ' + (d.type || '未知') + '</div>'
                                        )
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
                                    .text(d => d.label || d.id)
                                    .attr('fill', '#333');
                                
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
                                
                                // 更新位置
                                simulation.on('tick', () => {
                                    link
                                        .attr('x1', d => d.source.x)
                                        .attr('y1', d => d.source.y)
                                        .attr('x2', d => d.target.x)
                                        .attr('y2', d => d.target.y);
                                    
                                    linkLabel
                                        .attr('x', d => (d.source.x + d.target.x) / 2)
                                        .attr('y', d => (d.source.y + d.target.y) / 2)
                                        .attr('text-anchor', 'middle')
                                        .attr('dy', -5);
                                    
                                    node
                                        .attr('transform', d => `translate(${d.x},${d.y})`);
                                });
                            </script>
                        </body>
                        </html>
                        '''
                        # 计算节点和边的数量
                        all_nodes = set()
                        all_links = set()
                        for path in paths:
                            for node in path.get("nodes", []):
                                all_nodes.add(node.get("id"))
                            for edge in path.get("edges", []):
                                all_links.add((edge.get("source"), edge.get("target"), edge.get("label")))
                        return html, {"paths": len(paths), "nodes": len(all_nodes), "links": len(all_links)}
                    except Exception as e:
                        logger.error(f"查找路径失败: {e}")
                        return f"<div style='padding: 20px; text-align: center; color: var(--error-color);'>查找路径失败: {str(e)}</div>", {}
                
                def get_related_entities(entity_id, depth):
                    """获取相关实体"""
                    try:
                        if not entity_id:
                            return f"<div style='padding: 20px; text-align: center; color: var(--error-color);'>请输入实体ID</div>", {}
                        
                        related_data = graph_visualizer.get_related_entities(entity_id, depth)
                        
                        if not related_data["nodes"]:
                            return f"<div style='padding: 20px; text-align: center; color: var(--secondary-color);'>未找到相关实体</div>", {}
                        
                        # 生成相关实体可视化HTML
                        html = '''
                        <!DOCTYPE html>
                        <html>
                        <head>
                            <meta charset="utf-8">
                            <title>相关实体</title>
                            <script src="https://d3js.org/d3.v7.min.js"></script>
                            <style>
                                body {
                                    margin: 0;
                                    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                                    background-color: #f0f2f5;
                                }
                                #graph-container {
                                    width: 100%;
                                    height: 500px;
                                    border-radius: 12px;
                                    overflow: hidden;
                                    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
                                    background: white;
                                }
                                .node {
                                    cursor: pointer;
                                    transition: all 0.3s ease;
                                }
                                .node:hover {
                                    filter: brightness(1.1);
                                }
                                .node text {
                                    font-size: 12px;
                                    font-weight: 500;
                                    fill: #1e293b;
                                    pointer-events: none;
                                }
                                .link {
                                    stroke: #94a3b8;
                                    stroke-opacity: 0.6;
                                    transition: all 0.3s ease;
                                }
                                .link:hover {
                                    stroke-width: 3px;
                                    stroke-opacity: 1;
                                    stroke: #3b82f6;
                                }
                                .center-node circle {
                                    stroke: #3b82f6;
                                    stroke-width: 3;
                                    filter: drop-shadow(0 0 5px #3b82f6);
                                }
                                .link-label {
                                    font-size: 10px;
                                    fill: #64748b;
                                    font-weight: 500;
                                    pointer-events: none;
                                }
                                .tooltip {
                                    position: absolute;
                                    padding: 12px 16px;
                                    background: rgba(255, 255, 255, 0.95);
                                    border: 1px solid #e2e8f0;
                                    border-radius: 8px;
                                    pointer-events: none;
                                    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
                                    font-size: 13px;
                                    z-index: 1000;
                                    max-width: 300px;
                                    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                                }
                                .tooltip-title {
                                    font-weight: 600;
                                    margin-bottom: 8px;
                                    color: #1e293b;
                                    font-size: 14px;
                                }
                                .tooltip-type {
                                    color: #3b82f6;
                                    font-size: 12px;
                                    margin-bottom: 4px;
                                }
                                .info-panel {
                                    position: absolute;
                                    bottom: 16px;
                                    left: 16px;
                                    background: rgba(255, 255, 255, 0.95);
                                    padding: 12px 16px;
                                    border-radius: 8px;
                                    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
                                    font-size: 12px;
                                    color: #64748b;
                                    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                                }
                                .info-panel strong {
                                    color: #1e293b;
                                }
                            </style>
                        </head>
                        <body>
                            <div id="graph-container"></div>
                            <div class="info-panel">
                                中心实体: <strong id="center-entity">0</strong> | 
                                相关实体数: <strong id="related-count">0</strong> |
                                关系数: <strong id="relation-count">0</strong>
                            </div>
                            <script>
                                const relatedData = ''' + json.dumps(related_data) + ''';
                                
                                const nodes = relatedData.nodes;
                                const links = relatedData.links;
                                
                                // 找到中心实体
                                const centerNode = nodes.find(node => node.size === 15) || nodes[0] || { label: '未知' };
                                
                                // 更新统计信息
                                document.getElementById('center-entity').textContent = centerNode.label || '未知';
                                document.getElementById('related-count').textContent = nodes.length - 1;
                                document.getElementById('relation-count').textContent = links.length;
                                
                                const width = document.getElementById('graph-container').clientWidth;
                                const height = 500;
                                
                                const svg = d3.select('#graph-container')
                                    .append('svg')
                                    .attr('width', width)
                                    .attr('height', height);
                                
                                const tooltip = d3.select('body')
                                    .append('div')
                                    .attr('class', 'tooltip')
                                    .style('opacity', 0);
                                
                                // 力导向布局
                                const simulation = d3.forceSimulation(nodes)
                                    .force('link', d3.forceLink(links).id(d => d.id).distance(120))
                                    .force('charge', d3.forceManyBody().strength(-300))
                                    .force('center', d3.forceCenter(width / 2, height / 2))
                                    .force('collision', d3.forceCollide().radius(d => (d.size || 15) + 15));
                                
                                // 绘制边
                                const link = svg.append('g')
                                    .selectAll('line')
                                    .data(links)
                                    .enter()
                                    .append('line')
                                    .attr('class', 'link')
                                    .attr('stroke-width', d => Math.sqrt(d.value) || 1)
                                    .attr('stroke', d => d.color || '#94a3b8');
                                
                                // 绘制边标签
                                const linkLabel = svg.append('g')
                                    .selectAll('text')
                                    .data(links)
                                    .enter()
                                    .append('text')
                                    .attr('class', 'link-label')
                                    .text(d => d.label || '');
                                
                                // 绘制节点
                                const node = svg.append('g')
                                    .selectAll('g')
                                    .data(nodes)
                                    .enter()
                                    .append('g')
                                    .attr('class', d => d.size === 15 ? 'node center-node' : 'node')
                                    .call(d3.drag()
                                        .on('start', dragstarted)
                                        .on('drag', dragged)
                                        .on('end', dragended));
                                
                                // 节点圆形
                                node.append('circle')
                                    .attr('r', d => d.size || 15)
                                    .attr('fill', d => d.color || '#3b82f6')
                                    .on('mouseover', function(event, d) {
                                        tooltip.transition()
                                            .duration(200)
                                            .style('opacity', 0.9);
                                        tooltip.html(
                                            '<div class="tooltip-title">' + (d.label || d.id) + '</div>' +
                                            '<div class="tooltip-type">类型: ' + (d.type || '未知') + '</div>' +
                                            (d.size === 15 ? '<div class="tooltip-type">中心实体</div>' : '')
                                        )
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
                                    .text(d => d.label || d.id)
                                    .attr('fill', '#333');
                                
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
                                
                                // 更新位置
                                simulation.on('tick', () => {
                                    link
                                        .attr('x1', d => d.source.x)
                                        .attr('y1', d => d.source.y)
                                        .attr('x2', d => d.target.x)
                                        .attr('y2', d => d.target.y);
                                    
                                    linkLabel
                                        .attr('x', d => (d.source.x + d.target.x) / 2)
                                        .attr('y', d => (d.source.y + d.target.y) / 2)
                                        .attr('text-anchor', 'middle')
                                        .attr('dy', -5);
                                    
                                    node
                                        .attr('transform', d => `translate(${d.x},${d.y})`);
                                });
                            </script>
                        </body>
                        </html>
                        '''
                        # 找到中心实体
                        center_node = None
                        for node in related_data.get("nodes", []):
                            if node.get("size") == 15:
                                center_node = node
                                break
                        if not center_node and related_data.get("nodes"):
                            center_node = related_data.get("nodes")[0]
                        center_label = center_node.get("label", "未知") if center_node else "未知"
                        return html, {"center_entity": center_label, "related_count": len(related_data.get("nodes", [])) - 1, "relation_count": len(related_data.get("links", []))}
                    except Exception as e:
                        logger.error(f"获取相关实体失败: {e}")
                        return f"<div style='padding: 20px; text-align: center; color: var(--error-color);'>获取相关实体失败: {str(e)}</div>", {}
                
                refresh_graph_btn.click(
                    generate_graph_html,
                    inputs=[entity_input, max_nodes],
                    outputs=[graph_html, graph_stats]
                )
                
                export_btn.click(
                    export_graph,
                    inputs=[export_format],
                    outputs=[export_output]
                )
                
                # 路径查询事件绑定
                find_path_btn.click(
                    find_path,
                    inputs=[start_entity, end_entity, max_depth],
                    outputs=[graph_html, graph_stats]
                )
                
                # 相关实体查询事件绑定
                get_related_btn.click(
                    get_related_entities,
                    inputs=[related_entity, search_depth],
                    outputs=[graph_html, graph_stats]
                )
                
                # 初始加载
                demo.load(
                    generate_graph_html,
                    inputs=[entity_input, max_nodes],
                    outputs=[graph_html, graph_stats]
                )
            
            # 系统状态标签页
            with gr.TabItem("📊 系统状态"):
                gr.Markdown("### 系统状态概览")
                
                with gr.Row():
                    with gr.Column():
                        refresh_status_btn = gr.Button("刷新状态", variant="primary")
                        status_output = gr.JSON(label="系统状态")
                
                def get_system_status():
                    """获取系统状态"""
                    try:
                        # 获取文档统计
                        doc_stats = processor.get_processing_stats()
                        
                        # 获取图谱统计
                        graph_stats = graph_visualizer.get_graph_statistics()
                        
                        # 获取存储统计
                        from ..storage.database import get_db_manager
                        db = get_db_manager()
                        with db.get_session() as session:
                            from ..storage.models import WikiPage
                            wiki_pages_count = session.query(WikiPage).count()
                        
                        status = {
                            "documents": doc_stats,
                            "knowledge_graph": graph_stats,
                            "wiki_pages": wiki_pages_count,
                            "system": {
                                "name": config.system.name,
                                "version": config.system.version,
                                "language": config.system.language
                            }
                        }
                        return status
                    except Exception as e:
                        logger.error(f"获取系统状态失败: {e}")
                        return {"error": str(e)}
                
                refresh_status_btn.click(get_system_status, inputs=None, outputs=[status_output])
                
                # 初始加载
                demo.load(get_system_status, inputs=None, outputs=[status_output])
    
    return demo

def run_webui():
    """运行WebUI"""
    demo = create_gradio_ui()
    demo.launch()
