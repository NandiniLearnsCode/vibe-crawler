const byId = (id) => document.getElementById(id);

const form = byId("crawl-form");
const urlInput = byId("url-input");
const modeCheckbox = byId("agentic-mode");
const founderModeCheckbox = byId("founder-mode");
const statusCard = byId("status-card");
const statusText = byId("status-text");
const summaryCard = byId("summary-card");
const severityContainer = byId("severity-breakdown");
const digestCard = byId("digest-card");
const digestTitle = byId("digest-title");
const digestHeadline = byId("digest-headline");
const digestHighlights = byId("digest-highlights");
const digestRootCauses = byId("digest-root-causes");
const digestTopFindings = byId("digest-top-findings");
const digestFixFirst = byId("digest-fix-first");
const findingsContainer = byId("findings-container");
const pagesContainer = byId("pages-container");
const reportLink = byId("report-link");
const reportLinkWrap = byId("report-link-wrap");
const ticketMdLink = byId("ticket-md-link");
const ticketCsvLink = byId("ticket-csv-link");
const ticketGithubLink = byId("ticket-github-link");
const ticketLinearLink = byId("ticket-linear-link");
const ticketMarkdownLink = byId("ticket-markdown-link");
const ticketCsvDownloadLink = byId("ticket-csv-download-link");
const ticketMarkdownLinkWrap = byId("ticket-md-link-wrap");
const ticketCsvLinkWrap = byId("ticket-csv-link-wrap");
const copyTicketsButton = byId("copy-ticket-list-btn");
const pushGithubPreviewButton = byId("push-github-preview-btn");
const pushLinearPreviewButton = byId("push-linear-preview-btn");
const pushPreviewCard = byId("ticket-push-preview");
const pushPreviewTitle = byId("ticket-push-target");
const pushPreviewBody = byId("ticket-push-body");
const pushStatusText = byId("ticket-push-status");
const pushConfirmButton = byId("ticket-push-confirm-btn");
const pushCancelButton = byId("ticket-push-cancel-btn");
const agenticJsonLink = byId("agentic-json-link");
const agenticJsonLinkWrap = byId("agentic-json-link-wrap");
const agenticMdLink = byId("agentic-md-link");
const agenticMdLinkWrap = byId("agentic-md-link-wrap");
const agenticShareLink = byId("agentic-share-link");
const agenticShareLinkWrap = byId("agentic-share-link-wrap");
const clusterSummary = byId("cluster-summary");
const clusterList = byId("cluster-list");
const emptyFindings = byId("empty-findings");
const pageMeta = byId("page-meta");

let pollTimer = null;
let pendingPushAction = null;

function resetView() {
  statusCard.hidden = false;
  summaryCard.hidden = true;
  digestCard.hidden = true;
  digestTitle.textContent = "Founder TL;DR";
  statusText.textContent = "Starting crawl...";
  severityContainer.innerHTML = "";
  digestHeadline.textContent = "";
  digestHighlights.innerHTML = "";
  digestRootCauses.innerHTML = "";
  digestTopFindings.innerHTML = "";
  digestFixFirst.innerHTML = "";
  if (clusterSummary) clusterSummary.innerHTML = "";
  if (clusterList) clusterList.innerHTML = "";
  findingsContainer.innerHTML = "";
  pagesContainer.innerHTML = "";
  if (reportLinkWrap) reportLinkWrap.classList.add("hidden");
  if (ticketMarkdownLinkWrap) ticketMarkdownLinkWrap.classList.add("hidden");
  if (ticketCsvLinkWrap) ticketCsvLinkWrap.classList.add("hidden");
  if (ticketMdLink) ticketMdLink.classList.add("hidden");
  if (ticketCsvLink) ticketCsvLink.classList.add("hidden");
  if (ticketGithubLink) ticketGithubLink.classList.add("hidden");
  if (ticketLinearLink) ticketLinearLink.classList.add("hidden");
  agenticJsonLinkWrap.classList.add("hidden");
  agenticMdLinkWrap.classList.add("hidden");
  agenticShareLinkWrap.classList.add("hidden");
  if (pushPreviewCard) pushPreviewCard.classList.add("hidden");
  if (pushStatusText) pushStatusText.textContent = "";
  pendingPushAction = null;
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

function renderClusters(report) {
  const clusters = report.issue_clusters || [];
  if (!clusterSummary || !clusterList) return;
  if (clusterSummary) clusterSummary.innerHTML = "";
  if (clusterList) clusterList.innerHTML = "";
  if (!clusters.length) {
    return;
  }
  const reducedBy = Math.max((report.summary?.total_bugs || 0) - clusters.length, 0);
  const stat = document.createElement("div");
  stat.className = "metric";
  stat.innerHTML = `<div class="k">Clustered Root Causes</div><div class="v">${clusters.length}</div><div class="muted">Collapsed ${reducedBy} duplicate finding(s)</div>`;
  clusterSummary.appendChild(stat);

  for (const cluster of clusters) {
    const item = document.createElement("li");
    item.className = "bug-meta";
    const sev = String(cluster.severity_highest || "medium").toUpperCase();
    const title = cluster.root_cause_hint || cluster.type || "Root cause";
    const count = cluster.occurrences || 1;
    item.textContent = `[${sev}] ${title} — ${count} occurrence(s)`;
    clusterList.appendChild(item);
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

function renderDigest(report) {
  const digest = report.digest;
  if (!digest) {
    digestCard.hidden = true;
    return;
  }
  digestCard.hidden = false;
  const founderMode = digest.founder_mode || {};
  const isFounderView = (digest.default_view || "founder") === "founder";
  digestTitle.textContent = isFounderView ? "Founder TL;DR (default)" : "Digest";
  digestHeadline.textContent = digest.headline || "Crawl digest unavailable";

  digestHighlights.innerHTML = "";
  const summaryLines = founderMode.three_line_summary || digest.highlights || [];
  for (const line of summaryLines) {
    const li = document.createElement("li");
    li.className = "bug-meta";
    li.textContent = line;
    digestHighlights.appendChild(li);
  }
  if (!digestHighlights.children.length) {
    const li = document.createElement("li");
    li.className = "bug-meta";
    li.textContent = "Summary unavailable for this run.";
    digestHighlights.appendChild(li);
  }

  digestRootCauses.innerHTML = "";
  for (const cluster of digest.clustered_top_issues || []) {
    const li = document.createElement("li");
    li.className = "bug-meta";
    li.textContent = `[${String(cluster.severity_highest || "medium").toUpperCase()}] ${cluster.root_cause_hint || cluster.type || "Root cause"} (${cluster.occurrences || 1}x)`;
    digestRootCauses.appendChild(li);
  }
  if (!digestRootCauses.children.length) {
    const li = document.createElement("li");
    li.className = "bug-meta";
    li.textContent = "No clustered root causes for this run.";
    digestRootCauses.appendChild(li);
  }

  digestTopFindings.innerHTML = "";
  for (const finding of founderMode.top_blockers || digest.fix_first || []) {
    const li = document.createElement("li");
    li.className = "bug-meta";
    const confidence = formatPercent(finding.confidence || 0);
    li.textContent = `[${(finding.severity || "medium").toUpperCase()}] ${finding.title || "Untitled"} (${confidence})`;
    digestTopFindings.appendChild(li);
  }
  if (!digestTopFindings.children.length) {
    const li = document.createElement("li");
    li.className = "bug-meta";
    li.textContent = "No critical findings in this crawl.";
    digestTopFindings.appendChild(li);
  }

  digestFixFirst.innerHTML = "";
  for (const ticket of founderMode.engineering_ticket_list || []) {
    const li = document.createElement("li");
    li.className = "bug-meta";
    li.textContent = ticket;
    digestFixFirst.appendChild(li);
  }
  if (!digestFixFirst.children.length) {
    const li = document.createElement("li");
    li.className = "bug-meta";
    li.textContent = "No engineering tickets generated.";
    digestFixFirst.appendChild(li);
  }
}

async function copyTicketsToClipboard(jobId, report) {
  let text = "";
  if (report?.digest?.founder_mode?.engineering_ticket_block) {
    text = report.digest.founder_mode.engineering_ticket_block;
  }
  if (!text) {
    try {
      const response = await fetch(`/api/jobs/${encodeURIComponent(jobId)}/download/tickets/md`);
      if (response.ok) {
        text = await response.text();
      }
    } catch (error) {
      text = "";
    }
  }
  if (!text) {
    alert("No ticket content available for this run.");
    return;
  }
  try {
    await navigator.clipboard.writeText(text);
    copyTicketsButton.textContent = "Copied tickets";
    setTimeout(() => {
      copyTicketsButton.textContent = "Copy tickets";
    }, 1500);
  } catch (error) {
    alert("Could not copy tickets. You can download the markdown file instead.");
  }
}

function showPushPreview(kind, payload, jobId) {
  pendingPushAction = { kind, jobId };
  pushPreviewCard.hidden = false;
  pushPreviewTitle.textContent = kind === "github" ? "GitHub Push Preview" : "Linear Push Preview";
  pushPreviewBody.textContent = payload;
  pushStatusText.textContent = `Preview ready. Confirm to push to ${kind === "github" ? "GitHub Issues" : "Linear"}.`;
}

async function requestPushPreview(jobId, target) {
  try {
    const response = await fetch(`/api/jobs/${encodeURIComponent(jobId)}/push-preview/${target}`);
    const data = await response.json();
    if (!response.ok) {
      pushStatusText.textContent = `Preview failed: ${data.detail || "unknown error"}`;
      return;
    }
    showPushPreview(target, data.preview || "", jobId);
  } catch (error) {
    pushStatusText.textContent = `Preview failed: ${error.message}`;
  }
}

async function confirmPush() {
  if (!pendingPushAction) return;
  const { jobId, kind } = pendingPushAction;
  try {
    const response = await fetch(`/api/jobs/${encodeURIComponent(jobId)}/push-confirm/${kind}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    const data = await response.json();
    if (!response.ok) {
      pushStatusText.textContent = `Push failed: ${data.detail || "unknown error"}`;
      return;
    }
    const count = data.items_created ?? 0;
    pushStatusText.textContent = `Push successful: created ${count} ${kind === "github" ? "GitHub issue(s)" : "Linear issue(s)"}.`;
    if (pushPreviewCard) pushPreviewCard.classList.add("hidden");
    pendingPushAction = null;
  } catch (error) {
    pushStatusText.textContent = `Push failed: ${error.message}`;
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
  renderClusters(report);
  renderDigest(report);
  renderFindings(report);
  renderPages(report);

  reportLink.href = `/api/jobs/${encodeURIComponent(jobId)}/download`;
  reportLinkWrap.classList.remove("hidden");
  if (ticketMdLink) {
    ticketMdLink.href = `/api/jobs/${encodeURIComponent(jobId)}/download/tickets/md`;
    ticketMdLink.classList.remove("hidden");
  }
  if (ticketCsvLink) {
    ticketCsvLink.href = `/api/jobs/${encodeURIComponent(jobId)}/download/tickets/csv`;
    ticketCsvLink.classList.remove("hidden");
  }
  if (ticketGithubLink) {
    ticketGithubLink.href = `/api/jobs/${encodeURIComponent(jobId)}/download/tickets/github`;
    ticketGithubLink.classList.remove("hidden");
  }
  if (ticketLinearLink) {
    ticketLinearLink.href = `/api/jobs/${encodeURIComponent(jobId)}/download/tickets/linear`;
    ticketLinearLink.classList.remove("hidden");
  }
  if (ticketMarkdownLink) {
    ticketMarkdownLink.href = `/api/jobs/${encodeURIComponent(jobId)}/download/tickets/md`;
  }
  if (ticketCsvDownloadLink) {
    ticketCsvDownloadLink.href = `/api/jobs/${encodeURIComponent(jobId)}/download/tickets/csv`;
  }
  if (ticketMarkdownLinkWrap) ticketMarkdownLinkWrap.classList.remove("hidden");
  if (ticketCsvLinkWrap) ticketCsvLinkWrap.classList.remove("hidden");
  if (copyTicketsButton) {
    copyTicketsButton.onclick = () => {
      copyTicketsToClipboard(jobId, report);
    };
  }
  if (pushGithubPreviewButton) {
    pushGithubPreviewButton.onclick = () => {
      requestPushPreview(jobId, "github");
    };
  }
  if (pushLinearPreviewButton) {
    pushLinearPreviewButton.onclick = () => {
      requestPushPreview(jobId, "linear");
    };
  }

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

if (pushConfirmButton) {
  pushConfirmButton.addEventListener("click", confirmPush);
}
if (pushCancelButton) {
  pushCancelButton.addEventListener("click", () => {
    if (pushPreviewCard) pushPreviewCard.classList.add("hidden");
    pendingPushAction = null;
    if (pushStatusText) pushStatusText.textContent = "Push cancelled.";
  });
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
    view_mode: founderModeCheckbox && founderModeCheckbox.checked ? "founder" : "detailed",
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
