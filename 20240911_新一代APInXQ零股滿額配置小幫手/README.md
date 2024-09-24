# Python 零股滿額配置小幫手(GUI應用)

---
> ## **Disclaimer: 範例程式碼及執行檔僅供教學與參考之用，實務交易應自行評估並承擔相關風險**
> 
---

本程式碼為富邦新一代API & XQ化學反應(3-1)線上講座範例，示範如何應用新一代API零股功能在投資組合換股時做到滿額配置，即便只有1萬元也可以開始做投資組合<br> 
功能涵蓋如下:
* py_exe<br>
  本資料夾底下涵蓋編譯好的教學範例執行檔和執行需要的資源，可以直接開啟**Python投資組合滿額配置小幫手(教學範例，僅限現股).exe**做使用
* fraction_portfolio.py<br>
  **本檔案為主要程式也是執行檔原碼**，GUI套件使用Pyside6，Python版本須為3.11，有任何需求都可以從這邊做修正，直接執行本程式碼即可看到GUI畫面
  * 目前配置僅支援現股，有其他需要需自行更改
  * 損益試算無考慮成本，損益請以對帳單為準
* fraction_portfolio.spec<br>
  pyinstaller編譯執行檔用的描述檔，如想編出與範例一致的執行檔，請使用本描述檔操作
* login_gui.py<br>
  登入介面物件，可用於簽署及登錄API
     
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
> 憑證密碼 = #憑證密碼(如為預設密碼憑證，此欄請留白)<br>
> 交易帳號 = #不須分公司代碼之交易帳號(ex. 9801234)<br>

## 主程式設定
* Step 1. 先選取持有目標清單之路徑
* Step 2. 讀取清單，確認持有目標無誤
* Step 3. 設定配置金額，並做"下單試算"
* Step 4. 確認委託價格(預設為漲停買，跌停賣亦可於表格上直接修改)及數量無誤
* Step 5. 開始下單，並等待置委託數量均成功成交
* Step 6. 使用右上角"x"正確關閉程式，會於關閉時儲存當前持有結果

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

