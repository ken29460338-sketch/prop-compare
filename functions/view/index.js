// Cloudflare Pages Function：prop-compare.pages.dev/view → 給客戶看的分享頁（免登入）
// 內容和首頁同一份程式，只會用網址 #d= 裡的資料顯示比較表，不能編輯，也不會用到 Google 額度。
export async function onRequestGet({ request, env }) {
  const r = await env.ASSETS.fetch(new URL('/', request.url));
  const h = new Headers(r.headers); h.set('cache-control', 'no-cache'); h.set('x-robots-tag', 'noindex');
  return new Response(r.body, { status: r.status, headers: h });
}
