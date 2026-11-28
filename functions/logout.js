// 登出：清掉這台電腦的登入憑證
export function onRequest() {
  return new Response(null, { status: 303, headers: { location: '/login', 'cache-control': 'no-store', 'set-cookie': 'pc_s=; Path=/; Max-Age=0; HttpOnly; Secure; SameSite=Lax' } });
}
