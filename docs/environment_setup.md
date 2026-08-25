# Environment Setup — what to configure so the agent can run the thesis end to end

**Date:** 2026-08-17
**Purpose:** Kateryna asked how to set the cloud session up so it can fully
operate the thesis, including Google Drive and Colab. This document records what
was **measured** in the session (not assumed), what is blocked, and the exact
fixes in priority order.

---

## 1. What this session actually is

Measured 2026-08-17 inside the running container:

| Resource | Value | Implication |
|---|---|---|
| CPU / RAM | 4 cores / 15 GB | Ample for the econometrics (~2,850 rows × ~150 cols runs in seconds). |
| Free disk | ~30 GB | Enough for aggregated data; **not** for the 4.19 TB GDELT translingual archive. |
| Lifetime | ephemeral — reclaimed after inactivity | **Anything not committed to git is lost.** No state carries between sessions. |
| Python | 3.11, `pip install` works | `pandas`, `statsmodels`, `pyarrow` installed cleanly on demand; nothing is pre-installed. |
| Network egress | open to `googleapis.com`, `bigquery.googleapis.com`, `drive.google.com`, `colab.research.google.com`, `api.gdeltproject.org`, `api.github.com` | The network policy is not the constraint. Credentials are. |
| `gcloud` / `bq` / `gsutil` / `rclone` | **not installed** | Use Python client libraries instead (`google-cloud-bigquery`, `google-api-python-client`). |

**The environment:** `Master Thesis` — `env_01VScR7SCxNuVFYh6atb5pm8`
(the other one is `Default` — `env_0125fjYntahz7YtWaFnP9d3j`).

---

## 2. The three blockers, measured

### 2.1 GitHub — write access denied

```
$ git push -u origin claude/thesis-analysis-planning-p7ej41
fatal: ... The requested URL returned error: 403

$ curl -H "Authorization: Bearer $GITHUB_TOKEN" https://api.github.com/repos/katerynavalenia/WarSignalsThesis
{"message": "GitHub access is not enabled for this session.
             An org admin must connect the Claude GitHub App for this organization."}
```

Read works (`git ls-remote` lists `main` and `worktree-init-claude-md`); write does
not. Note the session's GitHub identity is **`NikitaTishkov`**, while the repo
belongs to **`katerynavalenia`** — so there are *two* things to fix (§3.1).

### 2.2 Google Drive — connector is read-crippled on this surface

The Google Drive connector shows as `connected: true, enabledInChat: true`, and
its directory blurb says "Search, read, and upload files instantly". But in a
Claude Code session only three tools are exposed:

- `share_file` (grant someone access)
- `trash_file` (move to trash)
- `update_file` (rename / move — its own description refers to a `search_files`
  tool that is not available here)

**There is no way to list, read, download, or upload file contents.** The Drive
connector as wired into this surface cannot be used as a data pipe. This is a
platform limitation, not a permission that can be granted — the fix is to reach
Drive through the Drive API with a service account instead (§3.3).

### 2.3 Google Colab — not programmatically drivable

Colab is an interactive browser product. There is no API to start a runtime,
execute a notebook, or collect its output. Nothing can change this. Colab's role
has to be redefined rather than automated (§4).

---

## 3. Fixes, in priority order

### 3.1 Connect GitHub — do this first

Without it nothing the agent produces can be saved.

**Nothing is installed into the repository.** No file, no workflow, no config.
GitHub access for cloud sessions is a property of the *connecting GitHub
account*, held at the account level.

Per the [Claude Code on the web docs](https://code.claude.com/docs/en/claude-code-on-the-web#github-authentication-options)
there are two ways to grant it, and **either one is sufficient**:

| Method | How | Notes |
|---|---|---|
| **`/web-setup`** | Run `/web-setup` in the Claude Code CLI on a local machine where `gh` is already authenticated | Fastest. Syncs the local `gh` token to the claude.ai account. No admin action needed — unless a Team/Enterprise Owner has disabled it via the "Quick web setup" toggle at claude.ai/admin-settings/claude-code. |
| **Claude GitHub App** | Authorize during web onboarding at claude.ai, or install from https://github.com/apps/claude | Installed on the **GitHub account** (visible afterwards at github.com/settings/installations), not on the repo. Also enables PR webhooks for Auto-fix. |

**The decisive requirement — and the one that actually blocks us:** the docs
state that "a cloud session can access any repository the connecting GitHub
account can see, not just the repositories the Claude GitHub App is installed
on. App installation … is not a session-level access control."

So access follows the **connecting account's own GitHub permissions**. This
session authenticates as **`NikitaTishkov`**, and the repository belongs to
**`katerynavalenia`**. Therefore:

- If **Kateryna** connects her own GitHub account, she already owns the repo and
  nothing further is needed.
- If **Nikita** is the connecting account, Kateryna must add him as a **Write**
  collaborator: repo → Settings → Collaborators and teams → Add people → Write.
  Installing the App does not substitute for this.

Note that only the *owner* of a personal GitHub account can install a GitHub App
on it — a collaborator cannot do it on someone else's behalf.

*Alternative if the two-account split stays awkward:* move the repository into a
GitHub organization both accounts belong to, or have Nikita work from a fork and
open pull requests.

**Verify it worked:** a new session should succeed at
`git push -u origin <branch>`. There are currently **2 unpushed commits** on
`claude/thesis-analysis-planning-p7ej41` waiting for this.

### 3.2 BigQuery service account — the change that removes the 4 TB problem

This is the highest-leverage item after GitHub. The GDELT translingual archive is
4.19 TB of files, which cannot come into this container — but BigQuery can do the
filtering and daily aggregation **server-side** and return a table of a few
megabytes. That takes Colab off the critical path entirely.

1. In Google Cloud, create (or reuse) a project and **enable the BigQuery API**.
   Reading the `gdelt-bq` public dataset is free; you pay only for bytes scanned,
   and the first 1 TB/month is free.
2. Create a service account, e.g. `claude-thesis@<project>.iam.gserviceaccount.com`.
3. Grant it **`roles/bigquery.jobUser`** on the project (enough to run queries).
   Add `roles/bigquery.dataEditor` on **one dedicated dataset** only if we want to
   materialise intermediate tables. Grant nothing else.
4. **Set a custom BigQuery quota** (Cloud console → IAM & Admin → Quotas →
   "Query usage per day"), e.g. 200 GB/day. This caps the worst case at a few
   dollars regardless of what any query does.
5. Create a JSON key and base64-encode it:
   `base64 -w0 key.json`
6. In Claude Code on the web → the **Master Thesis** environment → environment
   variables, add:
   - `GCP_SA_KEY_B64` = the base64 blob
   - `GCP_PROJECT` = the project id
7. Rotate/delete the key when the thesis is submitted.

With that in place the agent can, in-session:

```python
import base64, os, pathlib
pathlib.Path("/tmp/sa.json").write_bytes(base64.b64decode(os.environ["GCP_SA_KEY_B64"]))
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/tmp/sa.json"
from google.cloud import bigquery
client = bigquery.Client(project=os.environ["GCP_PROJECT"])
# every query is dry-run first to price it before it runs
```

**Security note, stated plainly:** a service account key in an environment
variable is readable by the session. Scope it to one project with only
`bigquery.jobUser`, cap the quota, and rotate it at the end. Do not reuse an
existing key that has broader roles.

**Zero-credential alternative:** Kateryna runs the aggregation query herself once
in the BigQuery console and commits the resulting CSV to the repo. The agent
writes the SQL; a human runs it. Slower to iterate, but no key leaves her
account. This is a legitimate choice.

### 3.3 Google Drive — reach it through the API, not the connector

If Drive access is wanted (to read the existing 5 GB `WarSignalsThesis_Data`
folder, or to write results back), use the **same service account**:

1. Enable the **Google Drive API** in the project.
2. In Drive, share the `WarSignalsThesis_Data` folder with the service account's
   email address — *Viewer* to read, *Editor* to also write results back. No
   domain-wide delegation is needed for an explicitly shared folder.
3. The agent then uses `google-api-python-client` (Drive v3) with the same
   credentials to list and download files.

**Or skip Drive entirely.** Under the architecture in §4 the only things that
need to move are aggregated daily series of a few MB, which belong in the git
repo anyway (versioned, diffable, and reproducible — which Drive is not). The
existing `.gitattributes` already routes `*.csv` and processed parquet through
Git LFS. Drive stays useful as *your* archive of the raw corpus; it does not need
to be in the agent's path.

### 3.4 A setup script so every session starts ready

Nothing is pre-installed, so each new session currently begins with a `pip
install`. Add a `SessionStart` hook to the repo (or a setup script on the
environment) that installs `requirements.txt` — `pandas`, `numpy`, `statsmodels`,
`linearmodels`, `arch`, `scikit-learn`, `xgboost`, `pyarrow`, `google-cloud-bigquery`,
`google-api-python-client`, `yfinance`. Small change, saves a few minutes and a
class of "module not found" detours every session.

---

## 4. The architecture this implies

The old design (GitHub for code → Drive for data → Colab for compute, moved by
`rclone`) was built for a human at a laptop. It does not fit an agent in an
ephemeral container. The replacement:

```
   BigQuery  ──────────────────────────────►  aggregated daily series (a few MB)
   (GDELT 4.19 TB stays in Google's cloud;          │
    filtering + daily aggregation run there)        │
                                                    ▼
                                          GitHub repo  ◄────► this session
                                       (code, configs,        (all econometrics,
                                        aggregated data,       figures, tables,
                                        outputs, thesis text)  writing)
                                                    ▲
                                                    │  notebooks the agent writes,
                                                    │  a human opens and runs
                                          Google Colab Pro
                                    (only: bulk-download fallback,
                                     heavy hyperparameter tuning)
```

Three rules that make this work:

1. **Raw data never enters the container.** Aggregation happens where the data
   lives.
2. **The repo is the single source of truth.** Aggregated data, outputs, and text
   are all committed. Nothing important lives only in Drive or only in a
   container.
3. **Colab is a fallback, not a dependency.** If BigQuery has the translingual
   records (one query to check — first task once §3.2 is done), Colab may not be
   needed at all.

### Colab's remaining role

The agent cannot start a Colab run. What it can do is write the notebook, commit
it, and give you a link; you open and run it, and the notebook writes its results
back:

```
https://colab.research.google.com/github/katerynavalenia/WarSignalsThesis/blob/<branch>/<path>.ipynb
```

Two jobs justify it: the bulk translingual download if BigQuery turns out not to
carry those records, and the XGBoost tuning grid (~110 min, already written in
`thesis_v1/scripts/phase7_tune.py`).

---

## 5. What no amount of setup will fix

Worth being explicit, so the plan does not assume otherwise:

- **Bloomberg.** The WAERLST/BSHIELDT files start 2020-01; the target sample
  starts 2015-02. Extending them needs a terminal, which is a human at a
  university machine. The fallback (a free long-history defence basket validated
  on the 2020–2026 overlap) is in `research_plan.md` §4.3.
- **The hand-labelled precision audit** of the source classifier (§5.5 of the
  plan). The agent can prepare the sample and the labelling sheet; someone has to
  open ~400 URLs and judge them. This is also the part that makes the methodology
  chapter credible, so it is worth doing properly.
- **The paper draft itself.** The reviewed version is not in the repository — only
  code, data pipelines, and audits are. To work on the text directly, commit the
  draft (as `.md`, `.tex`, or `.docx`) to the repo.
- **Supervisor judgement calls.** The reframing in `research_plan.md` §11
  needs Thomas's sign-off before the ~2-week data rebuild starts.

---

## 6. Minimum viable setup

If only one thing gets done: **§3.1, the GitHub App.** Without it no work
survives the session.

If two: add **§3.2, the BigQuery service account.** Those two together are enough
to execute Phases 1–5 of the research plan without Drive and without Colab.

Everything else is convenience.
