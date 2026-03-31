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
- **The filename is the title** by default. You can override it with `title::` if needed.
- **`slug::`** becomes the URL. Use only lowercase letters, numbers, and hyphens.
- **`date::`** is required for articles (controls the order). For other pages it's filled automatically.

### Journal articles (optional)

You can also write quick articles directly inside your **Logseq daily journal** — no need to create a dedicated page.

**Enable it** in `config/config.yaml`:
```yaml
journal_articles: true    # false by default
```

Then in any journal entry, add a top-level bullet with `type:: article`:
```
- type:: article
  menu:: blog
  lang:: fr
  title:: Découverte de n8n
  slug:: n8n-discovery
  description:: Premiers pas avec n8n et Docker
	- Premier paragraphe de contenu.
	- Deuxième paragraphe avec plus de détails.
		- Un sous-point.
```

**Rules:**
- Only **top-level bullets** (first level `- `) with `type::` are scanned
- `title::` and `slug::` are **required** (there is no filename to auto-deduce from)
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

python3 scripts/logseq_to_hugo.py \
  --config config/config.yaml \
  --site   /path/to/your-logseq-graph/site.yaml \
  --clean

cd site && hugo server
```

`--graph` and `--output` are optional — they default to `graph_path` in config.yaml and `site/content`.

---

## Initial setup

### 1. Clone and configure

```bash
git clone https://github.com/<your-username>/genWtao-app.git
cd genWtao-app
git submodule update --init --recursive

cp site.example.yaml /path/to/your-logseq-graph/site.yaml
# Edit site.yaml: your site URL, FTP host, FTP user, languages
# Edit config/config.yaml: set graph_path to your Logseq graph folder
```

In `generate-and-deploy.yml`, update the repository reference to point to your own graph repository:
```yaml
      - name: Checkout genWtao-graph
        uses: actions/checkout@v4
        with:
          repository: <your-username>/<your-graph-repo>   # ← your graph repo
```

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
     - **Contents**: `Read` (to checkout the graph)
     - **Actions**: `Write` (to trigger the deploy workflow via `repository_dispatch`)
5. Click **Generate token** and **copy the token immediately** (it won't be visible again)

### 3. Add secrets on GitHub

Add the following secrets on **both repositories** (Settings → Secrets and variables → Actions → New repository secret):

| Secret | Where | What it is |
|--------|-------|------------|
| `GH_TOKEN` | **app repo** + **graph repo** | The Personal Access Token created above |
| `FTP_PASSWORD` | **app repo** only | Your hosting FTP password |

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
      - 'site.yaml'

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

### The language flags are missing
- For pages/collections/forms: all translations of the same section automatically share a translationKey (= `menu::` value). Just make sure each language version has the same `menu::`.
- For articles: all translations should share the same `slug::`.
- Override: set `translationKey::` explicitly if auto-deduction doesn't work.

### The contact form redirects to an error page
- Check that `form_id::` is set in sitemap.md under the contact section
- Check that the form ID matches your account on the provider

### Blog articles don't show in the listing
- The section needs a `type:: collection` page (the index) + individual `type:: article` pages
- Make sure the collection page and the articles share the same `menu::` value

### FTP upload failed
- Check the FTP password in GitHub Secrets
- Verify `remote_path` in config.yaml

---

## Advanced — project layout & theme portability

### Project structure

```
genWtao-app/                              ← this repository
├── config/
│   └── config.yaml                       ← engine config (graph path, types, theme, colors)
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
├── site.yaml                             ← your personal site settings
├── pages/
│   ├── sitemap.md                        ← site structure, menus, contact provider
│   └── widgets.md                        ← widget definitions
├── journals/                             ← daily journal (optional article source)
└── assets/                               ← images used in your pages
```

### Theme portability

The project separates your content from the visual theme. If you want to switch themes later:

**What stays the same:** all your content, the multilingual setup, the conversion script.

**What needs updating:** 2 template files in `site/layouts/` and 3 lines in `config/config.yaml` (theme_params mapping).

---

## Resources

- [Hugo PaperMod](https://github.com/adityatelange/hugo-PaperMod)
- [Hugo documentation](https://gohugo.io/documentation/)
- [GitHub Actions](https://docs.github.com/en/actions)
- Contact form providers: [Formspree](https://formspree.io) · [Web3Forms](https://web3forms.com) · [FormSubmit](https://formsubmit.co) · [Getform](https://getform.io) · [Fabform](https://fabform.io)

---

## License

[MIT](LICENSE) — Shamantao, 2026