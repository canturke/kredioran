# -*- coding: utf-8 -*-
"""
update_rates.py — hangikredi.com'dan en düşük oranları çekip rates.json'ı günceller.
Sayfa yapısı değişir veya istek başarısız olursa ESKİ ORAN KORUNUR (site asla bozulmaz).
"""
import html as htmllib
import json, re, sys
from datetime import date

import requests

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
    r"(\d+)\s*ay\s*vadeli\s*([\d.]+)\s*TL[^%]{0,80}?"
    r"en avantajl[ıi] teklifi sunan banka\s*%\s*([\d,.]+)\s*"
    r"(?:Faiz|K[âa]r\s*Pay[ıi])\s*oran[ıi]\s*ile\s*([^.]{2,60}?)\s*oldu",
    re.S,
)

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; KrediOranBot/1.0; +https://kredioran.com)"}


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

    changed = False
    for key, url in PAGES.items():
        try:
            html = requests.get(url, headers=HEADERS, timeout=30).text
            new = parse(html)
            if new is None:
                print(f"[UYARI] {key}: cümle bulunamadı/parse edilemedi — eski oran korunuyor "
                      f"(%{rates[key]['rate']} {rates[key]['bank']})")
                continue
            if new != rates[key]:
                print(f"[GÜNCELLENDİ] {key}: %{rates[key]['rate']} {rates[key]['bank']} → "
                      f"%{new['rate']} {new['bank']} ({new['term']} ay, {new['amount']} TL)")
                rates[key] = new
                changed = True
            else:
                print(f"[AYNI] {key}: %{new['rate']} {new['bank']}")
        except Exception as e:
            print(f"[HATA] {key}: {e} — eski oran korunuyor")

    rates["updated"] = date.today().isoformat()
    with open("rates.json", "w", encoding="utf-8") as f:
        json.dump(rates, f, ensure_ascii=False, indent=2)

    # Çıkış kodu 0 her durumda — pipeline tarihi tazeleyip siteyi yeniden üretir
    print("changed" if changed else "no-change")


if __name__ == "__main__":
    main()
