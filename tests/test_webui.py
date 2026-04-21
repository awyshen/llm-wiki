#!/usr/bin/env python3
"""
测试WebUI启动
"""

import sys
import traceback
from src.interface.gradio_ui import create_gradio_ui, run_webui

print("开始测试WebUI创建...")
try:
    demo = create_gradio_ui()
    print("WebUI创建成功!")
    
    print("\n尝试启动WebUI...")
    # 这里不实际启动，只是测试创建过程
    print("WebUI启动测试完成!")
    
except Exception as e:
    print(f"错误: {e}")
    traceback.print_exc()
    sys.exit(1)

print("\n测试完成!")
sys.exit(0)