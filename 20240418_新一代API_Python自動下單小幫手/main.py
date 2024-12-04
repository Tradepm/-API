import pandas as pd
import numpy as np
import logging
import asyncio
import os
from dotenv import load_dotenv
import utils
from fubon_neo.sdk import FubonSDK, Order
from fubon_neo.constant import TimeInForce, OrderType, PriceType, MarketType, BSAction

global LOGGER


class TopTrader:
    global LOGGER

    def __init__(self, id, pwd, cert_filepath, certpwd):
        self.logger = LOGGER
        self.sdk = None
        self.credential = {
            "id": id,
            "pwd": pwd,
            "cert_filepath": cert_filepath,
            "certpwd": certpwd,
        }
        self.accounts = None  # 可使用帳號列表
        self.active_account = None  # 交易及帳務查詢時使用帳號
        self.trade_df = None  # 交易目標列表
        self.inventories = None  # 庫存資料
        self.is_trade_active = False  # 是否交易正在進行

        # 股票行情資訊相關
        self.tickers = None

    @staticmethod
    def check_account_set(func):
        """
        自定義的靜態方法，用於確認使用帳號是否已設置。
        如果未設置，則輸出錯誤訊息。
        """

        def wrapper(self, *args, **kwargs):
            if self.active_account is None:
                self.logger.error("未設置使用帳號，請先設置使用帳號")
            else:
                # 如果帳號已設置，執行原始函數
                return func(self, *args, **kwargs)

        return wrapper

    # Run routines
    # param:
    # - target_account: 交易帳號 (str)
    # - trade_list_filepath: 交易列表檔案 (str)
    def run(self, target_account: str, trade_list_filepath: str):
        # 登入
        self.__login()

        # 設定帳號
        self.set_active_account(target_account)

        # 設定交易列表並開始交易
        self.set_trade_list_and_start_trade(trade_list_filepath)

        self.logger.info("程式執行完畢")

    # 登入
    def __login(self):
        # 重設可用帳號列表
        self.accounts = None

        # 連接主機
        self.sdk = FubonSDK()

        # 登入取得帳號列表
        response = self.sdk.login(
            self.credential["id"],
            self.credential["pwd"],
            self.credential["cert_filepath"],
            self.credential["certpwd"],
        )

        self.logger.info(f"登入回報:\n{response}")

        # 登入行情主機行情
        self.sdk.init_realtime()

        # 更新可用帳號列表
        if response.data is not None and len(response.data) > 0:
            self.accounts = response.data

    # 取得可用帳戶列表
    def get_accounts(self):
        if self.accounts is None:
            self.logger.error(f"無可用帳戶")

        return self.accounts

    # 設定使用帳戶
    # param:
    # - target_account: 交易帳號 (str)
    def set_active_account(self, target_account: str):
        if self.accounts is None:
            self.logger.error(f"無可用帳戶")

        else:
            try:
                for account in self.accounts:
                    if target_account == account.account:
                        self.active_account = account
                        break

                if self.active_account is not None:
                    self.logger.info(f"當前使用帳號\n{self.active_account}")
                else:
                    self.logger.error(f"查無給定帳號, 給定帳號 {account}")
            except Exception as e:
                self.logger.error(f"設定使用帳號錯誤: {e}")

    # 設定交易列表
    @check_account_set
    def set_trade_list(self, filepath):
        # 子功能-------------------------------------
        def clean_trade_list(df):
            # 1. 移除所有空格並將空字符串轉換為 NaN
            df.replace(r'^\s*$', np.nan, regex=True, inplace=True)

            # 2. 將 target_lot 轉換為正整數（包括 0)
            try:
                df['target_lot'] = df['target_lot'].astype(float).astype(int)
                if (df['target_lot'] < 0).any():
                    raise Exception(f"目標張數不能為負數")
            except ValueError:
                df['target_lot'] = np.nan

            # 3. 將所有值轉換為字符串或 NaN
            df = df.astype(str)

            # 4. 添加新列 "market"，所有值設置為 NaN
            df['market'] = np.nan
            df['market'] = df['market'].astype('object')

            # 5. 添加市場 "market" 類型訊息
            for index, row in df.iterrows():
                symbol = row['symbol']
                market = self.__get_market_type(symbol)
                if market is not None:
                    df.at[index, 'market'] = market
                else:
                    self.logger.warning(f"因查無股票代號，將移除本行指令 {row}")

            # 5. 移除 "market" 無法定義內容
            df.dropna(subset=['market'], inplace=True)

            return df

        # ------------------------------------------

        # 確認是否交易正在進行
        if self.is_trade_active:
            self.logger.error(f"交易環節已啟動，無法設定交易列表")
            return False

        # 重置交易列表
        self.trade_df = None

        # 讀取並設置交易列表
        try:
            self.trade_df = pd.read_excel(filepath, dtype=str)
            self.trade_df.columns = ["symbol", "target_lot", "limit_price"]
        except FileNotFoundError as e:
            self.logger.error(f"找不到檔案 {filepath}, 錯誤訊息 {e}")
            return False
        except pd.errors.ParserError as e:
            self.logger.error(f"檔案格式解析錯誤, 錯誤訊息 {e}")
            return False

        # 清理交易列表格式
        self.trade_df = clean_trade_list(self.trade_df)

        return True

    # 啟動交易環節
    @check_account_set
    def activate_trade(self):
        # 確認是否交易正在進行
        if self.is_trade_active:
            self.logger.error(f"交易環節已啟動，無法設定交易列表")
            return False

        # 確認是否交易列表已設定成功
        if self.trade_df is None:
            self.logger.error(f"交易列表未設置，請先設定交易列表")
            return

        # 取得庫存資料
        inventories = self.__get_current_inventories()
        self.inventories = {item.stock_no: item.today_qty / 1000 for item in inventories if
                            item.order_type == OrderType.Stock}

        # 執行下單
        self.is_trade_active = True

        asyncio.run(self.__trader())

        self.is_trade_active = False

        return True

    # 設定交易列表且啟動交易環節
    @check_account_set
    def set_trade_list_and_start_trade(self, filepath):
        is_success = self.set_trade_list(filepath)
        if is_success and (self.trade_df is not None):
            self.activate_trade()
        else:
            self.logger.error(f"交易列表設定失敗，不執行交易環節")

    # -----------------------------------------------------------
    #                       API 串接相關功能
    # -----------------------------------------------------------
    @check_account_set
    def __get_market_type(self, symbol):
        if self.tickers is None:
            self.tickers = {}
            self.tickers["TSE"] = self.sdk.marketdata.rest_client.stock.intraday.tickers(type='EQUITY', exchange="TWSE",
                                                                                         market="TSE")["data"]
            self.tickers["OTC"] = self.sdk.marketdata.rest_client.stock.intraday.tickers(type='EQUITY', exchange="TPEx",
                                                                                         market="OTC")["data"]
            self.tickers["ESB"] = self.sdk.marketdata.rest_client.stock.intraday.tickers(type='EQUITY', exchange="TPEx",
                                                                                         market="ESB")["data"]

        # 判斷股票類型
        if any(item['symbol'] == symbol for item in self.tickers["TSE"]):
            return "TSE"
        elif any(item['symbol'] == symbol for item in self.tickers["OTC"]):
            return "OTC"
        elif any(item['symbol'] == symbol for item in self.tickers["ESB"]):
            return "ESB"
        else:
            self.logger.warning(f"查無代碼 {symbol}")
            return None

    @check_account_set
    def __get_current_inventories(self, retry=0):
        response = self.sdk.accounting.inventories(self.active_account)
        if not response.is_success and retry < 1:
            return self.__get_current_inventories(retry=retry + 1)
        elif not response.is_success:
            return []
        else:
            return response.data

    @check_account_set
    async def __trader(self):
        tasks = []
        for index, row in self.trade_df.iterrows():
            task = asyncio.create_task(self.__trader_assist(row))
            tasks.append(task)

        await asyncio.gather(*tasks)

    async def __trader_assist(self, row):
        symbol = row["symbol"]
        target_lot = float(row["target_lot"])
        limit_price = row["limit_price"]
        market = row["market"]

        # 計算差異張數
        inventory_qty = self.inventories[symbol] if symbol in self.inventories else 0
        trade_lot = target_lot - inventory_qty

        self.logger.debug(f"股號 {symbol}, 目標張數 {target_lot}, 現有庫存 {inventory_qty}, 買賣 {trade_lot} 張")

        if abs(trade_lot) > 0:
            # 建立委託單
            order = Order(
                buy_sell=BSAction.Buy if trade_lot > 0 else BSAction.Sell,
                symbol=symbol,
                price=limit_price if "nan" not in limit_price else None,
                quantity=int(abs(trade_lot) * 1000),
                market_type=MarketType.Common if not ("ESB" in market) else MarketType.Emg,
                price_type=PriceType.Limit if "nan" not in limit_price else PriceType.Market,
                time_in_force=TimeInForce.ROD,
                order_type=OrderType.Stock,
            )

            # 下單
            response = self.sdk.stock.place_order(self.active_account, order, unblock=False)
            self.logger.info(f"下單回報, 股票代碼 {symbol}:\n{response}\n")

        else:  # 現有庫存已達到目標張數，無須動作
            self.logger.info(f"現有庫存已達到目標張數，無須動作. 股票代號 {symbol}, 目標張數: {target_lot}")


# 主程式
if __name__ == '__main__':
    global LOGGER

    try:
        utils.mk_folder("log")
        LOGGER = utils.get_logger("TopTrader",
                                  "log/TopTrader.log",
                                  log_level=logging.DEBUG
                                  )

        # 讀取帳號密碼資料進入環境變數
        load_dotenv()

        id = os.getenv('ID')
        pwd = os.getenv('PWD')
        cert_filepath = os.getenv('CPATH')
        certpwd = os.getenv('CPWD')

        account = os.getenv('ACCOUNT')
        trade_list_filepath = os.getenv('TRADELIST')

        # 建立 TopTrader
        top_trader = TopTrader(id, pwd, cert_filepath, certpwd)

        # 啟動 TopTrader
        top_trader.run(account, trade_list_filepath)

    except Exception as e:
        LOGGER.error(f"{e}")

    finally:
        # 程式結束
        print("Press Enter to exit...")
        input()
