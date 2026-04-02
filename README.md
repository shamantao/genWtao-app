# genWtao — Build your website from Logseq

Write your content in **Logseq**, click a button, and your website is online.

Theme: [PaperMod](https://github.com/adityatelange/hugo-PaperMod) · License: [MIT](LICENSE)

---

## Table of contents

1. [How it works](#how-it-works)
2. [Writing content](#writing-content) — the 3 properties you need
3. [The 4 page types](#the-4-page-types) — page, article, collection, form
4. [Site structure](#site-structure) — sitemap.md, menus, sections
5. [Languages & translation](#languages--translation) — multilingual, language switcher
6. [Contact form](#contact-form) — providers, setup
7. [Widgets](#widgets) — embed buttons, videos, HTML
8. [Publishing](#publishing) — push, trigger, deploy
9. [Initial setup](#initial-setup)
10. [Troubleshooting](#troubleshooting)
11. [Advanced — project layout & theme portability](#advanced--project-layout--theme-portability)
12. [Tips & tricks](#tips--tricks) — future dates, video embeds, journal structure

---

## How it works

1. **Write** your pages in Logseq (on computer or phone)
2. **Sync** your Logseq graph to GitHub (via the Logseq Git plugin on your computer)
3. **Done** — your site rebuilds and deploys automatically in 2–3 minutes

When you push changes to your graph repository, a GitHub Actions workflow automatically triggers the build and deploy pipeline on the app repository. No manual step needed.

You can also trigger a build manually: go to your app repository on github.com → **Actions** tab → **Generate and Deploy** → **Run workflow**.

---

## Writing content

Every published page needs a small **properties block** at the top — 3 lines.

### The 3 properties

| Property | What it does | Example |
|---|---|---|
| `type::` | What kind of page (behaviour) | `type:: page` |
| `menu::` | Which section of the site | `menu:: cv` |
| `lang::` | The language of this page | `lang:: fr` |

**Everything else is auto-deduced:**

| What | How it's deduced | Override with |
|---|---|---|
| Title | From the Logseq filename | `title::` |
| Slug (URL) | From the title, slugified | `slug::` |
| Translation link | From `menu::` (pages) or `slug::` (articles) | `translationKey::` |
| Date | Today's date | `date::` |

### Optional properties

| Property | When to use | Example |
|---|---|---|
| `title::` | When the filename isn't a good title | `title:: My Resume` |
| `slug::` | When you want a specific URL | `slug:: cv` |
| `date::` | **Required for articles** | `date:: 2026-03-28` |
| `description::` | SEO summary | `description:: 10 years of experience` |
| `toc::` | Show table of contents | `toc:: true` |
| `public::` | Hide a page from the site | `public:: false` |
| `draft::` | Same as `public:: false` (Hugo convention) | `draft:: true` |
| `translationKey::` | Link translations manually | `translationKey:: my-article` |

### Examples

**A French CV page:**
```
type:: page
menu:: cv
lang:: fr
toc:: true
```
That's it. Title = filename, slug = auto, translationKey = `cv` (from menu).

**A blog article:**
```
type:: article
menu:: blog
lang:: fr
slug:: n8n-discovery
date:: 2026-03-28
description:: First steps with n8n and Docker
```

**The home page:**
```
type:: page
menu:: home
lang:: en
```

### Good to know

- **No `public:: true` needed** — a page is published when it has a `type::`. No `type::` = not published.
- **To hide a page:** add `public:: false` or `draft:: true` on any page that has `type::`. The page will be skipped during generation (not exported, not indexed for link resolution).
- **The filename is the title** by default. You can override it with `title::` if needed.
- **`slug::`** becomes the URL. Use only lowercase letters, numbers, and hyphens.
- **`date::`** is required for articles (controls the order). For other pages it's filled automatically.
- **Future dates:** Hugo does not publish articles with a future `date::` in production builds. They are visible in local preview (`hugo server`) but hidden on the live site until the date arrives.

### Global properties guide (quick cookbook)

Use this section as a practical reference for all property combinations.

#### 1) Minimal static page

```
type:: page
menu:: cv
lang:: en
```

Result: one page in `/en/cv/`, with title/slug auto-deduced.

#### 2) Collection index page

```
type:: collection
menu:: blog
lang:: fr
title:: Actualités
```

Result: collection landing page (`_index.md`) for that language and section.

#### 3) Article with explicit date/slug

```
type:: article
menu:: blog
lang:: en
slug:: release-notes-q2
date:: 2026-04-02
description:: Product updates for Q2
```

Result: article page in `/en/blog/release-notes-q2/`.

#### 4) Multilingual article pair (recommended)

When article titles differ by language, use an explicit shared `translationKey::`.

```
# French version
type:: article
menu:: curious
lang:: fr
slug:: guide-the-blanc
date:: 2026-04-02
translationKey:: white-tea-guide
```

```
# English version
type:: article
menu:: curious
lang:: en
slug:: white-tea-guide
date:: 2026-04-02
translationKey:: white-tea-guide
```

Result: language switcher links FR ↔ EN on the same article.

#### 5) Hide a page from publishing

```
lang:: en
menu:: blog
# no type::
```

Result: not published (no `type::` = ignored).

#### 6) Temporarily unpublish a page

```
type:: article
menu:: blog
lang:: fr
date:: 2026-04-01
public:: false
```

Result: page has `type::` but is explicitly excluded. Equivalent: `draft:: true`.

### Journal articles (optional)

You can also write quick articles directly inside your **Logseq daily journal** — no need to create a dedicated page.

**Enable it** in your graph's `config.yaml`:
```yaml
journal_articles: true    # false by default
```

Then in any journal entry, add a top-level bullet with your article title, and set `type:: article` in child properties:
```
- [[Découverte de n8n]]
	- type:: article
	  menu:: blog
	  lang:: fr
	- Premier paragraphe de contenu.
	- Deuxième paragraphe avec plus de détails.
		- Un sous-point.
```

Title = `Découverte de n8n` (auto-deduced from the bullet text). Slug = `decouverte-de-n8n` (auto-deduced from the title). Date = journal filename.

**Rules:**
- Only **top-level bullets** (first level `- `) with `type::` are scanned
- `title::` is **auto-deduced** from the bullet text (e.g. `[[My Title]]` → `My Title`), but you can override it
- `slug::` is **auto-deduced** from the title, but you can override it
- `date::` is **auto-deduced** from the journal filename (`2026_03_28.md` → `2026-03-28`), but you can override it
- Everything indented below the bullet = the article content
- If a page in `pages/` has the same slug, **the page wins** (pages always take priority)

---

## The 4 page types

`type::` defines the **behaviour** of a page, not where it goes (that's `menu::`).

| `type::` | Behaviour | Output file | Example |
|---|---|---|---|
| `page` | Single page per section/language | `_index.md` | Home, CV, Project |
| `article` | Individual post in a collection | `<slug>.md` | Blog post, resource |
| `collection` | Section listing page (shows articles) | `_index.md` | Blog index, Curiosity index |
| `form` | Page with a submission form | `_index.md` | Contact |

**Typical setup for a blog:**
- 1 page `type:: collection` + `menu:: blog` per language → the listing page
- N pages `type:: article` + `menu:: blog` → individual posts

---

## Site structure

The layout of your site — sections, menus, labels — is defined in a single Logseq file: `pages/sitemap.md`. This file is not published.

### How `sitemap.md` works

```
public:: false

- home
	- slug::
	- fr:: Accueil
	- en:: Home
	- zh-tw:: 首頁
- cv
	- slug:: cv
	- fr:: Expériences
	- en:: Experiences
	- zh-tw:: 工作經歷
- project
	- slug:: project
	- fr:: Projets
	- en:: Projects
	- zh-tw:: 專案
- contact
	- slug:: contact
	- provider:: formspree
	- form_id:: your_form_id
	- fr:: Contact
	- en:: Contact
	- zh-tw:: 聯絡我
- blog
	- slug:: blog
	- mode:: collection
	- fr:: Blog
	- en:: Blog
	- zh-tw:: 部落格
- curious
	- slug:: curious
	- mode:: collection
	- fr:: Curiosité
	- en:: Curiosity
	- zh-tw:: 好奇心
```

Each bullet is a **section**. Under each:
- `slug::` — the URL path (e.g. `cv` → your-site.com/fr/cv/)
- `mode:: collection` — this section lists multiple articles
- `provider::` / `form_id::` — contact form settings (see [Contact form](#contact-form))
- `fr::`, `en::`, `zh-tw::` — menu label for each language

### Menu order

**The order in sitemap.md = the order in the menu.** To reorder, just move the blocks. `home` is always excluded from the menu (it's the site root).

### Adding a new section

Add a block in `sitemap.md`:
```
- portfolio
	- slug:: portfolio
	- mode:: collection
	- fr:: Portfolio
	- en:: Portfolio
	- zh-tw:: 作品集
```
Then create pages with `menu:: portfolio`. The menu, URLs, and labels are generated automatically.

---

## Languages & translation

### Supported languages

| `lang::` value | Site URL | Switcher |
|---|---|---|
| `fr` | `/fr/...` | 🇫🇷 |
| `en` | `/en/...` | 🇬🇧 |
| `zh-TW` | `/zh-tw/...` | 🇹🇼 |

### How the language switcher works

The system automatically links pages that are translations of each other using `translationKey`. You don't need to set it manually — it's auto-deduced:

| Page type | translationKey = | Why |
|---|---|---|
| `page`, `collection`, `form` | `menu::` value | All CVs share `cv`, all contacts share `contact` |
| `article` | `slug::` value | Articles with the same slug across languages are linked |

**Override:** if you need a custom link, set `translationKey::` explicitly on the page.

### Switcher behavior: exact rules

- If another language version with the same `translationKey` exists, the flag links to that translated page.
- If no page exists in the target language for that `translationKey`, the flag links to that language home.
- For `page` / `collection` / `form`, this is usually automatic (shared `menu::`).
- For `article`, if titles/slugs differ by language, define `translationKey::` explicitly on each language version.

### Article translation best practice

For multilingual articles, prefer this pattern:

- Keep language-specific `title::` and `slug::`.
- Share one stable `translationKey::` across all languages.
- Use lowercase letters, numbers, and hyphens for readability (it can be any string technically, but readable keys are easier to maintain).

### Adding a new language

Add a label for each section in `sitemap.md`:
```
- cv
	- slug:: cv
	- fr:: Expériences
	- en:: Experiences
	- zh-tw:: 工作經歷
	- pl:: Doświadczenie     ← new language
```

---

## Contact form

The contact form is **provider-agnostic**. You choose a service, put its ID in `sitemap.md`, and the template handles the rest.

### Configuration in `sitemap.md`

```
- contact
	- slug:: contact
	- provider:: formspree
	- form_id:: your_form_id
	- fr:: Contact
	- en:: Contact
```

Two fields:
- **`provider::`** — which service handles submissions
- **`form_id::`** — your form/API key from that service

### Supported providers

| Provider | `provider::` | Free tier | `form_id::` = |
|---|---|---|---|
| [Formspree](https://formspree.io) | `formspree` | 50/month | Form hashid (e.g. `xyzabcde`) |
| [Web3Forms](https://web3forms.com) | `web3forms` | 250/month | Access key |
| [FormSubmit](https://formsubmit.co) | `formsubmit` | Unlimited, no signup | Email hash |
| [Getform](https://getform.io) | `getform` | 50/month | Endpoint ID |
| [Fabform](https://fabform.io) | `fabform` | 1000/month, EU servers | Form ID |
| Self-hosted PHP | `php` | Free (your server) | *(not needed)* |

### Switching providers

1. Create an account on the new provider
2. Get your form ID / access key
3. Update 2 lines in sitemap.md:
```
	- provider:: web3forms
	- form_id:: your_new_access_key
```
4. Regenerate. Done. No code changes.

---

## Widgets

Widgets let you embed external elements (buttons, videos, custom HTML) into any page, without touching code.

### Define widgets in `pages/widgets.md`

```
public:: false

- buymeacoffee
	- slug:: shamantao
	- color:: #40DCA5
	- emoji:: 🍵
	- text:: Buy me a tea
```

### Use a widget in any page

Write this anywhere in your Logseq page:
```
{{widget buymeacoffee}}
```

The script replaces it with the actual HTML when building the site.

### Available widget types

| Type | What you need | What it does |
|------|---------------|--------------|
| `buymeacoffee` | `slug` (your username) | A "Buy Me a Coffee" button |
| `youtube` | `id` (video ID) | An embedded YouTube video |
| `image` | `src` (image path) | An image with optional caption |
| `html` | `code` (HTML code) | Any custom HTML |

---

## Publishing

### Automatic (recommended)

Once [initial setup](#initial-setup) is complete, publishing is fully automatic:

1. Edit your pages in Logseq
2. The Logseq Git plugin pushes your changes to GitHub
3. The graph repository notifies the app repository → build → deploy
4. Your site is live in 2–3 minutes

### Manual trigger

You can also trigger a build manually from **any browser** (computer or phone):
1. Go to your app repository on github.com → **Actions** tab
2. Click **Generate and Deploy** → **Run workflow**

### Testing locally

```bash
cd genWtao-app

python3 scripts/logseq_to_hugo.py --clean

cd site && hugo server
```

`--graph` and `--output` are optional — they default to `graph_path` in `graph_path.yaml` and `site/content`. Config is auto-loaded from `{graph}/config.yaml`.

---

## Initial setup

### 1. Clone and configure

```bash
git clone https://github.com/<your-username>/genWtao-app.git
cd genWtao-app
git submodule update --init --recursive

./install.sh
# The script will:
#   - ask for your Logseq graph path
#   - generate graph_path.yaml (local pointer to the graph)
#   - copy config.example.yaml to your graph as config.yaml
#   - create template pages (sitemap.md, colors.md, widgets.md, 404.md)
```

Then edit `config.yaml` **in your graph**: set your hosting URL, FTP host/user, Hugo config, and languages.

### 2. Create a GitHub Personal Access Token

This token allows the two repositories to communicate (the graph triggers the build, and the app reads the graph content).

1. Go to **github.com** → your avatar (top right) → **Settings**
2. Scroll down to **Developer settings** (bottom of the left menu)
3. **Personal access tokens** → **Fine-grained tokens** → **Generate new token**
4. Fill in:
   - **Token name**: `genWtao-deploy` (or any name you like)
   - **Expiration**: 90 days (you can renew it later)
   - **Repository access**: **Only select repositories** → select both your app and graph repositories
   - **Permissions** → **Repository permissions**:
     - **Contents**: `Read and Write` (to checkout the graph and trigger dispatches)
     - **Actions**: `Write` (to trigger the deploy workflow via `repository_dispatch`)
5. Click **Generate token** and **copy the token immediately** (it won't be visible again)

### 3. Add secrets and variables on GitHub

Add the following **secrets** on both repositories (Settings → Secrets and variables → Actions → New repository secret):

| Secret | Where | What it is |
|--------|-------|------------|
| `GH_TOKEN` | **app repo** + **graph repo** | The Personal Access Token created above |
| `FTP_PASSWORD` | **app repo** only | Your hosting FTP password |

Add the following **variable** on the app repository (Settings → Secrets and variables → Actions → Variables → New repository variable):

| Variable | Where | What it is |
|----------|-------|------------|
| `GRAPH_REPO` | **app repo** | `owner/graph-repo-name` (e.g. `myuser/mysite-graph`) |

### 4. Add the notification workflow to your graph repository

Create the file `.github/workflows/notify-app.yml` in your graph repository:

```yaml
name: Notify app

on:
  push:
    branches: [main]
    paths:
      - 'pages/**'
      - 'journals/**'
      - 'assets/**'
      - 'config.yaml'

jobs:
  trigger-deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Trigger Generate and Deploy
        run: |
          curl -X POST \
            -H "Accept: application/vnd.github+json" \
            -H "Authorization: Bearer ${{ secrets.GH_TOKEN }}" \
            https://api.github.com/repos/<your-username>/<your-app-repo>/dispatches \
            -d '{"event_type": "graph-updated"}'
```

Replace `<your-username>/<your-app-repo>` with your actual app repository path.

### 5. Test the pipeline

1. Push a change to your graph repository (edit any file in `pages/`)
2. Go to your **graph repo** → Actions → the **"Notify app"** workflow should run
3. Then go to your **app repo** → Actions → **"Generate and Deploy"** should trigger automatically
4. Your site is live in 2–3 minutes

---

## Troubleshooting

### My page doesn't appear on the site
- Check that the page has `type::` defined (no type = not published)
- Check that `menu::` matches a section in sitemap.md
- Check for `public:: false` or `draft:: true` — these explicitly hide the page
- For **journal articles**: properties must be at the first indentation level (one tab under the title bullet). Properties nested under a heading or sub-bullet are not detected.

### The language flags are missing
- For pages/collections/forms: all translations of the same section automatically share a translationKey (= `menu::` value). Just make sure each language version has the same `menu::`.
- For articles: all translations must share the same `translationKey::` (or the same `slug::` if you rely on auto-deduction).
- Override: set `translationKey::` explicitly if auto-deduction doesn't work.

### The contact form redirects to an error page
- Check that `form_id::` is set in sitemap.md under the contact section
- Check that the form ID matches your account on the provider

### Blog articles don't show in the listing
- The section needs a `type:: collection` page (the index) + individual `type:: article` pages
- Make sure the collection page and the articles share the same `menu::` value

### FTP upload failed
- Check the FTP password in GitHub Secrets
- Verify `hosting.ftp.remote_path` in your graph's `config.yaml`

### A video embed makes an article disappear
- Use `{{video url}}` syntax, not `{{html url}}` (not supported yet)
- Supported video syntax: `{{video https://...}}`, `{{embed https://...}}`, `{{youtube https://...}}`
- Any unrecognized `{{...}}` in content can cause Hugo to crash silently on that page

---

## Advanced — project layout & theme portability

### Project structure

```
genWtao-app/                              ← this repository
├── install.sh                            ← first-time setup script
├── graph_path.yaml                       ← local pointer to the graph (gitignored)
├── graph_path.example.yaml               ← template — do not edit
├── config.example.yaml                   ← template for graph config — do not edit
├── scripts/
│   ├── logseq_to_hugo.py                 ← converts Logseq pages to Hugo format
│   ├── preview.sh                        ← local preview script
│   └── publish.sh                        ← local build script (offline use)
├── site/
│   ├── hugo.yaml                         ← auto-generated site configuration
│   ├── themes/PaperMod/                  ← visual theme
│   ├── content/                          ← auto-generated pages (do not edit)
│   ├── layouts/                          ← page templates
│   └── static/css/custom.css             ← custom styles
└── .github/workflows/
    └── generate-and-deploy.yml           ← the automated build pipeline

your-logseq-graph/                        ← separate repository (private)
├── config.yaml                           ← site config (hosting, hugo, languages)
├── pages/
│   ├── sitemap.md                        ← site structure, menus, contact provider
│   └── widgets.md                        ← widget definitions
├── journals/                             ← daily journal (optional article source)
└── assets/                               ← images used in your pages
```

### Theme portability

The project separates your content from the visual theme. If you want to switch themes later:

**What stays the same:** all your content, the multilingual setup, the conversion script.

**What needs updating:** 2 template files in `site/layouts/` and 3 lines in your graph's `config.yaml` (theme_params mapping).

---

## Resources

- [Hugo PaperMod](https://github.com/adityatelange/hugo-PaperMod)
- [Hugo documentation](https://gohugo.io/documentation/)
- [GitHub Actions](https://docs.github.com/en/actions)
- Contact form providers: [Formspree](https://formspree.io) · [Web3Forms](https://web3forms.com) · [FormSubmit](https://formsubmit.co) · [Getform](https://getform.io) · [Fabform](https://fabform.io)

---

## Tips & tricks

### Scheduled publishing (future dates)

If you set `date:: 2026-05-01` on an article, Hugo will **not** include it in production builds (because `buildFuture` defaults to `false`). The article is visible in local preview (`hugo server`) but hidden on the live site.

**Important:** Hugo generates a static site. There is no server checking dates in real time. The article will **not** appear automatically on May 1st — you need a new build at or after that date.

**Option 1 — manual:** push a change or click "Run workflow" in GitHub Actions when you're ready.

**Option 2 — daily cron:** add a scheduled trigger to your GitHub Actions workflow so the site rebuilds every day at midnight:

```yaml
on:
  schedule:
    - cron: '0 0 * * *'   # every day at 00:00 UTC
```

Any articles whose `date::` has passed will then appear automatically on the next daily build.

### Embedding videos (Odysee, YouTube…)

Use `{{video url}}` to embed a video from any supported platform:

```
{{video https://odysee.com/@user/video-slug}}
{{video https://www.youtube.com/watch?v=dQw4w9WgXcQ}}
```

The script auto-detects the platform and generates the right embed (iframe, Hugo shortcode, etc.).

**What works in Logseq:**

| Syntax | Logseq rendering | genWtao conversion | Hugo |
|--------|------------------|--------------------|------|
| `{{video url}}` | Renders the embed | Converts to iframe/shortcode | Works |
| `{{html url}}` | Highlighted placeholder (not rendered) | **Passes through unchanged** | **Breaks the page silently** |
| `{{embed url}}` | Line **disappears** in Logseq | Would be converted, but content is lost in Logseq | Unreliable |

**Recommendation:** always use `{{video url}}` for media embeds. It's the only syntax that works correctly in both Logseq and the generated site.

### Journal article structure

When writing articles in daily journals, properties **must** be at the first indentation level (one tab) under the title bullet:

```
✅ Correct:
- [[My Article Title]]
	- type:: article
	  menu:: blog
	  lang:: en
	- First paragraph of content.

❌ Wrong — properties under a heading (two levels deep):
- [[My Article Title]]
	- # Some heading
		- type:: article
		  lang:: en
```

In the wrong structure, the script cannot find the `type::` property and the article is silently skipped.

---

## License

[MIT](LICENSE) — Shamantao, 2026