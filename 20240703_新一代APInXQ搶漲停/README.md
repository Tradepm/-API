# Python & XQ 搶漲停範例教學程式(GUI應用)

---
> ## **Disclaimer: 範例程式碼及執行檔僅供教學與參考之用，實務交易應自行評估並承擔相關風險**
> 
---

本程式碼為富邦新一代API & XQ線上講座範例，示範如何應用 XQ 及 Python 搶漲停，Python 會以 GUI 工具製作自己的搶漲停圖形化介面程式<br> 
功能涵蓋如下:
* py_exe<br>
  本資料夾底下涵蓋編譯好的教學範例執行檔和執行需要的資源，可以直接開啟**Python搶漲停(範例教學).exe**做使用，須注意**本程式範例只涵蓋一般現股市價下單，全額交割股、處置股會下單失敗**，且程式邏輯**僅包含觸價進場**，出場方式請依個人喜好自由調整
* rush_limit_up_gui.py<br>
  **本檔案為主要程式也是執行檔原碼**，GUI套件使用Pyside6，Python版本須為3.11，有任何需求都可以從這邊做修正
* rush_limit_up_gui.spec<br>
  pyinstaller編譯執行檔用的描述檔，如想編出與範例一致的執行檔，請使用本描述檔操作
* XQ_追漲停.zip<br>
  內含XQ程式碼，解壓縮後直接匯入XQ即可使用，回測設定可以使用1分K，交易請使用逐筆洗價
     
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
  * 漲幅(%)可以控制幾%的股票要進入即時洗價區，預設7%，如無問題不須改動<br>
  * 定時每秒更新控制snapshot掃描市場的頻率，預設5秒，如無問題不須改動<br>
* 交易設定<br>
  * 每檔額度控制單檔漲停時要花多少錢搶，會依金額與成交價計算無條件捨去至整數位，預設0.1萬(僅買的到1塊錢的股票)，請衡量風險依自行負擔能力調整<br>

## Pyinstaller 編譯執行檔設定
建議使用conda指令安裝pyinstaller減少環境問題<br>
```
conda install pyinstaller
```
若想編譯與教學範例一致之執行檔，請先將rush_limit_up_gui.py、rush_limit_up_gui.spec、fast_icon.ico三個檔案移至同一資料夾，並用指令如下<br>
```
pyinstaller rush_limit_up_gui.spec
```
編譯完成後，應會出現單個執行檔在dist資料夾內<br>
若想由原始碼編譯，建議使用以下指令進行單檔打包，在部署到其他裝置時會比較容易
```
pyinstaller -F rush_limit_up_gui.py
```
pyinstaller會自動產生新的rush_limit_up_gui.spec，可以再依自己的喜好調整參數
