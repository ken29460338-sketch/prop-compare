# 物件比較分析

貼上物件訊息，整理路段、總價、含車與扣車單價，產出給客戶的比較圖、PDF、LINE 文字或分享連結。

- 純前端單一頁面（`index.html`），資料只存在使用者自己的瀏覽器。
- 分享連結會把整份比較表壓縮放進網址，不經過任何伺服器。
- 扣車單價 ＝（總價 − 車位價）÷（登記坪數 − 車位坪數）。

## 發佈

Settings → Pages → Source 選「Deploy from a branch」，Branch 選 `main`、資料夾 `/ (root)`，存檔後約一分鐘即可在
`https://<帳號>.github.io/<repo 名稱>/` 打開。
