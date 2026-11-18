# AltLigler.com

## Klasör yapısı
- `index.html` — site
- `logolar/` — kulüp ve lig logoları (kendi klasörünüzü buraya koyun)
- `veri/data.json` — otomatik güncelleme yazar (ilk çalıştırmadan önce yoktur; o zamana kadar site kendi içindeki verileri gösterir)
- `scripts/guncelle.py` — API-Football'dan verileri çeken betik
- `.github/workflows/veri.yml` — betiği her gün 23:47'de (Türkiye saati) çalıştıran görev

## Kurulum (bir kez)
1. Settings → Secrets and variables → Actions → New repository secret
   - Name: `API_FOOTBALL_KEY`
   - Secret: API-Football panelindeki anahtarınız
2. Settings → Pages → Branch: `main`, klasör `/ (root)` → Save
3. Actions sekmesi → "Veri güncelle" → Run workflow

## Yeni logo eklemek
Logolar önce `logolar/` klasöründe aranır; bulunamazsa API-Football'un gönderdiği logo kullanılır.
Kendi dosyanızı kullanmak isterseniz `logolar/` klasörüne kulübün adıyla koyun (ör. `galatasaray.png`). Site adı benzeyen dosyayı kendisi bulur.
Bulamazsa index.html'deki LOGOLAR listesine dosya adını yazın.

## Haberler
Haberler otomatik gelmez; index.html'deki `NEWS` listesine eklenir.
