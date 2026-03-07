# config/settings.py
import os

# 项目根目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Layer 1 配置
LAYER1_CONFIG = {
    "OUTPUT_DIR": os.path.join(BASE_DIR, "data", "processed", "stock_pools"),
    "MAX_CAPACITY": 500  # 股票池最大容量
}

# 日志路径
LOG_PATH = os.path.join(BASE_DIR, "logs")