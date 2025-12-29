# GestureHero (GestHero)

Manifest V3 tabanli, sifir bagimlilikli bir mouse gesture eklentisi. Tek komutla
tum dosyalari olusturur ve Chrome/Edge/Brave gibi Chromium tabanli tarayicilarda
calisir.

## Ozellikler

- Sag/orta/sol mouse butonu secilebilir.
- U/D/L/R + diagonal (UR/UL/DR/DL) hareketleri.
- Zengin aksiyon seti: tab islemleri, zoom, fullscreen, link/selection eylemleri.
- Ayarlar sayfasi: gesture listesi, presetler, import/export.
- Cizim trail rengi/kalinligi/fade, debug log toplama.

## Kurulum

1. Proje klasorunde:
   ```bash
   python3 build_extension.py
   ```
2. Chrome: `chrome://extensions`
3. Developer mode ac
4. **Load unpacked** -> `GestHero/` klasorunu sec

Not: Ikonlar icin `gestHero.svg` varsa PNG uretmeye calisir. `cairosvg`,
`rsvg-convert` veya macOS `sips` varsa otomatik donusur. Yoksa yerel PNG
fallback kullanilir.

## Kullanim

- Right click basili tutup cizim yap.
- Options sayfasindan gesture listesi ve ayarlari duzenle.
- Diagonaller token olarak girilir: `UR`, `UL`, `DR`, `DL`.
- Cok adimli hareketlerde bosluk kullan: `U R` gibi.

## Aksiyonlar (Ornekler)

- `new_tab`, `close_tab`, `reload_tab`, `reopen_closed_tab`
- `switch_tab_left/right`, `switch_tab_first/last`
- `move_tab_left/right`, `duplicate_tab`, `toggle_pin_tab`, `toggle_mute_tab`
- `zoom_in/out/reset`, `toggle_fullscreen`
- `open_link_new_tab/background/new_window`, `copy_link_url`
- `search_selected_text`, `scroll_top/bottom`

## GitHub'dan Indirip Chromium'a Ekleme

1. GitHub repo sayfasina git
2. **Code** -> **Download ZIP**
3. ZIP dosyasini cikart
4. Klasor icinde:
   ```bash
   python3 build_extension.py
   ```
5. Chrome/Edge/Brave: `chrome://extensions`
6. Developer mode ac
7. **Load unpacked** -> `GestHero/` klasorunu sec

## Debug Log

1. Options -> Debug -> **Enable debug logging**
2. Gesture dene
3. **Export Debug Log** ile `gesture_debug_log.json` al

## Notlar

- Content script tum sitelerde calisir. Sorunlu siteler icin "Disable on Sites"
  listesi kullan.
- Gesture algisi icin esik degerleri ayarlardan degistirilebilir.
