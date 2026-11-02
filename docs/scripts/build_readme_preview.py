"""Render README.md as a static local preview (requires mistune and beautifulsoup4)."""

import hashlib
import os
import re
from pathlib import Path
from urllib.parse import urlsplit

import mistune
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[2]
CSS = """
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body { margin: 0; background: #fff; color: #1f2328;
  font: 16px/1.55 -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  letter-spacing: 0; }
main { max-width: 980px; margin: 24px auto; border: 1px solid #d1d9e0;
  border-radius: 6px; }
.file-heading { padding: 12px 30px; background: #f6f8fa;
  border-bottom: 1px solid #d1d9e0; font: 13px/1.5 ui-monospace, monospace; }
article { padding: 24px 32px 40px; }
h1, h2, h3 { line-height: 1.3; font-weight: 600; scroll-margin-top: 24px; }
h1 { font-size: 32px; margin: 0 0 16px; padding-bottom: 10px;
  border-bottom: 1px solid #d1d9e0; }
h2 { font-size: 24px; margin: 28px 0 16px; padding-bottom: 8px;
  border-bottom: 1px solid #d1d9e0; }
h3 { font-size: 20px; margin: 24px 0 16px; }
p { margin: 0 0 16px; }
a { color: #0969da; text-decoration: none; overflow-wrap: anywhere; }
a:hover { text-decoration: underline; }
a:focus-visible { outline: 2px solid #0969da; outline-offset: 3px; }
article > a { display: inline-block; margin-bottom: 16px; }
ul, ol { padding-left: 30px; margin: 0 0 16px; }
li { margin: 5px 0; overflow-wrap: anywhere; }
li p { margin-bottom: 8px; }
.contents { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0 24px; }
.contents li { margin: 2px 0; }
blockquote { margin: 24px 0; padding: 10px 16px; color: #59636e;
  background: #f6f8fa; border-left: 3px solid #8c959f; }
blockquote p:last-child, blockquote ul:last-child { margin-bottom: 0; }
blockquote ul { padding-left: 22px; }
hr { border: 0; border-top: 1px solid #d1d9e0; margin: 28px 0; }
img { max-width: 100%; height: auto; vertical-align: middle; }
img[height='41'] { height: 41px; width: auto; }
code { font: 13px/1.5 ui-monospace, monospace; background: #f6f8fa; }
pre { padding: 16px; overflow: auto; background: #f6f8fa; }
@media (max-width: 700px) {
  main { margin: 0; border: 0; border-radius: 0; }
  .file-heading { padding: 10px 18px; }
  article { padding: 20px 18px 32px; }
  p { margin-bottom: 12px; }
  .contents { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0 18px; }
  h1 { font-size: 28px; }
  h2 { font-size: 23px; }
}
@media (prefers-reduced-motion: reduce) { html { scroll-behavior: auto; } }
"""


def validate_source(source):
    expected = 1
    for number, line in enumerate(source.splitlines(), 1):
        if line.startswith("## "):
            expected = 1
        item = re.match(r"^(\d+)\.\s", line)
        if item:
            if int(item.group(1)) != expected:
                raise ValueError(f"README line {number}: expected list number {expected}.")
            expected += 1


def validate_collection(document):
    errors = []
    if document.select("ol ol"):
        errors.append("Nested book list: check for a duplicated list number.")
    for index, item in enumerate(document.select("ol > li"), 1):
        text = item.get_text(" ", strip=True)
        links = item.find_all("a", href=True)
        if not links:
            errors.append(f"Entry {index}: no clickable book link.")
        if re.search(r"\*{2,}|\]\(|\]\[|\[\[", text):
            errors.append(f"Entry {index}: unrendered Markdown.")
        if re.search(r"\bby\s+by\b", text, re.I):
            errors.append(f"Entry {index}: duplicated author prefix.")
        for link in links:
            target = urlsplit(link["href"])
            label = link.get_text()
            if target.scheme not in {"http", "https"} or not target.netloc:
                errors.append(f"Entry {index}: invalid book URL.")
            if '" by ' in label:
                errors.append(f"Entry {index}: stray quote or author inside link label.")
            if label.count("(") != label.count(")"):
                errors.append(f"Entry {index}: unbalanced title parentheses.")
    if errors:
        raise ValueError("Invalid collection formatting:\n" + "\n".join(errors))


def render(source, output):
    validate_source(source)
    markdown = mistune.create_markdown(escape=False)
    document = BeautifulSoup(markdown(source), "html.parser")
    validate_collection(document)
    seen = {}
    for heading in document.find_all(re.compile(r"^h[1-6]$")):
        slug = re.sub(r"[^\w\-\s]", "", heading.get_text().lower()).strip()
        slug = re.sub(r"\s+", "-", slug)
        suffix = seen.get(slug, 0)
        seen[slug] = suffix + 1
        heading["id"] = slug if suffix == 0 else f"{slug}-{suffix}"
    toc = document.find(id="table-of-contents")
    toc.find_next_sibling("ul")["class"] = "contents"
    for node in document.find_all(["a", "img"]):
        attribute = "href" if node.name == "a" else "src"
        value = node.get(attribute, "")
        if value and not value.startswith(("#", "/")) and not urlsplit(value).scheme:
            target = ROOT / value
            node[attribute] = os.path.relpath(target, output.parent)
        if node.name == "a" and node.get("target") == "_blank":
            node["rel"] = "noopener noreferrer"
    digest = hashlib.sha256(source.encode()).hexdigest()
    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="A collection of free mathematics books, with separately labeled commercial editions.">
<meta name="readme-sha256" content="{digest}">
<title>Awesome Math Books | Free Book Collection</title>
<style>{CSS}</style>
</head>
<body>
<main>
<div class="file-heading">README.md</div>
<article>{document}</article>
</main>
</body>
</html>
"""
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")


if __name__ == "__main__":
    source = (ROOT / "README.md").read_text(encoding="utf-8")
    for output in (
        ROOT / "docs" / "index.html",
        ROOT / "docs" / "preview.html",
        ROOT / "docs" / "collection-preview.html",
    ):
        render(source, output)
        print(output)
