from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from time import perf_counter

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.gzip import GZipMiddleware

from agent.demo_cases import DEFAULT_DEMO_ID, get_demo_case, list_demo_cases
from agent.graph import PaperworkGraph
from agent.schemas import ResumeRequest
from agent.tools import AIConfigurationError, clean_profile, extract_upload_text


ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

app = FastAPI(
    title="PaperworkPilot Agent API",
    description="Stateful form navigation with evidence verification and human approval.",
    version="3.0.0",
)
service = PaperworkGraph()
app.add_middleware(GZipMiddleware, minimum_size=1_000)


@app.middleware("http")
async def release_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' https://fonts.googleapis.com; "
        "font-src https://fonts.gstatic.com; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "object-src 'none'; base-uri 'self'; form-action 'self'; "
        "frame-ancestors 'self' https://*.replit.com https://*.repl.co https://*.replit.dev"
    )
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    elif request.url.path.endswith((".css", ".js", ".svg")):
        response.headers["Cache-Control"] = "public, max-age=300"
    return response


@app.get("/api/health")
def health() -> dict:
    return {
        "ok": True,
        "aiConfigured": service.ai_configured,
        "model": service.model,
        "version": app.version,
        "demoCases": len(list_demo_cases()),
        "architecture": "LangGraph state machine",
        "memory": "thread-scoped session checkpoints",
        "recovery": ["dependency fallback", "verifier retry", "reject-revise-resume"],
        "costControls": "At most one structured model call for text extraction; verification and planning are deterministic.",
    }


@app.get("/api/demo")
def demo(case: str = DEFAULT_DEMO_ID) -> dict:
    try:
        selected = get_demo_case(case)
    except KeyError:
        raise HTTPException(status_code=404, detail="That demo scenario does not exist.")
    return {**selected, "cases": list_demo_cases()}


@app.post("/api/runs")
async def start_run(
    formText: str = Form(default=""),
    profile: str = Form(default="{}"),
    demo: bool = Form(default=False),
    demoCase: str = Form(default=DEFAULT_DEMO_ID),
    simulateFailure: bool = Form(default=False),
    failureScenario: str = Form(default="none"),
    file: UploadFile | None = File(default=None),
) -> JSONResponse:
    try:
        parsed_profile = clean_profile(json.loads(profile))
    except (json.JSONDecodeError, TypeError):
        raise HTTPException(status_code=400, detail="The saved-details profile is not valid JSON.")

    if demo:
        try:
            selected_demo = get_demo_case(demoCase)
        except KeyError:
            raise HTTPException(status_code=400, detail="That demo scenario does not exist.")
    else:
        selected_demo = None
    source_text = selected_demo["formText"] if selected_demo else formText.strip()
    source_name = selected_demo["sourceName"] if selected_demo else "Pasted form"
    if file is not None and not demo:
        data = await file.read()
        uploaded_text = await asyncio.to_thread(
            extract_upload_text,
            data,
            file.filename or "form",
            file.content_type or "application/octet-stream",
            service.client,
            service.model,
        )
        source_text = "\n\n".join(part for part in (source_text, uploaded_text) if part).strip()
        source_name = file.filename or "Uploaded form"
    if selected_demo:
        parsed_profile = {**selected_demo["profile"], **parsed_profile}
    if not source_text:
        raise HTTPException(status_code=400, detail="Paste form text or upload a supported file.")
    selected_failure = selected_demo.get("failureScenario", "none") if selected_demo else failureScenario
    allowed_failures = {"none", "verifier-timeout", "extractor-dependency"}
    if selected_failure not in allowed_failures:
        raise HTTPException(status_code=400, detail="That failure scenario is not supported.")

    try:
        started = perf_counter()
        result = await asyncio.to_thread(
            service.start,
            source_text=source_text[:100_000],
            source_name=source_name,
            profile=parsed_profile,
            mode=f"demo:{demoCase}" if demo else "ai",
            simulate_failure=simulateFailure or selected_failure == "verifier-timeout",
            failure_scenario=selected_failure,
        )
        elapsed_ms = round((perf_counter() - started) * 1000)
        result["runtime"] = {"serverMs": elapsed_ms, "modelCalls": result.get("modelCalls", 0)}
        return JSONResponse(
            result,
            status_code=202 if result["status"] == "waiting_review" else 200,
            headers={"Server-Timing": f"agent;dur={elapsed_ms}", "X-PaperworkPilot-Fallback": str(result.get("fallbackUsed", False)).lower()},
        )
    except AIConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        print(f"PaperworkPilot run failed: {type(exc).__name__}: {exc}")
        raise HTTPException(status_code=500, detail="The agent could not complete this run safely. Try again or use the sample demo.")


@app.post("/api/runs/{run_id}/resume")
async def resume_run(run_id: str, decision: ResumeRequest) -> JSONResponse:
    try:
        started = perf_counter()
        result = await asyncio.to_thread(service.resume, run_id, decision.model_dump())
        elapsed_ms = round((perf_counter() - started) * 1000)
        result["runtime"] = {"serverMs": elapsed_ms, "modelCalls": result.get("analysis", {}).get("modelCalls", result.get("modelCalls", 0))}
        return JSONResponse(
            result,
            status_code=202 if result["status"] == "waiting_review" else 200,
            headers={"Server-Timing": f"agent;dur={elapsed_ms}"},
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="This run expired or does not exist. Start a new analysis.")
    except Exception as exc:
        print(f"PaperworkPilot resume failed: {type(exc).__name__}: {exc}")
        raise HTTPException(status_code=500, detail="The saved run could not be resumed safely.")


@app.get("/api/runs/{run_id}")
async def run_status(run_id: str) -> dict:
    try:
        return await asyncio.to_thread(service.status, run_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="This run expired or does not exist.")


@app.delete("/api/runs/{run_id}", status_code=204)
async def delete_run(run_id: str) -> None:
    await asyncio.to_thread(service.discard, run_id)


@app.exception_handler(AIConfigurationError)
async def ai_config_handler(_request, exc: AIConfigurationError):
    return JSONResponse({"detail": str(exc)}, status_code=503)


app.mount("/", StaticFiles(directory=ROOT / "public", html=True), name="public")
