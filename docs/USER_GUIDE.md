# LLM Wiki 用户操作手册

## 目录

1. [快速开始](#快速开始)
2. [核心概念](#核心概念)
3. [使用指南](#使用指南)
4. [最佳实践](#最佳实践)
5. [常见问题](#常见问题)

## 快速开始

### 第一步：系统初始化

```bash
python main.py init
```

这将创建必要的目录结构和数据库。

### 第二步：导入文档

```bash
# 导入单个文件
python main.py import /path/to/document.pdf

# 导入整个目录
python main.py import /path/to/documents/
```

### 第三步：处理文档

```bash
python main.py process
```

系统将使用AI处理导入的文档，生成Wiki页面。

### 第四步：访问知识库

```bash
# 启动Web界面
python main.py webui

# 或启动API服务
python main.py api
```

## 核心概念

### 文档 (Document)

原始导入的文件，支持多种格式：
- Markdown (.md)
- PDF (.pdf)
- Word (.docx, .doc)
- 文本 (.txt)
- HTML (.html, .htm)

### Wiki页面 (WikiPage)

AI生成的结构化知识页面，存储在 `data/wiki/` 目录下：
- **articles/** - 普通文章
- **entities/** - 实体页面
- **concepts/** - 概念页面
- **indices/** - 索引页面

### 实体 (Entity)

从文档中提取的知识单元：
- 人物
- 组织
- 地点
- 概念
- 技术
- 项目
- 事件

### 知识图谱

实体之间的关系网络，支持：
- 自动关系提取
- 路径查找
- 关联推荐

## 使用指南

### 1. 文档导入

#### 通过Web界面

1. 打开Web界面 (`python main.py webui`)
2. 进入"文档导入"标签页
3. 选择要导入的文件
4. 点击"导入文档"

#### 通过命令行

```bash
# 导入单个文件
python main.py import ./my-document.pdf

# 导入目录（递归）
python main.py import ./my-documents/

# 导入目录（不递归）
python main.py import ./my-documents/ --no-recursive
```

#### 自动监控

系统会自动监控 `data/raw/` 目录，新放入的文件会自动导入。

### 2. 文档处理

#### 批量处理

```bash
python main.py process
```

#### 单个处理

通过API：
```bash
curl -X POST http://localhost:8000/api/process/document/{document_id}
```

### 3. 知识检索

#### 全文搜索

```bash
python main.py search "人工智能"
```

#### 高级搜索

通过Web界面：
1. 进入"搜索"标签页
2. 输入关键词
3. 查看结果

#### API搜索

```bash
curl "http://localhost:8000/api/wiki/search?q=关键词"
```

### 4. Wiki浏览

#### 通过文件系统

Wiki页面存储在 `data/wiki/` 目录，可直接使用Obsidian等工具打开。

#### 通过Web界面

1. 进入"Wiki浏览"标签页
2. 查看页面列表
3. 点击标题查看详情

### 5. 备份与恢复

#### 创建备份

```bash
# 通过API
curl -X POST http://localhost:8000/api/backup/create

# 或通过代码
python -c "from src.storage.backup_manager import BackupManager; BackupManager().create_backup()"
```

#### 查看备份

```bash
curl http://localhost:8000/api/backup/list
```

#### 恢复备份

```python
from src.storage.backup_manager import BackupManager

manager = BackupManager()
manager.restore_backup("backup_20240101_120000")
```

## 最佳实践

### 1. 文档组织

- 按主题组织文档目录
- 使用有意义的文件名
- 定期清理重复文档

### 2. 处理策略

- 大批量文档建议分批处理
- 重要文档优先处理
- 定期检查处理失败的任务

### 3. 知识维护

- 定期审查生成的Wiki页面
- 手动修正实体关系
- 添加缺失的标签

### 4. 备份策略

- 每日自动备份
- 重要变更前手动备份
- 定期验证备份完整性

### 5. 性能优化

- 控制单次处理文档数量
- 定期清理日志文件
- 监控磁盘空间

## 常见问题

### Q: 如何处理处理失败的文档？

A: 
1. 查看错误日志：`logs/llm_wiki_error_*.log`
2. 重新处理：`python main.py process`
3. 或通过API单独处理特定文档

### Q: 可以修改生成的Wiki页面吗？

A: 可以。Wiki页面是标准的Markdown文件，可以直接编辑。修改后系统会自动更新索引。

### Q: 如何导出知识库？

A: 
1. 创建完整备份
2. 直接复制 `data/wiki/` 目录
3. 导出数据库：`sqlite3 data/llm_wiki.db ".dump" > backup.sql`

### Q: 支持哪些LLM？

A: 目前支持：
- OpenAI (GPT-4, GPT-3.5)
- Anthropic (Claude)

可在配置中切换提供商。

### Q: 如何提高处理质量？

A:
1. 使用更强大的LLM模型（如GPT-4）
2. 预处理文档，确保文本清晰
3. 手动审查和修正生成的内容
4. 添加更多示例训练数据

### Q: 系统安全吗？

A:
- 数据存储在本地
- API密钥通过环境变量管理
- 支持HTTPS（需配置）
- 定期备份防止数据丢失

### Q: 可以多人协作吗？

A: 当前版本主要面向个人使用。多人协作功能正在开发中，建议：
- 使用Git管理Wiki文件
- 共享数据库备份
- 通过API集成到协作平台

## 获取帮助

- 查看日志：`logs/` 目录
- API文档：`http://localhost:8000/docs`
- 提交Issue：GitHub Issues

## 更新日志

### v1.0.0
- 初始版本发布
- 支持多格式文档导入
- AI驱动的知识处理
- Wiki页面自动生成
- 知识图谱构建
- Web界面和API
