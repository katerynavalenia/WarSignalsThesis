#!/usr/bin/env bash
# Re-authenticate rclone for the gdrive remote.
# Use when "rclone lsf gdrive:..." fails with unauthorized_client or token expired.
#
# Usage: bash .github/skills/rclone-drive-sync/scripts/reauth.sh
# Or:    bash reauth.sh [--no-wait]   # --no-wait: don't wait for user to complete flow

set -euo pipefail

NO_WAIT=false
if [[ "${1:-}" == "--no-wait" ]]; then
    NO_WAIT=true
fi

RCLONE_CONF="$HOME/.config/rclone/rclone.conf"
LOG="/tmp/rclone_auth_skill.log"

echo "=== rclone re-auth for [gdrive] ==="

# 1. Verify rclone is installed
if ! command -v rclone >/dev/null 2>&1; then
    echo "✗ rclone not installed. Run: sudo apt install rclone"
    exit 1
fi

# 2. Back up current config and strip the bad token
if [[ -f "$RCLONE_CONF" ]]; then
    cp "$RCLONE_CONF" "$RCLONE_CONF.bak"
    grep -v "^token" "$RCLONE_CONF.bak" | grep -v "^expiry" > "$RCLONE_CONF"
    echo "✓ Config backed up to rclone.conf.bak, token stripped"
else
    echo "✗ rclone config not found at $RCLONE_CONF"
    echo "  Run: rclone config to create one first."
    exit 1
fi

# 3. Kill any old rclone authorize processes
pkill -f "rclone authorize" 2>/dev/null || true
sleep 1

# 4. Start OAuth flow in background
unset BROWSER
rm -f "$LOG"
nohup rclone authorize drive > "$LOG" 2>&1 &
AUTH_PID=$!
echo "✓ Started rclone authorize, PID=$AUTH_PID"

# 5. Wait for the URL to appear
sleep 5
URL=$(grep -oP 'http://127\.0\.0\.1:\d+/auth\?state=\S+' "$LOG" | head -1 || true)
if [[ -z "$URL" ]]; then
    echo "✗ Failed to extract auth URL from log:"
    cat "$LOG"
    exit 1
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  ACTION REQUIRED: Open this URL in your browser:"
echo ""
echo "  $URL"
echo ""
echo "  Log in with the Google account that owns WarSignalsThesis_Data,"
echo "  click 'Allow' on the permissions screen, and rclone will receive"
echo "  the new token automatically."
echo "═══════════════════════════════════════════════════════════════"
echo ""

if $NO_WAIT; then
    echo "(--no-wait set: exiting. Run this script again to complete.)"
    exit 0
fi

# 6. Wait for the user to complete the flow (up to 120 seconds)
echo "Waiting for auth completion (max 120 seconds)..."
for i in {1..24}; do
    sleep 5
    if grep -q "Got code" "$LOG" 2>/dev/null; then
        echo "✓ Auth code received"
        break
    fi
    # Check if process is still alive
    if ! kill -0 "$AUTH_PID" 2>/dev/null; then
        echo "✗ rclone authorize process exited unexpectedly"
        cat "$LOG"
        exit 1
    fi
    echo "  ...still waiting (${i}/24)"
done

if ! grep -q "Got code" "$LOG" 2>/dev/null; then
    echo "✗ Timeout: rclone did not receive auth code within 120s"
    cat "$LOG"
    exit 1
fi

# 7. Parse the token and save it
python3 <<'PYEOF'
import re, json, configparser
log = open('/tmp/rclone_auth_skill.log').read()
match = re.search(r'--->\s*(\{.*?\})\s*<---', log, re.DOTALL)
if not match:
    print('✗ Could not parse token from log')
    exit(1)
token_data = json.loads(match.group(1).strip())
config = configparser.ConfigParser()
config.read('/home/mykyta/.config/rclone/rclone.conf')
config['gdrive']['token'] = json.dumps(token_data)
with open('/home/mykyta/.config/rclone/rclone.conf', 'w') as f:
    config.write(f)
print(f'✓ Token saved. Expires: {token_data.get("expiry", "unknown")}')
PYEOF

# 8. Verify auth works
echo ""
echo "=== Verifying auth ==="
if rclone lsf gdrive:WarSignalsThesis_Data/ 2>&1 | head -3; then
    echo ""
    echo "✓✓✓ Auth working. You can now run rclone commands."
else
    echo "✗ Auth verification failed"
    exit 1
fi
