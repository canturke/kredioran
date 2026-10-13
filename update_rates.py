# -*- coding: utf-8 -*-
"""Kredi oranlarını doğrulanmış karşılaştırma sayfalarından günceller."""
import html as htmllib
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

TR = timezone(timedelta(hours=3))

TARGETS = {
    "ihtiyac": {"amount": 10_000, "term": 36},
    "tasit": {"amount": 200_000, "term": 48},
    "konut": {"amount": 500_000, "term": 120},
}

SOURCES = {
    "hesapkurdu": {
        "ihtiyac": "https://www.hesapkurdu.com/ihtiyac-kredisi/36-ay-10000-tl",
        "tasit": "https://www.hesapkurdu.com/tasit-kredisi/48-ay-200000-tl-tl-ikinci-el",
        "konut": "https://www.hesapkurdu.com/konut-kredisi/120-ay-500000-tl",
    },
    "enuygun": {
        "ihtiyac": "https://www.enuygun.com/kredi/ihtiyac-kredisi/",
        "tasit": "https://www.enuygun.com/kredi/tasit-kredisi/",
        "konut": "https://www.enuygun.com/kredi/konut-kredisi/",
    },
}

BANKS = (
    "Alternatif Bank", "Albaraka Türk", "Anadolubank", "Aktif Bank", "Akbank",
    "CEPTETEB", "DenizBank", "Dünya Katılım", "Enpara.com", "Garanti BBVA",
    "GetirFinans", "getirfinans", "Halkbank", "HSBC", "ICBC Turkey", "ING",
    "İş Bankası", "Kuveyt Türk", "ON Dijital Bankacılık", "QNB", "Şekerbank",
    "TEB", "Türkiye Finans Katılım Bankası", "Vakıf Katılım", "Yapı Kredi",
    "Ziraat Bankası", "Ziraat Katılım",
)

HEADERS = {
    "User-Agent": "KrediOranBot/2.0 (+https://kredioran.com)",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.7",
}
BLOCK_MARKERS = (
    "sorry, you have been blocked", "attention required!", "verify you are human",
    "checking your browser", "cf-ray",
)


def clean(raw: str) -> str:
    text = htmllib.unescape(raw)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    text = re.sub(r"<script\b.*?</script>|<style\b.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def build_session():
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    retry = Retry(total=2, connect=2, read=2, backoff_factor=2,
                  status_forcelist=(429, 500, 502, 503, 504), allowed_methods=("GET",),
                  respect_retry_after_header=True)
    session = requests.Session()
    session.headers.update(HEADERS)
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


def fetch(session, source, key, url):
    response = session.get(url, timeout=35)
    content_type = response.headers.get("content-type", "")
    print(f"[HTTP] {source}/{key}: status={response.status_code}, type={content_type or '-'}, size={len(response.content)}")
    response.raise_for_status()
    if "html" not in content_type.lower():
        raise ValueError(f"beklenmeyen içerik tipi: {content_type or 'bilinmiyor'}")
    if any(marker in response.text.lower() for marker in BLOCK_MARKERS):
        raise RuntimeError("bot koruması yanıtı")
    return response.text


def load_pages():
    snapshot_path = os.getenv("RATE_SNAPSHOT_FILE")
    if snapshot_path:
        with open(snapshot_path, encoding="utf-8") as handle:
            snapshot = json.load(handle)
        pages = {}
        for source, categories in snapshot.get("pages", {}).items():
            pages[source] = {}
            for key, result in categories.items():
                status = int(result.get("status", 0))
                body = result.get("body", "")
                print(f"[KRIWEB] {source}/{key}: status={status}, size={len(body)}")
                if status == 200 and body:
                    pages[source][key] = body
        return pages

    import requests
    session = build_session()
    pages = {}
    for source, categories in SOURCES.items():
        pages[source] = {}
        for key, url in categories.items():
            try:
                pages[source][key] = fetch(session, source, key, url)
            except (requests.RequestException, ValueError, RuntimeError) as exc:
                print(f"[KAYNAK HATASI] {source}/{key}: {exc}")
    return pages


def _page_matches_target(text, amount, term):
    amount_text = f"{amount:,}".replace(",", ".")
    amount_ok = re.search(rf"{re.escape(amount_text)}\s*TL", text, re.I)
    term_ok = re.search(rf"{term}\s*Ay", text, re.I)
    return bool(amount_ok and term_ok)


def parse_offers(raw_html, amount, term):
    """Kampanya kartlarını değil, toplam ödeme içeren gerçek kredi tekliflerini seç."""
    text = clean(raw_html)
    if not _page_matches_target(text, amount, term):
        return None
    offers = []
    for bank in BANKS:
        for match in re.finditer(re.escape(bank), text, re.I):
            window = text[match.start():match.start() + 420]
            rate_match = re.search(
                r"(?:Faiz\s*Oran[ıi]|K[âa]r\s*Pay[ıi]|Ayl[ıi]k\s*Faiz)\s*%?\s*([0-9]+(?:[,.][0-9]+)?)"
                r".{0,180}?Toplam\s*(?:Geri\s*)?[ÖO]deme",
                window, re.I | re.S,
            )
            if not rate_match:
                continue
            rate = float(rate_match.group(1).replace(",", "."))
            if 0.1 <= rate <= 15:
                offers.append((rate, bank))
    if not offers:
        return None
    best_rate = min(rate for rate, _ in offers)
    best_banks = sorted({bank for rate, bank in offers if abs(rate - best_rate) < 0.001})
    return {"bank": ", ".join(best_banks), "rate": best_rate, "amount": amount, "term": term}


def choose_rate(key, pages):
    target = TARGETS[key]
    primary = parse_offers(pages.get("hesapkurdu", {}).get(key, ""), **target)
    secondary = parse_offers(pages.get("enuygun", {}).get(key, ""), **target)
    if primary and secondary:
        difference = abs(primary["rate"] - secondary["rate"])
        if difference > 0.75:
            raise ValueError(f"kaynaklar arası oran farkı yüksek: %{primary['rate']} / %{secondary['rate']}")
        primary["source"] = "Hesapkurdu (Enuygun ile doğrulandı)"
        print(f"[DOĞRULANDI] {key}: Hesapkurdu %{primary['rate']}, Enuygun %{secondary['rate']}")
        return primary
    if primary:
        primary["source"] = "Hesapkurdu"
        print(f"[ANA KAYNAK] {key}: Enuygun doğrulaması yok; Hesapkurdu sonucu kullanılıyor")
        return primary
    if secondary:
        secondary["source"] = "Enuygun (yedek)"
        print(f"[YEDEK KAYNAK] {key}: Hesapkurdu okunamadı; Enuygun sonucu kullanılıyor")
        return secondary
    return None


def main():
    with open("rates.json", encoding="utf-8") as handle:
        rates = json.load(handle)
    pages = load_pages()
    now_iso = datetime.now(TR).isoformat(timespec="minutes")
    changed, succeeded, failed = False, [], []

    for key in TARGETS:
        try:
            new = choose_rate(key, pages)
        except ValueError as exc:
            new = None
            failed.append((key, str(exc)))
        if new is None:
            if not any(item[0] == key for item in failed):
                failed.append((key, "hedef tutar/vadeye ait doğrulanabilir teklif bulunamadı"))
            print(f"[KORUNDU] {key}: eski doğrulanmış oran korunuyor")
            continue

        current = {field: rates[key].get(field) for field in ("bank", "rate", "amount", "term")}
        comparable = {field: new[field] for field in ("bank", "rate", "amount", "term")}
        old_updated = rates[key].get("updated", rates.get("updated"))
        if comparable != current:
            new["updated"] = now_iso
            changed = True
            print(f"[GÜNCELLENDİ] {key}: %{current['rate']} {current['bank']} → %{new['rate']} {new['bank']}")
        elif old_updated:
            new["updated"] = old_updated
        new["checked"] = now_iso
        rates[key] = new
        succeeded.append(key)

    legacy_checked = rates.get("checked", now_iso)
    rates["checked"] = min(rates[key].get("checked", legacy_checked) for key in TARGETS)
    if changed or "T" not in str(rates.get("updated", "")):
        rates["updated"] = now_iso
    with open("rates.json", "w", encoding="utf-8") as handle:
        json.dump(rates, handle, ensure_ascii=False, indent=2)

    print("changed" if changed else "no-change")
    if failed:
        summary = "; ".join(f"{key}: {reason}" for key, reason in failed)
        if succeeded:
            print(f"::warning::Kısmi oran güncellemesi. {summary}")
        else:
            print(f"::error::Hiçbir kategori doğrulanamadı. {summary}. Site yayınlanmadı.")
            sys.exit(1)


if __name__ == "__main__":
    main()
