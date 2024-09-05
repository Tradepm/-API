# Python & XQ 搶漲停強化版(GUI應用)

---
> ## **Disclaimer: 範例程式碼及執行檔僅供教學與參考之用，實務交易應自行評估並承擔相關風險**
> 
---

本程式碼為富邦新一代API & XQ化學反應(1-1)線上講座範例，示範如何應用 XQ 及 Python 自動化搶漲停的同時做總額度資金控管及篩選成交量門檻<br> 
功能涵蓋如下:
* py_exe<br>
  本資料夾底下涵蓋編譯好的教學範例執行檔和執行需要的資源，可以直接開啟**Python搶漲停強化版(教學範例，僅供參考).exe**做使用
* rlu_with_volume_n_budget.py<br>
  **本檔案為主要程式也是執行檔原碼**，GUI套件使用Pyside6，Python版本須為3.11，有任何需求都可以從這邊做修正，直接執行本程式碼即可看到GUI畫面，與執行檔畫面一致，總額度限制為"委託額度限制"使用時再多加留意
* rlu_with_volume_n_budget.spec<br>
  pyinstaller編譯執行檔用的描述檔，如想編出與範例一致的執行檔，請使用本描述檔操作
     
## 參考連結
富邦新一代API Python SDK載點及開發說明文件
* 新一代API SDK 載點<br>
https://www.fbs.com.tw/TradeAPI/docs/download/download-sdk
* 新一代API 開發說明文件<br>
https://www.fbs.com.tw/TradeAPI/docs/trading/introduction 
* 新一代API & XQ社群討論<br>
  * Line: https://reurl.cc/dnMxlV
  * Discord: https://discord.com/invite/VHjjc4C

## 登入設定
在程式登入畫面中請使用以下設定
> Your ID= #身份證字號<br>
> Password= #交易密碼<br>
> Cert path= #憑證路徑(可使用按鈕選取憑證檔案，會自動帶入路徑)<br>
> Cert Password= #憑證密碼<br>
> Account= #交易帳號<br>

## 主程式設定
* Step 1. 先設定目標清單路徑
* Step 2. 點擊"讀取檔案"按鈕，讀取目標清單
* Step 3. 點擊"下單試算"按鈕，針對委託價格試算委託張數
* Step 4. 點擊"開始下單"按鈕，會依據畫面上所顯示的委託價格及張數做下單動作

## Pyinstaller 編譯執行檔設定
建議使用conda指令安裝pyinstaller減少環境問題<br>
```
conda install pyinstaller
```
若想編譯與教學範例一致之執行檔，請先將login_gui.py、rlu_with_volume_n_budget.py、rlu_with_volume_n_budget.spec、fast_icon.ico等檔案移至同一資料夾，並用指令如下<br>
```
pyinstaller swing_trade.spec
```
編譯完成後，應會出現單個執行檔在dist資料夾內<br>
若想由原始碼編譯，建議使用以下指令進行單檔打包，在部署到其他裝置時會比較容易
```
pyinstaller -F swing_trade.py
```
pyinstaller會自動產生新的rlu_with_volume_n_budget.spec，可以再依自己的喜好調整參數
