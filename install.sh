#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────
# install.sh — First-time setup for genWtao
#
# What it does:
#   1. Asks for the Logseq graph path
#   2. Generates graph_path.yaml (local pointer to the graph)
#   3. Copies config.example.yaml to the graph root as config.yaml
#   4. Creates template pages in the graph: sitemap.md, colors.md,
#      widgets.md, 404.md (skips if they already exist)
# ──────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

CONFIG_EXAMPLE="config.example.yaml"
GRAPH_PATH_FILE="graph_path.yaml"
GRAPH_PATH_EXAMPLE="graph_path.example.yaml"

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

# ── 2. Generate graph_path.yaml ──────────────────────────────
if [[ ! -f "$GRAPH_PATH_EXAMPLE" ]]; then
    echo "❌ $GRAPH_PATH_EXAMPLE not found. Are you in the genWtao-app root?" >&2
    exit 1
fi

if [[ -f "$GRAPH_PATH_FILE" ]]; then
    echo "⚠️  $GRAPH_PATH_FILE already exists."
    read -r -p "   Overwrite? [y/N]: " confirm
    if [[ ! "$confirm" =~ ^[yY]$ ]]; then
        echo "   Skipped graph_path.yaml generation."
        echo ""
    else
        sed "s|graph_path:.*|graph_path: $GRAPH_PATH|" "$GRAPH_PATH_EXAMPLE" > "$GRAPH_PATH_FILE"
        echo "✅ $GRAPH_PATH_FILE updated with your graph path."
        echo ""
    fi
else
    sed "s|graph_path:.*|graph_path: $GRAPH_PATH|" "$GRAPH_PATH_EXAMPLE" > "$GRAPH_PATH_FILE"
    echo "✅ $GRAPH_PATH_FILE created."
    echo ""
fi

# ── 3. Copy config.example.yaml to graph ─────────────────────
GRAPH_CONFIG="$GRAPH_EXPANDED/config.yaml"

if [[ ! -f "$CONFIG_EXAMPLE" ]]; then
    echo "❌ $CONFIG_EXAMPLE not found. Are you in the genWtao-app root?" >&2
    exit 1
fi

if [[ -f "$GRAPH_CONFIG" ]]; then
    echo "ℹ️  config.yaml already exists in graph — skipped."
else
    cp "$CONFIG_EXAMPLE" "$GRAPH_CONFIG"
    echo "✅ config.yaml copied to graph root."
fi
echo ""

# ── 3. Create template pages in graph ───────────────────────
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
create_if_missing "colors.md" "- title:: Colors
  public:: false

- # Theme Colors
- Define your site colors here. The engine reads this file and generates theme-colors.css.
- Uncomment and adapt the values below. Remove the \`# \` at the start of each line to activate.
- light
	- # background:: #FFFFFF
	- # text_primary:: #1a1a1a
	- # text_secondary:: #6c6c6c
	- # surface:: #f4f4f5
	- # accent:: #0070f3
- dark
	- # background:: #1d1e20
	- # text_primary:: #dadada
	- # text_secondary:: #9b9c9d
	- # surface:: #2e2e33
	- # accent:: #3b82f6
- vars
	- # background:: --body-background
	- # text_primary:: --primary
	- # text_secondary:: --secondary
	- # surface:: --entry
	- # accent:: --tertiary"

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
echo "  1. Edit config.yaml in your graph: set hosting URL, FTP host/user, Hugo config, languages"
echo "  2. Edit the template pages in $PAGES_DIR"
echo "  3. On GitHub: set repository variable GRAPH_REPO = owner/your-graph-repo"
echo "  4. On GitHub: set secrets GH_TOKEN, FTP_PASSWORD"
echo "  5. Run: python3 scripts/logseq_to_hugo.py --clean"
echo ""
