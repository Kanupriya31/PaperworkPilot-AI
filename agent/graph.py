from __future__ import annotations

import os
import threading
import uuid
from copy import deepcopy
from typing import Any, Literal

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, RetryPolicy, interrupt
from openai import OpenAI

from agent.demo_cases import DEFAULT_DEMO_ID, demo_extraction
from agent.state import PaperworkState
from agent.tools import (
    AIConfigurationError,
    TransientVerificationError,
    detect_untrusted_instructions,
    extract_requirements_with_ai,
    find_ambiguities,
    heuristic_extraction,
    match_profile,
    trace_event,
    verify_extraction,
)


class PaperworkGraph:
    def __init__(self) -> None:
        self.model = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")
        self.client = OpenAI(api_key=os.environ["OPENAI_API_KEY"]) if os.getenv("OPENAI_API_KEY") else None
        self.checkpointer = InMemorySaver()
        self._invoke_lock = threading.RLock()
        self._failure_attempts: dict[str, int] = {}
        self._known_runs: set[str] = set()
        self.graph = self._build_graph()

    @property
    def ai_configured(self) -> bool:
        return self.client is not None

    def _build_graph(self):
        builder = StateGraph(PaperworkState)
        builder.add_node("safety_intake", self._safety_intake)
        builder.add_node("dependency_check", self._dependency_check)
        builder.add_node("extract_requirements", self._extract_requirements)
        builder.add_node(
            "verify_evidence",
            self._verify_evidence,
            retry_policy=RetryPolicy(
                max_attempts=2,
                initial_interval=0.05,
                backoff_factor=1.0,
                jitter=False,
                retry_on=TransientVerificationError,
            ),
        )
        builder.add_node("match_profile", self._match_profile)
        builder.add_node("review_uncertainty", self._review_uncertainty)
        builder.add_node("human_checkpoint", self._human_checkpoint)
        builder.add_node("request_revision", self._request_revision)
        builder.add_node("assemble_plan", self._assemble_plan)
        builder.add_node("stop_safely", self._stop_safely)

        builder.add_edge(START, "safety_intake")
        builder.add_edge("safety_intake", "dependency_check")
        builder.add_edge("dependency_check", "extract_requirements")
        builder.add_edge("extract_requirements", "verify_evidence")
        builder.add_edge("verify_evidence", "match_profile")
        builder.add_edge("match_profile", "review_uncertainty")
        builder.add_edge("review_uncertainty", "human_checkpoint")
        builder.add_conditional_edges(
            "human_checkpoint",
            self._route_after_human,
            {"assemble": "assemble_plan", "revise": "request_revision", "stop": "stop_safely"},
        )
        builder.add_conditional_edges(
            "request_revision",
            self._route_after_revision,
            {"assemble": "assemble_plan", "stop": "stop_safely"},
        )
        builder.add_edge("assemble_plan", END)
        builder.add_edge("stop_safely", END)
        return builder.compile(checkpointer=self.checkpointer)

    def start(
        self,
        *,
        source_text: str,
        source_name: str,
        profile: dict[str, str],
        mode: str,
        simulate_failure: bool,
        failure_scenario: str = "none",
    ) -> dict[str, Any]:
        run_id = str(uuid.uuid4())
        self._known_runs.add(run_id)
        initial: PaperworkState = {
            "run_id": run_id,
            "mode": mode,
            "source_text": source_text,
            "source_name": source_name,
            "profile": profile,
            "simulate_failure": simulate_failure,
            "failure_scenario": failure_scenario,
            "fallback_used": False,
            "model_calls": 0,
            "review_history": [],
            "trace": [],
            "status": "running",
        }
        with self._invoke_lock:
            result = self.graph.invoke(initial, config=self._config(run_id))
        return self._public_result(run_id, result)

    def resume(self, run_id: str, decision: dict[str, str]) -> dict[str, Any]:
        if run_id not in self._known_runs:
            raise KeyError(run_id)
        with self._invoke_lock:
            result = self.graph.invoke(Command(resume=decision), config=self._config(run_id))
        return self._public_result(run_id, result)

    def status(self, run_id: str) -> dict[str, Any]:
        if run_id not in self._known_runs:
            raise KeyError(run_id)
        with self._invoke_lock:
            snapshot = self.graph.get_state(self._config(run_id))
        values = dict(snapshot.values)
        interrupts = tuple(
            item
            for task in snapshot.tasks
            for item in getattr(task, "interrupts", ())
        )
        if interrupts:
            values["__interrupt__"] = interrupts
        return self._public_result(run_id, values)

    def discard(self, run_id: str) -> None:
        self._known_runs.discard(run_id)
        delete_thread = getattr(self.checkpointer, "delete_thread", None)
        if callable(delete_thread):
            delete_thread(run_id)

    def _config(self, run_id: str) -> dict[str, dict[str, str]]:
        return {"configurable": {"thread_id": run_id}}

    def _safety_intake(self, state: PaperworkState) -> PaperworkState:
        flags = detect_untrusted_instructions(state["source_text"])
        detail = "Document accepted as untrusted source content."
        if flags:
            detail = "Potential prompt injection was isolated and ignored."
        return {
            "safety_flags": flags,
            "trace": [trace_event("Safety intake", "done", detail)],
        }

    def _dependency_check(self, state: PaperworkState) -> PaperworkState:
        scenario = state.get("failure_scenario", "none")
        simulated_outage = scenario == "extractor-dependency"
        unavailable = simulated_outage or (not state.get("mode", "").startswith("demo") and self.client is None)
        if simulated_outage:
            detail = "Primary extraction dependency reported unavailable; the graph selected its local recovery path."
        elif unavailable:
            detail = "No model dependency is configured; text analysis will continue with the conservative local extractor."
        elif state.get("mode", "").startswith("demo"):
            detail = "Deterministic fixture dependency is available; no external model call is required."
        else:
            detail = f"Structured extraction dependency is available ({self.model})."
        return {
            "dependency_status": {
                "name": "structured-extraction",
                "available": not unavailable,
                "simulated": simulated_outage,
                "recovery": "local-conservative-extractor" if unavailable else "not-required",
            },
            "fallback_used": unavailable,
            "trace": [trace_event(
                "Dependency check",
                "recovered" if unavailable else "done",
                detail,
            )],
        }

    def _extract_requirements(self, state: PaperworkState) -> PaperworkState:
        recovered = False
        dependency_status = state.get("dependency_status", {})
        mode = state.get("mode", "")
        use_dependency_fallback = bool(state.get("fallback_used"))
        model_calls = 0
        if use_dependency_fallback and mode.startswith("demo"):
            case_id = mode.partition(":")[2] or DEFAULT_DEMO_ID
            extraction = demo_extraction(case_id)
            recovered = True
            detail = "Local recovery extractor completed after the primary dependency became unavailable."
        elif use_dependency_fallback:
            extraction = heuristic_extraction(state["source_text"])
            recovered = True
            detail = "Conservative local extraction completed without the model dependency."
        elif mode.startswith("demo"):
            case_id = mode.partition(":")[2] or DEFAULT_DEMO_ID
            extraction = demo_extraction(case_id)
            detail = "Loaded the deterministic demonstration fixture with source-linked requirements."
        else:
            try:
                model_calls = 1
                extraction = extract_requirements_with_ai(
                    state["source_text"], state.get("profile", {}), self.client, self.model
                )
                detail = f"Structured extraction completed with {self.model}."
            except AIConfigurationError:
                raise
            except Exception as exc:
                extraction = heuristic_extraction(state["source_text"])
                recovered = True
                dependency_status = {
                    "name": "structured-extraction",
                    "available": False,
                    "simulated": False,
                    "recovery": "local-conservative-extractor",
                }
                detail = f"Primary extraction failed safely; conservative fallback used ({type(exc).__name__})."
        extraction["warnings"] = extraction.get("warnings", []) + [
            {
                **flag,
                "evidence": {"quote": "AI-directed instruction pattern", "location": "Document content"},
            }
            for flag in state.get("safety_flags", [])
        ]
        return {
            "extraction": extraction,
            "fallback_used": recovered or use_dependency_fallback,
            "model_calls": model_calls,
            "dependency_status": dependency_status,
            "trace": [trace_event(
                "Requirement extraction",
                "recovered" if recovered else "done",
                detail,
                items=len(extraction.get("fields", [])) + len(extraction.get("documents", [])),
            )],
        }

    def _verify_evidence(self, state: PaperworkState) -> PaperworkState:
        run_id = state["run_id"]
        attempts = self._failure_attempts.get(run_id, 0)
        if state.get("simulate_failure") and attempts == 0:
            self._failure_attempts[run_id] = 1
            raise TransientVerificationError("Simulated verifier timeout")
        extraction, coverage = verify_extraction(state["extraction"], state["source_text"])
        recovered = self._failure_attempts.get(run_id, 0) > 0
        detail = f"Verified {coverage}% of extracted items against exact source quotes."
        if recovered:
            detail = f"Verifier recovered after a transient failure; {coverage}% evidence coverage confirmed."
        return {
            "extraction": extraction,
            "evidence_coverage": coverage,
            "trace": [trace_event("Evidence verification", "recovered" if recovered else "done", detail, attempts=2 if recovered else 1)],
        }

    def _match_profile(self, state: PaperworkState) -> PaperworkState:
        fields, documents = match_profile(state["extraction"], state.get("profile", {}))
        matched = sum(field["status"] == "complete" for field in fields)
        return {
            "required_fields": fields,
            "documents": documents,
            "trace": [trace_event(
                "Profile matching",
                "done",
                f"Matched {matched} fields from user-supplied details without inventing missing answers.",
                matched=matched,
            )],
        }

    def _review_uncertainty(self, state: PaperworkState) -> PaperworkState:
        extraction = state["extraction"]
        ambiguities = find_ambiguities(extraction, state["source_text"], state.get("evidence_coverage", 0))
        warnings = [self._warning_for_ui(item) for item in extraction.get("warnings", [])]
        return {
            "ambiguities": ambiguities,
            "warnings": warnings,
            "trace": [trace_event(
                "Uncertainty review",
                "done",
                f"Found {len(ambiguities)} item{'s' if len(ambiguities) != 1 else ''} requiring human judgment.",
                issues=len(ambiguities),
            )],
        }

    def _human_checkpoint(self, state: PaperworkState) -> PaperworkState:
        decision = interrupt({
            "kind": "initial",
            "title": "Human judgment required",
            "message": "PaperworkPilot paused before creating the final submission plan.",
            "issues": state.get("ambiguities", []),
            "evidenceCoverage": state.get("evidence_coverage", 0),
            "allowedActions": ["approve", "edit", "reject", "stop"],
        })
        action = str(decision.get("action", "stop")) if isinstance(decision, dict) else "stop"
        note = str(decision.get("note", ""))[:500] if isinstance(decision, dict) else ""
        if action in {"approve", "edit"}:
            status = "approved"
            detail = "The reviewer approved the plan boundary."
        elif action == "reject":
            status = "changes_requested"
            detail = "The reviewer requested changes; graph state was preserved for revision."
        else:
            status = "stopped"
            detail = "The reviewer stopped the run before plan generation."
        return {
            "human_decision": {"action": action, "note": note},
            "review_history": [{"action": action, "note": note}],
            "trace": [trace_event(
                "Human checkpoint",
                status,
                detail,
            )],
        }

    def _route_after_human(self, state: PaperworkState) -> Literal["assemble", "revise", "stop"]:
        action = state.get("human_decision", {}).get("action")
        if action in {"approve", "edit"}:
            return "assemble"
        return "revise" if action == "reject" else "stop"

    def _request_revision(self, state: PaperworkState) -> PaperworkState:
        requested_note = state.get("human_decision", {}).get("note", "")
        decision = interrupt({
            "kind": "revision",
            "title": "Changes requested · state preserved",
            "message": "The run remains checkpointed. Update the reviewer note, then resume the same graph or stop safely.",
            "issues": [{
                "title": "Reviewer change request",
                "detail": requested_note or "Clarify the requested change before resuming.",
                "evidence": "Human review note — no document evidence was changed.",
            }],
            "evidenceCoverage": state.get("evidence_coverage", 0),
            "allowedActions": ["edit", "stop"],
            "note": requested_note,
        })
        action = str(decision.get("action", "stop")) if isinstance(decision, dict) else "stop"
        note = str(decision.get("note", requested_note))[:500] if isinstance(decision, dict) else requested_note
        return {
            "human_decision": {"action": action, "note": note},
            "review_history": [{"action": action, "note": note}],
            "trace": [trace_event(
                "Revision checkpoint",
                "approved" if action in {"approve", "edit"} else "stopped",
                "The reviewer revised the instruction and resumed the same run." if action in {"approve", "edit"} else "The reviewer stopped the preserved run.",
            )],
        }

    def _route_after_revision(self, state: PaperworkState) -> Literal["assemble", "stop"]:
        return "assemble" if state.get("human_decision", {}).get("action") in {"approve", "edit"} else "stop"

    def _assemble_plan(self, state: PaperworkState) -> PaperworkState:
        extraction = deepcopy(state["extraction"])
        fields = deepcopy(state.get("required_fields", []))
        documents = deepcopy(state.get("documents", []))
        warnings = deepcopy(state.get("warnings", []))
        decision = state.get("human_decision", {})
        if decision.get("note"):
            warnings.append({
                "severity": "info",
                "title": "Reviewer note",
                "detail": decision["note"],
                "evidence": {"quote": decision["note"], "location": "Human checkpoint", "verified": True},
            })
        checklist = self._build_checklist(fields, documents, warnings)
        complete = sum(field["status"] == "complete" for field in fields)
        score = min(95, round(20 + (complete / max(len(fields), 1)) * 65 + state.get("evidence_coverage", 0) * 0.1))
        final_trace = state.get("trace", []) + [trace_event(
            "Submission plan",
            "done",
            f"Built an ordered {len(checklist)}-step plan after human approval.",
            checklistItems=len(checklist),
        )]
        analysis = {
            "runId": state["run_id"],
            "formTitle": extraction["formTitle"],
            "formPurpose": extraction["formPurpose"],
            "plainLanguageSummary": extraction["plainLanguageSummary"],
            "estimatedTime": extraction["estimatedTime"],
            "urgency": extraction["urgency"],
            "completionScore": score,
            "requiredFields": fields,
            "documents": documents,
            "warnings": warnings,
            "nextBestAction": extraction["nextBestAction"],
            "checklist": checklist,
            "confidenceNote": extraction["confidenceNote"],
            "evidenceCoverage": state.get("evidence_coverage", 0),
            "humanDecision": decision,
            "reviewHistory": state.get("review_history", []),
            "dependencyStatus": state.get("dependency_status", {}),
            "fallbackUsed": bool(state.get("fallback_used")),
            "modelCalls": int(state.get("model_calls", 0)),
            "agentTrace": final_trace,
            "sourceName": state.get("source_name", "Pasted form"),
            "safetyFlags": state.get("safety_flags", []),
        }
        return {
            "analysis": analysis,
            "status": "complete",
            "trace": [trace_event("Submission plan", "done", f"Built an ordered {len(checklist)}-step plan after human approval.", checklistItems=len(checklist))],
        }

    def _stop_safely(self, _state: PaperworkState) -> PaperworkState:
        return {
            "status": "rejected",
            "error": "The reviewer stopped this run. No final submission plan was generated.",
            "trace": [trace_event("Safe stop", "done", "No write or submission action was taken.")],
        }

    def _public_result(self, run_id: str, result: dict[str, Any]) -> dict[str, Any]:
        interrupts = result.get("__interrupt__", ())
        if interrupts:
            first = interrupts[0]
            payload = getattr(first, "value", first)
            checkpoint_step = "Revision checkpoint" if isinstance(payload, dict) and payload.get("kind") == "revision" else "Human checkpoint"
            trace = list(result.get("trace", [])) + [trace_event(
                checkpoint_step, "waiting", "The graph saved its state and paused for review."
            )]
            return {
                "runId": run_id,
                "status": "waiting_review",
                "review": payload,
                "trace": trace,
                "evidenceCoverage": result.get("evidence_coverage", 0),
                "dependencyStatus": result.get("dependency_status", {}),
                "fallbackUsed": bool(result.get("fallback_used")),
                "modelCalls": int(result.get("model_calls", 0)),
            }
        if result.get("status") == "complete":
            return {"runId": run_id, "status": "complete", "analysis": result["analysis"]}
        return {
            "runId": run_id,
            "status": result.get("status", "rejected"),
            "error": result.get("error", "The run did not complete."),
            "trace": result.get("trace", []),
        }

    @staticmethod
    def _warning_for_ui(item: dict[str, Any]) -> dict[str, Any]:
        return {
            "severity": item.get("severity", "info"),
            "title": item.get("title", "Review this item"),
            "detail": item.get("detail", "Verify this requirement."),
            "evidence": item.get("evidence", {}),
        }

    @staticmethod
    def _build_checklist(fields: list[dict], documents: list[dict], warnings: list[dict]) -> list[dict[str, str]]:
        items: list[dict[str, str]] = []
        missing_vehicle = [field for field in fields if field["status"] == "missing" and any(word in field["label"].lower() for word in ("vehicle", "plate"))]
        for field in fields:
            if field["status"] == "complete" or field in missing_vehicle:
                continue
            if field["status"] == "needs_review":
                continue
            items.append({"id": f"answer-{field['id']}", "label": f"Complete {field['label'].lower()}", "detail": field["draftAnswer"], "status": "todo", "category": "answer"})
        if missing_vehicle:
            items.append({"id": "answer-vehicle", "label": "Copy vehicle details", "detail": "Add the plate, state, make, and model from your current registration.", "status": "todo", "category": "answer"})
        for index, document in enumerate(documents, 1):
            verb = "Gather" if document.get("required", True) else "Check whether you need"
            items.append({"id": f"document-{index}", "label": f"{verb} {document['name'].lower()}", "detail": document["reason"], "status": "todo", "category": "document"})
        important = [warning for warning in warnings if warning.get("severity") in {"important", "caution"}]
        if important:
            items.append({"id": "review-warnings", "label": "Resolve warnings and ambiguous instructions", "detail": "Confirm deadlines, submission rules, and any sensitive or original-document requirements.", "status": "todo", "category": "review"})
        items.extend([
            {"id": "submit-review", "label": "Review, sign, and date", "detail": "Check every answer and attachment before signing.", "status": "todo", "category": "submit"},
            {"id": "submit-proof", "label": "Save proof of submission", "detail": "Keep a confirmation screen, receipt, or stamped copy.", "status": "todo", "category": "submit"},
        ])
        return items
