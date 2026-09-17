(() => {
  "use strict";

  const data = window.GTQ_DATA;
  const main = document.querySelector("#main-content");
  const breadcrumb = document.querySelector("#breadcrumb");
  const nav = document.querySelector("#primary-navigation");
  const menuButton = document.querySelector("#menu-button");
  const scrim = document.querySelector("#mobile-scrim");
  const toastRegion = document.querySelector("#toast-region");

  if (!data || !main) {
    document.body.innerHTML = "<p>The design fixture could not be loaded.</p>";
    return;
  }

  const stateLabels = {
    locked: "Locked",
    available: "Available",
    in_progress: "In progress",
    evidence_ready: "Evidence ready",
    locally_validated: "Locally validated",
    submitted: "Submitted",
    needs_changes: "Needs changes",
    verified: "Verified",
    detected: "Detected",
    present: "Present",
    warning: "Warning",
    missing: "Missing",
    fail: "Failed"
  };

  const iconFor = {
    validation: "V",
    review: "R",
    verified: "✓",
    pass: "✓",
    detected: "✓",
    present: "✓",
    warning: "!",
    needs_changes: "!",
    fail: "×",
    missing: "×",
    locked: "·"
  };

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function titleCase(value) {
    return String(value).replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
  }

  function questFor(id) {
    return data.quests.find((quest) => quest.id === id);
  }

  function regionFor(id) {
    return data.regions.find((region) => region.id === id);
  }

  function stateBadge(state) {
    const label = stateLabels[state] || titleCase(state);
    return `<span class="state-badge state-${escapeHtml(state)}">${escapeHtml(label)}</span>`;
  }

  function tags(values) {
    return `<div class="tag-list">${values.map((tag) => `<span class="tag">${escapeHtml(tag)}</span>`).join("")}</div>`;
  }

  function progressSegments(region) {
    const segments = [];
    const counts = [
      ["verified", region.verified],
      ["active", region.active],
      ["available", region.available],
      ["locked", region.locked]
    ];
    counts.forEach(([state, count]) => {
      for (let i = 0; i < count; i += 1) segments.push(`<span class="${state}"></span>`);
    });
    const limited = segments.slice(0, 16);
    while (limited.length < 16) limited.push("<span></span>");
    return limited.join("");
  }

  function questCard(quest, options = {}) {
    const region = regionFor(quest.region);
    return `
      <article class="card quest-card ${options.recommended ? "recommended-card" : ""}">
        <div class="card-topline">
          <span class="card-kicker">${escapeHtml(region?.shortTitle || quest.region)}</span>
          ${stateBadge(quest.state)}
        </div>
        <h3><a href="#quest/${escapeHtml(quest.id)}">${escapeHtml(quest.title)}</a></h3>
        <p>${escapeHtml(quest.summary)}</p>
        ${tags(quest.tags.slice(0, 3))}
        <div class="card-footer">
          <span>${escapeHtml(quest.level)} · ${quest.xp} XP</span>
          <span>${quest.minutes} min</span>
        </div>
      </article>`;
  }

  function regionCard(region) {
    return `
      <article class="card region-card accent-${escapeHtml(region.accent)}">
        <div class="card-topline">
          <span class="card-kicker">Region ${String(region.order / 10).padStart(2, "0")}</span>
          <span class="tag">${region.total} quests</span>
        </div>
        <h3><a href="#region/${escapeHtml(region.id)}">${escapeHtml(region.title)}</a></h3>
        <p>${escapeHtml(region.summary)}</p>
        <div class="region-counts">
          <span>${region.verified} verified</span>
          <span>${region.active} active</span>
          <span>${region.available} available</span>
        </div>
        <div class="region-progress" aria-label="${region.verified} verified, ${region.active} active, ${region.available} available, ${region.locked} locked">
          ${progressSegments(region)}
        </div>
      </article>`;
  }

  function pageHeading(eyebrow, title, description, actions = "") {
    return `
      <header class="page-heading">
        <div>
          <div class="eyebrow">${escapeHtml(eyebrow)}</div>
          <h1>${escapeHtml(title)}</h1>
          <p>${escapeHtml(description)}</p>
        </div>
        ${actions ? `<div class="button-row">${actions}</div>` : ""}
      </header>`;
  }

  function renderHome() {
    const recommended = questFor(data.recommendation.questId);
    const recommendedRegion = regionFor(recommended.region);
    const percent = Math.round((data.participant.verifiedXp / data.participant.availableXp) * 100);
    const available = data.quests.filter((quest) => ["available", "in_progress", "needs_changes"].includes(quest.state) && quest.id !== recommended.id).slice(0, 3);

    return `
      ${pageHeading(
        "Your field guide",
        `Welcome back, ${data.participant.name.split(" ")[0]}.`,
        "Continue the thread from human intent to evidence-backed delivery."
      )}

      <section class="hero-grid" aria-label="Recommended work and progress">
        <article class="panel recommendation-panel">
          <div class="eyebrow">Recommended next · ${escapeHtml(recommendedRegion.title)}</div>
          ${stateBadge(recommended.state)}
          <h2>${escapeHtml(recommended.title)}</h2>
          <p>${escapeHtml(recommended.summary)}</p>
          <ul class="recommendation-reasons">
            ${data.recommendation.reasons.map((reason) => `<li>${escapeHtml(reason)}</li>`).join("")}
          </ul>
          <div class="button-row">
            <a class="button button-primary" href="#quest/${escapeHtml(recommended.id)}">Continue quest</a>
            <a class="button button-quiet" href="#catalog">View alternatives</a>
          </div>
        </article>

        <aside class="panel metric-panel" aria-label="Journey progress">
          <div class="eyebrow">Journey progress</div>
          <div class="metric-stack">
            <div class="two-metrics">
              <div class="metric">
                <span>Verified XP</span>
                <strong class="verified-number">${data.participant.verifiedXp}</strong>
                <small>Reviewer approved</small>
              </div>
              <div class="metric">
                <span>Claimed XP</span>
                <strong>${data.participant.claimedXp}</strong>
                <small>Includes work in progress</small>
              </div>
            </div>
            <div class="metric">
              <span>Foundation track</span>
              <strong>${percent}%</strong>
              <div class="progress-track" aria-label="${percent}% verified"><span style="width:${percent}%"></span></div>
              <small>${data.participant.verifiedQuests} verified · ${data.participant.completedQuests} completed or submitted</small>
            </div>
          </div>
        </aside>
      </section>

      <div class="section-heading">
        <div><div class="eyebrow">Ready when you are</div><h2>Available quests</h2></div>
        <a class="quiet-link" href="#catalog">Browse all quests</a>
      </div>
      <section class="card-grid" aria-label="Available quests">
        ${available.map((quest) => questCard(quest)).join("")}
      </section>

      <div class="section-heading">
        <div><div class="eyebrow">Across the journey</div><h2>Active regions</h2></div>
        <a class="quiet-link" href="#map">Open quest map</a>
      </div>
      <section class="card-grid four" aria-label="Active regions">
        ${data.regions.filter((region) => region.active || region.verified || region.available).slice(0, 4).map(regionCard).join("")}
      </section>

      <div class="section-heading">
        <div><div class="eyebrow">Audit trail</div><h2>Recent activity</h2></div>
      </div>
      <section class="panel card" aria-label="Recent activity">
        <ul class="activity-list">
          ${data.activity.map((item) => `
            <li class="activity-item">
              <span class="activity-icon" aria-hidden="true">${iconFor[item.type] || "·"}</span>
              <a href="${escapeHtml(item.route)}">${escapeHtml(item.title)}</a>
              <time>${escapeHtml(item.time)}</time>
            </li>`).join("")}
        </ul>
      </section>`;
  }

  function renderMap() {
    const total = data.regions.reduce((sum, region) => sum + region.total, 0);
    const verified = data.regions.reduce((sum, region) => sum + region.verified, 0);
    const active = data.regions.reduce((sum, region) => sum + region.active, 0);

    return `
      <div class="map-header">
        ${pageHeading("The complete route", "Quest Map", "Explore the regions of AI Context Engineering. Progress is self-paced; verified mastery depends on evidence and review.")}
        <div class="legend" aria-label="Quest status legend">
          ${stateBadge("verified")}${stateBadge("in_progress")}${stateBadge("available")}${stateBadge("locked")}
        </div>
      </div>
      <section class="map-intro" aria-label="Journey statistics">
        <div class="panel map-stat"><strong>${data.regions.length}</strong><span>curriculum regions</span></div>
        <div class="panel map-stat"><strong>${total}</strong><span>planned quests</span></div>
        <div class="panel map-stat"><strong>${verified} / ${active}</strong><span>verified / active</span></div>
      </section>
      <div class="notice notice-info"><strong>The map is not a race.</strong>Choose quests that extend your real capability. Verified progress values reproducible work, not completion speed.</div>
      <div class="section-heading"><div><div class="eyebrow">Regions</div><h2>Your route through the Golden Thread</h2></div></div>
      <section class="card-grid four" aria-label="Quest regions">
        ${data.regions.sort((a, b) => a.order - b.order).map(regionCard).join("")}
      </section>`;
  }

  function renderRegion(regionId) {
    const region = regionFor(regionId);
    if (!region) return renderNotFound("Region not found", "The requested region does not exist in the prototype fixture.");
    const quests = data.quests.filter((quest) => quest.region === region.id);
    return `
      ${pageHeading("Quest region", region.title, region.summary, `<a class="button button-secondary" href="#map">Back to map</a>`)}
      <section class="panel card" aria-labelledby="region-outcomes-heading">
        <div class="eyebrow">Region outcomes</div>
        <h2 id="region-outcomes-heading">What you will demonstrate</h2>
        <ul class="outcome-list">${region.outcomes.map((outcome) => `<li>${escapeHtml(outcome)}</li>`).join("")}</ul>
        <div class="region-counts">
          <span>${region.verified} verified</span><span>${region.active} active</span><span>${region.available} available</span><span>${region.locked} locked</span>
        </div>
      </section>
      <div class="section-heading"><div><div class="eyebrow">Region catalog</div><h2>${quests.length ? `${quests.length} prototype quests` : "Content planned"}</h2></div></div>
      ${quests.length
        ? `<section class="card-grid">${quests.map((quest) => questCard(quest)).join("")}</section>`
        : `<div class="panel card"><h3>Quest files have not been authored for this region yet.</h3><p>The curriculum backlog defines the planned content. Adding valid quest files will populate this page without UI changes.</p><a class="button button-secondary" href="#catalog">Browse authored prototype quests</a></div>`}`;
  }

  function catalogControls() {
    const regionOptions = data.regions.map((region) => `<option value="${escapeHtml(region.id)}">${escapeHtml(region.title)}</option>`).join("");
    const states = [...new Set(data.quests.map((quest) => quest.state))];
    return `
      <form class="panel filter-bar" id="catalog-filters">
        <div class="field">
          <label for="quest-search">Search quests</label>
          <input id="quest-search" type="search" placeholder="Title, outcome, tag, or tool">
        </div>
        <div class="field">
          <label for="region-filter">Region</label>
          <select id="region-filter"><option value="">All regions</option>${regionOptions}</select>
        </div>
        <div class="field">
          <label for="state-filter">State</label>
          <select id="state-filter"><option value="">All states</option>${states.map((state) => `<option value="${state}">${stateLabels[state]}</option>`).join("")}</select>
        </div>
        <div class="field">
          <label for="level-filter">Level</label>
          <select id="level-filter"><option value="">All levels</option>${["Scout", "Explorer", "Builder", "Navigator", "Boss"].map((level) => `<option>${level}</option>`).join("")}</select>
        </div>
      </form>`;
  }

  function renderCatalog() {
    return `
      ${pageHeading("Find your next challenge", "Quest Catalog", "Filter by region, readiness, difficulty, tool, risk, or capability. The content model—not the interface—defines the catalog.")}
      ${catalogControls()}
      <div class="result-summary"><span id="catalog-count">${data.quests.length} quests</span><button class="button button-secondary" id="reset-filters" type="button">Reset filters</button></div>
      <section class="card-grid" id="catalog-results" aria-live="polite" aria-label="Quest catalog results">
        ${data.quests.map((quest) => questCard(quest)).join("")}
      </section>`;
  }

  function renderQuest(questId) {
    const quest = questFor(questId);
    if (!quest) return renderNotFound("Quest not found", "The requested quest does not exist in the prototype fixture.");
    const region = regionFor(quest.region);
    const prereqs = quest.prerequisites.map(questFor).filter(Boolean);
    const locked = quest.state === "locked";
    const action = locked
      ? `<button class="button button-secondary" disabled>Prerequisites required</button>`
      : quest.state === "verified"
        ? `<a class="button button-secondary" href="#passport">View verified record</a>`
        : quest.state === "evidence_ready" || quest.state === "needs_changes"
          ? `<a class="button button-primary" href="#evidence">Open evidence workspace</a>`
          : `<button class="button button-primary" type="button" data-demo-action="start-quest">${quest.state === "in_progress" ? "Continue quest" : "Start quest"}</button>`;

    return `
      ${pageHeading(region.title, quest.title, quest.summary, `<a class="button button-secondary" href="#region/${region.id}">View region</a>`)}
      ${locked ? `<div class="notice notice-warning"><strong>This quest is locked.</strong>Complete every prerequisite below before starting. You may still review the requirements.</div>` : ""}
      ${quest.state === "needs_changes" ? `<div class="notice notice-warning"><strong>Reviewer requested changes.</strong>The evidence and findings remain available. Correct the work, rerun validation, and resubmit the same attempt.</div>` : ""}
      <div class="workbench">
        <article class="panel document">
          <section>
            <div class="eyebrow">Mission</div>
            <h2>The capability you will demonstrate</h2>
            <p>${escapeHtml(quest.mission)}</p>
          </section>
          <section>
            <div class="eyebrow">Scenario</div>
            <h2>Why this matters</h2>
            <p>${escapeHtml(quest.scenario)}</p>
          </section>
          <section>
            <div class="eyebrow">Outcomes</div>
            <h2>What you will be able to do</h2>
            <ul class="outcome-list">${quest.outcomes.map((outcome) => `<li>${escapeHtml(outcome)}</li>`).join("")}</ul>
          </section>
          <section>
            <div class="eyebrow">Acceptance criteria</div>
            <h2>How the work will be evaluated</h2>
            <ol class="criteria-list">${quest.criteria.map((criterion) => `<li>${escapeHtml(criterion)}</li>`).join("")}</ol>
          </section>
          <section>
            <div class="eyebrow">Safety constraints</div>
            <h2>Keep the work controlled</h2>
            <ul class="safety-list">${quest.safety.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
          </section>
        </article>
        <aside class="context-rail" aria-label="Quest context and actions">
          <section class="panel">
            <div class="card-topline"><span class="card-kicker">Current state</span>${stateBadge(quest.state)}</div>
            <dl class="detail-list">
              <dt>Quest version</dt><dd>${quest.version}</dd>
              <dt>Level</dt><dd>${escapeHtml(quest.level)}</dd>
              <dt>Experience</dt><dd>${quest.xp} XP</dd>
              <dt>Estimate</dt><dd>${quest.minutes} minutes</dd>
              <dt>Bookend</dt><dd>${escapeHtml(titleCase(quest.bookend))}</dd>
              <dt>External write</dt><dd>${quest.externalWrite ? "Yes — confirmation" : "No"}</dd>
            </dl>
            <div class="button-row">${action}</div>
          </section>
          <section class="panel">
            <div class="eyebrow">Prerequisites</div>
            ${prereqs.length
              ? `<ul class="activity-list">${prereqs.map((item) => `<li class="activity-item"><span class="activity-icon">${item.state === "verified" ? "✓" : "·"}</span><a href="#quest/${item.id}">${escapeHtml(item.title)}</a>${stateBadge(item.state)}</li>`).join("")}</ul>`
              : `<p class="notice notice-success"><strong>Ready from the start.</strong>This quest has no prerequisites.</p>`}
          </section>
          <section class="panel">
            <div class="eyebrow">Tags</div>
            ${tags(quest.tags)}
          </section>
        </aside>
      </div>`;
  }

  function renderEvidence() {
    const quest = questFor(data.evidence.questId);
    const evidence = data.evidence;
    const completion = Math.round((evidence.proof.filter((item) => item.status !== "missing").length / evidence.proof.length) * 100);
    return `
      ${pageHeading("Attempt evidence", "Evidence Workspace", `Assemble reproducible proof for “${quest.title}.”`, `<a class="button button-secondary" href="#quest/${quest.id}">View quest</a>`)}
      <section class="evidence-summary" aria-label="Evidence summary">
        <div class="panel summary-tile"><span>Attempt</span><strong>${escapeHtml(evidence.attemptId)}</strong></div>
        <div class="panel summary-tile"><span>Evidence detected</span><strong>${completion}%</strong></div>
        <div class="panel summary-tile"><span>Latest validation</span><strong>${titleCase(evidence.validation.outcome)}</strong></div>
        <div class="panel summary-tile"><span>Git branch</span><strong>${escapeHtml(evidence.git.branch)}</strong></div>
      </section>
      <div class="notice notice-warning"><strong>One validator advisory remains.</strong>Required checks passed, but the removed-item report cannot yet distinguish deletion from lost permission. A reviewer will see this warning.</div>
      <div class="workbench">
        <div>
          <section class="panel card">
            <div class="section-heading"><div><div class="eyebrow">Required proof</div><h2>Evidence checklist</h2></div><span class="tag">${evidence.proof.length} requirements</span></div>
            <ul class="proof-list">
              ${evidence.proof.map((item) => `
                <li class="proof-item">
                  <span class="status-icon ${item.status}" aria-hidden="true">${iconFor[item.status] || "·"}</span>
                  <div><h3>${escapeHtml(item.title)}</h3><p>${escapeHtml(item.description)}</p><code class="path">${escapeHtml(item.path)}</code></div>
                  ${stateBadge(item.status)}
                </li>`).join("")}
            </ul>
          </section>

          <section class="panel validation-panel" style="margin-top:.8rem">
            <div class="validation-header">
              <div><div class="eyebrow">Registered validator</div><h2>Jira synchronization quality</h2><p>Run ${escapeHtml(evidence.validation.runId)} · ${escapeHtml(evidence.validation.duration)}</p></div>
              ${stateBadge(evidence.validation.outcome)}
            </div>
            <ul class="finding-list">
              ${evidence.validation.findings.map((finding) => `
                <li class="finding">
                  <span class="status-icon ${finding.outcome}" aria-hidden="true">${iconFor[finding.outcome] || "·"}</span>
                  <div><h3>${escapeHtml(finding.title)}</h3><p>${escapeHtml(finding.detail)}</p><div class="finding-meta"><span class="severity">${escapeHtml(finding.severity)}</span></div></div>
                </li>`).join("")}
            </ul>
            <div class="button-row" style="margin-top:1rem">
              <button class="button button-secondary" type="button" data-demo-action="run-validator">Run validation again</button>
              <button class="button button-secondary" type="button" data-demo-action="open-result">View structured result</button>
            </div>
          </section>
        </div>
        <aside class="context-rail">
          <section class="panel">
            <div class="eyebrow">Git status</div>
            <h2>Review before submission</h2>
            <dl class="detail-list">
              <dt>Branch</dt><dd>${escapeHtml(evidence.git.branch)}</dd>
              <dt>Changed</dt><dd>${evidence.git.changed} files</dd>
              <dt>Untracked</dt><dd>${evidence.git.untracked} file</dd>
              <dt>Ahead of origin</dt><dd>${evidence.git.ahead} commits</dd>
            </dl>
            <div class="notice notice-info"><strong>The prototype will not commit or push.</strong>Production UI reports status and provides safe instructions.</div>
          </section>
          <section class="panel">
            <div class="eyebrow">Submission readiness</div>
            <h2>Evidence ready</h2>
            <p style="color:var(--ink-600);font-size:.76rem">Artifacts are present and required checks passed. The warning will remain visible to the reviewer.</p>
            <div class="button-row">
              <button class="button button-primary" type="button" data-demo-action="submit-review">Prepare submission</button>
            </div>
          </section>
        </aside>
      </div>`;
  }

  function renderPassport() {
    return `
      ${pageHeading("Professional evidence", "Quest Passport", "A portfolio of capabilities demonstrated through artifacts, validation, and review—not merely boxes checked.")}
      <section class="panel passport-header">
        <div class="passport-avatar" aria-hidden="true">${escapeHtml(data.participant.initials)}</div>
        <div><div class="eyebrow">${escapeHtml(data.participant.track)}</div><h2>${escapeHtml(data.participant.name)}</h2><p>${escapeHtml(data.participant.role)}</p></div>
        <div class="xp-pair">
          <div class="xp-box"><strong>${data.participant.verifiedXp}</strong><span>Verified XP</span></div>
          <div class="xp-box"><strong>${data.participant.claimedXp}</strong><span>Claimed XP</span></div>
        </div>
      </section>

      <div class="section-heading"><div><div class="eyebrow">Recognition</div><h2>Badges</h2></div><p>Authority is shown for every award.</p></div>
      <section class="badge-grid" aria-label="Badges">
        ${data.badges.map((badge, index) => `
          <article class="panel badge-tile state-${escapeHtml(badge.state)}">
            <div class="badge-icon" aria-hidden="true">${badge.state === "earned" ? "✦" : index + 1}</div>
            <h3>${escapeHtml(badge.title)}</h3>
            <p>${escapeHtml(badge.description)}</p>
            <span class="badge-authority">${escapeHtml(badge.authority)} · ${escapeHtml(titleCase(badge.state))}</span>
          </article>`).join("")}
      </section>

      <div class="section-heading"><div><div class="eyebrow">Capability breadth</div><h2>Region evidence</h2></div></div>
      <section class="panel card">
        <table class="capability-table">
          <thead><tr><th>Region</th><th>Verified</th><th>Active</th><th>Available</th><th>Next signal</th></tr></thead>
          <tbody>
            ${data.regions.map((region) => `
              <tr>
                <td data-label="Region"><a href="#region/${region.id}">${escapeHtml(region.title)}</a></td>
                <td data-label="Verified">${region.verified}</td>
                <td data-label="Active">${region.active}</td>
                <td data-label="Available">${region.available}</td>
                <td data-label="Next signal">${region.active ? "Continue current evidence" : region.available ? "Quest available" : "Prerequisites remain"}</td>
              </tr>`).join("")}
          </tbody>
        </table>
      </section>

      <div class="section-heading"><div><div class="eyebrow">Public sharing</div><h2>Sanitized progress preview</h2></div></div>
      <section class="panel card">
        <div class="notice notice-info"><strong>Opt-in and minimized.</strong>This preview contains IDs, verified counts, XP, badges, and curriculum version—never evidence paths or private work content.</div>
        <pre class="code-preview">{
  "participant_handle": "alex-rivera",
  "verified_xp": ${data.participant.verifiedXp},
  "verified_quests": ${data.participant.verifiedQuests},
  "badges": ["context-scout"],
  "curriculum": "golden-thread-foundations@1"
}</pre>
      </section>`;
  }

  function renderHealth() {
    const failures = data.health.filter((item) => item.status === "fail").length;
    const warnings = data.health.filter((item) => item.status === "warning").length;
    return `
      ${pageHeading("Local readiness", "Environment Health", "Check the repository, runtime, service, and quest-specific tools without exposing credential values.", `<button class="button button-secondary" type="button" data-demo-action="refresh-health">Refresh checks</button>`)}
      <div class="notice ${failures ? "notice-warning" : "notice-success"}"><strong>${failures ? `${failures} quest-specific requirement needs attention.` : "Required foundation checks passed."}</strong>${warnings} warning${warnings === 1 ? "" : "s"} remain. A warning may not block unrelated quests.</div>
      <div class="section-heading"><div><div class="eyebrow">Current machine</div><h2>Readiness checks</h2></div></div>
      <section class="panel card">
        <ul class="health-list">
          ${data.health.map((item) => `
            <li class="health-item">
              <span class="status-icon ${item.status}" aria-hidden="true">${iconFor[item.status] || "·"}</span>
              <div><h3>${escapeHtml(item.name)}</h3><p>${escapeHtml(item.importance)}${item.remediation ? ` · ${escapeHtml(item.remediation)}` : ""}</p></div>
              <div class="health-value">${escapeHtml(item.value)}</div>
            </li>`).join("")}
        </ul>
      </section>
      <div class="section-heading"><div><div class="eyebrow">Safety boundary</div><h2>What health checks never display</h2></div></div>
      <section class="card-grid">
        <article class="card"><h3>Credential values</h3><p>Authentication presence and expiration may be reported; tokens, cookies, and secrets never are.</p></article>
        <article class="card"><h3>Unapproved paths</h3><p>The service reports only registered repository and participant locations.</p></article>
        <article class="card"><h3>Hidden external writes</h3><p>A health check may verify read access but cannot create or modify remote work.</p></article>
      </section>`;
  }

  function renderReview() {
    const review = data.review;
    const quest = questFor(review.questId);
    return `
      ${pageHeading("Reviewer workbench", "Review Submitted Evidence", `Evaluate whether ${review.participant}'s work demonstrates “${quest.title}.”`, `<a class="button button-secondary" href="#quest/${quest.id}">View quest definition</a>`)}
      <div class="notice notice-warning"><strong>This attempt needs changes.</strong>Evidence has not changed since the review. Findings remain open and no verified XP has been awarded.</div>
      <div class="review-grid">
        <div>
          <section class="panel review-section">
            <div class="section-heading"><div><div class="eyebrow">Submission identity</div><h2>${escapeHtml(quest.title)}</h2></div>${stateBadge(review.state)}</div>
            <dl class="detail-list">
              <dt>Participant</dt><dd>${escapeHtml(review.participant)}</dd>
              <dt>Attempt</dt><dd>${escapeHtml(review.attemptId)}</dd>
              <dt>Quest version</dt><dd>${quest.version}</dd>
              <dt>Submitted</dt><dd>${escapeHtml(review.submitted)}</dd>
              <dt>Evidence hash</dt><dd>${escapeHtml(titleCase(review.evidenceHashState))}</dd>
              <dt>Validation</dt><dd>${escapeHtml(titleCase(review.validationOutcome))}</dd>
            </dl>
          </section>
          <section class="panel review-section">
            <div class="eyebrow">Submitted artifacts</div><h2>Evidence package</h2>
            <ul class="artifact-list">
              ${review.artifacts.map((artifact) => `
                <li class="artifact-item">
                  <span class="status-icon ${artifact.status}" aria-hidden="true">${iconFor[artifact.status] || "✓"}</span>
                  <div><h3>${escapeHtml(artifact.title)}</h3><code class="path">${escapeHtml(artifact.path)}</code></div>
                  ${stateBadge(artifact.status === "present" ? "present" : "missing")}
                </li>`).join("")}
            </ul>
          </section>
          <section class="panel review-section">
            <div class="eyebrow">Open findings</div><h2>Required changes</h2>
            <ul class="finding-list">
              ${review.findings.map((finding) => `
                <li class="finding">
                  <span class="status-icon warning" aria-hidden="true">!</span>
                  <div><h3>${escapeHtml(finding.title)}</h3><p>${escapeHtml(finding.detail)}</p><div class="notice notice-warning" style="margin-top:.6rem"><strong>Required change</strong>${escapeHtml(finding.required)}</div><div class="finding-meta"><span class="severity">${escapeHtml(finding.severity)}</span></div></div>
                </li>`).join("")}
            </ul>
          </section>
        </div>
        <aside class="panel decision-panel" aria-labelledby="decision-heading">
          <div class="eyebrow">Review authority</div>
          <h2 id="decision-heading">Record a decision</h2>
          <p style="color:var(--ink-600);font-size:.75rem">This prototype demonstrates safeguards. It does not save a decision.</p>
          <fieldset style="border:0;padding:0;margin:0">
            <legend class="sr-only">Review decision</legend>
            <div class="radio-group">
              <label class="radio-card"><input type="radio" name="decision" value="approved"><span><strong>Approve</strong><span>Outcomes are demonstrated. Verification statement required.</span></span></label>
              <label class="radio-card"><input type="radio" name="decision" value="needs_changes" checked><span><strong>Needs changes</strong><span>Participant can correct and resubmit this attempt.</span></span></label>
              <label class="radio-card"><input type="radio" name="decision" value="rejected"><span><strong>Reject</strong><span>Evidence is not credible or is outside the quest.</span></span></label>
            </div>
          </fieldset>
          <div class="field">
            <label for="review-statement">Decision statement</label>
            <textarea id="review-statement">The assertion must validate the submitted account and amount before this quest can be verified.</textarea>
          </div>
          <div class="notice notice-info" style="margin:.8rem 0"><strong>Authority boundary</strong>A validator may support this decision but cannot approve the quest.</div>
          <button class="button button-primary" type="button" data-demo-action="record-review">Preview review record</button>
        </aside>
      </div>`;
  }

  function renderNotFound(title, message) {
    return `${pageHeading("Prototype route", title, message)}<a class="button button-primary" href="#home">Return home</a>`;
  }

  function parseRoute() {
    const raw = (window.location.hash || "#home").slice(1);
    const [name, id] = raw.split("/");
    return { name: name || "home", id };
  }

  function setCurrentNav(routeName) {
    const primary = routeName === "region" ? "map" : routeName === "quest" ? "catalog" : routeName;
    document.querySelectorAll("[data-route]").forEach((link) => {
      if (link.dataset.route === primary) link.setAttribute("aria-current", "page");
      else link.removeAttribute("aria-current");
    });
  }

  function render() {
    const route = parseRoute();
    let markup;
    let crumb;
    switch (route.name) {
      case "home": markup = renderHome(); crumb = "Journey / Home"; break;
      case "map": markup = renderMap(); crumb = "Journey / Quest Map"; break;
      case "region": {
        const region = regionFor(route.id);
        markup = renderRegion(route.id);
        crumb = `Journey / Quest Map / ${region?.title || "Region"}`;
        break;
      }
      case "catalog": markup = renderCatalog(); crumb = "Journey / Catalog"; break;
      case "quest": {
        const quest = questFor(route.id);
        markup = renderQuest(route.id);
        crumb = `Journey / Catalog / ${quest?.title || "Quest"}`;
        break;
      }
      case "evidence": markup = renderEvidence(); crumb = "Journey / Evidence"; break;
      case "passport": markup = renderPassport(); crumb = "Journey / Passport"; break;
      case "health": markup = renderHealth(); crumb = "Journey / Environment"; break;
      case "review": markup = renderReview(); crumb = "Journey / Reviewer"; break;
      default: markup = renderNotFound("Page not found", "The requested prototype page does not exist."); crumb = "Journey / Not found";
    }
    main.innerHTML = markup;
    breadcrumb.textContent = crumb;
    setCurrentNav(route.name);
    bindScreenEvents(route.name);
    closeMenu(false);
    window.scrollTo(0, 0);
    main.focus({ preventScroll: true });
  }

  function bindCatalogFilters() {
    const search = document.querySelector("#quest-search");
    const region = document.querySelector("#region-filter");
    const state = document.querySelector("#state-filter");
    const level = document.querySelector("#level-filter");
    const results = document.querySelector("#catalog-results");
    const count = document.querySelector("#catalog-count");
    const reset = document.querySelector("#reset-filters");
    if (!search || !results) return;

    const update = () => {
      const term = search.value.trim().toLowerCase();
      const filtered = data.quests.filter((quest) => {
        const haystack = [quest.title, quest.summary, quest.mission, quest.region, quest.level, ...quest.tags, ...quest.outcomes].join(" ").toLowerCase();
        return (!term || haystack.includes(term))
          && (!region.value || quest.region === region.value)
          && (!state.value || quest.state === state.value)
          && (!level.value || quest.level === level.value);
      });
      count.textContent = `${filtered.length} quest${filtered.length === 1 ? "" : "s"}`;
      results.innerHTML = filtered.length
        ? filtered.map((quest) => questCard(quest)).join("")
        : `<div class="panel card" style="grid-column:1/-1"><h3>No quests match these filters.</h3><p>Clear one or more filters or reset the catalog.</p></div>`;
    };
    [search, region, state, level].forEach((control) => control.addEventListener("input", update));
    reset.addEventListener("click", () => {
      search.value = "";
      region.value = "";
      state.value = "";
      level.value = "";
      update();
      search.focus();
    });
  }

  function demoAction(action) {
    const messages = {
      "start-quest": "Prototype: production would persist a new attempt, record an audit event, and rebuild the affected pages.",
      "run-validator": "Prototype: production would run only the registered validator under its path, time, environment, and output limits.",
      "open-result": "The structured result is represented below; production would link to the saved JSON record.",
      "submit-review": "Prototype: production would run readiness and secret checks, then prepare a review record without pushing automatically.",
      "refresh-health": "Prototype checks refreshed. No credential values or external writes are involved.",
      "record-review": "Prototype: a production decision would validate reviewer fields, evidence hash, and authority before writing the review record."
    };
    showToast(messages[action] || "Prototype action demonstrated.");
  }

  function bindScreenEvents(routeName) {
    if (routeName === "catalog") bindCatalogFilters();
    document.querySelectorAll("[data-demo-action]").forEach((button) => {
      button.addEventListener("click", () => demoAction(button.dataset.demoAction));
    });
  }

  function showToast(message) {
    const toast = document.createElement("div");
    toast.className = "toast";
    toast.textContent = message;
    toastRegion.append(toast);
    window.setTimeout(() => toast.remove(), 5200);
  }

  function openMenu() {
    nav.classList.add("is-open");
    scrim.hidden = false;
    menuButton.setAttribute("aria-expanded", "true");
    const firstLink = nav.querySelector("a");
    if (firstLink) firstLink.focus();
  }

  function closeMenu(returnFocus = true) {
    if (!nav.classList.contains("is-open")) return;
    nav.classList.remove("is-open");
    scrim.hidden = true;
    menuButton.setAttribute("aria-expanded", "false");
    if (returnFocus) menuButton.focus();
  }

  function initializeShell() {
    document.querySelector("#nav-user-name").textContent = data.participant.name;
    document.querySelector("#nav-user-role").textContent = data.participant.role;
    document.querySelector("#nav-avatar").textContent = data.participant.initials;
    document.querySelector("#nav-verified-xp").textContent = `${data.participant.verifiedXp} XP`;
    const percent = Math.round((data.participant.verifiedXp / data.participant.availableXp) * 100);
    document.querySelector("#nav-progress-percent").textContent = `${percent}%`;
    document.querySelector("#nav-progress-bar").style.width = `${percent}%`;
    document.querySelector("#build-label").textContent = data.site.buildLabel;
  }

  menuButton.addEventListener("click", () => {
    if (nav.classList.contains("is-open")) closeMenu();
    else openMenu();
  });
  scrim.addEventListener("click", () => closeMenu());
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && nav.classList.contains("is-open")) closeMenu();
  });
  window.addEventListener("hashchange", render);
  window.addEventListener("resize", () => {
    if (window.innerWidth > 860) closeMenu(false);
  });

  initializeShell();
  render();
})();
