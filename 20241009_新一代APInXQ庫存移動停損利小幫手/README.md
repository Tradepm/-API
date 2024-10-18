# Python 庫存移動停損利小幫手(GUI應用)

---
> ## **Disclaimer: 範例程式碼及執行檔僅供教學與參考之用，實務交易應自行評估並承擔相關風險**
> 
---

本程式碼為富邦新一代API & XQ化學反應(2-2)線上講座範例，示範如何應用新一代API搭配雲端條件單做庫存的移動停損利<br> 
功能涵蓋如下:
* py_exe<br>
  本資料夾底下涵蓋編譯好的教學範例執行檔和執行需要的資源，可以直接開啟**Python庫存移動停損利小幫手(教學範例，僅限現股).exe**做使用
* trail_stop_with_cloud.py<br>
  **本檔案為主要程式也是執行檔原碼**，GUI套件使用Pyside6，SDK版本為2.0.1，Python版本可為3.8~3.12，有任何需求都可以從這邊做修正，直接執行本程式碼即可看到GUI畫面
  * 目前配置僅支援現股買進的移動停損利設置，有其他需要請自行修改
  * 預設只需輸入當下移停%數即會發送對應條件單
  * 執行日期區間請以條件單查詢結果為準
* trail_stop_with_cloud.spec<br>
  pyinstaller編譯執行檔用的描述檔，如想編出與範例一致的執行檔，請使用本描述檔操作
* login_gui_v1.py<br>
  * Fubon SDK 2.0.1 已可支援預設憑證密碼登入，於憑證密碼欄位處留白即可
     
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
  * Discord: https://discord.com/invite/M8Gv9yKfza

## 登入設定
在程式登入畫面中請使用以下設定
> 身份證字號 = #身份證字號(ex. A123456789)<br>
> 交易密碼 = #交易密碼<br>
> 憑證路徑= #憑證路徑(可使用按鈕選取憑證檔案，會自動帶入路徑)<br>
> 憑證密碼 = #憑證密碼(如為預設密碼憑證，此欄請留白)<br>
> 交易帳號 = #不須分公司代碼之交易帳號(ex. 9801234)<br>

## 主程式設定
* Step 1. 移停(%)欄位直接輸入預計使用的%數
* Step 2. 輸入無誤，勾選後即會自動送出對應條件單
* Step 3. 確認相關基準價、觸發價、設定股數是否與預期一致

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
pip install fubon_neo-x.x.x-cp37-abi3-win_amd64
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

