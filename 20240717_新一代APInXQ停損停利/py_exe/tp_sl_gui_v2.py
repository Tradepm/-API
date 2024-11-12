from login_gui_v1 import LoginForm
from sdk_logger import fubon_neo_logger

import sys
import pickle
import json
from pathlib import Path

from fubon_neo.sdk import FubonSDK, Mode, Order
from fubon_neo.constant import TimeInForce, OrderType, PriceType, MarketType, BSAction

from PySide6.QtWidgets import QApplication, QWidget, QPushButton, QLabel, QLineEdit, QGridLayout, QVBoxLayout, QHeaderView, QMessageBox, QTableWidget, QTableWidgetItem, QPlainTextEdit, QFileDialog, QSizePolicy
from PySide6.QtGui import QTextCursor, QIcon, QColor
from PySide6.QtCore import Qt, Signal, QObject, QMutex

from threading import Timer

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

class RepeatTimer(Timer):
    def run(self):
        self.function(*self.args, **self.kwargs)
        while not self.finished.wait(self.interval):
            self.function(*self.args, **self.kwargs)

class Communicate(QObject):
    # 定義一個帶參數的信號
    print_log_signal = Signal(str)
    item_update_signal = Signal(dict)
    filled_data_signal = Signal(dict)

class MainApp(QWidget):
    def __init__(self, sdk, active_account):
        super().__init__()
        
        self.sdk = sdk
        self.active_account = active_account
        self.logger = fubon_neo_logger(logger_name="sl_tp")
        self.sl_tp_logger = self.logger.get_logger()

        self.sl_tp_parameter_dict = {}
        self.default_sl_percent = -0.05
        self.default_tp_percent = 0.05

        my_file = Path("./sl_tp_parameter.pkl")
        if my_file.is_file():
            with open("sl_tp_parameter.pkl", "rb") as f:
                self.sl_tp_parameter_dict = pickle.load(f)
                self.default_sl_percent = self.sl_tp_parameter_dict["default_sl_percent"]/100.0
                self.default_tp_percent = self.sl_tp_parameter_dict["default_tp_percent"]/100.0
        

        my_icon = QIcon()
        my_icon.addFile('inventory.png')

        self.setWindowIcon(my_icon)
        self.setWindowTitle("Python庫存停損停利(教學範例，僅限現股)")
        self.resize(1200, 600)
        
        self.mutex = QMutex()
        
        # 製作上下排列layout上為庫存表，下為log資訊
        layout = QVBoxLayout()
        # 庫存表表頭
        self.table_header = ['股票名稱', '股票代號', '類別', '庫存股數', '庫存均價', '現價', '停損', '停利', '損益試算', '獲利率%']
        
        self.tablewidget = QTableWidget(0, len(self.table_header))
        self.tablewidget.setHorizontalHeaderLabels([f'{item}' for item in self.table_header])
        
        # 整個設定區layout
        layout_condition = QGridLayout()

        # 監控區layout設定
        label_monitor = QLabel('預設新部位停損停利設定')
        label_monitor.setStyleSheet("QLabel { font-size: 24px; font-weight: bold; }")
        label_monitor.setAlignment(Qt.AlignCenter)
        layout_condition.addWidget(label_monitor, 0, 0)
        label_sl = QLabel('\t預設停損(%, 0為不預設停損):')
        layout_condition.addWidget(label_sl, 1, 0)
        self.lineEdit_default_sl = QLineEdit()
        self.lineEdit_default_sl.setText(str(self.default_sl_percent*100))
        layout_condition.addWidget(self.lineEdit_default_sl, 1, 1)
        label_sl_post = QLabel('%')
        layout_condition.addWidget(label_sl_post, 1, 2)
        label_tp = QLabel('\t預設停利(%, 0為不預設停利):')
        layout_condition.addWidget(label_tp, 2, 0)
        self.lineEdit_default_tp = QLineEdit()
        self.lineEdit_default_tp.setText(str(self.default_tp_percent*100))
        layout_condition.addWidget(self.lineEdit_default_tp, 2, 1)
        label_tp_post = QLabel('%')
        layout_condition.addWidget(label_tp_post, 2, 2)

        # 啟動按鈕
        self.button_start = QPushButton('開始監控')
        self.button_start.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.button_start.setStyleSheet("QPushButton { font-size: 24px; font-weight: bold; }")
        layout_condition.addWidget(self.button_start, 0, 6, 3, 1)

        # 停止按鈕
        self.button_stop = QPushButton('停止監控')
        self.button_stop.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.button_stop.setStyleSheet("QPushButton { font-size: 24px; font-weight: bold; }")
        layout_condition.addWidget(self.button_stop, 0, 6, 3, 1)
        self.button_stop.setVisible(False)

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

        layout.addWidget(self.tablewidget, stretch=8)
        layout.addLayout(layout_condition, stretch=1)
        # layout.addLayout(layout_sim, stretch=1)
        layout.addWidget(self.log_text, stretch=3)
        self.setLayout(layout)

        self.print_log("login success, 現在使用帳號: {}".format(self.active_account.account))
        self.print_log("建立行情連線...")
        self.sl_tp_logger.info("sdk init realtime...")
        self.ws_mode = Mode.Normal
        self.sdk.init_realtime(self.ws_mode) # 建立行情連線
        self.print_log("行情連線建立OK")
        self.sl_tp_logger.info("sdk init realtime done")
        self.reststock = self.sdk.marketdata.rest_client.stock
        self.wsstock = self.sdk.marketdata.websocket_client.stock

        # slot function connect
        self.button_start.clicked.connect(self.on_button_start_clicked)
        self.button_stop.clicked.connect(self.on_button_stop_clicked)
        self.tablewidget.itemClicked[QTableWidgetItem].connect(self.onItemClicked)
        self.button_fake_websocket.clicked.connect(self.fake_ws_data)
        self.button_fake_buy_filled.clicked.connect(self.fake_buy_filled)
        self.button_fake_sell_filled.clicked.connect(self.fake_sell_filled)

        # communicator init and slot function connect
        self.communicator = Communicate()
        self.communicator.print_log_signal.connect(self.print_log)
        self.communicator.item_update_signal.connect(self.item_update)
        self.communicator.filled_data_signal.connect(self.handle_filled_data)
        
        # 初始化庫存表資訊
        self.inventories = {}
        self.unrealized_pnl = {}
        self.row_idx_map = {}
        self.col_idx_map = dict(zip(self.table_header, range(len(self.table_header))))
        self.epsilon = 0.0000001

        self.tickers_name = {}
        self.tickers_name_init()
        self.sl_tp_logger.info("snapshoting tickers name finish")
        self.subscribed_ids = {}
        self.is_ordered = []
        
        self.stop_loss_dict = {}
        self.take_profit_dict = {}

        # 模擬用變數
        self.fake_price_cnt = 0
        self.fake_buy_clicked = 0
    
    # 當有庫存歸零時刪除該列的slot function
    def del_table_row(self, row_idx):
        symbol = self.tablewidget.item(row_idx, self.col_idx_map['股票代號']).text
        self.sl_tp_logger.info(f"Deleting {symbol} from table...")
        self.tablewidget.removeRow(row_idx)
        
        for key, value in self.row_idx_map.items():
            if value > row_idx:
                self.row_idx_map[key] = value-1
            elif value == row_idx:
                pop_idx = key
        pop_item = self.row_idx_map.pop(pop_idx)
        self.sl_tp_logger.info(f"Pop {pop_item} from inventory...done")

    # 當有成交有不在現有庫存的現股股票時新增至現有表格最下方
    def add_new_inv(self, symbol, qty, price):
        row = self.tablewidget.rowCount()
        self.tablewidget.insertRow(row)
        
        for j in range(len(self.table_header)):
            if self.table_header[j] == '股票名稱':
                item = QTableWidgetItem(self.tickers_name[symbol])
                self.tablewidget.setItem(row, j, item)
            elif self.table_header[j] == '股票代號':
                item = QTableWidgetItem(symbol)
                self.tablewidget.setItem(row, j, item)
            elif self.table_header[j] == '類別':
                item = QTableWidgetItem("Stock")
                self.tablewidget.setItem(row, j, item)
            elif self.table_header[j] == '庫存股數':
                item = QTableWidgetItem(str(qty))
                self.tablewidget.setItem(row, j, item)
            elif self.table_header[j] == '庫存均價':
                item = QTableWidgetItem(str(round(price+self.epsilon, 2)))
                self.tablewidget.setItem(row, j, item)
            elif self.table_header[j] == '現價':
                item = QTableWidgetItem(str(round(price+self.epsilon, 2)))
                self.tablewidget.setItem(row, j, item)
            elif self.table_header[j] == '停損':
                item = QTableWidgetItem()
                item.setFlags(Qt.ItemIsSelectable & ~Qt.ItemIsEditable | Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
                if self.default_sl_percent < 0:
                    item.setCheckState(Qt.Checked)
                    new_sl_price = round(price*(1+self.default_sl_percent)+self.epsilon, 2)
                    item.setText(str(new_sl_price))
                    self.stop_loss_dict[symbol] = new_sl_price
                    self.tablewidget.setItem(row, j, item)
                    self.sl_tp_logger.info(f'{symbol} add sl {self.default_sl_percent*100}%, new_sl_price: {new_sl_price}')
                else:
                    item.setCheckState(Qt.Unchecked)
                    self.tablewidget.setItem(row, j, item)
                    self.sl_tp_logger.info(f'{symbol} no default sl set')
                
            elif self.table_header[j] == '停利':
                item = QTableWidgetItem()
                item.setFlags(Qt.ItemIsSelectable & ~Qt.ItemIsEditable | Qt.ItemIsEnabled|Qt.ItemIsUserCheckable)
                if self.default_tp_percent > 0:
                    item.setCheckState(Qt.Checked)
                    new_tp_price = round(price*(1+self.default_tp_percent)+self.epsilon, 2)
                    item.setText(str(new_tp_price))
                    self.take_profit_dict[symbol] = new_tp_price
                    self.tablewidget.setItem(row, j, item)
                    self.sl_tp_logger.info(f'{symbol} add tp {self.default_tp_percent*100}%, new_tp_price: {new_tp_price}')
                else:
                    item.setCheckState(Qt.Unchecked)
                    self.tablewidget.setItem(row, j, item)
                    self.sl_tp_logger.info(f'{symbol} no default tp set')
                    
            elif self.table_header[j] == '損益試算':
                cur_upnl = 0
                item = QTableWidgetItem(str(cur_upnl))
                self.tablewidget.setItem(row, j, item)
            elif self.table_header[j] == '獲利率%':
                return_rate = 0
                item = QTableWidgetItem(str(round(return_rate+self.epsilon, 2))+'%')
                self.tablewidget.setItem(row, j, item)

        self.row_idx_map[symbol] = row
        self.sl_tp_logger.info(f'{symbol} inv adding done. Subscribing...')

        self.wsstock.subscribe({
            'channel': 'trades',
            'symbol': symbol
        })

    # 測試用假裝有賣出成交的按鈕slot function
    def fake_sell_filled(self):
        new_fake_sell = fake_filled_data()
        stock_no = list(self.row_idx_map.keys())[0]
        new_fake_sell.stock_no = stock_no
        new_fake_sell.buy_sell = BSAction.Sell
        new_fake_sell.filled_qty = 1000
        new_fake_sell.filled_price = 14
        new_fake_sell.account = self.active_account.account
        new_fake_sell.user_def = "inv_SL"
        self.on_filled(None, new_fake_sell)

    # 測試用假裝有買入成交的按鈕slot function
    def fake_buy_filled(self):
        self.fake_buy_clicked+=1
        if self.fake_buy_clicked%2 == 1:
            self.fake_buy_timer = RepeatTimer(1, self.fake_buy_timer_func)
            self.fake_buy_timer.start()
        else:
            self.fake_buy_timer.cancel()

    def fake_buy_timer_func(self):
        stock_list = ['2330']#, '2330', '2330', '2330', '2330', '2330', '2509', '3230', '4903', '6661']
        for stock_no in stock_list:
            new_fake_buy = fake_filled_data()
            new_fake_buy.stock_no = stock_no
            new_fake_buy.buy_sell = BSAction.Buy
            new_fake_buy.filled_qty = 2000
            new_fake_buy.filled_price = 17
            new_fake_buy.account = self.active_account.account
            self.on_filled(None, new_fake_buy)

    def filled_data_to_dict(self, content):
        filled_dict = {}
        filled_dict['account'] = content.account
        filled_dict['symbol'] = content.stock_no
        filled_dict['buy_sell'] = content.buy_sell
        filled_dict['filled_qty'] = content.filled_qty
        filled_dict['filled_price'] = content.filled_price
        filled_dict['filled_avg_price'] = content.filled_avg_price
        filled_dict['order_type'] = content.order_type
        filled_dict['filled_time'] = content.filled_time
        filled_dict['user_def'] = content.user_def
        return filled_dict

    # 主動回報做基本判斷後轉資料給mainthread
    def on_filled(self, err, content):
        self.sl_tp_logger.info(f'filled recived:')
        self.sl_tp_logger.info(f'content:{content}')
        if content.account == self.active_account.account:
            if content.order_type == OrderType.Stock and content.filled_qty >= 1000:
                cur_filled_data = self.filled_data_to_dict(content)
                self.communicator.filled_data_signal.emit(cur_filled_data)
    
    # 主動回報接回mainthread判斷，接入成交回報後判斷 row_idx_map 要如何更新，sl 及 tp 監控列表及庫存列表是否需pop，訂閱是否加退訂
    def handle_filled_data(self, filled_data):
        symbol = filled_data['symbol']
        filled_qty = filled_data['filled_qty']
        filled_price = filled_data['filled_price']

        if filled_data['buy_sell'] == BSAction.Buy:
            self.sl_tp_logger.info(f"recevied Buy filled data: {symbol}")
            if (symbol, str(filled_data['order_type'])) in self.inventories:
                
                inv_qty_item = self.tablewidget.item(self.row_idx_map[symbol], self.col_idx_map['庫存股數'])
                inv_qty = int(inv_qty_item.text())
                new_inv_qty = inv_qty + filled_qty
                self.sl_tp_logger.info(f"{symbol} already in inventories, original inv_qty:{inv_qty}, new_inv_qty:{new_inv_qty}")

                avg_item = self.tablewidget.item(self.row_idx_map[symbol], self.col_idx_map['庫存均價'])
                avg_price = float(avg_item.text())

                new_avg_price = ((inv_qty*avg_price) + (filled_qty*filled_price))/new_inv_qty
                new_pnl = (filled_price-new_avg_price)*new_inv_qty
                new_cost = new_avg_price*new_inv_qty
                new_rate_return = new_pnl/new_cost*100

                # update row
                self.tablewidget.item(self.row_idx_map[symbol], self.col_idx_map['庫存股數']).setText(str(new_inv_qty))
                self.tablewidget.item(self.row_idx_map[symbol], self.col_idx_map['庫存均價']).setText(str(round(new_avg_price+self.epsilon, 2)))
                self.tablewidget.item(self.row_idx_map[symbol], self.col_idx_map['現價']).setText(str(round(filled_price+self.epsilon, 2)))
                self.tablewidget.item(self.row_idx_map[symbol], self.col_idx_map['損益試算']).setText(str(round(new_pnl+self.epsilon, 2)))
                self.tablewidget.item(self.row_idx_map[symbol], self.col_idx_map['獲利率%']).setText(str(round(new_rate_return+self.epsilon, 2))+"%")
                self.sl_tp_logger.info(f"{symbol} inv: {new_inv_qty}, buy hoding inv update finish")

            else:
                self.sl_tp_logger.info(f"{symbol} brand new, adding inv...")
                self.add_new_inv(symbol, filled_qty, filled_price)
                self.inventories[(symbol, str(filled_data['order_type']))] = filled_data
                self.sl_tp_logger.info(f"{symbol} inv: {filled_qty}, buy new inv update finish")
                
        elif filled_data['buy_sell'] == BSAction.Sell:
            self.sl_tp_logger.info(f"recevied Sell filled data: {symbol}")
            if (symbol, str(filled_data['order_type'])) in self.inventories:
                inv_qty_item = self.tablewidget.item(self.row_idx_map[symbol], self.col_idx_map['庫存股數'])
                inv_qty = int(inv_qty_item.text())
                remain_qty = inv_qty-filled_qty

                self.sl_tp_logger.info(f"{symbol} sell is in inventories, cur_inv: {inv_qty}, remain_qty: {remain_qty}")
                if remain_qty > 0:
                    remain_qty_str = str(int(round(remain_qty, 0)))
                    if filled_data['user_def'] == "inv_SL":
                        self.print_log("停損出場 "+symbol+": "+str(filled_qty)+"股, 成交價:"+str(filled_price)+", 剩餘: "+remain_qty_str+"股")
                        self.sl_tp_logger.info(f"停損出場 {symbol}: {filled_qty} 股, 成交價: {filled_price}, 剩餘: {remain_qty_str} 股")
                    elif filled_data['user_def'] == "inv_TP":
                        self.print_log("停利出場 "+symbol+": "+str(filled_qty)+"股, 成交價:"+str(filled_price)+", 剩餘: "+remain_qty_str+"股")
                        self.sl_tp_logger.info(f"停利出場 {symbol}: {filled_qty} 股, 成交價: {filled_price}, 剩餘: {remain_qty_str} 股")
                
                    self.tablewidget.item(inv_qty_item.row(), self.col_idx_map['庫存股數']).setText(remain_qty_str)
                    avg_price_item = self.tablewidget.item(self.row_idx_map[symbol], self.col_idx_map['庫存均價'])
                    avg_price = float(avg_price_item.text())
                    new_pnl = (filled_price-avg_price)*remain_qty
                    new_cost = avg_price*remain_qty
                    new_rate_return = new_pnl/new_cost*100

                    # update row
                    self.tablewidget.item(self.row_idx_map[symbol], self.col_idx_map['庫存股數']).setText(str(remain_qty))
                    self.tablewidget.item(self.row_idx_map[symbol], self.col_idx_map['現價']).setText(str(round(filled_price+self.epsilon, 2)))
                    self.tablewidget.item(self.row_idx_map[symbol], self.col_idx_map['損益試算']).setText(str(round(new_pnl+self.epsilon, 2)))
                    self.tablewidget.item(self.row_idx_map[symbol], self.col_idx_map['獲利率%']).setText(str(round(new_rate_return+self.epsilon, 2))+"%")

                elif remain_qty == 0:
                    # del table row and unsubscribe
                    self.del_table_row(self.row_idx_map[symbol])

                    if symbol in self.stop_loss_dict:
                        self.stop_loss_dict.pop(symbol)
                    if symbol in self.take_profit_dict:
                        self.take_profit_dict.pop(symbol)
                    if symbol in self.subscribed_ids:
                        self.wsstock.unsubscribe({
                            'id':self.subscribed_ids[symbol]
                        })
                
                    if filled_data['user_def'] == "inv_SL":
                        self.print_log("停損出場 "+symbol+": "+str(filled_qty)+"股, 成交價:"+str(filled_price))
                        self.sl_tp_logger.info(f"停損出場 {symbol}: {filled_qty} 股, 成交價: {filled_price}")
                    elif filled_data['user_def'] == "inv_TP":
                        self.print_log("停利出場 "+symbol+": "+str(filled_qty)+"股, 成交價:"+str(filled_price))
                        self.sl_tp_logger.info(f"停利出場 {symbol}: {filled_qty} 股, 成交價: {filled_price}")
                    else:
                        self.print_log("手動出場 "+symbol+": "+str(filled_qty)+"股, 成交價:"+str(filled_price))
                        self.sl_tp_logger.info(f"手動出場 {symbol}: {filled_qty} 股, 成交價: {filled_price}")

                    print("deleting...")
                    while symbol in self.row_idx_map:
                        print("deleting...", symbol)
                        pass
                    print("deleting done")
            
                    self.inventories.pop(symbol, str(filled_data['order_type']))
                
                    try:
                        self.is_ordered.remove(symbol)
                        self.sl_tp_logger.info(f"Removed {symbol} from is_ordered map")
                    except ValueError as v_err:
                        self.sl_tp_logger.error(f"{symbol} not in is_ordered, error {v_err}")

    # 測試用假裝有websocket data的按鈕slot function
    def fake_ws_data(self):
        if self.fake_price_cnt % 2==0:
            self.price_interval = 0
            self.fake_ws_timer = RepeatTimer(0.1, self.fake_message)
            self.fake_ws_timer.start()
        else:
            self.fake_ws_timer.cancel()

        self.fake_price_cnt+=1

    def fake_message(self):
        self.price_interval+=1
        stock_list = ['00929']
        json_template = '''{{"event":"data","data":{{"symbol":"{symbol}","type":"EQUITY","exchange":"TWSE","market":"TSE","price":{price},"size":713,"bid":16.67,"ask":{price}, "isLimitUpAsk":true, "volume":8066,"isClose":true,"time":1718343000000000,"serial":9475857}},"id":"w4mkzAqYAYFKyEBLyEjmHEoNADpwKjUJmqg02G3OC9YmV","channel":"trades"}}'''
        json_price = 15+self.price_interval
        json_str = json_template.format(symbol=stock_list[self.price_interval % len(stock_list)], price=str(json_price))
        self.handle_message(json_str)

    # 更新表格內某一格值的slot function
    def item_update(self, tick_data):
        symbol = tick_data['symbol']
        if symbol not in self.row_idx_map:
            return
        
        row = self.row_idx_map[symbol]
        cur_price = tick_data['price']
        
        avg_price_item = self.tablewidget.item(row, self.col_idx_map['庫存均價'])
        avg_price = avg_price_item.text()
    
        share_item = self.tablewidget.item(row, self.col_idx_map['庫存股數'])
        share = share_item.text()
    
        cur_pnl = (cur_price-float(avg_price))*float(share)
        return_rate = cur_pnl/(float(avg_price)*float(share))*100
        
        self.tablewidget.item(row, self.col_idx_map['現價']).setText(str(cur_price))
        self.tablewidget.item(row, self.col_idx_map['損益試算']).setText(str(int(round(cur_pnl, 0))))
        self.tablewidget.item(row, self.col_idx_map['獲利率%']).setText(str(round(return_rate+self.epsilon, 2))+'%')


    def onItemClicked(self, item):
        if item.checkState() == Qt.Checked:
            if item.column() == self.col_idx_map['停損']:
                symbol = self.tablewidget.item(item.row(), self.col_idx_map['股票代號']).text()
                item_str = item.text()
                if symbol in self.stop_loss_dict:
                    return
                
                try:
                    item_price = float(item_str)
                except Exception as e:
                    self.print_log(str(e))
                    self.print_log("請輸入正確價格，停損價格必須小於現價並大於0")
                    item.setCheckState(Qt.Unchecked)
                    self.sl_tp_logger.error(f"{symbol} stop loss update fail, user input {item_str} is not digit")
                    return
                
                cur_price = self.tablewidget.item(item.row(), self.col_idx_map['現價']).text()
                cur_price = float(cur_price)
                if cur_price <= item_price or 0 >= item_price:
                    self.print_log("請輸入正確價格，停損價格必須小於現價並大於0")
                    self.sl_tp_logger.error(f"{symbol} stop loss update fail, user input {item_price} is less than 0 or greater than cur_price")
                    item.setCheckState(Qt.Unchecked)
                else:
                    self.stop_loss_dict[symbol] = item_price
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                    self.print_log(symbol+"...停損設定成功: "+item_str)
                    self.sl_tp_logger.info(f"{symbol} stop loss manul modify successfully: {self.stop_loss_dict}")

            elif item.column() == self.col_idx_map['停利']:
                symbol = self.tablewidget.item(item.row(), self.col_idx_map['股票代號']).text()
                item_str = item.text()

                if symbol in self.take_profit_dict:
                    return

                try:
                    item_price = float(item_str)
                except Exception as e:
                    self.print_log(str(e))
                    self.print_log("請輸入正確價格，停利價格必須大於現價")
                    item.setCheckState(Qt.Unchecked)
                    self.sl_tp_logger.error(f"{symbol} take profit update fail, user input {item_str} is not digit")
                    return
                
                cur_price = self.tablewidget.item(item.row(), self.col_idx_map['現價']).text()
                cur_price = float(cur_price)
                if cur_price >= item_price:
                    self.print_log("請輸入正確價格，停利價格必須大於現價")
                    self.sl_tp_logger.error(f"{symbol} take profit update fail, user input {item_price} is less than item_price")
                    item.setCheckState(Qt.Unchecked)
                else:
                    self.take_profit_dict[symbol] = item_price
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                    self.print_log(symbol+"...停利設定成功: "+item_str)
                    self.sl_tp_logger.info(f"{symbol} take profit manul modify successfully: {self.take_profit_dict}")

        elif item.checkState() == Qt.Unchecked:
            if item.column() == self.col_idx_map['停損']:
                item.setFlags(item.flags() | Qt.ItemIsEditable)
                symbol = self.tablewidget.item(item.row(), self.col_idx_map['股票代號']).text()
                if symbol in self.stop_loss_dict:
                    self.stop_loss_dict.pop(symbol)
                    self.print_log(symbol+"...移除停損，請重新設置")
                    self.sl_tp_logger.info(f"{symbol} stop loss cancelled: {self.stop_loss_dict}")

            elif item.column() == self.col_idx_map['停利']:
                item.setFlags(item.flags() | Qt.ItemIsEditable)
                symbol = self.tablewidget.item(item.row(), self.col_idx_map['股票代號']).text()
                if symbol in self.take_profit_dict:
                    self.take_profit_dict.pop(symbol)
                    self.print_log(symbol+"...移除停利，請重新設置")
                    self.sl_tp_logger.info(f"{symbol} take profet cancelled: {self.stop_loss_dict}")

    # 停損停利用的市價單函式
    def sell_market_order(self, stock_symbol, sell_qty, sl_or_tp):
        order = Order(
            buy_sell = BSAction.Sell,
            symbol = stock_symbol,
            price =  None,
            quantity =  int(sell_qty),
            market_type = MarketType.Common,
            price_type = PriceType.Market,
            time_in_force = TimeInForce.ROD,
            order_type = OrderType.Stock,
            user_def = sl_or_tp # optional field
        )

        order_res = self.sdk.stock.place_order(self.active_account, order)
        return order_res

    def handle_message(self, message):
        msg = json.loads(message)
        event = msg["event"]
        data = msg["data"]
        # print(event, data)
        
        # subscribed事件處理
        if event == "subscribed":
            id = data["id"]
            symbol = data["symbol"]
            self.communicator.print_log_signal.emit('訂閱成功...'+symbol)
            self.subscribed_ids[symbol] = id
        
        elif event == "unsubscribed":
            for key, value in self.subscribed_ids.items():
                if value == data["id"]:
                    print(key, value)
                    remove_key = key
            self.subscribed_ids.pop(remove_key)
            self.communicator.print_log_signal.emit(remove_key+"...成功移除訂閱")
        
        # data事件處理
        elif event == "snapshot":
            if 'isTrial' in data:
                if data['isTrial']:
                    return
                
            if 'price' in data:
                cur_price = data["price"]
            else:
                cur_price = '-'
            symbol = data["symbol"]

            self.communicator.item_update_signal.emit(data)

        # data事件處理
        elif event == "data":
            if 'isTrial' in data:
                if data['isTrial']:
                    return
            
            symbol = data["symbol"]
            
            if symbol not in self.row_idx_map:
                return
            
            if 'price' in data:
                cur_price = data["price"]
            else:
                return
                     
            self.communicator.item_update_signal.emit(data)
            
            if symbol in self.stop_loss_dict:
                if cur_price <= self.stop_loss_dict[symbol] and symbol not in self.is_ordered:
                    share_item = self.tablewidget.item(self.row_idx_map[symbol], self.col_idx_map['庫存股數'])
                    share = share_item.text()
                    self.communicator.print_log_signal.emit(symbol+"...停損市價單發送...")
                    sl_res = self.sell_market_order(symbol, share, "inv_SL")
                    if sl_res.is_success:
                        self.communicator.print_log_signal.emit(symbol+"...停損市價單發送成功，單號: "+sl_res.data.order_no)
                        self.is_ordered.append(symbol)
                        self.sl_tp_logger.info(f"{symbol} {share}股, 停損市價單發送成功, 單號: {sl_res.data.order_no}")
                    else:
                        self.communicator.print_log_signal.emit(symbol+"...停損市價單發送失敗...")
                        self.communicator.print_log_signal.emit(sl_res.message)
                        self.sl_tp_logger.error(f"{symbol} 停損市價單發送失敗, fail message: {sl_res.message}")
                elif symbol in self.is_ordered:
                    self.communicator.print_log_signal.emit(symbol+"...停損市價單已發送過...")
                    self.sl_tp_logger.info(f"{symbol} {share}股, 停損市價單已發送過")

            if symbol in self.take_profit_dict:
                if cur_price >= self.take_profit_dict[symbol] and symbol not in self.is_ordered:
                    share_item = self.tablewidget.item(self.row_idx_map[symbol], self.col_idx_map['庫存股數'])
                    share = share_item.text()
                    self.communicator.print_log_signal.emit(symbol+"...停利市價單發送...")
                    tp_res = self.sell_market_order(symbol, share, "inv_TP")
                    if tp_res.is_success:
                        self.communicator.print_log_signal.emit(symbol+"...停利市價單發送成功，單號: "+tp_res.data.order_no)
                        self.is_ordered.append(symbol)
                        self.sl_tp_logger.info(f"{symbol} {share}股, 停利市價單發送成功, 單號: {sl_res.data.order_no}")
                    else:
                        self.communicator.print_log_signal.emit(symbol+"...停利市價單發送失敗...")
                        self.communicator.print_log_signal.emit(tp_res.message)
                        self.sl_tp_logger.error(f"{symbol} 停利市價單發送失敗, fail message: {sl_res.message}")
                elif symbol in self.is_ordered:
                    self.communicator.print_log_signal.emit(symbol+"...停利市價單已發送過...")
                    self.sl_tp_logger.info(f"{symbol} {share}股, 停利市價單已發送過")
            
    def handle_connect(self):
        self.communicator.print_log_signal.emit('market data connected')
        self.sl_tp_logger.info("market data connected")
    
    def handle_disconnect(self, code, message):
        self.communicator.print_log_signal.emit(f'market data disconnect: {code}, {message}')
        self.sl_tp_logger.info(f"market data disconnect: {code}, {message}")
        self.mutex.unlock()
    
    def handle_error(self, error):
        self.communicator.print_log_signal.emit(f'market data error: {error}')
        self.sl_tp_logger.error(f'market data error: {error}')
        self.mutex.unlock()

    # 視窗啟動時撈取對應帳號的inventories和unrealized_pnl初始化表格
    def table_init(self):
        inv_res = self.sdk.accounting.inventories(self.active_account)
        if inv_res.is_success:
            self.print_log("庫存抓取成功")
            inv_data = inv_res.data
            for inv in inv_data:
                if inv.today_qty != 0 and inv.order_type == OrderType.Stock:
                    self.inventories[(inv.stock_no, str(inv.order_type))] = inv
        else:
            self.print_log("庫存抓取失敗")
        
        self.print_log("抓取未實現損益...")
        upnl_res = self.sdk.accounting.unrealized_gains_and_loses(self.active_account)
        if upnl_res.is_success:
            self.print_log("未實現損益抓取成功")
            upnl_data = upnl_res.data
            for upnl in upnl_data:
                self.unrealized_pnl[(upnl.stock_no, str(upnl.order_type))] = upnl
        else:
            self.print_log("未實現損益抓取失敗")

        # 依庫存及未實現損益資訊開始填表
        for key, value in self.inventories.items():
            stock_symbol = key[0]
            stock_name = self.tickers_name[key[0]]
            print(stock_symbol)
            row = self.tablewidget.rowCount()
            self.tablewidget.insertRow(row)
            self.row_idx_map[stock_symbol] = row
            for j in range(len(self.table_header)):
                item = QTableWidgetItem()
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                if self.table_header[j] == '股票名稱':
                    item.setText(stock_name)
                    self.tablewidget.setItem(row, j, item)
                elif self.table_header[j] == '股票代號':
                    item.setText(stock_symbol)
                    self.tablewidget.setItem(row, j, item)
                elif self.table_header[j] == '類別':
                    item.setText(str(value.order_type).split('.')[-1])
                    self.tablewidget.setItem(row, j, item)
                elif self.table_header[j] == '庫存股數':
                    item.setText(str(value.today_qty))
                    self.tablewidget.setItem(row, j, item)
                elif self.table_header[j] == '現價':
                    item.setText('-')
                    self.tablewidget.setItem(row, j, item)
                elif self.table_header[j] == '停損':
                    item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEditable | Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
                    item.setCheckState(Qt.Unchecked)
                    self.tablewidget.setItem(row, j, item)
                elif self.table_header[j] == '停利':
                    item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEditable | Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
                    item.setCheckState(Qt.Unchecked)
                    self.tablewidget.setItem(row, j, item)
                elif self.table_header[j] == '庫存均價':
                    item.setText(str(round(self.unrealized_pnl[key].cost_price+self.epsilon, 2)))
                    self.tablewidget.setItem(row, j, item)
                elif self.table_header[j] == '損益試算':
                    cur_upnl = 0
                    if self.unrealized_pnl[key].unrealized_profit > self.unrealized_pnl[key].unrealized_loss:
                        cur_upnl = self.unrealized_pnl[key].unrealized_profit
                    else:
                        cur_upnl = -(self.unrealized_pnl[key].unrealized_loss)
                    item.setText(str(cur_upnl))
                    self.tablewidget.setItem(row, j, item)
                elif self.table_header[j] == '獲利率%':
                    cur_upnl = 0
                    if self.unrealized_pnl[key].unrealized_profit > self.unrealized_pnl[key].unrealized_loss:
                        cur_upnl = self.unrealized_pnl[key].unrealized_profit
                    else:
                        cur_upnl = -(self.unrealized_pnl[key].unrealized_loss)
                    stock_cost = value.today_qty*self.unrealized_pnl[key].cost_price
                    return_rate = cur_upnl/stock_cost*100
                    item.setText(str(round(return_rate+self.epsilon, 2))+'%')
                    self.tablewidget.setItem(row, j, item)
            self.wsstock.subscribe({
                'channel': 'trades',
                'symbol': stock_symbol
            })

        self.print_log('庫存資訊初始化完成')
        self.sl_tp_logger.info('inventories fetched and initialized done')

        # 調整股票名稱欄位寬度
        header = self.tablewidget.horizontalHeader()      
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        print(self.row_idx_map)
        print(self.col_idx_map)

    def on_button_start_clicked(self):
        self.sl_tp_logger.info("button start click")
        try:
            self.default_sl_percent = float(self.lineEdit_default_sl.text())*0.01
            if self.default_sl_percent > 0:
                self.print_log("請輸入正確的監控停損(%), 範圍需小於0, 0為不預設")
                self.sl_tp_logger.error(f"default sl wrong input {self.default_sl_percent}")
                return
            elif self.default_sl_percent == 0:
                self.print_log("預設停損輸入為0, 不預設停損")
            else:
                self.print_log("預設停損"+str(self.default_sl_percent*100)+"%, 設定成功")
        except Exception as e:
            self.print_log("請輸入正確的監控停損(%), 範圍需小於0, 0為不預設 "+str(e))
            self.sl_tp_logger.error(f"something went wrong when setting default sl {e}")
            return
        
        try:
            self.default_tp_percent = float(self.lineEdit_default_tp.text())*0.01
            if self.default_tp_percent < 0:
                self.print_log("請輸入正確的監控停利(%), 範圍需大於0, 0為不預設")
                self.sl_tp_logger.error(f"default tp wrong input {self.default_tp_percent}")
                return
            elif self.default_tp_percent == 0:
                self.print_log("預設停利輸入為0, 不預設停利")
            else:
                self.print_log("預設停利"+str(self.default_tp_percent*100)+"%, 設定成功")
        except Exception as e:
            self.print_log("請輸入正確的監控停利(%), 範圍需大於0, 0為不預設 "+str(e))
            self.sl_tp_logger.info(f"something went wrong when setting default tp {e}")
            return
        
        self.sl_tp_logger.info(f"using default_sl {self.default_sl_percent} and default_tp {self.default_tp_percent}")
        self.sl_tp_logger.info("start monitoring")
        self.print_log("開始執行監控")
        self.lineEdit_default_sl.setReadOnly(True)
        self.lineEdit_default_tp.setReadOnly(True)
        self.button_start.setVisible(False)
        self.button_stop.setVisible(True)
        self.tablewidget.clearContents()
        self.tablewidget.setRowCount(0)

        self.sl_tp_logger.info(f"establishing quote websocket")
        self.print_log("建立WebSocket行情連線")
        self.sdk.init_realtime(self.ws_mode)
        self.wsstock = self.sdk.marketdata.websocket_client.stock
        self.wsstock.on("connect", self.handle_connect)
        self.wsstock.on("disconnect", self.handle_disconnect)
        self.wsstock.on("error", self.handle_error)
        self.wsstock.on('message', self.handle_message)
        self.wsstock.connect()
        
        self.sl_tp_logger.info(f"fetching inventories")
        self.print_log("抓取庫存...")
        self.table_init()
        self.sdk.set_on_filled(self.on_filled)

        self.save_sl_tp_parameter()

    def on_button_stop_clicked(self):
        self.print_log("停止執行監控")
        self.lineEdit_default_sl.setReadOnly(False)
        self.lineEdit_default_tp.setReadOnly(False)
        self.button_stop.setVisible(False)
        self.button_start.setVisible(True)

        self.wsstock.disconnect()
        try:
            if self.fake_ws_timer.is_alive():
                self.fake_ws_timer.cancel()
                self.fake_price_cnt+=1
        except AttributeError:
            print("no fake ws timer exist")

        self.save_sl_tp_parameter()

    def tickers_name_init(self):
        self.tickers_res = self.reststock.snapshot.quotes(market='TSE')
        for item in self.tickers_res['data']:
            if 'name' in item:
                self.tickers_name.update({item['symbol']: item['name']})
            else:
                self.tickers_name.update({item['symbol']: ''})

        self.tickers_res = self.reststock.snapshot.quotes(market='OTC')
        for item in self.tickers_res['data']:
            if 'name' in item:
                self.tickers_name.update({item['symbol']: item['name']})
            else:
                self.tickers_name.update({item['symbol']: ''})
    
    def save_sl_tp_parameter(self):
        with open('sl_tp_parameter.pkl', 'wb') as f:
            self.sl_tp_parameter_dict['default_sl_percent'] = self.default_sl_percent*100
            self.sl_tp_parameter_dict['default_tp_percent'] = self.default_tp_percent*100
            pickle.dump(self.sl_tp_parameter_dict, f)

    # 更新最新log到QPlainTextEdit的slot function
    def print_log(self, log_info):
        self.log_text.appendPlainText(log_info)
        self.log_text.moveCursor(QTextCursor.End)
    
    # 視窗關閉時要做的事，主要是關websocket連結
    def closeEvent(self, event):
        # do stuff
        self.save_sl_tp_parameter()
        self.print_log("disconnect websocket...")
        self.wsstock.disconnect()
        self.sdk.logout()

        try:
            if self.fake_ws_timer.is_alive():
                self.fake_ws_timer.cancel()
        except AttributeError:
            print("no fake ws timer exist")

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

    app.setStyleSheet("QWidget{font-size: 12pt;}")
    form = LoginForm(MainApp, sdk, 'inventory.png')
    form.show()
    
    sys.exit(app.exec())