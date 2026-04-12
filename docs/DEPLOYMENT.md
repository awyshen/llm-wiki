# LLM Wiki 部署指南

## 系统要求

### 最低配置
- **操作系统**: Linux/macOS/Windows
- **Python**: 3.9+
- **内存**: 4GB RAM
- **磁盘**: 10GB 可用空间
- **网络**: 可访问LLM API（OpenAI/Anthropic）

### 推荐配置
- **内存**: 8GB+ RAM
- **磁盘**: SSD，50GB+ 可用空间
- **CPU**: 多核处理器

## 安装步骤

### 1. 环境准备

#### Linux/macOS
```bash
# 检查Python版本
python3 --version

# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate
```

#### Windows
```powershell
# 检查Python版本
python --version

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
venv\Scripts\activate
```

### 2. 安装依赖

```bash
# 升级pip
pip install --upgrade pip

# 安装依赖
pip install -r requirements.txt
```

### 3. 配置系统

#### 3.1 配置文件

编辑 `config/config.yaml`：

```yaml
# 系统配置
system:
  name: "LLM Wiki - AI驱动个人知识库"
  language: "zh-CN"
  log_level: "INFO"

# LLM配置
llm:
  default_provider: "openai"
  
  openai:
    api_key: "your-openai-api-key-here"
    model: "gpt-4"
    temperature: 0.3
    max_tokens: 4096
```

#### 3.2 环境变量（推荐）

创建 `.env` 文件：

```bash
# LLM API密钥
OPENAI_API_KEY=your-openai-api-key-here
ANTHROPIC_API_KEY=your-anthropic-api-key-here

# 系统密钥
SECRET_KEY=your-secret-key-for-jwt
```

### 4. 初始化系统

```bash
# 初始化数据库和目录
python main.py init
```

输出示例：
```
正在初始化LLM Wiki系统...
✓ 系统初始化完成
  - 数据目录: ./data
  - Wiki目录: ./data/wiki
  - 数据库: sqlite:///data/llm_wiki.db
```

## 运行方式

### 方式一：命令行工具

```bash
# 导入文档
python main.py import /path/to/documents/

# 处理文档
python main.py process

# 搜索知识库
python main.py search "关键词"
```

### 方式二：API服务

```bash
# 启动API服务
python main.py api
```

服务将在 `http://localhost:8000` 启动

#### API文档

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### 方式三：Web界面

```bash
# 启动Web界面
python main.py webui
```

访问 `http://localhost:7860`

## 生产环境部署

### 使用Gunicorn（Linux/macOS）

```bash
# 安装Gunicorn
pip install gunicorn

# 启动服务
gunicorn -w 4 -k uvicorn.workers.UvicornWorker "src.api.app:create_app()" -b 0.0.0.0:8000
```

### 使用Docker

#### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY . .

# 创建数据目录
RUN mkdir -p data wiki backup logs

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["python", "main.py", "api"]
```

#### 构建和运行

```bash
# 构建镜像
docker build -t llm-wiki .

# 运行容器
docker run -d \
  --name llm-wiki \
  -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  -e OPENAI_API_KEY=your-api-key \
  llm-wiki
```

#### Docker Compose

```yaml
version: '3.8'

services:
  llm-wiki:
    build: .
    container_name: llm-wiki
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - SECRET_KEY=${SECRET_KEY}
    restart: unless-stopped
```

```bash
# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 使用Systemd（Linux）

创建服务文件 `/etc/systemd/system/llm-wiki.service`：

```ini
[Unit]
Description=LLM Wiki Service
After=network.target

[Service]
Type=simple
User=llm-wiki
WorkingDirectory=/opt/llm-wiki
Environment="OPENAI_API_KEY=your-api-key"
Environment="PATH=/opt/llm-wiki/venv/bin"
ExecStart=/opt/llm-wiki/venv/bin/python main.py api
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# 重新加载systemd
sudo systemctl daemon-reload

# 启动服务
sudo systemctl start llm-wiki

# 设置开机自启
sudo systemctl enable llm-wiki

# 查看状态
sudo systemctl status llm-wiki

# 查看日志
sudo journalctl -u llm-wiki -f
```

## Nginx反向代理

### 配置示例

```nginx
server {
    listen 80;
    server_name wiki.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
}
```

### HTTPS配置（Let's Encrypt）

```bash
# 安装Certbot
sudo apt install certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d wiki.yourdomain.com

# 自动续期
sudo certbot renew --dry-run
```

## 备份与恢复

### 自动备份

系统支持自动备份，在配置中启用：

```yaml
backup:
  enabled: true
  interval: 86400  # 每天
  max_backups: 7
  compress: true
```

### 手动备份

```bash
# 通过API创建备份
curl -X POST http://localhost:8000/api/backup/create

# 查看备份列表
curl http://localhost:8000/api/backup/list
```

### 恢复备份

```python
from src.storage.backup_manager import BackupManager

manager = BackupManager()
manager.restore_backup("backup_20240101_120000")
```

## 监控与日志

### 日志位置

- 应用日志: `logs/llm_wiki_YYYYMMDD.log`
- 错误日志: `logs/llm_wiki_error_YYYYMMDD.log`

### 日志轮转

日志自动轮转，保留最近5个文件，单个文件最大10MB。

### 健康检查

```bash
# 检查服务状态
curl http://localhost:8000/health

# 预期响应
{"status": "healthy", "version": "1.0.0"}
```

## 性能优化

### 数据库优化

```yaml
database:
  pool_size: 20
  max_overflow: 40
  pool_timeout: 60
```

### 异步处理

对于大量文档，建议使用异步处理：

```python
from src.process.knowledge_processor import KnowledgeProcessor

processor = KnowledgeProcessor()
processor.process_pending_documents_async()
```

## 故障排查

### 常见问题

#### 1. 数据库锁定

**症状**: `database is locked`

**解决**: 
- 检查是否有其他进程正在访问数据库
- 增加连接池大小
- 使用WAL模式

#### 2. LLM API错误

**症状**: API调用失败

**解决**:
- 检查API密钥是否正确
- 检查网络连接
- 查看API配额

#### 3. 内存不足

**症状**: 处理大文件时崩溃

**解决**:
- 增加系统内存
- 减小处理批次大小
- 启用流式处理

### 调试模式

```yaml
system:
  debug: true
  log_level: "DEBUG"
```

## 升级指南

### 备份数据

```bash
# 创建完整备份
curl -X POST http://localhost:8000/api/backup/create
```

### 更新代码

```bash
# 拉取最新代码
git pull origin main

# 更新依赖
pip install -r requirements.txt --upgrade

# 运行数据库迁移（如有）
python main.py migrate
```

### 验证升级

```bash
# 运行测试
pytest tests/

# 检查服务
python main.py init
curl http://localhost:8000/health
```

## 安全建议

1. **API密钥管理**: 使用环境变量，不要硬编码
2. **访问控制**: 配置防火墙，限制访问IP
3. **HTTPS**: 生产环境必须使用HTTPS
4. **定期备份**: 设置自动备份策略
5. **日志审计**: 定期检查日志文件

## 支持

- 文档: `docs/`
- 问题反馈: GitHub Issues
- 社区讨论: GitHub Discussions
