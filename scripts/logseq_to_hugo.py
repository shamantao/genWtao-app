#!/usr/bin/env python3
"""
logseq_to_hugo.py
Converts Logseq pages (with public:: true) to Hugo Markdown files.

Usage:
    python3 logseq_to_hugo.py --graph <graph_folder> --output <hugo_content_folder>
    python3 logseq_to_hugo.py --graph <graph_folder> --output <hugo_content_folder> \
                              --config <config/config.yaml> --site <site.yaml> [--clean]

Two configuration files:
    --config  Engine config (sections, theme, colors) — committed, shared.
    --site    Personal site config (languages, hugo, hosting) — private, in Logseq graph.

Supported Logseq syntax:
    [[Page]]                          → plain text
    #Tag                              → [#Tag](/lang/tags/tag/) + tags in front matter
    ^^text^^                          → <mark>text</mark>
    ../assets/img.ext                 → /assets/img.ext
    ![alt](path){:height H, :width W} → <img src="path" width="W">
    {{video https://...}}             → Hugo youtube shortcode or <video> tag
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

# Default Logseq type → Hugo section mapping
# Can be overridden via "sections:" in config.yaml
DEFAULT_SECTIONS = {
    'home':    '',
    'cv':      'cv',
    'post':    'blog',
    'blog':    'blog',
    'curious': 'curious',
    'contact': 'contact',
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

def load_config(config_path):
    """
    Load engine configuration from config/config.yaml.
    Returns a dict with 'sections', 'logseq_internal_keys', 'theme_params',
    'colors', and 'color_vars'.  No personal data.
    """
    defaults = {
        'sections':             DEFAULT_SECTIONS,
        'logseq_internal_keys': set(DEFAULT_INTERNAL_KEYS),
        'theme_params':         dict(DEFAULT_THEME_PARAMS),
        'colors':               {},
        'color_vars':           {},
    }
    if not config_path:
        return defaults
    try:
        import yaml
        with open(config_path, encoding='utf-8') as f:
            cfg = yaml.safe_load(f)
        tp = dict(DEFAULT_THEME_PARAMS)
        tp.update(cfg.get('theme_params', {}))
        return {
            'sections': cfg.get('sections', DEFAULT_SECTIONS),
            'logseq_internal_keys': set(
                k.lower() for k in cfg.get('logseq_internal_keys', list(DEFAULT_INTERNAL_KEYS))
            ),
            'theme_params': tp,
            'colors':    cfg.get('colors', {}),
            'color_vars': cfg.get('color_vars', {}),
        }
    except Exception as e:
        print(f"  ⚠️  Config not loaded ({e}), using defaults.", file=sys.stderr)
        return defaults


def load_site_config(site_path):
    """
    Load personal site configuration from site.yaml (lives in Logseq graph).
    Returns a dict with 'languages', 'hugo', and 'hosting'.
    """
    defaults = {
        'languages': {},
        'hugo':      {},
        'hosting':   {},
    }
    if not site_path:
        return defaults
    try:
        import yaml
        with open(site_path, encoding='utf-8') as f:
            cfg = yaml.safe_load(f)
        return {
            'languages': cfg.get('languages', {}),
            'hugo':      cfg.get('hugo', {}),
            'hosting':   cfg.get('hosting', {}),
        }
    except Exception as e:
        print(f"  ⚠️  Site config not loaded ({e}), using defaults.", file=sys.stderr)
        return defaults


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

def generate_hugo_yaml(hugo_block, hosting, hugo_site_dir, config_was_loaded):
    """
    Generate site/hugo.yaml from config.yaml hugo: block.

    The file is the main Hugo configuration. It is gitignored because
    it contains personal data (site title, base URL, etc.).

    baseURL is automatically derived from hosting.site_url.

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


def convert_video_embed(m):
    """{{video url}} → Hugo youtube shortcode or <video> tag."""
    url = m.group(1).strip()
    yt  = re.search(r'(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]+)', url)
    if yt:
        return '{{' + f'< youtube {yt.group(1)} >' + '}}'
    return f'<video src="{url}" controls></video>'


def extract_tags(text):
    """Extract all #Tags from content body (for Hugo front matter)."""
    # Skip the properties block at the top
    body = re.split(r'\n(?![\w_-]+::)', text, maxsplit=1)[-1]
    return sorted(set(re.findall(r'(?<![#\w])#(\w[\w/-]*)', body)))


def apply_inline_conversions(line, lang):
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
    # [[Page Name]] references → plain text
    line = re.sub(r'#?\[\[([^\]]+)\]\]', r'\1', line)
    # #Tags → Hugo taxonomy link
    line = re.sub(
        r'(?<![#\w])#(\w[\w/-]*)',
        lambda m: f'[#{m.group(1)}](/{lang}/tags/{m.group(1).lower()}/)',
        line,
    )
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

def convert_content(text, internal_keys, lang='fr'):
    """
    Converts a Logseq page body to Hugo-compatible Markdown/HTML.

    Processing order:
    1. Admonitions #+BEGIN_X...#+END_X (multi-line, global pass)
    2. Video embeds {{video url}} (multi-line)
    3. Line by line:
       a. Skip the properties block at the top
       b. Remove internal metadata (collapsed::, id::)
       c. Logseq bullets → Markdown; inline properties → value or drop
       d. Inline conversions (images, assets, highlight, refs, tags)
    """
    # ── Global multi-line passes ─────────────────────────────────────
    text = convert_admonitions(text)
    text = re.sub(
        r'\{\{(?:video|youtube)\s+(https?://[^\}]+)\}\}',
        convert_video_embed, text,
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

            content = apply_inline_conversions(content, lang)
            line    = content if tabs == 0 else ('  ' * (tabs - 1)) + '- ' + content
        else:
            # Non-bullet lines (headings ##, blockquotes >, paragraphs...)
            line = apply_inline_conversions(line, lang)

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

    return '\n'.join(cleaned).strip()


# ──────────────────────────────────────────────
# HUGO FRONT MATTER BUILDER
# ──────────────────────────────────────────────

def build_front_matter(props, source_file, tags=None, theme_params=None):
    """Build Hugo YAML front matter from Logseq page properties.

    theme_params: dict mapping logical keys ('toc', 'toc_open', 'show_tags')
                  to the actual front matter param names for the active theme
                  (e.g. 'ShowToc' for PaperMod). Falls back to DEFAULT_THEME_PARAMS.
    """
    if theme_params is None:
        theme_params = DEFAULT_THEME_PARAMS

    title = props.get('title', Path(source_file).stem)
    type_ = props.get('type', 'page')
    slug  = props.get('slug', re.sub(r'[^\w-]', '-', title.lower()))
    date  = props.get('date', TODAY)
    desc  = props.get('description', '')
    order = props.get('menu_order', '')
    # translationKey:: in Logseq → lowercased by parse_logseq_properties → 'translationkey'
    # Hugo uses this to link equivalent pages across languages (language switcher)
    tk    = props.get('translationkey', '')

    toc = props.get('toc', 'false').lower() in ('true', '1', 'yes')

    fm = ['---', f'title: "{title}"', f'slug: "{slug}"', f'type: "{type_}"', f'date: {date}']
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

def output_path(props, output_dir, sections_map):
    """Resolve the output path inside content/<lang>/<section>/."""
    lang    = props.get('lang', 'fr').lower().replace('_', '-')  # zh-TW → zh-tw
    type_   = props.get('type', 'page')
    slug    = props.get('slug', 'page')
    section = sections_map.get(type_, type_)  # fallback: use the type as section name

    if section:
        dir_path = Path(output_dir) / lang / section
    else:
        dir_path = Path(output_dir) / lang

    # Blog posts get one file per article (slug.md)
    # Everything else is a section with _index.md
    if type_ in ('post', 'blog'):
        filename = f'{slug}.md'
    else:
        filename = '_index.md'

    return dir_path / filename


# ──────────────────────────────────────────────
# FILE PROCESSOR
# ──────────────────────────────────────────────

def process_file(src_path, output_dir, sections_map, internal_keys, theme_params=None):
    text  = Path(src_path).read_text(encoding='utf-8')
    props = parse_logseq_properties(text)

    if props.get('public', 'false').lower() != 'true':
        return None

    lang         = props.get('lang', 'fr').lower()
    tags         = extract_tags(text)
    front_matter = build_front_matter(props, src_path, tags=tags or None, theme_params=theme_params)
    body         = convert_content(text, internal_keys, lang=lang)
    hugo_content = front_matter + '\n\n' + body

    out = output_path(props, output_dir, sections_map)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(hugo_content, encoding='utf-8')
    return str(out)


# ──────────────────────────────────────────────
# ENTRY POINT
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Convert a Logseq graph to Hugo content')
    parser.add_argument('--graph',  required=True, help='Logseq graph root folder')
    parser.add_argument('--output', required=True, help='Hugo content/ folder')
    parser.add_argument('--config', default=None,  help='Path to config/config.yaml (engine config)')
    parser.add_argument('--site',   default=None,  help='Path to site.yaml (personal site config)')
    parser.add_argument('--clean',  action='store_true', help='Remove output folder before export')
    args = parser.parse_args()

    graph_dir  = Path(args.graph)
    output_dir = Path(args.output)

    if not graph_dir.exists():
        print(f"❌ Graph folder not found: {graph_dir}", file=sys.stderr)
        sys.exit(1)

    # Load engine config (sections, theme, colors — committed, shared)
    cfg           = load_config(args.config)
    sections_map  = cfg['sections']
    internal_keys = cfg['logseq_internal_keys']
    theme_params  = cfg['theme_params']
    colors        = cfg['colors']
    color_vars    = cfg['color_vars']

    # Load personal site config (languages, hugo, hosting — private)
    site_cfg  = load_site_config(args.site)
    languages  = site_cfg['languages']
    hugo_block = site_cfg['hugo']
    hosting    = site_cfg['hosting']

    print(f"  ℹ️  Sections: {list(sections_map.keys())}")
    print(f"  ℹ️  Ignored internal keys: {sorted(internal_keys)}")
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

    # Generate hugo.yaml from site.yaml hugo: block
    site_was_loaded = args.site is not None
    generate_hugo_yaml(hugo_block, hosting, output_dir.parent, site_was_loaded)

    # Generate theme-colors.css from config.yaml colors: and color_vars:
    hugo_static = output_dir.parent / 'static'
    generate_theme_colors_css(colors, color_vars, hugo_static)

    # Generate data/languages.yaml from site.yaml languages:
    generate_languages_data(languages, output_dir.parent, config_was_loaded=site_was_loaded)

    exported = []
    skipped  = []

    for md_file in sorted(pages_dir.glob('*.md')):
        result = process_file(md_file, output_dir, sections_map, internal_keys, theme_params=theme_params)
        if result:
            exported.append(result)
            print(f"  ✅ {md_file.name} → {result}")
        else:
            skipped.append(md_file.name)

    print(f"\n📤 Export done: {len(exported)} page(s) exported, {len(skipped)} skipped (no public:: true)")
    if skipped:
        print(f"   Skipped: {', '.join(skipped)}")


if __name__ == '__main__':
    main()

