# AltLigler.com

## Klasör yapısı
- `index.html` — site
- `logolar/` — kulüp ve lig logoları (kendi klasörünüzü buraya koyun)
- `veri/data.json` — otomatik güncelleme yazar (ilk çalıştırmadan önce yoktur; o zamana kadar site kendi içindeki verileri gösterir)
- `scripts/guncelle.py` — TFF'nin puan cetveli sayfalarından verileri okuyan betik (anahtar gerekmez)
- `.github/workflows/veri.yml` — betiği her gün 23:47'de (Türkiye saati) çalıştıran görev

## Kurulum (bir kez)
1. Settings → Pages → Branch: `main`, klasör `/ (root)` → Save
2. Actions sekmesi → "Veri güncelle" → Run workflow

## Yeni logo eklemek
Kendi dosyanızı kullanmak isterseniz `logolar/` klasörüne kulübün adıyla koyun (ör. `galatasaray.png`). Site adı benzeyen dosyayı kendisi bulur.
Bulamazsa index.html'deki LOGOLAR listesine dosya adını yazın.

## Haberler
Haberler otomatik gelmez; index.html'deki `NEWS` listesine eklenir.
