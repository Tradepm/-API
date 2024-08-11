import sys
import pickle
import json
from datetime import datetime
import pandas as pd
from pathlib import Path

import fubon_neo
from fubon_neo.sdk import FubonSDK, Mode, Order
from fubon_neo.constant import TimeInForce, OrderType, PriceType, MarketType, BSAction

from PySide6.QtWidgets import QApplication, QWidget, QPushButton, QLabel, QLineEdit, QGridLayout, QVBoxLayout, QMessageBox, QTableWidget, QTableWidgetItem, QPlainTextEdit, QFileDialog, QSizePolicy
from PySide6.QtGui import QTextCursor, QIcon, QColor
from PySide6.QtCore import Qt, Signal, QObject
from threading import Timer

class LoginForm(QWidget):
    def __init__(self):
        super().__init__()
        my_icon = QIcon()
        my_icon.addFile('fast_icon.png')

        self.setWindowIcon(my_icon)
        self.setWindowTitle('新一代API登入')
        self.resize(500, 200)
        
        layout_all = QVBoxLayout()

        label_warning = QLabel('本範例僅供教學參考，使用前請先了解相關內容')
        layout_all.addWidget(label_warning)

        layout = QGridLayout()

        label_your_id = QLabel('Your ID:')
        self.lineEdit_id = QLineEdit()
        self.lineEdit_id.setPlaceholderText('Please enter your id')
        layout.addWidget(label_your_id, 0, 0)
        layout.addWidget(self.lineEdit_id, 0, 1)

        label_password = QLabel('Password:')
        self.lineEdit_password = QLineEdit()
        self.lineEdit_password.setPlaceholderText('Please enter your password')
        self.lineEdit_password.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(label_password, 1, 0)
        layout.addWidget(self.lineEdit_password, 1, 1)

        label_cert_path = QLabel('Cert path:')
        self.lineEdit_cert_path = QLineEdit()
        self.lineEdit_cert_path.setPlaceholderText('Please enter your cert path')
        layout.addWidget(label_cert_path, 2, 0)
        layout.addWidget(self.lineEdit_cert_path, 2, 1)
        
        label_cert_pwd = QLabel('Cert Password:')
        self.lineEdit_cert_pwd = QLineEdit()
        self.lineEdit_cert_pwd.setPlaceholderText('Please enter your cert password')
        self.lineEdit_cert_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(label_cert_pwd, 3, 0)
        layout.addWidget(self.lineEdit_cert_pwd, 3, 1)

        label_acc = QLabel('Account:')
        self.lineEdit_acc = QLineEdit()
        self.lineEdit_acc.setPlaceholderText('Please enter your account')
        self.lineEdit_cert_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(label_acc, 4, 0)
        layout.addWidget(self.lineEdit_acc, 4, 1)

        folder_btn = QPushButton('')
        folder_btn.setIcon(QIcon('folder.png'))
        layout.addWidget(folder_btn, 2, 2)

        login_btn = QPushButton('Login')
        layout.addWidget(login_btn, 5, 0, 1, 2)

        layout_all.addLayout(layout)
        self.setLayout(layout_all)
        
        folder_btn.clicked.connect(self.showDialog)
        login_btn.clicked.connect(self.check_password)
        
        my_file = Path("./info.pkl")
        if my_file.is_file():
            with open('info.pkl', 'rb') as f:
                user_info_dict = pickle.load(f)
                self.lineEdit_id.setText(user_info_dict['id'])
                self.lineEdit_password.setText(user_info_dict['pwd'])
                self.lineEdit_cert_path.setText(user_info_dict['cert_path'])
                self.lineEdit_cert_pwd.setText(user_info_dict['cert_pwd'])
                self.lineEdit_acc.setText(user_info_dict['target_account'])


    def showDialog(self):
        # Open the file dialog to select a file
        file_path, _ = QFileDialog.getOpenFileName(self, '請選擇您的憑證檔案', 'C:\\', 'All Files (*)')

        if file_path:
            self.lineEdit_cert_path.setText(file_path)
    
    def check_password(self):
        global active_account, sdk
        msg = QMessageBox()

        fubon_id = self.lineEdit_id.text()
        fubon_pwd = self.lineEdit_password.text()
        cert_path = self.lineEdit_cert_path.text()
        cert_pwd = self.lineEdit_cert_pwd.text()
        target_account = self.lineEdit_acc.text()
        
        user_info_dict = {
            'id':fubon_id,
            'pwd':fubon_pwd,
            'cert_path':cert_path,
            'cert_pwd':cert_pwd,
            'target_account':target_account
        }      
    
        accounts = sdk.login(fubon_id, fubon_pwd, Path(cert_path).__str__(), cert_pwd)
        if accounts.is_success:
            for cur_account in accounts.data:
                if cur_account.account == target_account:
                    active_account = cur_account
                    with open('info.pkl', 'wb') as f:
                        pickle.dump(user_info_dict, f)
                    
                    self.main_app = MainApp()
                    self.main_app.show()
                    self.close()
                    
            if active_account == None:
                sdk.logout()
                msg.setWindowTitle("登入失敗")
                msg.setText("找不到您輸入的帳號")
                msg.exec()
        else:
            msg.setWindowTitle("登入失敗")
            msg.setText(accounts.message)
            msg.exec()

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
    add_new_sub_signal = Signal(str, str, float, float, float, bool)
    update_table_row_signal = Signal(str, float, float, float, bool)
    order_qty_update = Signal(str, int)
    filled_qty_update = Signal(str, int)

class MainApp(QWidget):
    def __init__(self):
        super().__init__()

        ### Layout 設定
        my_icon = QIcon()
        my_icon.addFile('fast_icon.png')

        self.setWindowIcon(my_icon)
        self.setWindowTitle("Python搶漲停程式教學範例")
        self.resize(1000, 600)
        
        # 製作上下排列layout上為庫存表，下為log資訊
        layout = QVBoxLayout()
        # 庫存表表頭
        self.table_header = ['股票名稱', '股票代號', '上市櫃', '成交', '買進', '賣出', '漲幅(%)', '委託數量', '成交數量']
        
        self.tablewidget = QTableWidget(0, len(self.table_header))
        self.tablewidget.setHorizontalHeaderLabels([f'{item}' for item in self.table_header])
        self.tablewidget.setEditTriggers(QTableWidget.NoEditTriggers)

        # 整個設定區layout
        layout_condition = QGridLayout()

        # 監控區layout
        label_monitor = QLabel('監控設定')
        layout_condition.addWidget(label_monitor, 0, 0)
        label_up_range = QLabel('漲幅(%)')
        layout_condition.addWidget(label_up_range, 1, 0)
        self.lineEdit_up_range = QLineEdit()
        self.lineEdit_up_range.setText('7')
        layout_condition.addWidget(self.lineEdit_up_range, 1, 1)
        label_up_range_post = QLabel('以上')
        layout_condition.addWidget(label_up_range_post, 1, 2)
        label_freq = QLabel('定時每')
        layout_condition.addWidget(label_freq, 2, 0)
        self.lineEdit_freq = QLineEdit()
        self.lineEdit_freq.setText('5')
        layout_condition.addWidget(self.lineEdit_freq, 2, 1)
        label_freq_post = QLabel('秒更新')
        layout_condition.addWidget(label_freq_post, 2, 2)

        # 交易區layout
        label_trade = QLabel('交易設定')
        layout_condition.addWidget(label_trade, 0, 3)
        label_trade_budget = QLabel('每檔額度')
        layout_condition.addWidget(label_trade_budget, 1, 3)
        self.lineEdit_trade_budget = QLineEdit()
        self.lineEdit_trade_budget.setText('0.1')
        layout_condition.addWidget(self.lineEdit_trade_budget, 1, 4)
        label_trade_budget_post = QLabel('萬元')
        layout_condition.addWidget(label_trade_budget_post, 1, 5)

        # 啟動按鈕
        self.button_start = QPushButton('開始洗價')
        self.button_start.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.button_start.setStyleSheet("QPushButton { font-size: 24px; font-weight: bold; }")
        layout_condition.addWidget(self.button_start, 0, 6, 3, 1)

        # 停止按鈕
        self.button_stop = QPushButton('停止洗價')
        self.button_stop.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.button_stop.setStyleSheet("QPushButton { font-size: 24px; font-weight: bold; }")
        layout_condition.addWidget(self.button_stop, 0, 6, 3, 1)
        self.button_stop.setVisible(False)
        
        # 模擬區Layout設定
        self.button_fake_buy_filled = QPushButton('fake buy filled')
        self.button_show_var = QPushButton('show variable')
        self.button_fake_websocket = QPushButton('fake websocket')
        
        layout_sim = QGridLayout()
        label_sim = QLabel('測試用按鈕')
        label_sim.setStyleSheet("QLabel { font-size: 24px; font-weight: bold; }")
        label_sim.setAlignment(Qt.AlignCenter)
        layout_sim.addWidget(label_sim, 0, 1)
        layout_sim.addWidget(self.button_fake_buy_filled, 1, 0)
        layout_sim.addWidget(self.button_fake_websocket, 1, 1)
        layout_sim.addWidget(self.button_show_var, 1, 2)
        
        # Log區Layout設定
        self.log_text = QPlainTextEdit()
        self.log_text.setReadOnly(True)

        layout.addWidget(self.tablewidget)
        layout.addLayout(layout_condition)
        layout.addLayout(layout_sim)
        layout.addWidget(self.log_text)
        self.setLayout(layout)

        ### 建立連線開始跑主要城市
        self.print_log("login success, 現在使用帳號: {}".format(active_account.account))
        self.print_log("現在使用新一代SDK版本: "+fubon_neo.__version__)
        self.print_log("建立行情連線...")
        sdk.init_realtime(Mode.Normal) # 建立行情連線
        self.print_log("行情連線建立OK")
        self.reststock = sdk.marketdata.rest_client.stock
        self.wsstock = sdk.marketdata.websocket_client.stock

        # slot function connect
        self.button_start.clicked.connect(self.on_button_start_clicked)
        self.button_stop.clicked.connect(self.on_button_stop_clicked)
        self.button_show_var.clicked.connect(self.show_var)
        self.button_fake_buy_filled.clicked.connect(self.fake_buy_filled)
        self.button_fake_websocket.clicked.connect(self.fake_ws_data)

        # communicator init and slot function connect
        self.communicator = Communicate()
        self.communicator.print_log_signal.connect(self.print_log)
        self.communicator.add_new_sub_signal.connect(self.add_new_subscribed)
        self.communicator.update_table_row_signal.connect(self.update_table_row)
        self.communicator.order_qty_update.connect(self.update_order_qty_item)
        self.communicator.filled_qty_update.connect(self.update_filled_qty_item)

        # 各參數初始化
        self.snapshot_timer = None
        self.fake_ws_timer = None
        self.watch_percent = float(self.lineEdit_up_range.text())
        self.snapshot_freq = int(self.lineEdit_freq.text())
        self.trade_budget = float(self.lineEdit_trade_budget.text())

        open_time = datetime.today().replace(hour=9, minute=0, second=0, microsecond=0)
        self.open_unix = int(datetime.timestamp(open_time)*1000000)
        self.last_close_dict = {}
        self.subscribed_ids = {}
        self.is_ordered = {}
        self.order_tag = 'rlu'
        self.fake_price_cnt=0

        self.epsilon = 0.0000001
        self.row_idx_map = {}
        self.col_idx_map = dict(zip(self.table_header, range(len(self.table_header))))
    
    # 測試用假裝有websocket data的按鈕slot function
    def fake_ws_data(self):
        if self.fake_price_cnt % 2==0:
            self.price_interval = 0
            self.fake_ws_timer = RepeatTimer(1, self.fake_message, args=(list(self.row_idx_map.keys())[0], ))
            self.fake_ws_timer.start()
        else:
            self.fake_ws_timer.cancel()

        self.fake_price_cnt+=1

    def fake_message(self, stock_no):
        self.price_interval+=1
        json_template = '''{{"event":"data","data":{{"symbol":"{symbol}","type":"EQUITY","exchange":"TWSE","market":"TSE","price":{price},"size":713,"bid":16.67,"ask":{price}, "isLimitUpAsk":true, "volume":8066,"isClose":true,"time":1718343000000000,"serial":9475857}},"id":"w4mkzAqYAYFKyEBLyEjmHEoNADpwKjUJmqg02G3OC9YmV","channel":"trades"}}'''
        json_price = 15+self.price_interval
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
        new_fake_buy.account = active_account.account
        new_fake_buy.user_def = self.order_tag
        self.on_filled(None, new_fake_buy)

    def show_var(self):
        num = 40
        print('-'*num)
        print('row index', self.row_idx_map)
        print('-'*num)
        print('col index', self.col_idx_map)
        print('-'*num)
        print('subscribed ids', self.subscribed_ids)
        print('-'*num)
        print('is_ordered ids', self.is_ordered)
        print('-'*num)

    def update_filled_qty_item(self, symbol, filled_qty):
        pre_filled_qty = self.tablewidget.item(self.row_idx_map[symbol], self.col_idx_map['成交數量']).text()
        pre_filled_qty = int(pre_filled_qty)
        self.tablewidget.item(self.row_idx_map[symbol], self.col_idx_map['成交數量']).setText(str(filled_qty+pre_filled_qty))

    def update_order_qty_item(self, symbol, order_qty):
        self.tablewidget.item(self.row_idx_map[symbol], self.col_idx_map['委託數量']).setText(str(order_qty))

    def update_table_row(self, symbol, price, bid, ask, is_limit_up):
        self.tablewidget.item(self.row_idx_map[symbol], self.col_idx_map['成交']).setText(str(round(price+self.epsilon, 2)))
        if bid > 0:
            self.tablewidget.item(self.row_idx_map[symbol], self.col_idx_map['買進']).setText(str(round(bid+self.epsilon, 2)))
        elif bid == 0:
            self.tablewidget.item(self.row_idx_map[symbol], self.col_idx_map['買進']).setText('市價')
        elif bid == -1:
            self.tablewidget.item(self.row_idx_map[symbol], self.col_idx_map['買進']).setText('-')

        if ask > 0:
            self.tablewidget.item(self.row_idx_map[symbol], self.col_idx_map['賣出']).setText(str(round(ask+self.epsilon, 2)))
        elif ask == 0:
            self.tablewidget.item(self.row_idx_map[symbol], self.col_idx_map['賣出']).setText('市價')
        elif ask == -1:
            self.tablewidget.item(self.row_idx_map[symbol], self.col_idx_map['賣出']).setText('-')
        
        

        if price:
            up_range = (price-self.last_close_dict[symbol])/self.last_close_dict[symbol]*100
            self.tablewidget.item(self.row_idx_map[symbol], self.col_idx_map['漲幅(%)']).setText(str(round(up_range+self.epsilon, 2))+'%')
        else:
            self.tablewidget.item(self.row_idx_map[symbol], self.col_idx_map['賣出']).setText('-')
        
        if is_limit_up:
            self.tablewidget.item(self.row_idx_map[symbol], self.col_idx_map['漲幅(%)']).setBackground(QColor(Qt.red))
            self.tablewidget.item(self.row_idx_map[symbol], self.col_idx_map['漲幅(%)']).setForeground(QColor(Qt.white))
        else:
            self.tablewidget.item(self.row_idx_map[symbol], self.col_idx_map['漲幅(%)']).setBackground(QColor(Qt.transparent))
            self.tablewidget.item(self.row_idx_map[symbol], self.col_idx_map['漲幅(%)']).setForeground(QColor(Qt.black))

    # ['股票名稱', '股票代號', '上市櫃', '成交', '買進', '賣出', '漲幅(%)', '委託數量', '成交數量']
    def add_new_subscribed(self, symbol, tse_otc, price, bid, ask, is_limit_up):
        ticker_res = self.reststock.intraday.ticker(symbol=symbol)
        # self.print_log(ticker_res['name'])
        self.last_close_dict[symbol] = ticker_res['referencePrice']

        row = self.tablewidget.rowCount()
        self.tablewidget.insertRow(row)
        self.row_idx_map[symbol] = row
        
        for j in range(len(self.table_header)):
            if self.table_header[j] == '股票名稱':
                item = QTableWidgetItem(ticker_res['name'])
                self.tablewidget.setItem(row, j, item)
            elif self.table_header[j] == '股票代號':
                item = QTableWidgetItem(ticker_res['symbol'])
                self.tablewidget.setItem(row, j, item)
            elif self.table_header[j] == '上市櫃':
                item = QTableWidgetItem(tse_otc)
                self.tablewidget.setItem(row, j, item)
            elif self.table_header[j] == '成交':
                if price > 0:
                    item = QTableWidgetItem(str(round(price+self.epsilon, 2)))
                    self.tablewidget.setItem(row, j, item)
                else:
                    item = QTableWidgetItem('-')
                    self.tablewidget.setItem(row, j, item)
            elif self.table_header[j] == '買進':
                if bid > 0:
                    item = QTableWidgetItem(str(round(bid+self.epsilon, 2)))
                    self.tablewidget.setItem(row, j, item)
                elif bid == 0:
                    item = QTableWidgetItem('市價')
                    self.tablewidget.setItem(row, j, item)
                elif bid == -1:
                    item = QTableWidgetItem('-')
                    self.tablewidget.setItem(row, j, item)
            elif self.table_header[j] == '賣出':
                if ask>0:
                    item = QTableWidgetItem(str(round(ask+self.epsilon, 2)))
                    self.tablewidget.setItem(row, j, item)
                elif ask == 0:
                    item = QTableWidgetItem('市價')
                    self.tablewidget.setItem(row, j, item)
                elif ask == -1:
                    item = QTableWidgetItem('-')
                    self.tablewidget.setItem(row, j, item)
            elif self.table_header[j] == '漲幅(%)':
                if price > 0:
                    up_range = (price-ticker_res['referencePrice'])/ticker_res['referencePrice']*100
                    item = QTableWidgetItem(str(round(up_range+self.epsilon, 2))+'%')
                else:
                    item = QTableWidgetItem('-')

                if is_limit_up:
                    item.setBackground(QColor(Qt.red))
                    item.setForeground(QColor(Qt.white))
                else:
                    item.setBackground(QColor(Qt.transparent))
                    item.setForeground(QColor(Qt.black))
                self.tablewidget.setItem(row, j, item)
            elif self.table_header[j] == '委託數量':
                item = QTableWidgetItem('0')
                self.tablewidget.setItem(row, j, item)
            elif self.table_header[j] == '成交數量':
                item = QTableWidgetItem('0')
                self.tablewidget.setItem(row, j, item)

    def buy_market_order(self, symbol, buy_qty, tag='rlu'):
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

        order_res = sdk.stock.place_order(active_account, order)
        return order_res

    def handle_message(self, message):
        msg = json.loads(message)
        event = msg["event"]
        data = msg["data"]
        # print(event, data)

         # subscribed事件處理
        if event == "subscribed":
            if type(data) == list:
                for subscribed_item in data:
                    id = subscribed_item["id"]
                    symbol = subscribed_item["symbol"]
                    self.communicator.print_log_signal.emit('訂閱成功...'+symbol)
                    self.subscribed_ids[symbol] = id
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
            print(event, data)
            is_limit_up = False
            if 'isLimitUpPrice' in data:
                is_limit_up = True

            if 'ask' not in data:
                data['ask'] = -1
            if 'bid' not in data:
                data['bid'] = -1
            if 'price' not in data:
                data['price'] = -1

            self.communicator.add_new_sub_signal.emit(data['symbol'], data['market'], data['price'], data['bid'], data['ask'], is_limit_up)

        elif event == "data":
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
            
            print(event, data)
            self.communicator.update_table_row_signal.emit(data['symbol'], data['price'], data['bid'], data['ask'], is_limit_up)
            
            if ('isLimitUpPrice' in data) and (data['symbol'] not in self.is_ordered):
                if data['isLimitUpPrice']:
                    self.communicator.print_log_signal.emit(data['symbol']+'...送出市價單')
                    if 'price' in data:
                        buy_qty = self.trade_budget//(data['price']*1000)*1000
                        
                    if buy_qty <= 0:
                        self.communicator.print_log_signal.emit(data['symbol']+'...額度不足購買1張')
                    else:
                        self.communicator.print_log_signal.emit(data['symbol']+'...委託'+str(buy_qty)+'股')
                        order_res = self.buy_market_order(data['symbol'], buy_qty, self.order_tag)
                        if order_res.is_success:
                            self.communicator.print_log_signal.emit(data['symbol']+"...市價單發送成功，單號: "+order_res.data.order_no)
                            self.is_ordered[data['symbol']] = buy_qty
                            self.communicator.order_qty_update.emit(data['symbol'], buy_qty)
                        else:
                            self.communicator.print_log_signal.emit(data['symbol']+"...市價單發送失敗...")
                            self.communicator.print_log_signal.emit(order_res.message)

    def handle_connect(self):
        self.communicator.print_log_signal.emit('market data connected')
    
    def handle_disconnect(self, code, message):
        if not code and not message:
            self.communicator.print_log_signal.emit(f'WebSocket已停止')
        else:
            self.communicator.print_log_signal.emit(f'market data disconnect: {code}, {message}')
    
    def handle_error(self, error):
        self.communicator.print_log_signal.emit(f'market data error: {error}')

    def snapshot_n_subscribe(self):
        self.communicator.print_log_signal.emit("snapshoting...")
        TSE_movers = self.reststock.snapshot.movers(market='TSE', type='COMMONSTOCK', direction='up', change='percent', gte=self.watch_percent)
        TSE_movers_df = pd.DataFrame(TSE_movers['data'])
        OTC_movers = self.reststock.snapshot.movers(market='OTC', type='COMMONSTOCK', direction='up', change='percent', gte=self.watch_percent)
        OTC_movers_df = pd.DataFrame(OTC_movers['data'])

        all_movers_df = pd.concat([TSE_movers_df, OTC_movers_df])
        all_movers_df = all_movers_df[all_movers_df['lastUpdated']>self.open_unix]
        
        # all_movers_df['last_close'] = all_movers_df['closePrice']-all_movers_df['change']
        # self.last_close_dict.update(dict(zip(all_movers_df['symbol'], all_movers_df['last_close'])))

        new_subscribe = list(all_movers_df['symbol'])
        new_subscribe = list(set(new_subscribe).difference(set(self.subscribed_ids.keys())))
        self.communicator.print_log_signal.emit("NEW UP SYMBOL: "+str(new_subscribe))

        if new_subscribe:
            self.wsstock.subscribe({
                'channel': 'trades',
                'symbols': new_subscribe
            })

    def on_button_start_clicked(self):

        try:
            self.watch_percent = float(self.lineEdit_up_range.text())
            if self.watch_percent > 10 or self.watch_percent < 5:
                self.print_log("請輸入正確的監控漲幅(%), 範圍5~10")
                return
        except Exception as e:
            self.print_log("請輸入正確的監控漲幅(%), "+str(e))
            return

        try:
            self.snapshot_freq = int(self.lineEdit_freq.text())
            if self.snapshot_freq < 1:
                self.print_log("請輸入正確的監控頻率(整數，最低1秒)")
                return
        except Exception as e:
            self.print_log("請輸入正確的監控頻率(整數，最低1秒), "+str(e))
            return
        
        try:
            self.trade_budget = float(self.lineEdit_trade_budget.text())
            if self.trade_budget<0:
                self.print_log("請輸入正確的每檔買入額度(萬元), 必須大於0")
                return
            else:
                self.trade_budget = self.trade_budget*10000
        except Exception as e:
            self.print_log("請輸入正確的每檔買入額度(萬元), "+str(e))
            return
        
        self.print_log("開始執行監控")
        self.lineEdit_up_range.setReadOnly(True)
        self.lineEdit_freq.setReadOnly(True)
        self.lineEdit_trade_budget.setReadOnly(True)
        self.button_start.setVisible(False)
        self.button_stop.setVisible(True)
        self.tablewidget.clearContents()
        self.tablewidget.setRowCount(0)

        # 重啟時需重設之參數
        self.row_idx_map = {}
        self.subscribed_ids = {}

        sdk.init_realtime(Mode.Normal)
        self.wsstock = sdk.marketdata.websocket_client.stock
        self.wsstock.on('message', self.handle_message)
        self.wsstock.on('connect', self.handle_connect)
        self.wsstock.on('disconnect', self.handle_disconnect)
        self.wsstock.on('error', self.handle_error)
        self.wsstock.connect()

        sdk.set_on_filled(self.on_filled)

        self.snapshot_n_subscribe()
        self.snapshot_timer = RepeatTimer(self.snapshot_freq, self.snapshot_n_subscribe)
        self.snapshot_timer.start()

    def on_button_stop_clicked(self):
        self.print_log("停止執行監控")
        self.lineEdit_up_range.setReadOnly(False)
        self.lineEdit_freq.setReadOnly(False)
        self.lineEdit_trade_budget.setReadOnly(False)
        self.button_stop.setVisible(False)
        self.button_start.setVisible(True)

        self.wsstock.disconnect()

        try:
            if self.snapshot_timer.is_alive():
                self.snapshot_timer.cancel()
        except AttributeError:
            print("no snapshot timer exist")
        
        try:
            if self.fake_ws_timer.is_alive():
                self.fake_ws_timer.cancel()
        except AttributeError:
            print("no fake ws timer exist")


    def on_filled(self, err, content):
        if err:
            print("Filled Error:", err, "Content:", content)
            return
        
        if content.account == active_account.account:
            if content.user_def == self.order_tag:
                self.communicator.filled_qty_update.emit(content.stock_no, content.filled_qty)
                self.communicator.print_log_signal.emit(content.stock_no+'...成功成交'+str(content.filled_qty)+'股, '+'成交價:'+str(content.filled_price))

    # 更新最新log到QPlainTextEdit的slot function
    def print_log(self, log_info):
        self.log_text.appendPlainText(log_info)
        self.log_text.moveCursor(QTextCursor.End)
    
    # 視窗關閉時要做的事，主要是關websocket連結
    def closeEvent(self, event):
        # do stuff
        self.print_log("disconnect websocket...")
        self.wsstock.disconnect()
        try:
            if self.snapshot_timer.is_alive():
                self.snapshot_timer.cancel()
        except AttributeError:
            print("no snapshot timer exist")
        
        try:
            if self.fake_ws_timer.is_alive():
                self.fake_ws_timer.cancel()
        except AttributeError:
            print("no fake ws timer exist")
        
        sdk.logout()
        can_exit = True
        if can_exit:
            event.accept() # let the window close
        else:
            event.ignore()


try:
    sdk = FubonSDK()
except ValueError:
    raise ValueError("請確認網路連線")
active_account = None
 
if not QApplication.instance():
    app = QApplication(sys.argv)
else:
    app = QApplication.instance()
app.setStyleSheet("QWidget{font-size: 12pt;}")
form = LoginForm()
form.show()
 
sys.exit(app.exec())