#!/usr/bin/env python3
"""
AltLigler.com veri güncelleyici (kaynak: tff.org).

TFF'nin resmi puan cetveli sayfalarından Süper Lig, 1. Lig, 2. Lig (Beyaz/Kırmızı)
ve 3. Lig (1-2-3. Grup) puan durumlarını ve son oynanan haftanın sonuçlarını okur,
veri/data.json dosyasını yazar. API anahtarı gerekmez.

TFF sayfanın yapısını değiştirirse okuma bozulabilir; o durumda betik mevcut
veri/data.json dosyasına dokunmadan hata verir ve site son iyi veriyi göstermeye devam eder.
"""
import html, json, os, re, sys, time, urllib.request
from datetime import datetime, timedelta, timezone

BASE = "https://www.tff.org/Default.aspx?"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "veri", "data.json")
LOGO_DIR = os.path.join(ROOT, "logolar")
TZ = timezone(timedelta(hours=3))

# id, görünen ad, kısa ad, TFF sayfa parametreleri, bölgeler (yükselen, (play-off ilk, son), düşen)
TABLES = [
    ("superlig", "Trendyol Süper Lig", "Süper Lig", "pageID=198", None),
    ("1lig", "Trendyol 1. Lig", "1. Lig", "pageID=142", (2, (3, 7), 4)),
    ("2lig-beyaz", "Nesine 2. Lig Beyaz Grup", "2. Lig Beyaz", "pageID=976&grupID=3541", (1, (2, 5), 3)),
    ("2lig-kirmizi", "Nesine 2. Lig Kırmızı Grup", "2. Lig Kırmızı", "pageID=976&grupID=3542", (1, (2, 5), 4)),
    ("3lig-1", "Nesine 3. Lig 1. Grup", "3. Lig 1. Grup", "pageID=971&grupID=3543", (1, None, 0)),
    ("3lig-2", "Nesine 3. Lig 2. Grup", "3. Lig 2. Grup", "pageID=971&grupID=3544", (1, None, 0)),
    ("3lig-3", "Nesine 3. Lig 3. Grup", "3. Lig 3. Grup", "pageID=971&grupID=3545", (1, None, 0)),
]

ROW_RE = re.compile(r'lnkTakim"\s+href="[^"]*kulupID=(\d+)"\s*>([^<]+)</a>(.*?)</tr>', re.S | re.I)
NUM_RE = re.compile(r"<span[^>]*>\s*(-?\d+)\s*</span>", re.S)
FX_RE = re.compile(
    r'<td class="altCizgi"[^>]*>\s*<a href="[^"]*kulupId=(\d+)"\s*>([^<]+)</a>\s*</td>\s*'
    r'<td[^>]*>\s*<a href="[^"]*macId=\d+"\s*>([^<]*)</a>\s*</td>\s*'
    r'<td[^>]*>\s*<a href="[^"]*kulupId=(\d+)"\s*>([^<]+)</a>\s*</td>', re.S | re.I)
SCORE_RE = re.compile(r"^\s*(\d+)\s*-\s*(\d+)\s*$")

LOWER = str.maketrans({"I": "ı", "İ": "i"})
DROP = re.compile(r"\b(A\.?\s?Ş\.?|FUTBOL KULÜBÜ|FUTBOL SPOR KULÜBÜ|SPOR FAALİYETLERİ|FUTBOL YATIRIMLARI|KULÜBÜ|DERNEĞİ)\b\.?", re.I)


def tr_title(s):
    s = re.sub(r"^\s*\d+\.\s*", "", html.unescape(s)).strip()          # baştaki "1." sırasını at
    s = re.sub(r"\bSPOR KULÜBÜ\b", "SPOR", s, flags=re.I)
    s = re.sub(r"\s+", " ", DROP.sub("", s)).strip(" .-")
    s = re.sub(r"(\w) SPOR$", r"\1SPOR", s)  # "MUŞ SPOR" -> "MUŞSPOR"
    keep = {"FK", "SK", "FSK", "MKE", "SMS", "KCT", "GOG", "BB", "GFK", "TFF"}
    words = []
    for w in s.split(" "):
        if w.upper() in keep:
            words.append(w.upper())
            continue
        lw = w.translate(LOWER).lower()
        if not lw:
            continue
        first = lw[0].replace("i", "İ") if lw[0] == "i" else lw[0].upper()
        words.append(first + lw[1:])
    return " ".join(words) or s


def fetch(params):
    req = urllib.request.Request(BASE + params, headers={
        "User-Agent": "Mozilla/5.0 (AltLigler.com veri guncelleyici; gunluk 1 kez)",
        "Accept-Language": "tr-TR,tr;q=0.9"})
    with urllib.request.urlopen(req, timeout=60) as r:
        raw = r.read()
        ct = r.headers.get("Content-Type", "")
    enc = "windows-1254"
    m = re.search(r"charset=([\w-]+)", ct)
    if m:
        enc = m.group(1)
    return raw.decode(enc, errors="replace")


def parse(page, tid, name, short, params, zones):
    rows = []
    for m in ROW_RE.finditer(page):
        nums = [int(x) for x in NUM_RE.findall(m.group(3))]
        if len(nums) < 8:
            continue
        o, g, b, mg, a, y, _av, p = nums[:8]
        rows.append({"teamId": int(m.group(1)), "team": tr_title(m.group(2)), "p": o, "w": g, "d": b, "l": mg,
                     "gf": a, "ga": y, "pts": p, "zone": "", "desc": ""})
    if len(rows) < 8:
        raise ValueError(f"{name}: puan tablosu okunamadı ({len(rows)} satır)")
    rows.sort(key=lambda r: 0)  # TFF sırası korunur
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    if zones:
        up, po, down = zones
        n = len(rows)
        for i, r in enumerate(rows, 1):
            if i <= up:
                r["zone"] = "up"
            elif po and po[0] <= i <= po[1]:
                r["zone"] = "po"
            elif down and i > n - down:
                r["zone"] = "down"

    ids = {r["teamId"] for r in rows}
    weeks = []
    for chunk in page.split("<table"):
        ms = [m for m in FX_RE.finditer(chunk) if int(m.group(1)) in ids or int(m.group(4)) in ids]
        if ms:
            weeks.append(ms)
    week, results = None, []
    for i, ms in enumerate(weeks, 1):
        played = [m for m in ms if SCORE_RE.match(html.unescape(m.group(3)))]
        if played:
            week, results = i, played
    res = []
    for m in results:
        hs, as_ = SCORE_RE.match(html.unescape(m.group(3))).groups()
        res.append({"homeId": int(m.group(1)), "home": tr_title(m.group(2)), "awayId": int(m.group(4)),
                    "away": tr_title(m.group(5)), "hs": int(hs), "as": int(as_)})
    return {"id": tid, "name": name, "short": short, "week": week, "src": BASE + params,
            "table": rows, "results": res}


def main():
    old = {}
    if os.path.exists(OUT):
        try:
            with open(OUT, encoding="utf-8") as f:
                old = json.load(f)
        except Exception:
            old = {}
    old_tables = {t["id"]: t for t in old.get("tables", [])}

    tables, errors = [], []
    for i, (tid, name, short, params, zones) in enumerate(TABLES):
        if i:
            time.sleep(2)  # TFF sunucusunu yormamak için
        try:
            t = parse(fetch(params), tid, name, short, params, zones)
            tables.append(t)
            print(f"{name}: {len(t['table'])} takım, {t['week']}. hafta, {len(t['results'])} sonuç. "
                  f"Lider: {t['table'][0]['team']} ({t['table'][0]['pts']} p)")
        except Exception as e:
            errors.append(f"{name}: {e}")
            print(f"HATA {name}: {e}")
            if tid in old_tables:
                tables.append(old_tables[tid])
                print(f"  -> {name} için önceki veri korundu.")

    if not any(t for t in tables):
        sys.exit("Hiçbir tablo okunamadı; veri/data.json değiştirilmedi.")

    logos = sorted(f for f in os.listdir(LOGO_DIR) if f.lower().endswith((".png", ".jpg", ".jpeg", ".svg", ".webp"))) \
        if os.path.isdir(LOGO_DIR) else []
    data = {"updated": datetime.now(TZ).strftime("%Y-%m-%d %H:%M"), "source": "TFF",
            "tables": tables, "teams": {}, "logos": logos,
            "teamLogos": old.get("teamLogos") or {}, "teamLogosAt": old.get("teamLogosAt")}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(f"Yazıldı: veri/data.json ({len(tables)} tablo).")
    if errors and len(errors) == len(TABLES):
        sys.exit("Tüm tablolar hatalı.")


if __name__ == "__main__":
    main()
