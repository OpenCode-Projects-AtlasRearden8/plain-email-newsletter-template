"""Tests for plain-email-newsletter-template.

Standard library only:
    python3 -m unittest discover -s tests -v

They validate the emitted HTML and plain-text parts, the subject-line and
preview checks, and the template tokens. The dist/ folder serves as the
fixture; tests that mutate issue data build their own copies to /tmp.
"""

import json
import re
import shutil
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import build  # noqa: E402

REQUIRED_TOKENS = [
    "SUBJECT", "PREHEADER", "HEADER_TITLE", "HEADER_DATE", "STORIES",
    "CALLOUT", "FOOTER",
]
COPYRIGHT_LINE = "Copyright (c) 2026 Asdale Dynamics, LLC"


def build_all():
    out = Path(tempfile.mkdtemp(prefix="pwd-dist-"))
    code = build.main(["--out", str(out)])
    return out, code


def load_issues():
    return [build._load_issue_file(p) for p in sorted(build.DEFAULT_ISSUES_DIR.glob("*.json"))]


class SnapshotBuild(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out, cls.code = build_all()
        cls.issues = load_issues()
        cls.results = []
        for data in cls.issues:
            html, text, errs, warns = build.build_issue(data)
            cls.results.append((data, html, text, errs, warns))

    def test_all_three_issues_built(self):
        self.assertEqual(len(self.issues), 3, "repo must ship exactly three sample issues")
        self.assertEqual(self.code, 0)

    def test_paired_files_exist_for_every_issue(self):
        for data, *_ in self.results:
            html_path = self.out / f"{data['slug']}.html"
            text_path = self.out / f"{data['slug']}.txt"
            self.assertTrue(html_path.exists(), html_path)
            self.assertTrue(text_path.exists(), text_path)

    def test_html_and_text_are_true_twins(self):
        for data, html, text, _, _ in self.results:
            self.assertIn(data["preheader"], html)
            self.assertIn(
                textwrap.fill(
                    data["preheader"], build.WRAP,
                    initial_indent="  ", subsequent_indent="  ",
                ),
                text,
            )
            self.assertIn(data["header_title"], html)
            self.assertIn(data["header_title"], text)
            self.assertIn(data["callout"]["url"], html)
            self.assertIn(data["callout"]["url"], text)
            for story in data["stories"]:
                self.assertIn(story["title"], html)
                self.assertIn(story["title"], text)
                for paragraph in story["paragraphs"]:
                    body = str(paragraph).strip()
                    if not body:
                        continue
                    self.assertIn(body[:40], html)
                    self.assertIn(
                        textwrap.fill(body, build.WRAP),
                        text,
                        f"paragraph not rendered verbatim in text twin: {body[:40]}...",
                    )


class EmittedHtml(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out, cls.code = build_all()
        cls.issues = load_issues()

    def test_table_based_and_fixed_width(self):
        for data in self.issues:
            html = (self.out / f"{data['slug']}.html").read_text(encoding="utf-8")
            self.assertIn('<table role="presentation"', html)
            self.assertTrue(html.count("<table") >= 6, "shell must not be a div pie")
            self.assertIn("width:600px", html)
            self.assertIn('bgcolor="#0f4c50"', html, "header band missing")

    def test_no_scripts_no_external_css_no_images(self):
        for data in self.issues:
            html = (self.out / f"{data['slug']}.html").read_text(encoding="utf-8")
            self.assertNotIn("<script", html.lower())
            self.assertNotIn("<style", html.lower())
            self.assertNotIn("<img", html.lower())
            self.assertNotIn("<link", html.lower())
            self.assertNotIn("<iframe", html.lower())

    def test_every_href_is_https(self):
        for data in self.issues:
            html = (self.out / f"{data['slug']}.html").read_text(encoding="utf-8")
            hrefs = re.findall(r'href="(http[^"]+)"', html)
            self.assertTrue(hrefs, "issue must contain at least one link")
            for href in hrefs:
                self.assertTrue(href.startswith("https://"), f"insecure href: {href}")

    def test_callout_has_exactly_one_link(self):
        for data in self.issues:
            html = (self.out / f"{data['slug']}.html").read_text(encoding="utf-8")
            region = html.split("callout:start")[1].split("callout:end")[0]
            anchors = region.count("<a ")
            self.assertEqual(anchors, 1, "one-link callout was more than one link")
            self.assertIn(escape_url(data["callout"]["url"]), region)
            self.assertIn(data["callout"]["label"], region)

    def test_dark_mode_survival_markers(self):
        for data in self.issues:
            html = (self.out / f"{data['slug']}.html").read_text(encoding="utf-8")
            for marker in (
                'background-color:#f4f2ec',
                'background-color:#ffffff',
                'color:#1c1c1c',
                "color-scheme",
            ):
                self.assertIn(marker, html, f"dark-mode marker missing: {marker}")

    def test_preheader_hidden_block_present(self):
        for data in self.issues:
            html = (self.out / f"{data['slug']}.html").read_text(encoding="utf-8")
            self.assertIn("display:none", html)
            self.assertIn(data["preheader"], html.split("</head>")[1])

    def test_honest_footer(self):
        for data in self.issues:
            html = (self.out / f"{data['slug']}.html").read_text(encoding="utf-8")
            region = html.split("footer:start")[1].split("footer:end")[0]
            self.assertIn("Why you got this", region)
            self.assertIn("Asdale Dynamics, LLC", region)
            self.assertIn(data["footer"]["unsubscribe_url"], region)
            self.assertIn("unsubscribe in one click", region)


def escape_url(url):
    from html import escape
    return escape(url)


class PlainTextTwins(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out, cls.code = build_all()
        cls.issues = load_issues()

    def test_lines_do_not_exceed_78_columns(self):
        for data in self.issues:
            text = (self.out / f"{data['slug']}.txt").read_text(encoding="utf-8")
            for line in text.split("\n"):
                self.assertLessEqual(len(line), 78, f"long line in text twin: {line!r}")

    def test_text_twin_skeleton(self):
        for data in self.issues:
            text = (self.out / f"{data['slug']}.txt").read_text(encoding="utf-8")
            self.assertIn("IN THIS ISSUE", text)
            self.assertIn("ONE THING WORTH YOUR TIME", text)
            self.assertIn(data["footer"]["unsubscribe_url"], text)
            self.assertIn(data["footer"]["sender"], text)
            self.assertIn("Why you got this", text)
            self.assertIn("Unsubscribe in one click", text)
            self.assertNotIn("Copyright", text)

    def test_no_trailing_whitespace_and_single_trailing_newline(self):
        for data in self.issues:
            text = (self.out / f"{data['slug']}.txt").read_text(encoding="utf-8")
            self.assertFalse(text.endswith("\n\n"))
            for line in text.split("\n"):
                self.assertEqual(line, line.rstrip(), f"trailing space: {line!r}")


class SubjectAndPreviewChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.issues = load_issues()
        cls.good = json.loads(json.dumps(cls.issues[0]))

    def test_clean_issue_passes_with_no_findings(self):
        errors, warnings = build.validate_issue(self.good, self.good["slug"])
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_overlong_subject_is_a_hard_error(self):
        bad = json.loads(json.dumps(self.good))
        bad["subject"] = "x" * 200
        errors, _ = build.validate_issue(bad, bad["slug"])
        self.assertTrue(any("subject is 200 chars" in e for e in errors))

    def test_62_to_78_char_subject_is_a_warning_once(self):
        bad = json.loads(json.dumps(self.good))
        bad["subject"] = "x" * 70
        errors, warnings = build.validate_issue(bad, bad["slug"])
        self.assertEqual(errors, [])
        self.assertEqual(len([w for w in warnings if "soft limit" in w]), 1)

    def test_faked_reply_prefix_is_rejected(self):
        bad = json.loads(json.dumps(self.good))
        bad["subject"] = "Re: your question about AI"
        errors, _ = build.validate_issue(bad, bad["slug"])
        self.assertTrue(any("Re:" in e for e in errors))

    def test_short_preheader_warns(self):
        bad = json.loads(json.dumps(self.good))
        bad["preheader"] = "Hi there"
        errors, warnings = build.validate_issue(bad, bad["slug"])
        self.assertEqual(errors, [])
        self.assertTrue(any("preheader is 8 chars" in w for w in warnings))

    def test_missing_honest_footer_fields_are_errors(self):
        bad = json.loads(json.dumps(self.good))
        del bad["footer"]["sender"]
        del bad["footer"]["unsubscribe_url"]
        errors, _ = build.validate_issue(bad, bad["slug"])
        self.assertTrue(any("footer needs 'sender'" in e for e in errors))
        self.assertTrue(any("unsubscribe_url" in e for e in errors))

    def test_missing_postal_address_warns(self):
        bad = json.loads(json.dumps(self.good))
        del bad["footer"]["postal_address"]
        errors, warnings = build.validate_issue(bad, bad["slug"])
        self.assertEqual(errors, [])
        self.assertTrue(any("postal_address" in w for w in warnings))

    def test_unknown_story_key_warns(self):
        bad = json.loads(json.dumps(self.good))
        bad["stories"][0]["vibes"] = "high"
        errors, warnings = build.validate_issue(bad, bad["slug"])
        self.assertEqual(errors, [])
        self.assertTrue(any("vibes" in w for w in warnings))

    def test_empty_issue_is_rejected_firmly(self):
        errors, _ = build.validate_issue({}, "empty")
        self.assertGreaterEqual(len(errors), 3)
        self.assertTrue(any("stories" in e for e in errors))
        self.assertTrue(any("callout" in e for e in errors))
        self.assertTrue(any("footer needs" in e for e in errors))

    def test_preview_report_lists_every_issue(self):
        out, _ = build_all()
        report = (out / "preview-report.txt").read_text(encoding="utf-8")
        for data in self.issues:
            self.assertIn(data["slug"], report)
        self.assertIn("|...truncated", report)


class TemplateIntegrity(unittest.TestCase):
    def test_template_has_all_tokens(self):
        template = build.TEMPLATE_PATH.read_text(encoding="utf-8")
        for token in REQUIRED_TOKENS:
            self.assertIn("{" + token + "}", template, token)

    def test_leftover_tokens_fail_loudly(self):
        data = load_issues()[0].copy()
        original = build.TEMPLATE_PATH.read_text(encoding="utf-8")
        template_copy = build.ROOT / "tests" / "artifacts"
        try:
            template_copy.mkdir(exist_ok=True)
            broken = original.replace("{CALLOUT}", "{CALLOUT_BINDING_MISSING}")
            (template_copy / "break.html").write_text(broken, encoding="utf-8")
            build.TEMPLATE_PATH = template_copy / "break.html"
            with self.assertRaises(ValueError) as ctx:
                build.render_html(data)
            self.assertIn("CALLOUT_BINDING_MISSING", str(ctx.exception))
        finally:
            build.TEMPLATE_PATH = build.ROOT / "template" / "issue.template.html"
            shutil.rmtree(template_copy, ignore_errors=True)

    def test_render_text_is_stable(self):
        data = load_issues()[0]
        self.assertEqual(build.render_text(data), build.render_text(data))


class RepoShapes(unittest.TestCase):
    def test_license_is_exact_mit_line(self):
        license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
        self.assertIn(COPYRIGHT_LINE, license_text)
        self.assertIn("MIT License", license_text)

    def test_readme_credits_and_teaches(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("Asdale Dynamics, LLC", readme)
        self.assertIn("MIT", readme)
        self.assertIn("python3 build.py", readme)

    def test_requirement_sources_are_offline_stdlib(self):
        build_py = (ROOT / "build.py").read_text(encoding="utf-8")
        self.assertIn("Standard library only", build_py)
        for module in ("ssl", "smtplib", "imaplib"):
            self.assertNotIn(f"import {module}", build_py)


if __name__ == "__main__":
    unittest.main()
