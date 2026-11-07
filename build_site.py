"""Build the research site from Markdown in publish/."""

import argparse
from html import escape
import json
from pathlib import Path
import re
import shutil
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parent

CSS = """
:root { color-scheme: light; --ink: #261D11; --muted: #515151; --line: #d4d4d4; --wood: #F2E2C4; --blue: #0477BF; --yellow: #F2B705; --red: #A6290D; }
* { box-sizing: border-box; }
body { margin: 0; background: #fff; color: var(--ink); font: 1rem/1.8 system-ui, sans-serif; }
.wrap { width: min(64rem, calc(100% - 2.5rem)); margin-inline: auto; }
header, footer { padding-block: 1rem; border-block-end: 1px solid var(--line); }
footer { border-block-start: 1px solid var(--line); margin-block-start: 3rem; color: var(--muted); }
a { color: inherit; text-underline-offset: .2em; overflow-wrap: anywhere; }
a:focus-visible { outline: 3px solid #984322; outline-offset: 4px; }
.hero { margin-block: 2rem; display: grid; grid-template-columns: 2fr 1fr; background: var(--wood); }
.hero-copy { padding: clamp(1.4rem, 5vw, 4rem); }
.geometry { display: grid; grid-template-columns: 1fr 1fr; min-height: 8rem; overflow: hidden; background: var(--ink); }
.geometry i:first-child { grid-row: span 2; background: var(--blue); border-radius: 100% 0 0 100%; }
.geometry i:nth-child(2) { background: var(--yellow); border-radius: 0 0 100% 0; }
.geometry i:nth-child(3) { background: var(--red); border-radius: 100% 0 0 0; }
.about { border-block-end: 1px solid var(--line); margin-block-end: 2rem; }
nav { margin-block-end: 1rem; }
@media (max-width: 36rem) { .hero { grid-template-columns: 1fr; } }
h1, h2 { line-height: 1.3; }
h1 { font-size: clamp(2.2rem, 7vw, 4rem); margin: .35rem 0 .75rem; }
.kicker, .badge { color: var(--red); font-weight: 700; }
nav { display: flex; flex-wrap: wrap; gap: .6rem 1.4rem; }
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 24rem), 1fr)); gap: 1rem; }
.panel { padding: 1.2rem 1.4rem; background: #f5f5f5; border: 1px solid var(--line); }
.panel h2 { margin-block-start: 0; }
.panel ul { padding-inline-start: 1.2rem; }
.count, .empty, .intro { color: var(--muted); }
.reading { max-width: 46rem; margin-inline: auto; padding-block: 2.5rem; }
.reading h1 { font-size: clamp(2rem, 5vw, 3.1rem); }
.reading h2 { margin-block-start: 2rem; }
"""


def read_articles(categories):
    articles = {}
    for file in sorted((ROOT / "publish").glob("*.md")):
        opening, separator, rest = file.read_text(encoding="utf-8").partition("\n---\n")
        if not separator or not opening.startswith("---\n"):
            raise ValueError(f"{file.name} 缺少文章檔頭")
        data = {}
        for line in opening.splitlines()[1:]:
            key, _, value = line.partition(":")
            data[key.strip()] = json.loads(value)
        slug = data["slug"]
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug) or slug in articles:
            raise ValueError(f"{file.name} 的 slug 無效或重複")
        if data["category"] not in categories:
            raise ValueError(f"{file.name} 的分類不在 categories.json")
        articles[slug] = {**data, "body": rest}
    return articles


def inline(text):
    parts = re.split(r"(https?://[^\s<>]+|\*[^*\n]+\*)", text)
    for index in range(1, len(parts), 2):
        token = parts[index]
        if token.startswith("*"):
            parts[index] = f"<em>{escape(token[1:-1])}</em>"
        else:
            url = escape(token, quote=True)
            parts[index] = f'<a href="{url}">{url}</a>'
    return "".join(escape(part) if index % 2 == 0 else part
                   for index, part in enumerate(parts))


def article_body(markdown):
    blocks = re.split(r"\n\s*\n", markdown.strip())
    html = []
    for block in blocks:
        if block.startswith("# "):
            continue
        if block.startswith("## "):
            html.append(f"<h2>{inline(block[3:])}</h2>")
        else:
            html.append(f"<p>{inline(block)}</p>")
    return "\n".join(html)


def layout(title, content, home="./", preview=False):
    banner = '<span class="badge">本機預覽</span>' if preview else ""
    return f"""<!doctype html>
<html lang="zh-Hant"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)}｜個人研究筆記</title>
<style>{CSS}</style>
<header><div class="wrap"><a href="{home}index.html">個人研究筆記</a>　{banner}</div></header>
<main class="wrap">{content}</main>
<footer><div class="wrap">個人研究筆記</div></footer>
</html>
"""


def build(target, categories, articles, preview):
    target.mkdir()
    (target / "posts").mkdir()
    sections = []
    shortcuts = []
    for index, category in enumerate(categories, start=1):
        label = escape(category)
        anchor = f"category-{index}"
        shortcuts.append(f'<a href="#{anchor}">{label}</a>')
        items = []
        for slug, article in articles.items():
            if article["category"] == category:
                title = escape(article["title"])
                items.append(f'<li><a href="posts/{slug}.html">{title}</a></li>')
        listing = "<ul>" + "".join(items) + "</ul>" if items else '<p class="empty">這個分類目前沒有文章。</p>'
        sections.append(f'<section class="panel" id="{anchor}"><h2>{label} <small class="count">({len(items)})</small></h2>{listing}</section>')
    homepage = f"""
<section class="hero"><div class="hero-copy"><div class="kicker">RESEARCH NOTES</div><h1>個人研究筆記</h1>
<p class="intro">這裡收錄我寫過的文獻部落格，從研究問題和案例出發，整理科技、組織與創新相關的閱讀。</p></div><div class="geometry" aria-hidden="true"><i></i><i></i><i></i></div></section>
<section class="about"><h2>關於我</h2><p>我是張恩綺，目前就讀國立政治大學科技管理與智慧財產研究所碩士班，研究興趣是科技導入與意義建構。</p></section>
<section aria-labelledby="archive"><h2 id="archive">文章索引</h2><nav aria-label="文章分類">{"".join(shortcuts)}</nav>
<div class="grid">{"".join(sections)}</div></section>"""
    (target / "index.html").write_text(layout("閱讀索引", homepage, preview=preview), encoding="utf-8")
    for slug, article in articles.items():
        title = escape(article["title"])
        category = escape(article["category"])
        content = f'<article class="reading"><div class="kicker">{category}</div><h1>{title}</h1>{article_body(article["body"])}<a href="../index.html">← 返回文章索引</a></article>'
        (target / "posts" / f"{slug}.html").write_text(layout(article["title"], content, "../", preview), encoding="utf-8")
    (target / ".nojekyll").touch()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview", action="store_true")
    args = parser.parse_args()
    categories = json.loads((ROOT / "categories.json").read_text(encoding="utf-8"))
    articles = read_articles(categories)
    output = ROOT / ("preview" if args.preview else "site")
    with TemporaryDirectory(dir=ROOT) as staging:
        generated = Path(staging) / "generated"
        build(generated, categories, articles, args.preview)
        if output.exists():
            shutil.rmtree(output)
        generated.rename(output)
    print(f"{len(articles)} 篇文章 → {output / 'index.html'}")


if __name__ == "__main__":
    main()
