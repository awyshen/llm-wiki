# LLM Wiki - AI驱动个人知识库系统

基于Karpathy的LLM Wiki理念构建的个人知识管理系统，实现自动知识构建、沉淀与自我增强功能。

## 核心理念

不同于传统的RAG（检索增强生成）系统，LLM Wiki采用**增量式知识编译**的方式：

- **知识编译**：LLM将原始文档"编译"成结构化的Wiki页面，而非简单索引
- **持续积累**：知识被沉淀为可复用的Wiki页面，而非每次重新检索
- **自我增强**：系统能够自动发现知识关联、填补知识空白、解决矛盾

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                        用户交互层                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Web界面    │  │   API服务    │  │   CLI工具    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                        处理引擎层                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  知识处理器   │  │  实体提取器   │  │  图谱构建器   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                        存储层                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  关系数据库   │  │  Wiki文件    │  │  向量数据库   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

## 功能特性

### 知识采集

- 支持多种文件格式：Markdown、PDF、Word、HTML、纯文本
- 自动文件监控，实时检测新文件
- 批量导入目录
- 支持文件验证和错误处理

### AI处理引擎

- 智能文档解析和摘要生成
- 实体识别与关系提取
- 自动分类和标签生成
- 知识图谱构建
- 并行处理文档，提高处理效率

### 知识存储

- 关系型数据库存储元数据
- Markdown文件存储Wiki内容
- 支持Obsidian等工具直接访问
- 向量数据库存储嵌入向量

### 知识检索

- 全文搜索
- 实体关联查询
- 智能问答
- 知识图谱路径查询
- 相关实体查询

### 知识图谱

- 完整的node-link-node关系结构可视化
- 实体属性和关系属性的层级展示
- 支持图谱缩放、平移、节点拖拽等交互功能
- 支持节点高亮、路径查询结果可视化
- 支持图谱导出为JSON或CSV格式

## 快速开始

### 1. 安装依赖

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置系统

```bash
# 复制配置模板
cp config/config.yaml.example config/config.yaml

# 编辑配置，设置API密钥
vim config/config.yaml
```

### 3. 初始化系统

```bash
python main.py init
```

### 4. 导入文档

```bash
# 导入单个文件
python main.py import /path/to/document.pdf

# 导入整个目录
python main.py import /path/to/documents/
```

### 5. 处理文档

```bash
python main.py process
```

### 6. 启动服务

```bash
# 启动API服务
python main.py api

# 启动Web界面
python main.py webui
```

### 7. 访问前端界面

```bash
# 启动前端服务器
cd frontend
python3 -m http.server 8080

# 访问 http://localhost:8080/
```

## 使用方法

### CLI命令

```bash
# 初始化系统
python main.py init

# 导入文档
python main.py import ./my-docs

# 处理待处理文档
python main.py process

# 搜索知识库
python main.py search "关键词"

# 启动API服务
python main.py api

# 启动Web界面
python main.py webui
```

### API接口

系统提供RESTful API，主要端点包括：

- `GET /api/documents` - 获取文档列表
- `POST /api/documents/upload` - 上传文档
- `GET /api/wiki/pages` - 获取Wiki页面列表
- `GET /api/wiki/search?q=关键词` - 搜索Wiki
- `GET /api/entities` - 获取实体列表
- `POST /api/process/documents` - 处理待处理文档
- `POST /api/backup/create` - 创建备份

### Web界面

访问 `http://localhost:7860` 使用Web界面进行：

- 文档上传和管理
- Wiki页面浏览和编辑
- 知识图谱可视化
- 系统设置

### 前端界面

访问 `http://localhost:8080` 使用新的前端界面进行：

- 文档导入和管理
- 文档处理
- Wiki浏览
- 高级搜索
- 知识图谱可视化
- 系统状态监控

## 目录结构

```
llm-wiki/
├── config/                 # 配置文件
│   └── config.yaml        # 主配置
├── data/                   # 数据目录
│   ├── raw/               # 原始文件
│   ├── wiki/              # Wiki页面
│   │   ├── articles/     # 文章
│   │   ├── entities/     # 实体页面
│   │   └── indices/      # 索引页面
│   └── backup/            # 备份文件
├── logs/                   # 日志文件
├── src/                    # 源代码
│   ├── core/              # 核心模块
│   ├── collect/           # 采集模块
│   ├── process/           # 处理模块
│   ├── storage/           # 存储模块
│   ├── api/               # API模块
│   └── interface/         # 界面模块
├── frontend/              # 前端界面
│   ├── src/               # 前端源代码
│   ├── index.html         # 主页面
│   ├── styles.css         # 样式文件
│   └── script.js          # 主要脚本
├── tests/                  # 测试文件
├── docs/                   # 文档
├── main.py                 # 主入口
└── requirements.txt        # 依赖列表
```

## 配置说明

### 基础配置

```yaml
system:
  name: "LLM Wiki"
  language: "zh-CN"
  log_level: "INFO"

paths:
  data_dir: "./data"
  wiki_dir: "./data/wiki"
```

### LLM配置

```yaml
llm:
  default_provider: "openai"
  
  openai:
    api_key: "${OPENAI_API_KEY}"
    model: "gpt-4"
    temperature: 0.3
```

### 处理配置

```yaml
processing:
  auto_process: true
  process_interval: 300
  
  file_watcher:
    enabled: true
    patterns: ["*.md", "*.txt", "*.pdf"]
```

### 向量存储配置

```yaml
vector_store:
  type: "chroma"
  path: "./data/vector_db"
  embedding_model: "text-embedding-ada-002"
  collection_name: "llm_wiki"
```

## 核心模块功能

### 1. 文件采集模块
- **FileCollector**：负责从本地文件系统收集文档，支持导入单个文件或整个目录
- **支持的文件类型**：md, txt, pdf, doc, docx, rtf, html, htm, csv, xlsx, xls, ppt, pptx
- **错误处理**：提供文件验证、异常捕获和错误日志记录

### 2. 知识处理模块
- **KnowledgeProcessor**：协调文档处理流程，调用LLM进行知识提取和Wiki页面生成
- **并行处理**：支持多线程并行处理文档，提高处理效率
- **状态管理**：跟踪文档处理状态，支持失败重试

### 3. 知识图谱构建模块
- **KnowledgeGraphBuilder**：从文档和Wiki页面中提取实体和关系，构建知识图谱
- **实体提取**：使用LLM提取实体及其属性
- **关系提取**：识别实体之间的关系
- **图谱存储**：支持保存到数据库和文件

### 4. 知识图谱可视化模块
- **KnowledgeGraphVisualization**：提供知识图谱的构建和可视化功能
- **路径查询**：查找两个实体之间的路径
- **相关实体查询**：获取与指定实体相关的实体
- **图谱导出**：支持导出为JSON或CSV格式

### 5. 前端界面
- **现代化设计**：响应式布局，支持不同屏幕尺寸
- **交互式操作**：支持节点拖拽、缩放、平移等交互功能
- **功能完整**：包含文档导入、管理、处理、Wiki浏览、高级搜索、知识图谱可视化和系统状态监控

## 性能优化

- **并行处理**：使用ThreadPoolExecutor并行处理文档
- **批量操作**：数据库批量插入和更新
- **缓存机制**：配置缓存，减少重复加载
- **资源限制**：设置最大工作线程数，避免资源耗尽
- **错误处理**：完善的异常捕获和错误日志记录

## 最新变更

### v1.0.0 (2026-04-20)

#### 主要功能变更
- **完整的知识图谱功能**：实现了node-link-node关系结构可视化，支持实体属性和关系属性的层级展示
- **前端界面重构**：使用HTML、CSS和JavaScript构建了现代化的前端界面，替代了原来的Gradio界面
- **多文档导入处理**：支持批量导入和处理多个文档
- **知识图谱交互功能**：实现了图谱缩放、平移、节点拖拽等交互功能
- **路径查询与相关实体**：支持知识图谱的路径查询和相关实体查询
- **图谱导出功能**：支持将知识图谱导出为JSON或CSV格式

#### 性能优化
- **并行处理**：使用多线程并行处理文档，提高处理效率
- **错误处理**：完善的异常捕获和错误日志记录
- **缓存机制**：配置缓存，减少重复加载

#### 已知问题及修复情况
- **修复了centerNode未定义错误**：确保知识图谱相关实体查询功能正常运行
- **修复了路径查询功能**：解决了路径查询时的变量未定义问题
- **修复了图谱网络可视化问题**：确保图谱能够正常渲染和展示

## 开发计划

- [x] 核心架构设计
- [x] 配置管理系统
- [x] 数据库存储
- [x] 文件采集模块
- [x] LLM客户端
- [x] API服务
- [x] Web界面完善
- [x] 知识图谱可视化
- [x] 高级搜索功能
- [ ] 多语言支持
- [ ] 用户认证系统
- [ ] 更多可视化图表
- [ ] 优化移动端体验
- [ ] 集成更多数据源

## 贡献指南

欢迎提交Issue和Pull Request！

## 许可证

MIT License

## 致谢

- 感谢Andrej Karpathy提出的LLM Wiki理念