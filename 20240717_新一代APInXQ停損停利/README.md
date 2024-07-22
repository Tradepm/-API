# Python & XQ 庫存停損停利範例教學程式(GUI應用)

---
> ## **Disclaimer: 範例程式碼及執行檔僅供教學與參考之用，實務交易應自行評估並承擔相關風險**
> 
---

本程式碼為富邦新一代API & XQ化學反應(二)線上講座範例，示範如何應用 XQ 及 Python 執行庫存停損停利，Python 會以 GUI 工具製作自己的搶漲停圖形化介面程式<br> 
功能涵蓋如下:
* py_exe<br>
  本資料夾底下涵蓋編譯好的教學範例執行檔和執行需要的資源，可以直接開啟**Python庫存停損停利(教學範例, 僅現股操作).exe**做使用，須注意**本程式範例只涵蓋一般現股市價下單，全額交割股、處置股會下單失敗**，且程式邏輯**僅包含觸價發出市價單**，會發出當下觸即停損停利設定價格**庫存張數的市價單**
* tp_sl_gui.py<br>
  **本檔案為主要程式也是執行檔原碼**，GUI套件使用Pyside6，Python版本須為3.11，有任何需求都可以從這邊做修正
* tp_sl_gui.spec<br>
  pyinstaller編譯執行檔用的描述檔，如想編出與範例一致的執行檔，請使用本描述檔操作
<!-- * XQ_追漲停.zip<br>
  內含XQ程式碼，解壓縮後直接匯入XQ即可使用，回測設定可以使用1分K，交易請使用逐筆洗價 -->
     
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
* 監控設定<br>
  * 預設停損-5%(負數)，當有任何屬於該帳號的**新部位**透過成交回報進來時會依成交價格設定-5%停損, 若已存在相同股票則不覆蓋<br>
  * 預設停損5%(正數)，當有任何屬於該帳號的**新部位**透過成交回報進來時會依成交價格設定5%停利, 若已存在相同股票則不覆蓋<br>

## Pyinstaller 編譯執行檔設定
建議使用conda指令安裝pyinstaller減少環境問題<br>
```
conda install pyinstaller
```
若想編譯與教學範例一致之執行檔，請先將tp_sl_gui.py、tp_sl_gui.spec、inventory.ico三個檔案移至同一資料夾，並用指令如下<br>
```
pyinstaller tp_sl_gui.spec
```
編譯完成後，應會出現單個執行檔在dist資料夾內<br>
若想由原始碼編譯，建議使用以下指令進行單檔打包，在部署到其他裝置時會比較容易
```
pyinstaller -F tp_sl_gui.py
```
pyinstaller會自動產生新的tp_sl_gui.spec，可以再依自己的喜好調整參數
