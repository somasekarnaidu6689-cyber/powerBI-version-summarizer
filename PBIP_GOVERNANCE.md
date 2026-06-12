# PBIP PR Validation — Governance Documentation

---

## Issue 5 — Approval Gate Enforcement

The workflow alone cannot block merges. Branch protection rules must be
configured in GitHub to enforce this. Do the following once per repository:

### Step 1 — Enable branch protection on your target branch

Go to **Settings → Branches → Add rule** and set:

- Branch name pattern: `main` (or `main-v2`)
- ✅ Require a pull request before merging
- ✅ Require approvals → set minimum to `1` (or more)
- ✅ Require status checks to pass before merging
  - Search for and add: `validate` (the job name in `pr-validation.yml`)
  - Search for and add: `detect` (the detection job)
- ✅ Require branches to be up to date before merging
- ✅ Do not allow bypassing the above settings (blocks admins too)

### Step 2 — What this enforces

```
PR opened
    │
    ▼
detect job runs → finds changed powerBi/ projects
    │
    ▼
validate job runs per project → posts diff + test result to PR comment
    │
    ├── tests fail?  → GitHub blocks merge (required status check failed)
    ├── no approval? → GitHub blocks merge (approval required)
    └── both pass?   → merge button becomes available
```

The status check name GitHub looks for is the **job name** from the workflow,
not the workflow name. With `strategy.matrix`, each matrix job appears as
`validate (powerBi)`, `validate (ProjectAlpha/powerBi)` etc. To require all
matrix variants, enable **"Require all matrix jobs to pass"** in the status
check settings, or add the job names individually after the first run.

---

## Issue 6 — Baseline Strategy

By default the workflow diffs the PR branch against the **base branch HEAD**
(whatever branch the PR targets, e.g. `main`). Three additional strategies
are supported via `workflow_dispatch` inputs:

| Strategy | When to use |
|---|---|
| `base_branch` (default) | Normal PR review — compare against where you're merging into |
| `tag` | Compare against a named release tag, e.g. `v1.0.0` |
| `commit` | Compare against a specific commit SHA |
| `branch` | Compare against any other branch, e.g. `release/2024-Q4` |

These are configured in the workflow via `workflow_dispatch` inputs (see
`pr-validation.yml`). For automated PR runs the strategy is always
`base_branch` — the inputs only apply when triggering manually.

---

## Issue 7 — What Is and Is Not Compared

### What IS compared

| Area | Details |
|---|---|
| **Semantic model — tables** | Added, removed tables |
| **Semantic model — columns** | Added, removed, modified columns per table |
| **Semantic model — measures** | Changed DAX expressions, format strings, descriptions |
| **Semantic model — relationships** | Added, removed, changed cardinality or cross-filter behaviour |
| **Semantic model — roles (RLS/OLS)** | Added, removed, changed row-level or object-level security rules |
| **Report — pages** | Added, removed, renamed pages |
| **Report — visuals** | Added, removed, modified visuals per page |
| **Report — filters** | Changed report/page/visual-level filters |
| **Report — slicers** | Changed slicer configurations |
| **Layout — canvas** | Canvas size and background changes |
| **Layout — bookmarks** | Added, removed, changed bookmarks |
| **Layout — z-order** | Visual stacking order changes |

### What is NOT compared

These are outside the scope of PBIP file format and are not detectable from
the files in the repository:

| Area | Reason not compared |
|---|---|
| **Refresh schedules** | Stored in Power BI Service, not in PBIP files |
| **Data gateway configuration** | Service-side setting, not in PBIP files |
| **Workspace / deployment pipeline settings** | Service-side, not in PBIP files |
| **Row-level security membership** (who is in a role) | Service-side, only the rule definition is in PBIP |
| **Custom visuals (.pbiviz packages)** | Binary blobs, not diffable as text |
| **Themes (.json applied at service level)** | Only embedded theme JSON is compared; service-applied themes are not |
| **Dataflow / datamart dependencies** | Not stored in PBIP files |
| **Incremental refresh policies** | Partially in TMDL but refresh windows are service-side |
| **Report subscriptions and alerts** | Service-side only |
| **Endorsement / certification status** | Service-side metadata |

If any of the above areas are critical for your review process, they must be
verified manually in the Power BI Service before approving the PR.