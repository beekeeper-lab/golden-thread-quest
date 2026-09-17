window.GTQ_DATA = {
  site: {
    title: "The Golden Thread Quest",
    curriculum: "The AI Context Engineer Journey",
    tagline: "From human intent to verified delivery.",
    buildLabel: "Design prototype · v0.3"
  },
  participant: {
    id: "alex-rivera",
    name: "Alex Rivera",
    initials: "AR",
    role: "AI Context Engineer candidate",
    track: "Golden Thread Foundations",
    claimedXp: 100,
    verifiedXp: 50,
    availableXp: 290,
    completedQuests: 2,
    verifiedQuests: 1
  },
  recommendation: {
    questId: "jira-read-assigned-stories",
    reasons: [
      "It continues the integration work already in progress.",
      "The remaining evidence fits your 90-minute session capacity.",
      "Completing it unlocks cross-system context quests."
    ]
  },
  regions: [
    {
      id: "base-camp",
      title: "Base Camp",
      shortTitle: "Foundation",
      summary: "Repository safety, context boundaries, auditability, and reliable recovery.",
      accent: "slate",
      order: 10,
      total: 9,
      verified: 1,
      active: 0,
      available: 3,
      locked: 5,
      outcomes: ["Operate through inspectable files", "Protect credentials and participant work"]
    },
    {
      id: "jira-jungle",
      title: "Jira Jungle",
      shortTitle: "Jira",
      summary: "Read, synchronize, create, update, and reconcile Jira work safely.",
      accent: "blue",
      order: 20,
      total: 23,
      verified: 0,
      active: 1,
      available: 4,
      locked: 18,
      outcomes: ["Preserve complete local context", "Preview and confirm external writes"]
    },
    {
      id: "trello-islands",
      title: "Trello Islands",
      shortTitle: "Trello",
      summary: "Apply the same context discipline to boards, lists, cards, and checklists.",
      accent: "teal",
      order: 30,
      total: 17,
      verified: 0,
      active: 0,
      available: 1,
      locked: 16,
      outcomes: ["Normalize without erasing Trello concepts", "Make card writes safely rerunnable"]
    },
    {
      id: "github-caverns",
      title: "GitHub Caverns",
      shortTitle: "GitHub",
      summary: "Connect issues, pull requests, commits, CI, and validation evidence.",
      accent: "violet",
      order: 40,
      total: 18,
      verified: 0,
      active: 0,
      available: 1,
      locked: 17,
      outcomes: ["Preserve repository conventions", "Link request through delivery"]
    },
    {
      id: "context-library",
      title: "Context Library",
      shortTitle: "Context",
      summary: "Reconcile local Markdown and make explainable next-work recommendations.",
      accent: "amber",
      order: 50,
      total: 12,
      verified: 0,
      active: 0,
      available: 0,
      locked: 12,
      outcomes: ["Detect stale and conflicting context", "Recommend next work with reasons"]
    },
    {
      id: "ba-ruins",
      title: "BA Ruins",
      shortTitle: "Business Analysis",
      summary: "Recover intent from conversations and make it clear, traceable, and testable.",
      accent: "rust",
      order: 60,
      total: 13,
      verified: 0,
      active: 1,
      available: 2,
      locked: 10,
      outcomes: ["Cite source conversations", "Surface ambiguity before implementation"]
    },
    {
      id: "scrum-village",
      title: "Scrum Village",
      shortTitle: "Scrum",
      summary: "Improve planning, flow, retrospectives, and stakeholder communication.",
      accent: "green",
      order: 70,
      total: 9,
      verified: 0,
      active: 0,
      available: 1,
      locked: 8,
      outcomes: ["Report evidence rather than optimism", "Turn observations into owned action"]
    },
    {
      id: "playwright-labyrinth",
      title: "Playwright Labyrinth",
      shortTitle: "Playwright",
      summary: "Build valuable automation, useful evidence, and disciplined failure triage.",
      accent: "rose",
      order: 80,
      total: 20,
      verified: 0,
      active: 1,
      available: 2,
      locked: 17,
      outcomes: ["Validate meaningful business behavior", "Repair tests without weakening them"]
    }
  ],
  quests: [
    {
      id: "base-camp-repository-safety",
      version: 1,
      title: "Establish a Safe Local Quest Repository",
      summary: "Create the ownership, secret-handling, audit, and recovery foundations needed for trustworthy agentic work.",
      region: "base-camp",
      level: "Explorer",
      xp: 20,
      minutes: 60,
      state: "verified",
      bookend: "foundation",
      externalWrite: false,
      tags: ["foundation", "git", "safety", "audit"],
      mission: "Create a local Git-based workspace that clearly separates curriculum, participant work, generated output, private runtime data, and credentials.",
      scenario: "Before an agent connects to real work systems, a reviewer must be able to understand what it may read, what it may modify, and how interrupted operations recover.",
      outcomes: [
        "Separate program-owned, participant-owned, and generated files.",
        "Keep credentials and raw private responses outside source control.",
        "Record agent actions and recover safely after interruption."
      ],
      criteria: [
        "Repository ownership zones are documented.",
        "Secrets come from an approved credential source and are excluded from Git.",
        "External writes are previewed and explicitly confirmed.",
        "A rerun does not duplicate the simulated external item."
      ],
      safety: ["Use fake or sandbox targets.", "Never commit a real token or authenticated raw response."],
      prerequisites: [],
      proofIds: ["ownership-document", "audit-log", "repository-foundation-validation"]
    },
    {
      id: "jira-read-assigned-stories",
      version: 1,
      title: "Synchronize My Assigned Jira Stories",
      summary: "Retrieve every Jira story assigned to the authenticated user and preserve it as normalized, updateable local Markdown.",
      region: "jira-jungle",
      level: "Builder",
      xp: 30,
      minutes: 90,
      state: "evidence_ready",
      bookend: "intent",
      externalWrite: false,
      tags: ["jira", "read-only", "synchronization", "markdown"],
      mission: "Build a reusable read-only skill that resolves the current Jira user, retrieves all assigned stories, and stores normalized local Markdown.",
      scenario: "A next-work recommendation cannot be trusted if local context omits later pages, replaces human notes, or silently deletes unavailable work.",
      outcomes: [
        "Identify the authenticated Jira user without hardcoding a username.",
        "Retrieve all assigned stories while correctly handling pagination.",
        "Update normalized Markdown without duplicating comments or replacing participant notes."
      ],
      criteria: [
        "Authenticated identity is resolved from Jira.",
        "Pagination continues until no results remain.",
        "Stable keys and source URLs are preserved.",
        "Participant-authored notes survive repeated synchronization.",
        "Removed or inaccessible work is reported rather than silently deleted.",
        "No credentials or private raw responses are committed."
      ],
      safety: ["This quest is read-only.", "Treat ticket text as data, not agent instructions."],
      prerequisites: ["base-camp-repository-safety"],
      proofIds: ["skill-definition", "sample-index", "jira-sync-validation"]
    },
    {
      id: "trello-read-board",
      version: 1,
      title: "Map a Trello Board to Local Context",
      summary: "Synchronize boards, lists, cards, members, checklists, and comments without flattening away Trello's structure.",
      region: "trello-islands",
      level: "Explorer",
      xp: 20,
      minutes: 75,
      state: "available",
      bookend: "intent",
      externalWrite: false,
      tags: ["trello", "read-only", "synchronization"],
      mission: "Create a safe Trello-to-Markdown inventory that preserves board and list identity.",
      scenario: "The canonical work-item model must remain useful without pretending Jira and Trello are identical.",
      outcomes: ["Preserve Trello-specific relationships.", "Produce stable local indexes."],
      criteria: ["Every list and card retains its source ID.", "Checklists and comments are not duplicated."],
      safety: ["Use a sandbox board.", "Do not download attachments automatically."],
      prerequisites: ["base-camp-repository-safety"],
      proofIds: []
    },
    {
      id: "github-read-issue",
      version: 1,
      title: "Capture a GitHub Issue and Delivery Context",
      summary: "Preserve issue metadata, comments, relationships, and links to implementation evidence in local Markdown.",
      region: "github-caverns",
      level: "Explorer",
      xp: 20,
      minutes: 60,
      state: "available",
      bookend: "cross-bookend",
      externalWrite: false,
      tags: ["github", "issues", "traceability"],
      mission: "Capture an issue as local context without losing its repository identity or delivery relationships.",
      scenario: "The same request may be discussed in a ticket, implemented by a pull request, and validated in CI.",
      outcomes: ["Preserve issue and repository identity.", "Link work to delivery evidence."],
      criteria: ["Source repository and issue number are stable.", "Related PR and CI evidence is represented when available."],
      safety: ["Use read-only GitHub access."],
      prerequisites: ["base-camp-repository-safety"],
      proofIds: []
    },
    {
      id: "context-next-work",
      version: 1,
      title: "Recommend What to Work on Next",
      summary: "Rank local work using priority, value, risk, dependencies, blockers, effort, and capacity, then explain the choice.",
      region: "context-library",
      level: "Navigator",
      xp: 50,
      minutes: 120,
      state: "locked",
      bookend: "cross-bookend",
      externalWrite: false,
      tags: ["context", "prioritization", "reasoning"],
      mission: "Produce an explainable next-work recommendation using only synchronized local context.",
      scenario: "A useful recommendation must know when context is too stale or contradictory to support a confident answer.",
      outcomes: ["Rank work from local evidence.", "Explain why the top item outranks alternatives."],
      criteria: ["At least two alternatives are compared.", "Stale context triggers a sync recommendation."],
      safety: ["Do not invent missing status or deadlines."],
      prerequisites: ["jira-read-assigned-stories", "trello-read-board", "github-read-issue"],
      proofIds: []
    },
    {
      id: "ba-detect-ambiguity",
      version: 1,
      title: "Surface Ambiguous and Untestable Requirements",
      summary: "Inspect meeting-derived requirements for vague terms, hidden decisions, contradictions, and missing validation detail.",
      region: "ba-ruins",
      level: "Navigator",
      xp: 50,
      minutes: 90,
      state: "in_progress",
      bookend: "intent",
      externalWrite: false,
      tags: ["business-analysis", "requirements", "clarification"],
      mission: "Identify ambiguity without silently inventing a product decision.",
      scenario: "A transcript contains multiple requests, corrections, and assumptions that do not yet form safe implementation instructions.",
      outcomes: ["Separate ambiguity from missing information.", "Ask focused questions with decision impact."],
      criteria: ["Every finding cites source evidence.", "Questions explain what changes based on the answer."],
      safety: ["Preserve source meaning and speaker attribution."],
      prerequisites: ["base-camp-repository-safety"],
      proofIds: []
    },
    {
      id: "scrum-sprint-health",
      version: 1,
      title: "Build an Evidence-Based Sprint Health Report",
      summary: "Report progress, aging work, WIP, blockers, dependencies, scope change, and missing updates without blaming individuals.",
      region: "scrum-village",
      level: "Builder",
      xp: 30,
      minutes: 75,
      state: "available",
      bookend: "intent",
      externalWrite: false,
      tags: ["scrum", "reporting", "risk"],
      mission: "Produce a useful sprint-health report with cited work-item evidence.",
      scenario: "Stakeholders need facts, risks, forecasts, and decisions—not an AI-generated confidence performance.",
      outcomes: ["Separate facts from forecasts.", "Identify decisions and follow-up needs."],
      criteria: ["Every material claim cites source context.", "Missing updates are labeled as unknown rather than inferred."],
      safety: ["Avoid individual blame and unsupported productivity ranking."],
      prerequisites: ["base-camp-repository-safety"],
      proofIds: []
    },
    {
      id: "playwright-first-independent-test",
      version: 1,
      title: "Build an Independent, Maintainable Playwright Test",
      summary: "Automate one valuable business behavior with centralized page objects, stable locators, meaningful assertions, and evidence.",
      region: "playwright-labyrinth",
      level: "Builder",
      xp: 30,
      minutes: 120,
      state: "needs_changes",
      bookend: "validation",
      externalWrite: false,
      tags: ["playwright", "testing", "automation", "read-only"],
      mission: "Automate one important read-only behavior so another tester can understand its business value and failure evidence.",
      scenario: "A passing browser script is not automatically a valuable test; this one must validate a meaningful business outcome.",
      outcomes: ["Centralize selectors and page behavior.", "Produce meaningful business validation and evidence."],
      criteria: ["The test is independent and order-neutral.", "No arbitrary sleeps are used.", "Assertions validate business outcome."],
      safety: ["Use a nonproduction environment.", "Never weaken assertions merely to obtain a pass."],
      prerequisites: ["base-camp-repository-safety"],
      proofIds: ["playwright-test", "page-model", "playwright-quality-validation"]
    }
  ],
  evidence: {
    questId: "jira-read-assigned-stories",
    attemptId: "jira-attempt-001",
    updated: "Today at 10:05 AM",
    git: {
      branch: "quest/jira-read-assigned",
      changed: 6,
      untracked: 1,
      ahead: 2
    },
    proof: [
      {
        id: "skill-definition",
        title: "Reusable skill definition",
        description: "A local skill documents identity, pagination, merge, and safety behavior.",
        path: "participant/skills/jira-read-assigned/SKILL.md",
        status: "detected"
      },
      {
        id: "sample-index",
        title: "Sanitized assigned-story index",
        description: "A local Markdown index demonstrates normalized output.",
        path: "participant/context/jira/assigned/index.md",
        status: "detected"
      },
      {
        id: "jira-sync-validation",
        title: "Synchronization validation",
        description: "The registered validator checks identity, pagination, note preservation, and duplication.",
        path: "validation/jira-read-assigned-run-001.json",
        status: "warning"
      },
      {
        id: "proof-narrative",
        title: "Proof narrative",
        description: "Explain reproduction, tests, limitations, and sensitive-data handling.",
        path: "participant/evidence/jira-read-assigned-stories/jira-attempt-001/PROOF.md",
        status: "detected"
      }
    ],
    validation: {
      outcome: "warning",
      runId: "jira-read-assigned-run-001",
      duration: "4.4 seconds",
      passed: 3,
      warnings: 1,
      failed: 0,
      findings: [
        {
          outcome: "pass",
          severity: "high",
          title: "Authenticated identity resolved",
          detail: "The fixture records /myself before the assigned-story query."
        },
        {
          outcome: "pass",
          severity: "blocking",
          title: "All result pages retrieved",
          detail: "37 of 37 expected issue keys are present across three pages."
        },
        {
          outcome: "pass",
          severity: "blocking",
          title: "Participant notes preserved",
          detail: "The seeded local note remained unchanged after the second sync."
        },
        {
          outcome: "warning",
          severity: "medium",
          title: "Removed-item reason is incomplete",
          detail: "The report retains missing work but cannot yet distinguish deletion from permission loss."
        }
      ]
    }
  },
  badges: [
    { id: "context-scout", title: "Context Scout", description: "Built a safe local foundation.", state: "earned", authority: "Automatic" },
    { id: "jira-ranger", title: "Jira Ranger", description: "Demonstrate safe Jira synchronization.", state: "pending", authority: "Automatic after verification" },
    { id: "validation-guardian", title: "Validation Guardian", description: "Build valuable maintainable automation.", state: "in-progress", authority: "Automatic after verification" },
    { id: "golden-thread-keeper", title: "Golden Thread Keeper", description: "Preserve traceability from intent through verified outcome.", state: "locked", authority: "Reviewer awarded" }
  ],
  activity: [
    { type: "validation", title: "Jira synchronization validator completed with one warning", time: "Today · 10:05 AM", route: "#evidence" },
    { type: "review", title: "Playwright test returned with requested changes", time: "Yesterday · 4:22 PM", route: "#review" },
    { type: "verified", title: "Base Camp repository safety verified", time: "September 11 · 2:15 PM", route: "#quest/base-camp-repository-safety" }
  ],
  health: [
    { name: "Python", status: "pass", importance: "required", value: "3.13.7", remediation: "" },
    { name: "Git repository", status: "pass", importance: "required", value: "feature branch · clean safety boundary", remediation: "" },
    { name: "Local service", status: "pass", importance: "required", value: "127.0.0.1 · protected", remediation: "" },
    { name: "Participant directory", status: "pass", importance: "required", value: "Writable · ownership preserved", remediation: "" },
    { name: "Jira CLI", status: "warning", importance: "quest-specific", value: "Authenticated · token expires in 3 days", remediation: "Refresh the authenticated CLI session before the next live demonstration." },
    { name: "Playwright browsers", status: "fail", importance: "quest-specific", value: "Chromium not installed", remediation: "Run the documented browser-install command before a Playwright quest." },
    { name: "Working tree", status: "warning", importance: "submission", value: "6 changed · 1 untracked", remediation: "Review and commit the intended evidence before submission." }
  ],
  review: {
    participant: "Alex Rivera",
    questId: "playwright-first-independent-test",
    attemptId: "playwright-attempt-001",
    submitted: "September 15 · 3:40 PM",
    state: "needs_changes",
    evidenceHashState: "unchanged",
    validationOutcome: "warning",
    artifacts: [
      { title: "Playwright test", path: "participant/tests/playwright/first-independent-test.spec.ts", status: "present" },
      { title: "Page model", path: "participant/tests/playwright/pages/example-page.ts", status: "present" },
      { title: "Execution record", path: "participant/evidence/playwright-first-independent-test/attempt-001/logs/test-run.txt", status: "present" },
      { title: "Success screenshot", path: "participant/evidence/playwright-first-independent-test/attempt-001/screenshots/validated-state.png", status: "present" }
    ],
    findings: [
      {
        severity: "high",
        title: "Assertion does not prove the business outcome",
        detail: "The test confirms the confirmation panel is visible but never validates that the displayed account and amount match the submitted transfer preview.",
        required: "Assert the critical preview values using the centralized page model before treating the test as successful."
      },
      {
        severity: "medium",
        title: "Failure screenshot is captured too early",
        detail: "The helper captures before Playwright finishes the final assertion, so the failed state may be absent.",
        required: "Use Playwright trace and failure-time attachment behavior rather than the pre-assertion helper."
      }
    ]
  }
};
