#!/bin/bash
# LLM Wiki 启动脚本

set -e

echo "=========================================="
echo "  LLM Wiki - AI驱动个人知识库系统"
echo "=========================================="

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到Python3"
    exit 1
fi

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "创建虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
echo "激活虚拟环境..."
source venv/bin/activate

# 安装依赖
echo "检查依赖..."
pip install -q -r requirements.txt

# 初始化系统
echo "初始化系统..."
python main.py init

echo ""
echo "请选择运行模式:"
echo "1) API服务 (http://localhost:8000)"
echo "2) Web界面 (http://localhost:7860)"
echo "3) 导入文档"
echo "4) 处理文档"
echo "5) 搜索知识库"
echo ""
read -p "请输入选项 (1-5): " choice

case $choice in
    1)
        echo "启动API服务..."
        python main.py api
        ;;
    2)
        echo "启动Web界面..."
        python main.py webui
        ;;
    3)
        read -p "请输入文档路径: " doc_path
        python main.py import "$doc_path"
        ;;
    4)
        echo "处理待处理文档..."
        python main.py process
        ;;
    5)
        read -p "请输入搜索关键词: " query
        python main.py search "$query"
        ;;
    *)
        echo "无效选项"
        exit 1
        ;;
esac
