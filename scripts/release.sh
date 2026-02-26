#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# release.sh — Commit, tag, and push a new version
#
# Usage:
#   ./scripts/release.sh "Your commit message"
#   ./scripts/release.sh                        # opens $EDITOR for message
#
# What it does:
#   1. Reads version from config/config.yaml (committed engine config)
#   2. Stages all modified tracked files + new untracked files
#   3. Commits with your message (prefixed with version)
#   4. Creates an annotated git tag v<version>
#   5. Pushes commit + tag to origin
#
# To bump the version: edit config/config.yaml line 1 BEFORE running.
# ─────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(dirname "$SCRIPT_DIR")"
cd "$APP_DIR"

CONFIG_CFG="config/config.yaml"

# ── Read version ──────────────────────────────────────────────
if [[ ! -f "$CONFIG_CFG" ]]; then
    echo "❌ $CONFIG_CFG not found" >&2
    exit 1
fi

VERSION=$(grep -m1 '^version:' "$CONFIG_CFG" | sed 's/version:[[:space:]]*//')
if [[ -z "$VERSION" ]]; then
    echo "❌ No version: found in $CONFIG_CFG" >&2
    exit 1
fi

TAG="v$VERSION"
echo "📦 Version: $VERSION  →  tag: $TAG"

# ── Check tag doesn't already exist ──────────────────────────
if git tag -l "$TAG" | grep -q "$TAG"; then
    echo "❌ Tag $TAG already exists. Bump version in $CONFIG_CFG first." >&2
    exit 1
fi

# ── Commit message ────────────────────────────────────────────
if [[ $# -ge 1 ]]; then
    MSG="$1"
else
    # Open editor for multi-line message
    TMPFILE=$(mktemp)
    echo "# Write your commit message for $TAG below:" > "$TMPFILE"
    echo "" >> "$TMPFILE"
    ${EDITOR:-vi} "$TMPFILE"
    MSG=$(grep -v '^#' "$TMPFILE" | sed '/^$/d')
    rm -f "$TMPFILE"
    if [[ -z "$MSG" ]]; then
        echo "❌ Empty commit message — aborting." >&2
        exit 1
    fi
fi

FULL_MSG="$TAG: $MSG"

# ── Stage, commit, tag, push ─────────────────────────────────
echo ""
echo "▶ Staging changes..."
git add -A

# Check there is something to commit
if git diff --cached --quiet; then
    echo "  ℹ️  Nothing to commit — creating tag only."
else
    echo "▶ Committing: $FULL_MSG"
    git commit -m "$FULL_MSG"
fi

echo "▶ Tagging: $TAG"
git tag -a "$TAG" -m "$FULL_MSG"

if git remote get-url origin >/dev/null 2>&1; then
    echo "▶ Pushing to origin..."
    git push origin main --tags
else
    echo "  ⚠️  No 'origin' remote configured — skipping push."
    echo "     Run: git remote add origin <url> && git push origin main --tags"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀  Released $TAG"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
