"""
Tests for Wuthering Waves Resonators and Custom Companions
"""

import unittest
from pathlib import Path
from src.core.resonators import RESONATORS, get_resonator, list_all_resonators

class TestResonators(unittest.TestCase):
    def test_roster_contains_hsin_and_aemaeth(self):
        self.assertIn("hsin", RESONATORS)
        self.assertIn("aemaeth", RESONATORS)

        hsin = get_resonator("hsin")
        self.assertEqual(hsin["name"], "Hsin")
        self.assertEqual(hsin["element"], "Spectro")

        aemaeth = get_resonator("aemaeth")
        self.assertEqual(aemaeth["name"], "Aemaeth")
        self.assertEqual(aemaeth["element"], "Havoc")

    def test_all_elements_present(self):
        elements = {res["element"] for res in RESONATORS.values()}
        expected = {"Spectro", "Havoc", "Fusion", "Aero", "Glacio", "Electro"}
        self.assertTrue(expected.issubset(elements))

    def test_sprites_generated_for_all(self):
        base_assets = Path(__file__).resolve().parent.parent / "assets" / "resonators"
        for res_id in RESONATORS:
            res_dir = base_assets / res_id
            self.assertTrue(res_dir.exists(), f"Missing directory for {res_id}")
            self.assertTrue((res_dir / "pet_idle_0.png").exists(), f"Missing idle sprite for {res_id}")
            self.assertTrue((res_dir / "icon.png").exists(), f"Missing icon for {res_id}")

if __name__ == "__main__":
    unittest.main()
