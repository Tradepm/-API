from login_gui import LoginForm

import sys
import json
import math
from fubon_neo.sdk import FubonSDK, Mode, Order
from fubon_neo.constant import TimeInForce, OrderType, PriceType, MarketType, BSAction
import pandas as pd
from pathlib import Path
import pickle

from PySide6.QtWidgets import QTableWidgetItem, QFileDialog, QApplication, QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QGridLayout, QLabel, QLineEdit, QPushButton, QSizePolicy, QPlainTextEdit
from PySide6.QtGui import QIcon, QTextCursor
from PySide6.QtCore import Qt, Signal, QObject

# 仿FilledData的物件
class fake_filled_data():
    date="2023/09/15"
    branch_no="6460"
    account="9809789"
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
    new_table_item_update_signal = Signal(int, int, str)
    cur_table_item_update_signal = Signal(int, int, str)
    buy_exe_update_signal = Signal(str)
    sell_exe_update_signal = Signal(str)
    pnl_exe_update_signal = Signal(str)
    

class MainApp(QWidget):
    def __init__(self, active_account):
        super().__init__()

        self.active_account = active_account

        my_icon = QIcon()
        my_icon.addFile('fraction.png') 
        self.setWindowIcon(my_icon)
        self.setWindowTitle("Python零股滿額配置小幫手(教學範例)")
        self.resize(1200, 700)

        # 製作上下排列layout上為庫存表，下為log資訊
        layout = QVBoxLayout()

        layout_title = QHBoxLayout()
        cur_pos_title = QLabel('現在持有部位')
        cur_pos_title.setStyleSheet("QLabel { font-size: 24px; font-weight: bold; }")

        new_pos_title = QLabel('目標持有部位')
        new_pos_title.setStyleSheet("QLabel { font-size: 24px; font-weight: bold; }")

        layout_title.addWidget(cur_pos_title, stretch=6)
        layout_title.addWidget(new_pos_title, stretch=4)

        layout_table = QHBoxLayout()
        # 庫存表表頭
        self.cur_pos_header = ['股票名稱', '股票代號', '庫存股數', '庫存均價', '現價', '損益試算', '獲利率%', '委託數量', '委託價格', '成交數量', '成交價格']
        self.new_pos_header = ['股票名稱', '股票代號', '現價', '目標股數', '委託數量', '委託價格', '成交數量', '成交價格']
        
        self.cur_pos_table = QTableWidget(0, len(self.cur_pos_header))
        self.cur_pos_table.setHorizontalHeaderLabels([f'{item}' for item in self.cur_pos_header])

        self.new_pos_table = QTableWidget(0, len(self.new_pos_header))
        self.new_pos_table.setHorizontalHeaderLabels([f'{item}' for item in self.new_pos_header])

        layout_table.addWidget(self.cur_pos_table, stretch=6)
        layout_table.addWidget(self.new_pos_table, stretch=4)
        
        # 整個設定區layout
        layout_parameter = QGridLayout()

        # 參數設置區layout設定
        label_input_title = QLabel('配置參數設定')
        label_input_title.setStyleSheet("QLabel { font-size: 24px; font-weight: bold; }")
        label_input_title.setAlignment(Qt.AlignCenter)
        layout_parameter.addWidget(label_input_title, 0, 0)

        label_total_amount = QLabel('配置總金額:')
        layout_parameter.addWidget(label_total_amount, 1, 0)
        label_total_amount.setAlignment(Qt.AlignRight)
        self.lineEdit_default_total_amount = QLineEdit()
        self.lineEdit_default_total_amount.setText('10')
        layout_parameter.addWidget(self.lineEdit_default_total_amount, 1, 1)
        label_total_amount_post = QLabel('萬元, ')
        layout_parameter.addWidget(label_total_amount_post, 1, 2)

        label_file_path = QLabel('目標清單路徑:')
        layout_parameter.addWidget(label_file_path, 0, 3)
        self.lineEdit_default_file_path = QLineEdit()
        layout_parameter.addWidget(self.lineEdit_default_file_path, 0, 4, 1, 4)
        self.folder_btn = QPushButton('')
        self.folder_btn.setIcon(QIcon('folder.png'))
        layout_parameter.addWidget(self.folder_btn, 0, 8)

        self.read_csv_btn = QPushButton('')
        self.read_csv_btn.setText('讀取清單')
        self.read_csv_btn.setStyleSheet("QPushButton { font-weight: bold; }")
        layout_parameter.addWidget(self.read_csv_btn, 0, 9)

        self.simulate_cal_btn = QPushButton('')
        self.simulate_cal_btn.setText('下單試算')
        self.simulate_cal_btn.setStyleSheet("QPushButton { font-weight: bold; }")
        layout_parameter.addWidget(self.simulate_cal_btn, 0, 10)

        label_est_buy = QLabel('預估買進金額:')
        layout_parameter.addWidget(label_est_buy, 1, 3)
        self.lineEdit_default_est_buy = QLineEdit('0')
        self.lineEdit_default_est_buy.setReadOnly(True)
        layout_parameter.addWidget(self.lineEdit_default_est_buy, 1, 4)
        label_est_buy_post = QLabel('元')
        layout_parameter.addWidget(label_est_buy_post, 1, 5)

        label_est_sell = QLabel('預估賣出金額:')
        layout_parameter.addWidget(label_est_sell, 2, 3)
        self.lineEdit_default_est_sell = QLineEdit('0')
        self.lineEdit_default_est_sell.setReadOnly(True)
        layout_parameter.addWidget(self.lineEdit_default_est_sell, 2, 4)
        label_est_sell_post = QLabel('元')
        layout_parameter.addWidget(label_est_sell_post, 2, 5)

        label_est_pnl = QLabel('預估賣出損益:')
        layout_parameter.addWidget(label_est_pnl, 3, 3)
        self.lineEdit_default_est_pnl = QLineEdit('0')
        self.lineEdit_default_est_pnl.setReadOnly(True)
        layout_parameter.addWidget(self.lineEdit_default_est_pnl, 3, 4)
        label_est_pnl_post = QLabel('元')
        layout_parameter.addWidget(label_est_pnl_post, 3, 5)

        label_exe_buy = QLabel('執行買進金額:')
        layout_parameter.addWidget(label_exe_buy, 1, 6)
        self.lineEdit_default_exe_buy = QLineEdit('0')
        self.lineEdit_default_exe_buy.setReadOnly(True)
        layout_parameter.addWidget(self.lineEdit_default_exe_buy, 1, 7)
        label_exe_buy_post = QLabel('元')
        layout_parameter.addWidget(label_exe_buy_post, 1, 8)

        label_exe_sell = QLabel('執行賣出金額:')
        layout_parameter.addWidget(label_exe_sell, 2, 6)
        self.lineEdit_default_exe_sell = QLineEdit('0')
        self.lineEdit_default_exe_sell.setReadOnly(True)
        layout_parameter.addWidget(self.lineEdit_default_exe_sell, 2, 7)
        label_exe_sell_post = QLabel('元')
        layout_parameter.addWidget(label_exe_sell_post, 2, 8)

        label_exe_pnl = QLabel('執行賣出損益:')
        layout_parameter.addWidget(label_exe_pnl, 3, 6)
        self.lineEdit_default_exe_pnl = QLineEdit('0')
        self.lineEdit_default_exe_pnl.setReadOnly(True)
        layout_parameter.addWidget(self.lineEdit_default_exe_pnl, 3, 7)
        label_exe_pnl_post = QLabel('元')
        layout_parameter.addWidget(label_exe_pnl_post, 3, 8)

        # 啟動按鈕
        self.button_start = QPushButton('開始下單')
        self.button_start.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.button_start.setStyleSheet("QPushButton { font-size: 24px; font-weight: bold; }")
        layout_parameter.addWidget(self.button_start, 1, 9, 3, 2)

        # 模擬區layout設定
        self.button_fake_buy_filled = QPushButton('fake buy filled')
        self.button_fake_sell_filled = QPushButton('fake sell filled')
        self.button_fake_websocket = QPushButton('fake websocket')

        layout_sim = QGridLayout()
        label_sim = QLabel('測試用按鈕')
        label_sim.setStyleSheet("QLabel { font-size: 24px; font-weight: bold; }")
        label_sim.setAlignment(Qt.AlignCenter)
        layout_sim.addWidget(label_sim, 0, 1)
        layout_sim.addWidget(self.button_fake_buy_filled, 1, 0)
        layout_sim.addWidget(self.button_fake_sell_filled, 1, 1)
        layout_sim.addWidget(self.button_fake_websocket, 1, 2)
        
        self.log_text = QPlainTextEdit()
        self.log_text.setReadOnly(True)

        layout.addLayout(layout_title)
        layout.addLayout(layout_table)
        layout.addLayout(layout_parameter)
        layout.addLayout(layout_sim)
        layout.addWidget(self.log_text)

        layout.setStretchFactor(layout_table, 1)
        layout.setStretchFactor(layout_table, 7)
        layout.setStretchFactor(layout_parameter, 1)
        layout.setStretchFactor(layout_sim, 1)
        layout.setStretchFactor(self.log_text, 3)

        self.setLayout(layout)

        my_target_path = None
        my_target_list_file = Path("./target_list_path.pkl")
        if my_target_list_file.is_file():
            with open('./target_list_path.pkl', 'rb') as f:
                temp_dict = pickle.load(f)
                my_target_path = temp_dict['target_list_path']

        # Open the file dialog to select a file
        if my_target_path:
            self.lineEdit_default_file_path.setText(my_target_path)

        self.print_log("login success, 現在使用帳號: {}".format(self.active_account.account))
        self.print_log("建立行情連線...")

        sdk.init_realtime(Mode.Normal) # 建立買進行情連線
        self.reststock = sdk.marketdata.rest_client.stock
        self.buy_websocket = sdk.marketdata.websocket_client.stock

        sdk.init_realtime(Mode.Normal) # 建立賣出行情連線
        self.sell_websocket = sdk.marketdata.websocket_client.stock

        # table slot connect

        # button slot connect
        self.folder_btn.clicked.connect(self.showDialog)
        self.read_csv_btn.clicked.connect(self.read_target_list)
        self.simulate_cal_btn.clicked.connect(self.order_trial_calculate)
        self.button_start.clicked.connect(self.order_start)
        self.button_fake_buy_filled.clicked.connect(self.fake_buy_filled)
        self.button_fake_sell_filled.clicked.connect(self.fake_sell_filled)

        # signal slot connect
        self.communicator = Communicate()
        self.communicator.print_log_signal.connect(self.print_log)
        self.communicator.new_table_item_update_signal.connect(self.new_table_item_update)
        self.communicator.cur_table_item_update_signal.connect(self.cur_table_item_update)
        self.communicator.buy_exe_update_signal.connect(self.buy_exe_amount_update)
        self.communicator.sell_exe_update_signal.connect(self.sell_exe_amount_update)
        self.communicator.pnl_exe_update_signal.connect(self.sell_exe_pnl_update)

        # default parameter
        self.buy_h_def = 'sw_hb'
        self.buy_f_def = 'sw_fb'
        self.sell_h_def = 'sw_hs'
        self.sell_f_def = 'sw_fs'
        self.total_budget = 0
        self.single_budget = 0
        self.epsilon = 0.000001
        self.buy_exe_filled_amount = 0
        self.sell_exe_filled_amount = 0
        self.sell_exe_filled_pnl = 0
        self.hold_pos_dict = {}
        my_pos_dict_path = Path("./hold_pos.json")
        if my_pos_dict_path.is_file():
            with open('./hold_pos.json', 'r', encoding='utf8') as infile:
                self.hold_pos_dict = json.load(infile)

        self.new_table_row_idx_map = {}
        self.new_table_col_idx_map = dict(zip(self.new_pos_header, range(len(self.new_pos_header))))
        self.subscribed_buy_ids = {}

        self.cur_table_row_idx_map = {}
        self.cur_table_col_idx_map = dict(zip(self.cur_pos_header, range(len(self.cur_pos_header))))
        self.subscribed_sell_ids = {}

        self.buy_websocket.on("connect", self.handle_buy_connect)
        self.buy_websocket.on("disconnect", self.handle_buy_disconnect)
        self.buy_websocket.on("error", self.handle_buy_error)
        self.buy_websocket.on('message', self.handle_buy_message)
        self.buy_websocket.connect()
        self.print_log("WebSocket連線成功(buy)")

        self.sell_websocket.on("connect", self.handle_sell_connect)
        self.sell_websocket.on("disconnect", self.handle_sell_disconnect)
        self.sell_websocket.on("error", self.handle_sell_error)
        self.sell_websocket.on('message', self.handle_sell_message)
        self.sell_websocket.connect()
        self.print_log("WebSocket連線成功(sell)")

        sdk.set_on_filled(self.on_filled)
        self.cur_pos_table_init()
    
    def buy_exe_amount_update(self, value):
        self.lineEdit_default_exe_buy.setText(value)

    def sell_exe_amount_update(self, value):
        self.lineEdit_default_exe_sell.setText(value)

    def sell_exe_pnl_update(self, value):
        self.lineEdit_default_exe_pnl.setText(value)

    def cur_pos_table_init(self):
        if len(self.hold_pos_dict) == 0:
            return

        for key, value in self.hold_pos_dict.items():
            symbol = key
            ticker_res = self.reststock.intraday.ticker(symbol=symbol)
            stock_name = value['stock_name']

            # print(symbol, stock_name)
            row = self.cur_pos_table.rowCount()
            self.cur_pos_table.insertRow(row)

            # self.cur_pos_header = ['股票名稱', '股票代號', '庫存股數', '庫存均價', '現價', '損益試算', '獲利率%', '委託數量', '委託價格', '成交數量', '成交價格']           
            for j in range(len(self.cur_pos_header)):
                item = QTableWidgetItem()
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                if self.cur_pos_header[j] == '股票名稱':
                    item.setText(stock_name)
                    self.cur_pos_table.setItem(row, j, item)
                elif self.cur_pos_header[j] == '股票代號':
                    item.setText(symbol)
                    self.cur_pos_table.setItem(row, j, item)
                elif self.cur_pos_header[j] == '庫存股數':
                    item.setText(str(value['hold_qty']))
                    self.cur_pos_table.setItem(row, j, item)
                elif self.cur_pos_header[j] == '庫存均價':
                    item.setText(str(value['avg_price']))
                    self.cur_pos_table.setItem(row, j, item)
                elif self.cur_pos_header[j] == '現價':
                    item.setText('-')
                    self.cur_pos_table.setItem(row, j, item)
                elif self.cur_pos_header[j] == '損益試算':
                    item.setText('-')
                    self.cur_pos_table.setItem(row, j, item)
                elif self.cur_pos_header[j] == '獲利率%':
                    item.setText('-')
                    self.cur_pos_table.setItem(row, j, item)
                elif self.cur_pos_header[j] == '委託數量':
                    item.setText('-')
                    self.cur_pos_table.setItem(row, j, item)
                elif self.cur_pos_header[j] == '委託價格':
                    item.setText(str(ticker_res['limitDownPrice']))
                    item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEditable | Qt.ItemIsEnabled)
                    self.cur_pos_table.setItem(row, j, item)
                elif self.cur_pos_header[j] == '成交數量':
                    item.setText('-')
                    self.cur_pos_table.setItem(row, j, item)
                elif self.cur_pos_header[j] == '成交價格':
                    item.setText('-')
                    self.cur_pos_table.setItem(row, j, item)

            self.cur_table_row_idx_map[symbol] = row

            if symbol not in self.subscribed_sell_ids:
                self.sell_websocket.subscribe({
                    'channel': 'trades',
                    'symbol': symbol
                })

    def fake_sell_filled(self):
        for i in range(0, self.cur_pos_table.rowCount()):
            symbol = self.cur_pos_table.item(i, self.cur_table_col_idx_map['股票代號']).text()
            sell_order_qty = self.cur_pos_table.item(i, self.cur_table_col_idx_map['委託數量']).text()
            sell_order_price = self.cur_pos_table.item(i, self.cur_table_col_idx_map['委託價格']).text()

            print('send sell filled', sell_order_qty)

            if int(sell_order_qty) > 0:
                sell_h_qty = int(sell_order_qty)//1000*1000
                sell_f_qty = int(sell_order_qty)%1000
                if sell_h_qty>0:
                    sell_filled = fake_filled_data()
                    sell_filled.stock_no = symbol
                    sell_filled.sell_sell = BSAction.Sell
                    sell_filled.filled_qty = int(sell_h_qty)
                    sell_filled.filled_price = float(sell_order_price)
                    sell_filled.filled_avg_price = float(sell_order_price)
                    sell_filled.user_def = self.sell_h_def
                    self.on_filled(None, sell_filled)
                if sell_f_qty>0:
                    sell_filled = fake_filled_data()
                    sell_filled.stock_no = symbol
                    sell_filled.sell_sell = BSAction.Sell
                    sell_filled.filled_qty = int(sell_f_qty)
                    sell_filled.filled_price = float(sell_order_price)
                    sell_filled.filled_avg_price = float(sell_order_price)
                    sell_filled.user_def = self.sell_f_def
                    self.on_filled(None, sell_filled)

    def fake_buy_filled(self):
        for i in range(0, self.new_pos_table.rowCount()):
            symbol = self.new_pos_table.item(i, self.new_table_col_idx_map['股票代號']).text()
            buy_order_qty = self.new_pos_table.item(i, self.new_table_col_idx_map['委託數量']).text()
            buy_order_price = self.new_pos_table.item(i, self.new_table_col_idx_map['委託價格']).text()

            if int(buy_order_qty) > 0:
                buy_h_qty = int(buy_order_qty)//1000*1000
                buy_f_qty = int(buy_order_qty)%1000
                if buy_h_qty>0:
                    buy_filled = fake_filled_data()
                    buy_filled.stock_no = symbol
                    buy_filled.buy_sell = BSAction.Buy
                    buy_filled.filled_qty = int(buy_h_qty)
                    buy_filled.filled_price = float(buy_order_price)
                    buy_filled.filled_avg_price = float(buy_order_price)
                    buy_filled.user_def = self.buy_h_def
                    self.on_filled(None, buy_filled)
                if buy_f_qty>0:
                    buy_filled = fake_filled_data()
                    buy_filled.stock_no = symbol
                    buy_filled.buy_sell = BSAction.Buy
                    buy_filled.filled_qty = int(buy_f_qty)
                    buy_filled.filled_price = float(buy_order_price)
                    buy_filled.filled_avg_price = float(buy_order_price)
                    buy_filled.user_def = self.buy_f_def
                    self.on_filled(None, buy_filled)

    # 主動回報，根據成交數據維護GUI表格及cur_host_table
    def on_filled(self, err, content):
        print("hold pos:", self.hold_pos_dict)
        print('filled recived:', content.stock_no, content.buy_sell)
        print('content:', content)
        if content.account == self.active_account.account:
            if content.user_def == self.buy_h_def or content.user_def == self.buy_f_def:
                row = self.new_table_row_idx_map[content.stock_no]
                cur_filled_qty = self.new_pos_table.item(row, self.new_table_col_idx_map['成交數量']).text()
                new_filled_qty = content.filled_qty
                update_qty = 0
                avg_filled_price = content.filled_avg_price
                cur_filled_price = content.filled_price
                self.buy_exe_filled_amount += int(round((content.filled_qty*content.filled_price),0))

                if cur_filled_qty != '-':
                    if int(cur_filled_qty) > 0:
                        update_qty = int(cur_filled_qty)+new_filled_qty
                else:
                    update_qty = new_filled_qty
                
                stock_name = self.new_pos_table.item(row, self.new_table_col_idx_map['股票名稱']).text()
                if content.stock_no in self.hold_pos_dict:
                    pos_record = self.hold_pos_dict[content.stock_no]
                    pos_record['avg_price'] = ((pos_record['avg_price']*pos_record['hold_qty'])+(cur_filled_price*new_filled_qty))/(pos_record['hold_qty']+new_filled_qty)
                    pos_record['avg_price'] = round(pos_record['avg_price']+self.epsilon, 2)
                    pos_record['hold_qty'] = pos_record['hold_qty']+new_filled_qty
                    self.hold_pos_dict[content.stock_no] = pos_record
                else:
                    pos_record = {'stock_name': stock_name, 'hold_qty': new_filled_qty, 'avg_price': avg_filled_price}
                    self.hold_pos_dict[content.stock_no] = pos_record

                self.communicator.new_table_item_update_signal.emit(row, self.new_table_col_idx_map['成交數量'], str(update_qty))
                self.communicator.new_table_item_update_signal.emit(row, self.new_table_col_idx_map['成交價格'], str(avg_filled_price))
                self.communicator.buy_exe_update_signal.emit(str(self.buy_exe_filled_amount))
                print(self.hold_pos_dict)
            elif content.user_def == self.sell_h_def or content.user_def == self.sell_f_def:
                row = self.cur_table_row_idx_map[content.stock_no]
                cur_filled_qty = self.cur_pos_table.item(row, self.cur_table_col_idx_map['成交數量']).text()
                update_qty = 0
                new_filled_qty = content.filled_qty
                avg_filled_price = content.filled_avg_price
                self.sell_exe_filled_amount += int(round((content.filled_qty*content.filled_price),0))
                avg_pos_price = float(self.cur_pos_table.item(row, self.cur_table_col_idx_map['庫存均價']).text())
                self.sell_exe_filled_pnl += int(round((content.filled_qty * (content.filled_price-avg_pos_price)), 0))

                if cur_filled_qty != '-':
                    if int(cur_filled_qty) > 0:
                        update_qty = int(cur_filled_qty)+new_filled_qty
                else:
                    update_qty = new_filled_qty
                
                stock_name = self.cur_pos_table.item(row, self.cur_table_col_idx_map['股票名稱']).text()
                if content.stock_no in self.hold_pos_dict:
                    pos_record = self.hold_pos_dict[content.stock_no]
                    pos_record['hold_qty'] = pos_record['hold_qty'] - new_filled_qty
                    if pos_record['hold_qty'] > 0:
                        self.hold_pos_dict[content.stock_no] = pos_record
                    else:
                        self.hold_pos_dict.pop(content.stock_no)
                else:
                    pass

                self.communicator.cur_table_item_update_signal.emit(row, self.cur_table_col_idx_map['成交數量'], str(update_qty))
                self.communicator.cur_table_item_update_signal.emit(row, self.cur_table_col_idx_map['成交價格'], str(avg_filled_price))
                self.communicator.sell_exe_update_signal.emit(str(self.sell_exe_filled_amount))
                self.communicator.pnl_exe_update_signal.emit(str(self.sell_exe_filled_pnl))
                print(self.hold_pos_dict)
    
    def sell_limit_order(self, stock_symbol, order_price, sell_qty, swing_bs='sw_hs'):
        order = Order(
            buy_sell = BSAction.Sell,
            symbol = stock_symbol,
            price =  str(order_price),
            quantity = int(sell_qty),
            market_type = MarketType.Common,
            price_type = PriceType.Limit,
            time_in_force = TimeInForce.ROD,
            order_type = OrderType.Stock,
            user_def = swing_bs # optional field
        )

        order_res = sdk.stock.place_order(self.active_account, order)
        return order_res
    
    def sell_fraction_limit_order(self, stock_symbol, order_price, sell_qty, swing_bs='sw_fs'):
        order = Order(
            buy_sell = BSAction.Sell,
            symbol = stock_symbol,
            price =  str(order_price),
            quantity = int(sell_qty),
            market_type = MarketType.IntradayOdd,
            price_type = PriceType.Limit,
            time_in_force = TimeInForce.ROD,
            order_type = OrderType.Stock,
            user_def = swing_bs # optional field
        )

        order_res = sdk.stock.place_order(self.active_account, order)
        return order_res

    def buy_limit_order(self, stock_symbol, order_price, buy_qty, swing_bs='sw_hb'):
        order = Order(
            buy_sell = BSAction.Buy,
            symbol = stock_symbol,
            price =  str(order_price),
            quantity = int(buy_qty),
            market_type = MarketType.Common,
            price_type = PriceType.Limit,
            time_in_force = TimeInForce.ROD,
            order_type = OrderType.Stock,
            user_def = swing_bs # optional field
        )

        order_res = sdk.stock.place_order(self.active_account, order)
        return order_res

    def buy_fraction_limit_order(self, stock_symbol, order_price, buy_qty, swing_bs='sw_fb'):
        order = Order(
            buy_sell = BSAction.Buy,
            symbol = stock_symbol,
            price =  str(order_price),
            quantity = int(buy_qty),
            market_type = MarketType.IntradayOdd,
            price_type = PriceType.Limit,
            time_in_force = TimeInForce.ROD,
            order_type = OrderType.Stock,
            user_def = swing_bs # optional field
        )

        order_res = sdk.stock.place_order(self.active_account, order)
        return order_res

    def order_start(self):
        order_start_log = '='*20
        order_start_log += '開始下單'
        order_start_log += '='*20
        self.print_log(order_start_log)
        for i in range(0, self.cur_pos_table.rowCount()):
            symbol = self.cur_pos_table.item(i, self.cur_table_col_idx_map['股票代號']).text()
            sell_order_qty = self.cur_pos_table.item(i, self.cur_table_col_idx_map['委託數量']).text()
            sell_order_price = self.cur_pos_table.item(i, self.cur_table_col_idx_map['委託價格']).text()

            if sell_order_qty != '-':
                sell_h_qty = int(int(sell_order_qty)//1000)*1000
                sell_f_qty = int(sell_order_qty)%1000
                if sell_h_qty > 0:
                    sell_order_res = self.sell_limit_order(symbol, sell_order_price, str(sell_h_qty), self.sell_h_def)
                    if sell_order_res.is_success:
                        self.communicator.print_log_signal.emit(symbol+' 賣出整股委託成功, 委託價格: '+sell_order_price+', 委託數量:'+str(sell_h_qty))
                    else:
                        self.communicator.print_log_signal.emit(symbol+' 賣出整股委託失敗')
                        self.communicator.print_log_signal.emit(sell_order_res.message)
                if sell_f_qty > 0:
                    sell_frac_order_res = self.sell_fraction_limit_order(symbol, sell_order_price, str(sell_f_qty), self.sell_f_def)
                    if sell_frac_order_res.is_success:
                        self.communicator.print_log_signal.emit(symbol+' 賣出零股委託成功, 委託價格: '+sell_order_price+', 委託數量:'+str(sell_f_qty))
                    else:
                        self.communicator.print_log_signal.emit(symbol+' 賣出零股委託失敗')
                        self.communicator.print_log_signal.emit(sell_order_res.message)
            else:
                self.print_log('尚未進行賣單試算')

        for i in range(0, self.new_pos_table.rowCount()):
            symbol = self.new_pos_table.item(i, self.new_table_col_idx_map['股票代號']).text()
            buy_order_qty = self.new_pos_table.item(i, self.new_table_col_idx_map['委託數量']).text()
            buy_order_price = self.new_pos_table.item(i, self.new_table_col_idx_map['委託價格']).text()

            if buy_order_qty != '-':
                buy_h_qty = int(int(buy_order_qty)//1000*1000)
                buy_f_qty = int(buy_order_qty)%1000
                if buy_h_qty > 0:
                    buy_order_res = self.buy_limit_order(symbol, buy_order_price, str(buy_h_qty), self.buy_h_def)
                    if buy_order_res.is_success:
                        self.communicator.print_log_signal.emit(symbol+' 買進整股委託成功, 委託價格: '+buy_order_price+', 委託數量:'+str(buy_h_qty))
                    else:
                        self.communicator.print_log_signal.emit(symbol+' 買進整股委託失敗')
                        self.communicator.print_log_signal.emit(buy_order_res.message)

                if buy_f_qty > 0:
                    buy_frac_order_res = self.buy_fraction_limit_order(symbol, buy_order_price, str(buy_f_qty), self.buy_f_def)
                    if buy_frac_order_res.is_success:
                        self.communicator.print_log_signal.emit(symbol+' 買進零股委託成功, 委託價格: '+buy_order_price+', 委託數量:'+str(buy_f_qty))
                    else:
                        self.communicator.print_log_signal.emit(symbol+' 買進零股委託失敗')
                        self.communicator.print_log_signal.emit(buy_frac_order_res.message)
            else:
                self.print_log('尚未進行買單試算')
        
        self.print_log('下單結束，請等待成交完成或收盤後再關閉')
        self.button_start.setEnabled(False)
        self.button_start.setText('下單結束\n請等待成交')


    def update_est_buy(self):
        est_buy_total = 0
        for i in range(0, self.new_pos_table.rowCount()):
            buy_order_qty = self.new_pos_table.item(i, self.new_table_col_idx_map['委託數量']).text()
            buy_order_price = self.new_pos_table.item(i, self.new_table_col_idx_map['委託價格']).text()

            est_buy_total += math.ceil(float(buy_order_qty)*float(buy_order_price))
        self.lineEdit_default_est_buy.setText(str(est_buy_total))

    # 更新表格內某一格值的slot function
    def cur_table_item_update(self, row, col, value):
        try:
            self.cur_pos_table.item(row, col).setText(value)
            # print(row, col, value)
        except Exception as e:
            print(e, row, col, value)

    # 更新表格內某一格值的slot function
    def new_table_item_update(self, row, col, value):
        try:
            self.new_pos_table.item(row, col).setText(value)
            # print(row, col, value)
        except Exception as e:
            print(e, row, col, value)

    def read_target_list(self):
        print('new table subscribed ids', self.subscribed_buy_ids)
        
        if len(self.subscribed_buy_ids) > 0:
            self.print_log('deleting buy table...')
            for key in list(self.subscribed_buy_ids.keys()):
                print('取消訂閱', self.subscribed_buy_ids[key])
                self.buy_websocket.unsubscribe({'id':self.subscribed_buy_ids[key]})
            while self.subscribed_buy_ids:
                # print('deleting buy target...')
                pass
            self.new_table_row_idx_map = {}
        self.new_pos_table.clearContents()
        self.new_pos_table.setRowCount(0)
        
        buy_target_path = Path(self.lineEdit_default_file_path.text())
        # print(buy_target_path)
        if str(buy_target_path) == '.':
            self.communicator.print_log_signal('請輸入正確檔案路徑')
        else:
            try:
                self.buy_target = pd.read_csv(buy_target_path)
            except UnicodeDecodeError as e:
                print("uff-8 fail, try cp950...", e)
                self.buy_target = pd.read_csv(buy_target_path, encoding='cp950', skiprows=3)
            # print(self.buy_target)

            self.new_pos_table.blockSignals(True)

            for i in range(self.buy_target.shape[0]):
                symbol = self.buy_target.iloc[i, 1].replace('.TW', '')
                ticker_res = self.reststock.intraday.ticker(symbol=symbol)
                stock_name = self.buy_target.iloc[i, 2]

                # print(symbol, stock_name)
                row = self.new_pos_table.rowCount()
                self.new_pos_table.insertRow(row)

                # ['股票名稱', '股票代號', '現價', '委託數量', '委託價格', '成交數量', '成交價格']            
                for j in range(len(self.new_pos_header)):
                    item = QTableWidgetItem()
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                    if self.new_pos_header[j] == '股票名稱':
                        item.setText(stock_name)
                        self.new_pos_table.setItem(row, j, item)
                    elif self.new_pos_header[j] == '股票代號':
                        item.setText(symbol)
                        self.new_pos_table.setItem(row, j, item)
                    elif self.new_pos_header[j] == '現價':
                        item.setText('-')
                        self.new_pos_table.setItem(row, j, item)
                    elif self.new_pos_header[j] == '目標股數':
                        item.setText('-')
                        self.new_pos_table.setItem(row, j, item)
                    elif self.new_pos_header[j] == '委託數量':
                        item.setText('-')
                        self.new_pos_table.setItem(row, j, item)
                    elif self.new_pos_header[j] == '委託價格':
                        item.setText(str(ticker_res['limitUpPrice']))
                        item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEditable | Qt.ItemIsEnabled)
                        self.new_pos_table.setItem(row, j, item)
                    elif self.new_pos_header[j] == '成交數量':
                        item.setText('-')
                        self.new_pos_table.setItem(row, j, item)
                    elif self.new_pos_header[j] == '成交價格':
                        item.setText('-')
                        self.new_pos_table.setItem(row, j, item)

                self.new_table_row_idx_map[symbol] = row

                if symbol not in self.subscribed_buy_ids:
                    self.buy_websocket.subscribe({
                        'channel': 'trades',
                        'symbol': symbol
                    })

            self.new_pos_table.blockSignals(False)
    
    def order_trial_calculate(self):
        self.sell_trial_calculate()
        self.buy_trial_calculate()

    def sell_trial_calculate(self):
        sell_log_str = "="*20
        sell_log_str += "現有部位賣單試算"
        sell_log_str += "="*20
        self.print_log(sell_log_str)
        cur_pos_table_rows = self.cur_pos_table.rowCount()
        new_pos_table_rows = self.new_pos_table.rowCount()

        # print('sell_trial', cur_pos_table_rows)
        if cur_pos_table_rows==0:
            self.communicator.print_log_signal.emit('當前部位清單為空，只執行買入')
            return
        else:
            self.total_budget = float(self.lineEdit_default_total_amount.text())*10000
            if new_pos_table_rows == 0:
                pass
            else:
                self.single_budget = self.total_budget//new_pos_table_rows
            est_sell_total = 0
            est_sell_profit = 0

            for row in range(cur_pos_table_rows):
                symbol = self.cur_pos_table.item(row, self.cur_table_col_idx_map['股票代號']).text()
                order_price = float(self.cur_pos_table.item(row, self.cur_table_col_idx_map['委託價格']).text())
                sell_qty = int(self.cur_pos_table.item(row, self.cur_table_col_idx_map['庫存股數']).text())
                net_sell_qty = sell_qty
                avg_price = float(self.cur_pos_table.item(row, self.cur_table_col_idx_map['庫存均價']).text())

                if symbol in self.new_table_row_idx_map:
                    buy_price = float(self.new_pos_table.item(self.new_table_row_idx_map[symbol], self.new_table_col_idx_map['委託價格']).text())
                    buy_qty = int(self.single_budget//buy_price)
                    net_sell_qty = sell_qty-buy_qty
                    if net_sell_qty>=0:
                        whole_qty = net_sell_qty//1000*1000
                        frac_qty = net_sell_qty%1000
                        self.print_log(symbol+' 配置賣出: '+str(sell_qty)+'，存在目標，減少賣單: '+str(buy_qty)+'，預計賣出: '+str(net_sell_qty)+'，整股: '+str(whole_qty)+'，零股:'+str(frac_qty))
                    else:
                        whole_qty = 0
                        frac_qty = 0
                        self.print_log(symbol+'配置賣出: '+str(sell_qty)+' 存在目標，減少賣單: '+str(buy_qty)+'，預計賣出: 0'+'，整股: '+str(whole_qty)+'，零股:'+str(frac_qty))
                else:
                    self.print_log(symbol+'配置賣出: '+str(sell_qty)+' 非目標，預計賣出: '+str(sell_qty))
                
                if net_sell_qty > 0:
                    self.cur_pos_table.item(row, self.cur_table_col_idx_map['委託數量']).setText(str(int(net_sell_qty)))
                    est_sell_total += math.ceil(net_sell_qty*order_price)
                    est_sell_profit += int(round(net_sell_qty*(order_price-avg_price), 0))
                else:
                    self.cur_pos_table.item(row, self.cur_table_col_idx_map['委託數量']).setText('0')

            self.lineEdit_default_est_sell.setText(str(est_sell_total))
            self.lineEdit_default_est_pnl.setText(str(est_sell_profit))

    def buy_trial_calculate(self):
        buy_log_str = "="*20
        buy_log_str += "目標持有買單試算"
        buy_log_str += "="*20
        self.print_log(buy_log_str)
        new_pos_table_rows = self.new_pos_table.rowCount()
        # print('buy_trial', new_pos_table_rows)
        if new_pos_table_rows==0:
            self.communicator.print_log_signal.emit('目標清單為空，只執行賣出')
            return
        else:
            self.total_budget = float(self.lineEdit_default_total_amount.text())*10000
            self.single_budget = self.total_budget//new_pos_table_rows
            est_buy_total = 0

            for row in range(new_pos_table_rows):
                symbol = self.new_pos_table.item(row, self.new_table_col_idx_map['股票代號']).text()
                order_price = float(self.new_pos_table.item(row, self.new_table_col_idx_map['委託價格']).text())
                order_qty = int(self.single_budget//order_price)
                net_order_qty = order_qty
                whole_qty = order_qty//1000*1000
                frac_qty = order_qty%1000

                if symbol in self.cur_table_row_idx_map:
                    cur_qty = int(self.cur_pos_table.item(self.cur_table_row_idx_map[symbol], self.cur_table_col_idx_map['庫存股數']).text())
                    net_order_qty = order_qty-cur_qty
                    
                    if net_order_qty>=0:
                        whole_qty = net_order_qty//1000*1000
                        frac_qty = net_order_qty%1000
                        self.print_log(symbol+' 目標買入: '+str(order_qty)+' 已存在，減少買單: '+str(cur_qty)+'，預計買入: '+str(net_order_qty)+'，整股:'+str(whole_qty)+'，零股:'+str(frac_qty))
                    else:
                        whole_qty = 0
                        frac_qty = 0
                        self.print_log(symbol+' 目標買入: '+str(order_qty)+' 已存在，減少買單: '+str(cur_qty)+'，預計買入: 0，整股:'+str(whole_qty)+'，零股:'+str(frac_qty))
                else:
                    self.print_log(symbol+' 目標買入: '+str(order_qty)+' 新增部位，預計買入: '+str(order_qty)+'，整股:'+str(whole_qty)+'，零股:'+str(frac_qty))
                
                self.new_pos_table.item(row, self.new_table_col_idx_map['目標股數']).setText(str(int(order_qty)))
                if net_order_qty > 0:
                    self.new_pos_table.item(row, self.new_table_col_idx_map['委託數量']).setText(str(int(net_order_qty)))
                    est_buy_total += math.ceil(net_order_qty*order_price)
                else:
                    self.new_pos_table.item(row, self.new_table_col_idx_map['委託數量']).setText('0')

            self.lineEdit_default_est_buy.setText(str(est_buy_total))

    def handle_sell_message(self, message):
        msg = json.loads(message)
        event = msg["event"]
        data = msg["data"]
        # print(event, data)
        
        # subscribed事件處理
        if event == "subscribed":
            id = data["id"]
            symbol = data["symbol"]
            self.communicator.print_log_signal.emit('訂閱成功...'+symbol)
            self.subscribed_sell_ids[symbol] = id
        
        elif event == "unsubscribed":
            for key, value in self.subscribed_sell_ids.items():
                if value == data["id"]:
                    print(key, value)
                    remove_key = key
            self.subscribed_sell_ids.pop(remove_key)
            self.communicator.print_log_signal.emit(remove_key+"...成功移除訂閱")
        
        elif event == 'snapshot':
            symbol = data['symbol']

            if 'price' in data:
                row = self.cur_table_row_idx_map[symbol]
                cur_price = data['price']
                avg_price = float(self.cur_pos_table.item(row, self.cur_table_col_idx_map['庫存均價']).text())
                hold_qty = int(self.cur_pos_table.item(row, self.cur_table_col_idx_map['庫存股數']).text())

                self.communicator.cur_table_item_update_signal.emit(row, self.cur_table_col_idx_map['現價'], str(cur_price))
                cur_pnl = (cur_price - avg_price)*hold_qty
                cur_percent = cur_pnl/(avg_price*hold_qty)*100
                self.communicator.cur_table_item_update_signal.emit(row, self.cur_table_col_idx_map['損益試算'], str(int(round(cur_pnl, 0))))
                self.communicator.cur_table_item_update_signal.emit(row, self.cur_table_col_idx_map['獲利率%'], str(round(cur_percent, 2))+'%')

        # data事件處理
        elif event == "data":
            if 'isTrial' in data:
                if data['isTrial']:
                    return
            
            symbol = data['symbol']

            if symbol not in self.cur_table_row_idx_map:
                return
            
            if 'price' in data:
                row = self.cur_table_row_idx_map[symbol]
                cur_price = data['price']
                avg_price = float(self.cur_pos_table.item(row, self.cur_table_col_idx_map['庫存均價']).text())
                hold_qty = int(self.cur_pos_table.item(row, self.cur_table_col_idx_map['庫存股數']).text())

                self.communicator.cur_table_item_update_signal.emit(row, self.cur_table_col_idx_map['現價'], str(cur_price))
                cur_pnl = (cur_price - avg_price)*hold_qty
                cur_percent = cur_pnl/(avg_price*hold_qty)*100
                self.communicator.cur_table_item_update_signal.emit(row, self.cur_table_col_idx_map['損益試算'], str(int(round(cur_pnl, 0))))
                self.communicator.cur_table_item_update_signal.emit(row, self.cur_table_col_idx_map['獲利率%'], str(round(cur_percent, 2))+'%')
            else:
                return

    def handle_sell_connect(self):
        self.communicator.print_log_signal.emit('sell market data connected')
    
    def handle_sell_disconnect(self, code, message):
        self.communicator.print_log_signal.emit(f'sell market data disconnect: {code}, {message}')
    
    def handle_sell_error(self, error):
        self.communicator.print_log_signal.emit(f'sell market data error: {error}')

    def handle_buy_message(self, message):
        msg = json.loads(message)
        event = msg["event"]
        data = msg["data"]
        # print(event, data)
        
        # subscribed事件處理
        if event == "subscribed":
            id = data["id"]
            symbol = data["symbol"]
            self.communicator.print_log_signal.emit('訂閱成功(buy)...'+symbol)
            self.subscribed_buy_ids[symbol] = id
        
        elif event == "unsubscribed":
            for key, value in self.subscribed_buy_ids.items():
                if value == data["id"]:
                    print('pop', key, value)
                    remove_key = key
            self.subscribed_buy_ids.pop(remove_key)
            self.communicator.print_log_signal.emit(remove_key+"...成功移除訂閱(buy)")
        
        elif event == 'snapshot':
            symbol = data['symbol']

            if 'price' in data:
                cur_price = data['price']
                self.communicator.new_table_item_update_signal.emit(self.new_table_row_idx_map[symbol], self.new_table_col_idx_map['現價'], str(cur_price))

        # data事件處理
        elif event == "data":
            if 'isTrial' in data:
                if data['isTrial']:
                    return
            
            symbol = data['symbol']

            if symbol not in self.new_table_row_idx_map:
                return
            
            if 'price' in data:
                cur_price = data['price']
                self.communicator.new_table_item_update_signal.emit(self.new_table_row_idx_map[symbol], self.new_table_col_idx_map['現價'], str(cur_price))
            else:
                return

    def handle_buy_connect(self):
        self.communicator.print_log_signal.emit('buy market data connected')
    
    def handle_buy_disconnect(self, code, message):
        self.communicator.print_log_signal.emit(f'buy market data disconnect: {code}, {message}')
    
    def handle_buy_error(self, error):
        self.communicator.print_log_signal.emit(f'buy market data error: {error}')

    def showDialog(self):
        my_target_path = None
        my_target_list_file = Path("./target_list_path.pkl")
        if my_target_list_file.is_file():
            with open('./target_list_path.pkl', 'rb') as f:
                temp_dict = pickle.load(f)
                my_target_path = temp_dict['target_list_path']

        # Open the file dialog to select a file
        if my_target_path:
            file_path, _ = QFileDialog.getOpenFileName(self, '請選擇您的下單目標清單', my_target_path, 'All Files (*)')
        else:
            file_path, _ = QFileDialog.getOpenFileName(self, '請選擇您的下單目標清單', 'C:\\', 'All Files (*)')

        if file_path:
            self.lineEdit_default_file_path.setText(file_path)
            temp_dict = {
                'target_list_path': file_path
            }
            with open('target_list_path.pkl', 'wb') as f:
                pickle.dump(temp_dict, f)


    # 更新最新log到QPlainTextEdit的slot function
    def print_log(self, log_info):
        self.log_text.appendPlainText(log_info)
        self.log_text.moveCursor(QTextCursor.End)

    # 視窗關閉時要做的事，主要是關websocket連結及存檔現在持有部位
    def closeEvent(self, event):
        # do stuff
        self.print_log("saving position...")
        # Convert and write JSON object to file
        with open("hold_pos.json", "w", encoding='utf8') as outfile: 
            json.dump(self.hold_pos_dict, outfile, ensure_ascii=False)
        
        self.print_log("disconnect websocket...")
        self.buy_websocket.disconnect()
        self.sell_websocket.disconnect()
        sdk.logout()

        can_exit = True
        if can_exit:
            event.accept() # let the window close
        else:
            event.ignore()

if __name__ == "__main__":
    try:
        sdk = FubonSDK()
    except ValueError:
        raise ValueError("請確認網路連線")
    
    if not QApplication.instance():
        app = QApplication(sys.argv)
    else:
        app = QApplication.instance()
    app.setStyleSheet("QWidget{font-size: 12pt;}")
    form = LoginForm(MainApp, sdk, 'fraction.png')
    form.show()
    
    sys.exit(app.exec())