# 借券賣出餘額篩選面板(StreamLit應用)

---
> ## **Disclaimer: 範例程式碼僅供教學與參考之用，不保證數據正確性，實務交易應自行評估並承擔相關風險**
> 
---

本程式碼為基本市況報導網站提供之借券賣出餘額資訊配合新一代API，示範如何結合兩者並應用StreamLit做出市場資訊即時觀察小應用<br> 
使用方法如下:<br>
Step 1. 依據.env-template新增.env檔案<br>
Step 2. 依據requirements.txt安裝所需python package<br>
Step 3. 執行run.py，若出現需輸入email的prompt直接enter跳過即可<br>
Step 4. 若執行無誤，此時瀏覽器應會自動開啟面板<br>
     
## 參考連結
富邦新一代API Python SDK載點及開發說明文件
* 新一代API SDK 載點<br>
https://www.fbs.com.tw/TradeAPI/docs/download/download-sdk
* 新一代API 條件單說明文件<br>
https://www.fbs.com.tw/TradeAPI/docs/smart-condition/introduction/
* 新一代API 開發說明文件<br>
https://www.fbs.com.tw/TradeAPI/docs/trading/introduction 
* 基本市況報導網站<br>
https://mis.twse.com.tw/stock/index?lang=zhHant

## 登入設定(.env檔設定)
在程式登入畫面中請使用以下設定
> ID = #身份證字號(ex. A123456789)<br>
> TRADEPASS = #交易密碼<br>
> CERTFILEPATH= #憑證路徑(可使用按鈕選取憑證檔案，會自動帶入路徑)<br>
> CERTPASS = #憑證密碼(如為預設密碼憑證，此欄請留白)<br>

