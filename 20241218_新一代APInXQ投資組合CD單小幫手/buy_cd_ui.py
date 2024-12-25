from PySide6.QtWidgets import QTableWidgetItem, QFileDialog, QApplication, QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QGridLayout, QLabel, QLineEdit, QPushButton, QSizePolicy, QPlainTextEdit
from PySide6.QtGui import QIcon, QTextCursor
from PySide6.QtCore import Qt, Signal, QObject

class main_ui(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Python投資組合分時分量小幫手(教學範例)")
        self.resize(1200, 700)

        # 製作上下排列layout上為庫存表，下為log資訊
        layout = QVBoxLayout()

        title_font_size = "20px"

        layout_table = QVBoxLayout()
        cur_pos_title = QLabel('現在持有部位')
        cur_pos_title.setStyleSheet(f"QLabel {{ font-size: {title_font_size}; font-weight: bold; }}")

        new_pos_title = QLabel('目標持有部位')
        new_pos_title.setStyleSheet(f"QLabel {{ font-size: {title_font_size}; font-weight: bold; }}")
        
        # 庫存表表頭
        self.cur_pos_header = ['股票名稱', '股票代號', '庫存股數', '庫存均價', '現價', '損益試算', '獲利率%', '委託數量', '委託價格', '成交數量', '成交價格']
        self.new_pos_header = ['股票名稱', '股票代號', '參考價', '現價', '漲幅(%)', '目標股數', '委託數量', '委託價格', '成交數量', '成交價格']
        
        self.cur_pos_table = QTableWidget(0, len(self.cur_pos_header))
        self.cur_pos_table.setHorizontalHeaderLabels([f'{item}' for item in self.cur_pos_header])

        self.new_pos_table = QTableWidget(0, len(self.new_pos_header))
        self.new_pos_table.setHorizontalHeaderLabels([f'{item}' for item in self.new_pos_header])

        layout_table.addWidget(cur_pos_title, stretch=1)
        layout_table.addWidget(self.cur_pos_table, stretch=9)
        layout_table.addWidget(new_pos_title, stretch=1)
        layout_table.addWidget(self.new_pos_table, stretch=9)
        
        # 整個設定區layout
        layout_parameter = QGridLayout()

        # 參數設置區layout設定
        label_input_title = QLabel('配置參數設定')
        label_input_title.setStyleSheet(f"QLabel {{ font-size: {title_font_size}; font-weight: bold; }}")
        label_input_title.setAlignment(Qt.AlignCenter)
        layout_parameter.addWidget(label_input_title, 0, 0)

        label_total_amount = QLabel('配置總金額:')
        layout_parameter.addWidget(label_total_amount, 1, 0)
        label_total_amount.setAlignment(Qt.AlignRight)
        self.lineEdit_default_total_amount = QLineEdit()
        self.lineEdit_default_total_amount.setText('10')
        layout_parameter.addWidget(self.lineEdit_default_total_amount, 1, 1)
        label_total_amount_post = QLabel('萬元  ')
        layout_parameter.addWidget(label_total_amount_post, 1, 2)

        label_order_period = QLabel('下單時長(分):')
        layout_parameter.addWidget(label_order_period, 2, 0)
        label_order_period.setAlignment(Qt.AlignRight)
        self.lineEdit_order_period = QLineEdit()
        self.lineEdit_order_period.setText('10')
        layout_parameter.addWidget(self.lineEdit_order_period, 2, 1)
        label_order_period_post = QLabel('分鐘')
        layout_parameter.addWidget(label_order_period_post, 2, 2)

        label_order_times = QLabel('分批次數:')
        layout_parameter.addWidget(label_order_times, 3, 0)
        label_order_times.setAlignment(Qt.AlignRight)
        self.lineEdit_order_times = QLineEdit()
        self.lineEdit_order_times.setText('1')
        layout_parameter.addWidget(self.lineEdit_order_times, 3, 1)
        label_order_times_post = QLabel('次')
        layout_parameter.addWidget(label_order_times_post, 3, 2)

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
        label_sim.setStyleSheet(f"QLabel {{ font-size: {title_font_size}; font-weight: bold; }}")
        label_sim.setAlignment(Qt.AlignCenter)
        layout_sim.addWidget(label_sim, 0, 1)
        layout_sim.addWidget(self.button_fake_buy_filled, 1, 0)
        layout_sim.addWidget(self.button_fake_sell_filled, 1, 1)
        layout_sim.addWidget(self.button_fake_websocket, 1, 2)
        
        self.log_text = QPlainTextEdit()
        self.log_text.setReadOnly(True)

        layout.addLayout(layout_table)
        layout.addLayout(layout_parameter)
        layout.addLayout(layout_sim)
        layout.addWidget(self.log_text)

        layout.setStretchFactor(layout_table, 7)
        layout.setStretchFactor(layout_parameter, 3)
        layout.setStretchFactor(layout_sim, 1)
        layout.setStretchFactor(self.log_text, 2)

        self.setLayout(layout)