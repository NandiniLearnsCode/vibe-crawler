const form = document.getElementById("crawl-form");
const urlInput = document.getElementById("url-input");
const modeCheckbox = document.getElementById("agentic-mode");
const statusCard = document.getElementById("status-card");
const statusText = document.getElementById("status-text");
const summaryCard = document.getElementById("summary-card");
const severityContainer = document.getElementById("severity-breakdown");
const findingsContainer = document.getElementById("findings-container");
const pagesContainer = document.getElementById("pages-container");
const reportLink = document.getElementById("report-link");
const reportLinkWrap = document.getElementById("report-link-wrap");
const agenticJsonLink = document.getElementById("agentic-json-link");
const agenticJsonLinkWrap = document.getElementById("agentic-json-link-wrap");
const agenticMdLink = document.getElementById("agentic-md-link");
const agenticMdLinkWrap = document.getElementById("agentic-md-link-wrap");
const agenticShareLink = document.getElementById("agentic-share-link");
const agenticShareLinkWrap = document.getElementById("agentic-share-link-wrap");
const emptyFindings = document.getElementById("empty-findings");
const pageMeta = document.getElementById("page-meta");

let pollTimer = null;

function resetView() {
  statusCard.hidden = false;
  summaryCard.hidden = true;
  statusText.textContent = "Starting crawl...";
  severityContainer.innerHTML = "";
  findingsContainer.innerHTML = "";
  pagesContainer.innerHTML = "";
  reportLinkWrap.classList.add("hidden");
  agenticJsonLinkWrap.classList.add("hidden");
  agenticMdLinkWrap.classList.add("hidden");
  agenticShareLinkWrap.classList.add("hidden");
  emptyFindings.classList.add("hidden");
  pageMeta.textContent = "";
}

function formatPercent(value) {
  return `${Math.round(value * 100)}%`;
}

function setStatus(text) {
  statusCard.hidden = false;
  statusText.textContent = text;
}

function createTag(text, className = "") {
  const span = document.createElement("span");
  span.className = `pill ${className}`.trim();
  span.textContent = text;
  return span;
}

function renderSeverity(summary) {
  const map = summary.bugs_by_severity || {};
  const severities = ["high", "medium", "low"];
  for (const sev of severities) {
    const box = document.createElement("div");
    box.className = "metric";
    box.innerHTML = `<div class="k">${sev.toUpperCase()}</div><div class="v">${map[sev] || 0}</div>`;
    severityContainer.appendChild(box);
  }
}

function renderFindings(report) {
  const bugs = report.bugs || [];
  if (!bugs.length) {
    emptyFindings.classList.remove("hidden");
    return;
  }
  emptyFindings.classList.add("hidden");

  const grouped = { high: [], medium: [], low: [] };
  for (const bug of bugs) {
    (grouped[bug.severity] || grouped.medium).push(bug);
  }

  for (const sev of ["high", "medium", "low"]) {
    const items = grouped[sev];
    if (!items.length) continue;

    const section = document.createElement("section");
    section.className = "severity-group";
    section.innerHTML = `<div class="severity-title">${sev.toUpperCase()} (${items.length})</div>`;

    for (const bug of items) {
      const card = document.createElement("article");
      card.className = "bug";

      const meta = document.createElement("div");
      meta.appendChild(createTag(sev, sev));
      meta.appendChild(createTag(bug.type));
      meta.appendChild(createTag(`confidence ${formatPercent(bug.confidence || 0)}`));

      const title = document.createElement("div");
      title.className = "bug-title";
      title.textContent = bug.short_title;

      const bugMeta = document.createElement("div");
      bugMeta.className = "bug-meta";
      bugMeta.textContent = bug.page_url;

      const desc = document.createElement("p");
      desc.textContent = bug.description;

      const steps = document.createElement("ol");
      steps.className = "steps";
      for (const step of bug.reproduction_steps || []) {
        const li = document.createElement("li");
        li.textContent = step;
        steps.appendChild(li);
      }

      card.append(meta, title, bugMeta, desc, steps);

      if (bug.screenshot_path) {
        const screenshot = document.createElement("div");
        screenshot.className = "bug-meta";
        screenshot.textContent = `screenshot: ${bug.screenshot_path}`;
        card.appendChild(screenshot);
      }
      if (bug.network_evidence?.length) {
        const net = document.createElement("pre");
        net.textContent = bug.network_evidence.join("\n");
        card.appendChild(net);
      }
      if (bug.console_errors?.length) {
        const con = document.createElement("pre");
        con.textContent = bug.console_errors.join("\n");
        card.appendChild(con);
      }
      section.appendChild(card);
    }
    findingsContainer.appendChild(section);
  }
}

function renderPages(report) {
  const pages = report.pages || [];
  pageMeta.textContent = `${pages.length} page(s) crawled`;
  for (const page of pages) {
    const li = document.createElement("li");
    li.className = "bug-meta";
    li.textContent = `${page.url} | depth ${page.depth} | status ${page.status_code ?? "n/a"} | links ${page.discovered_links.length}`;
    pagesContainer.appendChild(li);
  }
}

function renderReport(report, jobId, jobMeta = null) {
  summaryCard.hidden = false;
  statusCard.hidden = true;

  const summary = report.summary || {};
  document.getElementById("run-id").textContent = report.run_id || "n/a";
  document.getElementById("run-mode").textContent = report.mode || "deterministic";
  document.getElementById("pages-crawled").textContent = summary.pages_crawled ?? 0;
  document.getElementById("total-bugs").textContent = summary.total_bugs ?? 0;
  renderSeverity(summary);
  renderFindings(report);
  renderPages(report);

  reportLink.href = `/api/jobs/${encodeURIComponent(jobId)}/download`;
  reportLinkWrap.classList.remove("hidden");

  if (jobMeta && jobMeta.agentic_json_path) {
    agenticJsonLink.href = `/api/jobs/${encodeURIComponent(jobId)}/download/agentic-json`;
    agenticJsonLinkWrap.classList.remove("hidden");
  }
  if (jobMeta && jobMeta.agentic_markdown_path) {
    agenticMdLink.href = `/api/jobs/${encodeURIComponent(jobId)}/download/agentic-markdown`;
    agenticMdLinkWrap.classList.remove("hidden");
    agenticShareLink.href = `/share/${encodeURIComponent(jobId)}`;
    agenticShareLinkWrap.classList.remove("hidden");
  }
}

async function pollJob(jobId) {
  if (pollTimer) clearTimeout(pollTimer);
  try {
    const response = await fetch(`/api/jobs/${encodeURIComponent(jobId)}`);
    const data = await response.json();
    if (!response.ok) {
      setStatus(`Job error: ${data.detail || "failed to fetch job status"}`);
      return;
    }

    if (data.status === "queued" || data.status === "running") {
      const label = data.status === "running" ? "Crawl running..." : "Crawl queued...";
      setStatus(label);
      pollTimer = setTimeout(() => pollJob(jobId), 1500);
      return;
    }

    if (data.status === "failed") {
      setStatus(`Crawl failed: ${data.error || "unknown error"}`);
      return;
    }

    if (data.status === "completed") {
      const reportRes = await fetch(`/api/jobs/${encodeURIComponent(jobId)}/report`);
      const report = await reportRes.json();
      if (!reportRes.ok) {
        setStatus(`Failed to load report: ${report.detail || "unknown error"}`);
        return;
      }
      renderReport(report, jobId, data);
    }
  } catch (error) {
    setStatus(`Network error: ${error.message}`);
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  resetView();

  const payload = {
    url: urlInput.value.trim(),
    mode: modeCheckbox && modeCheckbox.checked ? "agentic" : "deterministic",
    max_pages: Number(document.getElementById("max-pages").value || 8),
    max_depth: Number(document.getElementById("max-depth").value || 2),
    timeout_ms: Number(document.getElementById("timeout-ms").value || 20000),
    include_mobile_checks: document.getElementById("mobile-checks").checked,
    include_form_checks: document.getElementById("form-checks").checked,
  };

  try {
    const response = await fetch("/api/jobs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) {
      setStatus(`Could not start crawl: ${data.detail || "unknown error"}`);
      return;
    }
    setStatus(`Job created: ${data.job_id}. Running crawl...`);
    pollJob(data.job_id);
  } catch (error) {
    setStatus(`Request failed: ${error.message}`);
  }
});
