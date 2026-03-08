# config/settings.py
import os
from datetime import timedelta

# 基础路径配置
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_PATH = os.path.join(BASE_DIR, "logs")
OUTPUT_PATH = os.path.join(BASE_DIR, "output")
HISTORY_PATH = os.path.join(BASE_DIR, "history")  # 历史版本存储目录

# 富途订阅限制配置
FUTU_MAX_SUBSCRIBE = 1000  # 富途30天订阅上限
FUTU_SAFE_LIMIT = 900      # 安全阈值（预留100冗余）
FUTU_ROLLING_DAYS = 30     # 30天滚动计算窗口期

# 定期更新配置
UPDATE_CYCLE = timedelta(days=30)  # 30天滚动更新
UPDATE_TRIGGER_DAY = 1             # 备选：每月1号触发（二选一）

# 股票池优先级（从高到低）
POOL_PRIORITY = [
    "abnormal_pool",    # 异常股票池（人工标记/自动添加）
    "manual_pool",      # 手动添加池
    "nasdaq100_pool",   # 纳斯达克100
    "dji_pool",         # 道指
    "sp500_pool"        # 标普500
]

# 【更新】股票池文件路径配置
ABNORMAL_POOL_PATH = os.path.join(BASE_DIR, "pools", "abnormal_pool.csv")  # 改为CSV，存时间戳
MANUAL_POOL_PATH = os.path.join(BASE_DIR, "pools", "manual_pool.txt")      # 保持TXT，纯手动

# 确保目录存在
for path in [LOG_PATH, OUTPUT_PATH, HISTORY_PATH, os.path.dirname(ABNORMAL_POOL_PATH)]:
    os.makedirs(path, exist_ok=True)