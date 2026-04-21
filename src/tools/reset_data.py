#!/usr/bin/env python3
"""
系统数据重置脚本

清理并初始化文件数据库、知识图谱数据库及向量数据库，确保所有历史数据被彻底清除，数据库恢复至初始配置状态。
"""

import os
import shutil
import logging
from datetime import datetime

from src.core.config import get_config
from src.core.logger import get_logger
from src.storage.database import get_db_manager
from src.storage.models import Base
from src.storage.vector.factory import get_vector_store
from sqlalchemy import text

# 配置日志
logger = get_logger(__name__)
logger.setLevel(logging.INFO)

# 创建文件处理器
file_handler = logging.FileHandler('reset_data.log')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

# 控制台处理器
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(console_handler)


def reset_sql_database():
    """
    重置SQL数据库
    """
    try:
        logger.info("开始重置SQL数据库...")
        
        # 获取数据库管理器
        db_manager = get_db_manager()
        
        # 删除所有表
        Base.metadata.drop_all(bind=db_manager.engine)
        logger.info("成功删除所有数据库表")
        
        # 重新创建所有表
        Base.metadata.create_all(bind=db_manager.engine)
        logger.info("成功重新创建数据库表")
        
        return True
    except Exception as e:
        logger.error(f"重置SQL数据库失败: {e}")
        return False


def reset_vector_database():
    """
    重置向量数据库
    """
    try:
        logger.info("开始重置向量数据库...")
        
        # 获取配置
        config = get_config()
        vector_db_path = config.vector_store.path
        
        # 删除向量数据库目录
        if os.path.exists(vector_db_path):
            shutil.rmtree(vector_db_path)
            logger.info(f"成功删除向量数据库目录: {vector_db_path}")
        
        # 重新创建目录
        os.makedirs(vector_db_path, exist_ok=True)
        logger.info(f"成功重新创建向量数据库目录: {vector_db_path}")
        
        # 重新初始化向量存储
        vector_store = get_vector_store()
        if vector_store:
            logger.info("成功重新初始化向量存储")
        else:
            logger.warning("向量存储初始化失败")
        
        return True
    except Exception as e:
        logger.error(f"重置向量数据库失败: {e}")
        return False


def reset_data_directory():
    """
    重置数据目录
    """
    try:
        logger.info("开始重置数据目录...")
        
        # 获取配置
        config = get_config()
        data_dir = config.data_dir
        
        # 保留目录结构，只删除内容
        subdirs = ['raw', 'wiki', 'backup']
        for subdir in subdirs:
            subdir_path = os.path.join(data_dir, subdir)
            if os.path.exists(subdir_path):
                # 删除子目录内容
                for item in os.listdir(subdir_path):
                    item_path = os.path.join(subdir_path, item)
                    if os.path.isfile(item_path):
                        os.remove(item_path)
                    elif os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                logger.info(f"成功清空目录: {subdir_path}")
            else:
                # 创建目录
                os.makedirs(subdir_path, exist_ok=True)
                logger.info(f"成功创建目录: {subdir_path}")
        
        return True
    except Exception as e:
        logger.error(f"重置数据目录失败: {e}")
        return False


def verify_database_integrity():
    """
    验证数据库完整性
    """
    try:
        logger.info("开始验证数据库完整性...")
        
        # 验证SQL数据库
        db_manager = get_db_manager()
        with db_manager.get_session() as session:
            # 测试数据库连接
            session.execute(text("SELECT 1"))
            logger.info("SQL数据库连接正常")
        
        # 验证向量数据库
        vector_store = get_vector_store()
        if vector_store:
            logger.info("向量数据库连接正常")
        else:
            logger.warning("向量数据库连接异常")
        
        # 验证数据目录
        config = get_config()
        data_dir = config.data_dir
        if os.path.exists(data_dir):
            logger.info(f"数据目录存在: {data_dir}")
        else:
            logger.error(f"数据目录不存在: {data_dir}")
            return False
        
        return True
    except Exception as e:
        logger.error(f"验证数据库完整性失败: {e}")
        return False


def main():
    """
    主函数
    """
    logger.info("=" * 80)
    logger.info(f"开始系统数据重置操作 - {datetime.utcnow()}")
    logger.info("=" * 80)
    
    # 1. 重置SQL数据库
    sql_result = reset_sql_database()
    
    # 2. 重置向量数据库
    vector_result = reset_vector_database()
    
    # 3. 重置数据目录
    data_result = reset_data_directory()
    
    # 4. 验证数据库完整性
    integrity_result = verify_database_integrity()
    
    logger.info("=" * 80)
    logger.info("系统数据重置操作结果:")
    logger.info(f"- SQL数据库重置: {'成功' if sql_result else '失败'}")
    logger.info(f"- 向量数据库重置: {'成功' if vector_result else '失败'}")
    logger.info(f"- 数据目录重置: {'成功' if data_result else '失败'}")
    logger.info(f"- 数据库完整性验证: {'成功' if integrity_result else '失败'}")
    
    if all([sql_result, vector_result, data_result, integrity_result]):
        logger.info("系统数据重置操作完成，所有任务均成功")
    else:
        logger.warning("系统数据重置操作完成，但部分任务失败")
    
    logger.info("=" * 80)
    logger.info(f"系统数据重置操作结束 - {datetime.utcnow()}")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
