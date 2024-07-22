import sys
import pickle
import json
from pathlib import Path

from fubon_neo.sdk import FubonSDK, Order
from fubon_neo.constant import TimeInForce, OrderType, PriceType, MarketType, BSAction

from PySide6.QtWidgets import QApplication, QWidget, QPushButton, QLabel, QLineEdit, QGridLayout, QVBoxLayout, QHeaderView, QMessageBox, QTableWidget, QTableWidgetItem, QPlainTextEdit, QFileDialog, QSizePolicy
from PySide6.QtGui import QTextCursor, QIcon, QColor
from PySide6.QtCore import Qt, Signal, QObject, QMutex
from threading import Timer

class LoginForm(QWidget):
    def __init__(self):
        super().__init__()
        my_icon = QIcon()
        my_icon.addFile('inventory.png')

        self.setWindowIcon(my_icon)
        self.setWindowTitle('新一代API_登入')
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
    item_update_signal = Signal(int, int, str)
    add_new_inv_signal = Signal(str, int, float)
    del_row_signal = Signal(int)

class MainApp(QWidget):
    def __init__(self):
        super().__init__()

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
        self.lineEdit_default_sl.setText('-5')
        layout_condition.addWidget(self.lineEdit_default_sl, 1, 1)
        label_sl_post = QLabel('%')
        layout_condition.addWidget(label_sl_post, 1, 2)
        label_tp = QLabel('\t預設停利(%, 0為不預設停損):')
        layout_condition.addWidget(label_tp, 2, 0)
        self.lineEdit_default_tp = QLineEdit()
        self.lineEdit_default_tp.setText('5')
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

        layout.addWidget(self.tablewidget)
        layout.addLayout(layout_condition)
        layout.addLayout(layout_sim)
        layout.addWidget(self.log_text)
        self.setLayout(layout)

        self.print_log("login success, 現在使用帳號: {}".format(active_account.account))
        self.print_log("建立行情連線...")
        sdk.init_realtime() # 建立行情連線
        self.print_log("行情連線建立OK")
        self.reststock = sdk.marketdata.rest_client.stock
        self.wsstock = sdk.marketdata.websocket_client.stock

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
        self.communicator.add_new_inv_signal.connect(self.add_new_inv)
        self.communicator.del_row_signal.connect(self.del_table_row)
        
        # 初始化庫存表資訊
        self.default_sl_percent = float(self.lineEdit_default_sl.text())
        self.default_tp_percent = float(self.lineEdit_default_tp.text())

        self.inventories = {}
        self.unrealized_pnl = {}
        self.row_idx_map = {}
        self.col_idx_map = dict(zip(self.table_header, range(len(self.table_header))))
        self.epsilon = 0.0000001

        self.tickers_name = {}
        self.tickers_name_init()
        self.subscribed_ids = {}
        self.is_ordered = []
        
        self.stop_loss_dict = {}
        self.take_profit_dict = {}

        # 模擬用變數
        self.fake_price_cnt = 0
    
    # 當有庫存歸零時刪除該列的slot function
    def del_table_row(self, row_idx):
        self.tablewidget.removeRow(row_idx)
        
        for key, value in self.row_idx_map.items():
            if value > row_idx:
                self.row_idx_map[key] = value-1
            elif value == row_idx:
                pop_idx = key
        self.row_idx_map.pop(pop_idx)
        print("pop inventory finish")

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
                else:
                    item.setCheckState(Qt.Unchecked)
                    self.tablewidget.setItem(row, j, item)
                
            elif self.table_header[j] == '停利':
                item = QTableWidgetItem()
                item.setFlags(Qt.ItemIsSelectable & ~Qt.ItemIsEditable | Qt.ItemIsEnabled|Qt.ItemIsUserCheckable)
                if self.default_tp_percent > 0:
                    item.setCheckState(Qt.Checked)
                    new_tp_price = round(price*(1+self.default_tp_percent)+self.epsilon, 2)
                    item.setText(str(new_tp_price))
                    self.take_profit_dict[symbol] = new_tp_price
                    self.tablewidget.setItem(row, j, item)
                else:
                    item.setCheckState(Qt.Unchecked)
                    self.tablewidget.setItem(row, j, item)
                    
            elif self.table_header[j] == '損益試算':
                cur_upnl = 0
                item = QTableWidgetItem(str(cur_upnl))
                self.tablewidget.setItem(row, j, item)
            elif self.table_header[j] == '獲利率%':
                return_rate = 0
                item = QTableWidgetItem(str(round(return_rate+self.epsilon, 2))+'%')
                self.tablewidget.setItem(row, j, item)

        self.row_idx_map[symbol] = row
        self.wsstock.subscribe({
            'channel': 'trades',
            'symbol': symbol
        })

    # 測試用假裝有賣出成交的按鈕slot function
    def fake_sell_filled(self):
        new_fake_sell = fake_filled_data()
        stock_list = ['2330', '2881', '2454', '00940', '1101', '6598', '2509', '3230', '4903', '6661']
        for stock_no in stock_list:
            new_fake_sell.stock_no = stock_no
            new_fake_sell.buy_sell = BSAction.Sell
            new_fake_sell.filled_qty = 1000
            new_fake_sell.filled_price = 14
            new_fake_sell.account = active_account.account
            new_fake_sell.user_def = "inv_SL"
            self.on_filled(None, new_fake_sell)

    # 測試用假裝有買入成交的按鈕slot function
    def fake_buy_filled(self):
        stock_list = ['2330', '2881', '2454', '00940', '1101', '6598', '2509', '3230', '4903', '6661']
        for stock_no in stock_list:
            new_fake_buy = fake_filled_data()
            new_fake_buy.stock_no = stock_no
            new_fake_buy.buy_sell = BSAction.Buy
            new_fake_buy.filled_qty = 2000
            new_fake_buy.filled_price = 17
            new_fake_buy.account = active_account.account
            self.on_filled(None, new_fake_buy)

    # 主動回報，接入成交回報後判斷 row_idx_map 要如何更新，sl 及 tp 監控列表及庫存列表是否需pop，訂閱是否加退訂
    def on_filled(self, err, content):
        print('filled recived:', content.stock_no, content.buy_sell)
        print('content:', content)
        if content.account == active_account.account:
            # print("filled get lock")
            self.mutex.lock()
            if content.order_type == OrderType.Stock and content.filled_qty >= 1000:
                if content.buy_sell == BSAction.Buy:
                    print("buy:", content.buy_sell)
                    if (content.stock_no, str(content.order_type)) in self.inventories:
                        print("already in inventories", self.row_idx_map)
                        
                        inv_item = self.tablewidget.item(self.row_idx_map[content.stock_no], self.col_idx_map['庫存股數'])
                        inv_qty = int(inv_item.text())
                        new_inv_qty = inv_qty + content.filled_qty
                        
                        print(new_inv_qty)
                        avg_item = self.tablewidget.item(self.row_idx_map[content.stock_no], self.col_idx_map['庫存均價'])
                        avg_price = float(avg_item.text())
                        new_avg_price = ((inv_qty*avg_price) + (content.filled_qty*content.filled_price))/new_inv_qty
                        new_pnl = (content.filled_price-new_avg_price)*new_inv_qty
                        new_cost = new_avg_price*new_inv_qty
                        new_rate_return = new_pnl/new_cost*100

                        # update row
                        self.communicator.item_update_signal.emit(self.row_idx_map[content.stock_no], self.col_idx_map['庫存股數'], str(new_inv_qty))
                        self.communicator.item_update_signal.emit(self.row_idx_map[content.stock_no], self.col_idx_map['庫存均價'], str(round(new_avg_price+self.epsilon, 2)))
                        self.communicator.item_update_signal.emit(self.row_idx_map[content.stock_no], self.col_idx_map['現價'], str(round(content.filled_price+self.epsilon, 2)))
                        self.communicator.item_update_signal.emit(self.row_idx_map[content.stock_no], self.col_idx_map['損益試算'], str(round(new_pnl+self.epsilon, 2)))
                        self.communicator.item_update_signal.emit(self.row_idx_map[content.stock_no], self.col_idx_map['獲利率%'], str(round(new_rate_return+self.epsilon, 2))+"%")

                    else:
                        self.communicator.add_new_inv_signal.emit(content.stock_no, content.filled_qty, content.filled_price)
                        self.inventories[(content.stock_no, str(content.order_type))] = content
                        print("adding...", content.stock_no)
                        while content.stock_no not in self.row_idx_map:
                            print("adding...", content.stock_no)
                            pass
                        print("add done")
                        
                elif content.buy_sell == BSAction.Sell:
                    print("sell:", content.stock_no)
                    # print(self.inventories)
                    if (content.stock_no, str(content.order_type)) in self.inventories:
                        inv_item = self.tablewidget.item(self.row_idx_map[content.stock_no], self.col_idx_map['庫存股數'])
                        inv_qty = int(inv_item.text())
                        remain_qty = inv_qty-content.filled_qty
                        if remain_qty > 0:
                            remain_qty_str = str(int(round(remain_qty, 0)))
                            if content.user_def == "inv_SL":
                                self.communicator.print_log_signal.emit("停損出場 "+content.stock_no+": "+str(content.filled_qty)+"股, 成交價:"+str(content.filled_price)+", 剩餘: "+remain_qty_str+"股")
                            elif content.user_def == "inv_TP":
                                self.communicator.print_log_signal.emit("停利出場 "+content.stock_no+": "+str(content.filled_qty)+"股, 成交價:"+str(content.filled_price)+", 剩餘: "+remain_qty_str+"股")
                            
                            self.communicator.item_update_signal.emit(inv_item.row(), self.col_idx_map['庫存股數'], remain_qty_str)
                            avg_item = self.tablewidget.item(self.row_idx_map[content.stock_no], self.col_idx_map['庫存均價'])
                            avg_price = float(avg_item.text())
                            new_pnl = (content.filled_price-avg_price)*remain_qty
                            new_cost = avg_price*remain_qty
                            new_rate_return = new_pnl/new_cost*100

                            # update row
                            self.communicator.item_update_signal.emit(self.row_idx_map[content.stock_no], self.col_idx_map['庫存股數'], str(remain_qty))
                            self.communicator.item_update_signal.emit(self.row_idx_map[content.stock_no], self.col_idx_map['現價'], str(round(content.filled_price+self.epsilon, 2)))
                            self.communicator.item_update_signal.emit(self.row_idx_map[content.stock_no], self.col_idx_map['損益試算'], str(round(new_pnl+self.epsilon, 2)))
                            self.communicator.item_update_signal.emit(self.row_idx_map[content.stock_no], self.col_idx_map['獲利率%'], str(round(new_rate_return+self.epsilon, 2))+"%")

                        elif remain_qty == 0:
                            # del table row and unsubscribe
                            self.communicator.del_row_signal.emit(self.row_idx_map[content.stock_no])

                            if content.stock_no in self.stop_loss_dict:
                                self.stop_loss_dict.pop(content.stock_no)
                            if content.stock_no in self.take_profit_dict:
                                self.take_profit_dict.pop(content.stock_no)
                            if content.stock_no in self.subscribed_ids:
                                self.wsstock.unsubscribe({
                                    'id':self.subscribed_ids[content.stock_no]
                                })
                            
                            if content.user_def == "inv_SL":
                                self.communicator.print_log_signal.emit("停損出場 "+content.stock_no+": "+str(content.filled_qty)+"股, 成交價:"+str(content.filled_price))
                            elif content.user_def == "inv_TP":
                                self.communicator.print_log_signal.emit("停利出場 "+content.stock_no+": "+str(content.filled_qty)+"股, 成交價:"+str(content.filled_price))
                            else:
                                self.communicator.print_log_signal.emit("手動出場 "+content.stock_no+": "+str(content.filled_qty)+"股, 成交價:"+str(content.filled_price))

                            print("deleting...")
                            while content.stock_no in self.row_idx_map:
                                print("deleting...", content.stock_no)
                                pass
                            print("deleting done")
                        
                            self.inventories.pop((content.stock_no, str(content.order_type)))
                            
                            try:
                                self.is_ordered.remove(content.stock_no)
                            except ValueError as v_err:
                                print("not in is_ordered", v_err)
            # print("filled unlock", content.stock_no)
            self.mutex.unlock()

    # 測試用假裝有websocket data的按鈕slot function
    def fake_ws_data(self):
        if self.fake_price_cnt % 2==0:
            self.price_interval = 0
            self.fake_ws_timer = RepeatTimer(1, self.fake_message)
            self.fake_ws_timer.start()
        else:
            self.fake_ws_timer.cancel()

        self.fake_price_cnt+=1

    def fake_message(self):
        self.price_interval+=1
        stock_list = ['2330', '2881', '2454', '00940', '1101', '6598', '2509', '3230', '4903', '6661']
        json_template = '''{{"event":"data","data":{{"symbol":"{symbol}","type":"EQUITY","exchange":"TWSE","market":"TSE","price":{price},"size":713,"bid":16.67,"ask":{price}, "isLimitUpAsk":true, "volume":8066,"isClose":true,"time":1718343000000000,"serial":9475857}},"id":"w4mkzAqYAYFKyEBLyEjmHEoNADpwKjUJmqg02G3OC9YmV","channel":"trades"}}'''
        json_price = 15+self.price_interval
        json_str = json_template.format(symbol=stock_list[self.price_interval % len(stock_list)], price=str(json_price))
        self.handle_message(json_str)

    # 更新表格內某一格值的slot function
    def item_update(self, row, col, value):
        try:
            self.tablewidget.item(row, col).setText(value)
        except Exception as e:
            print(e, row, col, value)

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
                    print("stop loss:", self.stop_loss_dict)
                    return
                
                cur_price = self.tablewidget.item(item.row(), self.col_idx_map['現價']).text()
                cur_price = float(cur_price)
                if cur_price <= item_price or 0 >= item_price:
                    self.print_log("請輸入正確價格，停損價格必須小於現價並大於0")
                    item.setCheckState(Qt.Unchecked)
                else:
                    self.stop_loss_dict[symbol] = item_price
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                    self.print_log(symbol+"...停損設定成功: "+item_str)
                    
                print("stop loss:", self.stop_loss_dict)

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
                    print("take profit:", self.take_profit_dict)
                    return
                
                cur_price = self.tablewidget.item(item.row(), self.col_idx_map['現價']).text()
                cur_price = float(cur_price)
                if cur_price >= item_price:
                    self.print_log("請輸入正確價格，停利價格必須大於現價")
                    item.setCheckState(Qt.Unchecked)
                else:
                    self.take_profit_dict[symbol] = item_price
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                    self.print_log(symbol+"...停利設定成功: "+item_str)
                    
                print("take profit:", self.take_profit_dict)

        elif item.checkState() == Qt.Unchecked:
            if item.column() == self.col_idx_map['停損']:
                item.setFlags(item.flags() | Qt.ItemIsEditable)
                symbol = self.tablewidget.item(item.row(), self.col_idx_map['股票代號']).text()
                if symbol in self.stop_loss_dict:
                    self.stop_loss_dict.pop(symbol)
                    self.print_log(symbol+"...移除停損，請重新設置")
                    print("stop loss:", self.stop_loss_dict)

            elif item.column() == self.col_idx_map['停利']:
                item.setFlags(item.flags() | Qt.ItemIsEditable)
                symbol = self.tablewidget.item(item.row(), self.col_idx_map['股票代號']).text()
                if symbol in self.take_profit_dict:
                    self.take_profit_dict.pop(symbol)
                    self.print_log(symbol+"...移除停利，請重新設置")
                    print("take profit:", self.take_profit_dict)

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

        order_res = sdk.stock.place_order(active_account, order)
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
        elif event == "data":
            if 'isTrial' in data:
                if data['isTrial']:
                    return
            
            # print('handle_message get lock', data['symbol'])
            self.mutex.lock()
            
            symbol = data["symbol"]
            
            if symbol not in self.row_idx_map:
                # print("not in unlock")
                self.mutex.unlock()
                return
            
            if 'price' in data:
                cur_price = data["price"]
            else:
                self.mutex.unlock()
                return
                     
            self.communicator.item_update_signal.emit(self.row_idx_map[symbol], self.col_idx_map['現價'], str(cur_price))
        
            avg_price_item = self.tablewidget.item(self.row_idx_map[symbol], self.col_idx_map['庫存均價'])
            avg_price = avg_price_item.text()
        
            share_item = self.tablewidget.item(self.row_idx_map[symbol], self.col_idx_map['庫存股數'])
            share = share_item.text()
        
            cur_pnl = (cur_price-float(avg_price))*float(share)
            self.communicator.item_update_signal.emit(self.row_idx_map[symbol], self.col_idx_map['損益試算'], str(int(round(cur_pnl, 0))))
        
            return_rate = cur_pnl/(float(avg_price)*float(share))*100
            self.communicator.item_update_signal.emit(self.row_idx_map[symbol], self.col_idx_map['獲利率%'], str(round(return_rate+self.epsilon, 2))+'%')
            
            if symbol in self.stop_loss_dict:
                if cur_price <= self.stop_loss_dict[symbol] and symbol not in self.is_ordered:
                    self.communicator.print_log_signal.emit(symbol+"...停損市價單發送...")
                    sl_res = self.sell_market_order(symbol, share, "inv_SL")
                    if sl_res.is_success:
                        self.communicator.print_log_signal.emit(symbol+"...停損市價單發送成功，單號: "+sl_res.data.order_no)
                        self.is_ordered.append(symbol)
                    else:
                        self.communicator.print_log_signal.emit(symbol+"...停損市價單發送失敗...")
                        self.communicator.print_log_signal.emit(sl_res.message)
                elif symbol in self.is_ordered:
                    self.communicator.print_log_signal.emit(symbol+"...停損市價單已發送過...")
            if symbol in self.take_profit_dict:
                if cur_price >= self.take_profit_dict[symbol] and symbol not in self.is_ordered:
                    self.communicator.print_log_signal.emit(symbol+"...停利市價單發送...")
                    tp_res = self.sell_market_order(symbol, share, "inv_TP")
                    if tp_res.is_success:
                        self.communicator.print_log_signal.emit(symbol+"...停利市價單發送成功，單號: "+tp_res.data.order_no)
                        self.is_ordered.append(symbol)
                    else:
                        self.communicator.print_log_signal.emit(symbol+"...停利市價單發送失敗...")
                        self.communicator.print_log_signal.emit(tp_res.message)
                elif symbol in self.is_ordered:
                    self.communicator.print_log_signal.emit(symbol+"...停利市價單已發送過...")
            
            # print('handle_message release lock', symbol)
            self.mutex.unlock()
            
    def handle_connect(self):
        self.communicator.print_log_signal.emit('market data connected')
    
    def handle_disconnect(self, code, message):
        self.communicator.print_log_signal.emit(f'market data disconnect: {code}, {message}')
        self.mutex.unlock()
    
    def handle_error(self, error):
        self.communicator.print_log_signal.emit(f'market data error: {error}')
        self.mutex.unlock()

    # 視窗啟動時撈取對應帳號的inventories和unrealized_pnl初始化表格
    def table_init(self):
        inv_res = sdk.accounting.inventories(active_account)
        if inv_res.is_success:
            self.print_log("庫存抓取成功")
            inv_data = inv_res.data
            for inv in inv_data:
                if inv.today_qty != 0 and inv.order_type == OrderType.Stock:
                    self.inventories[(inv.stock_no, str(inv.order_type))] = inv
        else:
            self.print_log("庫存抓取失敗")
        
        self.print_log("抓取未實現損益...")
        upnl_res = sdk.accounting.unrealized_gains_and_loses(active_account)
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

        # 調整股票名稱欄位寬度
        header = self.tablewidget.horizontalHeader()      
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        print(self.row_idx_map)
        print(self.col_idx_map)

    def on_button_start_clicked(self):
        try:
            self.default_sl_percent = float(self.lineEdit_default_sl.text())*0.01
            if self.default_sl_percent > 0:
                self.print_log("請輸入正確的監控停損(%), 範圍需小於0, 0為不預設")
                return
            elif self.default_sl_percent == 0:
                self.print_log("預設停損輸入為0, 不預設停損")
            else:
                self.print_log("預設停損"+str(self.default_sl_percent)+"%, 設定成功")
        except Exception as e:
            self.print_log("請輸入正確的監控停損(%), 範圍需小於0, 0為不預設 "+str(e))
            return
        
        try:
            self.default_tp_percent = float(self.lineEdit_default_tp.text())*0.01
            if self.default_tp_percent < 0:
                self.print_log("請輸入正確的監控停利(%), 範圍需大於0, 0為不預設")
                return
            elif self.default_tp_percent == 0:
                self.print_log("預設停利輸入為0, 不預設停利")
            else:
                self.print_log("預設停利"+str(self.default_tp_percent)+"%, 設定成功")
        except Exception as e:
            self.print_log("請輸入正確的監控停利(%), 範圍需大於0, 0為不預設 "+str(e))
            return
        
        self.print_log("開始執行監控")
        self.lineEdit_default_sl.setReadOnly(True)
        self.lineEdit_default_tp.setReadOnly(True)
        self.button_start.setVisible(False)
        self.button_stop.setVisible(True)
        self.tablewidget.clearContents()
        self.tablewidget.setRowCount(0)

        self.print_log("建立WebSocket行情連線")
        sdk.init_realtime()
        self.wsstock = sdk.marketdata.websocket_client.stock
        self.wsstock.on("connect", self.handle_connect)
        self.wsstock.on("disconnect", self.handle_disconnect)
        self.wsstock.on("error", self.handle_error)
        self.wsstock.on('message', self.handle_message)
        self.wsstock.connect()

        self.print_log("抓取庫存...")
        self.table_init()
        sdk.set_on_filled(self.on_filled)

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

    # 更新最新log到QPlainTextEdit的slot function
    def print_log(self, log_info):
        self.log_text.appendPlainText(log_info)
        self.log_text.moveCursor(QTextCursor.End)
    
    # 視窗關閉時要做的事，主要是關websocket連結
    def closeEvent(self, event):
        # do stuff
        self.print_log("disconnect websocket...")
        self.wsstock.disconnect()
        sdk.logout()

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