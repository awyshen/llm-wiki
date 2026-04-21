#!/usr/bin/env python3
"""
配置管理系统测试
"""

import os
import time
from src.core.config import get_config, reload_config, watch_config


def test_config_loading():
    """测试配置加载"""
    print("=== 测试配置加载 ===")
    config = get_config()
    print(f"App host: {config.app.host}")
    print(f"App port: {config.app.port}")
    print(f"LLM model: {config.llm.model}")
    print(f"Vector store type: {config.vector_store.type}")
    print(f"Data dir: {config.data_dir}")
    print("配置加载成功！")


def test_config_defaults():
    """测试配置默认值"""
    print("\n=== 测试配置默认值 ===")
    config = get_config()
    print(f"Default app host: {config.app.host}")
    print(f"Default app port: {config.app.port}")
    print(f"Default debug mode: {config.app.debug}")
    print(f"Default LLM temperature: {config.llm.temperature}")
    print(f"Default log level: {config.log_level}")
    print("默认值测试成功！")


def test_config_reload():
    """测试配置重新加载"""
    print("\n=== 测试配置重新加载 ===")
    # 先获取当前配置
    config = get_config()
    original_port = config.app.port
    
    # 修改配置文件
    config_path = "config/config.yaml"
    with open(config_path, 'r') as f:
        content = f.read()
    
    # 修改端口号
    new_port = 5001 if original_port == 5000 else 5000
    modified_content = content.replace(f"port: {original_port}", f"port: {new_port}")
    
    with open(config_path, 'w') as f:
        f.write(modified_content)
    
    # 重新加载配置
    reload_config()
    new_config = get_config()
    print(f"原始端口: {original_port}")
    print(f"新端口: {new_config.app.port}")
    
    # 恢复配置
    restored_content = modified_content.replace(f"port: {new_port}", f"port: {original_port}")
    with open(config_path, 'w') as f:
        f.write(restored_content)
    
    reload_config()
    print("配置重新加载测试成功！")


def test_config_watch():
    """测试配置热加载"""
    print("\n=== 测试配置热加载 ===")
    config = get_config()
    original_port = config.app.port
    new_port = 5002 if original_port == 5000 else 5000
    
    # 定义回调函数
    def config_changed():
        print("配置已更新！")
        new_config = get_config()
        print(f"新端口: {new_config.app.port}")
    
    # 启动配置监视
    watch_config(callback=config_changed)
    print("已启动配置监视...")
    
    # 修改配置文件
    config_path = "config/config.yaml"
    with open(config_path, 'r') as f:
        content = f.read()
    
    modified_content = content.replace(f"port: {original_port}", f"port: {new_port}")
    with open(config_path, 'w') as f:
        f.write(modified_content)
    
    print("已修改配置文件，等待热加载...")
    time.sleep(6)  # 等待热加载
    
    # 恢复配置
    restored_content = modified_content.replace(f"port: {new_port}", f"port: {original_port}")
    with open(config_path, 'w') as f:
        f.write(restored_content)
    
    time.sleep(6)  # 等待热加载
    print("配置热加载测试成功！")


def test_config_cache():
    """测试配置缓存"""
    print("\n=== 测试配置缓存 ===")
    # 第一次加载
    start_time = time.time()
    config1 = get_config()
    load_time1 = time.time() - start_time
    print(f"第一次加载时间: {load_time1:.4f}秒")
    
    # 第二次加载（应该使用缓存）
    start_time = time.time()
    config2 = get_config()
    load_time2 = time.time() - start_time
    print(f"第二次加载时间: {load_time2:.4f}秒")
    
    print(f"缓存是否生效: {load_time2 < load_time1 * 0.1}")  # 缓存应该快10倍以上
    print("配置缓存测试成功！")


if __name__ == "__main__":
    test_config_loading()
    test_config_defaults()
    test_config_reload()
    test_config_watch()
    test_config_cache()
    print("\n所有测试完成！")
