#!/usr/bin/env bash
# preview.sh — Convert Logseq pages and preview the site locally
#
# Usage:  ./scripts/preview.sh          (hugo server — live reload)
#         ./scripts/preview.sh --build   (static build only, no server)
#
# The preview is generated outside the git repo to avoid pollution:
#   $HOME/Downloads/_tmp/genWtao-preview/
#
# Reads:
#   graph_path.yaml     — local pointer to the Logseq graph
#   {graph}/config.yaml  — site config (hosting, hugo, theme, colors)
set -euo pipefail

# ── Paths ────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(dirname "$SCRIPT_DIR")"
GRAPH_PATH_FILE="$APP_DIR/graph_path.yaml"

HUGO_PROJECT="$APP_DIR/site"
HUGO_CONTENT="$HUGO_PROJECT/content"

PREVIEW_DIR="$HOME/Downloads/_tmp/genWtao-preview"

# ── Locate Logseq graph ──────────────────────────────────────
if [[ -z "${LOGSEQ_GRAPH:-}" ]]; then
    LOGSEQ_GRAPH=$(python3 -c "
import yaml, os
with open('$GRAPH_PATH_FILE') as f:
    c = yaml.safe_load(f)
p = c.get('graph_path', '')
print(os.path.expandvars(os.path.expanduser(p)))
")
fi

CONFIG="$LOGSEQ_GRAPH/config.yaml"

# ── Utility functions ────────────────────────────────────────
log()  { echo ""; echo "▶ $*"; }
ok()   { echo "  ✅ $*"; }
fail() { echo "  ❌ $*"; exit 1; }

# ── Pre-flight checks ────────────────────────────────────────
log "Checking environment"

command -v hugo    >/dev/null 2>&1 || fail "Hugo not installed. Run: brew install hugo"
command -v python3 >/dev/null 2>&1 || fail "Python3 required"

[[ -d "$LOGSEQ_GRAPH" ]] || fail "Logseq graph not found: $LOGSEQ_GRAPH"
[[ -d "$HUGO_PROJECT" ]] || fail "Hugo project not found: $HUGO_PROJECT"

ok "Environment OK (graph: $LOGSEQ_GRAPH)"

# ── Step 1: Export Logseq → Hugo ─────────────────────────────
log "Step 1/2: Export Logseq → Hugo"

python3 "$SCRIPT_DIR/logseq_to_hugo.py" \
    --graph  "$LOGSEQ_GRAPH" \
    --output "$HUGO_CONTENT" \
    --config "$CONFIG" \
    --clean

ok "Export done"

# ── Step 2: Preview ──────────────────────────────────────────
mkdir -p "$PREVIEW_DIR"

if [[ "${1:-}" == "--build" ]]; then
    log "Step 2/2: Static build → $PREVIEW_DIR"
    cd "$HUGO_PROJECT"
    rm -rf "$PREVIEW_DIR"/*
    hugo --minify --destination "$PREVIEW_DIR"
    PAGES=$(find "$PREVIEW_DIR" -name "*.html" | wc -l | tr -d ' ')
    ok "Build done — $PAGES pages in $PREVIEW_DIR"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📂  Preview built: $PREVIEW_DIR"
    echo "    Open index.html or run:"
    echo "    cd $PREVIEW_DIR && python3 -m http.server 1313"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
else
    log "Step 2/2: Live preview (hugo server)"
    cd "$HUGO_PROJECT"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "👁️  Preview: http://localhost:1313/"
    echo "    Press Ctrl+C to stop"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    hugo server --disableFastRender --navigateToChanged
fi
