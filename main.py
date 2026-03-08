# main.py
import sys
import os
import logging
from config.settings import LOG_PATH, BASE_DIR

# ================= 路径适配 =================
try:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:
    print("⚠️  检测到交互环境，使用当前工作目录...")
    BASE_DIR = os.getcwd()
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# ================= 日志配置 =================
os.makedirs(LOG_PATH, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_PATH, f"layer1_{datetime.now().strftime('%Y%m%d')}.log")),
        logging.StreamHandler()
    ]
)

# ================= 核心执行 =================
from src.strategies.layer1_pool_gen import StockPoolGenerator
from datetime import datetime

if __name__ == "__main__" or "get_ipython" in globals():
    generator = StockPoolGenerator()
    result_df = generator.run()
    if result_df is not None:
        print(f"\n✅ 最终Layer1股票池生成完成，总标的数: {len(result_df)}")
        print(f"📄 最新版文件路径: {os.path.join(OUTPUT_PATH, 'layer1_stock_pool_latest.txt')}")
    else:
        print("\n❌ 股票池生成失败，请查看日志！")