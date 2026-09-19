import unittest

import update_rates


class ParserTests(unittest.TestCase):
    def test_original_sentence(self):
        page = """
        <p>36 ay vadeli 10.000 TL İhtiyaç Kredisi için en avantajlı
        teklifi sunan banka %2,99 Faiz oranı ile ING, DenizBank oldu.</p>
        """
        self.assertEqual(
            update_rates.parse(page),
            {"bank": "ING, DenizBank", "rate": 2.99, "amount": 10000, "term": 36},
        )

    def test_oraniyla_wording(self):
        page = """
        <p>48 ay vadeli 200.000 TL Taşıt Finansmanı için en avantajlı
        teklifi sunan banka %3,19 Kâr Payı oranıyla Vakıf Katılım,
        Albaraka Türk oldu.</p>
        """
        self.assertEqual(
            update_rates.parse(page),
            {
                "bank": "Vakıf Katılım, Albaraka Türk",
                "rate": 3.19,
                "amount": 200000,
                "term": 48,
            },
        )

    def test_unrelated_page_is_rejected(self):
        self.assertIsNone(update_rates.parse("<h1>Attention Required!</h1>"))


if __name__ == "__main__":
    unittest.main()
