#!/usr/bin/env python3
"""
AltLigler.com veri güncelleyici.

API-Football'dan Süper Lig, 1. Lig, 2. Lig ve 3. Lig'in puan durumlarını,
son 7 günün sonuçlarını ve kulüp bilgilerini çeker; veri/data.json dosyasını yazar.

API anahtarı GitHub'da API_FOOTBALL_KEY adlı gizli değişkende (secret) durur;
bu dosyada hiçbir anahtar yoktur.
Bir çalıştırma yaklaşık 13 istek harcar (ücretsiz paket: günde 100).
"""
import json, os, re, sys, unicodedata, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone

API = os.environ.get("API_BASE", "https://v3.football.api-sports.io")
KEY = os.environ.get("API_FOOTBALL_KEY", "").strip()
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "veri", "data.json")
LOGO_DIR = os.path.join(ROOT, "logolar")
TZ = timezone(timedelta(hours=3))  # Türkiye saati

# Sitede gösterilecek ligler: anahtar -> (görünen ad, kısa ad, API'deki adı yakalayan desen)
WANTED = [
    ("superlig", "Trendyol Süper Lig", "Süper Lig", r"^super lig"),
    ("1lig", "Trendyol 1. Lig", "1. Lig", r"^1\. lig"),
    ("2lig", "Nesine 2. Lig", "2. Lig", r"^2\. lig"),
    ("3lig", "Nesine 3. Lig", "3. Lig", r"^3\. lig"),
]
SKIP = ("women", "kadin", "u19", "u21", "u23", "reserve", "play")
calls = 0


def norm(s):
    s = (s or "").replace("ı", "i").replace("İ", "i")
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", s.lower()).strip()


def get(path, **params):
    global calls
    url = f"{API}/{path}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"x-apisports-key": KEY})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    calls += 1
    errs = data.get("errors")
    if errs:
        raise RuntimeError(f"API hatası ({path}): {errs}")
    return data.get("response", [])


def group_name(key, raw, count):
    if count == 1:
        return None
    n = norm(raw)
    if "white" in n or "beyaz" in n:
        return "Beyaz Grup"
    if "red" in n or "kirmizi" in n:
        return "Kırmızı Grup"
    m = re.search(r"(?:group|grup)\s*(\d+)", n)
    if m:
        return f"{int(m.group(1))}. Grup"
    return raw


def zone(desc):
    d = norm(desc)
    if not d:
        return ""
    if "relegation" in d:
        return "down"
    if "play" in d:
        return "po"
    if any(w in d for w in ("promotion", "champions", "europa", "conference")):
        return "up"
    return ""


def main():
    if not KEY:
        sys.exit("API_FOOTBALL_KEY tanımlı değil. GitHub > Settings > Secrets and variables > Actions bölümüne ekleyin.")

    leagues = get("leagues", country="Turkey", current="true")
    found = []
    for key, name, short, pat in WANTED:
        cands = [l for l in leagues
                 if l["league"].get("type") == "League"
                 and re.search(pat, norm(l["league"]["name"]))
                 and not any(s in norm(l["league"]["name"]) for s in SKIP)]
        if not cands:
            print(f"UYARI: {name} API'de bulunamadı, sitede eski veri kalacak.")
            continue
        # Gruplar API'de ayrı lig olarak da gelebilir (ör. "3. Lig - Group 1"): hepsini al.
        for l in sorted(cands, key=lambda c: norm(c["league"]["name"])):
            season = next((s for s in l["seasons"] if s.get("current")), l["seasons"][-1])
            suffix = group_name(key, l["league"]["name"], 2) if len(cands) > 1 else None
            found.append((key, name, short, l["league"]["id"], season["year"], suffix, l["league"].get("logo")))
            print(f"Bulundu: {l['league']['name']} -> API id {l['league']['id']}, sezon {season['year']}, "
                  f"puan durumu: {season.get('coverage', {}).get('standings')}")

    today = datetime.now(TZ).date()
    frm = (today - timedelta(days=7)).isoformat()
    tables, teams = [], {}
    for key, name, short, lid, season, suffix, llogo in found:
        st = get("standings", league=lid, season=season)
        groups = st[0]["league"]["standings"] if st else []
        fx = get("fixtures", league=lid, season=season, **{"from": frm, "to": today.isoformat()}, timezone="Europe/Istanbul")
        for t in get("teams", league=lid, season=season):
            tm, v = t.get("team", {}), t.get("venue", {}) or {}
            teams[tm.get("id")] = {"name": tm.get("name"), "founded": tm.get("founded"),
                                   "city": v.get("city"), "stadium": v.get("name"), "logo": tm.get("logo")}
        done = [f for f in fx if f["fixture"]["status"]["short"] in ("FT", "AET", "PEN")]
        for i, g in enumerate(groups):
            gname = suffix or group_name(key, g[0].get("group", "") if g else "", len(groups))
            if not gname:
                tid = key
            elif gname == "Beyaz Grup":
                tid = f"{key}-beyaz"
            elif gname == "Kırmızı Grup":
                tid = f"{key}-kirmizi"
            else:
                m = re.match(r"(\d+)\.", gname)
                tid = f"{key}-{m.group(1)}" if m else f"{key}-{i + 1}"
            ids = {r["team"]["id"] for r in g}
            for r in g:  # teams çağrısında olmayan kulüplerin logosunu puan tablosundan al
                teams.setdefault(r["team"]["id"], {"name": r["team"]["name"]}).setdefault("logo", r["team"].get("logo"))
            rows = [{
                "rank": r["rank"], "teamId": r["team"]["id"], "team": r["team"]["name"],
                "p": r["all"]["played"], "w": r["all"]["win"], "d": r["all"]["draw"], "l": r["all"]["lose"],
                "gf": r["all"]["goals"]["for"], "ga": r["all"]["goals"]["against"],
                "pts": r["points"], "zone": zone(r.get("description")), "desc": r.get("description") or "",
            } for r in g]
            res = [f for f in done if f["teams"]["home"]["id"] in ids]
            res.sort(key=lambda f: f["fixture"]["date"])
            week = None
            if res:
                m = re.search(r"(\d+)\s*$", res[-1]["league"].get("round", ""))
                week = int(m.group(1)) if m else None
            tables.append({
                "id": tid, "name": f"{name} {gname}" if gname else name,
                "short": f"{short} {gname.replace(' Grup', '') if gname in ('Beyaz Grup', 'Kırmızı Grup') else (gname or '')}".strip(),
                "apiId": lid, "season": season, "week": week, "leagueLogo": llogo,
                "table": rows,
                "results": [{"homeId": f["teams"]["home"]["id"], "home": f["teams"]["home"]["name"],
                             "awayId": f["teams"]["away"]["id"], "away": f["teams"]["away"]["name"],
                             "hs": f["goals"]["home"], "as": f["goals"]["away"],
                             "date": f["fixture"]["date"]} for f in res[-12:]],
            })
            print(f"  {tables[-1]['name']}: {len(rows)} takım, son 7 günde {len(res)} maç")

    logos = sorted(f for f in os.listdir(LOGO_DIR) if f.lower().endswith((".png", ".jpg", ".jpeg", ".svg", ".webp"))) \
        if os.path.isdir(LOGO_DIR) else []
    data = {"updated": datetime.now(TZ).strftime("%Y-%m-%d %H:%M"), "source": "API-Football",
            "tables": tables, "teams": {str(k): v for k, v in teams.items() if k}, "logos": logos}
    if not tables:
        sys.exit("Hiç tablo alınamadı; mevcut veri/data.json değiştirilmedi.")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(f"Yazıldı: veri/data.json ({len(tables)} tablo). Kullanılan istek: {calls}")


if __name__ == "__main__":
    main()
