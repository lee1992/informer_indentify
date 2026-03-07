# main.py
import sys
import os

# ================= 兼容交互环境的路径设置 =================
try:
    # 如果是作为脚本文件运行 (python main.py)
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:
    # 如果是在 Jupyter / IPython / 选中代码运行
    # 请手动把下面的路径改成你存放 OptionProject 文件夹的路径
    # 例如: r"D:\Work\OptionProject" 或者你当前打开的目录
    print("⚠️  检测到交互环境，尝试使用当前工作目录...")

    # 方法 A: 自动使用当前工作目录 (如果你在正确的文件夹下打开的终端)
    BASE_DIR = os.getcwd()

    # 方法 B: 如果方法 A 报错，手动取消下面这行的注释并填入绝对路径:
    # BASE_DIR = r"D:\你的\具体\路径\OptionProject"

    print(f"📍 当前工作目录设定为: {BASE_DIR}")

# 把路径加入系统，确保能 import 到 config 和 src
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
# ==========================================================

import logging
from config.settings import LOG_PATH

# 配置日志
os.makedirs(os.path.join(BASE_DIR, LOG_PATH), exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(BASE_DIR, LOG_PATH, "layer1.log")),
        logging.StreamHandler()
    ]
)

from src.strategies.layer1_pool_gen import StockPoolGenerator

if __name__ == "__main__" or "get_ipython" in globals():
    # 这里的判断也兼容了 Notebook 环境
    generator = StockPoolGenerator(BASE_DIR)
    result_df = generator.run()