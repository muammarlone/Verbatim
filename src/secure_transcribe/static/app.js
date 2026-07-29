import { layout, prepare } from "./pretext.js";

const state = {
  token: "",
  jobs: [],
  batches: [],
  activeJob: null,
  activeBatchId: null,
  transcript: null,
  analysis: null,
  analysisTab: "moments",
  pollTimer: null,
  batchPollTimer: null,
  selectedFile: null,
  health: null,
};

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

async function api(path, options = {}) {
  const headers = new Headers(options.headers || {});
  if (options.method && options.method !== "GET") headers.set("X-Studio-Token", state.token);
  const response = await fetch(path, { ...options, headers });
  if (response.status === 204) return null;
  const contentType = response.headers.get("content-type") || "";
  const body = contentType.includes("application/json") ? await response.json() : await response.text();
  if (!response.ok) {
    const message = body?.error?.message || "The local service could not complete that request.";
    const error = new Error(message);
    error.code = body?.error?.code || `HTTP_${response.status}`;
    throw error;
  }
  return body;
}

function showAlert(message) {
  const region = $("#alert-region");
  region.replaceChildren();
  const alert = document.createElement("div");
  alert.className = "inline-alert";
  alert.textContent = message;
  region.append(alert);
  window.setTimeout(() => alert.remove(), 6000);
}

function toast(message) {
  const element = $("#toast");
  element.textContent = message;
  element.hidden = false;
  window.clearTimeout(element._timer);
  element._timer = window.setTimeout(() => { element.hidden = true; }, 3200);
}

function formatBytes(bytes) {
  if (!Number.isFinite(bytes)) return "—";
  if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / 1024 ** 2).toFixed(1)} MB`;
}

function formatDuration(seconds) {
  if (!Number.isFinite(seconds)) return "—";
  const rounded = Math.max(0, Math.floor(seconds));
  const hours = Math.floor(rounded / 3600);
  const minutes = Math.floor((rounded % 3600) / 60);
  const secs = rounded % 60;
  return hours ? `${hours}:${String(minutes).padStart(2, "0")}:${String(secs).padStart(2, "0")}` : `${minutes}:${String(secs).padStart(2, "0")}`;
}

function formatDate(value) {
  return new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }).format(new Date(value));
}

function statusLabel(status) {
  return ({ queued: "Queued", validating: "Validating", extracting: "Extracting audio", transcribing: "Transcribing", analyzing: "Analyzing", complete: "Ready", failed: "Stopped" })[status] || status;
}

function statusClass(status) {
  if (status === "failed") return "is-failed";
  if (status !== "complete") return "is-processing";
  return "";
}

function batchStatusLabel(status) {
  return ({ queued: "Queued", running: "Processing", complete: "Complete", partial: "Needs review", failed: "Stopped" })[status] || status;
}

function batchStatusClass(status) {
  if (status === "failed" || status === "partial") return "is-failed";
  if (status === "queued" || status === "running") return "is-processing";
  return "";
}

function modelLabel(modelId) {
  const [name, digest] = modelId.split("@sha256:");
  return digest ? `${name}@${digest.slice(0, 10)}` : modelId;
}

function svgIcon(path) {
  const wrapper = document.createElement("span");
  wrapper.className = "job-file-icon";
  wrapper.innerHTML = `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="${path}"/></svg>`;
  return wrapper;
}

function renderJobs() {
  const list = $("#jobs-list");
  list.replaceChildren();
  $("#empty-jobs").hidden = state.jobs.length > 0;
  $("#nav-job-count").textContent = String(state.jobs.length);
  state.jobs.forEach((job) => {
    const row = document.createElement("article");
    row.className = "job-row";
    row.tabIndex = 0;
    row.setAttribute("role", "button");
    row.setAttribute("aria-label", `Open ${job.display_name}`);
    row.append(svgIcon("M7 4h7l4 4v12H7zM14 4v5h5M10 13h6M10 16h4"));

    const summary = document.createElement("div");
    const name = document.createElement("div");
    name.className = "job-name";
    name.textContent = job.display_name;
    const subtitle = document.createElement("div");
    subtitle.className = "job-subtitle";
    subtitle.textContent = `${formatDate(job.created_at)} · ${formatBytes(job.size_bytes)}${job.duration_seconds ? ` · ${formatDuration(job.duration_seconds)}` : ""}`;
    summary.append(name, subtitle);
    row.append(summary);

    if (job.status !== "complete" && job.status !== "failed") {
      const progress = document.createElement("div");
      progress.className = "job-progress";
      const track = document.createElement("span");
      track.style.setProperty("--progress", `${job.progress}%`);
      const detail = document.createElement("small");
      detail.textContent = `${job.progress}%`;
      progress.append(track, detail);
      row.append(progress);
    } else {
      row.append(document.createElement("span"));
    }

    const badge = document.createElement("span");
    badge.className = `status-badge ${statusClass(job.status)}`;
    badge.textContent = statusLabel(job.status);
    row.append(badge);
    const open = () => openJob(job.id);
    row.addEventListener("click", open);
    row.addEventListener("keydown", (event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); open(); } });
    list.append(row);
  });
}

async function loadJobs() {
  try {
    const payload = await api("/api/jobs");
    state.jobs = payload.jobs;
    renderJobs();
  } catch (error) {
    showAlert(error.message);
  }
}

function renderBatches() {
  const list = $("#batches-list");
  list.replaceChildren();
  $("#empty-batches").hidden = state.batches.length > 0;
  state.batches.forEach((batch) => {
    const card = document.createElement("article");
    card.className = "batch-card";

    const header = document.createElement("div");
    header.className = "batch-card-header";
    const title = document.createElement("div");
    const route = document.createElement("span");
    route.className = "batch-route";
    route.textContent = `${batch.input_folder} → ${batch.output_folder}`;
    const heading = document.createElement("h3");
    heading.textContent = `${batch.completed_files} of ${batch.total_files} files exported`;
    title.append(route, heading);
    const badge = document.createElement("span");
    badge.className = `status-badge ${batchStatusClass(batch.status)}`;
    badge.textContent = batchStatusLabel(batch.status);
    header.append(title, badge);

    const progress = document.createElement("div");
    progress.className = "batch-progress";
    const completeRatio = batch.total_files ? (batch.completed_files + batch.failed_files) / batch.total_files : 1;
    const track = document.createElement("span");
    track.style.setProperty("--progress", `${Math.round(completeRatio * 100)}%`);
    progress.append(track);

    const meta = document.createElement("div");
    meta.className = "batch-meta";
    const formats = document.createElement("span");
    formats.textContent = batch.formats.map((format) => format.toUpperCase()).join(" · ");
    const size = document.createElement("span");
    size.textContent = `${formatBytes(batch.total_bytes)} · ${formatDate(batch.created_at)}`;
    meta.append(formats, size);

    const batchError = document.createElement("p");
    batchError.className = "batch-error";
    batchError.textContent = batch.error?.message || "";
    batchError.hidden = !batch.error;

    const items = document.createElement("div");
    items.className = "batch-items";
    batch.items.forEach((item) => {
      const row = document.createElement("div");
      row.className = "batch-item";
      const name = document.createElement("strong");
      name.textContent = item.source_name;
      const detail = document.createElement("span");
      detail.textContent = item.outputs.length ? item.outputs.join(", ") : item.error?.code || batchStatusLabel(item.status);
      const itemBadge = document.createElement("span");
      itemBadge.className = `item-state ${item.status === "complete" ? "is-complete" : item.status === "failed" || item.status === "rejected" ? "is-failed" : ""}`;
      itemBadge.textContent = item.status;
      row.append(name, detail, itemBadge);
      items.append(row);
    });

    card.append(header, progress, meta, batchError, items);
    if (["complete", "partial", "failed"].includes(batch.status)) {
      const footer = document.createElement("div");
      footer.className = "batch-card-footer";
      const manifest = document.createElement("span");
      manifest.textContent = batch.manifest_name ? `Manifest: ${batch.manifest_name}` : "Manifest unavailable";
      const cleanup = document.createElement("button");
      cleanup.type = "button";
      cleanup.className = "text-button danger-text";
      cleanup.textContent = "Remove managed copies";
      cleanup.addEventListener("click", () => {
        state.activeBatchId = batch.id;
        $("#batch-delete-dialog").showModal();
      });
      footer.append(manifest, cleanup);
      card.append(footer);
    }
    list.append(card);
  });
}

async function loadBatches() {
  try {
    const payload = await api("/api/batches");
    state.batches = payload.batches;
    renderBatches();
    const active = state.batches.some((batch) => batch.status === "queued" || batch.status === "running");
    window.clearTimeout(state.batchPollTimer);
    if (active) state.batchPollTimer = window.setTimeout(async () => { await Promise.all([loadBatches(), loadJobs()]); }, 1200);
  } catch (error) {
    showAlert(error.message);
  }
}

async function loadBatchFolders() {
  try {
    const payload = await api("/api/batch-folders");
    $("#batch-workspace").textContent = payload.workspace;
    const options = payload.folders.map((folder) => {
      const option = document.createElement("option");
      option.value = folder;
      return option;
    });
    $("#batch-folder-options").replaceChildren(...options);
  } catch (error) {
    showAlert(error.message);
  }
}

function showView(name) {
  const review = name === "review";
  $("#workspace-view").hidden = review;
  $("#review-view").hidden = !review;
  $("#page-eyebrow").textContent = review ? "RECORDING REVIEW" : "PRIVATE WORKSPACE";
  $("#page-title").textContent = review ? "Transcript review" : "Transcription workspace";
  $$(".nav-item").forEach((item) => {
    const active = !review && item.dataset.view === (name === "jobs" ? "jobs" : "workspace");
    item.classList.toggle("is-active", active);
    if (active) item.setAttribute("aria-current", "page"); else item.removeAttribute("aria-current");
  });
  $(".sidebar").classList.remove("is-open");
  $("#mobile-menu").setAttribute("aria-expanded", "false");
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function updateReviewState(job) {
  state.activeJob = job;
  $("#review-title").textContent = job.display_name;
  const badge = $("#review-status");
  badge.className = `status-badge ${statusClass(job.status)}`;
  badge.textContent = statusLabel(job.status);
  $("#review-meta").textContent = `${formatBytes(job.size_bytes)} · ${job.duration_seconds ? formatDuration(job.duration_seconds) : "duration pending"} · ${modelLabel(job.model_id)}`;
  const processing = !["complete", "failed"].includes(job.status);
  $("#processing-panel").hidden = !processing;
  $("#failure-panel").hidden = job.status !== "failed";
  $("#review-workspace").hidden = job.status !== "complete";
  $("#export-button").disabled = job.status !== "complete";
  if (processing) {
    $("#processing-title").textContent = statusLabel(job.status);
    $("#processing-detail").textContent = job.status === "transcribing" ? "Whisper is converting speech to time-linked text on this device." : "The recording remains on this device.";
    $("#progress-bar").style.width = `${job.progress}%`;
    $("#progress-value").textContent = `${job.progress}%`;
  }
  if (job.status === "failed") {
    $("#failure-message").textContent = job.error?.message || "The job could not be completed.";
    $("#failure-code").textContent = job.error?.code || "UNKNOWN_ERROR";
  }
}

async function openJob(jobId) {
  window.clearTimeout(state.pollTimer);
  state.transcript = null;
  state.analysis = null;
  showView("review");
  try {
    const payload = await api(`/api/jobs/${jobId}`);
    updateReviewState(payload.job);
    if (payload.job.status === "complete") await loadCompletedJob(jobId);
    else if (payload.job.status !== "failed") schedulePoll(jobId);
  } catch (error) {
    showAlert(error.message);
    showView("workspace");
  }
}

function schedulePoll(jobId) {
  window.clearTimeout(state.pollTimer);
  state.pollTimer = window.setTimeout(async () => {
    try {
      const payload = await api(`/api/jobs/${jobId}`);
      updateReviewState(payload.job);
      await loadJobs();
      if (payload.job.status === "complete") await loadCompletedJob(jobId);
      else if (payload.job.status !== "failed") schedulePoll(jobId);
    } catch (error) {
      showAlert(error.message);
    }
  }, 1200);
}

async function loadCompletedJob(jobId) {
  try {
    const [transcriptPayload, analysisPayload] = await Promise.all([
      api(`/api/jobs/${jobId}/transcript`),
      api(`/api/jobs/${jobId}/analysis`),
    ]);
    state.transcript = transcriptPayload.transcript;
    state.analysis = analysisPayload.analysis;
    $("#media-player").src = `/api/jobs/${jobId}/media`;
    renderTranscript();
    renderAnalysis();
  } catch (error) {
    showAlert(error.message);
  }
}

function highlightedText(text, query) {
  const fragment = document.createDocumentFragment();
  if (!query) { fragment.append(document.createTextNode(text)); return fragment; }
  const lower = text.toLocaleLowerCase();
  const needle = query.toLocaleLowerCase();
  let offset = 0;
  while (true) {
    const index = lower.indexOf(needle, offset);
    if (index < 0) break;
    fragment.append(document.createTextNode(text.slice(offset, index)));
    const mark = document.createElement("mark");
    mark.textContent = text.slice(index, index + query.length);
    fragment.append(mark);
    offset = index + query.length;
  }
  fragment.append(document.createTextNode(text.slice(offset)));
  return fragment;
}

function renderTranscript() {
  const list = $("#transcript-list");
  list.replaceChildren();
  const query = $("#transcript-search").value.trim();
  const matches = state.transcript.segments.filter((segment) => !query || segment.text.toLocaleLowerCase().includes(query.toLocaleLowerCase()));
  $("#search-empty").hidden = matches.length > 0;
  matches.forEach((segment) => {
    const button = document.createElement("button");
    button.className = "transcript-segment";
    button.type = "button";
    button.dataset.segmentId = String(segment.id);
    button.dataset.start = String(segment.start);
    const time = document.createElement("span");
    time.className = "segment-time";
    time.textContent = formatDuration(segment.start);
    const text = document.createElement("span");
    text.className = "segment-text";
    text.append(highlightedText(segment.text, query));
    button.append(time, text);
    button.addEventListener("click", () => seekTo(segment.start));
    list.append(button);
  });
}

function seekTo(seconds) {
  const player = $("#media-player");
  player.currentTime = seconds;
  player.play().catch(() => {});
}

function syncActiveSegment() {
  if (!state.transcript) return;
  const current = $("#media-player").currentTime;
  const segment = state.transcript.segments.find((item) => current >= item.start && current < item.end);
  $$(".transcript-segment.is-active").forEach((item) => item.classList.remove("is-active"));
  if (!segment) return;
  const row = $(`.transcript-segment[data-segment-id="${segment.id}"]`);
  if (row) row.classList.add("is-active");
}

function renderAnalysis() {
  const report = state.analysis;
  if (!report) return;
  $("#metric-words").textContent = report.word_count.toLocaleString();
  $("#metric-minutes").textContent = report.speaking_minutes.toLocaleString();
  $("#metric-pace").textContent = report.words_per_minute.toLocaleString();
  const limitations = $("#limitations-list");
  limitations.replaceChildren(...report.limitations.map((text) => { const li = document.createElement("li"); li.textContent = text; return li; }));
  $$(".tab-list [role='tab']").forEach((tab) => tab.setAttribute("aria-selected", String(tab.dataset.tab === state.analysisTab)));
  const content = $("#analysis-content");
  content.replaceChildren();
  if (state.analysisTab === "terms") {
    const terms = document.createElement("div");
    terms.className = "term-list";
    report.top_terms.forEach((item) => {
      const chip = document.createElement("span");
      chip.className = "term-chip";
      const term = document.createTextNode(`${item.term} `);
      const count = document.createElement("strong");
      count.textContent = String(item.count);
      chip.append(term, count);
      terms.append(chip);
    });
    content.append(terms);
    return;
  }
  const key = ({ moments: "key_moments", actions: "action_candidates", questions: "questions" })[state.analysisTab];
  const items = report[key] || [];
  if (!items.length) {
    const empty = document.createElement("p");
    empty.className = "analysis-empty";
    empty.textContent = state.analysisTab === "actions" ? "No action-keyword matches found. Review the transcript before concluding there are no actions." : "No matching passages found.";
    content.append(empty);
    return;
  }
  items.forEach((item) => {
    const row = document.createElement("div");
    row.className = "analysis-item";
    const time = document.createElement("button");
    time.className = "analysis-time";
    time.type = "button";
    time.textContent = formatDuration(item.timestamp_seconds);
    time.addEventListener("click", () => seekTo(item.timestamp_seconds));
    const text = document.createElement("p");
    text.textContent = item.text;
    row.append(time, text);
    content.append(row);
  });
}

function selectFile(file) {
  if (!file) return;
  if (!file.name.toLocaleLowerCase().endsWith(".mp4")) { showAlert("Select an MP4 video file."); return; }
  state.selectedFile = file;
  const pill = $("#selected-file");
  pill.hidden = false;
  pill.textContent = `${file.name} · ${formatBytes(file.size)}`;
  updateUploadButton();
}

function updateUploadButton() {
  const systemReady = state.health?.status === "ready";
  $("#start-button").disabled = !(systemReady && state.selectedFile && $("#consent-checkbox").checked);
}

function selectedBatchFormats() {
  return $$("input[name='batch-format']:checked").map((input) => input.value);
}

function updateBatchButton() {
  const systemReady = state.health?.status === "ready";
  const foldersReady = $("#batch-input-folder").value.trim() && $("#batch-output-folder").value.trim();
  $("#batch-start-button").disabled = !(systemReady && foldersReady && selectedBatchFormats().length && $("#batch-consent-checkbox").checked);
}

function setUploadMode(mode) {
  const batch = mode === "batch";
  $("#upload-form").hidden = batch;
  $("#batch-form").hidden = !batch;
  $$('[data-upload-mode]').forEach((button) => button.setAttribute("aria-selected", String(button.dataset.uploadMode === mode)));
  if (batch) $("#batch-input-folder").focus(); else $("#drop-zone").focus();
}

async function submitBatch(event) {
  event.preventDefault();
  const button = $("#batch-start-button");
  button.disabled = true;
  button.textContent = "Starting bounded batch…";
  try {
    await api("/api/batches", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        input_folder: $("#batch-input-folder").value.trim(),
        output_folder: $("#batch-output-folder").value.trim(),
        formats: selectedBatchFormats(),
        language: $("#batch-language-select").value,
        consent_confirmed: $("#batch-consent-checkbox").checked,
      }),
    });
    $("#batch-consent-checkbox").checked = false;
    toast("Folder batch started. Originals remain in the input folder.");
    await Promise.all([loadBatches(), loadJobs(), loadBatchFolders()]);
    $("#batches-heading").scrollIntoView({ behavior: "smooth" });
  } catch (error) {
    showAlert(error.message);
  } finally {
    button.textContent = "Transcribe folder locally";
    updateBatchButton();
  }
}

async function submitUpload(event) {
  event.preventDefault();
  if (!state.selectedFile) return;
  const button = $("#start-button");
  const formData = new FormData();
  formData.append("file", state.selectedFile);
  formData.append("language", $("#language-select").value);
  formData.append("consent_confirmed", String($("#consent-checkbox").checked));
  button.disabled = true;
  button.textContent = "Securely importing…";
  try {
    const payload = await api("/api/jobs", { method: "POST", body: formData });
    resetUpload();
    await loadJobs();
    await openJob(payload.job.id);
  } catch (error) {
    showAlert(error.message);
  } finally {
    button.textContent = "Transcribe locally";
    updateUploadButton();
  }
}

function resetUpload() {
  state.selectedFile = null;
  $("#file-input").value = "";
  $("#consent-checkbox").checked = false;
  $("#selected-file").hidden = true;
}

async function loadHealth() {
  try {
    state.health = await api("/api/health");
    const ready = state.health.status === "ready";
    $("#health-label").textContent = ready ? "System ready" : "Setup needed";
    $("#health-dot").classList.toggle("is-warning", !ready);
    const details = $("#health-details");
    const rows = [
      ["FFmpeg audio tools", state.health.ffmpeg_ready && state.health.ffprobe_ready],
      ["Local Whisper model", state.health.model_ready],
      ["External network", !state.health.network_required],
    ];
    details.replaceChildren(...rows.map(([label, ok]) => {
      const row = document.createElement("div");
      row.className = "health-row";
      const name = document.createElement("span"); name.textContent = label;
      const value = document.createElement("strong"); value.textContent = ok ? "Ready" : "Needs attention"; value.style.color = ok ? "var(--accent-strong)" : "var(--warning)";
      row.append(name, value); return row;
    }));
    updateUploadButton();
    updateBatchButton();
  } catch (error) {
    $("#health-label").textContent = "Service unavailable";
    $("#health-dot").classList.add("is-warning");
  }
}

function initializePretext() {
  document.fonts.ready.then(() => {
    const elements = $$('[data-pretext]');
    const prepared = new Map();
    for (const element of elements) prepared.set(element, prepare(element.textContent, getComputedStyle(element).font));
    const relayout = () => {
      for (const [element, handle] of prepared) {
        const lineHeight = parseFloat(getComputedStyle(element).lineHeight);
        const result = layout(handle, element.clientWidth, lineHeight);
        if (Number.isFinite(result.height)) element.style.height = `${Math.ceil(result.height)}px`;
      }
    };
    new ResizeObserver(relayout).observe(document.body);
    relayout();
  }).catch(() => {});
}

function bindEvents() {
  const dropZone = $("#drop-zone");
  dropZone.addEventListener("click", () => $("#file-input").click());
  dropZone.addEventListener("keydown", (event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); $("#file-input").click(); } });
  $("#file-input").addEventListener("change", (event) => selectFile(event.target.files[0]));
  ["dragenter", "dragover"].forEach((name) => dropZone.addEventListener(name, (event) => { event.preventDefault(); dropZone.classList.add("is-dragging"); }));
  ["dragleave", "drop"].forEach((name) => dropZone.addEventListener(name, (event) => { event.preventDefault(); dropZone.classList.remove("is-dragging"); }));
  dropZone.addEventListener("drop", (event) => selectFile(event.dataTransfer.files[0]));
  $("#consent-checkbox").addEventListener("change", updateUploadButton);
  $("#upload-form").addEventListener("submit", submitUpload);
  $$('[data-upload-mode]').forEach((button) => button.addEventListener("click", () => setUploadMode(button.dataset.uploadMode)));
  ["input", "change"].forEach((eventName) => {
    $("#batch-input-folder").addEventListener(eventName, updateBatchButton);
    $("#batch-output-folder").addEventListener(eventName, updateBatchButton);
  });
  $("#batch-consent-checkbox").addEventListener("change", updateBatchButton);
  $$("input[name='batch-format']").forEach((input) => input.addEventListener("change", updateBatchButton));
  $("#batch-form").addEventListener("submit", submitBatch);
  $("#new-upload-button").addEventListener("click", () => { showView("workspace"); setUploadMode("single"); });
  $("#refresh-jobs").addEventListener("click", loadJobs);
  $("#refresh-batches").addEventListener("click", () => Promise.all([loadBatches(), loadBatchFolders()]));
  $("#back-button").addEventListener("click", () => { window.clearTimeout(state.pollTimer); showView("workspace"); loadJobs(); });
  $$(".nav-item").forEach((button) => button.addEventListener("click", () => { showView(button.dataset.view); if (button.dataset.view === "jobs") $("#recent-heading").scrollIntoView(); }));
  $("#mobile-menu").addEventListener("click", () => { const sidebar = $(".sidebar"); const open = sidebar.classList.toggle("is-open"); $("#mobile-menu").setAttribute("aria-expanded", String(open)); });
  $("#health-button").addEventListener("click", () => $("#health-dialog").showModal());
  $("#export-button").addEventListener("click", () => { const menu = $("#export-options"); menu.hidden = !menu.hidden; $("#export-button").setAttribute("aria-expanded", String(!menu.hidden)); });
  $$("#export-options button").forEach((button) => button.addEventListener("click", () => { if (state.activeJob) window.location.assign(`/api/jobs/${state.activeJob.id}/export?format=${button.dataset.format}`); $("#export-options").hidden = true; }));
  $("#delete-button").addEventListener("click", () => $("#delete-dialog").showModal());
  $("#cancel-delete").addEventListener("click", () => $("#delete-dialog").close());
  $("#confirm-delete").addEventListener("click", async () => {
    if (!state.activeJob) return;
    try {
      await api(`/api/jobs/${state.activeJob.id}`, { method: "DELETE" });
      $("#delete-dialog").close();
      toast("Recording and derived files deleted.");
      state.activeJob = null;
      await loadJobs();
      showView("workspace");
    } catch (error) { showAlert(error.message); }
  });
  $("#cancel-batch-delete").addEventListener("click", () => $("#batch-delete-dialog").close());
  $("#confirm-batch-delete").addEventListener("click", async () => {
    if (!state.activeBatchId) return;
    try {
      await api(`/api/batches/${state.activeBatchId}`, { method: "DELETE" });
      $("#batch-delete-dialog").close();
      state.activeBatchId = null;
      toast("Managed batch copies deleted. Input and output folders were not changed.");
      await Promise.all([loadBatches(), loadJobs()]);
    } catch (error) { showAlert(error.message); }
  });
  $("#transcript-search").addEventListener("input", renderTranscript);
  $("#media-player").addEventListener("timeupdate", syncActiveSegment);
  $$(".tab-list [role='tab']").forEach((tab) => tab.addEventListener("click", () => { state.analysisTab = tab.dataset.tab; renderAnalysis(); }));
  document.addEventListener("keydown", (event) => {
    if (event.key === "/" && !["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement.tagName) && !$("#review-view").hidden) {
      event.preventDefault(); $("#transcript-search").focus();
    }
    if (event.key === "Escape") $("#export-options").hidden = true;
  });
}

async function initialize() {
  bindEvents();
  initializePretext();
  try {
    const session = await api("/api/session");
    state.token = session.request_token;
    $("#upload-limits").textContent = `MP4 with audio · up to ${formatBytes(session.max_upload_bytes)} · ${Math.floor(session.max_media_seconds / 3600)} hours · retained ${session.retention_days} days unless deleted`;
    $("#batch-limits").textContent = `Non-recursive · up to ${session.max_batch_files} MP4s / ${formatBytes(session.max_batch_bytes)} combined · no overwrites · retained ${session.retention_days} days unless removed`;
    await Promise.all([loadHealth(), loadJobs(), loadBatches(), loadBatchFolders()]);
  } catch (error) {
    showAlert("The local transcription service is not available. Restart the utility and refresh this page.");
  }
}

initialize();
