#!/usr/bin/env python3
"""
logseq_to_hugo.py
Converts Logseq pages to Hugo Markdown files.

Usage (v0.8):
    python3 logseq_to_hugo.py [--clean]
    python3 logseq_to_hugo.py --graph /path/to/graph --clean

    graph_path is read from graph_path.yaml. Config is auto-loaded from {graph}/config.yaml.

Logseq page properties (v0.5 model — 3 properties):
    type::   page | article | collection | form
    menu::   section name from sitemap.md (cv, blog, contact…)
    lang::   language code (fr, en, zh-tw)

Two configuration files:
    --config  Engine config (graph_path, theme, colors, hosting, hugo, languages) — gitignored.

Supported Logseq syntax:
    [[Page]]                          → [Page](/lang/section/slug/) if published, plain text otherwise
    [Custom]([[Page]])                → [Custom](/lang/section/slug/) if published, plain text otherwise
    #Tag                              → [#Tag](/lang/tags/tag/) + tags in front matter
    #[[Tag Name]]                     → [#Tag Name](/lang/tags/tag-name/) + tags in front matter
    [^n] / [^n]: text                 → <sup><a href="#fn-n">n</a></sup> / <span id="fn-n"> in-place
    ^^text^^                          → <mark>text</mark>
    ==text==                          → <mark>text</mark>
    ../assets/img.ext                 → /assets/img.ext
    ![alt](path){:height H, :width W} → <img src="path" width="W">
    {{video|embed https://...}}        → platform embed (YouTube, Odysee, Maps, Mastodon, Bluesky, PDF)
    #+BEGIN_NOTE ... #+END_NOTE       → emoji-styled blockquote
    collapsed:: / id::                → removed (Logseq internal)
    logo:: ![]()                      → key removed, image value kept
    configurable internal keys        → see logseq_internal_keys in config.yaml
"""

import os
import re
import sys
import shutil
import argparse
from datetime import datetime
from pathlib import Path

# ──────────────────────────────────────────────
TODAY = datetime.today().strftime('%Y-%m-%d')

# Valid type:: values (v0.5 model — behavioural, not section-specific)
VALID_TYPES = {'page', 'article', 'collection', 'form'}

# Legacy Logseq type → Hugo section mapping (v0.4 compat)
# Used when a page has type:: cv instead of type:: page + menu:: cv
DEFAULT_SECTIONS = {
    'home':    '',
    'cv':      'cv',
    'post':    'blog',
    'blog':    'blog',
    'curious': 'curious',
    'contact': 'contact',
    'project': 'project',
    'page':    '',
}

# Logseq internal keys stripped by default
# Can be overridden via "logseq_internal_keys:" in config.yaml
DEFAULT_INTERNAL_KEYS = {
    'collapsed', 'id', 'background-color', 'heading',
    'card-last-reviewed', 'card-next-schedule',
    'card-last-score', 'card-ease-factor', 'card-repeats',
    'card-last-interval', 'logseq.order-list-type',
}

# Logseq/Org admonition type → emoji
ADMONITION_ICONS = {
    'NOTE':      '📝',
    'TIP':       '💡',
    'WARNING':   '⚠️',
    'CAUTION':   '🚨',
    'IMPORTANT': '❗',
    'EXAMPLE':   '📋',
    'QUOTE':     '💬',
    'PINNED':    '📌',
}


# Default front matter param names (PaperMod).
# Overridden by theme_params: in config.yaml.
DEFAULT_THEME_PARAMS = {
    'toc':       'ShowToc',
    'toc_open':  'TocOpen',
    'show_tags': 'ShowTags',
}

def load_graph_path_yaml():
    """Read graph_path from graph_path.yaml at the app root."""
    app_root = Path(__file__).resolve().parent.parent
    gp_file = app_root / 'graph_path.yaml'
    if not gp_file.exists():
        return None
    try:
        import yaml
        with open(gp_file, encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
        raw = data.get('graph_path', '')
        if raw:
            return os.path.expandvars(os.path.expanduser(raw))
    except Exception:
        pass
    return None


def load_config(config_path):
    """
    Load engine configuration from config.yaml (in the graph root).
    Returns a dict with keys: valid_types, legacy_sections,
    logseq_internal_keys, theme_params, colors, color_vars, languages, etc.
    """
    defaults = {
        'graph_path':           None,
        'valid_types':          set(VALID_TYPES),
        'legacy_sections':      dict(DEFAULT_SECTIONS),
        'logseq_internal_keys': set(DEFAULT_INTERNAL_KEYS),
        'theme_params':         dict(DEFAULT_THEME_PARAMS),
        'colors':               {},
        'color_vars':           {},
        'languages':            {},
        'hugo':                 {},
        'hosting':              {},
        'journal_articles':     False,
    }
    if not config_path:
        return defaults
    try:
        import yaml
        with open(config_path, encoding='utf-8') as f:
            cfg = yaml.safe_load(f)
        tp = dict(DEFAULT_THEME_PARAMS)
        tp.update(cfg.get('theme_params', {}))
        vt = cfg.get('valid_types', list(VALID_TYPES))
        return {
            'graph_path':  cfg.get('graph_path', None),
            'valid_types': set(v.lower() for v in vt),
            'legacy_sections': cfg.get('legacy_sections', cfg.get('sections', DEFAULT_SECTIONS)),
            'logseq_internal_keys': set(
                k.lower() for k in cfg.get('logseq_internal_keys', list(DEFAULT_INTERNAL_KEYS))
            ),
            'theme_params': tp,
            'colors':    cfg.get('colors', {}),
            'color_vars': cfg.get('color_vars', {}),
            'languages': cfg.get('languages', {}),
            'hugo':      cfg.get('hugo', {}),
            'hosting':   cfg.get('hosting', {}),
            'journal_articles': cfg.get('journal_articles', False),
        }
    except Exception as e:
        print(f"  ⚠️  Config not loaded ({e}), using defaults.", file=sys.stderr)
        return defaults


# ──────────────────────────────────────────────
# SITEMAP.MD PARSER
# ──────────────────────────────────────────────

def load_sitemap(graph_dir):
    """
    Parse pages/sitemap.md from the Logseq graph.

    Expected format (Logseq outline):
        - section_name
            - slug:: value
            - fr:: Label FR
            - en:: Label EN

    Returns a list of dicts:
        [{'section': 'cv', 'slug': 'cv', 'labels': {'fr': 'Expériences', 'en': 'Experiences', ...}}, ...]
    """
    sitemap_path = Path(graph_dir) / 'pages' / 'sitemap.md'
    if not sitemap_path.exists():
        return None

    text = sitemap_path.read_text(encoding='utf-8')
    entries = []
    current = None

    for line in text.splitlines():
        stripped = line.strip()
        # Skip properties block at top
        if re.match(r'^\w[\w_-]*::\s', stripped):
            continue

        # Top-level bullet: section name (e.g. "- cv")
        top_match = re.match(r'^- (\w[\w-]*)$', stripped)
        if top_match:
            if current:
                entries.append(current)
            current = {'section': top_match.group(1), 'slug': top_match.group(1), 'labels': {}}
            continue

        # Sub-bullet with property (e.g. "  - fr:: Expériences")
        # Use original line to detect indentation (tab or spaces before "- ")
        if current and re.match(r'^[\t ]+- ', line):
            sub_match = re.match(r'^(\w[\w-]*)::[ \t]*(.*)', stripped.lstrip('- '))
            if sub_match:
                key = sub_match.group(1).lower()
                val = sub_match.group(2).strip()
                if key == 'slug':
                    current['slug'] = val
                elif key == 'mode':
                    current['mode'] = val
                elif key == 'provider':
                    current['provider'] = val
                elif key == 'form_id':
                    current['form_id'] = val
                else:
                    current['labels'][key] = val

    if current:
        entries.append(current)

    return entries if entries else None


def sitemap_to_sections(sitemap_entries):
    """Convert sitemap entries to a sections dict (type → Hugo folder)
    and a set of collection types (multi-page sections)."""
    sections = {}
    collection_types = set()
    for entry in sitemap_entries:
        section = entry['section']
        slug = entry['slug']
        if section == 'home':
            sections[section] = ''
        else:
            sections[section] = slug if slug else section
        if entry.get('mode', '').lower() == 'collection':
            collection_types.add(section)
    return sections, collection_types


def inject_contact_provider(sitemap_entries, hugo_block):
    """Inject contact_provider from sitemap into hugo.yaml params.

    Reads provider:: on the contact section in sitemap.md and writes
    it to hugo_block['params']['contact_provider'] so the Hugo template
    can switch form behaviour per provider.
    """
    if not sitemap_entries or not hugo_block:
        return
    for entry in sitemap_entries:
        if entry['section'] == 'contact' and 'provider' in entry:
            if 'params' not in hugo_block:
                hugo_block['params'] = {}
            hugo_block['params']['contact_provider'] = entry['provider']
            if 'form_id' in entry:
                hugo_block['params']['contact_form_id'] = entry['form_id']
            print(f'  📧 Contact provider: {entry["provider"]}')
            return


def sitemap_to_menus(sitemap_entries, hugo_block):
    """Inject menu entries into hugo_block languages from sitemap data."""
    if not hugo_block or 'languages' not in hugo_block:
        return

    for lang_code, lang_cfg in hugo_block['languages'].items():
        menu_items = []
        weight = 10
        for entry in sitemap_entries:
            if entry['section'] == 'home':
                continue  # home is not a menu item, it's the site root
            label = entry['labels'].get(lang_code, entry['labels'].get('en', entry['section'].title()))
            slug = entry['slug'] if entry['slug'] else entry['section']
            menu_items.append({
                'name': label,
                'identifier': f"{lang_code.replace('-', '')}-{entry['section']}",
                'url': f"/{lang_code}/{slug}/",
                'weight': weight,
            })
            weight += 10
        if menu_items:
            if 'menu' not in lang_cfg:
                lang_cfg['menu'] = {}
            lang_cfg['menu']['main'] = menu_items


def generate_i18n_from_sitemap(sitemap_entries, hugo_site_dir):
    """Generate/update i18n YAML files with nav_ keys from sitemap."""
    import yaml as _yaml
    i18n_dir = Path(hugo_site_dir) / 'i18n'
    i18n_dir.mkdir(parents=True, exist_ok=True)

    # Collect all languages referenced in the sitemap
    all_langs = set()
    for entry in sitemap_entries:
        all_langs.update(entry['labels'].keys())

    for lang in all_langs:
        # Hugo i18n uses zh-TW (not zh-tw) for the filename
        filename = lang if lang.islower() and '-' not in lang else lang
        if lang == 'zh-tw':
            filename = 'zh-TW'
        filepath = i18n_dir / f'{filename}.yaml'

        # Load existing i18n content to preserve non-nav keys
        existing = {}
        if filepath.exists():
            existing = _yaml.safe_load(filepath.read_text(encoding='utf-8')) or {}

        # Add/update nav_ keys from sitemap
        for entry in sitemap_entries:
            nav_key = f"nav_{entry['section']}"
            label = entry['labels'].get(lang, entry['labels'].get('en', entry['section'].title()))
            existing[nav_key] = {'other': label}

        filepath.write_text(
            '# Auto-updated by logseq_to_hugo.py — nav_ keys from sitemap.md\n'
            + _yaml.dump(existing, allow_unicode=True, default_flow_style=False, sort_keys=True),
            encoding='utf-8',
        )
    print(f'🗺️  Generated i18n nav labels from sitemap.md ({len(all_langs)} language(s))')


# ──────────────────────────────────────────────
# WIDGETS SYSTEM
# ──────────────────────────────────────────────

def load_widgets(graph_dir):
    """
    Parse pages/widgets.md from the Logseq graph.

    Expected format:
        - widget_name
            - service:: buymeacoffee
            - slug:: shamantao
            - color:: #40DCA5

    Returns a dict: {'widget_name': {'service': 'buymeacoffee', 'slug': 'shamantao', ...}}
    """
    widgets_path = Path(graph_dir) / 'pages' / 'widgets.md'
    if not widgets_path.exists():
        return {}

    text = widgets_path.read_text(encoding='utf-8')
    widgets = {}
    current_name = None
    current_props = {}

    for line in text.splitlines():
        stripped = line.strip()
        # Skip page properties block at top
        if re.match(r'^\w[\w_-]*::\s', stripped):
            continue

        # Top-level bullet: widget name
        top_match = re.match(r'^- (\w[\w-]*)$', stripped)
        if top_match:
            if current_name:
                widgets[current_name] = current_props
            current_name = top_match.group(1)
            current_props = {}
            continue

        # Sub-bullet with property
        if current_name and re.match(r'^[\t ]+- ', line):
            sub_match = re.match(r'^([\w][\w-]*)::[ \t]*(.*)', stripped.lstrip('- '))
            if sub_match:
                current_props[sub_match.group(1).lower()] = sub_match.group(2).strip()

    if current_name:
        widgets[current_name] = current_props

    return widgets


def render_widget(name, props):
    """Render a widget dict to HTML based on its service type."""
    service = props.get('service', 'html')

    if service == 'buymeacoffee':
        slug = props.get('slug', '')
        return (
            f'<script type="text/javascript"'
            f' src="https://cdnjs.buymeacoffee.com/1.0.0/button.prod.min.js"'
            f' data-name="bmc-button"'
            f' data-slug="{slug}"'
            f' data-color="{props.get("color", "#40DCA5")}"'
            f' data-emoji="{props.get("emoji", "☕")}"'
            f' data-font="{props.get("font", "Cookie")}"'
            f' data-text="{props.get("text", "Buy me a coffee")}"'
            f' data-outline-color="{props.get("outline-color", "#000000")}"'
            f' data-font-color="{props.get("font-color", "#ffffff")}"'
            f' data-coffee-color="{props.get("coffee-color", "#FFDD00")}"'
            f'></script>'
        )

    if service == 'youtube':
        vid = props.get('id', '')
        return '{{' + f'< youtube {vid} >' + '}}'

    if service == 'image':
        src = props.get('src', '')
        src = re.sub(r'\.\.[\/\\]assets[\/\\]', '/assets/', src)
        alt = props.get('alt', '')
        width = props.get('width', '')
        parts = [f'src="{src}"']
        if alt:   parts.append(f'alt="{alt}"')
        if width: parts.append(f'width="{width}"')
        return f'<img {" ".join(parts)}>'

    if service == 'html':
        return props.get('html', f'<!-- widget "{name}": no html property -->')

    return f'<!-- unknown widget service "{service}" for "{name}" -->'


def apply_widgets(text, widgets):
    """Replace all {{widget name}} placeholders in text with rendered HTML."""
    if not widgets:
        return text

    def replace_widget(m):
        name = m.group(1).strip()
        if name in widgets:
            return render_widget(name, widgets[name])
        return f'<!-- widget "{name}" not found in widgets.md -->'

    return re.sub(r'\{\{widget\s+(\w[\w-]*)\s*\}\}', replace_widget, text)


# ──────────────────────────────────────────────
# THEME COLOR CSS GENERATOR
# ──────────────────────────────────────────────

def generate_languages_data(languages, hugo_static_parent, config_was_loaded):
    """
    Generate site/data/languages.yaml from config.yaml languages: block.

    The file is read by the header partial to display flag + name in the
    language switcher. It is gitignored (generated output).

    Keys must match Hugo language codes (e.g. fr, en, zh-tw).
    Special key 'display' (abbr|name|flag|flag_name) controls the switcher format.

    If config was not loaded (--config missing), the existing file is kept
    untouched to avoid silently erasing the language settings.
    """
    import yaml as _yaml
    data_dir = Path(hugo_static_parent) / 'data'
    out_path = data_dir / 'languages.yaml'

    if not config_was_loaded:
        if out_path.exists():
            print('  ℹ️  --config not provided — keeping existing data/languages.yaml unchanged.')
        else:
            print('  ⚠️  --config not provided and no data/languages.yaml found — language switcher will use fallback.')
        return

    data_dir.mkdir(parents=True, exist_ok=True)

    if not languages:
        out_path.write_text('# No languages: block defined in config.yaml\n', encoding='utf-8')
        print('  ℹ️  No languages defined in config — data/languages.yaml left empty.')
        return

    # Separate the display mode from the per-language entries
    display = languages.get('display', 'flag_name')
    lang_entries = {k: v for k, v in languages.items() if k != 'display'}

    output = {'display': display}
    output.update(lang_entries)

    out_path.write_text(
        '# Auto-generated by logseq_to_hugo.py — edit config.yaml languages: instead\n'
        + _yaml.dump(output, allow_unicode=True, default_flow_style=False),
        encoding='utf-8',
    )
    print(f'🇯 Generated data/languages.yaml ({len(lang_entries)} language(s), display: {display})')


# ──────────────────────────────────────────────
# HUGO CONFIG GENERATOR
# ──────────────────────────────────────────────

def generate_hugo_yaml(hugo_block, hosting, languages, hugo_site_dir, config_was_loaded):
    """
    Generate site/hugo.yaml from config.yaml hugo: block.

    The file is the main Hugo configuration. It is gitignored because
    it contains personal data (site title, base URL, etc.).

    baseURL is automatically derived from hosting.site_url.
    weight, languageName, and contentDir are auto-filled from the
    top-level languages: block when not explicitly set in hugo.languages.

    If config was not loaded (--config missing), the existing file is kept
    untouched to avoid breaking the Hugo build.
    """
    import yaml as _yaml
    out_path = Path(hugo_site_dir) / 'hugo.yaml'

    if not config_was_loaded:
        if out_path.exists():
            print('  ℹ️  --config not provided — keeping existing hugo.yaml unchanged.')
        else:
            print('  ⚠️  --config not provided and no hugo.yaml found — Hugo build will fail.')
        return

    if not hugo_block:
        print('  ℹ️  No hugo: block in config — skipping hugo.yaml generation.')
        return

    # Auto-fill hugo.languages from top-level languages: block
    if 'languages' in hugo_block and languages:
        weight = 1
        for lang_code, lang_cfg in hugo_block['languages'].items():
            top = languages.get(lang_code, {})
            if 'weight' not in lang_cfg:
                lang_cfg['weight'] = weight
                weight += 1
            if 'languageName' not in lang_cfg and 'name' in top:
                lang_cfg['languageName'] = top['name']
            if 'contentDir' not in lang_cfg:
                lang_cfg['contentDir'] = f'content/{lang_code}'

    # Derive baseURL from hosting.site_url
    site_url = hosting.get('site_url', '')
    if site_url:
        hugo_block['baseURL'] = site_url.rstrip('/') + '/'

    out_path.write_text(
        '# Auto-generated by logseq_to_hugo.py — edit config.yaml hugo: instead\n'
        + _yaml.dump(hugo_block, allow_unicode=True, default_flow_style=False, sort_keys=False),
        encoding='utf-8',
    )
    title = hugo_block.get('title', '(untitled)')
    theme = hugo_block.get('theme', '(none)')
    print(f'📝 Generated hugo.yaml (title: "{title}", theme: {theme})')


def generate_theme_colors_css(colors, color_vars, hugo_static_dir):
    """
    Generate site/static/css/theme-colors.css from config.yaml colors: and color_vars:.

    The output file is loaded by extend_head.html at build time.
    It is gitignored (generated output, like site/content/).

    Architecture:
      colors:      semantic names (background, surface, text_primary...)  ← theme-agnostic values
      color_vars:  semantic name → CSS variable name for the active theme  ← theme-specific mapping

    Switching themes = update color_vars: only.
    """
    css_dir  = Path(hugo_static_dir) / 'css'
    css_dir.mkdir(parents=True, exist_ok=True)
    out_path = css_dir / 'theme-colors.css'

    if not colors or not color_vars:
        # Write an empty placeholder so the <link> in extend_head.html never 404s
        out_path.write_text(
            '/* theme-colors.css — no colors: block defined in config.yaml */\n',
            encoding='utf-8',
        )
        print('  ℹ️  No colors defined in config — theme-colors.css left empty.')
        return

    lines = [
        '/* Auto-generated by logseq_to_hugo.py — edit config.yaml colors: instead */',
        '',
    ]
    # PaperMod uses :root for light mode and .dark class for dark mode
    for mode, selector in [('light', ':root'), ('dark', '.dark')]:
        mode_colors = colors.get(mode, {})
        if not mode_colors:
            continue
        lines.append(f'{selector} {{')
        for semantic_key, css_var in color_vars.items():
            value = mode_colors.get(semantic_key)
            if value:
                lines.append(f'    {css_var}: {value};')
        lines.append('}')
        lines.append('')

    out_path.write_text('\n'.join(lines), encoding='utf-8')
    print(f'🎨 Generated theme-colors.css ({len(color_vars)} variable(s), light + dark)')


# ──────────────────────────────────────────────
# CONVERSION HELPERS
# ──────────────────────────────────────────────

def convert_admonitions(text):
    """
    Converts #+BEGIN_X...#+END_X blocks to styled Hugo blockquotes.

        #+BEGIN_NOTE
        Content
        #+END_NOTE
        →
        > **📝 NOTE**
        >
        > Content
    """
    def replace(m):
        kind    = m.group(1).upper()
        content = m.group(2).strip()
        icon    = ADMONITION_ICONS.get(kind, 'ℹ️')
        body    = '\n'.join(f'> {line}' for line in content.splitlines())
        return f'> **{icon} {kind}**\n>\n{body}'
    return re.sub(
        r'#\+BEGIN_(\w+)\n(.*?)\n#\+END_\1',
        replace, text, flags=re.DOTALL | re.IGNORECASE,
    )


def convert_image_with_size(m):
    """
    Converts ![alt](path){:height H, :width W} to an HTML <img> tag.

    Only width is applied: the browser calculates height automatically,
    preserving aspect ratio and avoiding distortion.
    If only height is provided (no width), it is used instead.
    """
    alt   = m.group(1)
    path  = m.group(2)
    attrs = m.group(3)
    path  = re.sub(r'\.\.[\/\\]assets[\/\\]', '/assets/', path)
    h = re.search(r':height\s+(\d+)', attrs)
    w = re.search(r':width\s+(\d+)',  attrs)
    parts = [f'src="{path}"']
    if alt: parts.append(f'alt="{alt}"')
    # Width alone preserves aspect ratio; fall back to height if no width
    if w:   parts.append(f'width="{w.group(1)}"')
    elif h: parts.append(f'height="{h.group(1)}"')
    return f'<img {" ".join(parts)}>'


def convert_media_embed(m):
    """{{video|embed url}} → platform-specific HTML embed."""
    url = m.group(1).strip()

    # YouTube → Hugo native shortcode
    yt = re.search(r'(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]+)', url)
    if yt:
        return '{{' + f'< youtube {yt.group(1)} >' + '}}'

    # Odysee → iframe
    od = re.search(r'odysee\.com/(.+)', url)
    if od:
        embed_url = f'https://odysee.com/$/embed/{od.group(1)}'
        return _responsive_iframe(embed_url)

    # Google Maps → iframe (share link or embed link)
    if re.search(r'google\.\w+/maps|maps\.google\.\w+|maps\.app\.goo\.gl', url):
        # maps share URLs work directly as iframe src with /embed
        gm = re.search(r'google\.\w+/maps/(?:place|embed|dir|search)/([^?\s]+)', url)
        if gm:
            embed_url = re.sub(r'/maps/(place|dir|search)/', '/maps/embed/v1/\\1/', url.split('?')[0])
        else:
            embed_url = url
        return _responsive_iframe(embed_url, padding='60%')

    # Mastodon → iframe (instance.tld/@user/id format)
    masto = re.search(r'(https?://[^/]+/@\w+/\d+)', url)
    if masto and not re.search(r'(twitter|x|bsky|youtube|odysee)\.', url):
        return _responsive_iframe(f'{masto.group(1)}/embed', padding='auto', fixed_height='400px')

    # Bluesky → embed via bsky.app post URL
    bsky = re.search(r'bsky\.app/profile/([^/]+)/post/([a-z0-9]+)', url)
    if bsky:
        return _responsive_iframe(
            f'https://embed.bsky.app/embed/{bsky.group(1)}/app.bsky.feed.post/{bsky.group(2)}',
            padding='auto', fixed_height='450px',
        )

    # PDF → inline viewer
    if url.lower().endswith('.pdf') or 'pdf' in url.lower().split('?')[0].rsplit('.', 1)[-1:]:
        return (
            f'<iframe src="{url}" '
            'style="width:100%;height:600px;border:1px solid #ccc;border-radius:4px;">'
            '</iframe>'
        )

    # Fallback: HTML5 video tag
    return f'<video src="{url}" controls style="max-width:100%;"></video>'


def _responsive_iframe(src, padding='56.25%', fixed_height=None):
    """Generate a responsive iframe wrapper."""
    if fixed_height:
        return (
            f'<iframe src="{src}" '
            f'style="width:100%;height:{fixed_height};border:0;border-radius:4px;" '
            'allowfullscreen></iframe>'
        )
    return (
        f'<div style="position:relative;padding-bottom:{padding};height:0;overflow:hidden;">'
        f'<iframe src="{src}" style="position:absolute;top:0;left:0;width:100%;height:100%;border:0;" '
        'allowfullscreen></iframe></div>'
    )


def extract_tags(text):
    """Extract all #Tags and #[[Tag Name]] from content body (for Hugo front matter)."""
    # Skip the properties block at the top
    body = re.split(r'\n(?![\w_-]+::)', text, maxsplit=1)[-1]
    # Remove markdown link URLs to avoid false positives (e.g. https://.../#fragment)
    body_no_urls = re.sub(r'\]\([^)]+\)', ']()', body)
    # Simple #Tag
    simple = re.findall(r'(?<![#\w\["])#(\w[\w/-]*)', body_no_urls)
    # #[[Tag Name]] with spaces
    bracketed = re.findall(r'#\[\[([^\]]+)\]\]', body_no_urls)
    return sorted(set(simple + bracketed))


def _resolve_page_link(page_name, page_index):
    """Resolve a Logseq [[Page Name]] to a Hugo URL using the page index.

    Returns the URL string '/lang/section/slug/' if the page is published,
    or None if the page is not in the index (not published).
    """
    if not page_index:
        return None
    entry = page_index.get(page_name)
    if not entry:
        return None
    lang = entry['lang']
    section = entry['section']
    slug = entry['slug']
    if section:
        return f'/{lang}/{section}/{slug}/'
    return f'/{lang}/{slug}/'


def apply_inline_conversions(line, lang, page_index=None):
    """Apply all inline conversions to a single content line."""
    # Sized images → HTML <img>
    line = re.sub(
        r'!\[([^\]]*)\]\(([^)]+)\)\{([^}]+)\}',
        convert_image_with_size, line,
    )
    # Plain asset paths → Hugo rewrite
    line = re.sub(r'\.\.[\/\\]assets[\/\\]', '/assets/', line)
    # Highlight ^^text^^ → <mark>
    line = re.sub(r'\^\^(.+?)\^\^', r'<mark>\1</mark>', line)
    # Highlight ==text== → <mark>
    line = re.sub(r'==(.+?)==', r'<mark>\1</mark>', line)
    # Footnote references [^n] → clickable anchor (but NOT definitions [^n]:)
    line = re.sub(
        r'\[\^(\w+)\](?!:)',
        lambda m: f'<sup><a href="#fn-{m.group(1)}">{m.group(1)}</a></sup>',
        line,
    )
    # Footnote definitions [^n]: text → anchor target in-place
    line = re.sub(
        r'\[\^(\w+)\]:\s*',
        lambda m: f'<span id="fn-{m.group(1)}"></span>',
        line,
    )
    # [Custom text]([[Page Name]]) → resolved link or plain text
    def _replace_custom_link(m):
        display = m.group(1)
        page_name = m.group(2)
        url = _resolve_page_link(page_name, page_index)
        if url:
            return f'[{display}]({url})'
        return display
    line = re.sub(r'\[([^\]]+)\]\(\[\[([^\]]+)\]\]\)', _replace_custom_link, line)
    # #[[Tag Name]] → Hugo taxonomy link (must come before [[Page]] handling)
    def _replace_bracketed_tag(m):
        tag = m.group(1)
        slug = re.sub(r'[^\w-]', '-', tag.lower()).strip('-')
        return f'[#{tag}](/{lang}/tags/{slug}/)'
    line = re.sub(r'#\[\[([^\]]+)\]\]', _replace_bracketed_tag, line)
    # [[Page Name]] references → resolved link or plain text
    def _replace_page_link(m):
        page_name = m.group(1)
        url = _resolve_page_link(page_name, page_index)
        if url:
            return f'[{page_name}]({url})'
        return page_name
    line = re.sub(r'\[\[([^\]]+)\]\]', _replace_page_link, line)
    # #Tags → Hugo taxonomy link
    # Protect markdown link URLs from being matched: temporarily replace ](url) sections
    _link_urls = []
    def _stash_url(m):
        _link_urls.append(m.group(1))
        return f'](\x00LINK{len(_link_urls) - 1}\x00)'
    line = re.sub(r'\]\(([^)]+)\)', _stash_url, line)
    # Now apply #Tag conversion safely (no URLs to pollute)
    line = re.sub(
        r'(?<![#\w\["])#(\w[\w/-]*)',
        lambda m: f'[#{m.group(1)}](/{lang}/tags/{m.group(1).lower()}/)',
        line,
    )
    # Restore stashed URLs
    def _restore_url(m):
        return f']({_link_urls[int(m.group(1))]})'
    line = re.sub(r'\]\(\x00LINK(\d+)\x00\)', _restore_url, line)
    return line


# ──────────────────────────────────────────────
# LOGSEQ PROPERTIES PARSER
# ──────────────────────────────────────────────

def parse_logseq_properties(text):
    """Extract key:: value properties from the top of a Logseq page."""
    props = {}
    for line in text.splitlines():
        m = re.match(r'^(\w[\w_-]*)::[ \t]*(.*)', line.strip())
        if m:
            props[m.group(1).lower()] = m.group(2).strip()
        elif line.strip() and not line.startswith('-'):
            break  # end of properties block
    return props


# ──────────────────────────────────────────────
# LOGSEQ CONTENT → HUGO MARKDOWN CONVERTER
# ──────────────────────────────────────────────

def convert_content(text, internal_keys, lang='fr', widgets=None, page_index=None):
    """
    Converts a Logseq page body to Hugo-compatible Markdown/HTML.

    Processing order:
    1. Admonitions #+BEGIN_X...#+END_X (multi-line, global pass)
    2. Media embeds {{video|embed url}} (multi-line)
    3. Widget placeholders {{widget name}} (multi-line)
    4. Line by line:
       a. Skip the properties block at the top
       b. Remove internal metadata (collapsed::, id::)
       c. Logseq bullets → Markdown; inline properties → value or drop
       d. Inline conversions (images, assets, highlight, footnotes, refs, tags)
    """
    # ── Global multi-line passes ─────────────────────────────────────
    text = convert_admonitions(text)
    text = re.sub(
        r'\{\{(?:video|youtube|embed)\s+(https?://[^\}]+)\}\}',
        convert_media_embed, text,
    )
    lines    = text.splitlines()
    output   = []
    in_props = True

    for line in lines:
        # Skip the properties block at the top of the file
        if in_props:
            if re.match(r'^\w[\w_-]*::[ \t]', line.strip()) or line.strip() == '':
                continue
            else:
                in_props = False

        # Always strip collapsed:: and id:: (Logseq serialized metadata)
        if re.match(r'\s*collapsed::\s*(true|false)', line):
            continue
        if re.match(r'\s*id::\s+[a-f0-9-]{8}', line):
            continue

        # Empty Logseq bullet: bare "-" with no content → blank line
        if re.match(r'^\t*-\s*$', line):
            output.append('')
            continue

        # Logseq bullets
        indent_match = re.match(r'^(\t*)(- |\s{4})(.*)', line)
        if indent_match:
            tabs    = len(indent_match.group(1))
            content = indent_match.group(3)

            # Inline property inside a bullet: "key:: value"
            prop_m = re.match(r'^(\w[\w_-]*)::[ \t]*(.*)', content.strip())
            if prop_m:
                key = prop_m.group(1).lower()
                val = prop_m.group(2).strip()
                if key in internal_keys:
                    continue          # Internal key → drop entirely
                else:
                    content = val     # Custom key (logo::, cover::...) → keep value only

            content = apply_inline_conversions(content, lang, page_index=page_index)
            line    = content if tabs == 0 else ('  ' * (tabs - 1)) + '- ' + content
        else:
            # Non-bullet lines (headings ##, blockquotes >, paragraphs...)
            line = apply_inline_conversions(line, lang, page_index=page_index)

        output.append(line)

    # Ensure blank lines before and after <img> and <video> blocks.
    # goldmark requires blank lines around raw HTML to render it correctly.
    spaced = []
    for i, ln in enumerate(output):
        if re.match(r'^\s*<(?:img|video)\s', ln):
            if spaced and spaced[-1].strip() != '':
                spaced.append('')
            spaced.append(ln)
            spaced.append('')
        else:
            spaced.append(ln)
    output = spaced

    # Collapse runs of more than 2 consecutive blank lines
    cleaned, blank_count = [], 0
    for line in output:
        if line.strip() == '':
            blank_count += 1
            if blank_count <= 2:
                cleaned.append(line)
        else:
            blank_count = 0
            cleaned.append(line)

    result = '\n'.join(cleaned).strip()
    # Apply widgets AFTER all inline conversions so that HTML inside
    # widgets (e.g. hex colours like #40DCA5) is not mangled by the
    # Logseq #tag → link conversion.
    result = apply_widgets(result, widgets)
    return result


# ──────────────────────────────────────────────
# HUGO FRONT MATTER BUILDER
# ──────────────────────────────────────────────

def resolve_props(props, source_file, sections_map, valid_types, legacy_sections):
    """Resolve auto-deduced properties and normalise the v0.5 / legacy model.

    Detects whether the page uses the new model (menu:: present) or the
    legacy model (type:: is a section name).  Populates internal keys
    _title, _slug, _translationkey, _section, _page_type used by
    build_front_matter and output_path.

    Returns a list of validation warnings (empty = OK).
    """
    warnings = []
    raw_type = props.get('type', '').strip().lower()
    raw_menu = props.get('menu', '').strip().lower()

    # --- Detect model ------------------------------------------------
    if raw_menu:
        # New v0.5 model: type:: is behavioural, menu:: is the section
        page_type = raw_type if raw_type else 'page'
        section   = raw_menu
        if page_type not in valid_types:
            warnings.append(f"type:: inconnu '{page_type}' (attendu: {sorted(valid_types)})")
    elif raw_type in valid_types:
        # Explicit v0.5 without menu:: (e.g. type:: page with no menu → root)
        page_type = raw_type
        section   = ''
    elif raw_type and raw_type in legacy_sections:
        # Legacy v0.4 model: type:: is actually a section name
        page_type = 'page'
        section   = raw_type
    elif raw_type and raw_type in sections_map:
        # type:: matches a sitemap section directly
        page_type = 'page'
        section   = raw_type
    elif raw_type:
        # Unknown type, treat as section for backward compat but warn
        page_type = 'page'
        section   = raw_type
        warnings.append(f"type:: '{raw_type}' n'est ni un type valide ni une section connue")
    else:
        # No type at all → skip this page (will be filtered out)
        page_type = ''
        section   = ''

    # --- Auto-deduce title, slug, translationKey ----------------------
    title = props.get('title', Path(source_file).stem)
    slug  = props.get('slug', re.sub(r'[^\w-]', '-', title.lower()).strip('-'))

    # translationKey: explicit wins, else auto
    tk = props.get('translationkey', '')
    if not tk:
        if page_type == 'article':
            tk = slug
        else:
            tk = section if section else slug

    # --- Store resolved values in props (prefixed with _) -------------
    props['_title']          = title
    props['_slug']           = slug
    props['_translationkey'] = tk
    props['_section']        = section
    props['_page_type']      = page_type

    return warnings


def build_front_matter(props, source_file, tags=None, theme_params=None):
    """Build Hugo YAML front matter from Logseq page properties.

    v0.5 model: type:: is behavioural (page/article/collection/form),
    menu:: is the section. Auto-derives title, slug, translationKey.

    Retrocompat: if no menu:: is present, falls back to v0.4 behaviour
    where type:: is the section name directly.
    """
    if theme_params is None:
        theme_params = DEFAULT_THEME_PARAMS

    # Resolved properties (set by resolve_props before calling this)
    title   = props.get('_title', Path(source_file).stem)
    section = props.get('_section', '')
    slug    = props.get('_slug', re.sub(r'[^\w-]', '-', title.lower()))
    tk      = props.get('_translationkey', '')
    ptype   = props.get('_page_type', 'page')  # behavioural type

    date  = props.get('date', TODAY)
    # Normalise partial dates: "2011" → "2011-01-01", "2011-03" → "2011-03-01"
    if re.match(r'^\d{4}$', date):
        date = f'{date}-01-01'
    elif re.match(r'^\d{4}-\d{2}$', date):
        date = f'{date}-01'
    desc  = props.get('description', '')
    order = props.get('menu_order', '')

    toc = props.get('toc', 'false').lower() in ('true', '1', 'yes')

    # Hugo type = section name (not the behavioural type)
    hugo_type = section if section else 'page'

    fm = ['---', f'title: "{title}"', f'slug: "{slug}"', f'type: "{hugo_type}"', f'date: {date}']
    if desc:  fm.append(f'description: "{desc}"')
    if order: fm.append(f'weight: {order}')
    if tk:    fm.append(f'translationKey: "{tk}"')
    if toc and theme_params.get('toc'):      fm.append(f"{theme_params['toc']}: true")
    if toc and theme_params.get('toc_open'): fm.append(f"{theme_params['toc_open']}: true")
    if tags:  fm.append('tags: [' + ', '.join(f'"{t}"' for t in tags) + ']')
    fm.append('---')
    return '\n'.join(fm)


# ──────────────────────────────────────────────
# HUGO OUTPUT PATH RESOLVER
# ──────────────────────────────────────────────

def output_path(props, output_dir, sections_map, collection_types=None):
    """Resolve the output path inside content/<lang>/<section>/.

    Uses resolved props (_section, _slug, _page_type) set by resolve_props().
    """
    lang    = props.get('lang', 'fr').lower().replace('_', '-')  # zh-TW → zh-tw
    section = props.get('_section', '')
    slug    = props.get('_slug', 'page')
    ptype   = props.get('_page_type', 'page')

    # Map section name to Hugo folder via sitemap/legacy
    folder = sections_map.get(section, section)
    if folder:
        dir_path = Path(output_dir) / lang / folder
    else:
        dir_path = Path(output_dir) / lang

    # article type → individual file; everything else → _index.md
    if ptype == 'article':
        filename = f'{slug}.md'
    else:
        filename = '_index.md'

    return dir_path / filename


# ──────────────────────────────────────────────
# JOURNAL BLOCK EXTRACTION
# ──────────────────────────────────────────────

def extract_journal_blocks(journal_file):
    """Extract publishable blocks from a Logseq journal file.

    Scans top-level bullets (``- ...``) for block-level ``type::`` properties.
    Returns a list of ``(page_text, source_label)`` tuples where *page_text*
    is reconstructed as if it were a standalone Logseq page so it can be fed
    directly into ``process_file(..., text=page_text)``.

    Date is auto-deduced from the journal filename (``2026_03_28.md`` →
    ``2026-03-28``) unless ``date::`` is set explicitly in the block.
    """
    text = Path(journal_file).read_text(encoding='utf-8')
    if not text.strip():
        return []

    # Derive date from filename: 2026_03_28.md → 2026-03-28
    stem = Path(journal_file).stem
    journal_date = stem.replace('_', '-')

    # Split into top-level blocks (lines starting with "- " at column 0)
    blocks = []
    current_block = []
    for line in text.splitlines():
        if line.startswith('- '):
            if current_block:
                blocks.append(current_block)
            current_block = [line]
        else:
            current_block.append(line)
    if current_block:
        blocks.append(current_block)

    results = []
    for block_lines in blocks:
        # First line: strip "- " prefix
        first_line = block_lines[0][2:]

        props = {}
        first_line_text = None

        # Check if first line itself is a property
        m = re.match(r'^(\w[\w_-]*)::[ \t]*(.*)', first_line.strip())
        if m:
            props[m.group(1).lower()] = m.group(2).strip()
        else:
            first_line_text = first_line

        content_lines = []

        # Process remaining lines
        for line in block_lines[1:]:
            # Block properties: 2-space indent + key:: value
            prop_match = re.match(r'^  (\w[\w_-]*)::[ \t]*(.*)', line)
            if prop_match and not content_lines:
                # Properties must come before any content lines
                props[prop_match.group(1).lower()] = prop_match.group(2).strip()
                continue
            # Tab-indented child properties: \t- key:: val or \t  key:: val
            if not content_lines and line.startswith('\t'):
                child_prop = re.match(r'^\t[\- ]{0,2}(\w[\w_-]*)::[ \t]*(.*)', line)
                if child_prop:
                    props[child_prop.group(1).lower()] = child_prop.group(2).strip()
                    continue
            if line.startswith('\t'):
                # Child content: remove one leading tab
                content_lines.append(line[1:])
            elif line.strip() == '':
                content_lines.append('')
            else:
                content_lines.append(line)

        # Only process blocks that have type::
        if not props.get('type'):
            continue

        # Auto-set date from journal filename if not explicitly set
        if 'date' not in props:
            props['date'] = journal_date
        else:
            # Normalise Logseq date links: [[Mar 31st, 2026]] → 2026-03-31
            raw_date = props['date'].strip('[]')
            cleaned = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', raw_date)
            try:
                from dateutil.parser import parse as _date_parse
                props['date'] = _date_parse(cleaned).strftime('%Y-%m-%d')
            except ImportError:
                from datetime import datetime as _dt
                try:
                    props['date'] = _dt.strptime(cleaned, '%b %d, %Y').strftime('%Y-%m-%d')
                except ValueError:
                    props['date'] = journal_date
            except Exception:
                props['date'] = journal_date

        # Use first line text as title if no explicit title:: property
        if first_line_text and 'title' not in props:
            # Strip Logseq link brackets: [[My Title]] → My Title
            title = re.sub(r'\[\[([^\]]+)\]\]', r'\1', first_line_text).strip()
            if title:
                props['title'] = title

        # Reconstruct as page text (properties at top, then content)
        page_lines = []
        for k, v in props.items():
            page_lines.append(f'{k}:: {v}')
        page_lines.append('')  # separator
        page_lines.extend(content_lines)

        page_text = '\n'.join(page_lines)
        slug = props.get('slug', props.get('title', stem))
        source_label = f"{Path(journal_file).name}:{slug}"
        results.append((page_text, source_label))

    return results


# ──────────────────────────────────────────────
# PAGE INDEX (2-pass link resolution)
# ──────────────────────────────────────────────

def build_page_index(pages_dir, sections_map, valid_types=None, legacy_sections=None,
                     journals_dir=None, journal_articles_enabled=False):
    """Build an index of all publishable pages for [[Page]] link resolution.

    Pass 1: scan all pages/ (and optionally journals/) to collect
    {page_name: {lang, section, slug}} for every page that has type::.

    Returns a dict keyed by the Logseq page name (= filename without .md).
    """
    _valid  = valid_types or VALID_TYPES
    _legacy = legacy_sections or DEFAULT_SECTIONS
    index = {}

    # Index pages/
    for md_file in sorted(pages_dir.glob('*.md')):
        text = md_file.read_text(encoding='utf-8')
        props = parse_logseq_properties(text)
        if not props.get('type', '').strip():
            continue
        resolve_props(props, md_file, sections_map, _valid, _legacy)
        page_name = md_file.stem
        lang    = props.get('lang', 'fr').lower()
        section = sections_map.get(props.get('_section', ''), props.get('_section', ''))
        slug    = props.get('_slug', '')
        index[page_name] = {'lang': lang, 'section': section, 'slug': slug}

    # Index journal articles
    if journal_articles_enabled and journals_dir and journals_dir.exists():
        for journal_file in sorted(journals_dir.glob('*.md')):
            for page_text, source_label in extract_journal_blocks(journal_file):
                props = parse_logseq_properties(page_text)
                if not props.get('type', '').strip():
                    continue
                resolve_props(props, journal_file, sections_map, _valid, _legacy)
                title = props.get('_title', journal_file.stem)
                lang    = props.get('lang', 'fr').lower()
                section = sections_map.get(props.get('_section', ''), props.get('_section', ''))
                slug    = props.get('_slug', '')
                index[title] = {'lang': lang, 'section': section, 'slug': slug}

    return index


# ──────────────────────────────────────────────
# FILE PROCESSOR
# ──────────────────────────────────────────────

def process_file(src_path, output_dir, sections_map, internal_keys, theme_params=None,
                  widgets=None, collection_types=None, valid_types=None, legacy_sections=None,
                  text=None, page_index=None):
    if text is None:
        text = Path(src_path).read_text(encoding='utf-8')
    props = parse_logseq_properties(text)

    # v0.5: a page is publishable when type:: is defined (replaces public:: true)
    if not props.get('type', '').strip():
        return None, []

    _valid  = valid_types or VALID_TYPES
    _legacy = legacy_sections or DEFAULT_SECTIONS
    warnings = resolve_props(props, src_path, sections_map, _valid, _legacy)

    lang         = props.get('lang', 'fr').lower()
    tags         = extract_tags(text)
    front_matter = build_front_matter(props, src_path, tags=tags or None, theme_params=theme_params)
    body         = convert_content(text, internal_keys, lang=lang, widgets=widgets, page_index=page_index)
    hugo_content = front_matter + '\n\n' + body

    out = output_path(props, output_dir, sections_map, collection_types=collection_types)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(hugo_content, encoding='utf-8')
    return str(out), warnings


# ──────────────────────────────────────────────
# ENTRY POINT
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Convert a Logseq graph to Hugo content')
    parser.add_argument('--graph',  default=None, help='Logseq graph root folder (default: from graph_path.yaml)')
    parser.add_argument('--output', default=None, help='Hugo content/ folder (default: site/content)')
    parser.add_argument('--config', default=None,  help='Path to config.yaml (default: {graph}/config.yaml)')
    parser.add_argument('--clean',  action='store_true', help='Remove output folder before export')
    args = parser.parse_args()

    # 1. Resolve graph directory: CLI > graph_path.yaml > error
    if args.graph:
        graph_dir = Path(os.path.expandvars(os.path.expanduser(args.graph)))
    else:
        gp = load_graph_path_yaml()
        if gp:
            graph_dir = Path(gp)
        else:
            print("❌ No graph path: use --graph or create graph_path.yaml", file=sys.stderr)
            sys.exit(1)

    # 2. Resolve config path: CLI > {graph}/config.yaml
    config_path = args.config
    if not config_path:
        candidate = graph_dir / 'config.yaml'
        if candidate.exists():
            config_path = str(candidate)

    # 3. Load engine config
    cfg            = load_config(config_path)
    valid_types    = cfg['valid_types']
    legacy_sections = cfg['legacy_sections']
    internal_keys  = cfg['logseq_internal_keys']
    theme_params   = cfg['theme_params']
    colors         = cfg['colors']
    color_vars     = cfg['color_vars']

    # Resolve output_dir: CLI > default (site/content)
    if args.output:
        output_dir = Path(args.output)
    else:
        output_dir = Path(__file__).resolve().parent.parent / 'site' / 'content'

    if not graph_dir.exists():
        print(f"❌ Graph folder not found: {graph_dir}", file=sys.stderr)
        sys.exit(1)

    # Load personal site config (languages, hugo, hosting — from config.yaml)
    languages  = cfg.get('languages', {})
    hugo_block = cfg.get('hugo', {})
    hosting    = cfg.get('hosting', {})

    # Load sitemap.md from Logseq graph (overrides sections + generates menus/i18n)
    sitemap_entries = load_sitemap(graph_dir)
    sections_map    = dict(legacy_sections)
    collection_types = set()
    if sitemap_entries:
        sm_sections, collection_types = sitemap_to_sections(sitemap_entries)
        # Sitemap takes priority, legacy fills gaps
        for alias, target in sections_map.items():
            if alias not in sm_sections:
                sm_sections[alias] = target
                if target in collection_types:
                    collection_types.add(alias)
        sections_map = sm_sections
        sitemap_to_menus(sitemap_entries, hugo_block)
        inject_contact_provider(sitemap_entries, hugo_block)
        print(f'🗺️  Sitemap loaded: {len(sitemap_entries)} section(s) from pages/sitemap.md')
        if collection_types:
            print(f'  📚 Collection types (multi-page): {sorted(collection_types)}')
    else:
        print('  ℹ️  No sitemap.md found — using legacy_sections from config.yaml')

    # Load widgets.md from Logseq graph
    widgets = load_widgets(graph_dir)
    if widgets:
        print(f'🧩 Widgets loaded: {list(widgets.keys())} from pages/widgets.md')
    else:
        print('  ℹ️  No widgets.md found — {{widget ...}} placeholders will not be replaced')

    print(f"  ℹ️  Sections: {list(sections_map.keys())}")
    print(f"  ℹ️  Valid types: {sorted(valid_types)}")
    print(f"  ℹ️  Theme params: {theme_params}")

    if args.clean and output_dir.exists():
        shutil.rmtree(output_dir)
        print(f"🧹 Cleaned output folder: {output_dir}")

    pages_dir = graph_dir / 'pages'
    if not pages_dir.exists():
        print(f"❌ No 'pages' folder found in {graph_dir}", file=sys.stderr)
        sys.exit(1)

    # Copy Logseq assets → site/static/assets/
    assets_src  = graph_dir / 'assets'
    static_dest = output_dir.parent / 'static' / 'assets'
    if assets_src.exists():
        static_dest.mkdir(parents=True, exist_ok=True)
        copied_assets = 0
        for asset_file in assets_src.iterdir():
            if asset_file.is_file():
                shutil.copy2(asset_file, static_dest / asset_file.name)
                copied_assets += 1
        print(f"🖼️  Copied {copied_assets} asset(s): {assets_src} → {static_dest}")
    else:
        print(f"  ℹ️  No assets folder found in {graph_dir}")

    # Generate hugo.yaml from config.yaml hugo: block
    config_was_loaded = config_path is not None
    generate_hugo_yaml(hugo_block, hosting, languages, output_dir.parent, config_was_loaded)

    # Generate theme-colors.css from config.yaml colors: and color_vars:
    hugo_static = output_dir.parent / 'static'
    generate_theme_colors_css(colors, color_vars, hugo_static)

    # Generate data/languages.yaml from config.yaml languages:
    generate_languages_data(languages, output_dir.parent, config_was_loaded=config_was_loaded)

    # Generate i18n nav labels from sitemap.md
    if sitemap_entries:
        generate_i18n_from_sitemap(sitemap_entries, output_dir.parent)

    exported    = []
    skipped     = []
    all_warnings = []

    # ── Pass 1: build page index for [[Page]] link resolution ─────────
    journal_articles_enabled = cfg.get('journal_articles', False)
    journals_dir = graph_dir / 'journals'
    page_index = build_page_index(
        pages_dir, sections_map,
        valid_types=valid_types, legacy_sections=legacy_sections,
        journals_dir=journals_dir, journal_articles_enabled=journal_articles_enabled,
    )
    if page_index:
        print(f"🔗 Page index: {len(page_index)} publishable page(s) indexed for link resolution")

    # ── Pass 2: convert and export ────────────────────────────────────
    for md_file in sorted(pages_dir.glob('*.md')):
        result, warnings = process_file(
            md_file, output_dir, sections_map, internal_keys,
            theme_params=theme_params, widgets=widgets,
            collection_types=collection_types,
            valid_types=valid_types, legacy_sections=legacy_sections,
            page_index=page_index)
        if result:
            exported.append(result)
            print(f"  ✅ {md_file.name} → {result}")
            if warnings:
                for w in warnings:
                    print(f"     ⚠️  {w}")
                all_warnings.extend((md_file.name, w) for w in warnings)
        else:
            skipped.append(md_file.name)

    # ── Journal articles (optional) ──────────────────────────────────
    journal_exported = []
    if journal_articles_enabled:
        journals_dir = graph_dir / 'journals'
        if journals_dir.exists():
            print(f"\n📓 Scanning journal entries for articles…")
            known_slugs = {Path(p).stem for p in exported if '/blog/' in p or '/curious/' in p}
            for journal_file in sorted(journals_dir.glob('*.md')):
                for page_text, source_label in extract_journal_blocks(journal_file):
                    result, warnings = process_file(
                        journal_file, output_dir, sections_map, internal_keys,
                        theme_params=theme_params, widgets=widgets,
                        collection_types=collection_types,
                        valid_types=valid_types, legacy_sections=legacy_sections,
                        text=page_text, page_index=page_index)
                    if result:
                        # Check slug conflict: pages/ wins over journals/
                        result_slug = Path(result).stem
                        if result_slug in known_slugs:
                            print(f"  ⏭️  {source_label} → slug '{result_slug}' already exists in pages/, skipped")
                            continue
                        known_slugs.add(result_slug)
                        journal_exported.append(result)
                        print(f"  ✅ {source_label} → {result}")
                        if warnings:
                            for w in warnings:
                                print(f"     ⚠️  {w}")
                            all_warnings.extend((source_label, w) for w in warnings)
            if journal_exported:
                print(f"  📓 {len(journal_exported)} article(s) from journals")
            else:
                print(f"  ℹ️  No journal articles found (no top-level bullet with type::)")
        else:
            print(f"\n  ℹ️  No journals/ folder found in {graph_dir}")
    exported.extend(journal_exported)

    print(f"\n📤 Export done: {len(exported)} page(s) exported, {len(skipped)} skipped (no type:: defined)")
    if skipped:
        print(f"   Skipped: {', '.join(skipped)}")
    if all_warnings:
        print(f"\n⚠️  {len(all_warnings)} warning(s):")
        for fname, w in all_warnings:
            print(f"   {fname}: {w}")


if __name__ == '__main__':
    main()

