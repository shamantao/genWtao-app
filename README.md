# genWtao — Personal Site Generator (Logseq + Hugo)

Pipeline: Logseq → GitHub Actions → Hugo → InfinityFree  
Theme: [PaperMod](https://github.com/adityatelange/hugo-PaperMod)

---

## How it works — 3 steps

1. **Edit your pages** in Logseq on Mac (or Android via Dropbox)
2. **Push to GitHub** via the Logseq Git plugin (from Mac)
3. **Click "Run workflow"** on github.com → Actions → Generate and Deploy

The build and deployment happen entirely in the cloud. Your Mac does not need to be on at step 3.

---

## Logseq conventions — complete reference

### Required page properties

Every Logseq page intended for the site must start with a properties block:

```
title::      (displayed as the page title on the site)
lang::       (fr | en | zh-TW)
type::       (home | cv | post | curious | contact)
slug::       (URL-safe, no accents or spaces, e.g. my-article)
public::     true
date::       2026-02-24
```

**All properties are required** for `post` pages (blog articles).  
For `cv`, `home`, `curious`, `contact`: `date::` can be omitted (today's date is used automatically).

---

### Optional properties

```
description::     (short text for SEO meta tags)
menu_order::      (integer, e.g. 1 — controls listing order)
translationKey::  (shared key across languages — the language switcher links equivalent pages)
toc::             true  → generates an interactive table of contents with H2/H3 anchors
```

> **`toc:: true`**: displays a sticky sidebar TOC to the left of the content (via CSS Grid).  
> Hugo generates anchors automatically from heading text (`## Contact` → `#-contact`).  
> Nothing to write in Logseq — just add `toc:: true` to the page properties.

---

### `lang::` values

| Value | Language | Generated Hugo folder |
|-------|----------|-----------------------|
| `fr` | French | `content/fr/` |
| `en` | English | `content/en/` |
| `zh-TW` | Traditional Chinese | `content/zh-tw/` |

---

### `type::` values and generated pages

| `type::` | Output | Resulting URL |
|----------|--------|---------------|
| `home` | `content/<lang>/_index.md` | `/fr/` (language home page) |
| `cv` | `content/<lang>/cv/_index.md` | `/fr/cv/` |
| `post` | `content/<lang>/blog/<slug>.md` | `/fr/blog/my-article/` |
| `curious` | `content/<lang>/curious/_index.md` | `/fr/curious/` |
| `contact` | `content/<lang>/contact/_index.md` | `/fr/contact/` |

> **To add a new type**: add a line under `sections:` in `config/config.yaml`.  
> Example: `portfolio: portfolio` creates `content/<lang>/portfolio/`.  
> The Hugo menu (`site/hugo.yaml`) must also be updated manually.

---

### Role of `date::`

- For `post` pages: controls display order (newest first) and the article header.
- For other types: used in Hugo metadata, rarely visible to visitors.
- Required format: `YYYY-MM-DD` (e.g. `2026-02-24`).
- If missing: today's generation date is used automatically.

---

### Why `title::` and filename are independent

Logseq uses the **filename** as its internal identifier (for `[[links]]`).  
The `title::` property is the **displayed title** (on the site and in Logseq).  
The script reads `title::`, not the filename — renaming `title::` does not break anything.

⚠️ If Logseq auto-renames the file when you change `title::`, existing `[[links]]` pointing to the old name may break inside Logseq. *This does not affect the site* (the script ignores filenames).

---

### `slug::` rules

- Used as the page URL.
- Lowercase, hyphens only, no accents, no spaces.
- Must be **unique per language and type**.
- For `post` pages: also used as the generated filename (`<slug>.md`).

---

### Page examples

**French home page** (`Accueil.md`):
```
title::       Accueil
lang::        fr
type::        home
slug::        accueil
public::      true
```

**French CV** (`Mon CV.md`):
```
title::       Mon CV
lang::        fr
type::        cv
slug::        cv
public::      true
description:: Software engineer, 10 years of experience.
```

**Blog article** (`Article IA 2026.md`):
```
title::       AI in 2026
lang::        fr
type::        post
slug::        ai-2026
public::      true
date::        2026-02-24
description:: My thoughts on AI in 2026.
```

**Curious page** (`Curious FR.md`):
```
title::       Curiosités
lang::        fr
type::        curious
slug::        curious
public::      true
```

---

### Minimum pages per language

For each language (fr / en / zh-TW), create at least:

| Logseq page | `type::` | `slug::` |
|---|---|---|
| `Accueil.md` / `Home.md` / `首頁.md` | `home` | `accueil` / `home` / `home` |
| `Mon CV.md` / `My Resume.md` / `我的履歷.md` | `cv` | `cv` |

Blog, curious, and contact sections are optional to start.

---

## Adding a new section type

1. **`config/config.yaml`** — add under `sections:`:
   ```yaml
   sections:
     portfolio: portfolio   # ← new line
   ```
2. **`site/hugo.yaml`** — add a menu entry for each language:
   ```yaml
   languages:
     fr:
       menu:
         main:
           - name: Portfolio
             url: /fr/portfolio/
             weight: 25
   ```
3. **In Logseq** — use `type:: portfolio` on the relevant pages.

That's it.

---

## Project structure

```
genWtao-app/
├── README.md
├── config/
│   └── config.yaml           ← section types, FTP config, theme params
├── scripts/
│   ├── logseq_to_hugo.py     ← Logseq → Hugo converter
│   └── publish.sh            ← local script (Mac offline use)
├── site/
│   ├── hugo.yaml             ← Hugo config + multilingual menus
│   ├── themes/
│   │   └── PaperMod/         ← theme (git submodule)
│   ├── content/              ← generated by logseq_to_hugo.py — do not edit
│   │   ├── fr/
│   │   ├── en/
│   │   └── zh-tw/
│   ├── layouts/
│   │   ├── cv/
│   │   │   └── list.html     ← ⚠ PaperMod-specific override (TOC for CV pages)
│   │   └── partials/
│   │       ├── header.html   ← ⚠ PaperMod-specific override (language switcher)
│   │       └── extend_head.html  ← injects custom.css (theme-agnostic)
│   └── static/
│       ├── assets/           ← copied from Logseq assets/ by the script
│       └── css/
│           └── custom.css    ← functional CSS (sidebar TOC — theme-agnostic)
└── .github/workflows/
    └── generate-and-deploy.yml
```

---

## Theme portability

The project is designed to make theme migration straightforward.

**What survives a theme change (Hugo standard):**
- All generated content in `site/content/` — 100% Markdown + standard front matter
- Multilingual structure (`contentDir` per language)
- Taxonomies (tags, categories)
- `logseq_to_hugo.py` — front matter param names are mapped via `theme_params:` in `config.yaml`
- `site/static/css/custom.css` — may need selector updates if the new theme uses different class names

**What needs rewriting on theme change:**
- Files marked `⚠ PaperMod-specific` in `site/layouts/` (2 files)
- `theme_params:` values in `config/config.yaml` (3 lines)

See `config/config.yaml` → `theme_params:` section for the mapping.

---

## Initial setup

```bash
git clone https://github.com/shamantao/genWtao-app.git
cd genWtao-app

# Initialize the PaperMod theme submodule
git submodule update --init --recursive

# Create your personal config (gitignored — never committed)
cp config/config.example.yaml config/config.yaml
# Then edit config/config.yaml: fill in your paths, FTP user, site URL
```

Set the required secrets in GitHub → Settings → Secrets → Actions:

| Name | Value |
|------|-------|
| `GH_TOKEN` | Personal Access Token (read access to your Logseq graph repo) |
| `FTP_PASSWORD` | Your FTP hosting password |
| `FORMSPREE_ID` | Formspree form ID (for the contact form) |

---

## Local testing before pushing

**Rule: always test locally before triggering GitHub Actions.**

```bash
cd genWtao-app

python3 scripts/logseq_to_hugo.py \
  --graph  $(grep 'logseq:' config/config.yaml | awk '{print $2}') \
  --output site/content \
  --config config/config.yaml \
  --clean

cd site && hugo --minify
```

> The `--graph` path is read from your `config/config.yaml` (`paths.logseq`).

If the local build passes with no errors → the Actions workflow will pass.  
If the local build fails → fix before pushing.

---

## Running the pipeline

### From any browser (Mac or Android)

1. Go to `https://github.com/<your-username>/genWtao-app/actions`
2. Click **Generate and Deploy**
3. Click **Run workflow** (grey button)
4. Wait 2–3 min → site live at your hosting URL

### Prerequisite: Logseq graph up to date on GitHub

Before clicking Run workflow, the Logseq Git plugin (Mac) must have pushed the latest pages to your private Logseq graph repo.

---

## Troubleshooting

### Site does not update after a push
- Check that the page has `public:: true`
- Check that the push went through to `main`
- Re-run the workflow from the Actions tab

### FTP upload fails
- Check the FTP password in GitHub Secrets
- Verify that `remote_path` is correct in `config.yaml`
- Test the FTP connection manually:
  ```bash
  ftp YOUR_FTP_HOST
  # user: YOUR_FTP_USER
  # password: (from GitHub Secrets)
  ```

### Page renders incorrectly
- Check the generated file in `site/content/<lang>/<type>/`
- Run `hugo server` locally to inspect

---

## Resources

- [Hugo PaperMod](https://github.com/adityatelange/hugo-PaperMod)
- [Hugo documentation](https://gohugo.io/documentation/)
- [GitHub Actions](https://docs.github.com/en/actions)
- [Formspree](https://formspree.io)

---

## License

[MIT](LICENSE) — Philippe Bertieri, 2026
