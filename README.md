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

### AI处理引擎
- 智能文档解析和摘要生成
- 实体识别与关系提取
- 自动分类和标签生成
- 知识图谱构建

### 知识存储
- 关系型数据库存储元数据
- Markdown文件存储Wiki内容
- 支持Obsidian等工具直接访问

### 知识检索
- 全文搜索
- 实体关联查询
- 智能问答

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

## 开发计划

- [x] 核心架构设计
- [x] 配置管理系统
- [x] 数据库存储
- [x] 文件采集模块
- [x] LLM客户端
- [x] API服务
- [ ] Web界面完善
- [ ] 知识图谱可视化
- [ ] 高级搜索功能
- [ ] 多语言支持

## 贡献指南

欢迎提交Issue和Pull Request！

## 许可证

MIT License

## 致谢

- 感谢Andrej Karpathy提出的LLM Wiki理念
- 感谢所有开源项目的贡献者
