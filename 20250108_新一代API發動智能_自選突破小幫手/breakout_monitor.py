from login_gui_v2 import login_handler

import sys
import pickle
import json
import pandas as pd
from pathlib import Path

import fubon_neo
from fubon_neo.sdk import FubonSDK, Mode, Order
from fubon_neo.constant import TimeInForce, OrderType, PriceType, MarketType, BSAction
from breakout_ui import MyUI

from PySide6.QtWidgets import QApplication, QWidget, QTableWidgetItem, QFileDialog
from PySide6.QtGui import QTextCursor, QColor, QFont, QPalette
from PySide6.QtCore import Qt, Signal, QObject
from threading import Timer

class RepeatTimer(Timer):
    def run(self):
        while not self.finished.wait(self.interval):
            self.function(*self.args, **self.kwargs)

# 仿FilledData的物件
class fake_filled_data():
    date="2023/09/15"
    branch_no="6460"          
    account="123"   
    order_no="bA422"          
    stock_no="00900"            
    buy_sell=BSAction.Sell     
    filled_no="00000000001"    
    filled_avg_price=35.2      
    filled_qty=1000
    filled_price=35.2          
    order_type=OrderType.Stock
    filled_time="10:31:00.931"  
    user_def=None

class Communicate(QObject):
    # 定義一個帶參數的信號
    print_log_signal = Signal(str)
    update_table_row_signal = Signal(str, float, float, float, bool)
    order_qty_update = Signal(str, int)
    filled_qty_update = Signal(str, int)
    stop_btn_signal = Signal()
    start_btn_signal = Signal()

class bob_trader(QWidget):
    def __init__(self, login_handler):
        super().__init__()

        self.login_handler = login_handler
        self.sdk = self.login_handler.sdk
        self.active_account = self.login_handler.active_account

        self.bob_ui = MyUI()

        # 設定窗口屬性
        self.setWindowTitle(self.bob_ui.windowTitle())
        self.setWindowIcon(self.bob_ui.windowIcon())
        self.resize(1000, 600)

        # 將 MyUI 的佈局設定到 MainWindow
        self.setLayout(self.bob_ui.layout())

        my_target_path = None
        my_target_list_file = Path("./target_list_path.pkl")
        if my_target_list_file.is_file():
            with open('./target_list_path.pkl', 'rb') as f:
                temp_dict = pickle.load(f)
                my_target_path = temp_dict['target_list_path']
            self.bob_ui.lineEdit_default_file_path.setText(my_target_path)

        ### 建立連線開始跑主要程式
        self.print_log("現在使用SDK版本: "+fubon_neo.__version__)
        self.print_log("login success, 現在使用帳號: {}".format(self.active_account.account))
        self.print_log("建立行情連線...")

        self.connect_mode = Mode.Normal
        self.sdk.init_realtime(self.connect_mode) # 建立行情連線
        self.print_log("行情連線建立OK")
        self.reststock = self.sdk.marketdata.rest_client.stock
        self.wsstock = self.sdk.marketdata.websocket_client.stock

        # button slot function connect
        self.bob_ui.folder_btn.clicked.connect(self.showDialog)
        self.bob_ui.read_csv_btn.clicked.connect(self.read_target_list)
        self.bob_ui.button_start.clicked.connect(self.on_button_start_clicked)
        self.bob_ui.button_stop.clicked.connect(self.on_button_stop_clicked)
        self.bob_ui.button_fake_buy_filled.clicked.connect(self.fake_buy_filled)
        self.bob_ui.button_fake_websocket.clicked.connect(self.fake_ws_data)

        # communicator slot function connect
        self.communicator = Communicate()
        self.communicator.print_log_signal.connect(self.print_log)
        self.communicator.order_qty_update.connect(self.update_order_qty_item)
        self.communicator.filled_qty_update.connect(self.update_filled_qty_item)
        self.communicator.update_table_row_signal.connect(self.update_table_row)
        self.communicator.stop_btn_signal.connect(self.on_button_stop_clicked)
        self.communicator.start_btn_signal.connect(self.on_button_start_clicked)
        
        # variable init
        self.table_header = self.bob_ui.table_header
        self.row_idx_map = {}
        self.col_idx_map = dict(zip(self.table_header, range(0, len(self.table_header)))) 
        self.last_close_dict = {}
        self.subscribed_ids = {}
        self.order_tag = 'bob'
        self.is_ordered = {}
        self.is_filled = {}
        self.target_symbols = []
        self.epsilon = 0.0000001
        self.used_budget = 0
        self.active_logout = False
        self.fake_price_cnt = 0
        self.volume_threshold = 0
        self.chg_p_threshold = 0

    def fake_disconnect(self):
        # self.wsstock.disconnect()
        self.sdk.logout()

    # 測試用假裝有websocket data的按鈕slot function
    def fake_ws_data(self):
        if self.fake_price_cnt % 2==0:
            self.price_interval = 0
            self.fake_ws_timer = RepeatTimer(0.01, self.fake_message, args=(list(self.row_idx_map.keys())[0], ))
            self.fake_ws_timer.start()
        else:
            self.fake_ws_timer.cancel()

        self.fake_price_cnt+=1

    def fake_message(self, stock_no):
        self.price_interval+=1
        json_template = '''{{"event":"data","data":{{"symbol":"{symbol}","type":"EQUITY","exchange":"TWSE","market":"TSE","price":{price},"size":213,"bid":16.67,"ask":{price}, "isLimitUpAsk":true, "volume":8066,"isClose":true,"time":1718343000000000,"serial":9475857}},"id":"w4mkzAqYAYFKyEBLyEjmHEoNADpwKjUJmqg02G3OC9YmV","channel":"trades"}}'''
        json_price = 15+self.price_interval
        if json_price >= 20:
            json_template = '''{{"event":"data","data":{{"symbol":"{symbol}","type":"EQUITY","exchange":"TWSE","market":"TSE","price":{price},"size":213,"bid":16.67,"ask":{price}, "isLimitUpPrice":true, "volume":500,"isClose":true,"time":1718343000000000,"serial":9475857}},"id":"w4mkzAqYAYFKyEBLyEjmHEoNADpwKjUJmqg02G3OC9YmV","channel":"trades"}}'''
        json_str = json_template.format(symbol=stock_no, price=str(json_price))
        self.handle_message(json_str)

    # 測試用假裝有買入成交的按鈕slot function
    def fake_buy_filled(self):
        new_fake_buy = fake_filled_data()
        if self.row_idx_map:
            new_fake_buy.stock_no = list(self.row_idx_map.keys())[0]
        else:
            return
        new_fake_buy.buy_sell = BSAction.Buy
        new_fake_buy.filled_qty = 2000
        new_fake_buy.filled_price = 17
        new_fake_buy.account = self.active_account.account
        new_fake_buy.user_def = self.order_tag
        self.on_filled(None, new_fake_buy)

    def update_table_row(self, symbol, price, bid, ask, is_limit_up):
        if bid > 0:
            self.bob_ui.tablewidget.item(self.row_idx_map[symbol], self.col_idx_map['買進']).setText(str(round(bid+self.epsilon, 2)))
        elif bid == 0:
            self.bob_ui.tablewidget.item(self.row_idx_map[symbol], self.col_idx_map['買進']).setText('市價')
        elif bid == -1:
            self.bob_ui.tablewidget.item(self.row_idx_map[symbol], self.col_idx_map['買進']).setText('-')

        if ask > 0:
            self.bob_ui.tablewidget.item(self.row_idx_map[symbol], self.col_idx_map['賣出']).setText(str(round(ask+self.epsilon, 2)))
        elif ask == 0:
            self.bob_ui.tablewidget.item(self.row_idx_map[symbol], self.col_idx_map['賣出']).setText('市價')
        elif ask == -1:
            self.bob_ui.tablewidget.item(self.row_idx_map[symbol], self.col_idx_map['賣出']).setText('-')
        
        if price>0:
            self.bob_ui.tablewidget.item(self.row_idx_map[symbol], self.col_idx_map['成交']).setText(str(round(price+self.epsilon, 2)))
            up_range = (price-self.last_close_dict[symbol])/self.last_close_dict[symbol]*100
            self.bob_ui.tablewidget.item(self.row_idx_map[symbol], self.col_idx_map['漲幅(%)']).setText(str(round(up_range+self.epsilon, 2))+'%')
        else:
            self.bob_ui.tablewidget.item(self.row_idx_map[symbol], self.col_idx_map['成交']).setText('-')
        
        if is_limit_up:
            self.bob_ui.tablewidget.item(self.row_idx_map[symbol], self.col_idx_map['漲幅(%)']).setBackground(QColor(Qt.red))
            self.bob_ui.tablewidget.item(self.row_idx_map[symbol], self.col_idx_map['漲幅(%)']).setForeground(QColor(Qt.white))
        else:
            self.bob_ui.tablewidget.item(self.row_idx_map[symbol], self.col_idx_map['漲幅(%)']).setBackground(QColor(Qt.transparent))
            item = self.bob_ui.tablewidget.item(self.row_idx_map[symbol], self.col_idx_map['漲幅(%)'])
            # source.ensurePolished() # leave this commented for now
            default_color = self.bob_ui.tablewidget.palette().windowText().color()
            item.setForeground(default_color)

    def update_filled_qty_item(self, symbol, filled_qty):
        self.bob_ui.tablewidget.item(self.row_idx_map[symbol], self.col_idx_map['成交數量']).setText(str(filled_qty))

    def update_order_qty_item(self, symbol, order_qty):
        self.bob_ui.tablewidget.item(self.row_idx_map[symbol], self.col_idx_map['委託數量']).setText(str(order_qty))

    def on_event(self, code, content):
        if code == '300':
            self.communicator.print_log_signal.emit("Trade connection unexpected disconnect")
            self.communicator.print_log_signal.emit("Try reconnecting...")
            my_file = Path("./info.pkl")
            if my_file.is_file():
                with open('info.pkl', 'rb') as f:
                    user_info_dict = pickle.load(f)

            self.sdk = FubonSDK()
            if user_info_dict['cert_pwd'] != "":
                accounts = self.sdk.login(user_info_dict['id'], user_info_dict['pwd'], Path(user_info_dict['cert_path']).__str__(), user_info_dict['cert_pwd'])
            else:
                accounts = self.sdk.login(user_info_dict['id'], user_info_dict['pwd'], Path(user_info_dict['cert_path']).__str__())
            print(accounts)
            
            self.communicator.stop_btn_signal.emit()
            print("disconnect ws first")
            self.communicator.start_btn_signal.emit()
            print("connect success")

    def on_filled(self, err, content):
        if err:
            print("Filled Error:", err, "Content:", content)
            return
        
        if content.account == self.active_account.account:
            if content.user_def == self.order_tag:
                if content.stock_no in self.is_filled:
                    self.is_filled[content.stock_no] += content.filled_qty
                else:
                    self.is_filled[content.stock_no] = content.filled_qty

                self.communicator.filled_qty_update.emit(content.stock_no, self.is_filled[content.stock_no])
                self.communicator.print_log_signal.emit(content.stock_no+'...成功成交'+str(content.filled_qty)+'股, '+'成交價:'+str(content.filled_price))

    def buy_market_order(self, symbol, buy_qty, tag='bob'):
        order = Order(
            buy_sell = BSAction.Buy,
            symbol = symbol,
            price =  None,
            quantity =  int(buy_qty),
            market_type = MarketType.Common,
            price_type = PriceType.Market,
            time_in_force = TimeInForce.ROD,
            order_type = OrderType.Stock,
            user_def = tag # optional field
        )

        order_res = self.sdk.stock.place_order(self.active_account, order)
        return order_res

    def handle_message(self, message):
        msg = json.loads(message)
        event = msg["event"]
        data = msg["data"]
        print(event, data)

         # subscribed事件處理
        if event == "subscribed":
            if type(data) == list:
                for subscribed_item in data:
                    id = subscribed_item["id"]
                    symbol = subscribed_item["symbol"]
                    self.communicator.print_log_signal.emit('訂閱成功...'+symbol)
                    self.subscribed_ids[symbol] = id

                    if symbol in self.is_ordered:
                        self.communicator.order_qty_update.emit(symbol, self.is_ordered[symbol])
                    if symbol in self.is_filled:
                        self.communicator.filled_qty_update.emit(symbol, self.is_filled[symbol])
            else:
                id = data["id"]
                symbol = data["symbol"]
                self.communicator.print_log_signal.emit('訂閱成功'+symbol)
                self.subscribed_ids[symbol] = id
        
        elif event == "unsubscribed":
            for key, value in self.subscribed_ids.items():
                if value == data["id"]:
                    print(value)
                    remove_key = key
            self.subscribed_ids.pop(remove_key)
            self.communicator.print_log_signal.emit(remove_key+"...成功移除訂閱")

        elif event == "snapshot":
            symbol = data['symbol']
            if 'isTrial' in data:
                if data['isTrial']:
                    return
                
            is_limit_up = False
            if 'isLimitUpPrice' in data:
                is_limit_up = True

            if 'ask' not in data:
                data['ask'] = -1
            if 'bid' not in data:
                data['bid'] = -1
            if 'price' not in data:
                data['price'] = -1
            
            # print(event, data)
            self.communicator.update_table_row_signal.emit(symbol, data['price'], data['bid'], data['ask'], is_limit_up)

        elif event == "data":
            symbol = data['symbol']
            if 'isTrial' in data:
                if data['isTrial']:
                    return
                
            is_limit_up = False
            if 'isLimitUpPrice' in data:
                is_limit_up = True

            if 'ask' not in data:
                data['ask'] = -1
            if 'bid' not in data:
                data['bid'] = -1
            if 'price' not in data:
                data['price'] = -1
            
            # print(event, data)
            self.communicator.update_table_row_signal.emit(symbol, data['price'], data['bid'], data['ask'], is_limit_up)
            
            if 'price' in data:
                change_percent = (data['price']-self.last_close_dict[symbol])/self.last_close_dict[symbol]*100
                if change_percent >= self.chg_p_threshold and (symbol not in self.is_ordered):
                    if (self.trade_budget <= (self.total_budget-self.used_budget)):
                        self.communicator.print_log_signal.emit(symbol+'...送出市價單')
                        if data['volume'] >= self.volume_threshold:
                            print(change_percent, self.chg_p_threshold)
                            buy_qty = self.trade_budget//(data['price']*1000)*1000
                                
                            if buy_qty <= 0:
                                self.communicator.print_log_signal.emit(symbol+'...額度不足購買1張')
                            else:
                                self.communicator.print_log_signal.emit(symbol+'...委託'+str(buy_qty)+'股')
                                order_res = self.buy_market_order(symbol, buy_qty, self.order_tag)
                                if order_res.is_success:
                                    self.communicator.print_log_signal.emit(symbol+"...市價單發送成功，單號: "+order_res.data.order_no)
                                    self.is_ordered[symbol] = buy_qty
                                    self.used_budget+=buy_qty*data['price']
                                    self.communicator.order_qty_update.emit(symbol, buy_qty)
                                else:
                                    self.communicator.print_log_signal.emit(symbol+"...市價單發送失敗...")
                                    self.communicator.print_log_signal.emit(order_res.message)
                        else:
                            self.communicator.print_log_signal.emit(symbol+"...交易量不足，市價單發送失敗...")
                    else:
                        self.communicator.print_log_signal.emit(symbol+"總額度超限 "+"已使用額度/總額度: "+str(self.used_budget)+'/'+str(self.total_budget))

    def handle_connect(self):
        self.communicator.print_log_signal.emit('market data connected')
    
    def handle_disconnect(self, code, message):
        if self.active_logout:
            self.active_logout=False
            print("logout manully")
            self.communicator.print_log_signal.emit(f'WebSocket已停止')
        else:
            self.communicator.print_log_signal.emit(f'market data disconnect: {code}, {message}')
            self.communicator.print_log_signal.emit(f'try reconnect...')
            self.communicator.start_btn_signal.emit()
    
    def handle_error(self, error):
        self.communicator.print_log_signal.emit(f'market data error: {error}')

    def on_button_start_clicked(self):
        
        try:
            self.trade_budget = float(self.bob_ui.lineEdit_trade_budget.text())
            if self.trade_budget<0:
                self.print_log("請輸入正確的每檔買入額度(萬元), 必須大於0")
                return
            else:
                self.trade_budget = self.trade_budget*10000
        except Exception as e:
            self.print_log("請輸入正確的每檔買入額度(萬元), "+str(e))
            return

        try:
            self.total_budget = float(self.bob_ui.lineEdit_total_budget.text())
            if self.total_budget<0:
                self.print_log("請輸入正確的總額度(萬元), 必須大於0")
                return
            else:
                self.total_budget = self.total_budget*10000
        except Exception as e:
            self.print_log("請輸入正確的總額度(萬元), "+str(e))
            return
        
        try:
            self.volume_threshold = int(self.bob_ui.lineEdit_total_volume.text())
            if self.volume_threshold<0:
                self.print_log("請輸入正確的交易量門檻(張), 整數, 必須大於等於0")
                return
        except Exception as e:
            self.print_log("請輸入正確的交易量門檻(張), "+str(e))
            return
        
        try:
            self.chg_p_threshold = float(self.bob_ui.lineEdit_change_percent.text())
            if self.chg_p_threshold<0:
                self.print_log("請輸入正確的突破百分比(%), 浮點數, 必須大於等於0")
                return
        except Exception as e:
            self.print_log("請輸入正確的漲停前tick數, "+str(e))
            return

        self.print_log("開始執行監控, "+str(self.volume_threshold))
        self.bob_ui.lineEdit_trade_budget.setReadOnly(True)
        self.bob_ui.lineEdit_total_budget.setReadOnly(True)
        self.bob_ui.lineEdit_total_volume.setReadOnly(True)
        self.bob_ui.lineEdit_change_percent.setReadOnly(True)
        self.bob_ui.button_start.setVisible(False)
        self.bob_ui.button_stop.setVisible(True)
        self.bob_ui.folder_btn.setEnabled(False)
        self.bob_ui.read_csv_btn.setEnabled(False)

        self.print_log(f"現在使用 單檔金額:{self.trade_budget}, 總金額:{self.total_budget}, 交易量門檻:{self.volume_threshold}, 漲幅門檻:{self.chg_p_threshold}")

        # 重啟時需重設之參數
        self.sdk.init_realtime(self.connect_mode)
        self.wsstock = self.sdk.marketdata.websocket_client.stock
        self.wsstock.on('message', self.handle_message)
        self.wsstock.on('connect', self.handle_connect)
        self.wsstock.on('disconnect', self.handle_disconnect)
        self.wsstock.on('error', self.handle_error)
        self.wsstock.connect()

        if self.target_symbols:
            self.wsstock.subscribe({
                'channel': 'trades',
                'symbols': self.target_symbols
            })
        else:
            self.print_log("請先讀取下單目標清單")
            self.on_button_stop_clicked()

        self.sdk.set_on_filled(self.on_filled)
        self.sdk.set_on_event(self.on_event)

    def on_button_stop_clicked(self):
        self.print_log("停止執行監控")
        self.bob_ui.lineEdit_trade_budget.setReadOnly(False)
        self.bob_ui.lineEdit_total_budget.setReadOnly(False)
        self.bob_ui.lineEdit_total_volume.setReadOnly(False)
        self.bob_ui.lineEdit_change_percent.setReadOnly(False)
        self.bob_ui.button_stop.setVisible(False)
        self.bob_ui.button_start.setVisible(True)
        self.bob_ui.folder_btn.setEnabled(True)
        self.bob_ui.read_csv_btn.setEnabled(True)

        self.active_logout=True
        self.wsstock.disconnect()
        self.subscribed_ids = {}

    def tick_diff_price_cal(self, limit_up_price, diff_num):
        epsilon = 0.0000001

        if diff_num<0:
            for i in range(abs(diff_num)):
                if limit_up_price <= 10:
                    limit_up_price = limit_up_price-0.01
                elif limit_up_price <= 50:
                    limit_up_price = limit_up_price-0.05
                elif limit_up_price <= 100:
                    limit_up_price = limit_up_price-0.1
                elif limit_up_price <= 500:
                    limit_up_price = limit_up_price-0.5
                elif limit_up_price <= 1000:
                    limit_up_price = limit_up_price-1
                elif limit_up_price > 1000:
                    limit_up_price = limit_up_price-5
        else:
            for i in range(diff_num):
                if limit_up_price < 10:
                    limit_up_price = limit_up_price+0.01
                elif limit_up_price < 50:
                    limit_up_price = limit_up_price+0.05
                elif limit_up_price < 100:
                    limit_up_price = limit_up_price+0.1
                elif limit_up_price < 500:
                    limit_up_price = limit_up_price+0.5
                elif limit_up_price < 1000:
                    limit_up_price = limit_up_price+1
                elif limit_up_price >= 1000:
                    limit_up_price = limit_up_price+5

        return round(limit_up_price+epsilon, 2)

    def read_target_list(self):
        self.print_log("reading target list...")
        target_path = Path(self.bob_ui.lineEdit_default_file_path.text())
        # print(target_path)
        if str(target_path) == '.':
            self.communicator.print_log_signal('請輸入正確檔案路徑')
        else:
            try:
                self.buy_target = pd.read_csv(target_path, skiprows=3)
            except UnicodeDecodeError as e:
                print("uff-8 fail, try cp950...", e)
                self.buy_target = pd.read_csv(target_path, encoding='cp950', skiprows=3)
            # print(self.buy_target)
            self.buy_target = self.buy_target.dropna()

            self.target_symbols = list(self.buy_target.iloc[:, 1].str.replace('.TW', ''))
            self.print_log("target symbols: "+str(self.target_symbols))

            row = self.bob_ui.tablewidget.rowCount()
            if row!=0:
                self.bob_ui.tablewidget.clearContents()
                self.bob_ui.tablewidget.setRowCount(0)
                self.row_idx_map = {}

            for symbol in self.target_symbols:
                ticker_res = self.reststock.intraday.ticker(symbol=symbol)
                # self.print_log(ticker_res['name'])
                self.last_close_dict[symbol] = ticker_res['referencePrice']

                row = self.bob_ui.tablewidget.rowCount()
                self.bob_ui.tablewidget.insertRow(row)
                self.row_idx_map[symbol] = row

                for j in range(len(self.table_header)):
                    if self.table_header[j] == '股票名稱':
                        item = QTableWidgetItem(ticker_res['name'])
                        self.bob_ui.tablewidget.setItem(row, j, item)
                    elif self.table_header[j] == '股票代號':
                        item = QTableWidgetItem(ticker_res['symbol'])
                        self.bob_ui.tablewidget.setItem(row, j, item)
                    elif self.table_header[j] == '上市櫃':
                        item = QTableWidgetItem(ticker_res['market'])
                        self.bob_ui.tablewidget.setItem(row, j, item)
                    elif self.table_header[j] == '成交':
                        item = QTableWidgetItem('-')
                        self.bob_ui.tablewidget.setItem(row, j, item)
                    elif self.table_header[j] == '買進':
                        item = QTableWidgetItem('-')
                        self.bob_ui.tablewidget.setItem(row, j, item)
                    elif self.table_header[j] == '賣出':
                        item = QTableWidgetItem('-')
                        self.bob_ui.tablewidget.setItem(row, j, item)
                    elif self.table_header[j] == '漲幅(%)':
                        item = QTableWidgetItem('-')
                        self.bob_ui.tablewidget.setItem(row, j, item)
                    elif self.table_header[j] == '委託數量':
                        item = QTableWidgetItem('0')
                        self.bob_ui.tablewidget.setItem(row, j, item)
                    elif self.table_header[j] == '成交數量':
                        item = QTableWidgetItem('0')
                        self.bob_ui.tablewidget.setItem(row, j, item)

    def showDialog(self):
        my_target_path = None
        my_target_list_file = Path("./target_list_path.pkl")
        if my_target_list_file.is_file():
            with open('./target_list_path.pkl', 'rb') as f:
                temp_dict = pickle.load(f)
                my_target_path = temp_dict['target_list_path']

        # Open the file dialog to select a file
        if my_target_path:
            file_path, _ = QFileDialog.getOpenFileName(self, '請選擇您的自選清單', my_target_path, 'All Files (*)')
        else:
            file_path, _ = QFileDialog.getOpenFileName(self, '請選擇您的自選清單', 'C:\\', 'All Files (*)')

        if file_path:
            self.bob_ui.lineEdit_default_file_path.setText(file_path)
            temp_dict = {
                'target_list_path': file_path
            }
            with open('target_list_path.pkl', 'wb') as f:
                pickle.dump(temp_dict, f)

    # 更新最新log到QPlainTextEdit的slot function
    def print_log(self, log_info):
        self.bob_ui.log_text.appendPlainText(log_info)
        self.bob_ui.log_text.moveCursor(QTextCursor.End)
    
    # 視窗關閉時要做的事，主要是關websocket連結
    def closeEvent(self, event):
        # do stuff
        self.active_logout = True
        self.print_log("disconnect websocket...")
        self.wsstock.disconnect()

        try:
            if self.fake_ws_timer.is_alive():
                self.fake_ws_timer.cancel()
        except AttributeError:
            print("no fake ws timer exist")

        self.sdk.logout()
        can_exit = True
        if can_exit:
            event.accept() # let the window close
        else:
            event.ignore()

if __name__ == '__main__':
    try:
        sdk = FubonSDK()
    except ValueError:
        raise ValueError("請確認網路連線")
    
    if not QApplication.instance():
        app = QApplication(sys.argv)
    else:
        app = QApplication.instance()
    
    font = QFont("Microsoft JhengHei", 12)
    app.setFont(font)
    login_form = login_handler(sdk, 'breakout.ico')
    login_form.show()
    login_form_res = app.exec()

    if login_form.active_account:
        bob_trader = bob_trader(login_form)
        bob_trader.show()
        bob_trader_res = app.exec()
        sys.exit(bob_trader_res)