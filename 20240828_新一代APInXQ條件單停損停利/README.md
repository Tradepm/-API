# Python 條件單停損停利(GUI應用)

---
> ## **Disclaimer: 範例程式碼及執行檔僅供教學與參考之用，實務交易應自行評估並承擔相關風險**
> 
---

本程式碼為富邦新一代API & XQ化學反應(3-1)線上講座範例，示範如何應用 Python 做條件單的停損停利<br> 
功能涵蓋如下:
* py_exe<br>
  本資料夾底下涵蓋編譯好的教學範例執行檔和執行需要的資源，可以直接開啟**Python條件單庫存停損停利(教學範例，僅限現股).exe**做使用
* tp_sl_with_conditional_order.py<br>
  **本檔案為主要程式也是執行檔原碼**，GUI套件使用Pyside6，Python版本須為3.11，有任何需求都可以從這邊做修正，直接執行本程式碼即可看到GUI畫面
  * 目前停損停利僅支援現股，有其他需要需自行更改
  * 停損停利以條件單丟出，只要成功送出即使關閉程式仍會洗價
  * 部位若無變動隔夜仍會自動根據存下的status帶入停損停利畫面
  * 觸發條件單時若有開啟程式，會自動進行OCO刪單
* tp_sl_with_conditional_order.spec<br>
  pyinstaller編譯執行檔用的描述檔，如想編出與範例一致的執行檔，請使用本描述檔操作
* login_gui.py<br>
  登入介面物件，可用於簽署及登錄API
* auto_save_dict.py<br>
  自行改寫之dictionary物件，會在dictionary有新增或刪除的變動時自動存檔
     
## 參考連結
富邦新一代API Python SDK載點及開發說明文件
* 新一代API SDK 載點<br>
https://www.fbs.com.tw/TradeAPI/docs/download/download-sdk
* 新一代API 條件單說明文件<br>
https://www.fbs.com.tw/TradeAPI/docs/smart-condition/introduction/
* 新一代API 開發說明文件<br>
https://www.fbs.com.tw/TradeAPI/docs/trading/introduction 
* 新一代API & XQ社群討論<br>
  * Line: https://reurl.cc/dnMxlV
  * Discord: https://discord.com/invite/VHjjc4C

## 登入設定
在程式登入畫面中請使用以下設定
> 身份證字號 = #身份證字號(ex. A123456789)<br>
> 交易密碼 = #交易密碼<br>
> 憑證路徑= #憑證路徑(可使用按鈕選取憑證檔案，會自動帶入路徑)<br>
> 憑證密碼 = #憑證密碼(請使用自行輸入密碼之憑證，勿用預設密碼之憑證)<br>
> 交易帳號 = #不須分公司代碼之交易帳號(ex. 9801234)<br>

## 主程式設定
* Step 1. 預設停損請輸入小於等於0之數字，停損將以%數計算，0為不預設停損
* Step 2. 預設停利請輸入大於等於0之數字，停利將以%數計算，0為不預設停利
* Step 3. 點擊"開始監控"按鈕，即會帶入庫存並在出現新部位時以新部位成交價做預設停損利計算
* Step 4. 停損停利輸入後勾選即可發出停損利之條件觸價單，可至Online做對照查單
* Step 5. 程式會記錄所設之停損利並於下次開啟時帶入，若程式關閉時有發生部位異動，請自行確認部位與停損利條件單是否同步

## Pyinstaller 編譯執行檔設定
【pyinstaller 步驟教學】
建議如有想要自行編譯執行檔，使用的又是anaconda的話，按以下步驟嘗試
1. 使用conda先創建一個python 3.11的虛擬環境(envName)可代換為你想要的任何名稱
```
conda create --name [envName] python=3.11
```
2. 啟動該環境
```
conda activate [envName]
```
3. 在envName環境下僅安裝跑原始碼所需的必要套件(以下所列為rlu_with_volume_n_budget.py所需)
```
pip install pandas
pip install requests
pip install PySide6
pip install fubon_neo-1.3.1-cp37-abi3-win_amd64
```
4. 在envName環境下嘗試執行原始碼，如果成功可前往下一步，若失敗請依據所缺套件再行安裝
5. 在envName環境下安裝pyinstaller(請務必使用conda install)
```
conda install pyinstaller
```
6. 編譯原始碼(請記得使用-F編譯)
```
pyinstaller -F example.py
```

