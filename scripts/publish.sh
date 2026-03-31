#!/usr/bin/env bash
# publish.sh — Full genWtao pipeline (local build + FTP deploy)
#
# Usage:  ./scripts/publish.sh
#
# Reads:
#   config/config.yaml  — engine config (graph path, hosting, hugo, theme, colors)
#   .env                — secrets (FTP_PASSWORD)
set -euo pipefail

# ── Paths ────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(dirname "$SCRIPT_DIR")"
CONFIG="$APP_DIR/config/config.yaml"

HUGO_PROJECT="$APP_DIR/site"
HUGO_CONTENT="$HUGO_PROJECT/content"
HUGO_PUBLIC="$HUGO_PROJECT/public"

# ── Load .env (secrets) ──────────────────────────────────────
if [[ -f "$APP_DIR/.env" ]]; then
    source "$APP_DIR/.env"
fi
FTP_PASSWORD="${FTP_PASSWORD:-}"

# ── Locate Logseq graph ──────────────────────────────────────
# Override via LOGSEQ_GRAPH env var, otherwise read from config.yaml.
if [[ -z "${LOGSEQ_GRAPH:-}" ]]; then
    LOGSEQ_GRAPH=$(python3 -c "
import yaml, os
with open('$CONFIG') as f:
    c = yaml.safe_load(f)
p = c.get('graph_path', '')
print(os.path.expandvars(os.path.expanduser(p)))
")
fi

# ── Utility functions ────────────────────────────────────────
log()  { echo ""; echo "▶ $*"; }
ok()   { echo "  ✅ $*"; }
fail() { echo "  ❌ $*"; exit 1; }

# ── Read hosting config from config.yaml via Python ──────────
read_hosting_config() {
    python3 -c "
import yaml, sys
with open('$CONFIG') as f:
    c = yaml.safe_load(f)
h = c.get('hosting', {})
ftp = h.get('ftp', {})
print(h.get('site_url', ''))
print(ftp.get('host', ''))
print(ftp.get('user', ''))
print(str(ftp.get('port', 21)))
print(ftp.get('remote_path', '/htdocs'))
"
}

# ── Pre-flight checks ────────────────────────────────────────
log "Checking environment"

command -v hugo    >/dev/null 2>&1 || fail "Hugo not installed. Run: brew install hugo"
command -v python3 >/dev/null 2>&1 || fail "Python3 required"

[[ -d "$LOGSEQ_GRAPH" ]] || fail "Logseq graph not found: $LOGSEQ_GRAPH"
[[ -d "$HUGO_PROJECT" ]] || fail "Hugo project not found: $HUGO_PROJECT"
[[ -n "$FTP_PASSWORD" ]] || fail "FTP_PASSWORD not set. Create $APP_DIR/.env with FTP_PASSWORD=yourpassword"

# Read hosting details from config.yaml
IFS=$'\n' read -r -d '' SITE_URL FTP_HOST FTP_USER FTP_PORT FTP_REMOTE <<< "$(read_hosting_config)" || true

[[ -n "$FTP_HOST" ]] || fail "No hosting.ftp.host in $CONFIG"
[[ -n "$FTP_USER" ]] || fail "No hosting.ftp.user in $CONFIG"

ok "Environment OK (graph: $LOGSEQ_GRAPH)"

# ── Step 1: Export Logseq → Hugo ─────────────────────────────
log "Step 1/3: Export Logseq → Hugo"

python3 "$SCRIPT_DIR/logseq_to_hugo.py" \
    --graph  "$LOGSEQ_GRAPH" \
    --output "$HUGO_CONTENT" \
    --config "$CONFIG" \
    --clean

ok "Export done"

# ── Step 2: Build Hugo ───────────────────────────────────────
log "Step 2/3: Build Hugo"

cd "$HUGO_PROJECT"
rm -rf "$HUGO_PUBLIC"
hugo --minify --logLevel warn

PAGES=$(find "$HUGO_PUBLIC" -name "*.html" | wc -l | tr -d ' ')
ok "Build done — $PAGES pages generated"

# ── Step 3: Upload FTP ───────────────────────────────────────
log "Step 3/3: Upload FTP → $SITE_URL"

if command -v lftp >/dev/null 2>&1; then
    lftp -c "
        set ftp:ssl-allow no;
        open ftp://$FTP_USER:$FTP_PASSWORD@$FTP_HOST:$FTP_PORT;
        mirror --reverse --delete --verbose=1 $HUGO_PUBLIC $FTP_REMOTE
    "
elif command -v curl >/dev/null 2>&1; then
    find "$HUGO_PUBLIC" -type f | while read -r file; do
        REMOTE_PATH="${file#$HUGO_PUBLIC}"
        curl -s --ftp-create-dirs -T "$file" \
            "ftp://$FTP_USER:$FTP_PASSWORD@$FTP_HOST:$FTP_PORT$FTP_REMOTE$REMOTE_PATH" || true
    done
else
    fail "lftp or curl required for FTP deployment"
fi

ok "FTP upload done"

# ── Summary ──────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀  Site published: $SITE_URL"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
