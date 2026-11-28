// Cloudflare Pages Function：prop-compare.pages.dev/s/<代碼> → 轉到原本的長網址（縮網址資料存在中繼服務的 KV）
export async function onRequestGet({ params }) {
  const id = String(params.id || '').replace(/[^0-9A-Za-z]/g, '').slice(0, 12);
  if (id) {
    const r = await fetch('https://sinyi-proxy.ken29460338.workers.dev/s/' + id, { redirect: 'manual' });
    const loc = r.headers.get('location');
    if (loc) return new Response(null, { status: 302, headers: { location: loc, 'cache-control': 'public, max-age=86400' } });
  }
  return new Response('這個連結不存在或已過期，請向業務人員索取新的連結。', { status: 404, headers: { 'content-type': 'text/plain; charset=utf-8' } });
}
