# 向量存储服务部署与运维指南

## 1. 系统架构

### 1.1 架构概述
- **向量存储服务**：基于 Chroma DB 的向量存储实现
- **嵌入服务**：基于 SentenceTransformer 的文本嵌入生成
- **管理工具**：向量存储管理工具，提供备份、恢复、优化等功能
- **API 接口**：提供搜索、添加、删除等操作的 API 接口

### 1.2 组件关系
```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   API 服务      │────>│  向量存储服务   │────>│  嵌入服务       │
└─────────────────┘     └─────────────────┘     └─────────────────┘
          ↑                         ↑
          │                         │
          ↓                         ↓
┌─────────────────┐     ┌─────────────────┐
│  管理工具       │     │  持久化存储     │
└─────────────────┘     └─────────────────┘
```

## 2. 部署准备

### 2.1 硬件要求
- **CPU**：至少 4 核
- **内存**：至少 8GB
- **存储**：至少 50GB 可用空间
- **网络**：稳定的网络连接

### 2.2 软件要求
- **Python**：3.9+ 
- **依赖库**：
  - chromadb
  - sentence-transformers
  - numpy
  - pydantic
  - fastapi (可选，用于 API 服务)

### 2.3 环境配置
1. **创建虚拟环境**：
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```

2. **安装依赖**：
   ```bash
   pip install -r requirements.txt
   ```

3. **配置文件**：
   编辑 `config/config.yaml` 文件，配置向量存储相关参数：
   ```yaml
   vector_db:
     path: "./data/vector_db"
     collection_name: "documents"
     chunk_size: 1000
     chunk_overlap: 100
   vector_store:
     embedding_model: "all-MiniLM-L6-v2"
   ```

## 3. 部署方式

### 3.1 单实例部署
1. **启动服务**：
   ```bash
   python main.py api
   ```

2. **验证服务**：
   ```bash
   curl http://localhost:8000/api/health
   ```

### 3.2 容器化部署
1. **创建 Dockerfile**：
   ```dockerfile
   FROM python:3.9-slim

   WORKDIR /app

   COPY . .

   RUN pip install --no-cache-dir -r requirements.txt

   EXPOSE 8000

   CMD ["python", "main.py", "api"]
   ```

2. **构建镜像**：
   ```bash
   docker build -t llm-wiki-vector-store .
   ```

3. **运行容器**：
   ```bash
   docker run -d -p 8000:8000 -v ./data:/app/data llm-wiki-vector-store
   ```

### 3.3 高可用部署
1. **使用 Docker Compose**：
   创建 `docker-compose.yml` 文件：
   ```yaml
   version: '3.8'

   services:
     vector-store-1:
       image: llm-wiki-vector-store
       ports:
         - "8001:8000"
       volumes:
         - ./data:/app/data
       restart: always

     vector-store-2:
       image: llm-wiki-vector-store
       ports:
         - "8002:8000"
       volumes:
         - ./data:/app/data
       restart: always

     nginx:
       image: nginx:latest
       ports:
         - "8000:80"
       volumes:
         - ./nginx.conf:/etc/nginx/nginx.conf
       depends_on:
         - vector-store-1
         - vector-store-2
       restart: always
   ```

2. **配置 Nginx 负载均衡**：
   创建 `nginx.conf` 文件：
   ```nginx
   events {
     worker_connections 1024;
   }

   http {
     upstream vector_store {
       server vector-store-1:8000;
       server vector-store-2:8000;
     }

     server {
       listen 80;

       location / {
         proxy_pass http://vector_store;
         proxy_set_header Host $host;
         proxy_set_header X-Real-IP $remote_addr;
         proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
         proxy_set_header X-Forwarded-Proto $scheme;
       }
     }
   }
   ```

3. **启动服务**：
   ```bash
   docker-compose up -d
   ```

## 4. 运维管理

### 4.1 备份与恢复
1. **手动备份**：
   ```python
   from src.storage.vector.manager import get_vector_store_manager

   manager = get_vector_store_manager()
   backup_path = manager.backup()
   print(f"备份成功: {backup_path}")
   ```

2. **自动备份**：
   创建定时备份脚本 `backup.py`：
   ```python
   from src.storage.vector.manager import get_vector_store_manager

   manager = get_vector_store_manager()
   manager.backup()
   manager.clean_old_backups(keep_days=7)
   ```

   添加到 crontab：
   ```bash
   0 2 * * * cd /path/to/llm-wiki && python backup.py
   ```

3. **恢复数据**：
   ```python
   from src.storage.vector.manager import get_vector_store_manager

   manager = get_vector_store_manager()
   success = manager.restore("/path/to/backup.tar.gz")
   print(f"恢复成功: {success}")
   ```

### 4.2 性能监控
1. **监控指标**：
   - 查询响应时间
   - 内存使用情况
   - 磁盘使用情况
   - 缓存命中率

2. **监控工具**：
   - Prometheus + Grafana
   - 自定义监控脚本

3. **监控脚本**：
   ```python
   from src.storage.vector.manager import get_vector_store_manager

   manager = get_vector_store_manager()
   stats = manager.get_stats()
   print(stats)
   ```

### 4.3 性能优化
1. **索引优化**：
   - 定期执行优化
   ```python
   from src.storage.vector.manager import get_vector_store_manager

   manager = get_vector_store_manager()
   manager.optimize()
   ```

2. **缓存优化**：
   - 调整缓存大小
   - 定期清理缓存

3. **批量操作**：
   - 使用批量搜索和批量添加操作

### 4.4 故障处理
1. **常见故障**：
   - 嵌入模型加载失败
   - 向量存储连接失败
   - 内存不足

2. **故障排查**：
   - 检查日志文件
   - 检查系统资源使用情况
   - 验证配置文件

3. **故障恢复**：
   - 重启服务
   - 恢复备份
   - 调整资源配置

## 5. API 接口

### 5.1 搜索接口
- **URL**：`/api/search`
- **方法**：GET
- **参数**：
  - `q`：搜索查询
  - `top_k`：返回结果数量
  - `hybrid_weight`：混合搜索权重
- **返回**：搜索结果列表

### 5.2 管理接口
- **备份**：`/api/vector/backup`
- **恢复**：`/api/vector/restore`
- **优化**：`/api/vector/optimize`
- **统计**：`/api/vector/stats`

## 6. 最佳实践

### 6.1 性能优化
- **使用批量操作**：对于大量数据的添加和查询，使用批量操作
- **合理设置缓存**：根据系统资源和使用情况，合理设置缓存大小
- **定期优化**：定期执行向量存储优化，保持查询性能

### 6.2 高可用
- **多实例部署**：部署多个向量存储实例，实现负载均衡
- **数据同步**：确保多实例间的数据一致性
- **健康检查**：定期检查服务健康状态，及时发现和处理故障

### 6.3 安全
- **访问控制**：限制 API 访问权限
- **数据加密**：对敏感数据进行加密
- **备份安全**：确保备份数据的安全存储

## 7. 常见问题

### 7.1 嵌入模型加载失败
- **问题**：无法加载 SentenceTransformer 模型
- **解决**：检查网络连接，或使用本地模型

### 7.2 查询响应时间过长
- **问题**：查询响应时间超过 200ms
- **解决**：优化缓存，使用批量操作，调整索引参数

### 7.3 内存使用过高
- **问题**：内存使用超过系统限制
- **解决**：减少缓存大小，使用更轻量级的嵌入模型

### 7.4 数据备份失败
- **问题**：备份过程中出现错误
- **解决**：检查磁盘空间，确保文件权限正确

## 8. 总结

本指南提供了向量存储服务的部署和运维方案，包括单实例部署、容器化部署和高可用部署，以及备份恢复、性能监控和故障处理等运维管理措施。通过遵循本指南，可以确保向量存储服务的稳定运行和高性能响应，为 LLM Wiki 系统提供可靠的向量存储支持。
