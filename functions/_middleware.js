// 共用密碼登入門：除了客戶分享頁（/view）、短網址（/s/）和登入頁，其他都要先登入。
// 密碼存在中繼服務（SITE_PASSWORD），這裡只把瀏覽器的登入憑證拿去給中繼服務檢查。
const W = 'https://sinyi-proxy.ken29460338.workers.dev/';
const OK = new Map(); // 同一個憑證 10 分鐘內不重複檢查
const PUBLIC = p => p === '/view' || p.startsWith('/view/') || p.startsWith('/s/') || p === '/login' || p === '/logout' || p === '/favicon.ico' || p.startsWith('/api/');
export async function onRequest({ request, next }) {
  const u = new URL(request.url);
  if (PUBLIC(u.pathname)) return next(); // /api 由中繼服務自己檢查
  const m = (request.headers.get('cookie') || '').match(/(?:^|;\s*)pc_s=([^;]+)/);
  const t = m ? m[1] : '';
  const c = t && OK.get(t);
  if (c && c > Date.now()) return next();
  let ok = false;
  try {
    const r = await fetch(W + 'auth', { headers: { 'x-pc-session': t, origin: 'https://prop-compare.pages.dev' } });
    const j = await r.json();
    ok = j.ok === true; // 還沒設定密碼時中繼服務會回 ok:true，網站維持公開
  } catch (e) { ok = false; }
  if (ok) { if (t) { OK.set(t, Date.now() + 6e5); if (OK.size > 500) OK.clear(); } return next(); }
  return new Response(null, { status: 302, headers: { location: '/login?next=' + encodeURIComponent(u.pathname + u.search), 'cache-control': 'no-store' } });
}
