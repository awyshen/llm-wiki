"""
API服务

提供RESTful API接口，支持文档管理、Wiki操作、搜索等功能。
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from typing import Dict, Any

from ..core.config import get_config
from ..core.logger import get_logger
from ..core.exceptions import ProcessingError
from ..storage.database import get_db_manager
from ..storage.models import Document, WikiPage, Tag, ProcessingStatus, Entity
from ..collect.file_collector import FileCollector
from ..process.knowledge_processor import KnowledgeProcessor
from ..process.knowledge_graph_builder import get_knowledge_graph_builder
from ..interface.graph_visualization import KnowledgeGraphVisualization
from ..search.advanced_search import AdvancedSearch

logger = get_logger(__name__)


def create_app() -> Flask:
    """
    创建Flask应用

    Returns:
        Flask应用实例
    """
    app = Flask(__name__)
    CORS(app)

    config = get_config()
    app.config.from_mapping(
        DEBUG=config.app.get("debug", False),
        SECRET_KEY=config.app.get("secret_key", "dev"),
    )

    # 注册路由
    register_routes(app)

    return app


def register_routes(app: Flask):
    """
    注册路由

    Args:
        app: Flask应用实例
    """

    @app.route("/api/documents", methods=["GET"])
    def get_documents():
        """
        获取文档列表
        """
        db = get_db_manager()
        with db.get_session() as session:
            documents = session.query(Document).all()

            result = []
            for doc in documents:
                result.append(
                    {
                        "id": doc.id,
                        "title": doc.title,
                        "filename": doc.filename,
                        "file_type": doc.file_type,
                        "processing_status": doc.processing_status,
                        "created_at": (
                            doc.created_at.isoformat() if doc.created_at else None
                        ),
                        "processed_at": (
                            doc.processed_at.isoformat() if doc.processed_at else None
                        ),
                    }
                )

            return jsonify(result)

    @app.route("/api/documents/upload", methods=["POST"])
    def upload_document():
        """
        上传文档
        """
        if "file" not in request.files:
            return jsonify({"error": "No file provided"}), 400

        file = request.files["file"]
        if file.filename == "":
            return jsonify({"error": "No file selected"}), 400

        try:
            collector = FileCollector()
            document_info = collector.import_file_storage(file)
            # 使用返回的字典，避免Session绑定问题
            return (
                jsonify(
                    {
                        "id": document_info["id"],
                        "title": document_info["title"],
                        "filename": document_info["filename"],
                    }
                ),
                201,
            )
        except Exception as e:
            logger.error(f"上传文档失败: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/wiki/pages", methods=["GET"])
    def get_wiki_pages():
        """
        获取Wiki页面列表
        """
        db = get_db_manager()
        with db.get_session() as session:
            pages = session.query(WikiPage).all()

            result = []
            for page in pages:
                result.append(
                    {
                        "id": page.id,
                        "title": page.title,
                        "slug": page.slug,
                        "category": page.category,
                        "created_at": page.created_at.isoformat(),
                        "updated_at": page.updated_at.isoformat(),
                    }
                )

            return jsonify(result)

    @app.route("/api/wiki/search", methods=["GET"])
    def search_wiki():
        """
        搜索Wiki
        """
        query = request.args.get("q", "")
        if not query:
            return jsonify({"error": "Query parameter is required"}), 400

        try:
            searcher = AdvancedSearch()
            results = searcher.search(query)
            return jsonify(results)
        except Exception as e:
            logger.error(f"搜索失败: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/entities", methods=["GET"])
    def get_entities():
        """
        获取实体列表
        
        Query Parameters:
            type: 实体类型（可选）
            name: 实体名称（可选）
            limit: 返回结果数量限制（可选，默认100）
            offset: 分页偏移量（可选，默认0）
        
        Returns:
            实体列表，每个实体包含id、名称、类型等信息
        """
        try:
            # 获取查询参数
            entity_type = request.args.get("type", "")
            entity_name = request.args.get("name", "")
            limit = int(request.args.get("limit", 100))
            offset = int(request.args.get("offset", 0))
            
            # 验证参数
            if limit < 1 or limit > 1000:
                return jsonify({"error": "Limit must be between 1 and 1000"}), 400
            if offset < 0:
                return jsonify({"error": "Offset must be non-negative"}), 400
            
            # 从数据库获取实体
            db = get_db_manager()
            with db.get_session() as session:
                query = session.query(Entity)
                
                # 应用过滤条件
                if entity_type:
                    query = query.filter(Entity.type == entity_type)
                if entity_name:
                    query = query.filter(Entity.name.ilike(f"%{entity_name}%"))
                
                # 应用分页
                entities = query.offset(offset).limit(limit).all()
                
                # 构建返回结果
                result = []
                for entity in entities:
                    result.append(
                        {
                            "id": entity.id,
                            "name": entity.name,
                            "type": entity.type,
                            "description": entity.description,
                            "created_at": entity.created_at.isoformat() if entity.created_at else None,
                            "updated_at": entity.updated_at.isoformat() if entity.updated_at else None,
                        }
                    )
                
                return jsonify(result)
        except ValueError as e:
            logger.error(f"参数错误: {e}")
            return jsonify({"error": "Invalid parameter format"}), 400
        except Exception as e:
            logger.error(f"获取实体列表失败: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/process/documents", methods=["POST"])
    def process_documents():
        """
        处理待处理文档
        """
        try:
            processor = KnowledgeProcessor()
            stats = processor.process_pending_documents()
            return jsonify(stats)
        except Exception as e:
            logger.error(f"处理文档失败: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/backup/create", methods=["POST"])
    def create_backup():
        """
        创建备份
        """
        import os
        import shutil
        import tarfile
        import datetime
        from src.core.config import get_config
        from src.core.logger import get_logger
        from src.storage.database import get_db_manager

        logger = get_logger(__name__)
        config = get_config()

        try:
            # 生成备份文件名
            timestamp = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"backup_{timestamp}.tar.gz"

            # 备份目录
            backup_dir = os.path.join(config.data_dir, "backup")
            os.makedirs(backup_dir, exist_ok=True)

            # 备份文件路径
            backup_path = os.path.join(backup_dir, backup_filename)

            # 要备份的目录
            data_dir = config.data_dir
            wiki_dir = os.path.join(data_dir, "wiki")
            raw_dir = os.path.join(data_dir, "raw")

            # 创建tar.gz文件
            with tarfile.open(backup_path, "w:gz") as tar:
                # 备份wiki目录
                if os.path.exists(wiki_dir):
                    tar.add(wiki_dir, arcname="wiki")
                    logger.info(f"备份Wiki目录: {wiki_dir}")

                # 备份raw目录
                if os.path.exists(raw_dir):
                    tar.add(raw_dir, arcname="raw")
                    logger.info(f"备份原始文件目录: {raw_dir}")

                # 备份数据库
                db_manager = get_db_manager()
                db_path = db_manager.engine.url.database
                if os.path.exists(db_path):
                    tar.add(db_path, arcname="database.sqlite")
                    logger.info(f"备份数据库: {db_path}")

                # 备份配置文件
                config_path = os.path.join(os.path.dirname(os.path.dirname(data_dir)), "config", "config.yaml")
                if os.path.exists(config_path):
                    tar.add(config_path, arcname="config.yaml")
                    logger.info(f"备份配置文件: {config_path}")

            # 计算备份文件大小
            backup_size = os.path.getsize(backup_path)

            # 记录备份信息
            backup_info = {
                "backup_id": timestamp,
                "filename": backup_filename,
                "path": backup_path,
                "size": backup_size,
                "created_at": datetime.datetime.utcnow().isoformat(),
                "contents": {
                    "wiki": os.path.exists(wiki_dir),
                    "raw": os.path.exists(raw_dir),
                    "database": os.path.exists(db_path),
                    "config": os.path.exists(config_path)
                }
            }

            # 保存备份信息到文件
            backup_info_path = os.path.join(backup_dir, f"backup_info_{timestamp}.json")
            import json
            with open(backup_info_path, "w", encoding="utf-8") as f:
                json.dump(backup_info, f, ensure_ascii=False, indent=2)

            logger.info(f"备份创建成功: {backup_filename}, 大小: {backup_size} bytes")

            return jsonify({
                "message": "Backup created successfully",
                "backup_id": timestamp,
                "filename": backup_filename,
                "size": backup_size,
                "path": backup_path
            })
        except Exception as e:
            logger.error(f"创建备份失败: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/health", methods=["GET"])
    def health_check():
        """
        健康检查
        """
        return jsonify({"status": "healthy"})

    @app.route("/api/graph/data", methods=["GET"])
    def get_graph_data():
        """
        获取知识图谱数据
        
        Query Parameters:
            limit: 节点数量限制（可选，默认100）
            type: 实体类型过滤（可选）
        
        Returns:
            包含节点和边的图谱数据
        """
        try:
            # 获取查询参数
            limit = int(request.args.get("limit", 100))
            entity_type = request.args.get("type", "")
            
            # 验证参数
            if limit < 1 or limit > 1000:
                return jsonify({"error": "Limit must be between 1 and 1000"}), 400
            
            # 获取图谱可视化实例
            graph_visualization = KnowledgeGraphVisualization()
            graph_data = graph_visualization.get_graph_data(max_nodes=limit)
            
            return jsonify(graph_data)
        except ValueError as e:
            logger.error(f"参数错误: {e}")
            return jsonify({"error": "Invalid parameter format"}), 400
        except Exception as e:
            logger.error(f"获取图谱数据失败: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/graph/entity/<entity_id>", methods=["GET"])
    def get_entity_details(entity_id):
        """
        获取实体详细信息
        
        Args:
            entity_id: 实体ID
        
        Returns:
            实体详细信息
        """
        try:
            graph_visualization = KnowledgeGraphVisualization()
            # 从数据库获取实体详细信息
            db = get_db_manager()
            with db.get_session() as session:
                entity = session.query(Entity).filter(Entity.id == entity_id).first()
                if not entity:
                    return jsonify({"error": "Entity not found"}), 404
                
                # 构建实体详细信息
                entity_info = {
                    "id": entity.id,
                    "name": entity.name,
                    "type": entity.type,
                    "description": entity.description,
                    "created_at": entity.created_at.isoformat() if entity.created_at else None,
                    "updated_at": entity.updated_at.isoformat() if entity.updated_at else None
                }
            
            return jsonify(entity_info)
        except Exception as e:
            logger.error(f"获取实体详细信息失败: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/graph/entity/<entity_id>/relations", methods=["GET"])
    def get_entity_relations(entity_id):
        """
        获取实体的相关关系
        
        Args:
            entity_id: 实体ID
        
        Returns:
            实体的相关关系列表
        """
        try:
            graph_visualization = KnowledgeGraphVisualization()
            relations = graph_visualization.get_entity_relations(entity_id)
            
            return jsonify(relations)
        except Exception as e:
            logger.error(f"获取实体关系失败: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/graph/path", methods=["GET"])
    def find_path():
        """
        查找两个实体之间的路径
        
        Query Parameters:
            start: 起始实体ID
            end: 目标实体ID
            max_depth: 最大深度（可选，默认5）
        
        Returns:
            路径信息
        """
        try:
            start_entity_id = request.args.get("start")
            end_entity_id = request.args.get("end")
            max_depth = int(request.args.get("max_depth", 5))
            
            if not start_entity_id or not end_entity_id:
                return jsonify({"error": "Start and end entity IDs are required"}), 400
            
            if max_depth < 1 or max_depth > 10:
                return jsonify({"error": "Max depth must be between 1 and 10"}), 400
            
            graph_visualization = KnowledgeGraphVisualization()
            path = graph_visualization.find_path(start_entity_id, end_entity_id, max_depth)
            
            return jsonify(path)
        except ValueError as e:
            logger.error(f"参数错误: {e}")
            return jsonify({"error": "Invalid parameter format"}), 400
        except Exception as e:
            logger.error(f"查找路径失败: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/graph/related", methods=["GET"])
    def get_related_entities():
        """
        获取相关实体
        
        Query Parameters:
            entity_id: 实体ID
            depth: 搜索深度（可选，默认2）
            limit: 结果数量限制（可选，默认20）
        
        Returns:
            相关实体列表
        """
        try:
            entity_id = request.args.get("entity_id")
            depth = int(request.args.get("depth", 2))
            limit = int(request.args.get("limit", 20))
            
            if not entity_id:
                return jsonify({"error": "Entity ID is required"}), 400
            
            if depth < 1 or depth > 5:
                return jsonify({"error": "Depth must be between 1 and 5"}), 400
            
            if limit < 1 or limit > 100:
                return jsonify({"error": "Limit must be between 1 and 100"}), 400
            
            graph_visualization = KnowledgeGraphVisualization()
            related_entities = graph_visualization.get_related_entities(entity_id, depth)
            
            return jsonify(related_entities)
        except ValueError as e:
            logger.error(f"参数错误: {e}")
            return jsonify({"error": "Invalid parameter format"}), 400
        except Exception as e:
            logger.error(f"获取相关实体失败: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/graph/build", methods=["POST"])
    def build_graph():
        """
        构建知识图谱
        
        Request Body:
            {
                "text": "文本内容",
                "source_id": "来源ID",
                "source_type": "来源类型（wiki_page 或 document）"
            }
        
        Returns:
            构建结果
        """
        try:
            data = request.json
            text = data.get("text")
            source_id = data.get("source_id")
            source_type = data.get("source_type")
            
            if not text or not source_id or not source_type:
                return jsonify({"error": "Text, source_id, and source_type are required"}), 400
            
            if source_type not in ["wiki_page", "document"]:
                return jsonify({"error": "Source type must be either 'wiki_page' or 'document'"}), 400
            
            graph_builder = get_knowledge_graph_builder()
            graph_builder.clear()
            graph = graph_builder.build_from_text(text, source_id, source_type)
            
            # 保存到数据库
            save_result = graph_builder.save_to_database()
            
            return jsonify({
                "success": save_result,
                "entities": len(graph.get("entities", {})),
                "relations": len(graph.get("relations", []))
            })
        except Exception as e:
            logger.error(f"构建知识图谱失败: {e}")
            return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app = create_app()
    config = get_config()
    app.run(host=config.app.get("host", "0.0.0.0"), port=config.app.get("port", 8000))
