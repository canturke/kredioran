# kredioran.com — Otomatik Oran Güncelleme

## Nasıl çalışır
Her gün 07:00'de (TR) GitHub Actions:
1. `update_rates.py` → hangikredi.com'dan 3 kredi türünün en düşük oranını çeker, `rates.json`'a yazar.
   Çekemezse/parse edemezse **eski oran korunur**, site bozulmaz.
2. `generate_pages.py` → `site/` altında ana sayfayı yamalar, 115 landing page'i, sitemap'i yeniden üretir, tarihleri tazeler.
3. `site/` klasörü FTP ile Kriweb'e yüklenir (sadece değişen dosyalar).

## Kurulum (tek seferlik)
1. GitHub'da private repo açın, bu klasörü push edin.
2. Repo → Settings → Secrets and variables → Actions → New repository secret ile 4 secret ekleyin:
   - `FTP_SERVER`    → Kriweb FTP adresi (ör. ftp.kredioran.com)
   - `FTP_USERNAME`  → FTP kullanıcı adı
   - `FTP_PASSWORD`  → FTP şifresi
   - `FTP_REMOTE_DIR`→ Site kök dizini, sonu / ile (ör. /httpdocs/ veya /wwwroot/)
3. Actions sekmesi → "Günlük Oran Güncelleme" → **Run workflow** ile ilk çalıştırmayı elle yapın, logları izleyin.

## Elle oran düzeltme
`rates.json`'ı düzenleyip push'layın → workflow'u elle tetikleyin. Scraper bir sonraki gün
hangikredi'de farklı değer görürse üzerine yazar.

## Notlar
- Scraper hangikredi'nin "en avantajlı teklifi sunan banka ... oldu" cümlesini okur; sayfa
  yapısı değişirse Action log'unda [UYARI] görürsünüz — o tür eski oranla devam eder.
- Mantık filtreleri var: %0.1-15 dışı oran, saçma vade/tutar reddedilir.
