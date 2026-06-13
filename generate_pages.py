# -*- coding: utf-8 -*-
"""
kredioran.com — Programmatic SEO sayfa üretici
Tutar x Vade x Kredi Türü kombinasyonları için statik landing page + sitemap üretir.
Kullanım: python3 generate_pages.py
"""
import os, json, re
from datetime import datetime, timezone, timedelta

AYLAR = ["", "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
         "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
# Türkiye saati (UTC+3, yıl boyu sabit)
_t = datetime.now(timezone(timedelta(hours=3)))
TODAY = f"{_t.day} {AYLAR[_t.month]} {_t.year}, {_t:%H:%M}"
ISO = _t.date().isoformat()

DOMAIN = "https://kredioran.com"
OUT = "site/hesaplama"

with open("rates.json", encoding="utf-8") as _f:
    RATES = json.load(_f)

# hangikredi.com en düşük oranlar (güncellenecek tek yer)
TYPES = {
    "ihtiyac": {"name": "İhtiyaç Kredisi", "icon": "💰", **RATES["ihtiyac"], "tax": True,
                "amounts": [10_000, 25_000, 50_000, 75_000, 100_000, 125_000, 150_000, 200_000, 250_000, 300_000, 500_000],
                "terms": [3, 6, 12, 24, 36]},
    "tasit":   {"name": "Taşıt Kredisi", "icon": "🚗", **RATES["tasit"], "tax": True,
                "amounts": [100_000, 200_000, 300_000, 400_000, 500_000, 750_000, 1_000_000, 1_500_000],
                "terms": [12, 24, 36, 48, 60]},
    "konut":   {"name": "Konut Kredisi", "icon": "🏠", **RATES["konut"], "tax": False,
                "amounts": [500_000, 750_000, 1_000_000, 1_500_000, 2_000_000, 3_000_000, 5_000_000],
                "terms": [60, 120, 180, 240]},
}

def bddk_max(amount):  # ihtiyaç kredisi BDDK vade sınırı
    return 36 if amount < 125_000 else (24 if amount <= 250_000 else 12)

def fmt(v):  return f"{v:,.0f}".replace(",", ".") + " TL"
def fmt0(v): return f"{v:,.0f}".replace(",", ".")

def annuity(P, rate_pct, n, taxed):
    r = (rate_pct / 100) * (1.30 if taxed else 1.0)
    pay = P / n if r == 0 else P * r * (1 + r) ** n / ((1 + r) ** n - 1)
    return pay, pay * n

def schedule_rows(P, rate_pct, n, taxed, limit=12):
    r = (rate_pct / 100) * (1.30 if taxed else 1.0)
    pay, _ = annuity(P, rate_pct, n, taxed)
    bal, rows = P, []
    for m in range(1, n + 1):
        gi = bal * r
        ni = gi / 1.30 if taxed else gi
        prin = pay - gi
        bal = max(0.0, bal - prin)
        if m <= limit or m == n:
            rows.append((m, pay, prin, ni, gi - ni, bal))
    return rows

CSS = """*{box-sizing:border-box;margin:0;padding:0}html,body{overflow-x:hidden;max-width:100%}body{font-family:'Manrope',sans-serif;color:#22325E;background:#fff;line-height:1.55}.hero>div{min-width:0}
h1,h2,.big{font-family:'Sora',sans-serif}.wrap{max-width:860px;margin:0 auto;padding:0 16px}
header{background:linear-gradient(180deg,#fff,#EAF2FF);border-bottom:1px solid #DCE7FB;padding:26px 0}
.brand{font-size:22px;font-weight:800;color:#2563EB;text-decoration:none}.brand span{color:#10B981}
h1{font-size:clamp(22px,4.5vw,32px);color:#2563EB;margin:14px 0 6px}
.upd{font-size:13px;color:#5C6FA0}
.hero{background:#2563EB;color:#fff;border-radius:18px;padding:26px;margin:26px 0;display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:18px}
.hero .l{font-size:12px;font-weight:700;color:#BFD3FF;text-transform:uppercase;letter-spacing:.06em}
.hero .v{font-family:'Sora';font-size:clamp(22px,4vw,30px);font-weight:800;margin-top:4px}.hero .v.am{color:#A7F3D0}
.note{font-size:13.5px;color:#5C6FA0;background:#F4F8FF;border-radius:12px;padding:13px 16px;margin:16px 0}
table{width:100%;border-collapse:collapse;font-size:13.5px;margin:14px 0}
.tblscroll{overflow-x:auto}th{font-size:11px;text-transform:uppercase;color:#5C6FA0;text-align:right;padding:8px 10px;border-bottom:2px solid #DCE7FB}
th:first-child,td:first-child{text-align:left}td{padding:8px 10px;text-align:right;border-bottom:1px solid #DCE7FB;font-variant-numeric:tabular-nums;white-space:nowrap}
h2{font-size:19px;color:#2563EB;margin:30px 0 10px}
.cta{display:inline-block;background:#10B981;color:#fff;font-weight:800;text-decoration:none;border-radius:12px;padding:14px 24px;margin:8px 0 4px;font-size:16px}
.cta:hover{background:#059669}
.faq h3{font-size:15.5px;color:#2563EB;margin:16px 0 5px}.faq p{font-size:14.5px;color:#3D4F82}
.rel{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0 30px}
.rel a{font-size:13px;color:#2563EB;background:#F4F8FF;border:1px solid #DCE7FB;border-radius:99px;padding:7px 14px;text-decoration:none}
.rel a:hover{border-color:#10B981}
footer{background:#F4F8FF;border-top:1px solid #DCE7FB;color:#5C6FA0;padding:22px 0;font-size:12.5px;text-align:center;margin-top:40px}
footer a{color:#2563EB}"""

def page(tkey, t, P, n):
    pay, total = annuity(P, t["rate"], n, t["tax"])
    cost = total - P
    rows = schedule_rows(P, t["rate"], n, t["tax"])
    slug = f"{tkey}-kredisi-{P}-tl-{n}-ay.html"
    title = f"{fmt0(P)} TL {t['name']} Hesaplama — {n} Ay Vade Taksiti ({TODAY})"
    desc = (f"{fmt0(P)} TL {t['name'].lower()} {n} ay vadede aylık taksiti {fmt(pay)}. "
            f"En düşük faiz %{t['rate']:.2f} ({t['bank']}). Toplam geri ödeme ve ödeme planını saniyeler içinde görün.")
    h1 = f"{fmt0(P)} TL {t['name']} — {n} Ay Vade Taksit Hesaplama"

    # vade alternatifleri tablosu
    alt_terms = [x for x in t["terms"] if tkey != "ihtiyac" or x <= bddk_max(P)]
    alt_html = "".join(
        f"<tr{' style=\"background:#ECFDF5;font-weight:700\"' if x == n else ''}>"
        f"<td>{x} ay</td><td>{fmt(annuity(P, t['rate'], x, t['tax'])[0])}</td>"
        f"<td>{fmt(annuity(P, t['rate'], x, t['tax'])[1])}</td></tr>"
        for x in alt_terms)

    plan_html = "".join(
        f"<tr><td>{m}</td><td>{fmt(p)}</td><td>{fmt(pr)}</td><td>{fmt(ni)}</td><td>{fmt(v)}</td><td>{fmt(b)}</td></tr>"
        for m, p, pr, ni, v, b in rows)
    plan_note = f"İlk 12 ay ve son ay gösterilmektedir." if n > 13 else ""

    # ilgili sayfalar (aynı tür, komşu tutarlar)
    amts = t["amounts"]; i = amts.index(P)
    rel = []
    for j in [i - 1, i + 1]:
        if 0 <= j < len(amts):
            n2 = min(n, bddk_max(amts[j])) if tkey == "ihtiyac" else n
            if n2 in t["terms"] or tkey != "ihtiyac":
                rel.append((amts[j], n2))
    for x in alt_terms:
        if x != n: rel.append((P, x))
    rel_html = "".join(
        f'<a href="{tkey}-kredisi-{a}-tl-{v}-ay.html">{fmt0(a)} TL · {v} ay</a>' for a, v in rel[:6])

    tax_line = ("Hesaplamaya KKDF (%15) ve BSMV (%15) dahildir."
                if t["tax"] else "Konut kredileri KKDF ve BSMV'den muaftır.")

    faq_items = [
        (f"{fmt0(P)} TL {t['name'].lower()}nin {n} ay vadeli aylık taksiti ne kadar?",
         f"%{t['rate']:.2f} aylık faizle ({t['bank']}, dönemin en düşük oranı) aylık taksit {fmt(pay)}, toplam geri ödeme {fmt(total)} olur. {tax_line}"),
        (f"{fmt0(P)} TL kredinin toplam maliyeti nedir?",
         f"{n} ay vadede toplam faiz ve vergi yükü yaklaşık {fmt(cost)} olur; anaparayla birlikte {fmt(total)} geri ödersiniz."),
        ("Bu oranlar güncel mi?",
         f"Oranlar HangiKredi.com'da yayımlanan en düşük banka tekliflerinden alınmıştır. Son kontrol: {TODAY}. Bankaların güncel oranları değişiklik gösterebilir."),
    ]
    faq_html = "".join(f"<h3>{q}</h3><p>{a}</p>" for q, a in faq_items)
    faq_ld = ",".join(
        '{"@type":"Question","name":"%s","acceptedAnswer":{"@type":"Answer","text":"%s"}}' % (q.replace('"', "'"), a.replace('"', "'"))
        for q, a in faq_items)

    html = f"""<!DOCTYPE html><html lang="tr"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{DOMAIN}/hesaplama/{slug}">
<meta property="og:title" content="{title}"><meta property="og:description" content="{desc}">
<meta property="og:type" content="website"><meta property="og:url" content="{DOMAIN}/hesaplama/{slug}">
<link href="https://fonts.googleapis.com/css2?family=Sora:wght@600;800&family=Manrope:wght@400;700;800&display=swap" rel="stylesheet">
<script type="application/ld+json">{{"@context":"https://schema.org","@type":"FAQPage","mainEntity":[{faq_ld}]}}</script>
<script type="application/ld+json">{{"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[
{{"@type":"ListItem","position":1,"name":"Kredi Hesaplama","item":"{DOMAIN}/"}},
{{"@type":"ListItem","position":2,"name":"{t['name']}","item":"{DOMAIN}/#{tkey}"}},
{{"@type":"ListItem","position":3,"name":"{fmt0(P)} TL {n} Ay"}}]}}</script>
<style>{CSS}</style></head><body>
<header><div class="wrap"><a class="brand" href="../index.html">kredi<span>oran</span>.com</a>
<h1>{t['icon']} {h1}</h1>
<div class="upd">Son güncelleme: {TODAY} · En düşük oran kaynağı: HangiKredi.com</div></div></header>
<main class="wrap">
<div class="hero">
  <div><div class="l">Aylık Taksit</div><div class="v am">{fmt(pay)}</div></div>
  <div><div class="l">En Düşük Faiz</div><div class="v">%{t['rate']:.2f} <span style="font-size:13px;font-weight:700;color:#BFD3FF">{t['bank']}</span></div></div>
  <div><div class="l">Toplam Geri Ödeme</div><div class="v">{fmt(total)}</div></div>
  <div><div class="l">Toplam Faiz + Vergi</div><div class="v">{fmt(cost)}</div></div>
</div>
<a class="cta" href="../index.html?tip={tkey}&tutar={P}&vade={n}">⚡ Farklı tutar / vade ile hesapla →</a>
<div class="note">{tax_line} Dosya masrafı (azami ‰5) hesaplamaya dahil değildir. Sonuçlar bilgilendirme amaçlıdır.</div>

<h2>Vade Alternatifleri — {fmt0(P)} TL için</h2>
<div class="tblscroll"><table><thead><tr><th>Vade</th><th>Aylık Taksit</th><th>Toplam Ödeme</th></tr></thead>
<tbody>{alt_html}</tbody></table></div>

<h2>Ödeme Planı</h2>
<div class="tblscroll"><table><thead><tr><th>Ay</th><th>Taksit</th><th>Anapara</th><th>Faiz</th><th>Vergi</th><th>Kalan</th></tr></thead>
<tbody>{plan_html}</tbody></table></div>
<div class="upd">{plan_note}</div>

<h2>Sık Sorulan Sorular</h2>
<div class="faq">{faq_html}</div>

<h2>İlgili Hesaplamalar</h2>
<div class="rel">{rel_html}</div>
</main>
<footer><div class="wrap">© 2026 kredioran.com — <a href="../index.html">Kredi Hesaplama</a> · Oran kaynağı: <a href="https://www.hangikredi.com" rel="noopener">HangiKredi.com</a></div></footer>
</body></html>"""
    return slug, html

def patch_index():
    """site/index.html içindeki oranları, bankaları ve tarihleri rates.json ile senkronlar."""
    path = "site/index.html"
    s = open(path, encoding="utf-8").read()

    for k in ("ihtiyac", "tasit", "konut"):
        r = RATES[k]
        # DATA satırı: bank:'X' ... rate:N ... amount:N ... term:N  (her tür tek satır)
        def sub_line(m):
            line = m.group(0)
            line = re.sub(r"bank:'[^']*'", f"bank:'{r['bank']}'", line)
            line = re.sub(r"rate:[\d.]+", f"rate:{r['rate']}", line)
            line = re.sub(r"amount:\d+", f"amount:{r['amount']}", line)
            line = re.sub(r"term:\d+", f"term:{r['term']}", line)
            return line
        s = re.sub(rf"^\s*{k}:\s*\{{.*$", sub_line, s, count=1, flags=re.M)

    # Görünen tarih
    s = re.sub(r"(Son güncelleme: <b>)[^<]*(</b>)", rf"\g<1>{TODAY}\g<2>", s)
    # Oran kaynağı satırındaki dönem bilgisi
    s = re.sub(r"değerlendirmelerinden alınmıştır \([^)]*\)",
               f"değerlendirmelerinden alınmıştır (son kontrol: {TODAY})", s)
    # FAQ + JSON-LD içindeki banka/oran cümlesi (iki yerde geçer)
    faq = (f"ihtiyaç kredisinde {RATES['ihtiyac']['bank']} (%{str(RATES['ihtiyac']['rate']).replace('.', ',')}), "
           f"taşıt kredisinde {RATES['tasit']['bank']} (%{str(RATES['tasit']['rate']).replace('.', ',')}), "
           f"konut kredisinde {RATES['konut']['bank']} (~%{str(RATES['konut']['rate']).replace('.', ',')})")
    s = re.sub(r"ihtiyaç kredisinde [^(]{2,40}\(%[\d,]+\), taşıt kredisinde [^(]{2,40}\(%[\d,]+\), "
               r"konut kredisinde [^(]{2,40}\([~%][^)]*\)", faq, s)

    open(path, "w", encoding="utf-8").write(s)
    print("site/index.html oranlarla senkronlandı.")

def main():
    os.makedirs(OUT, exist_ok=True)
    urls = []
    for tkey, t in TYPES.items():
        for P in t["amounts"]:
            for n in t["terms"]:
                if tkey == "ihtiyac" and n > bddk_max(P):
                    continue  # BDDK sınırı dışı sayfa üretme
                slug, html = page(tkey, t, P, n)
                with open(os.path.join(OUT, slug), "w", encoding="utf-8") as f:
                    f.write(html)
                urls.append(f"{DOMAIN}/hesaplama/{slug}")
    # sitemap
    sm = ['<?xml version="1.0" encoding="UTF-8"?>',
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
          f"<url><loc>{DOMAIN}/</loc><lastmod>{ISO}</lastmod><changefreq>daily</changefreq><priority>1.0</priority></url>"]
    sm += [f"<url><loc>{u}</loc><lastmod>{ISO}</lastmod><changefreq>weekly</changefreq><priority>0.8</priority></url>" for u in urls]
    sm.append("</urlset>")
    with open("site/sitemap.xml", "w", encoding="utf-8") as f:
        f.write("\n".join(sm))
    with open("site/robots.txt", "w", encoding="utf-8") as f:
        f.write(f"User-agent: *\nAllow: /\nSitemap: {DOMAIN}/sitemap.xml\n")
    print(f"{len(urls)} landing page + sitemap.xml + robots.txt üretildi.")

def run():
    patch_index()
    main()

if __name__ == "__main__":
    run()
