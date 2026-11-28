// Cloudflare Pages Function：prop-compare.pages.dev/api/* → 中繼服務（sinyi-proxy Worker）
// 網站有共用密碼登入，這裡把登入憑證（pc_s）一起帶給中繼服務，
// 中繼服務驗證通過才會用 Google 車程／定位、讀信義官網，避免別人直接拿網址用掉額度。
const W = 'https://sinyi-proxy.ken29460338.workers.dev/';
export async function onRequest({ request, params }) {
  if (request.method === 'OPTIONS') return new Response(null, { status: 204 });
  const u = new URL(request.url);
  const path = [].concat(params.path || []).join('/');
  const h = new Headers({ origin: 'https://prop-compare.pages.dev' });
  const ck = (request.headers.get('cookie') || '').match(/(?:^|;\s*)pc_s=([^;]+)/);
  if (ck) h.set('x-pc-session', ck[1]);
  const ct = request.headers.get('content-type'); if (ct) h.set('content-type', ct);
  const r = await fetch(W + path + u.search, {
    method: request.method, headers: h, redirect: 'manual',
    body: request.method === 'GET' || request.method === 'HEAD' ? undefined : await request.arrayBuffer()
  });
  const oh = new Headers();
  ['content-type', 'cache-control', 'location'].forEach(k => { const v = r.headers.get(k); if (v) oh.set(k, v); });
  return new Response(r.body, { status: r.status, headers: oh });
}
