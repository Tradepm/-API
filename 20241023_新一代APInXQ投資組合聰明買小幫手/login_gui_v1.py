import sys
import pickle
import json
from pathlib import Path

from fubon_neo.sdk import FubonSDK

from PySide6.QtWidgets import QApplication, QWidget, QPushButton, QLabel, QLineEdit, QGridLayout, QVBoxLayout, QMessageBox, QFileDialog
from PySide6.QtGui import QIcon

class LoginForm(QWidget):
    def __init__(self, MainApp, fubon_sdk, icon_path='default.png'):
        super().__init__()

        self.main_app_object = MainApp
        self.sdk = fubon_sdk
        self.icon_path = icon_path

        my_icon = QIcon()
        my_icon.addFile(self.icon_path)

        self.setWindowIcon(my_icon)
        self.setWindowTitle('新一代API登入')
        self.resize(500, 200)
        
        layout_all = QVBoxLayout()

        label_warning = QLabel('本範例僅供教學參考，使用前請先了解相關內容')
        layout_all.addWidget(label_warning)

        layout = QGridLayout()

        label_your_id = QLabel('身份證字號:')
        self.lineEdit_id = QLineEdit()
        self.lineEdit_id.setPlaceholderText('請輸入身份證字號')
        layout.addWidget(label_your_id, 0, 0)
        layout.addWidget(self.lineEdit_id, 0, 1)

        label_password = QLabel('登入密碼:')
        self.lineEdit_password = QLineEdit()
        self.lineEdit_password.setPlaceholderText('請輸入登入密碼')
        self.lineEdit_password.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(label_password, 1, 0)
        layout.addWidget(self.lineEdit_password, 1, 1)

        label_cert_path = QLabel('憑證路徑:')
        self.lineEdit_cert_path = QLineEdit()
        self.lineEdit_cert_path.setPlaceholderText('請選擇憑證路徑')
        layout.addWidget(label_cert_path, 2, 0)
        layout.addWidget(self.lineEdit_cert_path, 2, 1)
        
        label_cert_pwd = QLabel('憑證密碼:')
        self.lineEdit_cert_pwd = QLineEdit()
        self.lineEdit_cert_pwd.setPlaceholderText('若為預設憑證密碼請留白')
        self.lineEdit_cert_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(label_cert_pwd, 3, 0)
        layout.addWidget(self.lineEdit_cert_pwd, 3, 1)

        label_acc = QLabel('帳號:')
        self.lineEdit_acc = QLineEdit()
        self.lineEdit_acc.setPlaceholderText('請輸入欲用來交易之帳號')
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
        
        login_btn.clicked.connect(self.check_password)
        folder_btn.clicked.connect(self.showDialog)
        
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
        self.active_account = None
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

        if cert_pwd == "":
            accounts = self.sdk.login(fubon_id, fubon_pwd, Path(cert_path).__str__())
        else:
            accounts = self.sdk.login(fubon_id, fubon_pwd, Path(cert_path).__str__(), cert_pwd)

        if accounts.is_success:
            for cur_account in accounts.data:
                if cur_account.account == target_account:
                    self.active_account = cur_account
                    with open('info.pkl', 'wb') as f:
                        pickle.dump(user_info_dict, f)
                    
                    self.main_app = self.main_app_object(self.sdk, self.active_account, self.icon_path)
                    self.main_app.show()
                    self.close()

                elif target_account[0] == '0':
                    if cur_account.account == target_account[1:]:
                        self.active_account = cur_account
                        with open('info.pkl', 'wb') as f:
                            pickle.dump(user_info_dict, f)

                    self.main_app = self.main_app_object(self.sdk, self.active_account, self.icon_path)
                    self.main_app.show()
                    self.close()
                    
            if self.active_account == None:
                self.sdk.logout()
                msg.setWindowTitle("登入失敗")
                msg.setText("找不到您輸入的帳號")
                msg.exec()
        else:
            msg.setWindowTitle("登入失敗")
            msg.setText(accounts.message)
            msg.exec()

class MainApp(QWidget):
    def __init__(self, active_account):
        super().__init__()

        self.active_account = active_account
        self.setWindowTitle("Python教學範例")
        self.resize(1200, 600)

if __name__ == "__main__":
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
    form = LoginForm(MainApp, sdk)
    form.show()
    
    sys.exit(app.exec())