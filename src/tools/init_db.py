"""
初始化数据库
"""

import os
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.config import get_config
from src.storage.database import get_db_manager
from src.storage.models import Base


def init_database():
    """
    初始化数据库
    """
    print("初始化数据库...")
    
    # 获取数据库引擎
    db_manager = get_db_manager()
    engine = db_manager.engine
    
    # 创建所有表
    Base.metadata.create_all(engine)
    
    print("数据库初始化完成！")


if __name__ == "__main__":
    init_database()
