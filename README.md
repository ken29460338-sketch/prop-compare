# 物件比較分析

貼上物件訊息，整理路段、總價、含車與扣車單價，產出給客戶的比較圖、PDF、LINE 文字或分享連結。

- 純前端單一頁面（`index.html`），資料只存在使用者自己的瀏覽器。
- 分享連結會把整份比較表壓縮放進網址，不經過任何伺服器。
- 扣車單價 ＝（總價 − 車位價）÷（登記坪數 − 車位坪數）。

## 發佈

Settings → Pages → Source 選「Deploy from a branch」，Branch 選 `main`、資料夾 `/ (root)`，存檔後約一分鐘即可在
`https://<帳號>.github.io/<repo 名稱>/` 打開。

網站同時部署在兩個網址，推到 `main` 後兩邊都會在約一分鐘內自動更新：

- 網站：https://prop-compare.pages.dev/ （需要共用密碼登入，登入一次維持 180 天）
- 客戶分享頁：https://prop-compare.pages.dev/view#d=…（免登入、唯讀）；短網址 /s/<代碼> 也免登入
- GitHub Pages 已關閉（無法加登入保護）

### 登入（共用密碼）
- 密碼存在中繼服務 sinyi-proxy 的 Secret `SITE_PASSWORD`；改這個值＝換密碼，所有人會被登出。
- 登入頁 functions/login.js、登出 /logout、門禁 functions/_middleware.js；網站呼叫中繼服務改走同網域 /api（functions/api/[[path]].js），中繼服務會檢查登入憑證。
- 密碼連錯 5 次鎖 15 分鐘。刪掉 `SITE_PASSWORD` 就會恢復公開。

官網資料由 `worker/sinyi-proxy.js`（Cloudflare Worker）提供，它只允許上面兩個網址呼叫；
新增網址時要把網址加進 Worker 開頭的 `A` 清單。Worker 也連著這個 repo（路徑 `/worker`、設定在
`worker/wrangler.toml`），推到 `main` 就會自動重新部署。讀過的物件會存在 KV（`prop-cache`）6 小時，
網頁上的「↻ 更新官網資料」會帶 `refresh=1` 跳過存檔重抓。

帶看路線的車程用 Google Routes API（含即時路況），經 Worker 的 `/route` 呼叫，金鑰存在 Worker Secret `GMAPS_KEY`；
每天最多 150 次（`ROUTE_DAILY_MAX` 可調），同路線 10 分鐘內用 KV 暫存。沒有金鑰或超過上限時，網頁自動改用 OSRM 乘路況倍數估算。
