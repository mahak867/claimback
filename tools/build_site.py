"""Build site/index.html (a full HTML document for hosting) from prototype/index.html.

Usage:  python tools/build_site.py
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HEAD = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="description" content="ClaimBack: a free AI agent that turns a rejected Indian health insurance claim into a cited appeal, in English, Tamil or Hindi. Prototype with a fictional case.">
<meta name="color-scheme" content="light dark">
"""


def build() -> str:
    page = (ROOT / "prototype" / "index.html").read_text(encoding="utf-8")
    head, sep, rest = page.partition("<style>")
    if not sep:
        raise SystemExit("prototype/index.html has no <style> block")
    return HEAD + head + "</head>\n<body>\n<style>" + rest + "\n</body>\n</html>\n"


if __name__ == "__main__":
    out = ROOT / "site" / "index.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(build(), encoding="utf-8")
    print(f"Wrote {out.relative_to(ROOT)}")
