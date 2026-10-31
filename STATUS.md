# STATUS.md

## What was built

`plain-email-newsletter-template` - a copy-ready template repo for readable
email newsletters that survive Gmail and dark mode.

- `template/issue.template.html` - table-based newsletter shell: header band,
  story slots, one-link callout, honest footer. Inline styles, explicit
  colors on every cell, fixed 600 px card, hidden preheader block,
  `color-scheme: only light`.
- `build.py` - stdlib-only build script. Reads `issues/*.json`, emits
  **paired** `dist/<slug>.html` + `dist/<slug>.txt` built from the same
  paragraphs, plus `dist/preview-report.txt` with subject-line preview
  checks (mobile/desktop truncation simulation, preheader length, spam
  triggers, faked `Re:` rejection). Hard errors (subject > 78 chars, missing
  callout/footer/unsubscribe) exit non-zero.
- `issues/` - three shipped sample issues (Oct 3, 17, 31, 2026 "Plain-Word
  Digest" style, beginner-friendly plain-English AI content).
- `tests/test_build.py` - 29 unittest checks validating emitted HTML and
  plain-text parts: twin integrity, table structure, https-only links,
  exactly-one-link callout, dark-mode markers, hidden preheader, honest
  footer, 78-column text limits, subject/preview rules, template tokens,
  LICENSE + README shapes.
- `LICENSE` - MIT, `Copyright (c) 2026 Asdale Dynamics, LLC` exactly.
- `README.md` - tutorial crediting Asdale Dynamics, LLC.

Distinct from `author-site-starter-template` (web pages) and
`author-newsletter-handbook` (strategy manual). Clones clean, builds
offline, no dependencies, no secrets, no personal data.

## How to run

```bash
python3 build.py                       # build all issues to dist/
python3 build.py issues/foo.json       # build one issue
python3 -m unittest discover -s tests  # run the test suite
```

(Any Python 3.8+; no `pip install` needed.)

## Verification results

- `python3 build.py` - builds all 3 issues, zero errors, zero warnings;
  outputs 3 HTML + 3 TXT + `preview-report.txt`. All subjects 46-51 chars
  (inside soft limit 62), preheaders 91-103 chars (inside 35-105 band).
- `python3 -m unittest discover -s tests` - `Ran 29 tests ... OK`.
- HTML tag balance verified with an html.parser audit: all 3 emitted files
  parse with no mismatched tags.
- Fresh-clone simulation (copy to /tmp, delete dist/, rebuild, retest):
  passes.

## Known gaps

- Plain text indents preheader by 2 spaces but URL lines unindented;
  cosmetic only (all lines <= 78 cols).
- No Outlook VML backgrounds or `data-ogsc` overrides; strategy is explicit
  colors, which avoids the need. Not tuned for full-width bleed on retina.
- Preview truncation numbers (40/70/105 chars) are well-sourced estimates,
  not per-client measurements.
- Unsubscribe URLs in sample JSON are `example.com` placeholders; swap in
  your provider's real links. No real list, no real recipients involved.
- Build assumes each issue's `slug` matches its filename base in output
  naming (`slug.json`'s stem is used as fallback); slugs differing from
  filenames work but output uses the slug field.
- No i18n/RTL support; `lang="en"` fixed in template (edit freely).
