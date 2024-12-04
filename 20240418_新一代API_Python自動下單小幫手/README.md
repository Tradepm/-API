# 自動下單小幫手 with 富邦新一代API
本程式碼為程式交易串接教學範例，展示如何串接富邦新一代API Python SDK實現「獲取庫存資料」及「送出現股委託」<br>

> Disclaimer: 本範例程式碼僅供教學與參考之用，實務交易應自行評估並承擔相關風險
> 
## 參考連結
富邦新一代API Python SDK載點及開發說明文件
* 新一代API SDK 載點<br>
https://www.fbs.com.tw/TradeAPI/docs/download/download-sdk
* 新一代API 開發說明文件<br>
https://www.fbs.com.tw/TradeAPI/docs/trading/introduction 
* 新一代API 社群討論<br>
https://discord.com/invite/VHjjc4C

## 檔案列表
`main.py` - 主程式<br>
`trade_list_example.xlsx` - 交易標的設定表<br>
`my_assistant.py` - 互動式執行版（功能與main.py等同，可於互動執行環境執行）<br>
<br>
***註：互動執行環境設定方式，可參考後文說明***

## 安裝封包
`pip install -r requirements.txt`<br>

另需安裝富邦新一代API Python SDK

## 登入設定
在程式資料夾中新建檔案 `.env` 並輸入以下內容<br>
> ID= #身份證字號<br>
> PWD= #交易密碼<br>
> CPATH= #憑證路徑<br>
> CPWD= #憑證密碼<br>
> ACCOUNT= #帳號<br>
> TRADELIST=trade_list_example.xlsx #交易目標清單<br>


## 互動執行環境設定說明(for `my_assistant.py`)

### 使用環境
* 講座演示使用環境為**Anaconda+vscode+jupyter code cells**，建置方式可參考vscode官方說明文件
    * jupyter code cells 官方說明文件
    https://code.visualstudio.com/docs/python/jupyter-support-py
    

## 編譯執行檔
若有想使用Pyinstaller將程式碼編譯成執行檔，建議配合anaconda環境使用以下指令安裝套件
* conda install -c conda-forge pyinstaller
