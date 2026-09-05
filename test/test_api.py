from __future__ import annotations

import json
import unittest

from fastapi.testclient import TestClient

from backend.app import app


class ApiContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def test_health_describes_stateful_architecture(self) -> None:
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["architecture"], "LangGraph state machine")
        self.assertIn("checkpoints", body["memory"])
        self.assertEqual(body["version"], "3.0.0")
        self.assertEqual(body["demoCases"], 5)
        self.assertEqual(body["recovery"], ["dependency fallback", "verifier retry", "reject-revise-resume"])
        self.assertIn("one structured model call", body["costControls"])
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        self.assertIn("default-src 'self'", response.headers["Content-Security-Policy"])

    def test_demo_api_pauses_then_resumes(self) -> None:
        start = self.client.post("/api/runs", data={
            "demo": "true",
            "simulateFailure": "true",
            "profile": json.dumps({}),
            "formText": "",
        })
        self.assertEqual(start.status_code, 202)
        self.assertIn("agent;dur=", start.headers["Server-Timing"])
        paused = start.json()
        self.assertEqual(paused["status"], "waiting_review")
        saved = self.client.get(f"/api/runs/{paused['runId']}")
        self.assertEqual(saved.status_code, 200)
        self.assertEqual(saved.json()["status"], "waiting_review")
        self.assertEqual(saved.json()["review"]["title"], paused["review"]["title"])
        resume = self.client.post(
            f"/api/runs/{paused['runId']}/resume",
            json={"action": "approve", "note": "Verify the deadline year."},
        )
        self.assertEqual(resume.status_code, 200)
        self.assertEqual(resume.json()["status"], "complete")

    def test_live_text_without_key_uses_conservative_fallback(self) -> None:
        response = self.client.post("/api/runs", data={
            "demo": "false",
            "profile": "{}",
            "formText": "APPLICATION\nFull name: __________\nSignature: __________",
        })
        self.assertEqual(response.status_code, 202)
        body = response.json()
        self.assertEqual(body["status"], "waiting_review")
        self.assertIn("agent;dur=", response.headers["Server-Timing"])
        if not self.client.get("/api/health").json()["aiConfigured"]:
            self.assertTrue(body["fallbackUsed"])
            self.assertEqual(body["modelCalls"], 0)
            self.assertEqual(response.headers["X-PaperworkPilot-Fallback"], "true")

    def test_demo_catalog_exposes_five_distinct_scenarios(self) -> None:
        response = self.client.get("/api/demo")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual([case["id"] for case in body["cases"]], [
            "parking-permit", "school-trip", "utility-hardship",
            "dependency-outage", "revision-loop",
        ])
        titles = set()
        for case in body["cases"]:
            selected = self.client.get("/api/demo", params={"case": case["id"]})
            self.assertEqual(selected.status_code, 200)
            titles.add(selected.json()["sourceName"])
        self.assertEqual(len(titles), 5)

    def test_dependency_failure_case_recovers_observably(self) -> None:
        start = self.client.post("/api/runs", data={
            "demo": "true", "demoCase": "dependency-outage", "profile": "{}", "formText": "",
        })
        self.assertEqual(start.status_code, 202)
        body = start.json()
        self.assertTrue(body["fallbackUsed"])
        self.assertEqual(body["modelCalls"], 0)
        self.assertEqual(body["dependencyStatus"]["recovery"], "local-conservative-extractor")
        self.assertTrue(any(item["step"] == "Dependency check" and item["status"] == "recovered" for item in body["trace"]))

    def test_reject_then_edit_resumes_same_api_run(self) -> None:
        started = self.client.post("/api/runs", data={
            "demo": "true", "demoCase": "revision-loop", "profile": "{}", "formText": "",
        }).json()
        revision_response = self.client.post(
            f"/api/runs/{started['runId']}/resume",
            json={"action": "reject", "note": "Explain the deadline ambiguity."},
        )
        self.assertEqual(revision_response.status_code, 202)
        revision = revision_response.json()
        self.assertEqual(revision["runId"], started["runId"])
        self.assertEqual(revision["review"]["kind"], "revision")
        completed = self.client.post(
            f"/api/runs/{started['runId']}/resume",
            json={"action": "edit", "note": "State that the year is not printed."},
        ).json()
        self.assertEqual(completed["status"], "complete")
        self.assertEqual(completed["runId"], started["runId"])
        self.assertEqual([item["action"] for item in completed["analysis"]["reviewHistory"]], ["reject", "edit"])

    def test_unknown_demo_case_fails_safely(self) -> None:
        response = self.client.post("/api/runs", data={
            "demo": "true", "demoCase": "not-a-real-case", "profile": "{}", "formText": "",
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn("does not exist", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
