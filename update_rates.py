# -*- coding: utf-8 -*-
"""
update_rates.py — hangikredi.com'dan en düşük oranları çekip rates.json'ı günceller.
Sayfa yapısı değişir veya istek başarısız olursa ESKİ ORAN KORUNUR (site asla bozulmaz).
"""
import html as htmllib
import json, re, sys
from datetime import datetime, timezone, timedelta

TR = timezone(timedelta(hours=3))  # Türkiye saati (yıl boyu sabit)

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

PAGES = {
    "ihtiyac": "https://www.hangikredi.com/kredi/ihtiyac-kredisi",
    "tasit":   "https://www.hangikredi.com/kredi/tasit-kredisi",
    "konut":   "https://www.hangikredi.com/kredi/konut-kredisi",
}

# hangikredi cümlesi (tag/HTML-yorumları temizlendikten sonra), ör:
#   "... 36 ay vadeli 10.000 TL İhtiyaç Kredisi için en avantajlı teklifi sunan
#    banka %2,99 Faiz oranı ile ING,DenizBank oldu."
# Katılım bankalarında "Faiz oranı" yerine "Kâr Payı oranı" yazar.
PATTERN = re.compile(
    r"(\d+)\s*ay\s*vadeli\s*([\d.]+)\s*TL.{0,300}?"
    r"en avantajl[ıi].{0,120}?%\s*([\d,.]+)\s*"
    r"(?:Faiz|K[âa]r\s*Pay[ıi])\s*oran[ıi](?:\s*ile|yla|yle)?\s*"
    r"([^.]{2,80}?)\s*oldu",
    re.I | re.S,
)

HEADERS = {
    "User-Agent": "KrediOranBot/1.1 (+https://kredioran.com)",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.7",
}
BLOCK_MARKERS = (
    "sorry, you have been blocked",
    "attention required!",
    "verify you are human",
    "checking your browser",
    "cf-ray",
)


def build_session():
    """Geçici sunucu/rate-limit hatalarını sınırlı ve gecikmeli olarak tekrar dene."""
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        backoff_factor=2,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
        respect_retry_after_header=True,
    )
    session = requests.Session()
    session.headers.update(HEADERS)
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


def fetch(session, key, url):
    """HTTP, içerik tipi ve güvenlik engelini parse hatasından ayır."""
    response = session.get(url, timeout=30)
    content_type = response.headers.get("content-type", "")
    print(
        f"[HTTP] {key}: status={response.status_code}, "
        f"type={content_type or '-'}, size={len(response.content)}"
    )
    response.raise_for_status()
    if "html" not in content_type.lower():
        raise ValueError(f"beklenmeyen içerik tipi: {content_type or 'bilinmiyor'}")
    body = response.text
    low = body.lower()
    if any(marker in low for marker in BLOCK_MARKERS):
        raise RuntimeError("Cloudflare/bot koruması yanıtı")
    return body


def clean(raw: str) -> str:
    """HTML entity'lerini çöz, yorum ve etiketleri at, boşlukları sadeleştir."""
    t = htmllib.unescape(raw)
    t = re.sub(r"<!--.*?-->", "", t, flags=re.S)
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", t)


def parse(html: str):
    m = PATTERN.search(clean(html))
    if not m:
        return None
    term = int(m.group(1))
    amount = int(m.group(2).replace(".", ""))
    rate = float(m.group(3).replace(",", "."))
    bank = re.sub(r"\s*,\s*", ", ", m.group(4).strip())
    # Mantık kontrolleri — saçma değer geldiyse reddet
    if not (0.1 <= rate <= 15 and 3 <= term <= 360 and 1_000 <= amount <= 50_000_000 and 2 <= len(bank) <= 40):
        return None
    return {"bank": bank, "rate": rate, "amount": amount, "term": term}


def main():
    with open("rates.json", encoding="utf-8") as f:
        rates = json.load(f)

    now = datetime.now(TR)
    now_iso = now.isoformat(timespec="minutes")
    changed = False
    succeeded = []
    failed = []
    session = build_session()
    for key, url in PAGES.items():
        try:
            page_html = fetch(session, key, url)
        except (requests.RequestException, ValueError, RuntimeError) as e:
            failed.append((key, f"HTTP/kaynak hatası: {e}"))
            print(f"[KAYNAK HATASI] {key}: {e} — eski oran korunuyor")
            continue

        new = parse(page_html)
        if new is None:
            failed.append((key, "beklenen oran cümlesi bulunamadı"))
            print(f"[PARSE HATASI] {key}: beklenen oran cümlesi bulunamadı. "
                  f"Eski oran korunuyor (%{rates[key]['rate']} {rates[key]['bank']}).")
            continue

        cur = {k: rates[key].get(k) for k in ("bank", "rate", "amount", "term")}
        old_updated = rates[key].get("updated", rates.get("updated"))
        if new != cur:
            print(f"[GÜNCELLENDİ] {key}: %{cur['rate']} {cur['bank']} → "
                  f"%{new['rate']} {new['bank']} ({new['term']} ay, {new['amount']} TL)")
            new["updated"] = now_iso
            changed = True
        else:
            print(f"[AYNI] {key}: %{new['rate']} {new['bank']}")
            if old_updated:
                new["updated"] = old_updated
        new["checked"] = now_iso
        rates[key] = new
        succeeded.append(key)

    # Geriye dönük uyumluluk: üst seviye checked, üç kategorinin de doğrulandığı en eski zamanı gösterir.
    legacy_checked = rates.get("checked", now_iso)
    checked_values = [rates[key].get("checked", legacy_checked) for key in PAGES]
    rates["checked"] = min(checked_values)
    if changed or "T" not in str(rates.get("updated", "")):
        rates["updated"] = now_iso

    with open("rates.json", "w", encoding="utf-8") as f:
        json.dump(rates, f, ensure_ascii=False, indent=2)

    print("changed" if changed else "no-change")

    if failed:
        summary = "; ".join(f"{key}: {reason}" for key, reason in failed)
        if succeeded:
            print(f"::warning::Kısmi oran güncellemesi. {summary}. "
                  "Başarısız kategorilerde eski doğrulanmış oran ve tarih korundu.")
        else:
            print(f"::error::Hiçbir oran kaynağı doğrulanamadı. {summary}. Site yayınlanmadı.")
            sys.exit(1)


if __name__ == "__main__":
    main()
