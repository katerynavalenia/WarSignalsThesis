# Working on this thesis from a phone (Claude Code cloud sessions)

Goal: keep making progress when the laptop is not around. A *cloud session*
runs Claude Code on an Anthropic-managed VM that clones this repo, works on a
branch, and pushes back — steered from [claude.ai/code](https://claude.ai/code)
in a browser or from the Claude mobile app. The session survives you closing
the phone.

This document covers the one-time setup and, more importantly, **what is and
is not workable from a cloud session given that this repo's data lives on
Google Drive, not in git.**

---

## 1. One-time setup: GitHub access

This is the step that produced the "install the Claude GitHub App" prompt.

> **Status, 2026-08-18: done — Option B.** `/web-setup` was run from a local
> CLI, and a cloud session has now pushed to `origin` successfully. Before that
> it failed with `403` and *"GitHub access is not enabled for this session"*,
> because the gate is on the **claude.ai account side**, not GitHub's — the two
> facts below (public repo, `NikitaTishkov` has push rights) are both correct
> and were both insufficient on their own. `worktree-cloud-ready` had reached
> `origin` from a **local** session using its own git credentials, which a cloud
> session does not inherit.

**The important thing to know first:** a cloud session can reach **any
repository the connected GitHub account can see** — installing the Claude
GitHub App *on this repository* is not required for session access. That
matters here because the repo is owned by `katerynavalenia`, not by you, so
requiring an install on the owner's account would have meant waiting on her.
It does not.

Two facts that make this straightforward:

- `katerynavalenia/WarSignalsThesis` is a **public** repository — any
  authenticated GitHub account can clone it.
- The `NikitaTishkov` account has **collaborator push access** (it is how
  `worktree-init-claude-md` got to `origin`), so a cloud session can push
  branches and open PRs.

Pick one of the two ways to connect. Either is sufficient.

### Option A — authorize the Claude GitHub App (works entirely from a phone)

1. Open [claude.ai/code](https://claude.ai/code) and start the onboarding.
2. Choose **Connect GitHub** and authorize the Claude GitHub App for the
   `NikitaTishkov` account.
3. Select `katerynavalenia/WarSignalsThesis` when picking a repository.

This is the path to use if the laptop is already unavailable. Requires a Pro,
Max, or Team plan — Claude Code on the web is in research preview for those.

### Option B — sync the `gh` CLI token (needs the laptop once)

From a terminal on the laptop:

```bash
sudo apt install gh      # not currently installed on this machine
gh auth login            # authenticate as NikitaTishkov
claude                   # then, inside Claude Code:
/web-setup
```

`/web-setup` copies your local `gh` token to your Claude account, and cloud
sessions use it thereafter. Good if you would rather not add another OAuth
authorization.

### When you *do* need the app installed on the repo

Only for **Auto-fix**, the feature where Claude watches a pull request and
responds to CI failures and review comments. That works through GitHub
webhooks, which require the app installed on the repository itself — so it
would need `katerynavalenia` to install it from
[github.com/apps/claude](https://github.com/apps/claude). Everything in this
document works without it. This repo has no CI, so Auto-fix buys little today.

---

## 2. One-time setup: the cloud environment's setup script

A cloud session's VM ships with Python, pip, uv, pytest, git, and ripgrep, but
**not** this project's scientific stack and **not** `git-lfs`. Installing
`statsmodels`, `arch`, `xgboost`, and `shap` on every session start would waste
a minute or two each time.

The fix is the environment's **setup script**, which runs once and is then
captured in a filesystem snapshot that later sessions start from. Paste this
into the **Setup script** field of the environment settings dialog at
[claude.ai/code](https://claude.ai/code):

```bash
#!/bin/bash
apt-get update -qq && apt-get install -y -qq git-lfs || true
uv pip install --system -q \
  pandas numpy pyarrow openpyxl xlrd pyyaml matplotlib seaborn pytest \
  requests tqdm langdetect datasketch \
  statsmodels scikit-learn arch xgboost shap \
  linearmodels rapidfuzz || true
exit 0
```

Notes on that script:

- Packages are listed **by name rather than from `requirements.txt`** so it
  does not depend on where the clone lands or whether it has happened yet.
  Keep it in sync with `thesis_v2/requirements.txt` when that file changes.
- It also installs `linearmodels` and `rapidfuzz`, which the v2 plan needs
  (PanelOLS, SIPRI name→ticker matching) and which `requirements.txt` does not
  yet list.
- Every command ends in `|| true` and the script exits 0. A setup script that
  exits non-zero makes the **session fail to start**.
- Keep it under ~5 minutes or the snapshot cache will not build.
- Network access must stay at the default **Trusted** level; PyPI is on the
  default allowlist. At **None**, the installs fail.

The snapshot rebuilds when you edit the script or the allowed hosts, and
expires after roughly seven days.

---

## 3. What the repo now does for itself

`.claude/settings.json` registers a `SessionStart` hook that runs
`.claude/cloud_setup.sh` on every cloud session start and resume. It:

1. Writes `thesis_v1/config/paths.yaml` and `thesis_v2/config/paths.yaml` from
   their `.example` templates. These are gitignored, so **every** fresh clone
   lacks them and the config loader raises on import.
2. Installs the Python dependencies **only if they are missing** — a cheap
   `import` probe, so it is a no-op once the environment snapshot exists. This
   is the safety net if you skip step 2 above.
3. Runs `git lfs pull` when `git-lfs` is available.

The script exits immediately when `CLAUDE_CODE_REMOTE` is not `"true"`, so it
never touches your laptop. For a laptop or a Colab clone, run `bootstrap.sh`
at the repo root instead — that one creates the `.venv` this project expects.

`.claude/settings.json` also pre-approves the routine read-only and test
commands, which matters more on a phone than on a laptop: every permission
prompt is a round trip you have to notice and tap.

---

## 4. What actually works without the data

**This is the real constraint, and it is not fixable by configuration.**

`data/**` is gitignored — the canonical store is the Google Drive folder
`WarSignalsThesis_Data/`, synced with `rclone` (see
`docs/v1/data_sharing.md`). A cloud VM has no Drive credentials, so a cloud
session gets a checkout with **no data files at all**. Not even the derived
Phase 5 parquets that are present on your laptop: `daily_master.parquet`,
`feature_matrix.parquet`, and `model_matrix.parquet` are all gitignored.

Measured on a fresh, dataless checkout of `main` with `paths.yaml` in place:

```
426 passed, 4 failed, 33 skipped
```

All four failures are `thesis_v1/tests/test_phase5_merge.py::TestLoaders`
(`test_load_financial`, `test_load_attack`, `test_load_news_enriched`,
`test_load_news_pivot_casts_category_to_datetime`). They are missing-data, not
code. **Treat "426 passed, 4 failed, 33 skipped" as the green baseline for a
cloud session** and do not try to fix those four there.

> Note: `.gitignore` carries negation rules that read as though
> `thesis_v1/data/processed/news/*.parquet` are tracked via LFS. They are not
> — `git ls-files` under `data/` returns only `.gitkeep` files and three
> markdown reports. The ten files that are actually LFS-tracked are CSVs under
> `thesis_v1/outputs/`.

### Well suited to a cloud session

- **Thesis writing** — `thesis_v1/thesis/`, and all of `docs/v2/`
  (`research_plan.md`, `decision_log.md`, `project_status.md`).
- **Writing v2 code from the skeleton.** `src/` is currently just
  empty `__init__.py` files and `scripts/`/`tests/` are empty, so the entire
  first pass of module and test authoring is data-independent.
- **Tests that use fixtures or synthetic frames** — 426 of them, including all
  of `test_phase6_baselines.py`, `test_expanding_window.py`, `test_recursive.py`,
  and `test_date_utils.py`. Enough to develop against the modelling engine.
- **Reading, refactoring, and reviewing** v1's `src/`, and inspecting the
  tracked `thesis_v1/outputs/` figures and tables.
- **Planning** — deciding a phase's approach, drafting the decision-log entry.

### Not possible in a cloud session

- Any `scripts/phase*.py` run. The whole Phase 5 → 6 → 7 chain reads parquets
  that are not there.
- v2's Phase 1, which needs the GPR and SIPRI raw files
  (`thesis_v1/thesis_old_try/data/raw/{gpr,sipri}/`) — absent from git *and*
  from your local checkout.
- Anything that regenerates `outputs/`.

### The exception: GDELT work *is* possible from a cloud session

The constraint above is about the **Drive-hosted parquets**, and it holds. It
does **not** hold for the v3 GDELT rebuild, which is the project's main
remaining data task. GDELT is a public dataset on BigQuery, so a cloud session
with a service-account key can run the filtering and daily aggregation
**server-side** and receive a few megabytes of daily series — the 4.19 TB never
touches the VM. That makes the single largest piece of remaining work
cloud-native rather than laptop-bound.

See [`v3/environment_setup.md`](v3/environment_setup.md) §3.2 for the service
account setup, §3.3 for reaching Drive through the Drive API (the Drive
*connector* exposes only share/trash/rename in a Claude Code session — it cannot
read or download file contents), and §4 for how this changes the architecture.

**Do not let a cloud session "fix" a missing-data failure by re-downloading
from GDELT or the original sources.** That is the failure mode this section
exists to prevent — it would burn hours and produce a corpus that does not
match the one the results were built on. The correct response is to stop and
leave it for a laptop session with Drive synced.

---

## 5. Working from the phone

Starting a session:

- **From the phone:** open [claude.ai/code](https://claude.ai/code) or the
  Claude mobile app, pick `katerynavalenia/WarSignalsThesis`, and describe the
  task.
- **From the laptop, to pick up later on the phone:**
  ```bash
  claude --cloud "Draft the Phase 1 data-loading module for thesis_v2"
  ```
  The VM clones the **GitHub remote at your current branch**, not your working
  tree — so commit and push first.

Getting the work back:

- The session works on its own branch and can open a PR. Review the diff in
  the web UI, leave inline comments, and send them back as a message.
- On the laptop, `claude --teleport` pulls the session and its branch into a
  local terminal with the full conversation history. It requires a clean
  working tree.

Two things worth doing to make phone sessions productive:

- **Plan on the laptop, execute in the cloud.** Write the plan into
  `docs/v2/` and commit it, then a phone session has an unambiguous brief and
  needs far less back-and-forth — which is the expensive part on a phone.
- **State the data constraint in the task.** Something like "the cloud
  checkout has no data; write the module and its tests against synthetic
  frames, do not attempt a pipeline run" saves a wasted session. `CLAUDE.md`
  says this too, but repeating it in the task makes it stick.

---

## 6. Note on repository size

Local `.git` is ~7.3 GB and the tree is ~12 GB, which looks alarming for cloud
work. It is not a problem:

- `size-pack` is **21.8 MiB**. That, plus ten small LFS CSVs, is what a cloud
  session clones.
- The bulk is 989 loose objects (~4.4 GB) that exist only on your laptop, plus
  a 2.9 GB local LFS cache and ~9.4 GB of gitignored Drive-synced data under
  `thesis_v1/data/`.
- To reclaim the loose-object space locally, run `git gc --prune=now` at the
  repo root. It changes nothing about the remote and nothing about cloud
  sessions — purely a local cleanup, and safe to skip.
