#!/usr/bin/env python3
"""
plain-email-newsletter-template - build.py

Turns one JSON file per issue into a paired email set:
  dist/<slug>.html        the email: table-based, inline styles, dark-mode safe
  dist/<slug>.txt         the plain-text twin
  dist/preview-report.txt subject-line and preview-text checks

Sources of truth: issues/*.json + template/issue.template.html.
Stories are authored as plain paragraphs, so the HTML and text twins can
never drift apart. Standard library only - works offline, no installs.

Usage:
  python3 build.py            build every issue in issues/ into dist/
  python3 build.py FILE.json  build specific issues
  python3 build.py --help
"""

import argparse
import json
import re
import sys
import textwrap
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TEMPLATE_PATH = ROOT / "template" / "issue.template.html"
DEFAULT_ISSUES_DIR = ROOT / "issues"
DEFAULT_OUT_DIR = ROOT / "dist"

ACCENT_BG = "#0f4c50"
ACCENT_TEXT = "#ffffff"
INK = "#1c1c1c"
MUTED = "#5f5a4e"
RULE = "#e3ded3"
TINT_BG = "#fbfaf6"
CARD_BG = "#ffffff"
PAGE_BG = "#f4f2ec"

URL_REGEXP = re.compile(r"^https?://\S+$")
LEFTOVER_TOKEN = re.compile(r"\{[A-Z_]+\}")

WRAP = 74
SUBJECT_HARD_LIMIT = 78
SUBJECT_SOFT_LIMIT = 62
PREHEADER_MIN = 35
PREHEADER_MAX = 105


# ---------------------------------------------------------------- validation

def validate_issue(data, slug):
    """Check one issue; return (errors, warnings) as human-readable strings."""
    errors = []
    warnings = []

    for field in ("subject", "preheader", "header_title", "date"):
        if not str(data.get(field, "")).strip():
            errors.append(f"{slug}: missing required field '{field}'")
    if not data.get("slug") or not re.match(r"^[A-Za-z0-9._-]+$", str(data.get("slug"))):
        errors.append(
            f"{slug}: 'slug' is required and may only contain letters, digits, '.', '_', '-'"
        )

    stories = data.get("stories")
    if not isinstance(stories, list) or not stories:
        errors.append(f"{slug}: needs at least one story under 'stories'")
    else:
        for i, story in enumerate(stories, 1):
            label = f"{slug}: story {i}"
            extra = set(story) - {"title", "paragraphs", "link"}
            if extra:
                warnings.append(
                    f"{label}: unknown keys {sorted(extra)} will be ignored"
                )
            if not str(story.get("title", "")).strip():
                errors.append(f"{label}: missing 'title'")
            paragraphs = story.get("paragraphs")
            if not isinstance(paragraphs, list) or not any(
                str(p).strip() for p in paragraphs
            ):
                errors.append(
                    f"{label}: needs 'paragraphs', a non-empty list of sentences"
                )
            link = story.get("link")
            if link is not None:
                if not isinstance(link, dict) or not URL_REGEXP.match(
                    str(link.get("url", ""))
                ):
                    errors.append(f"{label}: 'link.url' must be an http(s) URL")
                elif not str(link.get("label", "")).strip():
                    errors.append(f"{label}: 'link.label' is required with 'link.url'")

    callout = data.get("callout") or {}
    for field in ("text", "url", "label"):
        if not str(callout.get(field, "")).strip():
            errors.append(
                f"{slug}: callout needs '{field}' (the one-link callout is required)"
            )
    if callout.get("url") and not URL_REGEXP.match(str(callout["url"])):
        errors.append(f"{slug}: callout 'url' must be an http(s) URL")

    footer = data.get("footer") or {}
    for field in ("sender", "unsubscribe_url"):
        if not str(footer.get(field, "")).strip():
            errors.append(
                f"{slug}: footer needs '{field}' (an honest footer is required)"
            )
    if not footer.get("postal_address"):
        warnings.append(
            f"{slug}: footer has no 'postal_address'; CAN-SPAM expects a physical address"
        )
    if footer.get("unsubscribe_url") and not URL_REGEXP.match(
        str(footer["unsubscribe_url"])
    ):
        errors.append(f"{slug}: footer 'unsubscribe_url' must be an http(s) URL")
    elif str(footer.get("unsubscribe_url", "")).startswith("http://"):
        warnings.append(f"{slug}: footer 'unsubscribe_url' should be https://")

    if errors:
        return errors, warnings

    subject = str(data["subject"])
    if len(subject) > SUBJECT_HARD_LIMIT:
        errors.append(
            f"{slug}: subject is {len(subject)} chars (limit {SUBJECT_HARD_LIMIT}); "
            "it would be clipped in every inbox"
        )
    elif len(subject) > SUBJECT_SOFT_LIMIT:
        warnings.append(
            f"{slug}: subject is {len(subject)} chars (soft limit {SUBJECT_SOFT_LIMIT}); "
            f'most phones will show about "{subject[:40]}..."'
        )
    if subject.lower().startswith(("re:", "fw:", "fwd:")):
        errors.append(f"{slug}: subject must not fake 'Re:'/'Fw:' - keep it honest")
    if "!!!" in subject or "free" in subject.lower():
        warnings.append(f"{slug}: subject contains spam-trigger wording ('!!!' / 'free')")

    preheader = str(data["preheader"])
    if len(preheader) > PREHEADER_MAX:
        warnings.append(
            f"{slug}: preheader is {len(preheader)} chars; Gmail shows about {PREHEADER_MAX}"
        )
    elif len(preheader) < PREHEADER_MIN:
        warnings.append(
            f"{slug}: preheader is {len(preheader)} chars; aim for "
            f"{PREHEADER_MIN}-{PREHEADER_MAX} so it does not collapse to one word"
        )

    return errors, warnings


def preview_lines(data, errors, warnings):
    """Subject/preview truncation simulation for the preview report."""
    status_bits = []
    if errors:
        status_bits.append(f"ERRORS: {len(errors)}")
    if warnings:
        status_bits.append(f"warnings: {len(warnings)}")
    lines = [f"{data['slug']}: " + ("; ".join(status_bits) if status_bits else "clean")]

    subject = str(data["subject"])
    preheader = str(data["preheader"])
    mobile = 40
    desktop = 70
    lines.append(f'  subject ({len(subject)} chars): "{subject}"')
    lines.append(
        f'    phone view   -> "{subject[:mobile]}"'
        + ("  |...truncated" if len(subject) > mobile else "")
    )
    lines.append(
        f'    desktop view -> "{subject[:desktop]}"'
        + ("  |...truncated" if len(subject) > desktop else "")
    )
    state = "OK" if PREHEADER_MIN <= len(preheader) <= PREHEADER_MAX else "review"
    lines.append(f"  preheader ({len(preheader)} chars) shows beside the subject [{state}]:")
    lines.append(f'    "{preheader}"')
    return lines


# ---------------------------------------------------------------- rendering

def _esc(text):
    return escape(str(text), quote=False)


def _par_1():
    return {}


def _story_html(story):
    rows = [
        "<table role=\"presentation\" width=\"100%\" cellpadding=\"0\" cellspacing=\"0\" "
        f"border=\"0\" bgcolor=\"{CARD_BG}\" style=\"background-color:{CARD_BG};\">"
    ]
    rows.append(
        f'<tr><td style="padding:26px 28px 0 28px;font-family:Arial,Helvetica,sans-serif;'
        f'font-size:20px;line-height:26px;font-weight:bold;color:{INK};">{_esc(story["title"])}</td></tr>'
    )
    for paragraph in story["paragraphs"]:
        text = str(paragraph).strip()
        if not text:
            continue
        rows.append(
            f'<tr><td style="padding:12px 28px 0 28px;font-family:Arial,Helvetica,sans-serif;'
            f'font-size:16px;line-height:24px;color:{INK};">{_esc(text)}</td></tr>'
        )
    link = story.get("link")
    if link:
        rows.append(
            '<tr><td style="padding:14px 28px 0 28px;font-family:Arial,Helvetica,sans-serif;">'
            f'<a href="{escape(str(link["url"]))}" target="_blank" rel="noopener noreferrer" '
            f'style="color:{ACCENT_BG};text-decoration:underline;">'
            f'{_esc(link["label"])}</a></td></tr>'
        )
    rows.append(
        f'<tr><td style="padding:22px 28px 0 28px;">'
        f'<hr style="border:none;border-top:1px solid {RULE};margin:0;"></td></tr>'
    )
    rows.append("</table>")
    return "".join(rows)


def _signature_html():
    return (
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        f'border="0" bgcolor="{CARD_BG}" style="background-color:{CARD_BG};"><tr>'
        f'<td style="padding:18px 28px 30px 28px;font-family:Arial,Helvetica,sans-serif;'
        f'font-size:16px;line-height:24px;color:{INK};">'
        "Small steps, clearly explained. That is the whole trick.</td></tr></table>"
    )


def _callout_html(callout):
    return (
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        'border="0"><tr>'
        f'<td bgcolor="{TINT_BG}" style="padding:28px;background-color:{TINT_BG};'
        f'color:{INK};">'
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        'border="0"><tr><td>'
        '<p style="margin:0 0 16px 0;font-family:Arial,Helvetica,sans-serif;font-size:15px;'
        f'line-height:23px;color:{INK};">'
        f'<strong style="color:{ACCENT_BG};">One thing worth your time.</strong><br>'
        f'{_esc(callout["text"])}</p>'
        '<table role="presentation" cellpadding="0" cellspacing="0" border="0" '
        'style="margin:0;"><tr>'
        f'<td bgcolor="{ACCENT_BG}" style="background-color:{ACCENT_BG};border-radius:6px;">'
        f'<a href="{escape(str(callout["url"]))}" target="_blank" rel="noopener noreferrer" '
        'style="display:inline-block;padding:12px 22px;font-family:Arial,Helvetica,sans-serif;'
        f'font-size:15px;line-height:19px;font-weight:bold;color:{ACCENT_TEXT};'
        f'text-decoration:none;border-radius:6px;">{_esc(callout["label"])}</a>'
        "</td></tr></table>"
        "</td></tr></table>"
        "</td>"
        "</tr></table>"
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        'border="0"><tr>'
        f'<td style="padding:28px 28px 0 28px;">'
        f'<hr style="border:none;border-top:1px solid {RULE};margin:0;"></td>'
        "</tr></table>"
    )


def _footer_html(data):
    footer = data["footer"]
    parts = ['<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
             f'border="0" bgcolor="{CARD_BG}" style="background-color:{CARD_BG};"><tr>'
             '<td style="padding:6px 28px 30px 28px;font-family:Arial,Helvetica,sans-serif;'
             f'font-size:13px;line-height:20px;color:{MUTED};">']

    parts.append(
        f'<p style="margin:0 0 10px 0;">Why you got this: you subscribed to '
        f'{_esc(data["header_title"])} at {_esc(footer.get("signup_source", "our signup page"))}. '
        f'This issue is dated {_esc(data["date"])}.</p>'
    )

    sent = f'Sent by {_esc(footer["sender"])}.'
    if footer.get("postal_address"):
        sent += f" Postal address: {_esc(footer['postal_address'])}."
    parts.append(f'<p style="margin:0 0 10px 0;">{sent}</p>')

    parts.append(
        f'<p style="margin:0 0 10px 0;">Done for now: '
        f'<a href="{escape(str(footer["unsubscribe_url"]))}" target="_blank" '
        f'rel="noopener noreferrer" style="color:{ACCENT_BG};text-decoration:underline;">'
        'unsubscribe in one click</a>. No guilt, no "did you mean to leave?" maze.</p>'
    )
    parts.append(
        '<p style="margin:0;">Plain in, plain out. The template that made this '
        'is MIT licensed - see the repository README.</p>'
    )
    parts.append("</td></tr></table>")
    return "".join(parts)


def render_html(data):
    """Render the full newsletter email for one issue."""
    stories_block = "".join(_story_html(story) for story in data["stories"])
    stories_block += _signature_html()

    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    substitutions = {
        "SUBJECT": escape(str(data["subject"]), quote=True),
        "PREHEADER": escape(str(data["preheader"]), quote=False),
        "HEADER_TITLE": escape(str(data["header_title"]), quote=False),
        "HEADER_DATE": escape(str(data["date"]), quote=False),
        "STORIES": stories_block,
        "CALLOUT": _callout_html(data["callout"]),
        "FOOTER": _footer_html(data),
    }
    html = template
    for token, value in substitutions.items():
        html = html.replace("{" + token + "}", value)
    leftover = LEFTOVER_TOKEN.findall(html)
    if leftover:
        raise ValueError(
            "unfilled template tokens remain: " + ", ".join(sorted(set(leftover)))
        )
    return html


# ------------------------------------------------------------ plain-text twin

def render_text(data):
    """Render the plain-text twin for one issue."""
    sep = "-" * WRAP
    out = [f"{data['header_title']} - {data['date']}", sep, ""]

    out.append("The short version, in one line:")
    out.append(textwrap.fill(str(data["preheader"]), WRAP, initial_indent="  ", subsequent_indent="  "))
    out.append("")

    out.append(sep)
    out.append("IN THIS ISSUE")
    for story in data["stories"]:
        out.append(f"  * {story['title']}")
    out.append("")

    for story in data["stories"]:
        out.append(sep)
        out.append(str(story["title"]).upper())
        out.append("")
        for paragraph in story["paragraphs"]:
            text = str(paragraph).strip()
            if not text:
                continue
            out.append(textwrap.fill(text, WRAP))
            out.append("")
        link = story.get("link")
        if link:
            out.append(f"Link ({link['label']}):")
            out.append(f"  {link['url']}")
            out.append("")

    out.append(sep)
    out.append("ONE THING WORTH YOUR TIME")
    out.append("")
    out.append(textwrap.fill(str(data["callout"]["text"]), WRAP))
    out.append("")
    out.append(f"{data['callout']['label']}:")
    out.append(f"  {data['callout']['url']}")
    out.append("")

    out.append(sep)
    footer = data["footer"]
    out.append(
        textwrap.fill(
            f"Why you got this: you subscribed to {data['header_title']} at "
            f"{footer.get('signup_source', 'our signup page')}. Dated {data['date']}.",
            WRAP,
        )
    )
    sent = f"Sent by {footer['sender']}."
    if footer.get("postal_address"):
        sent += f" Postal address: {footer['postal_address']}."
    out.append(textwrap.fill(sent, WRAP))
    out.append("Unsubscribe in one click:")
    out.append(f"  {footer['unsubscribe_url']}")
    out.append("")
    out.append("Plain in, plain out.")

    cleaned = [line.rstrip() for line in "\n".join(out).split("\n")]
    return "\n".join(cleaned) + "\n"


# ------------------------------------------------------------------- driver

def build_issue(data):
    """Validate and render an issue.

    Returns (html, text, errors, warnings).
    """
    errors, warnings = validate_issue(data, data.get("slug", "issue"))
    if errors:
        return None, None, errors, warnings
    return render_html(data), render_text(data), errors, warnings


def _load_issue_file(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: top level must be a JSON object")
    if not str(data.get("slug", "")).strip():
        data["slug"] = path.stem
    return data


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Build newsletter issues into paired HTML + plain-text files."
    )
    parser.add_argument(
        "issue_files", nargs="*", help=".json issue files (default: all in issues/)"
    )
    parser.add_argument("--out", default=str(DEFAULT_OUT_DIR), help="output directory")
    args = parser.parse_args(argv)

    files = [Path(f) for f in args.issue_files] or sorted(DEFAULT_ISSUES_DIR.glob("*.json"))
    if not files:
        print("No issue files found in issues/.", file=sys.stderr)
        return 1

    out_dir = Path(args.out)
    all_errors, all_warnings, previews = [], [], []

    for path in files:
        try:
            data = _load_issue_file(path)
        except (json.JSONDecodeError, ValueError) as exc:
            all_errors.append(str(exc))
            continue
        html, text, errors, warnings = build_issue(data)
        all_errors.extend(errors)
        all_warnings.extend(warnings)
        previews.extend(preview_lines(data, errors, warnings))
        if errors:
            continue
        slug = data["slug"]
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / f"{slug}.html").write_text(html, encoding="utf-8")
        (out_dir / f"{slug}.txt").write_text(text, encoding="utf-8")
        print(f"built {slug} -> {out_dir / (slug + '.html')} and .txt")

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "preview-report.txt").write_text("\n".join(previews) + "\n", encoding="utf-8")

    for warning in all_warnings:
        print(f"warning: {warning}")
    for error in all_errors:
        print(f"error: {error}", file=sys.stderr)
    if all_errors:
        print(f"\n{len(all_errors)} error(s); failing build.", file=sys.stderr)
        return 1
    print(f"\nPreview report: {out_dir / 'preview-report.txt'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
