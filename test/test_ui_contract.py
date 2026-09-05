from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "public" / "index.html").read_text(encoding="utf-8")
JAVASCRIPT = (ROOT / "public" / "app.js").read_text(encoding="utf-8")


class UiContractTests(unittest.TestCase):
    def test_every_static_id_used_by_javascript_exists(self) -> None:
        ids = set(re.findall(r'\$\("#([A-Za-z][\w-]*)"\)', JAVASCRIPT))
        missing = sorted(item for item in ids if f'id="{item}"' not in HTML)
        self.assertEqual(missing, [])

    def test_accessibility_landmarks_and_live_regions_exist(self) -> None:
        for landmark in ("<header", "<main", "<footer", "aria-live=", 'role="alert"'):
            self.assertIn(landmark, HTML)

    def test_human_checkpoint_is_visible_in_product_copy(self) -> None:
        self.assertIn("Human judgment required", HTML)
        self.assertIn("Approve and resume agent", HTML)
        self.assertIn("Request changes", HTML)
        self.assertIn("AGENT RUN RECEIPT", HTML)

    def test_demo_gallery_contains_resilience_and_revision_scenarios(self) -> None:
        self.assertIn('id="demo-case"', HTML)
        for case_id in ("parking-permit", "school-trip", "utility-hardship", "dependency-outage", "revision-loop"):
            self.assertIn(f'value="{case_id}"', HTML)
        self.assertIn('formData.append("demoCase", state.demoCase)', JAVASCRIPT)
        self.assertIn('formData.append("failureScenario", state.failureScenario)', JAVASCRIPT)
        self.assertIn('resumeRun("stop")', JAVASCRIPT)


if __name__ == "__main__":
    unittest.main()
