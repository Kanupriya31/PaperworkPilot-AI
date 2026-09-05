from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent.demo import DEMO_FORM_TEXT, DEMO_PROFILE
from agent.demo_cases import DEMO_CASES
from agent.graph import PaperworkGraph
from agent.tools import detect_untrusted_instructions


def main() -> int:
    cases = json.loads((ROOT / "evaluation" / "cases.json").read_text(encoding="utf-8"))
    correct_injection = 0
    correct_sensitive = 0
    for case in cases:
        injection = bool(detect_untrusted_instructions(case["text"]))
        sensitive = bool(re.search(r"\b(ssn|social security|bank account|routing number|passport)\b", case["text"], re.IGNORECASE))
        correct_injection += injection == case["expectInjection"]
        correct_sensitive += sensitive == case["expectSensitive"]

    graph = PaperworkGraph()
    paused = graph.start(
        source_text=DEMO_FORM_TEXT,
        source_name="evaluation fixture",
        profile=DEMO_PROFILE,
        mode="demo",
        simulate_failure=True,
    )
    completed = graph.resume(paused["runId"], {"action": "approve", "note": "Evaluation approval"})
    analysis = completed["analysis"]
    invented_values = [
        field for field in analysis["requiredFields"]
        if field["status"] == "missing" and field["currentValue"]
    ]
    scenario_coverage: dict[str, int] = {}
    scenario_inventions = list(invented_values)
    for case_id, case in DEMO_CASES.items():
        scenario_paused = graph.start(
            source_text=case["formText"], source_name=case["sourceName"], profile=case["profile"],
            mode=f"demo:{case_id}", simulate_failure=case["failureScenario"] == "verifier-timeout",
            failure_scenario=case["failureScenario"],
        )
        scenario_completed = graph.resume(
            scenario_paused["runId"], {"action": "approve", "note": "Cross-scenario evaluation"}
        )
        scenario_analysis = scenario_completed["analysis"]
        scenario_coverage[case_id] = scenario_analysis["evidenceCoverage"]
        scenario_inventions.extend(
            field for field in scenario_analysis["requiredFields"]
            if field["status"] == "missing" and field["currentValue"]
        )
    outage_case = DEMO_CASES["dependency-outage"]
    outage = graph.start(
        source_text=outage_case["formText"], source_name=outage_case["sourceName"],
        profile=outage_case["profile"], mode="demo:dependency-outage",
        simulate_failure=False, failure_scenario="extractor-dependency",
    )
    revision_case = DEMO_CASES["revision-loop"]
    revision_start = graph.start(
        source_text=revision_case["formText"], source_name=revision_case["sourceName"],
        profile=revision_case["profile"], mode="demo:revision-loop",
        simulate_failure=False, failure_scenario="none",
    )
    revision_pause = graph.resume(
        revision_start["runId"], {"action": "reject", "note": "Explain the deadline ambiguity."}
    )
    revision_complete = graph.resume(
        revision_start["runId"], {"action": "edit", "note": "The printed form does not include a year."}
    )
    report = {
        "fixtureCases": len(cases),
        "promptInjectionRouting": f"{correct_injection}/{len(cases)}",
        "sensitiveFieldRouting": f"{correct_sensitive}/{len(cases)}",
        "demoEvidenceCoverage": analysis["evidenceCoverage"],
        "demoScenarioEvidence": scenario_coverage,
        "transientFailureRecovered": any(item["status"] == "recovered" for item in analysis["agentTrace"]),
        "humanInterruptResumed": completed["status"] == "complete",
        "dependencyFailureRecovered": outage["fallbackUsed"] and any(
            item["step"] == "Dependency check" and item["status"] == "recovered" for item in outage["trace"]
        ),
        "dependencyFallbackModelCalls": outage["modelCalls"],
        "rejectPreservedCheckpoint": revision_pause["status"] == "waiting_review" and revision_pause["runId"] == revision_start["runId"],
        "revisionResumedSameRun": revision_complete["status"] == "complete" and revision_complete["runId"] == revision_start["runId"],
        "inventedMissingValues": len(scenario_inventions),
    }
    print(json.dumps(report, indent=2))
    return 0 if all([
        correct_injection == len(cases),
        correct_sensitive == len(cases),
        analysis["evidenceCoverage"] == 100,
        all(coverage == 100 for coverage in scenario_coverage.values()),
        report["transientFailureRecovered"],
        report["humanInterruptResumed"],
        report["dependencyFailureRecovered"],
        report["dependencyFallbackModelCalls"] == 0,
        report["rejectPreservedCheckpoint"],
        report["revisionResumedSameRun"],
        not scenario_inventions,
    ]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
