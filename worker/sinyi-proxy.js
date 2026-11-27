// Cloudflare Worker：讀取信義房屋物件頁，回傳比較工具需要的欄位（JSON）。
// 用法：GET https://<worker 網址>/?code=5946NX
// 只允許下面列出的網站呼叫，避免被別人拿去用。
const ALLOWED_ORIGINS = [
  'https://ken29460338-sketch.github.io',
];

const json = (data, status, origin) => new Response(JSON.stringify(data), {
  status,
  headers: {
    'content-type': 'application/json; charset=utf-8',
    'access-control-allow-origin': origin,
    'vary': 'Origin',
    'cache-control': status === 200 ? 'public, max-age=1800' : 'no-store',
  },
});

const num = v => {
  const n = parseFloat(String(v ?? '').replace(/,/g, ''));
  return Number.isFinite(n) ? n : null;
};

export default {
  async fetch(request) {
    const origin = request.headers.get('origin') || '';
    const allow = ALLOWED_ORIGINS.includes(origin) ? origin : ALLOWED_ORIGINS[0];
    if (request.method === 'OPTIONS') return json({}, 204, allow);

    const code = (new URL(request.url).searchParams.get('code') || '').toUpperCase();
    if (!/^[0-9A-Z]{4,8}$/.test(code)) return json({ error: 'bad_code' }, 400, allow);

    const res = await fetch(`https://www.sinyi.com.tw/buy/house/${code}`, {
      headers: {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36',
        'accept-language': 'zh-TW,zh;q=0.9',
      },
      cf: { cacheTtl: 1800, cacheEverything: true },
    });
    if (!res.ok) return json({ error: 'upstream', status: res.status }, 502, allow);

    const html = await res.text();
    const m = html.match(/<script id="__NEXT_DATA__"[^>]*>([\s\S]*?)<\/script>/);
    if (!m) return json({ error: 'no_data' }, 404, allow);

    let c;
    try { c = JSON.parse(m[1])?.props?.initialReduxState?.buyReducer?.contentData; } catch { c = null; }
    if (!c || !c.houseNo) return json({ error: 'not_found' }, 404, allow);

    const areaOf = title => (c.areaInfo || []).find(a => String(a.title).startsWith(title))?.area ?? null;
    const parking = String(c.parking || '').trim();

    return json({
      code: c.houseNo,
      title: String(c.name || '').replace(/^專任/, ''),
      community: c.commName || '',
      address: c.address || '',
      price: num(c.totalPrice),
      origPrice: num(c.priceFirst),
      area: num(c.areaBuilding),
      mainArea: num(areaOf('主建物')),
      parkArea: num(areaOf('停車空間')),
      parkType: c.isParking ? (parking.replace(/^\d+個/, '') || '有') : '無',
      age: num(c.age),
      floor: c.floor ? `${c.floor}樓/${c.floors}樓` : '',
      layout: c.totalLayout || c.layout || '',
      direction: c.buildingFront || '',
      mgmtFee: num((String(c.monthlyFee || '').match(/([\d,]+)\s*元/) || [])[1]),
      lat: num(c.latitude),
      lng: num(c.longitude),
      layoutImage: /^https:\/\/res\.sinyi\.com\.tw\//.test(c.layoutImage || '') ? c.layoutImage : '',
      photo: /^https:\/\/res\.sinyi\.com\.tw\//.test(c.images?.[0] || '') ? c.images[0] : '',
    }, 200, allow);
  },
};
