const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

const state = { analysis: null, file: null, runId: null, demo: false, demoCase: "parking-permit", demoReviewNote: "", demoFlow: "approve", failureScenario: "verifier-timeout", runtime: null };
const views = {
  intake: $("#intake-view"),
  loading: $("#loading-view"),
  approval: $("#approval-view"),
  results: $("#results-view")
};
const stages = [
  ["Safety intake", "Treating the form as untrusted source material."],
  ["Dependency check", "Selecting the primary extractor or a safe local recovery path."],
  ["Requirement extraction", "Mapping fields, documents, signatures, and deadlines."],
  ["Evidence verification", "Checking every requirement against an exact source quote."],
  ["Profile matching", "Using only details you supplied—never filling gaps by guessing."],
  ["Uncertainty review", "Finding ambiguity, sensitive requests, and submission risks."],
  ["Human checkpoint", "Saving graph state before the final plan is created."]
];

$$('.tab').forEach((button) => button.addEventListener('click', () => selectTab(button.dataset.tab)));
$("#form-file").addEventListener("change", (event) => setFile(event.target.files[0]));
$("#drop-zone").addEventListener("dragover", (event) => { event.preventDefault(); event.currentTarget.classList.add("dragging"); });
$("#drop-zone").addEventListener("dragleave", (event) => event.currentTarget.classList.remove("dragging"));
$("#drop-zone").addEventListener("drop", (event) => {
  event.preventDefault();
  event.currentTarget.classList.remove("dragging");
  setFile(event.dataTransfer.files[0]);
});
$("#toggle-profile").addEventListener("click", toggleProfile);
$("#analyze-button").addEventListener("click", () => analyze(false));
$("#demo-button").addEventListener("click", runDemo);
$("#demo-case").addEventListener("change", updateDemoSelection);
$("#approve-button").addEventListener("click", () => resumeRun("approve"));
$("#reject-button").addEventListener("click", () => resumeRun("reject"));
$("#stop-button").addEventListener("click", () => resumeRun("stop"));
$("#new-form-button").addEventListener("click", resetApp);
$("#copy-button").addEventListener("click", copyChecklist);
$("#print-button").addEventListener("click", () => window.print());

function selectTab(tab) {
  $$('.tab').forEach((button) => {
    const active = button.dataset.tab === tab;
    button.classList.toggle('active', active);
    button.setAttribute('aria-selected', String(active));
  });
  $("#upload-panel").classList.toggle("hidden", tab !== "upload");
  $("#paste-panel").classList.toggle("hidden", tab !== "paste");
}

function setFile(file) {
  if (!file) return;
  if (file.size > 10 * 1024 * 1024) return showError("That file is larger than the 10 MB limit.");
  state.file = file;
  const chip = $("#file-chip");
  chip.classList.remove("hidden");
  chip.innerHTML = `<span>📄 ${escapeHtml(file.name)} · ${formatBytes(file.size)}</span><button type="button" aria-label="Remove file">Remove</button>`;
  chip.querySelector("button").addEventListener("click", () => {
    state.file = null;
    $("#form-file").value = "";
    chip.classList.add("hidden");
    chip.innerHTML = "";
  });
}

function toggleProfile() {
  const fields = $("#profile-fields");
  fields.classList.toggle("hidden");
  const expanded = !fields.classList.contains("hidden");
  $("#toggle-profile").textContent = expanded ? "Hide" : "Show";
  $("#toggle-profile").setAttribute("aria-expanded", String(expanded));
}

async function runDemo() {
  clearError();
  try {
    state.demoCase = $("#demo-case").value;
    const demo = await fetchJson(`/api/demo?case=${encodeURIComponent(state.demoCase)}`);
    state.demoReviewNote = demo.reviewNote;
    state.demoFlow = demo.flow;
    state.failureScenario = demo.failureScenario;
    $("#form-text").value = demo.formText;
    ["fullName", "dateOfBirth", "address", "email", "phone"].forEach((key) => { $(`#${key}`).value = ""; });
    Object.entries(demo.profile).forEach(([key, value]) => {
      const input = $(`#${key}`);
      if (input) input.value = value;
    });
    selectTab("paste");
    await analyze(true);
  } catch (error) {
    showError(error.message);
  }
}

async function analyze(demo) {
  clearError();
  const formText = $("#form-text").value.trim();
  if (!demo && !state.file && !formText) return showError("Add a form first, or run the sample demo.");

  state.demo = demo;
  showView("loading");
  const formData = new FormData();
  if (state.file) formData.append("file", state.file);
  formData.append("formText", formText);
  formData.append("demo", String(demo));
  formData.append("demoCase", state.demoCase);
  formData.append("simulateFailure", "false");
  formData.append("failureScenario", state.failureScenario);
  formData.append("profile", JSON.stringify(getProfile()));

  const animation = animateStages();
  try {
    const responsePromise = fetch("/api/runs", { method: "POST", body: formData });
    const [response] = await Promise.all([responsePromise, animation]);
    const data = await response.json().catch(() => ({}));
    if (!response.ok && response.status !== 202) throw new Error(data.detail || "Analysis failed.");
    handleRunResponse(data);
  } catch (error) {
    showView("intake");
    showError(error.message);
  }
}

async function animateStages() {
  const container = $("#agent-steps");
  container.innerHTML = stages.map((stage, index) => `<div class="agent-step" data-stage="${index}">${escapeHtml(stage[0])}</div>`).join("");
  for (let index = 0; index < stages.length; index += 1) {
    $("#loading-title").textContent = `${stages[index][0]}…`;
    $("#loading-detail").textContent = stages[index][1];
    $$('[data-stage]').forEach((node, step) => {
      node.className = `agent-step ${step < index ? "done" : step === index ? "active" : ""}`;
    });
    await wait(115);
  }
  $$('[data-stage]').forEach((node) => node.className = "agent-step done");
}

function handleRunResponse(data) {
  state.runId = data.runId;
  state.runtime = data.runtime || state.runtime;
  if (data.status === "waiting_review") {
    renderReview(data);
    showView("approval");
    return;
  }
  if (data.status === "complete") {
    state.analysis = data.analysis;
    renderResults(data.analysis);
    showView("results");
    return;
  }
  showView("intake");
  showError(data.error || "The run stopped before a plan was generated.");
}

function renderReview(data) {
  const revision = data.review.kind === "revision";
  $("#review-title").textContent = data.review.title || (revision ? "Changes requested · state preserved" : "Human judgment required.");
  $("#review-message").textContent = data.review.message;
  $("#trace-coverage").textContent = `${data.evidenceCoverage}% evidence`;
  $("#review-note").value = data.review.note || (state.demo ? (state.demoReviewNote || "Keep all safety warnings in the final checklist.") : "");
  $("#approve-button").querySelector("span").textContent = revision ? "Apply revision and resume agent" : "Approve and resume agent";
  $("#reject-button").classList.toggle("hidden", revision);
  $("#stop-button").textContent = revision ? "Stop preserved run" : "Stop run";
  $("#review-issues").innerHTML = data.review.issues.map((issue) => `
    <article class="review-issue">
      <span aria-hidden="true">!</span>
      <div><h2>${escapeHtml(issue.title)}</h2><p>${escapeHtml(issue.detail)}</p><blockquote>${escapeHtml(issue.evidence)}</blockquote></div>
    </article>`).join("");
  $("#review-trace").innerHTML = renderTrace(data.trace);
}

async function resumeRun(action) {
  if (!state.runId) return;
  $("#review-error").classList.add("hidden");
  const note = $("#review-note").value.trim();
  const buttons = [$("#approve-button"), $("#reject-button"), $("#stop-button")];
  buttons.forEach((button) => { button.disabled = true; });
  $("#approve-button").querySelector("span").textContent = "Resuming saved graph…";
  try {
    const response = await fetch(`/api/runs/${encodeURIComponent(state.runId)}/resume`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action, note })
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok && response.status !== 202) throw new Error(data.detail || "The run could not be resumed.");
    handleRunResponse(data);
  } catch (error) {
    const errorBox = $("#review-error");
    errorBox.textContent = error.message;
    errorBox.classList.remove("hidden");
  } finally {
    buttons.forEach((button) => { button.disabled = false; });
  }
}

function renderResults(data) {
  $("#result-title").textContent = data.formTitle;
  $("#result-purpose").textContent = data.formPurpose;
  const missing = data.requiredFields.filter((field) => field.status !== "complete").length;
  const recovered = data.agentTrace.some((event) => event.status === "recovered");
  $("#proof-metrics").innerHTML = `
    <div><strong>${Number(data.evidenceCoverage)}%</strong><span>Evidence coverage</span></div>
    <div><strong>${data.agentTrace.length}</strong><span>Recorded steps</span></div>
    <div><strong>${recovered ? "Recovered" : "Clean"}</strong><span>Tool health</span></div>
    <div><strong>${Number(data.modelCalls || 0)}</strong><span>Model calls</span></div>
    <div><strong>${Number(state.runtime?.serverMs || 0)} ms</strong><span>Server runtime</span></div>`;
  $("#result-trace").innerHTML = renderTrace(data.agentTrace);

  $("#summary-card").innerHTML = `
    <div class="score-ring" style="--score:${Number(data.completionScore)}"><strong>${Number(data.completionScore)}%</strong></div>
    <div class="summary-copy"><span>FORM READINESS</span><h2>${missing ? `${missing} items still need your attention` : "Your form looks ready for final review"}</h2><p>${escapeHtml(data.plainLanguageSummary)}</p></div>
    <div class="summary-meta"><div><span>Estimated time</span><b>${escapeHtml(data.estimatedTime)}</b></div><div><span>Urgency</span><b>${escapeHtml(capitalize(data.urgency.level))}</b></div></div>`;

  $("#field-count").textContent = `${data.requiredFields.length} fields`;
  $("#fields-list").innerHTML = data.requiredFields.map((field) => `
    <article class="field-item"><span class="status-icon ${field.status}">${field.status === "complete" ? "✓" : field.status === "missing" ? "?" : "!"}</span>
      <div class="item-copy"><h3>${escapeHtml(field.label)}</h3><p>${escapeHtml(field.plainLanguage)} · ${escapeHtml(field.whyItMatters)}</p>${field.draftAnswer ? `<div class="draft-answer"><b>Suggested:</b> ${escapeHtml(field.draftAnswer)} <small>· ${escapeHtml(field.source)}</small></div>` : ""}${evidenceMarkup(field.evidence)}</div>
      <span class="status-label ${field.status}">${escapeHtml(statusText(field.status))}</span></article>`).join("");

  $("#document-count").textContent = `${data.documents.length} documents`;
  $("#documents-list").innerHTML = data.documents.map((doc) => `
    <article class="document-item"><span class="status-icon ${doc.status}">${doc.status === "ready" ? "✓" : doc.status === "missing" ? "?" : "!"}</span>
      <div class="item-copy"><h3>${escapeHtml(doc.name)}</h3><p>${escapeHtml(doc.reason)}</p><p class="examples">Examples: ${doc.acceptableExamples.map(escapeHtml).join(", ")}</p>${evidenceMarkup(doc.evidence)}</div>
      <span class="status-label ${doc.status}">${escapeHtml(statusText(doc.status))}</span></article>`).join("");

  $("#checklist-list").innerHTML = data.checklist.map((item) => `
    <label class="check-item"><input type="checkbox" data-check-id="${escapeHtml(item.id)}" ${item.status === "done" ? "checked" : ""}><span class="custom-check"></span><div><h3>${escapeHtml(item.label)}</h3><p>${escapeHtml(item.detail)}</p></div></label>`).join("");
  $$('[data-check-id]').forEach((input) => input.addEventListener('change', updateChecklistProgress));
  updateChecklistProgress();
  $("#next-action").textContent = data.nextBestAction;
  $("#warnings-list").innerHTML = data.warnings.map((warning) => `<div class="warning-item"><h4>${escapeHtml(warning.title)}</h4><p>${escapeHtml(warning.detail)}</p></div>`).join("");
  $("#confidence-note").textContent = data.confidenceNote;
}

function renderTrace(trace = []) {
  return trace.map((event, index) => `
    <div class="trace-item ${escapeHtml(event.status)}">
      <span class="trace-dot">${event.status === "recovered" ? "↻" : event.status === "waiting" ? "Ⅱ" : "✓"}</span>
      <div><b>${escapeHtml(event.step)}</b><p>${escapeHtml(event.detail)}</p></div>
      <small>${index + 1}</small>
    </div>`).join("");
}

function evidenceMarkup(evidence = {}) {
  if (!evidence.quote) return "";
  return `<div class="evidence-chip ${evidence.verified ? "verified" : "unverified"}"><span>${evidence.verified ? "✓ Source verified" : "Review source"}</span><q>${escapeHtml(evidence.quote)}</q><small>${escapeHtml(evidence.location || "Form")}</small></div>`;
}

function updateChecklistProgress() {
  const inputs = $$('[data-check-id]');
  const completed = inputs.filter((input) => input.checked).length;
  $("#checklist-progress").textContent = `${completed} of ${inputs.length} done`;
}

async function copyChecklist() {
  if (!state.analysis) return;
  const text = [
    state.analysis.formTitle,
    `Evidence coverage: ${state.analysis.evidenceCoverage}%`,
    "",
    ...state.analysis.checklist.map((item, index) => `${index + 1}. ${item.label} — ${item.detail}`)
  ].join("\n");
  try {
    await navigator.clipboard.writeText(text);
  } catch {
    const area = document.createElement("textarea");
    area.value = text;
    document.body.appendChild(area);
    area.select();
    document.execCommand("copy");
    area.remove();
  }
  const button = $("#copy-button");
  const old = button.textContent;
  button.textContent = "Copied!";
  setTimeout(() => { button.textContent = old; }, 1500);
}

async function resetApp() {
  if (state.runId) fetch(`/api/runs/${encodeURIComponent(state.runId)}`, { method: "DELETE" }).catch(() => {});
  state.analysis = null;
  state.runId = null;
  state.demo = false;
  state.demoReviewNote = "";
  state.runtime = null;
  showView("intake");
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function showView(name) {
  Object.entries(views).forEach(([key, view]) => view.classList.toggle("hidden", key !== name));
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function getProfile() {
  return {
    fullName: $("#fullName").value,
    dateOfBirth: $("#dateOfBirth").value,
    address: $("#address").value,
    email: $("#email").value,
    phone: $("#phone").value
  };
}

function showError(message) {
  const el = $("#error-message");
  el.textContent = message;
  el.classList.remove("hidden");
  el.scrollIntoView({ behavior: "smooth", block: "center" });
}
function clearError() { $("#error-message").classList.add("hidden"); }
function statusText(status) { return ({ complete: "Ready", missing: "Missing", needs_review: "Review", ready: "Ready", verify: "Verify" })[status] || status; }
function capitalize(value = "") { return value.charAt(0).toUpperCase() + value.slice(1); }
function wait(ms) { return new Promise((resolve) => setTimeout(resolve, ms)); }
function formatBytes(bytes) { return bytes < 1024 * 1024 ? `${Math.ceil(bytes / 1024)} KB` : `${(bytes / 1024 / 1024).toFixed(1)} MB`; }
function escapeHtml(value = "") { return String(value).replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#039;", '"': "&quot;" })[char]); }
async function fetchJson(url) { const response = await fetch(url); if (!response.ok) throw new Error("Could not load the demo."); return response.json(); }

async function loadDemoCatalog() {
  try {
    const demo = await fetchJson("/api/demo");
    const select = $("#demo-case");
    select.innerHTML = demo.cases.map((item) => `<option value="${escapeHtml(item.id)}">${escapeHtml(item.label)}</option>`).join("");
    select.value = state.demoCase;
    await updateDemoSelection();
  } catch {
    // Static fallback options keep the page useful while the server starts.
  }
}

async function updateDemoSelection() {
  state.demoCase = $("#demo-case").value;
  try {
    const demo = await fetchJson(`/api/demo?case=${encodeURIComponent(state.demoCase)}`);
    state.demoReviewNote = demo.reviewNote;
    state.demoFlow = demo.flow;
    state.failureScenario = demo.failureScenario;
    $("#demo-badge").textContent = demo.badge;
    $("#demo-description").textContent = demo.description;
    $("#demo-guidance").textContent = demo.flow === "revision"
      ? "At review, choose Request changes. The same run will pause again with its state preserved."
      : demo.failureScenario === "extractor-dependency"
        ? "Watch the dependency check recover locally, then approve the checkpoint."
        : "Run the scenario, inspect source evidence, then approve the checkpoint.";
  } catch {
    // Keep the current card copy if metadata is temporarily unavailable.
  }
}

loadDemoCatalog();
