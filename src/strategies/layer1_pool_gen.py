# src/strategies/layer1_pool_gen.py
import os
import pandas as pd
import logging
import json
import shutil
from datetime import datetime

# 注意：这里需要确保能导入到 config，我们在 main.py 里处理路径
from config.settings import LAYER1_CONFIG
from src.data.external_data import ExternalDataFetcher

logger = logging.getLogger(__name__)


class StockPoolGenerator:
    def __init__(self, base_dir):
        self.external_fetcher = ExternalDataFetcher()
        self.config = LAYER1_CONFIG
        self.max_capacity = self.config['MAX_CAPACITY']
        self.base_dir = base_dir

        # 路径管理
        self.manual_config_path = os.path.join(base_dir, 'config', 'manual_tickers.json')
        self.output_dir = self.config['OUTPUT_DIR']
        self.archive_dir = os.path.join(self.output_dir, 'archive')

        self.latest_csv_path = os.path.join(self.output_dir, 'stock_pool_latest.csv')
        self.latest_txt_path = os.path.join(self.output_dir, 'stock_pool_live.txt')
        self.meta_path = os.path.join(self.output_dir, 'meta.json')

        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.archive_dir, exist_ok=True)

    def _convert_to_futu_code(self, ticker):
        if not ticker or ticker == "NAN":
            return None
        return f"US.{ticker}"

    def _archive_current(self):
        if os.path.exists(self.latest_csv_path):
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            archive_path = os.path.join(self.archive_dir, f"stock_pool_{timestamp}.csv")
            shutil.copy(self.latest_csv_path, archive_path)
            logger.info(f"已归档旧版本")

    def _save_meta(self, status, source):
        meta = {
            'last_success': datetime.now().isoformat() if status == 'success' else None,
            'last_attempt': datetime.now().isoformat(),
            'status': status,
            'source': source
        }
        # 尝试加载旧的成功时间
        if os.path.exists(self.meta_path):
            with open(self.meta_path, 'r') as f:
                old_meta = json.load(f)
                if status != 'success' and 'last_success' in old_meta:
                    meta['last_success'] = old_meta['last_success']

        with open(self.meta_path, 'w') as f:
            json.dump(meta, f, indent=2)

    def _save_results(self, df):
        self._archive_current()
        df.to_csv(self.latest_csv_path, index=False)

        df_sorted = df.sort_values(by='tier', ascending=True)
        df_sorted['code'].to_csv(self.latest_txt_path, index=False, header=False)
        logger.info("✅ 股票池已保存")

    def _load_cache(self):
        logger.warning("⚠️ 网络失败，尝试加载本地缓存...")
        if os.path.exists(self.latest_csv_path):
            df = pd.read_csv(self.latest_csv_path)
            logger.info("✅ 加载缓存成功")
            return df
        else:
            logger.error("❌ 没有缓存可用")
            return None

    def run(self):
        logger.info("=" * 40)
        logger.info("启动 Layer 1: 股票池生成")
        logger.info("=" * 40)

        df = None

        try:
            # 1. 加载手动配置
            tier_1, tier_2 = self.external_fetcher.load_manual_config(self.manual_config_path)

            # 2. 获取网络数据
            tier_3 = self.external_fetcher.get_tier3_universe()
            if not tier_3:
                raise Exception("未获取到网络数据")

            # 3. 合并
            pool_dict = {}
            for t in tier_3: pool_dict[t] = {'ticker': t, 'tier': 3, 'priority': 10}
            for t in tier_2: pool_dict[t] = {'ticker': t, 'tier': 2, 'priority': 50}
            for t in tier_1: pool_dict[t] = {'ticker': t, 'tier': 1, 'priority': 100}

            df = pd.DataFrame(list(pool_dict.values()))
            df['code'] = df['ticker'].apply(self._convert_to_futu_code)
            df = df.dropna(subset=['code'])

            # 4. 排序与限流
            df = df.sort_values(by='priority', ascending=False).reset_index(drop=True)
            if len(df) > self.max_capacity:
                df = df.head(self.max_capacity)

            self._save_meta('success', 'wiki')
            self._save_results(df)

        except Exception as e:
            logger.error(f"❌ 生成失败: {e}")
            self._save_meta('failed', 'wiki')
            df = self._load_cache()

        # 最终输出
        if df is not None:
            logger.info("-" * 30)
            logger.info(f"完成！共 {len(df)} 只股票")
            logger.info(f"  - Tier 1: {len(df[df['tier'] == 1])}")
            logger.info(f"  - Tier 2: {len(df[df['tier'] == 2])}")
            logger.info(f"  - Tier 3: {len(df[df['tier'] == 3])}")
            logger.info("-" * 30)

        return df