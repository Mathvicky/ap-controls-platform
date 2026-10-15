import os
import tempfile
import unittest
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from app.server import assess, initialize

class ServiceTests(unittest.TestCase):
    def setUp(self):
        Path(".test-work").mkdir(exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=".test-work")
        os.environ["SQLITE_PATH"] = self.tmp.name + "/test.db"
        initialize()
    def tearDown(self):
        self.tmp.cleanup()
    def invoice(self, **changes):
        return dict(vendor="Acme", reference="INV-1", amount="120.00", **changes)
    def test_duplicate_normalization(self):
        self.assertEqual(assess(self.invoice())["risk"], "low")
        self.assertIn("duplicate_reference", assess({"vendor":" ACME ","reference":"inv-1","amount":"120"})["reasons"])
    def test_threshold(self):
        self.assertEqual(assess({"vendor":"a","reference":"b","amount":"10000"})["reasons"], ["high_amount"])
    def test_invalid(self):
        for amount in ["NaN", "Infinity", "-1", "0", "1.001", "bad", "1000000001"]:
            with self.subTest(amount=amount), self.assertRaises(ValueError):
                assess({"vendor":"a","reference":"b","amount":amount})
    def test_invalid_shape(self):
        for payload in [[], None, {"vendor":4}, {"vendor":"","reference":"a","amount":1}]:
            with self.assertRaises(ValueError): assess(payload)
    def test_concurrent_duplicates(self):
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _: assess(self.invoice()), range(20)))
        self.assertEqual(sum(r["risk"] == "low" for r in results), 1)

if __name__ == "__main__": unittest.main()
