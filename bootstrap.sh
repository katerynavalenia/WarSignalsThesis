#!/usr/bin/env bash
# Make a fresh checkout usable — cloud sandbox (claude.ai/code), a new laptop,
# or a Colab clone. Idempotent: safe to re-run.
#
#   bash bootstrap.sh
#
# What it does NOT do: fetch data. `data/**` lives on Google Drive and is
# gitignored (see CLAUDE.md § "Data hosting and compute"). A bootstrapped
# checkout has *no* data at all — that is expected, and 4 tests fail because
# of it. See docs/cloud_sessions.md for what is workable without data.

set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

PY="${PYTHON:-python3}"
VENV=".venv"

echo "==> Python: $("$PY" --version)"

# 1. Virtualenv at the project root, shared by v1 and v2.
if [ ! -x "$VENV/bin/python" ]; then
  echo "==> Creating $VENV"
  "$PY" -m venv "$VENV"
else
  echo "==> Reusing existing $VENV"
fi
VPY="$VENV/bin/python"

# 2. Dependencies. v1 and v2 requirements are identical; install once.
echo "==> Installing dependencies (a few minutes on a cold container)"
"$VPY" -m pip install --quiet --upgrade pip
"$VPY" -m pip install --quiet -r thesis_v2/requirements.txt

# 3. Local path config. Gitignored, so every fresh checkout lacks it, and
#    modules raise a pointed error when it is missing.
for v in thesis_v1 thesis_v2; do
  if [ ! -f "$v/config/paths.yaml" ]; then
    cp "$v/config/paths.yaml.example" "$v/config/paths.yaml"
    echo "==> Wrote $v/config/paths.yaml from example"
  fi
done

# 4. Git LFS pointers, if the tool is available. Only ~10 small CSVs under
#    thesis_v1/outputs/ are LFS-tracked, so this is cheap.
if command -v git-lfs >/dev/null 2>&1; then
  git lfs install --local >/dev/null 2>&1 || true
  git lfs pull >/dev/null 2>&1 || echo "==> git lfs pull failed (non-fatal)"
fi

cat <<'DONE'

==> Ready.

    source .venv/bin/activate
    cd thesis_v1 && python -m pytest -q

Expected on a dataless checkout: 426 passed, 4 failed, 33 skipped.
All 4 failures are missing-data (test_phase5_merge.py::TestLoaders), not code.
DONE
