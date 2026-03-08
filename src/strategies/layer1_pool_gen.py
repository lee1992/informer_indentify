# src/strategies/layer1_pool_gen.py
import os
import logging
import requests
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import shutil
from config.settings import *


class StockPoolGenerator:
    def __init__(self):
        # 基础初始化
        self.logger = logging.getLogger(__name__)
        self.proxies = {'http': 'http://127.0.0.1:10809', 'https': 'http://127.0.0.1:10809'}
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")  # 时间戳（用于历史版本命名）

        # 指数配置
        self.index_config = {
            "nasdaq100_pool": {"name": "纳斯达克100", "url": "https://en.wikipedia.org/wiki/Nasdaq-100",
                               "ticker_col": "Ticker"},
            "dji_pool": {"name": "道琼斯工业平均指数",
                         "url": "https://en.wikipedia.org/wiki/Dow_Jones_Industrial_Average", "ticker_col": "Symbol"},
            "sp500_pool": {"name": "标普500", "url": "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
                           "ticker_col": "Symbol"},
        }

        # 存储各池数据（key=池名称，value=[{"ticker": 代码, "in_pool_time": 入池时间}]）
        self.pool_data = {}

    def _test_proxy_connectivity(self):
        """【更新】代理连通性测试，增加明确的VPN提示"""
        test_url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        try:
            self.logger.info(f"正在测试代理连接 (检查 V2rayN 是否启动)...")
            resp = requests.get(test_url, proxies=self.proxies, timeout=10, headers=self.headers)
            if resp.status_code == 200:
                self.logger.info("✅ 代理连通性测试通过")
                return True
            else:
                self.logger.error(f"❌ 代理测试失败，状态码: {resp.status_code}")
                return False
        except requests.exceptions.ProxyError as e:
            self.logger.error("=" * 50)
            self.logger.error("❌ 【严重错误】代理连接失败！")
            self.logger.error("   👉 请检查：")
            self.logger.error("      1. V2rayN 是否已启动？")
            self.logger.error("      2. 代理端口是否为 10809？")
            self.logger.error("      3. 代理是否已开启 '允许局域网连接'？")
            self.logger.error("=" * 50)
            return False
        except Exception as e:
            self.logger.error(f"❌ 网络连接报错: {str(e)}", exc_info=True)
            return False

    def _load_static_pool(self, pool_path, pool_name):
        """【更新】加载静态池，支持异常池的CSV格式"""
        try:
            if not os.path.exists(pool_path):
                self.logger.warning(f"⚠️ {pool_name}文件不存在，创建空文件")
                # 根据后缀创建不同格式的空文件
                if pool_path.endswith(".csv"):
                    df_empty = pd.DataFrame(columns=["ticker", "add_time", "reason"])
                    df_empty.to_csv(pool_path, index=False, encoding="utf-8")
                else:
                    with open(pool_path, "w", encoding="utf-8") as f:
                        f.write("")
                self.pool_data[pool_name] = []
                return

            if pool_path.endswith(".csv"):
                # 读取异常池 (CSV格式: ticker, add_time, reason)
                df = pd.read_csv(pool_path)
                # 确保必要列存在
                if "ticker" not in df.columns:
                    raise ValueError("CSV文件缺少 'ticker' 列")
                # 格式化数据
                df["in_pool_time"] = df.get("add_time", self.timestamp)  # 兼容旧数据
                self.pool_data[pool_name] = df[["ticker", "in_pool_time"]].to_dict("records")
            else:
                # 读取手动池 (TXT格式: 每行一个代码)
                with open(pool_path, "r", encoding="utf-8") as f:
                    tickers = [line.strip().upper() for line in f if line.strip()]
                self.pool_data[pool_name] = [{"ticker": t, "in_pool_time": self.timestamp} for t in tickers]

            self.logger.info(f"✅ 加载{pool_name}完成，共{len(self.pool_data[pool_name])}个标的")
        except Exception as e:
            self.logger.error(f"❌ 加载{pool_name}失败: {str(e)}", exc_info=True)
            self.pool_data[pool_name] = []

    # ================= 【新增】异常池自动追加接口 =================
    def add_abnormal_stock(self, ticker, reason="未注明原因"):
        """
        供未来策略调用的接口：自动向异常池添加标的（永不删除）
        :param ticker: 股票代码 (如 AAPL)
        :param reason: 添加原因 (如 "20240520 期权异动")
        """
        ticker = ticker.upper().strip()
        add_time = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 1. 读取现有异常池
        if os.path.exists(ABNORMAL_POOL_PATH):
            df = pd.read_csv(ABNORMAL_POOL_PATH)
        else:
            df = pd.DataFrame(columns=["ticker", "add_time", "reason"])

        # 2. 检查是否已存在（避免重复添加）
        if ticker in df["ticker"].values:
            self.logger.info(f"ℹ️ 标的 {ticker} 已在异常池中，跳过添加")
            return False

        # 3. 追加新数据
        new_row = pd.DataFrame([{"ticker": ticker, "add_time": add_time, "reason": reason}])
        df = pd.concat([df, new_row], ignore_index=True)

        # 4. 保存（覆盖原文件，但由于是追加，历史数据不会丢）
        df.to_csv(ABNORMAL_POOL_PATH, index=False, encoding="utf-8")
        self.logger.info(f"✅ 已向异常池添加标的: {ticker} (原因: {reason})")
        return True

    def _fetch_single_index(self, pool_key, config):
        """抓取单个指数成分股，记录入池时间"""
        tickers = []
        try:
            self.logger.info(f"开始抓取【{config['name']}】成分股")
            resp = requests.get(config["url"], proxies=self.proxies, timeout=15, headers=self.headers)
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, 'html.parser')
            for table in soup.find_all('table', {'class': 'wikitable'}):
                headers = [th.text.strip() for th in table.find_all('th')]
                if config["ticker_col"] not in headers:
                    continue
                col_idx = headers.index(config["ticker_col"])
                rows = table.find_all('tr')[1:]
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) <= col_idx:
                        continue
                    ticker = cells[col_idx].text.strip().replace('\n', '').upper()  # 统一大写
                    if ticker and ticker not in [t["ticker"] for t in tickers]:
                        tickers.append({"ticker": ticker, "in_pool_time": self.timestamp})

            self.pool_data[pool_key] = tickers
            self.logger.info(f"✅ 【{config['name']}】抓取完成，共{len(tickers)}只成分股")
        except Exception as e:
            self.logger.error(f"❌ 抓取【{config['name']}】失败: {str(e)}", exc_info=True)
            self.pool_data[pool_key] = []

    def _merge_pools_by_priority(self):
        """按优先级合并所有池（高优先级覆盖低优先级）"""
        merged_tickers = {}  # key=ticker, value={"in_pool_time": 时间, "source": 来源池}
        for pool_name in POOL_PRIORITY:
            if pool_name not in self.pool_data:
                self.logger.warning(f"⚠️ {pool_name}无数据，跳过合并")
                continue

            for item in self.pool_data[pool_name]:
                ticker = item["ticker"]
                # 高优先级未覆盖时，才添加低优先级标的
                if ticker not in merged_tickers:
                    merged_tickers[ticker] = {
                        "in_pool_time": item["in_pool_time"],
                        "source": pool_name
                    }

        # 转换为DataFrame，便于后续处理
        merged_df = pd.DataFrame.from_dict(merged_tickers, orient="index").reset_index()
        merged_df.rename(columns={"index": "ticker"}, inplace=True)
        self.logger.info(f"✅ 按优先级合并完成，总标的数: {len(merged_df)}")
        return merged_df

    def _check_futu_subscribe_limit(self, merged_df):
        """校验富途订阅限制（30天滚动≤900）"""
        # 1. 筛选30天内入池的标的（滚动计算）
        cutoff_time = (datetime.now() - timedelta(days=FUTU_ROLLING_DAYS)).strftime("%Y%m%d")
        merged_df["in_pool_date"] = merged_df["in_pool_time"].str[:8]  # 提取日期（YYYYMMDD）
        rolling_tickers = merged_df[merged_df["in_pool_date"] >= cutoff_time]

        # 2. 校验数量
        rolling_count = len(rolling_tickers)
        if rolling_count > FUTU_SAFE_LIMIT:
            self.logger.error(f"❌ 30天内入池标的数({rolling_count})超过安全阈值({FUTU_SAFE_LIMIT})，终止自动流程！")
            self.logger.error(f"超量标的清单:\n{rolling_tickers[['ticker', 'source', 'in_pool_time']].to_string()}")
            # 输出超量清单到文件，便于人工筛选
            over_limit_path = os.path.join(OUTPUT_PATH, f"over_limit_tickers_{self.timestamp}.csv")
            rolling_tickers.to_csv(over_limit_path, index=False, encoding="utf-8")
            self.logger.info(f"📄 超量标的清单已保存至: {over_limit_path}")
            return None
        else:
            self.logger.info(f"✅ 订阅量校验通过：30天内入池标的数={rolling_count} ≤ {FUTU_SAFE_LIMIT}")
            return merged_df

    def _save_history_version(self, data, filename_prefix):
        """留存历史版本（按时间戳命名）"""
        history_path = os.path.join(HISTORY_PATH, f"{filename_prefix}_{self.timestamp}.csv")
        data.to_csv(history_path, index=False, encoding="utf-8")
        self.logger.info(f"✅ 历史版本已留存: {history_path}")

    def _check_update_cycle(self):
        """检查是否满足定期更新条件（30天滚动/每月固定日）"""
        # 读取上次更新记录（无则首次更新）
        last_update_path = os.path.join(OUTPUT_PATH, "last_update.txt")
        if not os.path.exists(last_update_path):
            self.logger.info("📅 首次运行，触发更新")
            return True

        # 读取上次更新时间
        with open(last_update_path, "r", encoding="utf-8") as f:
            last_update_str = f.read().strip()
        last_update = datetime.strptime(last_update_str, "%Y%m%d_%H%M%S")

        # 校验30天滚动周期
        if datetime.now() - last_update >= UPDATE_CYCLE:
            self.logger.info(f"📅 满足30天更新周期（上次更新: {last_update_str}），触发更新")
            return True
        else:
            self.logger.info(f"📅 未到更新周期（上次更新: {last_update_str}），终止流程")
            return False

    def run(self):
        """核心执行入口"""
        # 1. 校验定期更新条件
        if not self._check_update_cycle():
            return None

        # 2. 代理连通性测试
        if not self._test_proxy_connectivity():
            self.logger.error("❌ 代理测试失败，终止任务")
            return None

        # 3. 加载静态池（异常池/手动池，仅读取）
        self._load_static_pool(ABNORMAL_POOL_PATH, "abnormal_pool")
        self._load_static_pool(MANUAL_POOL_PATH, "manual_pool")

        # 4. 抓取三大指数成分股
        for pool_key, config in self.index_config.items():
            self._fetch_single_index(pool_key, config)

        # 5. 按优先级合并所有池
        merged_df = self._merge_pools_by_priority()
        if merged_df.empty:
            self.logger.error("❌ 合并后无标的，终止流程")
            return None

        # 6. 校验富途订阅限制
        final_df = self._check_futu_subscribe_limit(merged_df)
        if final_df is None:
            return None

        # 7. 留存历史版本（异常池/手动池/最终池）
        # 7.1 留存异常池/手动池历史（复制原文件+时间戳）
        for pool_name, pool_path in [("abnormal_pool", ABNORMAL_POOL_PATH), ("manual_pool", MANUAL_POOL_PATH)]:
            if os.path.exists(pool_path):
                # 提取文件后缀
                ext = os.path.splitext(pool_path)[1]
                history_copy_path = os.path.join(HISTORY_PATH, f"{pool_name}_{self.timestamp}{ext}")
                shutil.copy2(pool_path, history_copy_path)
                self.logger.info(f"✅ {pool_name}历史版本留存: {history_copy_path}")
        # 7.2 留存最终池历史
        self._save_history_version(final_df, "layer1_final_pool")

        # 8. 输出最终池
        final_pool_path = os.path.join(OUTPUT_PATH, f"layer1_stock_pool_{self.timestamp}.csv")
        final_df.to_csv(final_pool_path, index=False, encoding="utf-8")
        # 生成简易txt版本（便于快速查看）
        final_txt_path = os.path.join(OUTPUT_PATH, "layer1_stock_pool_latest.txt")
        with open(final_txt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(final_df["ticker"].tolist()))

        # 9. 记录本次更新时间（用于下次周期校验）
        with open(os.path.join(OUTPUT_PATH, "last_update.txt"), "w", encoding="utf-8") as f:
            f.write(self.timestamp)

        self.logger.info(f"✅ 全流程完成！最终池文件: {final_pool_path} | 简易版: {final_txt_path}")
        self.logger.info(f"📅 下次更新时间预估: {(datetime.now() + UPDATE_CYCLE).strftime('%Y%m%d_%H%M%S')}")
        return final_df