#%%

import os
from dotenv import load_dotenv

load_dotenv(override=True)
id = os.getenv('ID')
pwd = os.getenv('PWD')
cert_filepath = os.getenv('CPATH')
certpwd = os.getenv('CPWD')

target_account = os.getenv('ACCOUNT')
trade_list_filepath = os.getenv('TRADELIST')

print("交易目標清單路徑:", trade_list_filepath)
print("下單帳號:", target_account)

# %%

from fubon_neo.sdk import FubonSDK
# 連接主機
sdk = FubonSDK()

# 登入取得帳號列表
response = sdk.login(
    id,
    pwd,
    cert_filepath,
    certpwd,
)

# 更新可用帳號列表
accounts = response.data

# 設定啟用帳號
active_account = None
for account in accounts:
    if target_account == account.account:
        active_account = account
        break

if active_account is not None:
    print(f"當前使用帳號\n{active_account}")
    
#%%
import pandas as pd
import numpy as np

# 以字串格式讀取交易清單
trade_df = pd.read_excel(trade_list_filepath, 
                         dtype=str)

trade_df.columns = ["symbol", "target_lot", "limit_price"]

# 移除所有空格並將空字符串轉換為 NaN
trade_df.replace(r'^\s*$', np.nan, regex=True, inplace=True)

# 檢查 target_lot 不可為負數
if (trade_df['target_lot'].astype(int)<0).any():
    raise Exception(f"目標張數不能為負數")

#%%
# 建立行情連線
sdk.init_realtime()
reststock = sdk.marketdata.rest_client.stock

# 建立市場別對應代號字典
tickers = {}
tickers["TSE"] = reststock.intraday.tickers(type='EQUITY', exchange="TWSE", market="TSE")["data"]
tickers["OTC"] = reststock.intraday.tickers(type='EQUITY', exchange="TPEx", market="OTC")["data"]
tickers["ESB"] = reststock.intraday.tickers(type='EQUITY', exchange="TPEx", market="ESB")["data"]

# 建立代號查詢市場別函式
def get_market_type(stock_symbol, tickers_dict):
    # 判斷股票類型
    if any(item['symbol'] == stock_symbol for item in tickers_dict["TSE"]):
        return "TSE"
    elif any(item['symbol'] == stock_symbol for item in tickers_dict["OTC"]):
        return "OTC"
    elif any(item['symbol'] == stock_symbol for item in tickers_dict["ESB"]):
        return "ESB"
    else:
        print(f"查無代碼 {symbol}")
        return None

#%%
# 添加新欄位 "market"，所有值設置為 None
trade_df['market'] = None

# 添加symbol對應 "market" 類訊息
for index, row in trade_df.iterrows():
    symbol = row['symbol']
    market = get_market_type(symbol, tickers)
    if market is not None:
        trade_df.at[index, 'market'] = market
    else:
        print(f"因查無股票代號，將移除本行指令 {row}")

# 移除 "market" 無法定義內容
trade_df.dropna(subset=['market'], inplace=True)
trade_df = trade_df.astype(str)
# %%

# 引用OrderType方便比對庫存型式
from fubon_neo.constant import OrderType

# 抓取庫存資料
inventories = sdk.accounting.inventories(active_account).data

# 將庫存資料整理成 代號:張數 的dictionary
inventories_dict = {
    item.stock_no: item.today_qty/1000 
    for item in inventories 
    if item.order_type == OrderType.Stock
} 

#%%

# 引用所需套件
from fubon_neo.sdk import Order
from fubon_neo.constant import TimeInForce, PriceType, MarketType, BSAction

# 依據交易目標清單開始逐筆檢視下單參數
for index, row in trade_df.iterrows():
    # 獲取該筆交易目標參數
    symbol = row["symbol"]
    target_lot = float(row["target_lot"])
    limit_price = row["limit_price"]
    market = row["market"]

    # 計算庫存差異張數
    trade_lot = target_lot - inventories_dict[symbol] if symbol in inventories_dict else target_lot
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
        response = sdk.stock.place_order(active_account, order)
        print(f"下單回報, 股票代碼 {symbol}:\n{response}\n")

    else:  # 現有庫存已達到目標張數，無須動作
        print(f"現有庫存已達到目標張數，無須動作. 股票代號 {symbol}, 目標張數: {target_lot}")
# %%

