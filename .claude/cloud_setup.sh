#!/usr/bin/env bash
# SessionStart hook — prepares a cloud session VM (claude.ai/code, the mobile
# app, routines). No-op on a local machine.
#
# Wired up in .claude/settings.json. Runs on every cloud session start and
# resume, so it must be fast and idempotent: the heavy pip install is skipped
# whenever the packages are already present, which is the normal case once the
# cloud environment's filesystem snapshot has been built.
#
# For a laptop or a Colab clone use ../bootstrap.sh instead — that one creates
# the .venv this repo expects locally.

# Never fail a session start. Every branch below ends up at exit 0.
set -u

# CLAUDE_CODE_REMOTE is "true" only inside a cloud session VM.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0

# 1. Local path config. Gitignored, so a fresh clone never has it, and the
#    config loader raises a pointed error when it is missing — which is what
#    made 1 of the 5 dataless test failures.
for v in .; do
  if [ -f "$v/config/paths.yaml.example" ] && [ ! -f "$v/config/paths.yaml" ]; then
    cp "$v/config/paths.yaml.example" "$v/config/paths.yaml"
    echo "cloud_setup: wrote $v/config/paths.yaml"
  fi
done

# 2. Python dependencies. The cloud environment snapshot normally already has
#    them, so probe first and install only on a cold VM. `arch` and `xgboost`
#    are the two slowest/most likely to be absent, so they make a good probe.
if ! python3 -c "import pandas, statsmodels, arch, xgboost, shap" 2>/dev/null; then
  echo "cloud_setup: installing Python dependencies (cold environment)"
  if command -v uv >/dev/null 2>&1; then
    uv pip install --system -q -r requirements.txt || \
      pip install -q -r requirements.txt || \
      echo "cloud_setup: dependency install failed — ask Claude to retry"
  else
    pip install -q -r requirements.txt || \
      echo "cloud_setup: dependency install failed — ask Claude to retry"
  fi
fi

# 3. Git LFS. Not pre-installed on the session VM, and ~10 small CSVs under
#    outputs/ are LFS-tracked — without it they are pointer stubs.
if command -v git-lfs >/dev/null 2>&1; then
  git lfs install --local >/dev/null 2>&1
  git lfs pull >/dev/null 2>&1 || echo "cloud_setup: git lfs pull failed (non-fatal)"
fi

exit 0
