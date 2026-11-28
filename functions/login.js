// 登入頁：輸入共用密碼，正確就發一張 180 天有效的登入憑證（存在瀏覽器 cookie）
const W = 'https://sinyi-proxy.ken29460338.workers.dev/';
const esc = s => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const safeNext = n => (/^\/(?!\/)[^\s]*$/.test(n || '') && !n.startsWith('/login')) ? n : '/';
function page(msg, next) {
  return new Response(`<!DOCTYPE html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex"><title>登入｜物件比較分析</title>
<style>body{margin:0;min-height:100vh;display:grid;place-items:center;background:#f8f6f1;font-family:"Noto Sans TC","PingFang TC","Microsoft JhengHei",sans-serif;color:#3f3f38}
form{background:#fdfcf9;border-radius:14px;box-shadow:0 3px 14px rgba(80,70,50,.12);padding:36px 32px;width:min(360px,88vw)}
h1{font-size:24px;margin:0 0 6px}p{margin:0 0 20px;color:#7a776d;font-size:15px}
label{display:block;font-size:15px;margin-bottom:6px}input{width:100%;box-sizing:border-box;font-size:18px;padding:11px 12px;border:1px solid #cfc8b8;border-radius:8px;background:#fff}
button{margin-top:16px;width:100%;font-size:18px;padding:12px;border:0;border-radius:8px;background:#7d8f6e;color:#fff;cursor:pointer}
.err{color:#a3402b;margin:12px 0 0;font-size:15px}</style></head><body>
<form method="post" action="/login"><h1>物件比較分析</h1><p>請輸入同仁共用密碼</p>
<label for="pw">密碼</label><input id="pw" name="password" type="password" autocomplete="current-password" required autofocus>
<input type="hidden" name="next" value="${esc(next)}"><button type="submit">登入</button>
${msg ? `<p class="err" role="alert">${esc(msg)}</p>` : ''}</form></body></html>`,
  { status: msg ? 401 : 200, headers: { 'content-type': 'text/html; charset=utf-8', 'cache-control': 'no-store', 'x-robots-tag': 'noindex' } });
}
export async function onRequestGet({ request }) {
  return page('', safeNext(new URL(request.url).searchParams.get('next')));
}
export async function onRequestPost({ request }) {
  const f = await request.formData();
  const next = safeNext(String(f.get('next') || '/'));
  let r, j = {};
  try {
    r = await fetch(W + 'login', { method: 'POST', headers: { 'content-type': 'application/json', 'x-pc-ip': request.headers.get('cf-connecting-ip') || '', origin: 'https://prop-compare.pages.dev' }, body: JSON.stringify({ password: String(f.get('password') || '') }) });
    j = await r.json();
  } catch (e) { return page('暫時無法登入，請稍後再試。', next); }
  if (r.ok && j.token) {
    const age = Math.floor((j.exp - Date.now()) / 1000);
    return new Response(null, { status: 303, headers: { location: next, 'cache-control': 'no-store', 'set-cookie': `pc_s=${j.token}; Path=/; Max-Age=${age}; HttpOnly; Secure; SameSite=Lax` } });
  }
  if (j.error === 'locked') return page('密碼錯太多次，請 15 分鐘後再試。', next);
  if (j.error === 'not_configured') return new Response(null, { status: 303, headers: { location: next } });
  return page(j.left > 0 ? `密碼不正確，還可以再試 ${j.left} 次。` : '密碼不正確。', next);
}
