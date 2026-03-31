#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────
# install.sh — First-time setup for genWtao
#
# What it does:
#   1. Asks for the Logseq graph path
#   2. Generates config/config.yaml from config/config.example.yaml
#   3. Copies site.example.yaml to the graph (if site.yaml doesn't exist)
#   4. Creates template pages in the graph: sitemap.md, colors.md,
#      widgets.md, 404.md (skips if they already exist)
# ──────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

CONFIG_EXAMPLE="config/config.example.yaml"
CONFIG_FILE="config/config.yaml"

# ── Helpers ───────────────────────────────────────────────────
ask() {
    local prompt="$1" default="$2" reply
    if [[ -n "$default" ]]; then
        read -r -p "$prompt [$default]: " reply
        echo "${reply:-$default}"
    else
        while true; do
            read -r -p "$prompt: " reply
            [[ -n "$reply" ]] && break
            echo "  ⚠️  This field is required." >&2
        done
        echo "$reply"
    fi
}

# ── 1. Graph path ────────────────────────────────────────────
echo ""
echo "🔧 genWtao — first-time setup"
echo "────────────────────────────────────────────"
echo ""

GRAPH_PATH=$(ask "Path to your Logseq graph folder" "")

# Expand ~ and $HOME for validation
GRAPH_EXPANDED="${GRAPH_PATH/#\~/$HOME}"
GRAPH_EXPANDED="${GRAPH_EXPANDED//\$HOME/$HOME}"

if [[ ! -d "$GRAPH_EXPANDED" ]]; then
    echo "❌ Directory not found: $GRAPH_EXPANDED" >&2
    echo "   Please create it first, or check the path." >&2
    exit 1
fi

if [[ ! -d "$GRAPH_EXPANDED/pages" ]]; then
    echo "❌ No pages/ subdirectory in $GRAPH_EXPANDED" >&2
    echo "   This doesn't look like a Logseq graph." >&2
    exit 1
fi

echo "✅ Graph found: $GRAPH_EXPANDED"
echo ""

# ── 2. Generate config.yaml ─────────────────────────────────
if [[ ! -f "$CONFIG_EXAMPLE" ]]; then
    echo "❌ $CONFIG_EXAMPLE not found. Are you in the genWtao-app root?" >&2
    exit 1
fi

if [[ -f "$CONFIG_FILE" ]]; then
    echo "⚠️  $CONFIG_FILE already exists."
    read -r -p "   Overwrite? [y/N]: " confirm
    if [[ ! "$confirm" =~ ^[yY]$ ]]; then
        echo "   Skipped config generation."
        echo ""
    else
        sed "s|graph_path:.*|graph_path: $GRAPH_PATH|" "$CONFIG_EXAMPLE" > "$CONFIG_FILE"
        echo "✅ $CONFIG_FILE updated with your graph path."
        echo ""
    fi
else
    sed "s|graph_path:.*|graph_path: $GRAPH_PATH|" "$CONFIG_EXAMPLE" > "$CONFIG_FILE"
    echo "✅ $CONFIG_FILE created."
    echo ""
fi

# ── 3. Copy site.example.yaml to graph ──────────────────────
SITE_EXAMPLE="site.example.yaml"
SITE_TARGET="$GRAPH_EXPANDED/site.yaml"

if [[ -f "$SITE_EXAMPLE" ]]; then
    if [[ -f "$SITE_TARGET" ]]; then
        echo "ℹ️  site.yaml already exists in graph — skipped."
    else
        cp "$SITE_EXAMPLE" "$SITE_TARGET"
        echo "✅ site.yaml copied to graph. Edit it with your hosting details."
    fi
else
    echo "⚠️  site.example.yaml not found — skipping site.yaml creation."
fi
echo ""

# ── 4. Create template pages in graph ───────────────────────
PAGES_DIR="$GRAPH_EXPANDED/pages"

create_if_missing() {
    local file="$PAGES_DIR/$1"
    local content="$2"
    if [[ -f "$file" ]]; then
        echo "ℹ️  $1 already exists — skipped."
    else
        printf '%s\n' "$content" > "$file"
        echo "✅ $1 created."
    fi
}

echo "Creating template pages in $PAGES_DIR …"
echo ""

# sitemap.md
create_if_missing "sitemap.md" "title:: Sitemap
public:: false

- home
	- slug::
	- fr:: Accueil
	- en:: Home
- blog
	- slug:: blog
	- mode:: collection
	- fr:: Blog
	- en:: Blog
- contact
	- slug:: contact
	- fr:: Contact
	- en:: Contact"

# colors.md
create_if_missing "colors.md" "title:: Colors
public:: false

Configure your theme colors in config/config.yaml (colors: section).
This page is a reminder — the engine reads colors from config.yaml, not from here.

- Light theme
	- background:: rgb(255, 255, 255)
	- text_primary:: rgb(30, 30, 30)
	- text_secondary:: rgb(108, 108, 108)
- Dark theme
	- background:: rgb(29, 30, 32)
	- text_primary:: rgb(218, 218, 219)
	- text_secondary:: rgb(155, 156, 157)"

# widgets.md
create_if_missing "widgets.md" "title:: Widgets
public:: false

Add widgets here. Each top-level bullet is a widget.
Inactive example (uncomment and adapt):

- # buymeacoffee
	- service:: buymeacoffee
	- slug:: your-username
	- color:: #40DCA5
	- emoji:: ☕
	- text:: Buy me a coffee"

# 404.md
create_if_missing "404.md" "title:: 404
type:: page
lang:: fr
slug:: 404

- ## Page introuvable
- L'adresse que vous avez suivie n'existe plus ou a changé.
- [Retour à l'accueil](/)"

echo ""
echo "────────────────────────────────────────────"
echo "🎉 Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Edit $CONFIG_FILE if you need to adjust settings"
echo "  2. Edit $SITE_TARGET with your hosting details"
echo "  3. Edit the template pages in $PAGES_DIR"
echo "  4. On GitHub: set repository variable GRAPH_REPO = owner/your-graph-repo"
echo "  5. On GitHub: set secrets GH_TOKEN, FTP_PASSWORD, CONTACT_FORM_ID"
echo "  6. Run: python3 scripts/logseq_to_hugo.py --graph <graph> --output site/content --config $CONFIG_FILE --site <graph>/site.yaml"
echo ""
