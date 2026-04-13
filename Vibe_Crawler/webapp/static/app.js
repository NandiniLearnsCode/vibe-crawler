const form = document.getElementById("crawl-form");
const statusBox = document.getElementById("job-status");
const summaryBox = document.getElementById("summary-box");
const findings = document.getElementById("findings");
const formMessage = document.getElementById("form-message");
let activePoll = null;

function setMessage(text, isError = false) {
  formMessage.textContent = text;
  formMessage.className = isError ? "hint error" : "hint";
}

function resetReportView() {
  summaryBox.innerHTML = "No report yet.";
  findings.innerHTML = "";
}

function setStatus(job) {
  if (!job) {
    statusBox.textContent = "No active job.";
    return;
  }
  const lines = [
    `Job: ${job.job_id}`,
    `URL: ${job.url}`,
    `Status: ${job.status}`,
    `Pages crawled: ${job.pages_crawled}`,
    `Bugs found: ${job.bugs_found}`,
  ];
  if (job.error) lines.push(`Error: ${job.error}`);
  statusBox.textContent = lines.join("\n");
}

function groupBySeverity(bugs) {
  const grouped = { high: [], medium: [], low: [] };
  for (const bug of bugs) {
    if (grouped[bug.severity]) grouped[bug.severity].push(bug);
    else grouped.medium.push(bug);
  }
  return grouped;
}

function renderSummary(report, jobId) {
  const summary = report.summary || {};
  summaryBox.innerHTML = `
    <div><strong>Run ID:</strong> ${report.run_id}</div>
    <div><strong>Pages crawled:</strong> ${summary.pages_crawled ?? 0}</div>
    <div><strong>Total bugs:</strong> ${summary.total_bugs ?? 0}</div>
    <div><strong>Started:</strong> ${report.started_at ?? "n/a"}</div>
    <div><strong>Finished:</strong> ${report.finished_at ?? "n/a"}</div>
    <div style="margin-top:8px;"><a href="/api/jobs/${encodeURIComponent(jobId)}/download" target="_blank" rel="noopener">Download JSON report</a></div>
  `;
}

function renderFindings(report) {
  const bugs = report.bugs || [];
  if (!bugs.length) {
    findings.innerHTML = `<div class="status-box">No high-confidence bugs detected for this run.</div>`;
    return;
  }
  const grouped = groupBySeverity(bugs);
  const order = ["high", "medium", "low"];
  findings.innerHTML = "";

  for (const severity of order) {
    const items = grouped[severity];
    if (!items.length) continue;

    const section = document.createElement("section");
    section.className = "finding-group";
    section.innerHTML = `<h3>${severity.toUpperCase()} (${items.length})</h3>`;

    for (const bug of items) {
      const card = document.createElement("article");
      card.className = "bug";

      const confidencePct = Math.round((bug.confidence || 0) * 100);
      const steps = (bug.reproduction_steps || []).map((step) => `<li>${step}</li>`).join("");
      const network = (bug.network_evidence || []).join("\n");
      const consoleOut = (bug.console_errors || []).join("\n");

      card.innerHTML = `
        <div>
          <span class="pill ${severity}">${severity}</span>
          <span class="pill">${bug.type}</span>
          <span class="pill">confidence ${confidencePct}%</span>
        </div>
        <div class="bug-title">${bug.short_title}</div>
        <div class="bug-meta">${bug.page_url}</div>
        <p>${bug.description}</p>
        <ol class="steps">${steps}</ol>
        ${bug.screenshot_path ? `<p class="bug-meta">screenshot: ${bug.screenshot_path}</p>` : ""}
        ${network ? `<pre>${network}</pre>` : ""}
        ${consoleOut ? `<pre>${consoleOut}</pre>` : ""}
      `;
      section.appendChild(card);
    }
    findings.appendChild(section);
  }
}

async function loadReport(jobId) {
  const response = await fetch(`/api/jobs/${encodeURIComponent(jobId)}/report`);
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || "Could not load report");
  }
  return data;
}

async function pollJob(jobId) {
  if (activePoll) {
    clearTimeout(activePoll);
    activePoll = null;
  }
  try {
    const response = await fetch(`/api/jobs/${encodeURIComponent(jobId)}`);
    const job = await response.json();
    if (!response.ok) {
      throw new Error(job.detail || "Could not fetch job status");
    }
    setStatus(job);

    if (job.status === "queued" || job.status === "running") {
      activePoll = setTimeout(() => pollJob(jobId), 1500);
      return;
    }
    if (job.status === "failed") {
      setMessage(`Crawl failed: ${job.error || "Unknown error"}`, true);
      return;
    }
    if (job.status === "completed") {
      const report = await loadReport(jobId);
      renderSummary(report, jobId);
      renderFindings(report);
      setMessage("Crawl complete.");
    }
  } catch (error) {
    setMessage(`Polling failed: ${error.message}`, true);
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  resetReportView();
  setMessage("Submitting crawl job...");

  const payload = {
    url: document.getElementById("start-url").value.trim(),
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
      throw new Error(data.detail || "Could not create crawl job");
    }
    setMessage(`Job ${data.job_id} created. Running crawl...`);
    setStatus({
      job_id: data.job_id,
      url: payload.url,
      status: data.status,
      pages_crawled: 0,
      bugs_found: 0,
    });
    await pollJob(data.job_id);
  } catch (error) {
    setMessage(error.message, true);
  }
});
