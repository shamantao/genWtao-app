#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# publish.sh — Full genWtao pipeline
# Usage:  ./scripts/publish.sh
# Mobile: via iOS Shortcuts → SSH → this script
# ─────────────────────────────────────────────────────────────
set -euo pipefail

# ── Paths ────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(dirname "$SCRIPT_DIR")"
CONFIG="$APP_DIR/config/config.yaml"

LOGSEQ_GRAPH="/Users/phil/Library/CloudStorage/Dropbox/logseq/genWtao"
HUGO_PROJECT="$APP_DIR/site"
HUGO_CONTENT="$HUGO_PROJECT/content"
HUGO_PUBLIC="$HUGO_PROJECT/public"

FTP_HOST="YOUR_FTP_HOST"
FTP_USER="YOUR_FTP_USER"
FTP_REMOTE="/htdocs"
SITE_URL="https://genwtao.free.nf"

# FTP password: from environment variable or local .env file
if [[ -f "$APP_DIR/.env" ]]; then
    source "$APP_DIR/.env"
fi
FTP_PASSWORD="${FTP_PASSWORD:-}"

# ── Utility functions ─────────────────────────────────────────
log()  { echo ""; echo "▶ $*"; }
ok()   { echo "  ✅ $*"; }
fail() { echo "  ❌ $*"; exit 1; }

# ── Pre-flight checks ────────────────────────────────────────
log "Checking environment"

command -v hugo   >/dev/null 2>&1 || fail "Hugo not installed. Run: brew install hugo"
command -v python3 >/dev/null 2>&1 || fail "Python3 required"

[[ -d "$LOGSEQ_GRAPH" ]]   || fail "Logseq graph not found: $LOGSEQ_GRAPH"
[[ -d "$HUGO_PROJECT" ]]   || fail "Hugo project not found: $HUGO_PROJECT"
[[ -n "$FTP_PASSWORD" ]]   || fail "FTP_PASSWORD not set. Create $APP_DIR/.env with FTP_PASSWORD=yourpassword"

ok "Environment OK"

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
        open ftp://$FTP_USER:$FTP_PASSWORD@$FTP_HOST;
        mirror --reverse --delete --verbose=1 $HUGO_PUBLIC $FTP_REMOTE
    "
elif command -v curl >/dev/null 2>&1; then
    # Fallback to curl if lftp is missing (slower)
    find "$HUGO_PUBLIC" -type f | while read -r file; do
        REMOTE_PATH="${file#$HUGO_PUBLIC}"
        curl -s --ftp-create-dirs -T "$file" \
            "ftp://$FTP_USER:$FTP_PASSWORD@$FTP_HOST$FTP_REMOTE$REMOTE_PATH" || true
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
