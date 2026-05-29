# GestHero — Proje Analiz Raporu

> Hazırlanma tarihi: 2026-05-29
> Kapsam: Depo kök dizini (`build_extension.py`) ve üretilen eklenti paketi (`gestHero/`)
> İncelenen sürüm: `manifest.json` v1.0.0 (Manifest V3)

---

## 1. Yönetici Özeti

GestHero, Chromium tabanlı tarayıcılar için yazılmış, bağımlılığı olmayan (vanilla JS)
sade bir mouse-gesture eklentisidir. Mimari açıdan **temiz, okunabilir ve iyi
modüllere ayrılmış** durumdadır: gesture algılama (`content.js`), aksiyon yürütme
(`background.js`) ve ayar yönetimi (`options.*`) sorumlulukları net biçimde
ayrılmıştır. Özellik seti (preset'ler, import/export, site bazlı devre dışı bırakma,
diagonal hareketler, görsel trail, debug log) bu boyuttaki bir eklenti için zengindir.

Bununla birlikte projenin **sürdürülebilirliğini ve güvenilirliğini doğrudan tehdit
eden** birkaç yapısal sorun var. En önemlisi, tüm kaynak kodun hem `gestHero/`
klasöründe hem de `build_extension.py` içinde Python string'i olarak **iki kez** var
olması. İkinci en önemli eksik ise, `technical_journey.md`'de görülen yoğun
deneme-yanılma sürecine rağmen **hiçbir otomatik test ve CI** bulunmaması.

**Genel durum:** Çalışan, kullanışlı bir ürün; ancak teknik borç birikmeye başlamış.
Aşağıdaki öneriler kod davranışını değiştirmeden bakım maliyetini ciddi biçimde düşürür.

---

## 2. Mimari Genel Bakış

| Bileşen        | Dosya                                  |     Satır | Sorumluluk                                                             |
| -------------- | -------------------------------------- | --------: | ---------------------------------------------------------------------- |
| Build/üretici  | `build_extension.py`                   |      2279 | Eklenti dosyalarını gömülü string'lerden üretir, SVG→PNG ikon dönüşümü |
| Content script | `gestHero/content.js`                  |      1030 | Mouse olayları, gesture algılama, çizim, context-menu yönetimi         |
| Service worker | `gestHero/background.js`               |       286 | Sekme/pencere/zoom aksiyonları, debug log toplama                      |
| Ayarlar UI     | `gestHero/options.html` / `options.js` | 364 / 405 | Gesture tablosu, ayarlar, preset/import/export                         |
| Manifest       | `gestHero/manifest.json`               |        43 | MV3 tanımı                                                             |

**Veri akışı:** `options.js` → `chrome.storage.sync` → `content.js` (gesture algılar) →
`chrome.runtime.sendMessage` → `background.js` (aksiyonu yürütür). Temiz ve standart.

---

## 3. Güçlü Yönler

- **Sıfır bağımlılık, sıfır build-toolchain zorunluluğu.** Klasör doğrudan `Load
unpacked` ile yüklenebiliyor.
- **Net sorumluluk ayrımı** ve tutarlı kod stili.
- **Saf (pure) ve test edilmeye çok uygun fonksiyonlar**: `tokenizeSequence`,
  `collapseRepeats`, `simplifyTokens`, `normalizeSequence`, `getDirection`.
- **İyi savunmacı kodlama**: `blur`/`visibilitychange` ile gesture iptali, buton
  maskesi kontrolü, `chrome.runtime.lastError` kontrolünün bazı yerlerde yapılması.
- **Platforma duyarlılık**: macOS'ta çift sağ tık, Windows/Linux'ta hold-delay ile
  context-menu ayrımı düşünülmüş.
- **Şeffaf geliştirme günlüğü** (`technical_journey.md`) — kararların izlenebilirliği iyi.

---

## 4. Sorunlar ve Çözüm Önerileri

Önem derecesi: 🔴 Yüksek · 🟡 Orta · 🟢 Düşük

### 🔴 S1 — Kaynak kodun iki yerde birebir tekrarı (en kritik)

`build_extension.py`, `content.js`/`background.js`/`options.js`/`options.html`
içeriğinin **tamamını** `textwrap.dedent("""...""")` string'leri olarak barındırıyor
(örn. `build_extension.py:49` BACKGROUND_JS, ardından CONTENT_JS, OPTIONS_HTML,
OPTIONS_JS). Aynı kod `gestHero/` altında da commit'li. Build çıktısı bugün
birebir aynı (drift yok — doğrulandı), ama:

- Her değişiklik **iki yerde** yapılmak zorunda; biri unutulursa sessiz drift oluşur.
- JS, Python string'i içinde olduğu için editör/linter/syntax-highlight desteği yok.
- 2279 satırlık dosyanın ~2150 satırı yalnızca gömülü kaynak.

**Çözüm (önerilen):** Tek bir doğruluk kaynağı (single source of truth) belirle.
`gestHero/` altındaki dosyalar canonical olsun. `build_extension.py` yalnızca:

1. Gerçek dosyaları kopyalasın/derlesin (string gömme yerine `shutil.copy`),
2. SVG→PNG ikon üretsin,
3. İsteğe bağlı dağıtım için `.zip` paketi oluştursun.

Alternatif (daha hızlı): Klasör zaten doğrudan yüklenebildiğinden, build script'i
yalnızca ikon üretimi + zip'leme ile sınırla; ~2000 satır gömülü kodu sil.

> Bu tek değişiklik bakım yükünü yaklaşık yarıya indirir ve drift riskini sıfırlar.

### 🔴 S2 — İsim/branding tutarsızlığı

`manifest.json:2` ve `:19` → `"Simple Gestures"`. Oysa README "GestureHero",
`options.html:5` başlık "GestHero". Sonuç: kullanıcı `chrome://extensions`'ta
eklentiyi **"Simple Gestures"** olarak görür; export dosya adı da
`simple_gestures_settings.json` (`options.js:329`). Marka kafa karışıklığı yaratır.

**Çözüm:** Tek isimde karar ver (ör. "GestHero"). `manifest.json` (hem build script
`build_extension.py:18,26` hem üretilen dosya), `options.html` başlığı ve export
dosya adlarını hizala.

### 🔴 S3 — Otomatik test ve CI yokluğu

4400+ satır JS için sıfır test. `technical_journey.md`'deki uzun context-menu
hata-düzeltme zinciri (özellikle 2025-12-29/30 kayıtları), regresyona en açık alanın
tam burası olduğunu gösteriyor. Saf fonksiyonlar test edilmeye hazır.

**Çözüm:**

- `tokenizeSequence`, `collapseRepeats`, `simplifyTokens`, `normalizeSequence`,
  `getDirection`, `getAxisDistance` için birim testleri (Node + Vitest/Jest; DOM
  gerekmez — bu fonksiyonları küçük bir modüle ayırıp hem content.js hem teste import et).
- Manifest doğrulaması ve "build çıktısı = commit'li dosyalar" eşitliğini kontrol eden
  bir CI adımı (GitHub Actions). Bu, S1 kalana kadar drift'i otomatik yakalar.
- `eslint` + `prettier` ile statik analiz.

### 🟡 S4 — MV3 service worker'da kalıcı olmayan debug log

`background.js:4` `debugEvents` dizisi yalnızca RAM'de. MV3 service worker'ları ~30 sn
boştan sonra sonlandırılır; bu durumda toplanan log kaybolur. Ayrıca `content.js:53`
kendi `debugEvents` kopyasını tutuyor ama export bunu hiç kullanmıyor (export sadece
`background`'tan okuyor — `options.js:361`). Yani worker yeniden başlarsa log eksik gelir.

**Çözüm:** Debug olaylarını `chrome.storage.local`'a yaz (kota dostu, döngüsel tampon),
veya content.js'teki yerel tamponu da export'a dahil et. En azından README'ye "debug
logu kalıcı değildir" notu düşülmeli.

### 🟡 S5 — `chrome.runtime.sendMessage` çağrılarında `lastError` kontrolü eksik

`content.js:219` (logDebug) ve `:775` (handleGesture) yanıt beklemeden mesaj atıyor.
Service worker uykudaysa/alıcı yoksa konsola "Unchecked runtime.lastError" uyarıları
düşebilir.

**Çözüm:** Callback ekleyip `chrome.runtime.lastError`'ı sessizce tüket, ya da
`.catch()` ile promise tabanlı API kullan.

### 🟡 S6 — Aşırı geniş izinler ve iframe davranışı

- `host_permissions: ["<all_urls>"]` + content script tüm sayfalarda. Mağaza incelemesi
  ve gizlilik açısından gerekçelendirme gerektirir (README'de kısmen var).
- `content_scripts` içinde `all_frames` tanımlı değil (`manifest.json:32`) → gesture'lar
  iframe içinde çalışmaz. Bu bilinçli bir tercih olabilir ama dokümante edilmemiş.

**Çözüm:** İzin gereksinimini README/mağaza açıklamasında net gerekçelendir. iframe
davranışını ya dokümante et ya da `all_frames: true` ile destekle (dikkat: çoklu canvas
çakışması olabilir).

### 🟢 S7 — Deprecated `navigator.platform`

`content.js:35` `IS_MAC` tespiti için `navigator.platform` kullanıyor (deprecated).

**Çözüm:** `navigator.userAgentData?.platform` öncelikli, `navigator.platform` fallback.

### 🟢 S8 — `getDirection` mantığında fazlalık

`content.js:386-426` hem açı-temelli (atan2 + tolerance) hem oran-temelli (bias) iki
ayrı yön kararı barındırıyor; ikisi kısmen örtüşüyor ve okunması zor.

**Çözüm:** Tek yaklaşıma indir (tercihen açı eşikleri). Davranışı koruduğundan emin olmak
için önce S3'teki testleri yaz.

### 🟢 S9 — i18n / dil tutarsızlığı

README Türkçe, UI ve manifest İngilizce, `_locales` yok.

**Çözüm:** Mağaza hedefleniyorsa `chrome.i18n` + `_locales/` ile en az EN/TR.

### 🟢 S10 — Sürüm yönetimi ve dokümantasyon

- `version` sabit `1.0.0`; build sırasında bump yok, `CHANGELOG.md` yok.
- Dokunmatik/kalem (pointer events) desteklenmiyor — yalnızca mouse olayları.

**Çözüm:** `CHANGELOG.md` ekle; sürümü build argümanıyla bump edilebilir yap.

---

## 5. İyileştirme ve Geliştirme Önerileri (Yeni Özellikler)

Mevcut mimariye doğal oturanlar:

1. **Rocker / wheel gesture'ları** — sağ+sol tık kombinasyonu, gesture sırasında scroll
   ile sekme değiştirme (FoxyGestures/Gesturefy paritesi).
2. **Gesture başına özel URL / script aksiyonu** — kullanıcı tanımlı "şu adrese git".
3. **Görsel gesture editörü** — metin token (`U R`) yerine fare ile çizdirip kaydetme;
   yeni kullanıcılar için öğrenme eğrisini düşürür.
4. **Gesture ipucu (cheat-sheet) overlay'i** — basılı tutunca olası gesture'ları gösteren
   yardımcı katman.
5. **Çakışma/duplike uyarısı** — `options.js` kaydederken aynı sequence iki aksiyona
   atanmışsa uyar.
6. **Aksiyon önizleme/geri-al** — yanlış gesture sonrası kısa "undo" toast'ı.
7. **Tema/erişilebilirlik** — options sayfasında koyu mod, trail için yüksek kontrast
   seçenekleri.
8. **Senkron yedekleme dosyası sürümleme** — import sırasında şema sürümü kontrolü
   (ileri uyumluluk).

---

## 6. Önerilen Yol Haritası

**Faz 1 — Teknik borç (davranış değişmeden):** ✅ _Tamamlandı (2026-05-29)_

- [x] S2: İsim/branding'i tek değere ("GestHero") hizalandı.
- [x] S1: Build script tek-kaynak modeline geçirildi (ikon + zip); ~2000 satır gömülü kod silindi.
- [x] S3: `gestures-core.js` çekirdeği + `node:test` birim testleri + ESLint/Prettier + GitHub Actions CI eklendi.

**Faz 2 — Sağlamlaştırma:** ✅ _Tamamlandı (2026-05-29)_

- [x] S4: Debug logu `chrome.storage.local`'a kalıcılaştırıldı (hydrate + debounce flush).
- [x] S5: `lastError` kontrolleri eklendi (content.js sendMessage çağrıları + background tabs.sendMessage).
- [x] S7: `navigator.userAgentData` öncelikli macOS tespitine geçildi (platform fallback'li).
- [x] S6: İzin gerekçeleri, iframe (top-frame only) ve pointer sınırı README'de dokümante edildi.

**Faz 3 — Ürün geliştirme:** ✅ _Tamamlandı (2026-05-29)_

- [x] S8: `getDirection` okunabilirlik için yeniden düzenlendi; davranış korundu, sınır testleri eklendi. (Not: `diagonalBias` knob'u geriye dönük uyumluluk için bilinçli olarak korundu — kaldırmak ayar göçü/kırılma getirirdi.)
- [x] Görsel gesture editörü (options'ta "Draw" ile çizerek kaydetme) + çakışma uyarısı + koyu mod eklendi. Çekirdeğe `recognizePoints`/`findConflicts`/`normalizeForMatch` (testli).
- [x] Cheat-sheet overlay: gesture çizilirken yapılandırılmış hareketleri listeleyen panel (opt-in, varsayılan kapalı; etiketler i18n'den).
- [x] S10: CHANGELOG.md eklendi; sürüm 1.2.0'a yükseltildi (manifest + package.json).
- [x] S9: i18n eklendi — `chrome.i18n` + `_locales/` (EN/TR), `default_locale: en`. Options UI, aksiyon etiketleri ve eklenti açıklaması yerelleşir.

---

## 7. Hızlı Kazanımlar (Quick Wins)

Düşük efor / yüksek etki, hemen yapılabilir:

1. **Branding hizalama** (S2) — birkaç string değişikliği.
2. **`lastError` callback'leri** (S5) — konsol gürültüsünü keser.
3. **`navigator.userAgentData` fallback'i** (S7) — geleceğe dönük güvence.
4. **README'ye not**: debug logu kalıcı değil + iframe'de çalışmaz.

---

_Not: Bu rapor yalnızca analiz amaçlıdır; mevcut çalışan koda dokunmadan hazırlanmıştır.
Önerilerin uygulanması için her madde bağımsız olarak ele alınabilir._
