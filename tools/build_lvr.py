#!/usr/bin/env python3
"""下載內政部實價登錄 Open Data（不動產買賣），整理成「縣市/行政區/路名.json」給網站的社區行情查詢。

資料來源：內政部不動產交易實價查詢服務網 Open Data（政府資料開放授權條款）
https://plvr.land.moi.gov.tw/DownloadOpenData

用法：python3 tools/build_lvr.py            # 預設臺中市（B）
      CITIES=B,N python3 tools/build_lvr.py  # 多個縣市
輸出：data/lvr/<縣市代碼>/<行政區>/<路名>.json 與 data/lvr/<縣市代碼>/index.json
"""
import csv, io, json, os, re, sys, time, urllib.request, datetime, shutil

csv.field_size_limit(10 ** 8)  # 部分預售屋資料欄位很長（備註、棟及號）
CITIES = [c.strip().upper() for c in os.environ.get('CITIES', 'B').split(',') if c.strip()]
OUT = os.path.join(os.path.dirname(__file__), '..', 'data', 'lvr')
BASE = 'https://plvr.land.moi.gov.tw/'
UA = {'User-Agent': 'Mozilla/5.0 (prop-compare open-data builder; +https://github.com/ken29460338-sketch/prop-compare)'}


def get(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=120) as r:
                b = r.read()
            return b
        except Exception as e:
            print('  retry', i + 1, url, e, flush=True)
            time.sleep(3 + i * 5)
    return None


def decode(b):
    for enc in ('utf-8-sig', 'utf-8', 'big5', 'cp950'):
        try:
            return b.decode(enc)
        except UnicodeDecodeError:
            pass
    return b.decode('utf-8', 'replace')


def seasons():
    now = datetime.date.today()
    roc = now.year - 1911
    for y in range(101, roc + 1):
        for s in range(1, 5):
            if y == roc and (s - 1) * 3 + 1 > now.month:
                break
            yield f'{y}S{s}'


def num(x):
    try:
        return float(str(x).replace(',', '').strip())
    except Exception:
        return None


CN = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '十': 10, '〇': 0, '零': 0}


def cnum(s):
    """中文數字樓層（例：十三層、二十一層）轉數字"""
    s = str(s or '').replace('層', '').strip()
    if not s:
        return None
    if s.isdigit():
        return int(s)
    if '地下' in s:
        return None
    total, cur = 0, 0
    for ch in s:
        if ch == '十':
            total += (cur or 1) * 10
            cur = 0
        elif ch == '百':
            total += (cur or 1) * 100
            cur = 0
        elif ch in CN:
            cur = CN[ch]
        else:
            return None
    return total + cur


FW = str.maketrans('０１２３４５６７８９～', '0123456789~')
ROAD = re.compile(r'^(.+?(?:路|街|大道)(?:[一二三四五六七八九十\d]+段)?)')


def split_addr(addr, town):
    """回傳 (路名, 號碼起, 號碼迄, 巷弄門牌尾)。舊資料門牌是區間（例：五權七街91~120號）"""
    a = str(addr or '').translate(FW).replace(' ', '')
    a = re.sub(r'^(臺|台)?(北|中|南)?(市|縣)', '', a) if re.match(r'^(臺|台)(北|中|南)(市|縣)', a) else re.sub(r'^\S{2}(市|縣)', '', a)
    if town and a.startswith(town):
        a = a[len(town):]
    a = re.sub(r'^[^路街道]{1,6}?里(?![路街])(?=.*(路|街|大道))', '', a)  # 去掉「XX里」
    m = ROAD.match(a)
    if not m:
        return None
    road = m.group(1)
    rest = a[len(road):]
    lane = ''
    lm = re.match(r'^((?:\d+巷)?(?:\d+弄)?)', rest)
    if lm:
        lane = lm.group(1)
        rest = rest[len(lane):]
    nm = re.match(r'^(\d+)(?:之\d+)?(?:~(\d+)(?:之\d+)?)?號', rest)
    lo = hi = None
    if nm:
        lo = int(nm.group(1))
        hi = int(nm.group(2)) if nm.group(2) else lo
    return road, lane, lo, hi, a[len(road):]


def safe(name):
    return re.sub(r'[\\/:*?"<>|]', '_', name)


def presale_names(code):
    """預售屋資料有「建案名稱」與門牌：整理成 (區, 路, 巷, 號) → 建案名稱，補到同門牌的成屋成交上"""
    from collections import Counter
    exact, ranges = {}, {}
    urls = [f'{BASE}DownloadSeason?season={s}&fileName={code}_lvr_land_B.csv' for s in seasons()]
    urls.append(f'{BASE}Download?fileName={code}_lvr_land_B.csv')
    for url in urls:
        b = get(url, tries=2)
        if not b or len(b) < 200:
            continue
        try:
            rows_ = list(csv.reader(io.StringIO(decode(b))))
        except csv.Error as e:
            print('presale parse error', url, e, flush=True)
            continue
        rd = iter(rows_)
        head = next(rd, None)
        if not head or '建案名稱' not in ''.join(head):
            continue
        H = {h.strip(): i for i, h in enumerate(head)}
        it, ia, iname = H.get('鄉鎮市區'), H.get('土地位置建物門牌'), H.get('建案名稱')
        if None in (it, ia, iname):
            continue
        for r in rd:
            if len(r) <= max(it, ia, iname) or r[0].startswith('The '):
                continue
            name = re.sub(r'\s+', '', r[iname])
            if not name or name in ('-', '無'):
                continue
            sp = split_addr(r[ia], r[it].strip())
            if not sp or sp[2] is None:
                continue
            road, lane, lo, hi, _ = sp
            key = (r[it].strip(), road, lane)
            if lo == hi:
                exact.setdefault(key + (lo,), Counter())[name] += 1
            else:
                ranges.setdefault(key, []).append((lo, hi, name))
        time.sleep(0.5)
    ex = {k: c.most_common(1)[0][0] for k, c in exact.items()}
    print('presale names', len(ex), 'ranges', sum(len(v) for v in ranges.values()), flush=True)
    return ex, ranges


def name_for(names, town, road, lane, lo, hi):
    ex, ranges = names
    if lo is None:
        return ''
    if lo == hi:
        n = ex.get((town, road, lane, lo))
        if n:
            return n
    cand = {nm for a, b, nm in ranges.get((town, road, lane), []) if a <= lo and hi <= b}
    return cand.pop() if len(cand) == 1 else ''


def build_city(code):
    names = presale_names(code)
    rows = {}  # (town, road) -> [row]
    lands, houses = {}, {}  # town -> [row]（純土地、同區域透天）
    seen = set()
    files = [(s, f'{BASE}DownloadSeason?season={s}&fileName={code}_lvr_land_A.csv') for s in seasons()]
    # 本期（每 10 天一批，只提供最新一批）：每次下載都存一份到 data/lvr/raw/，季資料出來前才不會漏掉中間幾批
    rawdir = os.path.join(OUT, 'raw', code)
    os.makedirs(rawdir, exist_ok=True)
    nb = get(f'{BASE}Download?fileName={code}_lvr_land_A.csv')
    if nb and len(nb) > 200 and '鄉鎮市區' in decode(nb[:400]):
        import hashlib
        h = hashlib.sha1(nb).hexdigest()[:10]
        if not any(f.endswith(h + '.csv') for f in os.listdir(rawdir)):
            with open(os.path.join(rawdir, f'now-{datetime.date.today():%Y%m%d}-{h}.csv'), 'wb') as f:
                f.write(nb)
    cutoff = (datetime.date.today() - datetime.timedelta(days=300)).strftime('%Y%m%d')
    for f in sorted(os.listdir(rawdir)):
        if f[4:12] < cutoff:
            os.remove(os.path.join(rawdir, f))  # 季資料早已涵蓋
        else:
            files.append(('raw:' + f, 'file://' + os.path.abspath(os.path.join(rawdir, f))))
    for tag, url in files:
        b = open(url[7:], 'rb').read() if url.startswith('file://') else get(url)
        if not b or len(b) < 200 or b[:15].lower().startswith(b'<!doctype') or b[:6].lower() == b'<html>':
            print('skip', tag, flush=True)
            continue
        text = decode(b)
        rd = csv.reader(io.StringIO(text))
        head = next(rd, None)
        if not head or '鄉鎮市區' not in ''.join(head):
            print('bad header', tag, head[:3] if head else None, flush=True)
            continue
        H = {h.strip(): i for i, h in enumerate(head)}

        def col(*names):
            for n in names:
                for h, i in H.items():
                    if h == n or h.replace('(', '').replace(')', '') == n:
                        return i
            return None
        C = dict(larea=col('土地移轉總面積平方公尺'), zone=col('都市土地使用分區'), nzone=col('非都市土地使用分區'),
                 town=col('鄉鎮市區'), target=col('交易標的'), addr=col('土地位置建物門牌'), date=col('交易年月日'),
                 floor=col('移轉層次'), floors=col('總樓層數'), btype=col('建物型態'), use=col('主要用途'),
                 built=col('建築完成年月'), area=col('建物移轉總面積平方公尺'), rooms=col('建物現況格局-房'),
                 halls=col('建物現況格局-廳'), baths=col('建物現況格局-衛'), mgmt=col('有無管理組織'),
                 price=col('總價元'), unit=col('單價元平方公尺'), ptype=col('車位類別'),
                 parea=col('車位移轉總面積平方公尺', '車位移轉總面積(平方公尺)'), pprice=col('車位總價元'),
                 note=col('備註'), id=col('編號'), main=col('主建物面積'), lift=col('電梯'))
        n = 0
        for r in rd:
            if not r or len(r) < 10 or r[0].startswith('The ') or r[0] == 'The villages and towns urban district':
                continue
            g = lambda k: (r[C[k]].strip() if C[k] is not None and C[k] < len(r) else '')
            target = g('target')
            land_only = target == '土地'
            if '建物' not in target and not land_only:
                continue  # 有建物的交易（房地、房地＋車）＋純土地；車位單獨交易不收
            rid = g('id') or (g('addr') + g('date') + g('price'))
            if rid in seen:
                continue
            seen.add(rid)
            town = g('town')
            larea = num(g('larea'))
            zone = (g('zone') or g('nzone'))[:12]
            if land_only:  # 純土地：位置是「XX段XX地號」，沒有路名，依地段與行政區歸檔
                price = num(g('price')) or 0
                if price <= 0:
                    continue
                d = re.sub(r'\D', '', g('date'))
                loc = re.sub(r'^(臺|台)?中市', '', str(g('addr')).translate(FW).replace(' ', ''))
                if loc.startswith(town):
                    loc = loc[len(town):]
                sec = (re.match(r'^(.+?段)', loc) or [None, ''])[1]
                lrow = [int(d) if d else 0, loc, '', None, None, '', None, '土地', round(price / 10000), None, None, 0, None, None, None, '',
                        '', 0, g('note')[:60], '', '', '', round(larea, 2) if larea else None, sec, zone, '']
                lands.setdefault(town, []).append(lrow)
                continue
            sp = split_addr(g('addr'), town)
            if not sp:
                continue
            road, lane, lo, hi, tail = sp
            area = num(g('area')) or 0
            price = num(g('price')) or 0
            if area <= 0 or price <= 0:
                continue
            pprice = num(g('pprice')) or 0
            parea = num(g('parea')) or 0
            ping = area / 3.30579
            unit = (price / 10000) / ping if ping else None
            unit_np = ((price - pprice) / 10000) / ((area - parea) / 3.30579) if pprice and area - parea > 0 else None
            main = num(g('main'))
            d = re.sub(r'\D', '', g('date'))
            b_ = re.sub(r'\D', '', g('built'))
            age = None
            if len(d) >= 5 and len(b_) >= 5:
                try:
                    age = round((int(d[:-4]) + int(d[-4:-2]) / 12) - (int(b_[:-4]) + int(b_[-4:-2]) / 12), 1)
                except Exception:
                    age = None
            row = [
                int(d) if d else 0,                                    # 0 交易日期（民國 yyymmdd）
                tail,                                                  # 1 路名之後的門牌（巷弄號樓）
                lane, lo, hi,                                          # 2-4 巷弄、號碼區間
                g('floor'), cnum(g('floors')),                         # 5 移轉層次、6 總樓層
                g('btype').split('(')[0],                              # 7 建物型態
                round(price / 10000),                                  # 8 總價（萬）
                round(unit, 2) if unit else None,                      # 9 單價（萬/坪，含車）
                round(unit_np, 2) if unit_np else None,                # 10 扣車單價（萬/坪）
                round(ping, 2),                                        # 11 總坪數
                round(main / area * 100, 1) if main else None,         # 12 主建物占比
                age,                                                   # 13 屋齡
                int(b_[:-4]) if len(b_) >= 5 else None,                # 14 建築完成年（民國）
                f"{g('rooms')}/{g('halls')}/{g('baths')}",             # 15 格局 房/廳/衛
                g('ptype'), round(pprice / 10000) if pprice else 0,   # 16 車位類別、17 車位價（萬）
                g('note')[:60], g('mgmt'), g('lift'), g('use'),        # 18 備註、19 管理、20 電梯、21 用途
                round(larea, 2) if larea else None, '', zone,          # 22 土地移轉總面積（㎡）、23 地段、24 使用分區
                name_for(names, town, road, lane, lo, hi),             # 25 社區（建案）名稱：預售屋資料同門牌的建案名稱
            ]
            rows.setdefault((town, road), []).append(row)
            if '透天' in row[7]:
                houses.setdefault(town, []).append([road] + row)  # 同區域透天（路段案例不足時用）
            n += 1
        print('ok', tag, n, flush=True)
        time.sleep(1)

    out = os.path.join(OUT, code)
    if os.path.isdir(out):
        shutil.rmtree(out)
    os.makedirs(out, exist_ok=True)
    index = {}
    for (town, road), lst in rows.items():
        lst.sort(key=lambda x: -x[0])
        p = os.path.join(out, safe(town))
        os.makedirs(p, exist_ok=True)
        with open(os.path.join(p, safe(road) + '.json'), 'w', encoding='utf-8') as f:
            json.dump(lst, f, ensure_ascii=False, separators=(',', ':'))
        index.setdefault(town, []).append(road)
    for t in index:
        index[t].sort()
    for name, bucket in (('_土地', lands), ('_透天', houses)):  # 每區一個檔：同區域土地、同區域透天
        for town, lst in bucket.items():
            lst.sort(key=lambda x: -(x[1] if name == '_透天' else x[0]))
            p = os.path.join(out, safe(town))
            os.makedirs(p, exist_ok=True)
            with open(os.path.join(p, name + '.json'), 'w', encoding='utf-8') as f:
                json.dump(lst, f, ensure_ascii=False, separators=(',', ':'))
    meta = {'updated': datetime.date.today().isoformat(), 'rows': sum(len(v) for v in rows.values()),
            'cols': ['date', 'tail', 'lane', 'lo', 'hi', 'floor', 'floors', 'type', 'price', 'unit', 'unitNoPark',
                     'ping', 'mainPct', 'age', 'builtYear', 'layout', 'parkType', 'parkPrice', 'note', 'mgmt', 'lift', 'use',
                     'landM2', 'section', 'zone', 'community'],
            'extra': {'_土地': '純土地（每列同上欄位，位置在 tail、地段在 section）', '_透天': '同區域透天（每列最前面多一欄路名）'},
            'towns': index}
    with open(os.path.join(out, 'index.json'), 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, separators=(',', ':'))
    print('city', code, 'rows', meta['rows'], 'roads', sum(len(v) for v in index.values()), flush=True)
    return meta['rows']


if __name__ == '__main__':
    total = sum(build_city(c) for c in CITIES)
    if total == 0:
        print('no data downloaded', file=sys.stderr)
        sys.exit(1)
