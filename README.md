# plain-email-newsletter-template

Copy-ready template for readable email newsletters that survive Gmail and dark
mode. One JSON file per issue in, paired HTML + plain text out, with
subject-line preview checks that poke you before your subscribers do.

It is deliberately web-page-hostile: table-based HTML, inline styles, a fixed
600 px card, and explicit colors on every cell. That is what keeps text from
vanishing in Gmail's dark mode, from breaking in Outlook, and from falling
apart when a subscriber forwards the issue.

- **Distinct from** `author-site-starter-template` (web pages) and
  `author-newsletter-handbook` (strategy manual). This repo only renders
  emails.
- **Offline and dependency-free.** Python 3 standard library only. No `pip
  install`, no API keys, no personal data shipped in the repo.

Built and maintained by **Asdale Dynamics, LLC** (Dylan Asdale, registered
nurse turned AI author). It follows the house style from *The Massive AI
Manual*: plain English, step by step, never condescending.

Licensed under the MIT license - see [LICENSE](LICENSE).

---

## What is in the box

```
plain-email-newsletter-template/
├── build.py                      build script (stdlib only)
├── template/
│   └── issue.template.html       the newsletter shell (header, slots, callout, footer)
├── issues/                       one JSON file per issue (3 samples included)
├── dist/                         built emails (HTML, plain text, preview report)
└── tests/                        unittest suite validating every emitted part
```

For each issue `foo.json` the build emits:

| File | What it is |
|---|---|
| `dist/foo.html` | the email - table-based, inline styles, dark-mode safe |
| `dist/foo.txt` | the plain-text twin, generated from the same paragraphs |
| `dist/preview-report.txt` | subject-line + preview-text truncation checks |

## The 90-second tutorial

**1. Build the samples and sniff the output.**

```bash
python3 build.py
cat dist/preview-report.txt
```

**2. Simply look at what you get.**

Copy an HTML file and paste it at https://www.caniemail.com or drop it into
your email provider's preview (a "paste HTML" step exists in Mailchimp,
Buttondown, Listmonk, and friends). Or email it to yourself and switch your
phone to dark mode first.

**3. Write your own issue.**

Copy a sample JSON file from `issues/`, rename it, and edit the fields:

- `subject` - hard limit 78 chars, warn past 62 (build tells you what phones will show)
- `preheader` - 35 to 105 chars; shows beside the subject in Gmail
- `stories[].paragraphs` - plain sentences; the HTML and text twins are built
  from these, so they can never drift apart
- `stories[].link` - optional, `{ "label", "url" }`
- `callout` - your one link of the day, `{ "text", "url", "label" }`
- `footer` - sender, signup source, working one-click `unsubscribe_url`,
  optional `postal_address` (CAN-SPAM likes one)

**4. Test-drive and rebuild.**

```bash
python3 build.py issues/my-issue.json
python3 -m unittest discover -s tests
```

**5. Ship.** Paste `dist/my-issue.html` into your provider and attach
`dist/my-issue.txt` as the plain-text alternative. Both arrive from the same
source, so they always agree with each other.

## How it survives Gmail and dark mode

1. **Explicit colors on every cell.** Dark-mode "help" kicks in when a color
   is missing. Every `td` carries its own `background-color`/color.
2. **Tables with inline styles.** Layout the oldest clients (and the newest
   webmail) both understand.
3. **`meta color-scheme: only light`.** The design owns its colors, so
   `prefers-color-scheme` does not locally repaint the card.
4. **Hidden preheader block.** Gmail shows `{PREHEADER}` next to the subject,
   not "View in browser" or the first odd sentence.
5. **A 600 px card on a full-width wrapper.** No fight with inbox sidebars.

The unit test suite pins every one of these down; if an edit breaks a
guarantee, the tests catch it before you hit send.

## Preview checks in detail

`dist/preview-report.txt` shows for each issue:

- subject length, with simulated ~40-char mobile and ~70-char desktop views
- preheader length and the exact text Gmail would pair with that subject
- warnings (faked `Re:` prefixes, `free`/`!!!` spam triggers, missing postal
  address) and hard errors (subject > 78 chars runs the build red)

## No-true-scotsman clause, for humans

An honest newsletter says who is sending, why you are on the list, how to
leave, and includes a physical address. This template refuses to build an
issue with a missing sender or unsubscribe URL, and its subjects are not
allowed to spoof `Re:`/`Fw:`.

## Running the tests

```bash
python3 -m unittest discover -s tests -v
```

29 checks cover: paired twin integrity, table-based structure, https-only
links, the one-link callout, dark-mode markers, hidden preheader, honest
footer, text-line widths, subject/preview rules, template tokens, and the
LICENSE/README shapes.

## Credits and license

Made by **Asdale Dynamics, LLC** as one of its open-source author and
small-business tools; connect to the hub at
https://dylanasdale.github.io/, where the book *The Massive AI Manual*
explains AI like a friend would.

MIT License. Copyright (c) 2026 Asdale Dynamics, LLC.
