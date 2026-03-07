# src/data/external_data.py
import pandas as pd
import logging
import json
import os

logger = logging.getLogger(__name__)


class ExternalDataFetcher:
    def __init__(self):
        pass

    def _get_wikipedia_table(self, url, column_name='Symbol'):
        """通用方法：从 Wikipedia 页面解析表格获取股票代码"""
        try:
            logger.info(f"正在解析 Wikipedia: {url}")
            tables = pd.read_html(url)
            for i, df in enumerate(tables):
                if column_name in df.columns:
                    tickers = df[column_name].tolist()
                    tickers = [str(t).replace('.', '-') for t in tickers if pd.notna(t)]
                    logger.info(f"成功提取 {len(tickers)} 只标的")
                    return tickers
            logger.error(f"未在页面中找到包含 '{column_name}' 列的表格")
            return []
        except Exception as e:
            logger.error(f"解析 Wikipedia 失败: {e}")
            return []

    def get_sp500_tickers(self):
        """获取标普500成分股"""
        url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
        return self._get_wikipedia_table(url, column_name='Symbol')

    def get_nasdaq100_tickers(self):
        """获取纳斯达克100成分股"""
        url = 'https://en.wikipedia.org/wiki/NASDAQ-100'
        return self._get_wikipedia_table(url, column_name='Ticker')

    def get_tier3_universe(self):
        """获取 Tier 3 基础池 (标普500 + 纳指100 并集)"""
        sp500 = self.get_sp500_tickers()
        nasdaq100 = self.get_nasdaq100_tickers()
        combined = list(set(sp500 + nasdaq100))
        logger.info(f"标普500 + 纳指100 去重后共 {len(combined)} 只标的")
        return combined

    def load_manual_config(self, config_path):
        """加载手动配置的 JSON"""
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"找不到配置文件: {config_path}")

        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        tier_1 = []
        for category in data['tier_1_core']:
            tier_1.extend(data['tier_1_core'][category])

        tier_2 = data.get('tier_2_legacy', [])

        tier_1 = list(set([str(t).upper() for t in tier_1]))
        tier_2 = list(set([str(t).upper() for t in tier_2]))

        return tier_1, tier_2