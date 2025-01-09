### Layout 設定
import sys

from PySide6.QtWidgets import QApplication, QWidget, QPushButton, QLabel, QLineEdit, QGridLayout, QVBoxLayout, QTableWidget, QPlainTextEdit, QSizePolicy
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt

class MyUI(QWidget):
    def __init__(self):
        super().__init__()

        my_icon = QIcon()
        my_icon.addFile('breakout.ico')

        self.setWindowIcon(my_icon)
        self.setWindowTitle("Python自選清單突破買進小幫手")
        self.resize(1000, 600)

        # 製作上下排列layout上為庫存表，下為log資訊
        layout = QVBoxLayout()
        # 庫存表表頭
        self.table_header = ['股票名稱', '股票代號', '上市櫃', '成交', '買進', '賣出', '漲幅(%)', '委託數量', '成交數量']
        
        label_program_name = QLabel("突破買進小幫手(百分比版，教學範例)")
        label_program_name.setStyleSheet("color: red; font-size: 24px; font-weight: bold;")

        self.tablewidget = QTableWidget(0, len(self.table_header))
        self.tablewidget.setHorizontalHeaderLabels([f'{item}' for item in self.table_header])
        self.tablewidget.setEditTriggers(QTableWidget.NoEditTriggers)

        #讀取區layout
        layout_read_file = QGridLayout()

        #清單讀取
        label_file_path = QLabel('清單路徑:')
        label_file_path.setStyleSheet("QLabel { font-weight: bold; }")
        label_file_path.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        layout_read_file.addWidget(label_file_path, 0, 0)
        self.lineEdit_default_file_path = QLineEdit()
        layout_read_file.addWidget(self.lineEdit_default_file_path, 0, 1, 1, 4)
        self.folder_btn = QPushButton('')
        self.folder_btn.setIcon(QIcon('folder.png'))
        self.folder_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        layout_read_file.addWidget(self.folder_btn, 0, 5)

        self.read_csv_btn = QPushButton('')
        self.read_csv_btn.setText('讀取清單')
        self.read_csv_btn.setStyleSheet("QPushButton { font-weight: bold; }")
        self.read_csv_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        layout_read_file.addWidget(self.read_csv_btn, 0, 6)

        label_dummy = QLabel(' '*60)
        layout_read_file.addWidget(label_dummy, 0, 7)

        # 整個設定區layout
        layout_condition = QGridLayout()

        # 交易區layout
        label_trade = QLabel('交易設定:')
        label_trade.setStyleSheet("QLabel { font-weight: bold; }")
        layout_condition.addWidget(label_trade, 1, 0)
        label_trade_budget = QLabel('每檔額度')
        layout_condition.addWidget(label_trade_budget, 2, 0)
        self.lineEdit_trade_budget = QLineEdit()
        self.lineEdit_trade_budget.setText('0.1')
        layout_condition.addWidget(self.lineEdit_trade_budget, 2, 1)
        label_trade_budget_post = QLabel('萬元')
        layout_condition.addWidget(label_trade_budget_post, 2, 2)
        label_total_budget = QLabel('總額度')
        layout_condition.addWidget(label_total_budget, 3, 0)
        self.lineEdit_total_budget = QLineEdit()
        self.lineEdit_total_budget.setText('0.1')
        layout_condition.addWidget(self.lineEdit_total_budget, 3, 1)
        label_total_budget_post = QLabel('萬元')
        layout_condition.addWidget(label_total_budget_post, 3, 2)
        
        label_total_volume = QLabel('交易量>=')
        layout_condition.addWidget(label_total_volume, 2, 3)
        self.lineEdit_total_volume = QLineEdit()
        self.lineEdit_total_volume.setText('0')
        layout_condition.addWidget(self.lineEdit_total_volume, 2, 4)
        label_total_volume_post = QLabel('張')
        layout_condition.addWidget(label_total_volume_post, 2, 5)

        label_change_percent = QLabel('漲幅(%)>=')
        layout_condition.addWidget(label_change_percent, 3, 3)
        self.lineEdit_change_percent = QLineEdit()
        self.lineEdit_change_percent.setText('100')
        layout_condition.addWidget(self.lineEdit_change_percent, 3, 4)
        label_change_percent_post = QLabel('%')
        layout_condition.addWidget(label_change_percent_post, 3, 5)

        # 啟動按鈕
        self.button_start = QPushButton('開始洗價')
        self.button_start.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.button_start.setStyleSheet("QPushButton { font-size: 24px; font-weight: bold; }")
        layout_condition.addWidget(self.button_start, 1, 9, 3, 1)

        # 停止按鈕
        self.button_stop = QPushButton('停止洗價')
        self.button_stop.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.button_stop.setStyleSheet("QPushButton { font-size: 24px; font-weight: bold; }")
        layout_condition.addWidget(self.button_stop, 1, 9, 3, 1)
        self.button_stop.setVisible(False)
        
        # 模擬區Layout設定
        self.button_fake_buy_filled = QPushButton('fake buy filled')
        self.button_fake_websocket = QPushButton('fake websocket')
        
        layout_sim = QGridLayout()
        label_sim = QLabel('測試用按鈕')
        label_sim.setStyleSheet("QLabel { font-size: 24px; font-weight: bold; }")
        label_sim.setAlignment(Qt.AlignCenter)
        layout_sim.addWidget(label_sim, 0, 0, 1, 2)
        layout_sim.addWidget(self.button_fake_buy_filled, 1, 0)
        layout_sim.addWidget(self.button_fake_websocket, 1, 1)
        
        # Log區Layout設定
        self.log_text = QPlainTextEdit()
        self.log_text.setReadOnly(True)
        
        layout.addWidget(label_program_name, stretch=0)
        layout.addWidget(self.tablewidget, stretch=7)
        layout.addLayout(layout_read_file, stretch=1)
        layout.addLayout(layout_condition, stretch=1)
        layout.addLayout(layout_sim, stretch=1)
        layout.addWidget(self.log_text, stretch=3)

        self.setLayout(layout)

if __name__ == "__main__":
    if not QApplication.instance():
        app = QApplication(sys.argv)
    else:
        app = QApplication.instance()
    
    app.setStyleSheet("QWidget{font-size: 12pt;}")
    ui = MyUI()
    ui.show()
    sys.exit(app.exec())