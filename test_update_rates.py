import unittest

import update_rates


class ParserTests(unittest.TestCase):
    def test_selects_lowest_real_offer_and_skips_campaign(self):
        page = """
        <h1>10.000 TL 36 Ay Vadeli İhtiyaç Kredileri</h1>
        <div>Faizsiz Fırsat QNB Faiz Oranı %0 Toplam 85.000 TL</div>
        <div>İhtiyaç Kredisi QNB Faiz Oranı %3,04 Toplam Ödeme 18.963 TL Aylık Taksit 525 TL</div>
        <div>İhtiyaç Kredisi DenizBank Faiz Oranı %2,89 Toplam Ödeme 18.454 TL</div>
        """
        self.assertEqual(update_rates.parse_offers(page, 10000, 36), {
            "bank": "DenizBank", "rate": 2.89, "amount": 10000, "term": 36,
        })

    def test_preserves_multiple_banks_at_same_rate(self):
        page = """
        <h1>500.000 TL 120 Ay Vadeli Konut Kredileri</h1>
        <div>Konut Finansmanı Kuveyt Türk Kâr Payı %2,87 Toplam Ödeme 1.800.000 TL</div>
        <div>Konut Kredisi Ziraat Bankası Faiz Oranı %2,87 Toplam Ödeme 1.810.000 TL</div>
        """
        result = update_rates.parse_offers(page, 500000, 120)
        self.assertEqual(result["rate"], 2.87)
        self.assertEqual(result["bank"], "Kuveyt Türk, Ziraat Bankası")

    def test_rejects_wrong_amount_or_term(self):
        page = "<h1>100.000 TL 12 Ay</h1><p>QNB Faiz Oranı %2,84 Toplam Ödeme 126.088 TL</p>"
        self.assertIsNone(update_rates.parse_offers(page, 10000, 36))

    def test_rejects_campaign_without_total_payment(self):
        page = "<h1>10.000 TL 36 Ay</h1><p>QNB Faiz Oranı %0 Toplam 10.000 TL</p>"
        self.assertIsNone(update_rates.parse_offers(page, 10000, 36))

    def test_primary_is_preferred_when_verified(self):
        def page(bank, rate):
            return f"<h1>10.000 TL 36 Ay</h1><p>İhtiyaç Kredisi {bank} Faiz Oranı %{rate} Toplam Ödeme 18.000 TL</p>"
        pages = {"hesapkurdu": {"ihtiyac": page("DenizBank", "2,89")},
                 "enuygun": {"ihtiyac": page("QNB", "2,99")}}
        result = update_rates.choose_rate("ihtiyac", pages)
        self.assertEqual(result["bank"], "DenizBank")
        self.assertIn("doğrulandı", result["source"])

    def test_secondary_is_used_as_fallback(self):
        page = "<h1>200.000 TL 48 Ay</h1><p>Taşıt Kredisi Vakıf Katılım Kâr Payı %3,14 Toplam Ödeme 460.000 TL</p>"
        result = update_rates.choose_rate("tasit", {"enuygun": {"tasit": page}})
        self.assertEqual(result["source"], "Enuygun (yedek)")

    def test_large_source_difference_is_rejected(self):
        primary = "<h1>10.000 TL 36 Ay</h1><p>DenizBank Faiz Oranı %2,89 Toplam Ödeme 18.000 TL</p>"
        secondary = "<h1>10.000 TL 36 Ay</h1><p>QNB Faiz Oranı %4,29 Toplam Ödeme 23.000 TL</p>"
        with self.assertRaises(ValueError):
            update_rates.choose_rate("ihtiyac", {"hesapkurdu": {"ihtiyac": primary}, "enuygun": {"ihtiyac": secondary}})


if __name__ == "__main__":
    unittest.main()
