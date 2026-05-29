# Changelog

Bu projedeki dikkate değer değişiklikler bu dosyada tutulur.
Format [Keep a Changelog](https://keepachangelog.com/) temellidir ve proje
[Semantic Versioning](https://semver.org/) kullanır.

## [1.1.0] - 2026-05-29

### Added

- **Görsel gesture kaydedici**: Options'taki her satırda "Draw" butonu ile
  fareyle çizerek sequence alanını doldurma (paylaşılan tanıyıcıyı kullanır).
- **Çakışma uyarısı**: Aynı kanonik diziye eşlenen gesture satırları kırmızı
  ile işaretlenir ve kaydederken uyarı gösterilir.
- **Koyu mod**: Options sayfası `prefers-color-scheme` ile sistem temasına uyar.
- Paylaşılan çekirdeğe `normalizeForMatch`, `findConflicts` ve `recognizePoints`
  fonksiyonları (birim testleriyle) eklendi.

### Changed

- `getDirection` davranışı korunarak okunabilirlik için yeniden düzenlendi;
  sınır davranışları testlerle kilitlendi (S8).
- Content script artık eşleştirme anahtarı için paylaşılan `normalizeForMatch`
  fonksiyonunu kullanıyor (tekrar azaltıldı).

## [1.0.x] - öncesi

### Added (Faz 1 — teknik borç)

- Branding "GestHero" olarak tek değere hizalandı (manifest adı/başlığı, export
  dosya adı).
- `build_extension.py` tek-kaynak modeline geçirildi: gömülü ~2000 satır kaynak
  kaldırıldı; script yalnızca ikon üretir ve `gestHero.zip` paketler.
- Paylaşılan saf gesture mantığı `gestHero/gestures-core.js` içine çıkarıldı;
  `node:test` birim testleri, ESLint + Prettier ve GitHub Actions CI eklendi.

### Changed/Fixed (Faz 2 — sağlamlaştırma)

- Debug logu `chrome.storage.local`'a kalıcılaştırıldı (MV3 service worker
  yeniden başlasa bile korunur).
- Fire-and-forget `sendMessage` çağrılarına `chrome.runtime.lastError`
  kontrolleri eklendi.
- macOS tespiti `navigator.userAgentData` önceliğine geçirildi.
- İzin gerekçeleri, top-frame-only enjeksiyon ve pointer sınırı dokümante edildi.

### Notes

- Eklenti çekirdeği başlangıçta `build_extension.py` ile üretiliyordu; gesture
  algılama, sağ tık menüsü davranışı ve görsel trail bu temele dayanır.

[1.1.0]: https://github.com/tahircengiz/gestHero
