# GestureHero

Public repo: https://github.com/tahircengiz/gestHero

GestureHero, Chromium tabanli tarayicilar icin sade ve hizli bir mouse gesture
eklentesidir. Kurulumda build adimi yoktur; hazir paket de, tek komutla uretim
de desteklenir.

## Hizli Kurulum (Hazir Paket)

1. GitHub -> Code -> Download ZIP
2. ZIP'i cikart
3. Chrome/Edge/Brave: `chrome://extensions`
4. Developer mode ac
5. **Load unpacked** -> `gestHero/` klasorunu sec

## Gelistirme

Eklentinin tek dogruluk kaynagi (single source of truth) `gestHero/` klasorudur;
dosyalar dogrudan duzenlenir. Paylasilan saf gesture mantigi
`gestHero/gestures-core.js` icinde olup hem content script hem options sayfasi hem
de testler tarafindan kullanilir.

```bash
npm install        # gelistirme bagimliliklarini kurar (eslint, prettier)
npm test           # node:test ile birim testleri (cekirdek gesture mantigi)
npm run lint       # eslint
npm run format     # prettier ile bicimlendirir
```

CI (GitHub Actions) her push/PR'de lint + format + test + build calistirir.

## Paketleme (Dagitim Icin)

```bash
python3 build_extension.py        # ikonlari yeniler ve gestHero.zip uretir
python3 build_extension.py --no-zip
```

Bu komut **JS/HTML uretmez**; yalnizca (1) `gestHero.svg`'den PNG ikonlari
yenilemeye calisir ve (2) magaza/dagitim icin `gestHero.zip` olusturur.

Not: Ikonlar icin `gestHero.svg` varsa PNG uretmeye calisir. `cairosvg`,
`rsvg-convert` veya macOS `sips` varsa otomatik donusur. Yoksa mevcut commit'li
PNG'ler korunur.

## Ozellikler

- Sag/orta/sol mouse butonu secilebilir
- U/D/L/R + diagonal (UR/UL/DR/DL) hareketleri
- Tab kontrolu, zoom, fullscreen, link/selection aksiyonlari
- Presetler, import/export, site bazli devre disi
- Renkli trail ve debug log

## Kullanim

- Secilen mouse butonunu basili tutup cizim yap
- Options sayfasindan gesture listesi ve ayarlari duzenle
- Diagonaller token olarak girilir: `UR`, `UL`, `DR`, `DL`
- Cok adimli hareketlerde bosluk kullan: `U R`
- **macOS (Chrome/Brave)**: Native sag menu icin **cift sag tik** kullan.
- **Windows/Linux**: Kisa sag tik menu acar, uzun basili tutma gesture baslatir.
- "Hold delay (ms)" ile menu/gesture esigini ayarlayabilirsin.

## Debug Log

1. Options -> Debug -> **Enable debug logging**
2. Gesture dene
3. **Export Debug Log** ile `gesture_debug_log.json` al

## Guvenlik

- Content script tum sayfalarda calisir (`<all_urls>`). Gerekirse "Disable on
  Sites" listesi ile sinirla.
