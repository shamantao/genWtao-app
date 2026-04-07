#!/usr/bin/env python3
"""Unit tests for logseq_to_hugo.py — EPIC 0.9.0 (Logseq advanced syntax)."""

import unittest
import sys
import tempfile
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from logseq_to_hugo import (
    apply_inline_conversions,
    extract_tags,
    convert_content,
    build_page_index,
    build_front_matter,
    parse_logseq_properties,
    process_file,
    resolve_props,
    load_colors,
    DEFAULT_INTERNAL_KEYS,
    DEFAULT_SECTIONS,
    VALID_TYPES,
    _resolve_page_link,
)

# ──────────────────────────────────────────────
# Shared fixtures
# ──────────────────────────────────────────────

SAMPLE_PAGE_INDEX = {
    'Contact': {'lang': 'fr', 'section': 'contact', 'slug': 'contact'},
    'Contact me': {'lang': 'en', 'section': 'contact', 'slug': 'contact-me'},
    'Mes Projets': {'lang': 'fr', 'section': 'project', 'slug': 'mes-projets'},
    'Home-fr': {'lang': 'fr', 'section': '', 'slug': 'accueil---philippe-bertieri'},
    'Les Thés Taiwanais 臺灣🇹🇼': {'lang': 'fr', 'section': 'curious', 'slug': 'les-th-s-taiwanais-------'},
}


# ──────────────────────────────────────────────
# US-1: Footnotes + ==highlight==
# ──────────────────────────────────────────────

class TestFootnotes(unittest.TestCase):
    """US-1: Footnote references and definitions → HTML anchors."""

    def test_footnote_ref_becomes_clickable_sup(self):
        line = 'Camellia Sinensis[^1] est une plante.'
        result = apply_inline_conversions(line, 'fr')
        self.assertIn('<sup><a href="#fn-1">1</a></sup>', result)
        self.assertNotIn('[^1]', result)

    def test_footnote_def_becomes_span_anchor(self):
        line = '[^1]: ***Camellia sinensis***'
        result = apply_inline_conversions(line, 'fr')
        self.assertIn('<span id="fn-1"></span>', result)
        self.assertIn('***Camellia sinensis***', result)
        self.assertNotIn('[^1]:', result)

    def test_footnote_def_in_bullet(self):
        """Footnote definition inside a Logseq bullet preserves content."""
        text = "type:: article\nlang:: fr\nmenu:: curious\n\n- texte[^1]\n\t- [^1]: ma note"
        result = convert_content(text, DEFAULT_INTERNAL_KEYS, lang='fr')
        self.assertIn('<sup><a href="#fn-1">1</a></sup>', result)
        self.assertIn('<span id="fn-1"></span>', result)
        self.assertIn('ma note', result)

    def test_multiple_footnotes(self):
        line = 'premier[^1] et second[^2]'
        result = apply_inline_conversions(line, 'fr')
        self.assertIn('<sup><a href="#fn-1">1</a></sup>', result)
        self.assertIn('<sup><a href="#fn-2">2</a></sup>', result)

    def test_footnote_sub_bullets_preserved(self):
        """Sub-bullets after a footnote definition remain intact."""
        text = (
            "type:: article\nlang:: fr\nmenu:: curious\n\n"
            "- texte[^1]\n"
            "\t- [^1]: plante\n"
            "\t\t- sous-espèce sinensis\n"
            "\t\t- sous-espèce assamica"
        )
        result = convert_content(text, DEFAULT_INTERNAL_KEYS, lang='fr')
        self.assertIn('sous-espèce sinensis', result)
        self.assertIn('sous-espèce assamica', result)


class TestHighlight(unittest.TestCase):
    """US-1: ==text== and ^^text^^ both produce <mark>."""

    def test_double_equals_highlight(self):
        line = 'ceci est ==important== dans le texte'
        result = apply_inline_conversions(line, 'fr')
        self.assertEqual(result, 'ceci est <mark>important</mark> dans le texte')

    def test_caret_highlight_unchanged(self):
        """Regression: ^^text^^ still works."""
        line = 'ceci est ^^important^^ dans le texte'
        result = apply_inline_conversions(line, 'fr')
        self.assertEqual(result, 'ceci est <mark>important</mark> dans le texte')

    def test_mixed_highlights(self):
        line = '==first== and ^^second^^'
        result = apply_inline_conversions(line, 'fr')
        self.assertIn('<mark>first</mark>', result)
        self.assertIn('<mark>second</mark>', result)


# ──────────────────────────────────────────────
# US-2: [[Page]] → resolved links
# ──────────────────────────────────────────────

class TestPageLinks(unittest.TestCase):
    """US-2: [[Page Name]] resolves to site URL when published."""

    def test_published_page_becomes_link(self):
        line = 'Voir la page [[Contact]]'
        result = apply_inline_conversions(line, 'fr', page_index=SAMPLE_PAGE_INDEX)
        self.assertIn('[Contact](/fr/contact/contact/)', result)

    def test_unpublished_page_becomes_plain_text(self):
        line = 'Voir la page [[Page inexistante]]'
        result = apply_inline_conversions(line, 'fr', page_index=SAMPLE_PAGE_INDEX)
        self.assertIn('Page inexistante', result)
        self.assertNotIn('[[', result)
        self.assertNotIn('](', result)

    def test_page_link_with_section(self):
        line = 'Mes [[Mes Projets]] sont ici'
        result = apply_inline_conversions(line, 'fr', page_index=SAMPLE_PAGE_INDEX)
        self.assertIn('[Mes Projets](/fr/project/mes-projets/)', result)

    def test_page_link_different_lang(self):
        """[[Contact me]] (en) resolves to English URL."""
        line = 'Go to [[Contact me]]'
        result = apply_inline_conversions(line, 'en', page_index=SAMPLE_PAGE_INDEX)
        self.assertIn('[Contact me](/en/contact/contact-me/)', result)

    def test_page_link_no_index_fallback_plain(self):
        """Without page_index, [[Page]] falls back to plain text."""
        line = 'Voir [[Contact]]'
        result = apply_inline_conversions(line, 'fr', page_index=None)
        self.assertEqual(result, 'Voir Contact')

    def test_page_link_root_section(self):
        """Page with empty section → /lang/slug/."""
        line = 'Retour à [[Home-fr]]'
        result = apply_inline_conversions(line, 'fr', page_index=SAMPLE_PAGE_INDEX)
        self.assertIn('/fr/accueil---philippe-bertieri/', result)

    def test_resolve_page_link_helper(self):
        url = _resolve_page_link('Contact', SAMPLE_PAGE_INDEX)
        self.assertEqual(url, '/fr/contact/contact/')

    def test_resolve_page_link_not_found(self):
        url = _resolve_page_link('Nope', SAMPLE_PAGE_INDEX)
        self.assertIsNone(url)

    def test_page_link_unicode_normalization(self):
        """[[Page]] resolves even if source uses NFD accents and index key is NFC."""
        line = 'Lire [[Les The\u0301s Taiwanais 臺灣🇹🇼]]'
        result = apply_inline_conversions(line, 'fr', page_index=SAMPLE_PAGE_INDEX)
        self.assertIn('/fr/curious/les-th-s-taiwanais-------/', result)


class TestBuildPageIndex(unittest.TestCase):
    """US-2: build_page_index scans pages/ and builds the index."""

    def test_index_from_temp_pages(self, tmp_dir=None):
        """Build index from a temp directory with sample pages."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            pages = Path(tmpdir) / 'pages'
            pages.mkdir()
            (pages / 'MonCV.md').write_text(
                'type:: page\nlang:: fr\nmenu:: cv\n\n- contenu', encoding='utf-8'
            )
            (pages / 'NoType.md').write_text(
                'lang:: fr\n\n- pas publié', encoding='utf-8'
            )
            sections_map = {'cv': 'cv', 'blog': 'blog'}
            index = build_page_index(pages, sections_map)
            self.assertIn('MonCV', index)
            self.assertEqual(index['MonCV']['lang'], 'fr')
            self.assertEqual(index['MonCV']['section'], 'cv')
            self.assertNotIn('NoType', index)


# ──────────────────────────────────────────────
# US-3: #[[Tag Name]] → taxonomy link
# ──────────────────────────────────────────────

class TestBracketedTags(unittest.TestCase):
    """US-3: #[[Tag with spaces]] → taxonomy link + front matter."""

    def test_bracketed_tag_becomes_link(self):
        line = 'Voir #[[Mon Tag]] ici'
        result = apply_inline_conversions(line, 'fr')
        self.assertIn('[#Mon Tag](/fr/tags/mon-tag/)', result)

    def test_bracketed_tag_in_front_matter(self):
        text = "type:: article\nlang:: fr\nmenu:: blog\n\n- texte #[[Mon Tag]] ici"
        tags = extract_tags(text)
        self.assertIn('Mon Tag', tags)

    def test_simple_tag_still_works(self):
        """Regression: #Tag (no brackets) still works."""
        line = 'un #Marketing tag'
        result = apply_inline_conversions(line, 'fr')
        self.assertIn('[#Marketing](/fr/tags/marketing/)', result)

    def test_hash_in_url_not_treated_as_tag(self):
        """#fragment inside a markdown URL must NOT become a tag."""
        line = '[Terre des Thés](https://www.terre-des-thes.fr/le-theier/#faq-question-123)'
        result = apply_inline_conversions(line, 'fr')
        self.assertNotIn('/fr/tags/', result)
        self.assertIn('https://www.terre-des-thes.fr/le-theier/#faq-question-123', result)

    def test_hash_in_url_not_extracted_as_tag(self):
        """#fragment in URLs must not appear in extracted tags."""
        text = "type:: article\nlang:: fr\nmenu:: blog\n\n- [site](https://example.com/#section)"
        tags = extract_tags(text)
        self.assertNotIn('section', tags)

    def test_bracketed_tag_not_treated_as_page_link(self):
        """#[[Tag]] must NOT be resolved as a page link even if a page named 'Tag' exists."""
        page_index = {'Mon Tag': {'lang': 'fr', 'section': 'blog', 'slug': 'mon-tag'}}
        line = '#[[Mon Tag]]'
        result = apply_inline_conversions(line, 'fr', page_index=page_index)
        # Should be a tag link, not a page link
        self.assertIn('/fr/tags/mon-tag/', result)
        self.assertNotIn('/fr/blog/mon-tag/', result)


# ──────────────────────────────────────────────
# US-4: [Custom text]([[Page]]) → resolved link
# ──────────────────────────────────────────────

class TestCustomTextLinks(unittest.TestCase):
    """US-4: [display text]([[Page Name]]) → resolved link or plain text."""

    def test_custom_text_resolved(self):
        line = 'Voir [mon CV]([[Mes Projets]])'
        result = apply_inline_conversions(line, 'fr', page_index=SAMPLE_PAGE_INDEX)
        self.assertIn('[mon CV](/fr/project/mes-projets/)', result)

    def test_custom_text_unpublished_fallback(self):
        line = 'Voir [lien]([[Inexistant]])'
        result = apply_inline_conversions(line, 'fr', page_index=SAMPLE_PAGE_INDEX)
        self.assertEqual(result, 'Voir lien')
        self.assertNotIn('[[', result)

    def test_standard_markdown_link_untouched(self):
        """Standard [text](https://...) must NOT be affected."""
        line = 'Voir [Logseq](https://logseq.com)'
        result = apply_inline_conversions(line, 'fr', page_index=SAMPLE_PAGE_INDEX)
        self.assertEqual(result, 'Voir [Logseq](https://logseq.com)')


# ──────────────────────────────────────────────
# Integration: full convert_content with all features
# ──────────────────────────────────────────────

class TestConvertContentIntegration(unittest.TestCase):
    """Integration tests combining multiple v0.9 features."""

    def test_full_article_with_footnotes_and_links(self):
        text = (
            "type:: article\nlang:: fr\nmenu:: curious\n\n"
            "- Le thé *Camellia Sinensis*[^1] est populaire.\n"
            "- Voir aussi [[Mes Projets]] et #[[Mon Tag]]\n"
            "- ==important== et ^^aussi^^.\n"
            "\t- [^1]: Plante originaire de Chine\n"
            "\t\t- sous-espèce sinensis"
        )
        result = convert_content(
            text, DEFAULT_INTERNAL_KEYS, lang='fr',
            page_index=SAMPLE_PAGE_INDEX
        )
        # Footnotes
        self.assertIn('<sup><a href="#fn-1">1</a></sup>', result)
        self.assertIn('<span id="fn-1"></span>', result)
        self.assertIn('Plante originaire de Chine', result)
        self.assertIn('sous-espèce sinensis', result)
        # Page link
        self.assertIn('[Mes Projets](/fr/project/mes-projets/)', result)
        # Bracketed tag
        self.assertIn('/fr/tags/mon-tag/', result)
        # Highlights
        self.assertIn('<mark>important</mark>', result)
        self.assertIn('<mark>aussi</mark>', result)


# ──────────────────────────────────────────────
# Logseq date normalisation in front matter
# ──────────────────────────────────────────────

class TestDateNormalisation(unittest.TestCase):
    """Logseq date links [[Mon Day, Year]] must become ISO dates."""

    def _fm(self, date_val):
        props = {'_slug': 'test', '_page_type': 'article', '_translationkey': 'test',
                 'date': date_val, 'lang': 'fr', '_section': 'blog'}
        return build_front_matter(props, 'Test', tags=[], theme_params={})

    def test_logseq_date_link_normalised(self):
        fm = self._fm('[[Apr 2nd, 2026]]')
        self.assertIn('date: 2026-04-02', fm)

    def test_logseq_date_link_march(self):
        fm = self._fm('[[Mar 31st, 2026]]')
        self.assertIn('date: 2026-03-31', fm)

    def test_iso_date_unchanged(self):
        fm = self._fm('2026-04-02')
        self.assertIn('date: 2026-04-02', fm)

    def test_partial_year_normalised(self):
        fm = self._fm('2011')
        self.assertIn('date: 2011-01-01', fm)


# ──────────────────────────────────────────────
# Opt-out: public:: false / draft:: true
# ──────────────────────────────────────────────

class TestPublishOptOut(unittest.TestCase):
    """Pages with public:: false or draft:: true must not be published."""

    SECTIONS_MAP = {'blog': 'blog', 'curious': 'curious'}

    def _run(self, text):
        import tempfile, os
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, 'content')
            os.makedirs(out)
            return process_file(
                'test.md', out, self.SECTIONS_MAP, DEFAULT_INTERNAL_KEYS,
                text=text, collection_types={'blog', 'curious'},
            )

    def test_public_false_skips_page(self):
        text = 'type:: article\nmenu:: blog\nlang:: fr\ndate:: 2026-04-01\npublic:: false\n\nContent here.'
        result, _ = self._run(text)
        self.assertIsNone(result)

    def test_draft_true_skips_page(self):
        text = 'type:: article\nmenu:: blog\nlang:: fr\ndate:: 2026-04-01\ndraft:: true\n\nContent here.'
        result, _ = self._run(text)
        self.assertIsNone(result)

    def test_public_true_publishes(self):
        text = 'type:: article\nmenu:: blog\nlang:: fr\ndate:: 2026-04-01\npublic:: true\n\nContent here.'
        result, _ = self._run(text)
        self.assertIsNotNone(result)

    def test_no_opt_out_publishes(self):
        text = 'type:: article\nmenu:: blog\nlang:: fr\ndate:: 2026-04-01\n\nContent here.'
        result, _ = self._run(text)
        self.assertIsNotNone(result)


# ──────────────────────────────────────────────
# Safety net: unknown {{...}} macros
# ──────────────────────────────────────────────

class TestUnknownMacroEscape(unittest.TestCase):
    """Unrecognised {{...}} macros must be commented out, not left raw for Hugo."""

    def test_html_macro_escaped(self):
        """{{html url}} is not a recognised keyword → should become an HTML comment."""
        text = 'type:: page\nmenu:: cv\nlang:: fr\n\n- {{html https://odysee.com/@foo/bar}}'
        result = convert_content(text, DEFAULT_INTERNAL_KEYS, lang='fr')
        self.assertIn('<!-- {{html https://odysee.com/@foo/bar}} -->', result)
        # Must not appear as bare macro (outside HTML comment)
        self.assertNotIn('\n{{html', result)

    def test_video_macro_not_escaped(self):
        """{{video url}} is recognised → must NOT be commented out."""
        text = 'type:: page\nmenu:: cv\nlang:: fr\n\n- {{video https://odysee.com/@foo/bar}}'
        result = convert_content(text, DEFAULT_INTERNAL_KEYS, lang='fr')
        self.assertNotIn('<!--', result)
        self.assertIn('iframe', result)

    def test_hugo_shortcode_not_escaped(self):
        """Hugo shortcodes {{< youtube ID >}} must survive untouched."""
        text = 'type:: page\nmenu:: cv\nlang:: fr\n\n- {{video https://youtube.com/watch?v=abc123}}'
        result = convert_content(text, DEFAULT_INTERNAL_KEYS, lang='fr')
        self.assertIn('{{< youtube abc123 >}}', result)
        self.assertNotIn('<!--', result)

    def test_arbitrary_unknown_macro_escaped(self):
        """Any random {{something ...}} should be safely escaped."""
        text = 'type:: page\nmenu:: cv\nlang:: fr\n\n- {{renderer :todomaster}}'
        result = convert_content(text, DEFAULT_INTERNAL_KEYS, lang='fr')
        self.assertIn('<!-- {{renderer :todomaster}} -->', result)


# ──────────────────────────────────────────────
# EPIC-0.10: Colors from colors.md
# ──────────────────────────────────────────────

class TestLoadColors(unittest.TestCase):

    def _make_graph(self, colors_content=None):
        """Create a temporary graph dir with an optional pages/colors.md."""
        tmp = tempfile.mkdtemp()
        pages = Path(tmp) / 'pages'
        pages.mkdir()
        if colors_content is not None:
            (pages / 'colors.md').write_text(colors_content, encoding='utf-8')
        return Path(tmp)

    def test_colors_md_absent_returns_none(self):
        """When colors.md does not exist, load_colors returns (None, None)."""
        graph = self._make_graph()
        colors, color_vars = load_colors(graph)
        self.assertIsNone(colors)
        self.assertIsNone(color_vars)

    def test_colors_md_parses_light_dark_vars(self):
        """A well-formed colors.md is parsed into colors and color_vars dicts."""
        content = (
            '- title:: Colors\n'
            '  public:: false\n'
            '\n'
            '- light\n'
            '\t- background:: #FFFFFF\n'
            '\t- text_primary:: #1a1a1a\n'
            '- dark\n'
            '\t- background:: #1d1e20\n'
            '\t- text_primary:: #dadada\n'
            '- vars\n'
            '\t- background:: --body-background\n'
            '\t- text_primary:: --primary\n'
        )
        graph = self._make_graph(content)
        colors, color_vars = load_colors(graph)
        self.assertEqual(colors['light']['background'], '#FFFFFF')
        self.assertEqual(colors['light']['text_primary'], '#1a1a1a')
        self.assertEqual(colors['dark']['background'], '#1d1e20')
        self.assertEqual(colors['dark']['text_primary'], '#dadada')
        self.assertEqual(color_vars['background'], '--body-background')
        self.assertEqual(color_vars['text_primary'], '--primary')

    def test_colors_md_empty_sections_returns_none(self):
        """A colors.md with no actual values returns (None, None)."""
        content = '- title:: Colors\n  public:: false\n'
        graph = self._make_graph(content)
        colors, color_vars = load_colors(graph)
        self.assertIsNone(colors)
        self.assertIsNone(color_vars)

    def test_colors_md_partial_only_vars(self):
        """A colors.md with only vars section is valid."""
        content = (
            '- vars\n'
            '\t- background:: --body-background\n'
        )
        graph = self._make_graph(content)
        colors, color_vars = load_colors(graph)
        self.assertEqual(color_vars['background'], '--body-background')
        self.assertEqual(colors, {})

    def test_colors_md_page_props_skipped(self):
        """Page-level properties (title::, public::) are not parsed as color keys."""
        content = (
            'title:: Colors\n'
            'public:: false\n'
            '\n'
            '- light\n'
            '\t- bg:: #FFF\n'
        )
        graph = self._make_graph(content)
        colors, color_vars = load_colors(graph)
        self.assertNotIn('title', colors.get('light', {}))
        self.assertEqual(colors['light']['bg'], '#FFF')


if __name__ == '__main__':
    unittest.main()
