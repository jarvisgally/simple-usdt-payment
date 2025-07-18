import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class Config:
    # Flask配置
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-please-change'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///orders.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # BSC配置
    BSC_ENDPOINT = os.environ.get('BSC_ENDPOINT') or 'https://bsc-dataseed.bnbchain.org'
    BSC_COLLECT_ADDRESS = os.environ.get('BSC_COLLECT_ADDRESS')
    BSC_GAS_ADDRESS = os.environ.get('BSC_GAS_ADDRESS')
    BSC_GAS_ADDRESS_PRIVATE_KEY = os.environ.get('BSC_GAS_ADDRESS_PRIVATE_KEY')
    
    # 调度器配置
    SCHEDULER_API_ENABLED = True
    JOBS = [
        {
            'id': 'check_orders',
            'func': 'scheduler:check_orders',
            'trigger': 'interval',
            'seconds': 30,  # 每30秒检查一次
            'args': (None,)  # 将在运行时替换为app实例
        }
    ]
