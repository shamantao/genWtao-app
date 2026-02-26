#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# publish.sh — Pipeline complet genWtao
# Usage :  ./scripts/publish.sh
# Mobile : via iOS Shortcuts → SSH → ce script
# ─────────────────────────────────────────────────────────────
set -euo pipefail

# ── Chemins ──────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(dirname "$SCRIPT_DIR")"
CONFIG="$APP_DIR/config/config.yaml"

LOGSEQ_GRAPH="/Users/phil/Library/CloudStorage/Dropbox/logseq/genWtao"
HUGO_PROJECT="$APP_DIR/site"
HUGO_CONTENT="$HUGO_PROJECT/content"
HUGO_PUBLIC="$HUGO_PROJECT/public"

FTP_HOST="ftpupload.net"
FTP_USER="if0_41224106"
FTP_REMOTE="/htdocs"
SITE_URL="https://genwtao.free.nf"

# Mot de passe FTP : depuis variable d'environnement ou fichier .env local
if [[ -f "$APP_DIR/.env" ]]; then
    source "$APP_DIR/.env"
fi
FTP_PASSWORD="${FTP_PASSWORD:-}"

# ── Fonctions utilitaires ─────────────────────────────────────
log()  { echo ""; echo "▶ $*"; }
ok()   { echo "  ✅ $*"; }
fail() { echo "  ❌ $*"; exit 1; }

# ── Vérifications préalables ─────────────────────────────────
log "Vérification de l'environnement"

command -v hugo   >/dev/null 2>&1 || fail "Hugo non installé. Lance : brew install hugo"
command -v python3 >/dev/null 2>&1 || fail "Python3 requis"

[[ -d "$LOGSEQ_GRAPH" ]]   || fail "Graph Logseq introuvable : $LOGSEQ_GRAPH"
[[ -d "$HUGO_PROJECT" ]]   || fail "Projet Hugo introuvable : $HUGO_PROJECT"
[[ -n "$FTP_PASSWORD" ]]   || fail "FTP_PASSWORD non défini. Crée $APP_DIR/.env avec FTP_PASSWORD=tonmotdepasse"

ok "Environnement OK"

# ── Étape 1 : Export Logseq → Hugo ───────────────────────────
log "Étape 1/3 : Export Logseq → Hugo"

python3 "$SCRIPT_DIR/logseq_to_hugo.py" \
    --graph  "$LOGSEQ_GRAPH" \
    --output "$HUGO_CONTENT" \
    --config "$CONFIG" \
    --clean

ok "Export terminé"

# ── Étape 2 : Build Hugo ──────────────────────────────────────
log "Étape 2/3 : Build Hugo"

cd "$HUGO_PROJECT"
rm -rf "$HUGO_PUBLIC"
hugo --minify --logLevel warn

PAGES=$(find "$HUGO_PUBLIC" -name "*.html" | wc -l | tr -d ' ')
ok "Build terminé — $PAGES pages générées"

# ── Étape 3 : Upload FTP ─────────────────────────────────────
log "Étape 3/3 : Upload FTP → $SITE_URL"

if command -v lftp >/dev/null 2>&1; then
    lftp -c "
        set ftp:ssl-allow no;
        open ftp://$FTP_USER:$FTP_PASSWORD@$FTP_HOST;
        mirror --reverse --delete --verbose=1 $HUGO_PUBLIC $FTP_REMOTE
    "
elif command -v curl >/dev/null 2>&1; then
    # Fallback curl si lftp absent (plus lent)
    find "$HUGO_PUBLIC" -type f | while read -r file; do
        REMOTE_PATH="${file#$HUGO_PUBLIC}"
        curl -s --ftp-create-dirs -T "$file" \
            "ftp://$FTP_USER:$FTP_PASSWORD@$FTP_HOST$FTP_REMOTE$REMOTE_PATH" || true
    done
else
    fail "lftp ou curl requis pour le déploiement FTP"
fi

ok "Upload FTP terminé"

# ── Résumé ────────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀  Site publié : $SITE_URL"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
